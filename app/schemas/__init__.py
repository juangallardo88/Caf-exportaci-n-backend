"""DTO de entrada validados con Pydantic."""
from __future__ import annotations

import re
from typing import Annotated

from flask import request
from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from ..errors import ErrorApp

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PATRON_TELEFONO = re.compile(r"^\+?[0-9][0-9 ()-]{6,19}$")


def _correo(valor: str) -> str:
    if not PATRON_CORREO.match(valor):
        raise ValueError("Correo electrónico inválido")
    return valor.lower()


def _telefono(valor: str) -> str:
    if not PATRON_TELEFONO.match(valor):
        raise ValueError("Teléfono inválido: usa solo números, espacios, +, - y paréntesis (7 a 20)")
    return valor


Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Correo = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160), AfterValidator(_correo)]
Telefono = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_telefono)]


class Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def leer(esquema: type[Esquema]):
    """Valida el JSON de la petición contra el esquema dado."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApp("El cuerpo de la petición debe ser un objeto JSON")
    return esquema.model_validate(datos)
