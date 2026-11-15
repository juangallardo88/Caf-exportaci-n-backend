"""Reglas de negocio puras (sin base de datos): se prueban con pruebas unitarias."""
from __future__ import annotations

import datetime as dt

# --- Exportaciones (HU-17, HU-21, HU-22) -------------------------------------------

TRANSICIONES = {
    "BORRADOR": {"CONFIRMADA", "CANCELADA"},
    "CONFIRMADA": {"EN_TRANSITO", "CANCELADA"},
    "EN_TRANSITO": {"ENTREGADA"},
    "ENTREGADA": set(),
    "CANCELADA": set(),
}

ESTADOS_QUE_DESCUENTAN_STOCK = {"CONFIRMADA", "EN_TRANSITO", "ENTREGADA"}
ESTADOS_CERRADOS = {"ENTREGADA", "CANCELADA"}


def transicion_valida(actual: str, nuevo: str) -> bool:
    return nuevo in TRANSICIONES.get(actual, set())


def siguiente_consecutivo(ultimo: str | None, anio: int) -> str:
    """EXP-AAAA-NNNN; la numeración reinicia cada año."""
    prefijo = f"EXP-{anio}-"
    numero = 1
    if ultimo and ultimo.startswith(prefijo):
        numero = int(ultimo.removeprefix(prefijo)) + 1
    return f"{prefijo}{numero:04d}"


def calcular_totales(detalles: list[dict], impuestos: float, flete: float) -> dict:
    subtotal = round(sum(d["cantidad"] * d["precio_unitario"] for d in detalles), 2)
    return {
        "subtotal": subtotal,
        "impuestos": round(impuestos, 2),
        "flete": round(flete, 2),
        "total": round(subtotal + impuestos + flete, 2),
    }


def fechas_validas(embarque: dt.date | None, llegada: dt.date | None) -> bool:
    return embarque is None or llegada is None or llegada >= embarque


# --- Inventario (HU-24, HU-25, HU-26) ----------------------------------------------

def nuevo_stock(actual: int, tipo: str, cantidad: int) -> int:
    """Cantidad resultante tras un movimiento. Lanza ValueError si no es válido."""
    if tipo == "ENTRADA":
        if cantidad <= 0:
            raise ValueError("Una entrada debe tener cantidad positiva")
        return actual + cantidad
    if tipo == "SALIDA":
        if cantidad <= 0:
            raise ValueError("Una salida debe tener cantidad positiva")
        if cantidad > actual:
            raise ValueError(f"Stock insuficiente: hay {actual} unidades y se piden {cantidad}")
        return actual - cantidad
    if tipo == "AJUSTE":
        if cantidad == 0:
            raise ValueError("Un ajuste no puede ser cero")
        if actual + cantidad < 0:
            raise ValueError("El ajuste dejaría el inventario en negativo")
        return actual + cantidad
    raise ValueError("Tipo de movimiento inválido")


def estado_stock(cantidad: int, minimo: int) -> str:
    if cantidad == 0:
        return "AGOTADO"
    if cantidad <= minimo:
        return "BAJO"
    return "DISPONIBLE"
