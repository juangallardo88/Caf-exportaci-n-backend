"""Pruebas unitarias de contraseñas y tokens JWT (HU-01, HU-02)."""
import datetime as dt

import jwt
import pytest

from app.errors import NoAutenticado
from app.security import cifrar_contrasena, decodificar_token, emitir_token, verificar_contrasena

USUARIO = {"id": 7, "nombre": "Ana", "rol": "OPERADOR"}


def test_la_contrasena_no_se_guarda_en_texto_plano(app):
    with app.app_context():
        hash_ = cifrar_contrasena("Secreta123*")
    assert "Secreta123*" not in hash_
    assert verificar_contrasena(hash_, "Secreta123*")
    assert not verificar_contrasena(hash_, "otra-clave")


def test_token_contiene_usuario_y_rol(app):
    with app.app_context():
        token, _ = emitir_token(USUARIO)
        carga = decodificar_token(token)
    assert carga["sub"] == "7" and carga["rol"] == "OPERADOR" and carga["jti"]


def test_token_manipulado_se_rechaza(app):
    with app.app_context():
        token, _ = emitir_token(USUARIO)
        falso = jwt.encode({**jwt.decode(token, options={"verify_signature": False}), "rol": "ADMINISTRADOR"},
                           "otra-clave-secreta-de-un-atacante-123", algorithm="HS256")
        with pytest.raises(NoAutenticado, match="inválido"):
            decodificar_token(falso)


def test_token_vencido_se_rechaza(app):
    with app.app_context():
        vencido = jwt.encode(
            {"sub": "7", "rol": "OPERADOR", "jti": "x", "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)},
            app.config["SECRET_KEY"], algorithm="HS256")
        with pytest.raises(NoAutenticado, match="expiró"):
            decodificar_token(vencido)
