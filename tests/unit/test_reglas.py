"""Pruebas unitarias de las reglas de negocio puras (sin base de datos ni HTTP)."""
import datetime as dt

import pytest

from app.domain.reglas import (
    calcular_totales,
    estado_stock,
    fechas_validas,
    nuevo_stock,
    proyectar_agotamiento,
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


class TestProyeccionAgotamiento:
    HOY = dt.date(2026, 11, 22)

    def test_ritmo_promedio_de_la_ventana(self):
        # 90 sacos en 90 días = 1 saco/día; con 100 de stock y mínimo 40 llega al mínimo en 60 días
        r = proyectar_agotamiento(100, 40, [(dt.date(2026, 10, 1), "SALIDA", 90)], self.HOY, dias=90)
        assert r["consumo_diario"] == 1 and r["consumo_semanal"] == 7
        assert r["dias_para_minimo"] == 60 and r["dias_para_agotarse"] == 100
        assert r["fecha_minimo"] == "2027-01-21" and r["fecha_agotamiento"] == "2027-03-02"
        assert r["nivel"] == "BAJA"

    def test_ignora_salidas_fuera_de_la_ventana(self):
        r = proyectar_agotamiento(100, 40, [(dt.date(2026, 1, 10), "SALIDA", 500)], self.HOY, dias=90)
        assert r["nivel"] == "SIN_CONSUMO" and r["dias_para_agotarse"] is None

    def test_las_entradas_no_cuentan_como_consumo(self):
        r = proyectar_agotamiento(100, 40, [(dt.date(2026, 11, 1), "ENTRADA", 300)], self.HOY)
        assert r["consumo_diario"] == 0 and r["nivel"] == "SIN_CONSUMO"

    @pytest.mark.parametrize("stock,nivel", [(50, "ALTA"), (80, "MEDIA"), (200, "BAJA")])
    def test_nivel_de_urgencia_segun_dias_para_el_minimo(self, stock, nivel):
        # consumo de 1 saco/día y mínimo 40: 10, 40 y 160 días para el mínimo
        r = proyectar_agotamiento(stock, 40, [(dt.date(2026, 10, 1), "SALIDA", 90)], self.HOY, dias=90)
        assert r["nivel"] == nivel

    def test_bajo_el_minimo_es_urgente(self):
        r = proyectar_agotamiento(30, 40, [(dt.date(2026, 11, 1), "SALIDA", 45)], self.HOY, dias=90)
        assert r["nivel"] == "ALTA" and r["dias_para_minimo"] == 0 and r["dias_para_agotarse"] == 60

    def test_sin_stock_esta_agotado(self):
        r = proyectar_agotamiento(0, 40, [(dt.date(2026, 11, 1), "SALIDA", 45)], self.HOY)
        assert r["nivel"] == "AGOTADO" and r["dias_para_agotarse"] == 0

    def test_serie_reconstruye_el_stock_hacia_atras(self):
        movimientos = [(dt.date(2026, 11, 10), "ENTRADA", 50), (dt.date(2026, 11, 15), "SALIDA", 20),
                       (dt.date(2026, 11, 20), "AJUSTE", -5)]
        r = proyectar_agotamiento(125, 10, movimientos, self.HOY, dias=30)
        stock_por_dia = {p["fecha"]: p["stock"] for p in r["serie"]}
        assert len(r["serie"]) == 31 and r["serie"][-1] == {"fecha": "2026-11-22", "stock": 125}
        assert stock_por_dia["2026-11-09"] == 100   # antes de la entrada
        assert stock_por_dia["2026-11-10"] == 150
        assert stock_por_dia["2026-11-15"] == 130
        assert stock_por_dia["2026-11-20"] == 125
