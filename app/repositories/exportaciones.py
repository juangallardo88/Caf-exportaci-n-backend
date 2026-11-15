"""Exportaciones, su detalle y su transporte."""
from __future__ import annotations

from . import Repositorio, patron

TOTALES = (
    "COALESCE((SELECT SUM(d.subtotal) FROM detalle_exportacion d WHERE d.exportacion_id = e.id), 0)"
)

SELECT_EXPORTACION = (
    "SELECT e.*, c.razon_social AS cliente, pa.nombre AS pais_destino,"
    f" {TOTALES} AS subtotal,"
    f" {TOTALES} + e.impuestos + e.flete AS total"
    " FROM exportacion e JOIN cliente c ON c.id = e.cliente_id JOIN pais pa ON pa.id = e.pais_destino_id"
)


class ExportacionRepositorio(Repositorio):
    tabla = "exportacion"
    columnas_editables = ("estado", "impuestos", "flete", "fecha_embarque", "fecha_estimada_llegada")

    def listar(self, estado=None, desde=None, hasta=None, cliente_id=None, q=None):
        condiciones, params = [], []
        if estado:
            condiciones.append("e.estado = ?")
            params.append(estado)
        if desde:
            condiciones.append("COALESCE(e.fecha_embarque, DATE(e.creado_en)) >= ?")
            params.append(desde)
        if hasta:
            condiciones.append("COALESCE(e.fecha_embarque, DATE(e.creado_en)) <= ?")
            params.append(hasta)
        if cliente_id:
            condiciones.append("e.cliente_id = ?")
            params.append(cliente_id)
        if q:
            condiciones.append(
                "(LOWER(e.consecutivo) LIKE ? ESCAPE '\\' OR LOWER(c.razon_social) LIKE ? ESCAPE '\\')"
            )
            params += [patron(q), patron(q)]
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self.db.todos(f"{SELECT_EXPORTACION}{where} ORDER BY e.creado_en DESC, e.id DESC", params)

    def por_id(self, id_: int):
        return self.db.uno(f"{SELECT_EXPORTACION} WHERE e.id = ?", (id_,))

    def ultimo_consecutivo(self, anio: int):
        return self.db.valor(
            "SELECT MAX(consecutivo) AS ultimo FROM exportacion WHERE consecutivo LIKE ?", (f"EXP-{anio}-%",)
        )

    def crear(self, d: dict) -> int:
        return self.db.insertar(
            "INSERT INTO exportacion (consecutivo, cliente_id, pais_destino_id, puerto_salida, incoterm,"
            " creado_por) VALUES (?, ?, ?, ?, ?, ?)",
            (d["consecutivo"], d["cliente_id"], d["pais_destino_id"], d["puerto_salida"], d["incoterm"],
             d["creado_por"]),
        )

    # --- Detalle (HU-18) ---
    def detalles(self, exportacion_id: int):
        return self.db.todos(
            "SELECT d.id, d.producto_id, p.sku, p.nombre AS producto, d.cantidad, d.precio_unitario,"
            " d.subtotal FROM detalle_exportacion d JOIN producto p ON p.id = d.producto_id"
            " WHERE d.exportacion_id = ? ORDER BY d.id",
            (exportacion_id,),
        )

    def detalle_de_producto(self, exportacion_id: int, producto_id: int):
        return self.db.uno(
            "SELECT * FROM detalle_exportacion WHERE exportacion_id = ? AND producto_id = ?",
            (exportacion_id, producto_id),
        )

    def agregar_detalle(self, exportacion_id, producto_id, cantidad, precio):
        return self.db.insertar(
            "INSERT INTO detalle_exportacion (exportacion_id, producto_id, cantidad, precio_unitario,"
            " subtotal) VALUES (?, ?, ?, ?, ?)",
            (exportacion_id, producto_id, cantidad, precio, round(cantidad * precio, 2)),
        )

    def actualizar_detalle(self, detalle_id, cantidad, precio):
        self.db.ejecutar(
            "UPDATE detalle_exportacion SET cantidad = ?, precio_unitario = ?, subtotal = ? WHERE id = ?",
            (cantidad, precio, round(cantidad * precio, 2), detalle_id),
        )

    def quitar_detalle(self, exportacion_id: int, detalle_id: int) -> int:
        return self.db.ejecutar(
            "DELETE FROM detalle_exportacion WHERE id = ? AND exportacion_id = ?", (detalle_id, exportacion_id)
        )

    # --- Transporte (HU-23) ---
    def transporte(self, exportacion_id: int):
        return self.db.uno("SELECT * FROM transporte WHERE exportacion_id = ?", (exportacion_id,))

    def guardar_transporte(self, exportacion_id: int, d: dict):
        if self.transporte(exportacion_id):
            self.db.ejecutar(
                "UPDATE transporte SET tipo = ?, empresa = ?, numero_guia = ?, numero_contenedor = ?"
                " WHERE exportacion_id = ?",
                (d["tipo"], d["empresa"], d["numero_guia"], d.get("numero_contenedor"), exportacion_id),
            )
        else:
            self.db.insertar(
                "INSERT INTO transporte (exportacion_id, tipo, empresa, numero_guia, numero_contenedor)"
                " VALUES (?, ?, ?, ?, ?)",
                (exportacion_id, d["tipo"], d["empresa"], d["numero_guia"], d.get("numero_contenedor")),
            )
