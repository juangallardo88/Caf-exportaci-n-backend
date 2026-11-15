-- Esquema equivalente a schema.sql (PostgreSQL) para desarrollo local y pruebas con SQLite.
-- La fuente oficial del modelo es el repositorio de base de datos.

DROP TABLE IF EXISTS token_revocado;
DROP TABLE IF EXISTS movimiento_inventario;
DROP TABLE IF EXISTS transporte;
DROP TABLE IF EXISTS detalle_exportacion;
DROP TABLE IF EXISTS exportacion;
DROP TABLE IF EXISTS inventario;
DROP TABLE IF EXISTS cliente;
DROP TABLE IF EXISTS proveedor;
DROP TABLE IF EXISTS producto;
DROP TABLE IF EXISTS pais;
DROP TABLE IF EXISTS usuario;

CREATE TABLE usuario (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre           VARCHAR(120) NOT NULL,
    correo           VARCHAR(160) NOT NULL UNIQUE,
    contrasena_hash  VARCHAR(255) NOT NULL,
    rol              VARCHAR(20)  NOT NULL CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR', 'AUDITOR')),
    activo           BOOLEAN      NOT NULL DEFAULT 1,
    creado_en        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE token_revocado (
    jti        VARCHAR(64) PRIMARY KEY,
    expira_en  TIMESTAMP   NOT NULL
);

CREATE TABLE pais (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       VARCHAR(100) NOT NULL UNIQUE,
    codigo_iso2  CHAR(2)      NOT NULL UNIQUE CHECK (codigo_iso2 GLOB '[A-Z][A-Z]'),
    codigo_iso3  CHAR(3)      NOT NULL UNIQUE CHECK (codigo_iso3 GLOB '[A-Z][A-Z][A-Z]'),
    region       VARCHAR(80)  NOT NULL
);

CREATE TABLE producto (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          VARCHAR(40)    NOT NULL UNIQUE,
    nombre       VARCHAR(120)   NOT NULL,
    descripcion  TEXT,
    categoria    VARCHAR(20)    NOT NULL CHECK (categoria IN ('CAFE', 'CACAO')),
    precio       NUMERIC(12, 2) NOT NULL CHECK (precio >= 0),
    peso_kg      NUMERIC(10, 2) NOT NULL CHECK (peso_kg > 0),
    volumen_m3   NUMERIC(10, 3) NOT NULL CHECK (volumen_m3 > 0),
    activo       BOOLEAN        NOT NULL DEFAULT 1,
    creado_en    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id   INTEGER     NOT NULL UNIQUE REFERENCES producto (id) ON DELETE CASCADE,
    cantidad      INTEGER     NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    ubicacion     VARCHAR(80) NOT NULL DEFAULT 'Bodega principal',
    stock_minimo  INTEGER     NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0)
);

CREATE TABLE proveedor (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    nit                      VARCHAR(30)  NOT NULL UNIQUE,
    razon_social             VARCHAR(160) NOT NULL,
    pais_id                  INTEGER      NOT NULL REFERENCES pais (id),
    direccion                VARCHAR(200) NOT NULL,
    telefono                 VARCHAR(30)  NOT NULL,
    correo                   VARCHAR(160) NOT NULL,
    condiciones_comerciales  TEXT,
    creado_en                TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cliente (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_id             VARCHAR(40)  NOT NULL UNIQUE,
    razon_social       VARCHAR(160) NOT NULL,
    pais_id            INTEGER      NOT NULL REFERENCES pais (id),
    ciudad             VARCHAR(100) NOT NULL,
    direccion_entrega  VARCHAR(200) NOT NULL,
    contacto_compras   VARCHAR(120) NOT NULL,
    correo             VARCHAR(160),
    creado_en          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exportacion (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    consecutivo             VARCHAR(20)    NOT NULL UNIQUE,
    cliente_id              INTEGER        NOT NULL REFERENCES cliente (id),
    pais_destino_id         INTEGER        NOT NULL REFERENCES pais (id),
    puerto_salida           VARCHAR(120)   NOT NULL,
    incoterm                VARCHAR(3)     NOT NULL CHECK (incoterm IN ('FOB', 'CIF', 'EXW', 'DDP')),
    estado                  VARCHAR(20)    NOT NULL DEFAULT 'BORRADOR'
                            CHECK (estado IN ('BORRADOR', 'CONFIRMADA', 'EN_TRANSITO', 'ENTREGADA', 'CANCELADA')),
    impuestos               NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (impuestos >= 0),
    flete                   NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (flete >= 0),
    fecha_embarque          DATE,
    fecha_estimada_llegada  DATE,
    creado_por              INTEGER        REFERENCES usuario (id),
    creado_en               TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (fecha_embarque IS NULL OR fecha_estimada_llegada IS NULL
           OR fecha_estimada_llegada >= fecha_embarque)
);

CREATE TABLE detalle_exportacion (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    exportacion_id   INTEGER        NOT NULL REFERENCES exportacion (id) ON DELETE CASCADE,
    producto_id      INTEGER        NOT NULL REFERENCES producto (id),
    cantidad         INTEGER        NOT NULL CHECK (cantidad > 0),
    precio_unitario  NUMERIC(12, 2) NOT NULL CHECK (precio_unitario >= 0),
    subtotal         NUMERIC(14, 2) NOT NULL CHECK (subtotal >= 0),
    UNIQUE (exportacion_id, producto_id)
);

CREATE TABLE transporte (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    exportacion_id     INTEGER      NOT NULL UNIQUE REFERENCES exportacion (id) ON DELETE CASCADE,
    tipo               VARCHAR(20)  NOT NULL CHECK (tipo IN ('MARITIMO', 'AEREO', 'TERRESTRE', 'MULTIMODAL')),
    empresa            VARCHAR(120) NOT NULL,
    numero_guia        VARCHAR(60)  NOT NULL,
    numero_contenedor  VARCHAR(60)
);

CREATE TABLE movimiento_inventario (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id  INTEGER      NOT NULL REFERENCES producto (id) ON DELETE CASCADE,
    tipo         VARCHAR(10)  NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA', 'AJUSTE')),
    cantidad     INTEGER      NOT NULL CHECK (cantidad <> 0),
    motivo       VARCHAR(200) NOT NULL,
    fecha        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_id   INTEGER      REFERENCES usuario (id)
);
