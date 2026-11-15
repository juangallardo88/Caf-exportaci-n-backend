"""Autenticación y gestión de usuarios (HU-01, HU-02, HU-03)."""
from __future__ import annotations

import datetime as dt

from flask import g

from ..errors import Conflicto, NoAutenticado, NoEncontrado, ReglaNegocio
from ..repositories.usuarios import UsuarioRepositorio
from ..security import ADMINISTRADOR, cifrar_contrasena, emitir_token, verificar_contrasena


def iniciar_sesion(correo: str, contrasena: str) -> dict:
    repo = UsuarioRepositorio()
    usuario = repo.por_correo(correo)
    # Mismo mensaje para correo o contraseña incorrectos: no revela qué correos existen
    if not usuario or not verificar_contrasena(usuario["contrasena_hash"], contrasena):
        raise NoAutenticado("Correo o contraseña incorrectos")
    if not usuario["activo"]:
        raise NoAutenticado("El usuario está desactivado")
    token, expira = emitir_token(usuario)
    publico = {k: usuario[k] for k in ("id", "nombre", "correo", "rol")}
    return {"token": token, "expira_en": expira.isoformat(), "usuario": publico}


def cerrar_sesion():
    expira = dt.datetime.fromtimestamp(g.token["exp"], tz=dt.timezone.utc).replace(tzinfo=None)
    UsuarioRepositorio().revocar_token(g.token["jti"], expira.isoformat(sep=" ", timespec="seconds"))


def listar_usuarios():
    return UsuarioRepositorio().listar()


def crear_usuario(datos) -> dict:
    repo = UsuarioRepositorio()
    if repo.por_correo(datos.correo):
        raise Conflicto("Ya existe un usuario con ese correo")
    nuevo_id = repo.crear(datos.nombre, datos.correo, cifrar_contrasena(datos.contrasena), datos.rol)
    return repo.por_id(nuevo_id)


def cambiar_usuario(usuario_id: int, datos) -> dict:
    repo = UsuarioRepositorio()
    actual = repo.por_id(usuario_id)
    if not actual:
        raise NoEncontrado("Usuario no encontrado")
    cambios = datos.model_dump(exclude_none=True)
    deja_de_ser_admin = actual["rol"] == ADMINISTRADOR and actual["activo"] and (
        cambios.get("rol", ADMINISTRADOR) != ADMINISTRADOR or cambios.get("activo") is False
    )
    if deja_de_ser_admin and repo.contar_administradores_activos() <= 1:
        raise ReglaNegocio("Debe quedar al menos un administrador activo")
    repo.actualizar(usuario_id, cambios)
    return repo.por_id(usuario_id)
