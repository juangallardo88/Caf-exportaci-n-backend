"""Países, proveedores y clientes."""
from __future__ import annotations

from . import Repositorio, patron


class PaisRepositorio(Repositorio):
    tabla = "pais"
    columnas_editables = ("nombre", "codigo_iso2", "codigo_iso3", "region")

    def listar(self):
        return self.db.todos("SELECT * FROM pais ORDER BY nombre")

    def por_id(self, id_: int):
        return self.db.uno("SELECT * FROM pais WHERE id = ?", (id_,))

    def duplicado(self, datos: dict, excluir_id: int | None = None):
        return self.db.uno(
            "SELECT id FROM pais WHERE (LOWER(nombre) = LOWER(?) OR codigo_iso2 = ? OR codigo_iso3 = ?)"
            " AND id <> ?",
            (datos["nombre"], datos["codigo_iso2"], datos["codigo_iso3"], excluir_id or 0),
        )

    def crear(self, d: dict) -> int:
        return self.db.insertar(
            "INSERT INTO pais (nombre, codigo_iso2, codigo_iso3, region) VALUES (?, ?, ?, ?)",
            (d["nombre"], d["codigo_iso2"], d["codigo_iso3"], d["region"]),
        )


class ProveedorRepositorio(Repositorio):
    tabla = "proveedor"
    columnas_editables = (
        "nit", "razon_social", "pais_id", "direccion", "telefono", "correo", "condiciones_comerciales",
    )
    _select = (
        "SELECT pr.*, pa.nombre AS pais FROM proveedor pr JOIN pais pa ON pa.id = pr.pais_id"
    )

    def listar(self, q: str | None = None, pais_id: int | None = None):
        condiciones, params = [], []
        if q:
            condiciones.append(
                "(LOWER(pr.razon_social) LIKE ? ESCAPE '\\' OR LOWER(pr.nit) LIKE ? ESCAPE '\\')"
            )
            params += [patron(q), patron(q)]
        if pais_id:
            condiciones.append("pr.pais_id = ?")
            params.append(pais_id)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self.db.todos(f"{self._select}{where} ORDER BY pr.razon_social", params)

    def por_id(self, id_: int):
        return self.db.uno(f"{self._select} WHERE pr.id = ?", (id_,))

    def por_nit(self, nit: str, excluir_id: int | None = None):
        return self.db.uno(
            "SELECT id FROM proveedor WHERE LOWER(nit) = LOWER(?) AND id <> ?", (nit, excluir_id or 0)
        )

    def crear(self, d: dict) -> int:
        return self.db.insertar(
            "INSERT INTO proveedor (nit, razon_social, pais_id, direccion, telefono, correo,"
            " condiciones_comerciales) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d["nit"], d["razon_social"], d["pais_id"], d["direccion"], d["telefono"], d["correo"],
             d.get("condiciones_comerciales")),
        )

    def eliminar(self, id_: int) -> int:
        return self.db.ejecutar("DELETE FROM proveedor WHERE id = ?", (id_,))


class ClienteRepositorio(Repositorio):
    tabla = "cliente"
    columnas_editables = (
        "tax_id", "razon_social", "pais_id", "ciudad", "direccion_entrega", "contacto_compras", "correo",
    )
    _select = "SELECT c.*, pa.nombre AS pais FROM cliente c JOIN pais pa ON pa.id = c.pais_id"

    def listar(self, q: str | None = None, pais_id: int | None = None):
        condiciones, params = [], []
        if q:
            condiciones.append(
                "(LOWER(c.razon_social) LIKE ? ESCAPE '\\' OR LOWER(c.tax_id) LIKE ? ESCAPE '\\')"
            )
            params += [patron(q), patron(q)]
        if pais_id:
            condiciones.append("c.pais_id = ?")
            params.append(pais_id)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return self.db.todos(f"{self._select}{where} ORDER BY c.razon_social", params)

    def por_id(self, id_: int):
        return self.db.uno(f"{self._select} WHERE c.id = ?", (id_,))

    def por_tax_id(self, tax_id: str, excluir_id: int | None = None):
        return self.db.uno(
            "SELECT id FROM cliente WHERE LOWER(tax_id) = LOWER(?) AND id <> ?", (tax_id, excluir_id or 0)
        )

    def crear(self, d: dict) -> int:
        return self.db.insertar(
            "INSERT INTO cliente (tax_id, razon_social, pais_id, ciudad, direccion_entrega,"
            " contacto_compras, correo) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d["tax_id"], d["razon_social"], d["pais_id"], d["ciudad"], d["direccion_entrega"],
             d["contacto_compras"], d.get("correo")),
        )
