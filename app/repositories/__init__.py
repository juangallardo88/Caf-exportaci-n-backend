"""Repositorios: única capa que escribe SQL. Siempre con parámetros (sin concatenar datos)."""
from __future__ import annotations

from ..database import Conexion, obtener_db


class Repositorio:
    tabla: str = ""
    columnas_editables: tuple[str, ...] = ()

    def __init__(self, db: Conexion | None = None):
        self.db = db or obtener_db()

    def actualizar(self, id_: int, campos: dict) -> int:
        campos = {k: v for k, v in campos.items() if k in self.columnas_editables}
        if not campos:
            return 0
        asignaciones = ", ".join(f"{columna} = ?" for columna in campos)
        return self.db.ejecutar(
            f"UPDATE {self.tabla} SET {asignaciones} WHERE id = ?", (*campos.values(), id_)
        )


def patron(texto: str) -> str:
    """Patrón LIKE insensible a mayúsculas; escapa los comodines del usuario."""
    limpio = texto.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpio}%"
