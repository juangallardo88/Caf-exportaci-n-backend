-- =====================================================================
-- Sistema de Gestión Logística, Exportaciones y Control de Inventario
-- RiTech SAS · Esquema PostgreSQL (Neon)
--
-- Ejecutar sobre una base vacía:  psql "$DATABASE_URL" -f schema.sql
-- El script es idempotente: borra y recrea todas las tablas.
-- =====================================================================

BEGIN;

DROP TABLE IF EXISTS token_revocado        CASCADE;
DROP TABLE IF EXISTS evento_exportacion    CASCADE;
DROP TABLE IF EXISTS movimiento_inventario CASCADE;
DROP TABLE IF EXISTS transporte            CASCADE;
DROP TABLE IF EXISTS detalle_exportacion   CASCADE;
DROP TABLE IF EXISTS exportacion           CASCADE;
DROP TABLE IF EXISTS inventario            CASCADE;
DROP TABLE IF EXISTS cliente               CASCADE;
DROP TABLE IF EXISTS proveedor             CASCADE;
DROP TABLE IF EXISTS producto              CASCADE;
DROP TABLE IF EXISTS pais                  CASCADE;
DROP TABLE IF EXISTS usuario               CASCADE;

-- ---------------------------------------------------------------------
-- USUARIO · HU-01, HU-02, HU-03 (autenticación y control de acceso RBAC)
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre           VARCHAR(120) NOT NULL,
    correo           VARCHAR(160) NOT NULL UNIQUE,
    contrasena_hash  VARCHAR(255) NOT NULL,
    rol              VARCHAR(20)  NOT NULL
                     CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR', 'AUDITOR')),
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tokens JWT invalidados al cerrar sesión (HU-02)
CREATE TABLE token_revocado (
    jti         VARCHAR(64) PRIMARY KEY,
    expira_en   TIMESTAMP   NOT NULL
);

-- ---------------------------------------------------------------------
-- PAIS · HU-16
-- ---------------------------------------------------------------------
CREATE TABLE pais (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL UNIQUE,
    codigo_iso2  CHAR(2)      NOT NULL UNIQUE CHECK (codigo_iso2 ~ '^[A-Z]{2}$'),
    codigo_iso3  CHAR(3)      NOT NULL UNIQUE CHECK (codigo_iso3 ~ '^[A-Z]{3}$'),
    region       VARCHAR(80)  NOT NULL
);

-- ---------------------------------------------------------------------
-- PRODUCTO · HU-04 a HU-08
-- (el stock vive en INVENTARIO para no duplicar la cantidad disponible)
-- ---------------------------------------------------------------------
CREATE TABLE producto (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku          VARCHAR(40)    NOT NULL UNIQUE,
    nombre       VARCHAR(120)   NOT NULL,
    descripcion  TEXT,
    categoria    VARCHAR(20)    NOT NULL CHECK (categoria IN ('CAFE', 'CACAO')),
    precio       NUMERIC(12, 2) NOT NULL CHECK (precio >= 0),
    peso_kg      NUMERIC(10, 2) NOT NULL CHECK (peso_kg > 0),
    volumen_m3   NUMERIC(10, 3) NOT NULL CHECK (volumen_m3 > 0),
    activo       BOOLEAN        NOT NULL DEFAULT TRUE,
    creado_en    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- INVENTARIO · HU-24, HU-25, HU-26 (1 a 1 con producto)
-- ---------------------------------------------------------------------
CREATE TABLE inventario (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id   INTEGER      NOT NULL UNIQUE REFERENCES producto (id) ON DELETE CASCADE,
    cantidad      INTEGER      NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    ubicacion     VARCHAR(80)  NOT NULL DEFAULT 'Bodega principal',
    stock_minimo  INTEGER      NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0)
);

-- ---------------------------------------------------------------------
-- PROVEEDOR · HU-09 a HU-12
-- ---------------------------------------------------------------------
CREATE TABLE proveedor (
    id                       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nit                      VARCHAR(30)  NOT NULL UNIQUE,
    razon_social             VARCHAR(160) NOT NULL,
    pais_id                  INTEGER      NOT NULL REFERENCES pais (id),
    direccion                VARCHAR(200) NOT NULL,
    telefono                 VARCHAR(30)  NOT NULL,
    correo                   VARCHAR(160) NOT NULL,
    condiciones_comerciales  TEXT,
    creado_en                TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- CLIENTE · HU-13 a HU-15 (nacionales e internacionales)
-- ---------------------------------------------------------------------
CREATE TABLE cliente (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tax_id             VARCHAR(40)  NOT NULL UNIQUE,
    razon_social       VARCHAR(160) NOT NULL,
    pais_id            INTEGER      NOT NULL REFERENCES pais (id),
    ciudad             VARCHAR(100) NOT NULL,
    direccion_entrega  VARCHAR(200) NOT NULL,
    contacto_compras   VARCHAR(120) NOT NULL,
    correo             VARCHAR(160),
    creado_en          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- EXPORTACION · HU-17 a HU-22
-- ---------------------------------------------------------------------
CREATE TABLE exportacion (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    CONSTRAINT fechas_en_orden CHECK (
        fecha_embarque IS NULL OR fecha_estimada_llegada IS NULL
        OR fecha_estimada_llegada >= fecha_embarque)
);

CREATE TABLE detalle_exportacion (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    exportacion_id   INTEGER        NOT NULL REFERENCES exportacion (id) ON DELETE CASCADE,
    producto_id      INTEGER        NOT NULL REFERENCES producto (id),
    cantidad         INTEGER        NOT NULL CHECK (cantidad > 0),
    precio_unitario  NUMERIC(12, 2) NOT NULL CHECK (precio_unitario >= 0),
    subtotal         NUMERIC(14, 2) NOT NULL CHECK (subtotal >= 0),
    UNIQUE (exportacion_id, producto_id)
);

-- ---------------------------------------------------------------------
-- TRANSPORTE · HU-23 (1 a 1 con exportación)
-- ---------------------------------------------------------------------
CREATE TABLE transporte (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    exportacion_id     INTEGER      NOT NULL UNIQUE REFERENCES exportacion (id) ON DELETE CASCADE,
    tipo               VARCHAR(20)  NOT NULL
                       CHECK (tipo IN ('MARITIMO', 'AEREO', 'TERRESTRE', 'MULTIMODAL')),
    empresa            VARCHAR(120) NOT NULL,
    numero_guia        VARCHAR(60)  NOT NULL,
    numero_contenedor  VARCHAR(60)
);

-- ---------------------------------------------------------------------
-- EVENTO_EXPORTACION · historial de cada exportación (quién hizo qué y cuándo)
-- ---------------------------------------------------------------------
CREATE TABLE evento_exportacion (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    exportacion_id  INTEGER      NOT NULL REFERENCES exportacion (id) ON DELETE CASCADE,
    tipo            VARCHAR(20)  NOT NULL
                    CHECK (tipo IN ('CREADA', 'PRODUCTOS', 'COSTOS', 'FECHAS', 'TRANSPORTE', 'ESTADO')),
    estado          VARCHAR(20)
                    CHECK (estado IS NULL OR estado IN ('BORRADOR', 'CONFIRMADA', 'EN_TRANSITO', 'ENTREGADA', 'CANCELADA')),
    descripcion     VARCHAR(300) NOT NULL,
    usuario_id      INTEGER      REFERENCES usuario (id),
    fecha           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- MOVIMIENTO_INVENTARIO · HU-25 (entradas, salidas y ajustes auditados)
-- ---------------------------------------------------------------------
CREATE TABLE movimiento_inventario (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id  INTEGER      NOT NULL REFERENCES producto (id) ON DELETE CASCADE,
    tipo         VARCHAR(10)  NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA', 'AJUSTE')),
    cantidad     INTEGER      NOT NULL CHECK (cantidad <> 0),
    motivo       VARCHAR(200) NOT NULL,
    fecha        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_id   INTEGER      REFERENCES usuario (id)
);

-- ---------------------------------------------------------------------
-- Índices para búsquedas y filtros (HU-10, HU-14, HU-19, HU-29)
-- ---------------------------------------------------------------------
CREATE INDEX idx_proveedor_pais        ON proveedor (pais_id);
CREATE INDEX idx_proveedor_razon       ON proveedor (LOWER(razon_social));
CREATE INDEX idx_cliente_pais          ON cliente (pais_id);
CREATE INDEX idx_cliente_razon         ON cliente (LOWER(razon_social));
CREATE INDEX idx_producto_nombre       ON producto (LOWER(nombre));
CREATE INDEX idx_exportacion_estado    ON exportacion (estado);
CREATE INDEX idx_exportacion_cliente   ON exportacion (cliente_id);
CREATE INDEX idx_exportacion_embarque  ON exportacion (fecha_embarque);
CREATE INDEX idx_detalle_producto      ON detalle_exportacion (producto_id);
CREATE INDEX idx_movimiento_producto   ON movimiento_inventario (producto_id, fecha);
CREATE INDEX idx_evento_exportacion   ON evento_exportacion (exportacion_id, fecha);

COMMIT;
