"""Productos e inventario."""
from __future__ import annotations

from . import Repositorio, patron

SELECT_PRODUCTO = (
    "SELECT p.*, i.cantidad AS stock, i.stock_minimo, i.ubicacion"
    " FROM producto p JOIN inventario i ON i.producto_id = p.id"
)


class ProductoRepositorio(Repositorio):
    tabla = "producto"
    columnas_editables = ("sku", "nombre", "descripcion", "categoria", "precio", "peso_kg", "volumen_m3", "activo")

    def listar(self, q: str | None = None, categoria: str | None = None, solo_activos: bool = True):
        condiciones, params = [], []
        if solo_activos:
            condiciones.append("p.activo = ?")
            params.append(True)
        if q:
            condiciones.append("(LOWER(p.nombre) LIKE ? ESCAPE '\\' OR LOWER(p.sku) LIKE ? ESCAPE '\\')")
            params += [patron(q), patron(q)]
        if categoria:
            condiciones.append("p.categoria = ?")
            params.append(categoria)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self.db.todos(f"{SELECT_PRODUCTO}{where} ORDER BY p.nombre", params)

    def por_id(self, id_: int):
        return self.db.uno(f"{SELECT_PRODUCTO} WHERE p.id = ?", (id_,))

    def por_sku(self, sku: str, excluir_id: int | None = None):
        return self.db.uno(
            "SELECT id FROM producto WHERE UPPER(sku) = UPPER(?) AND id <> ?", (sku, excluir_id or 0)
        )

    def crear(self, d: dict) -> int:
        return self.db.insertar(
            "INSERT INTO producto (sku, nombre, descripcion, categoria, precio, peso_kg, volumen_m3)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d["sku"], d["nombre"], d.get("descripcion"), d["categoria"], d["precio"], d["peso_kg"],
             d["volumen_m3"]),
        )


class InventarioRepositorio(Repositorio):
    tabla = "inventario"

    def crear(self, producto_id: int, cantidad: int, ubicacion: str, stock_minimo: int) -> int:
        return self.db.insertar(
            "INSERT INTO inventario (producto_id, cantidad, ubicacion, stock_minimo) VALUES (?, ?, ?, ?)",
            (producto_id, cantidad, ubicacion, stock_minimo),
        )

    def listar(self, q: str | None = None, solo_bajo_stock: bool = False):
        condiciones, params = ["p.activo = ?"], [True]
        if q:
            condiciones.append("(LOWER(p.nombre) LIKE ? ESCAPE '\\' OR LOWER(p.sku) LIKE ? ESCAPE '\\')")
            params += [patron(q), patron(q)]
        if solo_bajo_stock:
            condiciones.append("i.cantidad <= i.stock_minimo")
        return self.db.todos(
            "SELECT i.producto_id, p.sku, p.nombre, p.categoria, i.cantidad, i.ubicacion, i.stock_minimo"
            " FROM inventario i JOIN producto p ON p.id = i.producto_id"
            f" WHERE {' AND '.join(condiciones)} ORDER BY p.nombre",
            params,
        )

    def por_producto(self, producto_id: int):
        return self.db.uno(
            "SELECT i.producto_id, p.sku, p.nombre, p.categoria, p.activo, i.cantidad, i.ubicacion,"
            " i.stock_minimo FROM inventario i JOIN producto p ON p.id = i.producto_id"
            " WHERE i.producto_id = ?",
            (producto_id,),
        )

    def fijar_cantidad(self, producto_id: int, cantidad: int):
        self.db.ejecutar("UPDATE inventario SET cantidad = ? WHERE producto_id = ?", (cantidad, producto_id))

    def actualizar_datos(self, producto_id: int, ubicacion: str, stock_minimo: int):
        self.db.ejecutar(
            "UPDATE inventario SET ubicacion = ?, stock_minimo = ? WHERE producto_id = ?",
            (ubicacion, stock_minimo, producto_id),
        )

    def registrar_movimiento(self, producto_id: int, tipo: str, cantidad: int, motivo: str, usuario_id):
        return self.db.insertar(
            "INSERT INTO movimiento_inventario (producto_id, tipo, cantidad, motivo, usuario_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (producto_id, tipo, cantidad, motivo, usuario_id),
        )

    def movimientos(self, producto_id: int | None = None, limite: int = 100):
        condicion, params = "", []
        if producto_id:
            condicion = " WHERE m.producto_id = ?"
            params.append(producto_id)
        params.append(limite)
        return self.db.todos(
            "SELECT m.id, m.producto_id, p.sku, p.nombre AS producto, m.tipo, m.cantidad, m.motivo,"
            " m.fecha, u.nombre AS usuario FROM movimiento_inventario m"
            " JOIN producto p ON p.id = m.producto_id LEFT JOIN usuario u ON u.id = m.usuario_id"
            f"{condicion} ORDER BY m.fecha DESC, m.id DESC LIMIT ?",
            params,
        )
