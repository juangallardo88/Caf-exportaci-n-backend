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


# --- Proyección de agotamiento de stock ----------------------------------------------

DIAS_ALERTA_ALTA = 14
DIAS_ALERTA_MEDIA = 45


def _signo(tipo: str, cantidad: int) -> int:
    """Efecto de un movimiento sobre el stock: las salidas restan; entradas y ajustes ya traen su signo."""
    return -cantidad if tipo == "SALIDA" else cantidad


def proyectar_agotamiento(stock: int, minimo: int, movimientos: list[tuple[dt.date, str, int]],
                          hoy: dt.date, dias: int = 90) -> dict:
    """Estima en cuántos días un producto llega a su stock mínimo y se agota.

    Proyección lineal: el consumo diario es el ritmo promedio de salidas de los últimos ``dias``
    días, y se supone que sigue igual. Con tan pocos movimientos, una regresión sobre las salidas
    acumuladas sesga el resultado (una salida antigua pesa más que una reciente), por eso se usa
    el promedio.

    ``movimientos`` son tuplas (fecha, tipo, cantidad) de cualquier fecha; las que quedan fuera
    de la ventana se ignoran. Devuelve el consumo, los días y fechas estimadas, un nivel de
    urgencia y la serie de stock de la ventana (para graficar).
    """
    inicio = hoy - dt.timedelta(days=dias)
    en_ventana = [(f, t, c) for f, t, c in movimientos if inicio < f <= hoy]

    total = sum(c for _, t, c in en_ventana if t == "SALIDA")
    consumo = total / dias

    # Stock al final de cada día, reconstruido hacia atrás desde el stock actual
    cambio_por_dia = [0] * (dias + 1)
    for fecha, tipo, cantidad in en_ventana:
        cambio_por_dia[(fecha - inicio).days] += _signo(tipo, cantidad)
    serie, nivel_stock = [], stock
    for x in range(dias, -1, -1):
        serie.append({"fecha": (inicio + dt.timedelta(days=x)).isoformat(), "stock": nivel_stock})
        nivel_stock -= cambio_por_dia[x]
    serie.reverse()

    resultado = {
        "consumo_diario": round(consumo, 2),
        "consumo_semanal": round(consumo * 7, 1),
        "salidas_ventana": total,
        "dias_ventana": dias,
        "dias_para_minimo": None,
        "dias_para_agotarse": None,
        "fecha_minimo": None,
        "fecha_agotamiento": None,
        "serie": serie,
    }
    if stock == 0:
        return {**resultado, "nivel": "AGOTADO", "dias_para_minimo": 0, "dias_para_agotarse": 0,
                "fecha_minimo": hoy.isoformat(), "fecha_agotamiento": hoy.isoformat()}
    if consumo <= 0:
        return {**resultado, "nivel": "SIN_CONSUMO"}

    dias_agotarse = int(stock / consumo)
    dias_minimo = max(0, int((stock - minimo) / consumo))
    if dias_minimo <= DIAS_ALERTA_ALTA:
        nivel = "ALTA"
    elif dias_minimo <= DIAS_ALERTA_MEDIA:
        nivel = "MEDIA"
    else:
        nivel = "BAJA"
    return {
        **resultado,
        "nivel": nivel,
        "dias_para_minimo": dias_minimo,
        "dias_para_agotarse": dias_agotarse,
        "fecha_minimo": (hoy + dt.timedelta(days=dias_minimo)).isoformat(),
        "fecha_agotamiento": (hoy + dt.timedelta(days=dias_agotarse)).isoformat(),
    }
