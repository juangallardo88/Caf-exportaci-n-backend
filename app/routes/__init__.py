"""Rutas HTTP (controladores). Solo traducen HTTP ↔ servicios; la lógica vive en los servicios."""
from __future__ import annotations

import datetime as dt

from flask import request

from ..errors import ErrorApp


def arg_entero(nombre: str) -> int | None:
    valor = request.args.get(nombre)
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except ValueError:
        raise ErrorApp(f"El parámetro '{nombre}' debe ser un número entero")


def arg_fecha(nombre: str) -> str | None:
    valor = request.args.get(nombre)
    if not valor:
        return None
    try:
        return dt.date.fromisoformat(valor).isoformat()
    except ValueError:
        raise ErrorApp(f"El parámetro '{nombre}' debe ser una fecha AAAA-MM-DD")


def arg_texto(nombre: str) -> str | None:
    valor = (request.args.get(nombre) or "").strip()
    return valor or None


def registrar(app):
    from . import auth, catalogos, exportaciones, inventario, analitica

    for modulo in (auth, catalogos, exportaciones, inventario, analitica):
        app.register_blueprint(modulo.bp, url_prefix="/api")
