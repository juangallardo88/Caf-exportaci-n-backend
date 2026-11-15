"""Errores de la aplicación y manejo centralizado de respuestas de error."""
import logging

from flask import jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class ErrorApp(Exception):
    estado = 400
    codigo = "SOLICITUD_INVALIDA"

    def __init__(self, mensaje: str, detalles=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles


class NoEncontrado(ErrorApp):
    estado, codigo = 404, "NO_ENCONTRADO"


class Conflicto(ErrorApp):
    estado, codigo = 409, "CONFLICTO"


class ReglaNegocio(ErrorApp):
    estado, codigo = 422, "REGLA_DE_NEGOCIO"


class NoAutenticado(ErrorApp):
    estado, codigo = 401, "NO_AUTENTICADO"


class SinPermiso(ErrorApp):
    estado, codigo = 403, "SIN_PERMISO"


def _respuesta(estado, codigo, mensaje, detalles=None):
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje}}
    if detalles:
        cuerpo["error"]["detalles"] = detalles
    return jsonify(cuerpo), estado


def _traducir_validacion(err: ValidationError):
    detalles = []
    for e in err.errors():
        campo = ".".join(str(p) for p in e["loc"]) or "cuerpo"
        mensaje = e["msg"].removeprefix("Value error, ")
        detalles.append({"campo": campo, "mensaje": mensaje})
    return detalles


def registrar(app):
    @app.errorhandler(ErrorApp)
    def error_app(err: ErrorApp):
        return _respuesta(err.estado, err.codigo, err.mensaje, err.detalles)

    @app.errorhandler(ValidationError)
    def error_validacion(err: ValidationError):
        return _respuesta(422, "DATOS_INVALIDOS", "Revisa los datos enviados", _traducir_validacion(err))

    @app.errorhandler(HTTPException)
    def error_http(err: HTTPException):
        mensajes = {404: "Recurso no encontrado", 405: "Método no permitido"}
        return _respuesta(err.code, "HTTP_%s" % err.code, mensajes.get(err.code, err.description))

    @app.errorhandler(Exception)
    def error_inesperado(err: Exception):
        if type(err).__name__ == "IntegrityError":
            return _respuesta(409, "CONFLICTO", "El registro entra en conflicto con datos existentes")
        log.exception("Error no controlado")
        return _respuesta(500, "ERROR_INTERNO", "Ocurrió un error inesperado. Intenta de nuevo.")
