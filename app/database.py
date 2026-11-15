"""Acceso a datos con soporte para PostgreSQL (producción, Neon) y SQLite (desarrollo y pruebas).

Las consultas se escriben con marcadores ``?``; para PostgreSQL se traducen a ``%s``.
Las filas se devuelven como diccionarios con tipos JSON: Decimal → float, fechas → texto ISO.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from decimal import Decimal
from pathlib import Path

from flask import current_app, g

COLUMNAS_BOOLEANAS = {"activo"}


def _normalizar(fila) -> dict:
    datos = {}
    for clave, valor in dict(fila).items():
        if isinstance(valor, Decimal):
            valor = float(valor)
        elif isinstance(valor, dt.datetime):
            valor = valor.isoformat(sep=" ", timespec="seconds")
        elif isinstance(valor, dt.date):
            valor = valor.isoformat()
        elif clave in COLUMNAS_BOOLEANAS and isinstance(valor, int):
            valor = bool(valor)
        datos[clave] = valor
    return datos


class Conexion:
    """Envuelve una conexión DB-API con una interfaz única para ambos motores."""

    def __init__(self, url: str):
        self.url = url
        if url.startswith("sqlite:///"):
            self.motor = "sqlite"
            ruta = url.removeprefix("sqlite:///")
            if ruta != ":memory:":
                Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            self._con = sqlite3.connect(ruta)
            self._con.row_factory = sqlite3.Row
            self._con.execute("PRAGMA foreign_keys = ON")
            self.ErrorIntegridad = sqlite3.IntegrityError
        elif url.startswith(("postgres://", "postgresql://")):
            import psycopg2
            import psycopg2.extras

            self.motor = "postgres"
            self._con = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
            self.ErrorIntegridad = psycopg2.IntegrityError
        else:
            raise RuntimeError("DATABASE_URL no soportada: use sqlite:/// o postgresql://")

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.motor == "postgres" else sql

    def _ejecutar(self, sql: str, params=()):
        cur = self._con.cursor()
        if self.motor == "postgres" and not params:
            cur.execute(sql)  # sin parámetros psycopg2 no interpreta los '%' del texto
        else:
            cur.execute(self._sql(sql), tuple(params))
        return cur

    def todos(self, sql: str, params=()) -> list[dict]:
        return [_normalizar(f) for f in self._ejecutar(sql, params).fetchall()]

    def uno(self, sql: str, params=()) -> dict | None:
        fila = self._ejecutar(sql, params).fetchone()
        return _normalizar(fila) if fila is not None else None

    def valor(self, sql: str, params=()):
        fila = self.uno(sql, params)
        return next(iter(fila.values())) if fila else None

    def ejecutar(self, sql: str, params=()) -> int:
        return self._ejecutar(sql, params).rowcount

    def insertar(self, sql: str, params=()) -> int:
        """Ejecuta un INSERT ... RETURNING id y devuelve el id generado."""
        fila = self._ejecutar(sql + " RETURNING id", params).fetchone()
        return fila["id"]

    def mes(self, columna: str) -> str:
        """Expresión SQL que agrupa una fecha por año-mes (AAAA-MM)."""
        if self.motor == "postgres":
            return f"to_char({columna}, 'YYYY-MM')"
        return f"strftime('%Y-%m', {columna})"

    def confirmar(self):
        self._con.commit()

    def revertir(self):
        self._con.rollback()

    def cerrar(self):
        self._con.close()

    def script(self, sql: str):
        if self.motor == "sqlite":
            self._con.executescript(sql)
        else:
            self._ejecutar(sql)
            self._con.commit()


def obtener_db() -> Conexion:
    """Una conexión por petición; se confirma o revierte al terminar."""
    if "db" not in g:
        g.db = Conexion(current_app.config["DATABASE_URL"])
    return g.db


def registrar(app):
    @app.after_request
    def confirmar_o_revertir(respuesta):
        db = g.pop("db", None)
        if db is not None:
            if respuesta.status_code < 400:
                db.confirmar()
            else:
                db.revertir()
            db.cerrar()
        return respuesta

    @app.teardown_appcontext
    def cerrar(_excepcion):
        db = g.pop("db", None)
        if db is not None:
            db.revertir()
            db.cerrar()


ESQUEMA_SQLITE = Path(__file__).resolve().parent.parent / "db" / "schema_sqlite.sql"


def crear_esquema_sqlite(url: str):
    """Crea las tablas en SQLite (desarrollo local y pruebas)."""
    con = Conexion(url)
    con.script(ESQUEMA_SQLITE.read_text(encoding="utf-8"))
    con.cerrar()


