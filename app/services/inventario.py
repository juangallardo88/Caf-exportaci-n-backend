"""Productos (HU-04 a HU-08) e inventario (HU-24 a HU-26)."""
from __future__ import annotations

import datetime as dt

from flask import g

from ..domain.reglas import estado_stock, nuevo_stock, proyectar_agotamiento
from ..errors import Conflicto, NoEncontrado, ReglaNegocio
from ..repositories.productos import InventarioRepositorio, ProductoRepositorio


def _con_estado(fila: dict, cantidad="stock", minimo="stock_minimo") -> dict:
    fila["estado_stock"] = estado_stock(fila[cantidad], fila[minimo])
    return fila


# --- Productos ---

def listar_productos(q=None, categoria=None):
    return [_con_estado(p) for p in ProductoRepositorio().listar(q, categoria)]


def obtener_producto(producto_id: int) -> dict:
    producto = ProductoRepositorio().por_id(producto_id)
    if not producto or not producto["activo"]:
        raise NoEncontrado("Producto no encontrado")
    return _con_estado(producto)


def crear_producto(datos) -> dict:
    productos, inventario = ProductoRepositorio(), InventarioRepositorio()
    d = datos.model_dump()
    if productos.por_sku(d["sku"]):
        raise Conflicto("Ya existe un producto con ese SKU")
    producto_id = productos.crear(d)
    inventario.crear(producto_id, d["stock_inicial"], d["ubicacion"], d["stock_minimo"])
    if d["stock_inicial"] > 0:
        inventario.registrar_movimiento(producto_id, "ENTRADA", d["stock_inicial"], "Stock inicial",
                                        g.usuario["id"])
    return obtener_producto(producto_id)


def actualizar_producto(producto_id: int, datos) -> dict:
    repo, d = ProductoRepositorio(), datos.model_dump()
    obtener_producto(producto_id)
    if repo.por_sku(d["sku"], excluir_id=producto_id):
        raise Conflicto("Ya existe otro producto con ese SKU")
    repo.actualizar(producto_id, d)
    return obtener_producto(producto_id)


def eliminar_producto(producto_id: int):
    """Baja lógica: el producto conserva su historial en exportaciones y movimientos."""
    obtener_producto(producto_id)
    ProductoRepositorio().actualizar(producto_id, {"activo": False})


def disponibilidad(q=None):
    """HU-08: productos con su stock y estado (disponible, bajo o agotado)."""
    return [_con_estado(f, "cantidad") for f in InventarioRepositorio().listar(q)]


# --- Inventario ---

def listar_inventario(q=None, solo_bajo_stock=False):
    return [_con_estado(f, "cantidad") for f in InventarioRepositorio().listar(q, solo_bajo_stock)]


def obtener_inventario(producto_id: int) -> dict:
    fila = InventarioRepositorio().por_producto(producto_id)
    if not fila or not fila["activo"]:
        raise NoEncontrado("Producto no encontrado")
    return _con_estado(fila, "cantidad")


def actualizar_inventario(producto_id: int, datos) -> dict:
    obtener_inventario(producto_id)
    InventarioRepositorio().actualizar_datos(producto_id, datos.ubicacion, datos.stock_minimo)
    return obtener_inventario(producto_id)


def mover_stock(producto_id: int, tipo: str, cantidad: int, motivo: str) -> dict:
    """Aplica un movimiento validado y lo deja registrado para auditoría (HU-25)."""
    repo = InventarioRepositorio()
    actual = obtener_inventario(producto_id)
    try:
        resultado = nuevo_stock(actual["cantidad"], tipo, cantidad)
    except ValueError as err:
        raise ReglaNegocio(f"{actual['nombre']}: {err}")
    repo.fijar_cantidad(producto_id, resultado)
    repo.registrar_movimiento(producto_id, tipo, cantidad, motivo, g.usuario["id"])
    return obtener_inventario(producto_id)


def registrar_movimiento(datos) -> dict:
    return mover_stock(datos.producto_id, datos.tipo, datos.cantidad, datos.motivo)


def listar_movimientos(producto_id=None, limite=100):
    return InventarioRepositorio().movimientos(producto_id, limite)


_ORDEN_NIVEL = {"AGOTADO": 0, "ALTA": 1, "MEDIA": 2, "BAJA": 3, "SIN_CONSUMO": 4}


def proyeccion(dias: int = 90, hoy: dt.date | None = None) -> list[dict]:
    """Proyección de agotamiento por producto, de lo más urgente a lo menos urgente."""
    hoy = hoy or dt.date.today()
    repo = InventarioRepositorio()
    desde = (hoy - dt.timedelta(days=dias)).isoformat()
    por_producto: dict[int, list] = {}
    for m in repo.movimientos_desde(desde):
        fecha = dt.date.fromisoformat(str(m["fecha"])[:10])
        por_producto.setdefault(m["producto_id"], []).append((fecha, m["tipo"], m["cantidad"]))
    resultado = []
    for fila in repo.listar():
        p = proyectar_agotamiento(fila["cantidad"], fila["stock_minimo"], por_producto.get(fila["producto_id"], []),
                                  hoy, dias)
        resultado.append({"producto_id": fila["producto_id"], "sku": fila["sku"], "nombre": fila["nombre"],
                          "stock": fila["cantidad"], "stock_minimo": fila["stock_minimo"], **p})
    resultado.sort(key=lambda r: (_ORDEN_NIVEL[r["nivel"]], r["dias_para_minimo"] if r["dias_para_minimo"] is not None
                                  else 10**9, r["nombre"]))
    return resultado
