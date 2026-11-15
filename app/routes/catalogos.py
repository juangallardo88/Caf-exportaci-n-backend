from flask import Blueprint, jsonify

from ..schemas import leer
from ..schemas.entradas import Cliente, Pais, Proveedor
from ..security import ADMINISTRADOR, ESCRITURA, requiere_roles, requiere_sesion
from ..services import catalogos as srv
from . import arg_entero, arg_texto

bp = Blueprint("catalogos", __name__)


# --- Países (HU-16) ---

@bp.get("/paises")
@requiere_sesion
def listar_paises():
    return jsonify(srv.listar_paises())


@bp.post("/paises")
@requiere_roles(ADMINISTRADOR)
def crear_pais():
    return jsonify(srv.crear_pais(leer(Pais))), 201


@bp.put("/paises/<int:pais_id>")
@requiere_roles(ADMINISTRADOR)
def actualizar_pais(pais_id):
    return jsonify(srv.actualizar_pais(pais_id, leer(Pais)))


# --- Proveedores (HU-09 a HU-12) ---

@bp.get("/proveedores")
@requiere_sesion
def listar_proveedores():
    return jsonify(srv.listar_proveedores(arg_texto("q"), arg_entero("pais_id")))


@bp.get("/proveedores/<int:proveedor_id>")
@requiere_sesion
def obtener_proveedor(proveedor_id):
    return jsonify(srv.obtener_proveedor(proveedor_id))


@bp.post("/proveedores")
@requiere_roles(*ESCRITURA)
def crear_proveedor():
    return jsonify(srv.crear_proveedor(leer(Proveedor))), 201


@bp.put("/proveedores/<int:proveedor_id>")
@requiere_roles(*ESCRITURA)
def actualizar_proveedor(proveedor_id):
    return jsonify(srv.actualizar_proveedor(proveedor_id, leer(Proveedor)))


@bp.delete("/proveedores/<int:proveedor_id>")
@requiere_roles(*ESCRITURA)
def eliminar_proveedor(proveedor_id):
    srv.eliminar_proveedor(proveedor_id)
    return "", 204


# --- Clientes (HU-13 a HU-15) ---

@bp.get("/clientes")
@requiere_sesion
def listar_clientes():
    return jsonify(srv.listar_clientes(arg_texto("q"), arg_entero("pais_id")))


@bp.get("/clientes/<int:cliente_id>")
@requiere_sesion
def obtener_cliente(cliente_id):
    return jsonify(srv.obtener_cliente(cliente_id))


@bp.post("/clientes")
@requiere_roles(*ESCRITURA)
def crear_cliente():
    return jsonify(srv.crear_cliente(leer(Cliente))), 201


@bp.put("/clientes/<int:cliente_id>")
@requiere_roles(*ESCRITURA)
def actualizar_cliente(cliente_id):
    return jsonify(srv.actualizar_cliente(cliente_id, leer(Cliente)))
