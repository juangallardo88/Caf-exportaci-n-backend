"""Fixtures compartidas: cada prueba usa una base de datos limpia y aislada de producción.

Por defecto es un archivo SQLite temporal. Si se define TEST_DATABASE_URL con una base
PostgreSQL de pruebas (como en GitHub Actions), las tablas se recrean allí antes de cada prueba.
"""
import os
from pathlib import Path

import pytest

from app import create_app
from app.database import Conexion, crear_esquema_sqlite
from werkzeug.security import generate_password_hash

ESQUEMA_POSTGRES = Path(__file__).resolve().parent.parent / "db" / "schema_postgres.sql"

HASH_RAPIDO = "pbkdf2:sha256:1000"  # menos iteraciones solo para que las pruebas sean rápidas

USUARIOS = {
    "ADMINISTRADOR": ("admin@prueba.co", "Admin123*"),
    "OPERADOR": ("operador@prueba.co", "Operador123*"),
    "AUDITOR": ("auditor@prueba.co", "Auditor123*"),
}


@pytest.fixture
def app(tmp_path):
    url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'pruebas.db'}"
    if url.startswith("sqlite"):
        crear_esquema_sqlite(url)
    else:
        con = Conexion(url)
        con.script(ESQUEMA_POSTGRES.read_text(encoding="utf-8"))
        con.cerrar()
    db = Conexion(url)
    for rol, (correo, clave) in USUARIOS.items():
        db.insertar(
            "INSERT INTO usuario (nombre, correo, contrasena_hash, rol) VALUES (?, ?, ?, ?)",
            (f"Usuario {rol.title()}", correo, generate_password_hash(clave, method=HASH_RAPIDO), rol),
        )
    db.confirmar()
    db.cerrar()
    aplicacion = create_app({
        "TESTING": True,
        "DATABASE_URL": url,
        "SECRET_KEY": "clave-de-pruebas-con-longitud-suficiente-123",
        "HASH_METHOD": HASH_RAPIDO,
        "CORS_ORIGINS": ["https://cafe-exportacion.vercel.app"],
    })
    yield aplicacion


@pytest.fixture
def client(app):
    return app.test_client()


def _token(client, rol):
    correo, clave = USUARIOS[rol]
    respuesta = client.post("/api/auth/login", json={"correo": correo, "contrasena": clave})
    assert respuesta.status_code == 200, respuesta.json
    return respuesta.json["token"]


@pytest.fixture
def admin(client):
    return {"Authorization": f"Bearer {_token(client, 'ADMINISTRADOR')}"}


@pytest.fixture
def operador(client):
    return {"Authorization": f"Bearer {_token(client, 'OPERADOR')}"}


@pytest.fixture
def auditor(client):
    return {"Authorization": f"Bearer {_token(client, 'AUDITOR')}"}


# --- Datos de apoyo -----------------------------------------------------------------

PAIS_CO = {"nombre": "Colombia", "codigo_iso2": "CO", "codigo_iso3": "COL", "region": "América del Sur"}
PAIS_DE = {"nombre": "Alemania", "codigo_iso2": "DE", "codigo_iso3": "DEU", "region": "Unión Europea"}


def proveedor_valido(pais_id, **cambios):
    datos = {
        "nit": "891100345-1", "razon_social": "Cooperativa del Huila", "pais_id": pais_id,
        "direccion": "Cra 5 # 10-20, Neiva", "telefono": "+57 608 871 2233",
        "correo": "compras@coophuila.co", "condiciones_comerciales": "Pago a 30 días",
    }
    datos.update(cambios)
    return datos


def cliente_valido(pais_id, **cambios):
    datos = {
        "tax_id": "DE-HRB-112233", "razon_social": "Hamburg Kaffee Import GmbH", "pais_id": pais_id,
        "ciudad": "Hamburgo", "direccion_entrega": "Speicherstadt 12", "contacto_compras": "Anna Müller",
        "correo": "einkauf@hamburgkaffee.de",
    }
    datos.update(cambios)
    return datos


def producto_valido(**cambios):
    datos = {
        "sku": "CAF-SUP-70", "nombre": "Café Excelso Supremo", "descripcion": "Saco de 70 kg",
        "categoria": "CAFE", "precio": 280, "peso_kg": 70, "volumen_m3": 0.11,
        "stock_inicial": 100, "stock_minimo": 20, "ubicacion": "Bodega Buenaventura",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def base(client, admin):
    """Países, un cliente y dos productos creados por la API."""
    co = client.post("/api/paises", json=PAIS_CO, headers=admin).json
    de = client.post("/api/paises", json=PAIS_DE, headers=admin).json
    cliente = client.post("/api/clientes", json=cliente_valido(de["id"]), headers=admin).json
    cafe = client.post("/api/productos", json=producto_valido(), headers=admin).json
    cacao = client.post("/api/productos", json=producto_valido(
        sku="CAC-FIN-60", nombre="Cacao Fino de Aroma", categoria="CACAO", precio=250, peso_kg=60,
        stock_inicial=30, stock_minimo=40), headers=admin).json
    return {"co": co, "de": de, "cliente": cliente, "cafe": cafe, "cacao": cacao}


@pytest.fixture
def exportacion(client, admin, base):
    """Una exportación en borrador hacia Alemania."""
    return client.post("/api/exportaciones", json={
        "cliente_id": base["cliente"]["id"], "pais_destino_id": base["de"]["id"],
        "puerto_salida": "Buenaventura", "incoterm": "FOB",
    }, headers=admin).json
