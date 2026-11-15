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
    return detalle(repo.crear(d))


def actualizar_costos(exportacion_id: int, datos) -> dict:
    exp = _exigir(exportacion_id)
    if exp["estado"] in ESTADOS_CERRADOS:
        raise ReglaNegocio("No se pueden cambiar los costos de una exportación cerrada")
    ExportacionRepositorio().actualizar(exportacion_id, datos.model_dump())
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
    else:
        repo.agregar_detalle(exportacion_id, datos.producto_id, datos.cantidad, producto["precio"])
    return detalle(exportacion_id)


def quitar_producto(exportacion_id: int, detalle_id: int) -> dict:
    exp = _exigir(exportacion_id)
    _exigir_borrador(exp)
    if not ExportacionRepositorio().quitar_detalle(exportacion_id, detalle_id):
        raise NoEncontrado("El producto no está en esta exportación")
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
    return detalle(exportacion_id)


def registrar_transporte(exportacion_id: int, datos) -> dict:
    exp = _exigir(exportacion_id)
    if exp["estado"] in ESTADOS_CERRADOS:
        raise ReglaNegocio("No se puede cambiar el transporte de una exportación cerrada")
    ExportacionRepositorio().guardar_transporte(exportacion_id, datos.model_dump())
    return detalle(exportacion_id)
