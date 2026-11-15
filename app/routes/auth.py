from flask import Blueprint, g, jsonify

from ..schemas import leer
from ..schemas.entradas import Login, UsuarioCambio, UsuarioNuevo
from ..security import ADMINISTRADOR, requiere_roles, requiere_sesion
from ..services import auth as srv

bp = Blueprint("auth", __name__)


@bp.get("/salud")
def salud():
    return jsonify({"estado": "ok"})


@bp.post("/auth/login")
def login():
    datos = leer(Login)
    return jsonify(srv.iniciar_sesion(datos.correo, datos.contrasena))


@bp.post("/auth/logout")
@requiere_sesion
def logout():
    srv.cerrar_sesion()
    return jsonify({"mensaje": "Sesión cerrada"})


@bp.get("/auth/yo")
@requiere_sesion
def yo():
    return jsonify(g.usuario)


@bp.get("/usuarios")
@requiere_roles(ADMINISTRADOR)
def listar_usuarios():
    return jsonify(srv.listar_usuarios())


@bp.post("/usuarios")
@requiere_roles(ADMINISTRADOR)
def crear_usuario():
    return jsonify(srv.crear_usuario(leer(UsuarioNuevo))), 201


@bp.patch("/usuarios/<int:usuario_id>")
@requiere_roles(ADMINISTRADOR)
def cambiar_usuario(usuario_id):
    return jsonify(srv.cambiar_usuario(usuario_id, leer(UsuarioCambio)))
