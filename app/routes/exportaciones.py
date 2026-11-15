from flask import Blueprint, jsonify

from ..schemas import leer
from ..schemas.entradas import CambioEstado, ExportacionCostos, ExportacionNueva, Fechas, LineaProducto, Transporte
from ..security import ESCRITURA, requiere_roles, requiere_sesion
from ..services import exportaciones as srv
from . import arg_entero, arg_fecha, arg_texto

bp = Blueprint("exportaciones", __name__)


@bp.get("/exportaciones")
@requiere_sesion
def listar():
    return jsonify(srv.listar(arg_texto("estado"), arg_fecha("desde"), arg_fecha("hasta"),
                              arg_entero("cliente_id"), arg_texto("q")))


@bp.post("/exportaciones")
@requiere_roles(*ESCRITURA)
def crear():
    return jsonify(srv.crear(leer(ExportacionNueva))), 201


@bp.get("/exportaciones/<int:exportacion_id>")
@requiere_sesion
def detalle(exportacion_id):
    return jsonify(srv.detalle(exportacion_id))


@bp.put("/exportaciones/<int:exportacion_id>/costos")
@requiere_roles(*ESCRITURA)
def costos(exportacion_id):
    return jsonify(srv.actualizar_costos(exportacion_id, leer(ExportacionCostos)))


@bp.post("/exportaciones/<int:exportacion_id>/productos")
@requiere_roles(*ESCRITURA)
def agregar_producto(exportacion_id):
    return jsonify(srv.agregar_producto(exportacion_id, leer(LineaProducto))), 201


@bp.delete("/exportaciones/<int:exportacion_id>/productos/<int:detalle_id>")
@requiere_roles(*ESCRITURA)
def quitar_producto(exportacion_id, detalle_id):
    return jsonify(srv.quitar_producto(exportacion_id, detalle_id))


@bp.patch("/exportaciones/<int:exportacion_id>/estado")
@requiere_roles(*ESCRITURA)
def cambiar_estado(exportacion_id):
    return jsonify(srv.cambiar_estado(exportacion_id, leer(CambioEstado).estado))


@bp.put("/exportaciones/<int:exportacion_id>/fechas")
@requiere_roles(*ESCRITURA)
def fechas(exportacion_id):
    return jsonify(srv.registrar_fechas(exportacion_id, leer(Fechas)))


@bp.put("/exportaciones/<int:exportacion_id>/transporte")
@requiere_roles(*ESCRITURA)
def transporte(exportacion_id):
    return jsonify(srv.registrar_transporte(exportacion_id, leer(Transporte)))
