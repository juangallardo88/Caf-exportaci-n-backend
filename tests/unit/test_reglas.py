"""Pruebas unitarias de las reglas de negocio puras (sin base de datos ni HTTP)."""
import datetime as dt

import pytest

from app.domain.reglas import (
    calcular_totales,
    estado_stock,
    fechas_validas,
    nuevo_stock,
    siguiente_consecutivo,
    transicion_valida,
)


class TestEstadosExportacion:  # HU-21
    @pytest.mark.parametrize("actual,nuevo", [
        ("BORRADOR", "CONFIRMADA"), ("CONFIRMADA", "EN_TRANSITO"),
        ("EN_TRANSITO", "ENTREGADA"), ("BORRADOR", "CANCELADA"), ("CONFIRMADA", "CANCELADA"),
    ])
    def test_transiciones_permitidas(self, actual, nuevo):
        assert transicion_valida(actual, nuevo)

    @pytest.mark.parametrize("actual,nuevo", [
        ("BORRADOR", "ENTREGADA"), ("ENTREGADA", "CANCELADA"), ("CANCELADA", "BORRADOR"),
        ("EN_TRANSITO", "CANCELADA"), ("CONFIRMADA", "BORRADOR"),
    ])
    def test_transiciones_prohibidas(self, actual, nuevo):
        assert not transicion_valida(actual, nuevo)


class TestConsecutivo:  # HU-17
    def test_primer_consecutivo_del_anio(self):
        assert siguiente_consecutivo(None, 2026) == "EXP-2026-0001"

    def test_incrementa_el_ultimo(self):
        assert siguiente_consecutivo("EXP-2026-0041", 2026) == "EXP-2026-0042"

    def test_reinicia_con_el_anio_nuevo(self):
        assert siguiente_consecutivo("EXP-2025-0099", 2026) == "EXP-2026-0001"


class TestTotales:  # HU-18
    def test_suma_subtotal_impuestos_y_flete(self):
        detalles = [{"cantidad": 200, "precio_unitario": 280}, {"cantidad": 50, "precio_unitario": 340}]
        totales = calcular_totales(detalles, impuestos=1460, flete=4200)
        assert totales == {"subtotal": 73000, "impuestos": 1460, "flete": 4200, "total": 78660}

    def test_exportacion_sin_productos(self):
        assert calcular_totales([], 0, 0)["total"] == 0


class TestFechas:  # HU-22
    def test_llegada_posterior_es_valida(self):
        assert fechas_validas(dt.date(2026, 11, 25), dt.date(2026, 12, 16))

    def test_mismo_dia_es_valido(self):
        assert fechas_validas(dt.date(2026, 11, 25), dt.date(2026, 11, 25))

    def test_llegada_anterior_es_invalida(self):
        assert not fechas_validas(dt.date(2026, 12, 10), dt.date(2026, 12, 1))


class TestMovimientosInventario:  # HU-25
    def test_entrada_suma(self):
        assert nuevo_stock(100, "ENTRADA", 50) == 150

    def test_salida_resta(self):
        assert nuevo_stock(100, "SALIDA", 30) == 70

    def test_salida_mayor_al_stock_se_rechaza(self):
        with pytest.raises(ValueError, match="Stock insuficiente"):
            nuevo_stock(10, "SALIDA", 11)

    def test_ajuste_negativo(self):
        assert nuevo_stock(100, "AJUSTE", -5) == 95

    def test_ajuste_que_deja_negativo_se_rechaza(self):
        with pytest.raises(ValueError, match="negativo"):
            nuevo_stock(3, "AJUSTE", -4)

    @pytest.mark.parametrize("tipo,cantidad", [("ENTRADA", 0), ("SALIDA", -1), ("AJUSTE", 0), ("REGALO", 5)])
    def test_movimientos_invalidos(self, tipo, cantidad):
        with pytest.raises(ValueError):
            nuevo_stock(10, tipo, cantidad)


class TestEstadoStock:  # HU-08 y HU-26
    @pytest.mark.parametrize("cantidad,minimo,esperado", [
        (0, 10, "AGOTADO"), (5, 10, "BAJO"), (10, 10, "BAJO"), (11, 10, "DISPONIBLE"),
    ])
    def test_clasificacion(self, cantidad, minimo, esperado):
        assert estado_stock(cantidad, minimo) == esperado
