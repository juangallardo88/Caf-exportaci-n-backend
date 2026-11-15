"""Integración: autenticación, cierre de sesión y control de acceso por rol (HU-01 a HU-03)."""
from tests.conftest import PAIS_CO


def test_login_correcto_devuelve_token_y_usuario(client):
    r = client.post("/api/auth/login", json={"correo": "admin@prueba.co", "contrasena": "Admin123*"})
    assert r.status_code == 200
    assert r.json["token"] and r.json["usuario"]["rol"] == "ADMINISTRADOR"
    assert "contrasena_hash" not in r.json["usuario"]


def test_login_con_contrasena_incorrecta(client):
    r = client.post("/api/auth/login", json={"correo": "admin@prueba.co", "contrasena": "mala"})
    assert r.status_code == 401
    assert r.json["error"]["mensaje"] == "Correo o contraseña incorrectos"


def test_login_con_correo_inexistente_da_el_mismo_mensaje(client):
    r = client.post("/api/auth/login", json={"correo": "nadie@prueba.co", "contrasena": "Admin123*"})
    assert r.status_code == 401
    assert r.json["error"]["mensaje"] == "Correo o contraseña incorrectos"


def test_endpoint_protegido_sin_token(client):
    assert client.get("/api/productos").status_code == 401


def test_logout_invalida_el_token(client, operador):  # HU-02
    assert client.get("/api/auth/yo", headers=operador).status_code == 200
    assert client.post("/api/auth/logout", headers=operador).status_code == 200
    r = client.get("/api/auth/yo", headers=operador)
    assert r.status_code == 401 and "cerrada" in r.json["error"]["mensaje"]


def test_auditor_solo_consulta(client, auditor):  # HU-03
    assert client.get("/api/paises", headers=auditor).status_code == 200
    assert client.post("/api/paises", json=PAIS_CO, headers=auditor).status_code == 403


def test_operador_no_gestiona_usuarios(client, operador):
    assert client.get("/api/usuarios", headers=operador).status_code == 403


def test_admin_crea_usuario_y_este_puede_iniciar_sesion(client, admin):
    r = client.post("/api/usuarios", json={"nombre": "Ana Ruiz", "correo": "ana@prueba.co",
                                           "contrasena": "Segura123*", "rol": "OPERADOR"}, headers=admin)
    assert r.status_code == 201
    login = client.post("/api/auth/login", json={"correo": "ana@prueba.co", "contrasena": "Segura123*"})
    assert login.status_code == 200


def test_usuario_desactivado_no_puede_entrar(client, admin):
    nuevo = client.post("/api/usuarios", json={"nombre": "Luis", "correo": "luis@prueba.co",
                                               "contrasena": "Segura123*", "rol": "AUDITOR"}, headers=admin).json
    client.patch(f"/api/usuarios/{nuevo['id']}", json={"activo": False}, headers=admin)
    r = client.post("/api/auth/login", json={"correo": "luis@prueba.co", "contrasena": "Segura123*"})
    assert r.status_code == 401


def test_no_se_puede_quitar_el_ultimo_administrador(client, admin):
    yo = client.get("/api/auth/yo", headers=admin).json
    r = client.patch(f"/api/usuarios/{yo['id']}", json={"rol": "OPERADOR"}, headers=admin)
    assert r.status_code == 422
