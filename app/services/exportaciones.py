"""Exportaciones (HU-17 a HU-22) y transporte (HU-23)."""
from __future__ import annotations

import datetime as dt

from flask import g

from ..domain.reglas import (
    ESTADOS_CERRADOS,
    TRANSICIONES,
    siguiente_consecutivo,
    transicion_valida,
)
from ..errors import NoEncontrado, ReglaNegocio
from ..repositories.catalogos import ClienteRepositorio, PaisRepositorio
from ..repositories.exportaciones import ExportacionRepositorio
from ..repositories.productos import InventarioRepositorio, ProductoRepositorio
from . import inventario as inventario_srv


def _exigir(exportacion_id: int) -> dict:
    exp = ExportacionRepositorio().por_id(exportacion_id)
    if not exp:
        raise NoEncontrado("Exportación no encontrada")
    return exp


MODOS = {"MARITIMO": "Marítimo", "AEREO": "Aéreo", "TERRESTRE": "Terrestre", "MULTIMODAL": "Multimodal"}


def _usd(valor: float) -> str:
    """US$ 3.100,00 (formato colombiano)."""
    return "US$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _fecha(valor) -> str:
    return dt.date.fromisoformat(str(valor)[:10]).strftime("%d/%m/%Y")


def _sacos(n: int) -> str:
    return f"{n} saco" if n == 1 else f"{n} sacos"


def _evento(exportacion_id: int, tipo: str, descripcion: str, estado: str | None = None):
    """Deja constancia en el historial; se guarda en la misma transacción que el cambio."""
    ExportacionRepositorio().registrar_evento(exportacion_id, tipo, descripcion, g.usuario["id"], estado)


def historial(exportacion_id: int) -> list[dict]:
    _exigir(exportacion_id)
    return ExportacionRepositorio().eventos(exportacion_id)


def _exigir_borrador(exp: dict):
    if exp["estado"] != "BORRADOR":
        raise ReglaNegocio("Solo se pueden modificar los productos de una exportación en borrador")


def listar(estado=None, desde=None, hasta=None, cliente_id=None, q=None):
    return ExportacionRepositorio().listar(estado, desde, hasta, cliente_id, q)


def detalle(exportacion_id: int) -> dict:
    """HU-20: la exportación con sus productos, transporte y transiciones posibles."""
    repo = ExportacionRepositorio()
    exp = _exigir(exportacion_id)
    exp["productos"] = repo.detalles(exportacion_id)
    exp["transporte"] = repo.transporte(exportacion_id)
    exp["estados_siguientes"] = sorted(TRANSICIONES[exp["estado"]])
    return exp


def crear(datos) -> dict:
    repo = ExportacionRepositorio()
    if not ClienteRepositorio().por_id(datos.cliente_id):
        raise ReglaNegocio("El cliente seleccionado no existe")
    if not PaisRepositorio().por_id(datos.pais_destino_id):
        raise ReglaNegocio("El país de destino no existe")
    anio = dt.date.today().year
    d = datos.model_dump()
    d["consecutivo"] = siguiente_consecutivo(repo.ultimo_consecutivo(anio), anio)
    d["creado_por"] = g.usuario["id"]
    nueva = repo.crear(d)
    exp = repo.por_id(nueva)
    _evento(nueva, "CREADA", f"Creó la exportación {exp['consecutivo']} para {exp['cliente']} hacia "
            f"{exp['pais_destino']} ({exp['incoterm']}, salida por {exp['puerto_salida']})", "BORRADOR")
    return detalle(nueva)


def actualizar_costos(exportacion_id: int, datos) -> dict:
    exp = _exigir(exportacion_id)
    if exp["estado"] in ESTADOS_CERRADOS:
        raise ReglaNegocio("No se pueden cambiar los costos de una exportación cerrada")
    ExportacionRepositorio().actualizar(exportacion_id, datos.model_dump())
    _evento(exportacion_id, "COSTOS", f"Actualizó los costos: impuestos {_usd(datos.impuestos)} · flete {_usd(datos.flete)}")
    return detalle(exportacion_id)


def agregar_producto(exportacion_id: int, datos) -> dict:
    """HU-18: agrega un producto validando el stock; si ya estaba, suma la cantidad."""
    repo = ExportacionRepositorio()
    exp = _exigir(exportacion_id)
    _exigir_borrador(exp)
    producto = ProductoRepositorio().por_id(datos.producto_id)
    if not producto or not producto["activo"]:
        raise ReglaNegocio("El producto no existe o fue dado de baja")
    existente = repo.detalle_de_producto(exportacion_id, datos.producto_id)
    cantidad_total = datos.cantidad + (existente["cantidad"] if existente else 0)
    if cantidad_total > producto["stock"]:
        raise ReglaNegocio(
            f"Stock insuficiente de {producto['nombre']}: hay {producto['stock']} y se piden {cantidad_total}"
        )
    if existente:
        repo.actualizar_detalle(existente["id"], cantidad_total, producto["precio"])
        texto = f"Sumó {_sacos(datos.cantidad)} de {producto['nombre']} (ahora {_sacos(cantidad_total)})"
    else:
        repo.agregar_detalle(exportacion_id, datos.producto_id, datos.cantidad, producto["precio"])
        texto = f"Agregó {_sacos(datos.cantidad)} de {producto['nombre']} a {_usd(producto['precio'])} c/u"
    _evento(exportacion_id, "PRODUCTOS", texto)
    return detalle(exportacion_id)


def quitar_producto(exportacion_id: int, detalle_id: int) -> dict:
    repo = ExportacionRepositorio()
    exp = _exigir(exportacion_id)
    _exigir_borrador(exp)
    linea = next((d for d in repo.detalles(exportacion_id) if d["id"] == detalle_id), None)
    if not linea or not repo.quitar_detalle(exportacion_id, detalle_id):
        raise NoEncontrado("El producto no está en esta exportación")
    _evento(exportacion_id, "PRODUCTOS", f"Quitó {linea['producto']} ({_sacos(linea['cantidad'])})")
    return detalle(exportacion_id)


def cambiar_estado(exportacion_id: int, nuevo: str) -> dict:
    """HU-21: aplica la máquina de estados y mueve el inventario cuando corresponde."""
    repo = ExportacionRepositorio()
    exp = detalle(exportacion_id)
    actual = exp["estado"]
    if not transicion_valida(actual, nuevo):
        raise ReglaNegocio(f"No se puede pasar de {actual} a {nuevo}")

    if nuevo == "CONFIRMADA":
        if not exp["productos"]:
            raise ReglaNegocio("Agrega al menos un producto antes de confirmar")
        # Se valida todo antes de mover stock, para no dejar descuentos a medias
        inventario = InventarioRepositorio()
        for linea in exp["productos"]:
            disponible = inventario.por_producto(linea["producto_id"])["cantidad"]
            if linea["cantidad"] > disponible:
                raise ReglaNegocio(
                    f"Stock insuficiente de {linea['producto']}: hay {disponible} y se piden {linea['cantidad']}"
                )
        for linea in exp["productos"]:
            inventario_srv.mover_stock(linea["producto_id"], "SALIDA", linea["cantidad"],
                                       f"Exportación {exp['consecutivo']}")
    elif nuevo == "EN_TRANSITO" and not exp["transporte"]:
        raise ReglaNegocio("Registra el transporte antes de marcar la exportación en tránsito")
    elif nuevo == "CANCELADA" and actual == "CONFIRMADA":
        for linea in exp["productos"]:
            inventario_srv.mover_stock(linea["producto_id"], "ENTRADA", linea["cantidad"],
                                       f"Cancelación de {exp['consecutivo']}")

    repo.actualizar(exportacion_id, {"estado": nuevo})
    sacos = sum(linea["cantidad"] for linea in exp["productos"])
    texto = {
        "CONFIRMADA": f"Confirmó la exportación: se descontaron {_sacos(sacos)} del inventario",
        "EN_TRANSITO": f"Marcó la carga en tránsito desde {exp['puerto_salida']}",
        "ENTREGADA": f"Marcó la exportación como entregada a {exp['cliente']}",
        "CANCELADA": "Canceló la exportación"
                     + (f": se devolvieron {_sacos(sacos)} al inventario" if actual == "CONFIRMADA" else ""),
    }[nuevo]
    _evento(exportacion_id, "ESTADO", texto, nuevo)
    return detalle(exportacion_id)


def registrar_fechas(exportacion_id: int, datos) -> dict:
    """HU-22: fechas de embarque y llegada estimada (ya validadas en orden)."""
    exp = _exigir(exportacion_id)
    if exp["estado"] in ESTADOS_CERRADOS:
        raise ReglaNegocio("No se pueden cambiar las fechas de una exportación cerrada")
    ExportacionRepositorio().actualizar(exportacion_id, {
        "fecha_embarque": datos.fecha_embarque.isoformat(),
        "fecha_estimada_llegada": datos.fecha_estimada_llegada.isoformat(),
    })
    _evento(exportacion_id, "FECHAS", f"Registró las fechas: embarque {_fecha(datos.fecha_embarque)} · "
            f"llegada estimada {_fecha(datos.fecha_estimada_llegada)}")
    return detalle(exportacion_id)


def registrar_transporte(exportacion_id: int, datos) -> dict:
    exp = _exigir(exportacion_id)
    if exp["estado"] in ESTADOS_CERRADOS:
        raise ReglaNegocio("No se puede cambiar el transporte de una exportación cerrada")
    repo = ExportacionRepositorio()
    habia = repo.transporte(exportacion_id)
    repo.guardar_transporte(exportacion_id, datos.model_dump())
    contenedor = f" · contenedor {datos.numero_contenedor}" if datos.numero_contenedor else ""
    _evento(exportacion_id, "TRANSPORTE", f"{'Actualizó' if habia else 'Registró'} el transporte: "
            f"{MODOS.get(datos.tipo, datos.tipo)} · {datos.empresa} · guía {datos.numero_guia}{contenedor}")
    return detalle(exportacion_id)
