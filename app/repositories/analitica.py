"""Consultas de dashboard, estadísticas, búsqueda y reportes (HU-27 a HU-30)."""
from __future__ import annotations

from . import Repositorio, patron
from .exportaciones import SELECT_EXPORTACION, TOTALES

VALOR_EXPORTACION = f"({TOTALES} + e.impuestos + e.flete)"
# Las exportaciones en borrador o canceladas no cuentan como valor exportado
ESTADOS_CON_VALOR = ("CONFIRMADA", "EN_TRANSITO", "ENTREGADA")


class AnaliticaRepositorio(Repositorio):
    def _en_estados(self) -> tuple[str, tuple]:
        return "e.estado IN (?, ?, ?)", ESTADOS_CON_VALOR

    def conteo_por_estado(self):
        return self.db.todos("SELECT estado, COUNT(*) AS cantidad FROM exportacion GROUP BY estado")

    def valor_exportado(self) -> float:
        cond, params = self._en_estados()
        return self.db.valor(f"SELECT COALESCE(SUM({VALOR_EXPORTACION}), 0) AS v FROM exportacion e WHERE {cond}",
                             params) or 0

    def contar(self, tabla: str) -> int:
        tablas = {"cliente", "proveedor", "pais"}
        if tabla not in tablas:
            raise ValueError("Tabla no permitida")
        return self.db.valor(f"SELECT COUNT(*) AS n FROM {tabla}")

    def resumen_inventario(self):
        return self.db.uno(
            "SELECT COUNT(*) AS productos, COALESCE(SUM(i.cantidad), 0) AS unidades,"
            " COALESCE(SUM(i.cantidad * p.precio), 0) AS valor,"
            " COALESCE(SUM(CASE WHEN i.cantidad <= i.stock_minimo THEN 1 ELSE 0 END), 0) AS bajo_stock"
            " FROM inventario i JOIN producto p ON p.id = i.producto_id WHERE p.activo = ?",
            (True,),
        )

    def ultimas_exportaciones(self, limite: int = 5):
        return self.db.todos(f"{SELECT_EXPORTACION} ORDER BY e.creado_en DESC, e.id DESC LIMIT ?", (limite,))

    def por_mes(self):
        cond, params = self._en_estados()
        mes = self.db.mes("e.creado_en")
        return self.db.todos(
            f"SELECT {mes} AS mes, COUNT(*) AS cantidad, COALESCE(SUM({VALOR_EXPORTACION}), 0) AS valor"
            f" FROM exportacion e WHERE {cond} GROUP BY {mes} ORDER BY mes",
            params,
        )

    def por_destino(self):
        cond, params = self._en_estados()
        return self.db.todos(
            f"SELECT pa.nombre AS pais, COUNT(*) AS cantidad, COALESCE(SUM({VALOR_EXPORTACION}), 0) AS valor"
            f" FROM exportacion e JOIN pais pa ON pa.id = e.pais_destino_id WHERE {cond}"
            " GROUP BY pa.nombre ORDER BY valor DESC",
            params,
        )

    def top_productos(self, limite: int = 5):
        cond, params = self._en_estados()
        return self.db.todos(
            "SELECT p.sku, p.nombre, SUM(d.cantidad) AS unidades, SUM(d.subtotal) AS valor"
            " FROM detalle_exportacion d JOIN exportacion e ON e.id = d.exportacion_id"
            f" JOIN producto p ON p.id = d.producto_id WHERE {cond}"
            " GROUP BY p.sku, p.nombre ORDER BY unidades DESC LIMIT ?",
            (*params, limite),
        )

    def inventario_por_categoria(self):
        return self.db.todos(
            "SELECT p.categoria, COALESCE(SUM(i.cantidad), 0) AS unidades,"
            " COALESCE(SUM(i.cantidad * p.precio), 0) AS valor"
            " FROM inventario i JOIN producto p ON p.id = i.producto_id WHERE p.activo = ?"
            " GROUP BY p.categoria ORDER BY p.categoria",
            (True,),
        )

    def buscar(self, q: str, limite: int = 5) -> dict:
        p = patron(q)
        return {
            "productos": self.db.todos(
                "SELECT id, sku, nombre, categoria FROM producto WHERE activo = ? AND"
                " (LOWER(nombre) LIKE ? ESCAPE '\\' OR LOWER(sku) LIKE ? ESCAPE '\\') ORDER BY nombre LIMIT ?",
                (True, p, p, limite),
            ),
            "proveedores": self.db.todos(
                "SELECT id, nit, razon_social FROM proveedor WHERE LOWER(razon_social) LIKE ? ESCAPE '\\'"
                " OR LOWER(nit) LIKE ? ESCAPE '\\' ORDER BY razon_social LIMIT ?",
                (p, p, limite),
            ),
            "clientes": self.db.todos(
                "SELECT id, tax_id, razon_social FROM cliente WHERE LOWER(razon_social) LIKE ? ESCAPE '\\'"
                " OR LOWER(tax_id) LIKE ? ESCAPE '\\' ORDER BY razon_social LIMIT ?",
                (p, p, limite),
            ),
            "exportaciones": self.db.todos(
                "SELECT e.id, e.consecutivo, e.estado, c.razon_social AS cliente FROM exportacion e"
                " JOIN cliente c ON c.id = e.cliente_id WHERE LOWER(e.consecutivo) LIKE ? ESCAPE '\\'"
                " OR LOWER(c.razon_social) LIKE ? ESCAPE '\\' ORDER BY e.creado_en DESC LIMIT ?",
                (p, p, limite),
            ),
        }
