"""Fábrica de la aplicación Flask."""
from __future__ import annotations

import logging

from flask import Flask, request

from . import database, errors, routes
from .config import Config


def _registrar_cors_y_seguridad(app: Flask):
    origenes = app.config["CORS_ORIGINS"]

    def origen_permitido(origen: str | None) -> str | None:
        if not origen:
            return None
        if "*" in origenes:
            return "*"
        return origen if origen in origenes else None

    @app.before_request
    def preflight():
        if request.method == "OPTIONS":
            return app.make_default_options_response()

    @app.after_request
    def cabeceras(respuesta):
        permitido = origen_permitido(request.headers.get("Origin"))
        if permitido:
            respuesta.headers["Access-Control-Allow-Origin"] = permitido
            respuesta.headers["Vary"] = "Origin"
            respuesta.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            respuesta.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        return respuesta


def create_app(configuracion: dict | None = None) -> Flask:
    app = Flask(__name__)
    Config.validar()
    app.config.from_object(Config)
    app.config["JSON_SORT_KEYS"] = False
    if configuracion:
        app.config.update(configuracion)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    database.registrar(app)
    errors.registrar(app)
    _registrar_cors_y_seguridad(app)
    routes.registrar(app)

    from .cli import registrar as registrar_cli

    registrar_cli(app)
    return app
