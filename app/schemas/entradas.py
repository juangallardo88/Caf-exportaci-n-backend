"""Esquemas de entrada de cada módulo."""
from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal, Optional

from pydantic import Field, StringConstraints, model_validator

from . import Correo, Esquema, Telefono, Texto

Rol = Literal["ADMINISTRADOR", "OPERADOR", "AUDITOR"]


# --- Autenticación y usuarios (HU-01 a HU-03) ---------------------------------------

class Login(Esquema):
    correo: Correo
    contrasena: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class UsuarioNuevo(Esquema):
    nombre: Annotated[Texto, StringConstraints(max_length=120)]
    correo: Correo
    contrasena: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    rol: Rol


class UsuarioCambio(Esquema):
    rol: Optional[Rol] = None
    activo: Optional[bool] = None


# --- Países (HU-16) ----------------------------------------------------------------

class Pais(Esquema):
    nombre: Annotated[Texto, StringConstraints(max_length=100)]
    codigo_iso2: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{2}$")]
    codigo_iso3: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{3}$")]
    region: Annotated[Texto, StringConstraints(max_length=80)]


# --- Productos (HU-04 a HU-08) -----------------------------------------------------

class ProductoBase(Esquema):
    sku: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9-]{3,40}$")]
    nombre: Annotated[Texto, StringConstraints(max_length=120)]
    descripcion: Optional[Annotated[str, StringConstraints(max_length=500)]] = None
    categoria: Literal["CAFE", "CACAO"]
    precio: float = Field(ge=0, le=10_000_000)
    peso_kg: float = Field(gt=0, le=100_000)
    volumen_m3: float = Field(gt=0, le=1000)


class ProductoNuevo(ProductoBase):
    stock_inicial: int = Field(default=0, ge=0, le=10_000_000)
    stock_minimo: int = Field(default=0, ge=0, le=10_000_000)
    ubicacion: Annotated[Texto, StringConstraints(max_length=80)] = "Bodega principal"


class ProductoCambio(ProductoBase):
    pass


# --- Proveedores (HU-09 a HU-12) ---------------------------------------------------

class Proveedor(Esquema):
    nit: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9A-Za-z.-]{5,30}$")]
    razon_social: Annotated[Texto, StringConstraints(max_length=160)]
    pais_id: int = Field(gt=0)
    direccion: Annotated[Texto, StringConstraints(max_length=200)]
    telefono: Telefono
    correo: Correo
    condiciones_comerciales: Optional[Annotated[str, StringConstraints(max_length=500)]] = None


# --- Clientes (HU-13 a HU-15) ------------------------------------------------------

class Cliente(Esquema):
    tax_id: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9A-Za-z.-]{5,40}$")]
    razon_social: Annotated[Texto, StringConstraints(max_length=160)]
    pais_id: int = Field(gt=0)
    ciudad: Annotated[Texto, StringConstraints(max_length=100)]
    direccion_entrega: Annotated[Texto, StringConstraints(max_length=200)]
    contacto_compras: Annotated[Texto, StringConstraints(max_length=120)]
    correo: Optional[Correo] = None


# --- Exportaciones (HU-17 a HU-23) -------------------------------------------------

class ExportacionNueva(Esquema):
    cliente_id: int = Field(gt=0)
    pais_destino_id: int = Field(gt=0)
    puerto_salida: Annotated[Texto, StringConstraints(max_length=120)]
    incoterm: Literal["FOB", "CIF", "EXW", "DDP"]


class ExportacionCostos(Esquema):
    impuestos: float = Field(ge=0, le=100_000_000)
    flete: float = Field(ge=0, le=100_000_000)


class LineaProducto(Esquema):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1_000_000)


class CambioEstado(Esquema):
    estado: Literal["BORRADOR", "CONFIRMADA", "EN_TRANSITO", "ENTREGADA", "CANCELADA"]


class Fechas(Esquema):
    fecha_embarque: dt.date
    fecha_estimada_llegada: dt.date

    @model_validator(mode="after")
    def en_orden(self):
        if self.fecha_estimada_llegada < self.fecha_embarque:
            raise ValueError("La fecha estimada de llegada no puede ser anterior a la fecha de embarque")
        return self


class Transporte(Esquema):
    tipo: Literal["MARITIMO", "AEREO", "TERRESTRE", "MULTIMODAL"]
    empresa: Annotated[Texto, StringConstraints(max_length=120)]
    numero_guia: Annotated[Texto, StringConstraints(max_length=60)]
    numero_contenedor: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]] = None


# --- Inventario (HU-24 a HU-26) ----------------------------------------------------

class Movimiento(Esquema):
    producto_id: int = Field(gt=0)
    tipo: Literal["ENTRADA", "SALIDA", "AJUSTE"]
    cantidad: int = Field(ge=-10_000_000, le=10_000_000)
    motivo: Annotated[Texto, StringConstraints(min_length=3, max_length=200)]

    @model_validator(mode="after")
    def signo(self):
        if self.cantidad == 0:
            raise ValueError("La cantidad no puede ser cero")
        if self.tipo in ("ENTRADA", "SALIDA") and self.cantidad < 0:
            raise ValueError("En entradas y salidas la cantidad debe ser positiva")
        return self


class InventarioCambio(Esquema):
    ubicacion: Annotated[Texto, StringConstraints(max_length=80)]
    stock_minimo: int = Field(ge=0, le=10_000_000)
