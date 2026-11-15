import datetime as dt

from flask import Blueprint, Response, jsonify

from ..security import ADMINISTRADOR, AUDITOR, requiere_roles, requiere_sesion
from ..services import analitica as srv
from . import arg_fecha, arg_texto

bp = Blueprint("analitica", __name__)


@bp.get("/dashboard")
@requiere_sesion
def dashboard():
    return jsonify(srv.dashboard())


@bp.get("/estadisticas")
@requiere_sesion
def estadisticas():
    return jsonify(srv.estadisticas())


@bp.get("/busqueda")
@requiere_sesion
def busqueda():
    return jsonify(srv.buscar(arg_texto("q")))


def _descarga(contenido: str, nombre: str) -> Response:
    fecha = dt.date.today().isoformat()
    return Response(
        contenido,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}-{fecha}.csv"'},
    )


@bp.get("/reportes/exportaciones")
@requiere_roles(ADMINISTRADOR, AUDITOR)
def reporte_exportaciones():
    contenido = srv.reporte_exportaciones(arg_texto("estado"), arg_fecha("desde"), arg_fecha("hasta"))
    return _descarga(contenido, "reporte-exportaciones")


@bp.get("/reportes/inventario")
@requiere_roles(ADMINISTRADOR, AUDITOR)
def reporte_inventario():
    return _descarga(srv.reporte_inventario(), "reporte-inventario")
