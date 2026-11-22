from flask import Blueprint, jsonify, request

from ..schemas import leer
from ..schemas.entradas import InventarioCambio, Movimiento, ProductoCambio, ProductoNuevo
from ..security import ESCRITURA, requiere_roles, requiere_sesion
from ..services import inventario as srv
from . import arg_entero, arg_texto

bp = Blueprint("inventario", __name__)


# --- Productos (HU-04 a HU-08) ---

@bp.get("/productos")
@requiere_sesion
def listar_productos():
    return jsonify(srv.listar_productos(arg_texto("q"), arg_texto("categoria")))


@bp.get("/productos/disponibilidad")
@requiere_sesion
def disponibilidad():
    return jsonify(srv.disponibilidad(arg_texto("q")))


@bp.get("/productos/<int:producto_id>")
@requiere_sesion
def obtener_producto(producto_id):
    return jsonify(srv.obtener_producto(producto_id))


@bp.post("/productos")
@requiere_roles(*ESCRITURA)
def crear_producto():
    return jsonify(srv.crear_producto(leer(ProductoNuevo))), 201


@bp.put("/productos/<int:producto_id>")
@requiere_roles(*ESCRITURA)
def actualizar_producto(producto_id):
    return jsonify(srv.actualizar_producto(producto_id, leer(ProductoCambio)))


@bp.delete("/productos/<int:producto_id>")
@requiere_roles(*ESCRITURA)
def eliminar_producto(producto_id):
    srv.eliminar_producto(producto_id)
    return "", 204


# --- Inventario (HU-24 a HU-26) ---

@bp.get("/inventario")
@requiere_sesion
def listar_inventario():
    solo_bajo = request.args.get("bajo_stock", "").lower() in ("1", "true", "si")
    return jsonify(srv.listar_inventario(arg_texto("q"), solo_bajo))


@bp.get("/inventario/bajo-stock")
@requiere_sesion
def bajo_stock():
    return jsonify(srv.listar_inventario(solo_bajo_stock=True))


@bp.get("/inventario/proyeccion")
@requiere_sesion
def proyeccion():
    dias = min(max(arg_entero("dias") or 90, 30), 365)
    return jsonify(srv.proyeccion(dias))


@bp.get("/inventario/movimientos")
@requiere_sesion
def movimientos():
    limite = min(arg_entero("limite") or 100, 500)
    return jsonify(srv.listar_movimientos(arg_entero("producto_id"), limite))


@bp.post("/inventario/movimientos")
@requiere_roles(*ESCRITURA)
def registrar_movimiento():
    return jsonify(srv.registrar_movimiento(leer(Movimiento))), 201


@bp.get("/inventario/<int:producto_id>")
@requiere_sesion
def obtener_inventario(producto_id):
    return jsonify(srv.obtener_inventario(producto_id))


@bp.put("/inventario/<int:producto_id>")
@requiere_roles(*ESCRITURA)
def actualizar_inventario(producto_id):
    return jsonify(srv.actualizar_inventario(producto_id, leer(InventarioCambio)))
