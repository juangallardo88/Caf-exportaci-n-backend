"""Pruebas unitarias de validación de datos de entrada (DTO con Pydantic)."""
import pytest
from pydantic import ValidationError

from app.schemas.entradas import Cliente, Fechas, Movimiento, Pais, ProductoNuevo, Proveedor, UsuarioNuevo

PROVEEDOR = {
    "nit": "891100345-1", "razon_social": "Cooperativa del Huila", "pais_id": 1,
    "direccion": "Cra 5 # 10-20", "telefono": "+57 608 871 2233", "correo": "Compras@CoopHuila.co",
}


def campos_con_error(err: ValidationError) -> set:
    return {".".join(str(p) for p in e["loc"]) for e in err.errors()}


class TestProveedor:  # HU-09 y HU-11
    def test_datos_validos_y_correo_en_minusculas(self):
        assert Proveedor(**PROVEEDOR).correo == "compras@coophuila.co"

    def test_correo_invalido(self):
        with pytest.raises(ValidationError) as err:
            Proveedor(**{**PROVEEDOR, "correo": "compras-sin-arroba"})
        assert campos_con_error(err.value) == {"correo"}

    @pytest.mark.parametrize("telefono", ["abc123", "12", "+57 (608) 871 2233 99999999"])
    def test_telefono_invalido(self, telefono):
        with pytest.raises(ValidationError) as err:
            Proveedor(**{**PROVEEDOR, "telefono": telefono})
        assert "telefono" in campos_con_error(err.value)

    def test_campos_desconocidos_se_rechazan(self):
        with pytest.raises(ValidationError):
            Proveedor(**PROVEEDOR, es_admin=True)


class TestCliente:  # HU-13 y HU-15
    def test_razon_social_vacia(self):
        datos = {"tax_id": "ESB12345678", "razon_social": "   ", "pais_id": 1, "ciudad": "Madrid",
                 "direccion_entrega": "Alcalá 120", "contacto_compras": "Lucía"}
        with pytest.raises(ValidationError) as err:
            Cliente(**datos)
        assert campos_con_error(err.value) == {"razon_social"}


class TestPais:  # HU-16
    def test_codigos_se_convierten_a_mayusculas(self):
        pais = Pais(nombre="Japón", codigo_iso2="jp", codigo_iso3="jpn", region="Asia")
        assert (pais.codigo_iso2, pais.codigo_iso3) == ("JP", "JPN")

    def test_codigo_iso_con_longitud_incorrecta(self):
        with pytest.raises(ValidationError):
            Pais(nombre="Japón", codigo_iso2="JPN", codigo_iso3="JP", region="Asia")


class TestProducto:  # HU-04
    def test_precio_negativo(self):
        with pytest.raises(ValidationError) as err:
            ProductoNuevo(sku="CAF-1", nombre="Café", categoria="CAFE", precio=-1, peso_kg=70, volumen_m3=0.1)
        assert campos_con_error(err.value) == {"precio"}

    def test_categoria_fuera_de_catalogo(self):
        with pytest.raises(ValidationError):
            ProductoNuevo(sku="TE-1", nombre="Té", categoria="TE", precio=1, peso_kg=1, volumen_m3=0.1)


class TestFechas:  # HU-22
    def test_llegada_anterior_al_embarque(self):
        with pytest.raises(ValidationError, match="anterior"):
            Fechas(fecha_embarque="2026-12-10", fecha_estimada_llegada="2026-12-01")

    def test_fecha_inexistente(self):
        with pytest.raises(ValidationError):
            Fechas(fecha_embarque="2026-02-31", fecha_estimada_llegada="2026-03-10")


class TestMovimiento:  # HU-25
    def test_salida_negativa(self):
        with pytest.raises(ValidationError):
            Movimiento(producto_id=1, tipo="SALIDA", cantidad=-5, motivo="Despacho")

    def test_ajuste_negativo_permitido(self):
        assert Movimiento(producto_id=1, tipo="AJUSTE", cantidad=-5, motivo="Merma").cantidad == -5


class TestUsuario:  # HU-03
    def test_contrasena_corta(self):
        with pytest.raises(ValidationError):
            UsuarioNuevo(nombre="Ana", correo="ana@ritech.co", contrasena="123", rol="OPERADOR")

    def test_rol_inexistente(self):
        with pytest.raises(ValidationError):
            UsuarioNuevo(nombre="Ana", correo="ana@ritech.co", contrasena="Segura123*", rol="SUPERUSUARIO")
