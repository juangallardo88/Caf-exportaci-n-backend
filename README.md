# Café Exportación · Backend

API REST del **Sistema de Gestión Logística, Exportaciones y Control de Inventario** de RiTech SAS. Implementa las 30 historias de usuario del Product Backlog (HU-01 a HU-30).

- **Tecnología:** Python 3.12 · Flask · PyJWT · Pydantic · PostgreSQL (Neon) · pytest
- **Despliegue:** Render
- **Documentación de la API:** [`docs/API.md`](docs/API.md)

## Arquitectura

```
app/
├── __init__.py        Fábrica de la app: registra BD, errores, CORS y rutas
├── config.py          Configuración por variables de entorno
├── database.py        Conexión única para PostgreSQL y SQLite (consultas parametrizadas)
├── errors.py          Errores de negocio y respuestas de error centralizadas
├── security.py        Contraseñas cifradas, JWT y decorador de permisos por rol
├── domain/reglas.py   Reglas de negocio puras (estados, stock, totales, consecutivos)
├── schemas/           DTO de entrada validados con Pydantic
├── repositories/      Acceso a datos (única capa con SQL)
├── services/          Lógica de negocio por módulo
├── routes/            Controladores HTTP por módulo (blueprints)
└── cli.py             Comandos para crear la base local y cargar datos de demostración
tests/
├── unit/              Reglas, validaciones y seguridad, sin BD ni HTTP
└── integration/       La API completa contra una base de datos aislada
```

Una petición recorre **ruta → servicio → repositorio → base de datos**. Cada petición es una transacción: si algo falla, no queda nada a medias (por ejemplo, una confirmación que no alcanzó a descontar todo el inventario).

## Seguridad

- Contraseñas cifradas con PBKDF2-SHA256 (nunca en texto plano).
- JWT firmado con `SECRET_KEY`, con vencimiento. Al cerrar sesión el token queda revocado en la base.
- Permisos por rol en cada endpoint (ADMINISTRADOR, OPERADOR, AUDITOR).
- Validación de todos los datos de entrada; los campos desconocidos se rechazan.
- SQL siempre parametrizado (sin concatenar datos del usuario), lo que previene la inyección SQL.
- CORS limitado al dominio del frontend, más cabeceras de seguridad.
- Credenciales solo en variables de entorno. En producción la app no arranca sin `SECRET_KEY` segura ni PostgreSQL.

## Ejecutar en local

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
flask --app wsgi datos-demo     # crea instance/desarrollo.db con datos de ejemplo
flask --app wsgi run            # http://127.0.0.1:5000/api/salud
```

Usuarios de demostración: `admin@ritech.co / Admin123*`, `operador@ritech.co / Operador123*` y `auditor@ritech.co / Auditor123*`.

## Pruebas automatizadas

```bash
python -m pytest -v
```

| Tipo | Carpeta | Qué comprueba |
|---|---|---|
| Unitarias | `tests/unit` | Estados de exportación, cálculo de totales, consecutivos, movimientos de stock, validación de datos, contraseñas y tokens |
| Integración | `tests/integration` | Cada historia a través de la API: permisos por rol, registro y búsqueda, reglas de stock, máquina de estados, reportes CSV, CORS y manejo de errores |

**GitHub Actions** (`.github/workflows/pruebas.yml`) las ejecuta en cada push:
1. Todas las pruebas sobre SQLite. Genera `reporte-pruebas.xml`, que se descarga desde la ejecución.
2. Las pruebas de integración contra **PostgreSQL 16**, el mismo motor de Neon.

Los resultados están en la pestaña **Actions** del repositorio.

## Despliegue en Render

1. Carga `schema.sql` y `seed.sql` del repositorio de base de datos en Neon.
2. En Render: **New → Blueprint** y selecciona este repositorio. Usa `render.yaml`.
3. Completa las variables:
   - `DATABASE_URL`: cadena de conexión de Neon (`postgresql://…?sslmode=require`)
   - `CORS_ORIGINS`: URL del frontend en Vercel (por ejemplo `https://cafe-exportacion.vercel.app`)
   - `SECRET_KEY`: Render la genera sola
4. Verifica que `https://<servicio>.onrender.com/api/salud` responda `{"estado": "ok"}`.

> En el plan gratuito Render apaga el servicio tras 15 minutos sin uso; la primera petición puede tardar unos 50 segundos.
