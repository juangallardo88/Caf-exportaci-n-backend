"""Países (HU-16), proveedores (HU-09 a HU-12) y clientes (HU-13 a HU-15)."""
from __future__ import annotations

from ..errors import Conflicto, NoEncontrado, ReglaNegocio
from ..repositories.catalogos import ClienteRepositorio, PaisRepositorio, ProveedorRepositorio


def _exigir_pais(pais_id: int):
    if not PaisRepositorio().por_id(pais_id):
        raise ReglaNegocio("El país seleccionado no existe", [{"campo": "pais_id", "mensaje": "País inexistente"}])


# --- Países ---

def listar_paises():
    return PaisRepositorio().listar()


def crear_pais(datos) -> dict:
    repo, d = PaisRepositorio(), datos.model_dump()
    if repo.duplicado(d):
        raise Conflicto("Ya existe un país con ese nombre o código ISO")
    return repo.por_id(repo.crear(d))


def actualizar_pais(pais_id: int, datos) -> dict:
    repo, d = PaisRepositorio(), datos.model_dump()
    if not repo.por_id(pais_id):
        raise NoEncontrado("País no encontrado")
    if repo.duplicado(d, excluir_id=pais_id):
        raise Conflicto("Ya existe un país con ese nombre o código ISO")
    repo.actualizar(pais_id, d)
    return repo.por_id(pais_id)


# --- Proveedores ---

def listar_proveedores(q=None, pais_id=None):
    return ProveedorRepositorio().listar(q, pais_id)


def obtener_proveedor(proveedor_id: int) -> dict:
    proveedor = ProveedorRepositorio().por_id(proveedor_id)
    if not proveedor:
        raise NoEncontrado("Proveedor no encontrado")
    return proveedor


def crear_proveedor(datos) -> dict:
    repo, d = ProveedorRepositorio(), datos.model_dump()
    _exigir_pais(d["pais_id"])
    if repo.por_nit(d["nit"]):
        raise Conflicto("Ya existe un proveedor con ese NIT/RUT")
    return repo.por_id(repo.crear(d))


def actualizar_proveedor(proveedor_id: int, datos) -> dict:
    repo, d = ProveedorRepositorio(), datos.model_dump()
    obtener_proveedor(proveedor_id)
    _exigir_pais(d["pais_id"])
    if repo.por_nit(d["nit"], excluir_id=proveedor_id):
        raise Conflicto("Ya existe otro proveedor con ese NIT/RUT")
    repo.actualizar(proveedor_id, d)
    return repo.por_id(proveedor_id)


def eliminar_proveedor(proveedor_id: int):
    obtener_proveedor(proveedor_id)
    ProveedorRepositorio().eliminar(proveedor_id)


# --- Clientes ---

def listar_clientes(q=None, pais_id=None):
    return ClienteRepositorio().listar(q, pais_id)


def obtener_cliente(cliente_id: int) -> dict:
    cliente = ClienteRepositorio().por_id(cliente_id)
    if not cliente:
        raise NoEncontrado("Cliente no encontrado")
    return cliente


def crear_cliente(datos) -> dict:
    repo, d = ClienteRepositorio(), datos.model_dump()
    _exigir_pais(d["pais_id"])
    if repo.por_tax_id(d["tax_id"]):
        raise Conflicto("Ya existe un cliente con ese Tax ID")
    return repo.por_id(repo.crear(d))


def actualizar_cliente(cliente_id: int, datos) -> dict:
    repo, d = ClienteRepositorio(), datos.model_dump()
    obtener_cliente(cliente_id)
    _exigir_pais(d["pais_id"])
    if repo.por_tax_id(d["tax_id"], excluir_id=cliente_id):
        raise Conflicto("Tax ID ya registrado en otro cliente")
    repo.actualizar(cliente_id, d)
    return repo.por_id(cliente_id)
