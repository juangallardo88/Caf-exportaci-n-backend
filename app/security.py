"""Contraseñas, tokens JWT y control de acceso por rol (HU-01, HU-02, HU-03)."""
from __future__ import annotations

import datetime as dt
import uuid
from functools import wraps

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .database import obtener_db
from .errors import NoAutenticado, SinPermiso

ADMINISTRADOR, OPERADOR, AUDITOR = "ADMINISTRADOR", "OPERADOR", "AUDITOR"
ROLES = (ADMINISTRADOR, OPERADOR, AUDITOR)
ESCRITURA = (ADMINISTRADOR, OPERADOR)


def cifrar_contrasena(contrasena: str) -> str:
    return generate_password_hash(contrasena, method=current_app.config["HASH_METHOD"])


def verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    return check_password_hash(hash_guardado, contrasena)


def emitir_token(usuario: dict) -> tuple[str, dt.datetime]:
    expira = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=current_app.config["JWT_HORAS"])
    carga = {
        "sub": str(usuario["id"]),
        "rol": usuario["rol"],
        "nombre": usuario["nombre"],
        "jti": uuid.uuid4().hex,
        "exp": expira,
    }
    return jwt.encode(carga, current_app.config["SECRET_KEY"], algorithm="HS256"), expira


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise NoAutenticado("La sesión expiró. Inicia sesión de nuevo.")
    except jwt.InvalidTokenError:
        raise NoAutenticado("Token inválido")


def _token_de_la_peticion() -> str:
    cabecera = request.headers.get("Authorization", "")
    tipo, _, token = cabecera.partition(" ")
    if tipo.lower() != "bearer" or not token:
        raise NoAutenticado("Debes iniciar sesión")
    return token


def _autenticar():
    carga = decodificar_token(_token_de_la_peticion())
    db = obtener_db()
    if db.uno("SELECT jti FROM token_revocado WHERE jti = ?", (carga["jti"],)):
        raise NoAutenticado("La sesión fue cerrada. Inicia sesión de nuevo.")
    usuario = db.uno(
        "SELECT id, nombre, correo, rol, activo FROM usuario WHERE id = ?", (int(carga["sub"]),)
    )
    if not usuario or not usuario["activo"]:
        raise NoAutenticado("Usuario inactivo o inexistente")
    g.usuario = usuario
    g.token = carga


def requiere_roles(*roles: str):
    """Exige un token válido y, si se indican, uno de los roles dados."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            _autenticar()
            if roles and g.usuario["rol"] not in roles:
                raise SinPermiso("Tu rol no tiene permiso para esta acción")
            return vista(*args, **kwargs)

        return envoltura

    return decorador


requiere_sesion = requiere_roles()
