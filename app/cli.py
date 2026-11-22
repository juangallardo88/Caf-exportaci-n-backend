"""Comandos de consola para desarrollo local con SQLite.

    flask --app wsgi crear-db      # crea las tablas
    flask --app wsgi datos-demo    # carga los mismos datos de ejemplo del repositorio de base de datos

En producción las tablas y datos se cargan en Neon con schema.sql y seed.sql.
"""
from __future__ import annotations

import datetime as dt

import click
from werkzeug.security import generate_password_hash

from .database import Conexion, crear_esquema_sqlite

USUARIOS = [
    ("Administrador RiTech", "admin@ritech.co", "Admin123*", "ADMINISTRADOR"),
    ("Operador Logístico", "operador@ritech.co", "Operador123*", "OPERADOR"),
    ("Auditor Interno", "auditor@ritech.co", "Auditor123*", "AUDITOR"),
]
PAISES = [
    ("Colombia", "CO", "COL", "América del Sur"), ("Alemania", "DE", "DEU", "Unión Europea"),
    ("Bélgica", "BE", "BEL", "Unión Europea"), ("Países Bajos", "NL", "NLD", "Unión Europea"),
    ("España", "ES", "ESP", "Unión Europea"), ("Italia", "IT", "ITA", "Unión Europea"),
    ("Francia", "FR", "FRA", "Unión Europea"), ("Japón", "JP", "JPN", "Asia"),
    ("Estados Unidos", "US", "USA", "América del Norte"),
]
# sku, nombre, descripción, categoría, precio, peso, volumen, cantidad, ubicación, mínimo, entrada inicial
PRODUCTOS = [
    ("CAF-SUP-70", "Café Excelso Supremo", "Café verde arábica, saco de 70 kg", "CAFE", 280, 70, 0.11, 420, "Bodega Buenaventura", 100, 700),
    ("CAF-HUI-70", "Café Especial Huila", "Café de especialidad, saco de 70 kg", "CAFE", 340, 70, 0.11, 180, "Bodega Buenaventura", 80, 230),
    ("CAF-ORG-35", "Café Orgánico Sierra Nevada", "Café orgánico certificado, saco de 35 kg", "CAFE", 210, 35, 0.06, 45, "Bodega Santa Marta", 60, 75),
    ("CAF-DEC-70", "Café Descafeinado", "Café descafeinado por proceso de agua, 70 kg", "CAFE", 300, 70, 0.11, 90, "Bodega Buenaventura", 50, 90),
    ("CAC-FIN-60", "Cacao Fino de Aroma", "Cacao en grano fermentado y seco, saco de 60 kg", "CACAO", 250, 60, 0.10, 260, "Bodega Cartagena", 100, 410),
    ("CAC-TUM-60", "Cacao Tumaco", "Cacao en grano de Tumaco, saco de 60 kg", "CACAO", 230, 60, 0.10, 70, "Bodega Cartagena", 80, 70),
]
PROVEEDORES = [
    ("891100345-1", "Cooperativa de Caficultores del Huila", "Cra 5 # 10-20, Neiva", "+57 608 871 2233", "compras@coophuila.co", "Pago a 30 días"),
    ("900456789-2", "Asociación Cacaotera de Tumaco", "Calle 12 # 3-45, Tumaco", "+57 602 727 1100", "ventas@cacaotumaco.co", "Pago contra entrega"),
    ("800234567-3", "Finca La Esperanza", "Vereda El Carmen, Santa Marta", "+57 605 421 9988", "info@laesperanza.co", "Pago a 15 días"),
    ("901234567-4", "Trilladora del Valle", "Av 3N # 45-10, Cali", "+57 602 664 5544", "comercial@trilladora.co", "Pago a 45 días"),
]
CLIENTES = [
    ("DE-HRB-112233", "Hamburg Kaffee Import GmbH", "DE", "Hamburgo", "Speicherstadt 12, 20457 Hamburgo", "Anna Müller", "einkauf@hamburgkaffee.de"),
    ("BE-0456789123", "Antwerp Cocoa Traders BV", "BE", "Amberes", "Haven 210, 2030 Amberes", "Pieter Janssens", "buy@antwerpcocoa.be"),
    ("ESB12345678", "Café de Madrid SL", "ES", "Madrid", "Calle Alcalá 120, 28009 Madrid", "Lucía Gómez", "compras@cafedemadrid.es"),
    ("JP-4011001234567", "Tokyo Beans KK", "JP", "Tokio", "2-1 Shibuya, Tokio 150-0002", "Kenji Sato", "purchasing@tokyobeans.jp"),
    ("NL-854321987B01", "Amsterdam Chocolate Makers", "NL", "Ámsterdam", "Keizersgracht 300, Ámsterdam", "Sanne de Vries", "orders@amsterdamchoco.nl"),
    ("900123456-7", "Tostadora Andina SAS", "CO", "Medellín", "Cra 43A # 1-50, Medellín", "Carlos Restrepo", "compras@tostadoraandina.co"),
]
# consecutivo, tax_id, puerto, incoterm, estado, impuestos, flete, embarque, llegada, creado, [(sku, cantidad)], transporte
EXPORTACIONES = [
    ("EXP-2026-0001", "DE-HRB-112233", "Buenaventura", "FOB", "ENTREGADA", 1460, 4200, "2026-08-10", "2026-09-05", "2026-08-01 09:00:00",
     [("CAF-SUP-70", 200), ("CAF-HUI-70", 50)], ("MARITIMO", "Hapag-Lloyd", "HLCU-BUN-884512", "HLXU 452187-3")),
    ("EXP-2026-0002", "BE-0456789123", "Cartagena", "CIF", "EN_TRANSITO", 750, 3100, "2026-10-20", "2026-11-18", "2026-10-05 10:30:00",
     [("CAC-FIN-60", 150)], ("MARITIMO", "Maersk", "MAEU-CTG-221907", "MSKU 778120-5")),
    ("EXP-2026-0003", "ESB12345678", "Cartagena", "FOB", "CONFIRMADA", 574, 2500, "2026-11-25", "2026-12-16", "2026-11-03 14:15:00",
     [("CAF-SUP-70", 80), ("CAF-ORG-35", 30)], ("MARITIMO", "CMA CGM", "CMAU-CTG-330118", None)),
    ("EXP-2026-0004", "JP-4011001234567", "Buenaventura", "DDP", "BORRADOR", 0, 0, None, None, "2026-11-10 08:45:00",
     [("CAF-HUI-70", 40)], None),
    ("EXP-2026-0005", "NL-854321987B01", "Santa Marta", "EXW", "CANCELADA", 0, 0, None, None, "2026-09-15 16:20:00",
     [("CAC-TUM-60", 50)], None),
]


# Los eventos del historial se guardan en UTC (como CURRENT_TIMESTAMP); Colombia es UTC-5.
UTC_COLOMBIA = dt.timedelta(hours=5)
MODOS_DEMO = {"MARITIMO": "Marítimo", "AEREO": "Aéreo", "TERRESTRE": "Terrestre", "MULTIMODAL": "Multimodal"}


def _usd(valor: float) -> str:
    return "US$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def momentos_demo(exportacion) -> dict:
    """Hora local de cada paso de una exportación de ejemplo."""
    cons, tax, puerto, inco, estado, imp, flete, emb, lle, creado, lineas, transp = exportacion
    t0 = dt.datetime.fromisoformat(creado)
    return {
        "creada": t0,
        "confirmada": t0 + dt.timedelta(days=1, hours=2),
        "en_transito": dt.datetime.fromisoformat(f"{emb} 08:00:00") if emb else None,
        "entregada": dt.datetime.fromisoformat(f"{lle} 15:00:00") if lle else None,
        "cancelada": t0 + dt.timedelta(days=3, hours=1),
    }


def eventos_demo(exportacion, cliente: str, pais: str) -> list[tuple]:
    """Historial coherente con los datos de ejemplo: (fecha UTC, tipo, estado, descripción, correo)."""
    cons, tax, puerto, inco, estado, imp, flete, emb, lle, creado, lineas, transp = exportacion
    m, op, adm = momentos_demo(exportacion), "operador@ritech.co", "admin@ritech.co"
    t0, eventos = m["creada"], []
    eventos.append((t0, "CREADA", "BORRADOR",
                    f"Creó la exportación {cons} para {cliente} hacia {pais} ({inco}, salida por {puerto})", op))
    precios = {p[0]: (p[1], p[4]) for p in PRODUCTOS}
    for i, (sku, cantidad) in enumerate(lineas, start=1):
        nombre, precio = precios[sku]
        eventos.append((t0 + dt.timedelta(minutes=10 * i), "PRODUCTOS", None,
                        f"Agregó {cantidad} sacos de {nombre} a {_usd(precio)} c/u", op))
    if estado in ("CONFIRMADA", "EN_TRANSITO", "ENTREGADA"):
        eventos.append((t0 + dt.timedelta(hours=1), "COSTOS", None,
                        f"Actualizó los costos: impuestos {_usd(imp)} · flete {_usd(flete)}", op))
        f_emb, f_lle = (dt.date.fromisoformat(x).strftime("%d/%m/%Y") for x in (emb, lle))
        eventos.append((t0 + dt.timedelta(hours=1, minutes=5), "FECHAS", None,
                        f"Registró las fechas: embarque {f_emb} · llegada estimada {f_lle}", op))
        tipo, empresa, guia, contenedor = transp
        extra = f" · contenedor {contenedor}" if contenedor else ""
        eventos.append((t0 + dt.timedelta(days=1), "TRANSPORTE", None,
                        f"Registró el transporte: {MODOS_DEMO[tipo]} · {empresa} · guía {guia}{extra}", op))
        sacos = sum(c for _, c in lineas)
        eventos.append((m["confirmada"], "ESTADO", "CONFIRMADA",
                        f"Confirmó la exportación: se descontaron {sacos} sacos del inventario", adm))
    if estado in ("EN_TRANSITO", "ENTREGADA"):
        eventos.append((m["en_transito"], "ESTADO", "EN_TRANSITO", f"Marcó la carga en tránsito desde {puerto}", op))
    if estado == "ENTREGADA":
        eventos.append((m["entregada"], "ESTADO", "ENTREGADA", f"Marcó la exportación como entregada a {cliente}", op))
    if estado == "CANCELADA":
        eventos.append((m["cancelada"], "ESTADO", "CANCELADA", "Canceló la exportación", adm))
    return [(fecha + UTC_COLOMBIA, *resto) for fecha, *resto in eventos]


def cargar_datos_demo(db: Conexion, metodo_hash: str = "pbkdf2:sha256"):
    ids = {}
    for nombre, correo, clave, rol in USUARIOS:
        ids[correo] = db.insertar(
            "INSERT INTO usuario (nombre, correo, contrasena_hash, rol) VALUES (?, ?, ?, ?)",
            (nombre, correo, generate_password_hash(clave, method=metodo_hash), rol),
        )
    operador = ids["operador@ritech.co"]
    paises = {iso2: db.insertar("INSERT INTO pais (nombre, codigo_iso2, codigo_iso3, region) VALUES (?, ?, ?, ?)",
                                (n, iso2, iso3, r)) for n, iso2, iso3, r in PAISES}
    productos = {}
    for sku, nombre, desc, cat, precio, peso, vol, cant, ubic, minimo, entrada in PRODUCTOS:
        pid = db.insertar(
            "INSERT INTO producto (sku, nombre, descripcion, categoria, precio, peso_kg, volumen_m3)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)", (sku, nombre, desc, cat, precio, peso, vol))
        productos[sku] = (pid, precio)
        db.insertar("INSERT INTO inventario (producto_id, cantidad, ubicacion, stock_minimo) VALUES (?, ?, ?, ?)",
                    (pid, cant, ubic, minimo))
        db.insertar("INSERT INTO movimiento_inventario (producto_id, tipo, cantidad, motivo, fecha, usuario_id)"
                    " VALUES (?, 'ENTRADA', ?, 'Compra inicial a proveedor', '2026-07-20 08:00:00', ?)",
                    (pid, entrada, operador))
    for nit, razon, dire, tel, correo, cond in PROVEEDORES:
        db.insertar("INSERT INTO proveedor (nit, razon_social, pais_id, direccion, telefono, correo,"
                    " condiciones_comerciales) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (nit, razon, paises["CO"], dire, tel, correo, cond))
    clientes = {}
    for tax, razon, iso, ciudad, dire, contacto, correo in CLIENTES:
        clientes[tax] = (db.insertar(
            "INSERT INTO cliente (tax_id, razon_social, pais_id, ciudad, direccion_entrega, contacto_compras, correo)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)", (tax, razon, paises[iso], ciudad, dire, contacto, correo)), paises[iso])
    nombres_cliente = {c[0]: c[1] for c in CLIENTES}
    nombres_pais = {pid: next(n for n, iso2, *_ in PAISES if iso2 == iso) for iso, pid in paises.items()}
    for exportacion in EXPORTACIONES:
        cons, tax, puerto, inco, estado, imp, flete, emb, lle, creado, lineas, transp = exportacion
        cliente_id, pais_id = clientes[tax]
        eid = db.insertar(
            "INSERT INTO exportacion (consecutivo, cliente_id, pais_destino_id, puerto_salida, incoterm, estado,"
            " impuestos, flete, fecha_embarque, fecha_estimada_llegada, creado_por, creado_en)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cons, cliente_id, pais_id, puerto, inco, estado, imp, flete, emb, lle, operador, creado))
        for sku, cantidad in lineas:
            pid, precio = productos[sku]
            db.insertar("INSERT INTO detalle_exportacion (exportacion_id, producto_id, cantidad, precio_unitario,"
                        " subtotal) VALUES (?, ?, ?, ?, ?)", (eid, pid, cantidad, precio, cantidad * precio))
            if estado in ("CONFIRMADA", "EN_TRANSITO", "ENTREGADA"):
                confirmada = momentos_demo(exportacion)["confirmada"].isoformat(sep=" ")
                db.insertar("INSERT INTO movimiento_inventario (producto_id, tipo, cantidad, motivo, fecha, usuario_id)"
                            " VALUES (?, 'SALIDA', ?, ?, ?, ?)", (pid, cantidad, f"Exportación {cons}", confirmada, operador))
        if transp:
            db.insertar("INSERT INTO transporte (exportacion_id, tipo, empresa, numero_guia, numero_contenedor)"
                        " VALUES (?, ?, ?, ?, ?)", (eid, *transp))
        for fecha, tipo, estado_ev, descripcion, correo in eventos_demo(exportacion, nombres_cliente[tax], nombres_pais[pais_id]):
            db.insertar("INSERT INTO evento_exportacion (exportacion_id, tipo, estado, descripcion, usuario_id, fecha)"
                        " VALUES (?, ?, ?, ?, ?, ?)", (eid, tipo, estado_ev, descripcion, ids[correo], fecha.isoformat(sep=" ")))
    db.confirmar()


def registrar(app):
    @app.cli.command("crear-db")
    def crear_db():
        """Crea las tablas en la base SQLite local."""
        url = app.config["DATABASE_URL"]
        if not url.startswith("sqlite"):
            raise click.ClickException("Para PostgreSQL usa schema.sql del repositorio de base de datos")
        crear_esquema_sqlite(url)
        click.echo("Tablas creadas")

    @app.cli.command("datos-demo")
    def datos_demo():
        """Crea las tablas y carga los datos de ejemplo en SQLite."""
        url = app.config["DATABASE_URL"]
        if not url.startswith("sqlite"):
            raise click.ClickException("Para PostgreSQL usa seed.sql del repositorio de base de datos")
        crear_esquema_sqlite(url)
        db = Conexion(url)
        cargar_datos_demo(db, app.config["HASH_METHOD"])
        db.cerrar()
        click.echo("Datos de demostración cargados")
