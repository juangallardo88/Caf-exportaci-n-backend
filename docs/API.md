# API REST · Café Exportación

Base: `https://<tu-backend>.onrender.com/api` · Formato JSON · Autenticación con `Authorization: Bearer <token>`.

## Roles y permisos

| Acción | ADMINISTRADOR | OPERADOR | AUDITOR |
|---|:-:|:-:|:-:|
| Consultar cualquier módulo, dashboard y búsqueda | ✓ | ✓ | ✓ |
| Crear y editar productos, proveedores, clientes, exportaciones e inventario | ✓ | ✓ | — |
| Gestionar países y usuarios | ✓ | — | — |
| Descargar reportes CSV | ✓ | — | ✓ |

## Errores

Todas las respuestas de error tienen la misma forma:

```json
{ "error": { "codigo": "DATOS_INVALIDOS", "mensaje": "Revisa los datos enviados",
             "detalles": [{ "campo": "correo", "mensaje": "Correo electrónico inválido" }] } }
```

| Código HTTP | Cuándo |
|---|---|
| 400 | JSON mal formado o parámetro inválido |
| 401 | Sin sesión, token vencido, inválido o cerrado |
| 403 | El rol no tiene permiso |
| 404 | El recurso no existe |
| 409 | Dato único repetido (NIT, Tax ID, SKU, correo, país) |
| 422 | Datos inválidos o regla de negocio incumplida |

## Endpoints

### Autenticación y usuarios · HU-01 a HU-03
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | `{correo, contrasena}` → `{token, expira_en, usuario}` |
| POST | `/auth/logout` | Invalida el token actual |
| GET | `/auth/yo` | Usuario de la sesión |
| GET / POST | `/usuarios` | Listar / crear usuario `{nombre, correo, contrasena, rol}` (admin) |
| PATCH | `/usuarios/{id}` | Cambiar `rol` o `activo` (admin). Siempre queda al menos un administrador |

### Países · HU-16
| GET | `/paises` | Listar |
|---|---|---|
| POST / PUT | `/paises`, `/paises/{id}` | `{nombre, codigo_iso2, codigo_iso3, region}` (admin) |

### Productos · HU-04 a HU-08
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/productos?q=&categoria=` | Listar con stock y estado (`DISPONIBLE`, `BAJO`, `AGOTADO`) |
| GET | `/productos/disponibilidad?q=` | Disponibilidad de todos los productos (HU-08) |
| GET | `/productos/{id}` | Detalle |
| POST | `/productos` | `{sku, nombre, descripcion, categoria, precio, peso_kg, volumen_m3, stock_inicial, stock_minimo, ubicacion}` |
| PUT | `/productos/{id}` | Editar datos (el stock se cambia con movimientos) |
| DELETE | `/productos/{id}` | Baja lógica: conserva el historial |

### Proveedores · HU-09 a HU-12
| GET | `/proveedores?q=&pais_id=` | Buscar por nombre o NIT, filtrar por país |
|---|---|---|
| GET | `/proveedores/{id}` | Detalle |
| POST / PUT | `/proveedores`, `/proveedores/{id}` | `{nit, razon_social, pais_id, direccion, telefono, correo, condiciones_comerciales}` |
| DELETE | `/proveedores/{id}` | Eliminar |

### Clientes · HU-13 a HU-15
| GET | `/clientes?q=&pais_id=` | Buscar por nombre o Tax ID |
|---|---|---|
| GET | `/clientes/{id}` | Detalle |
| POST / PUT | `/clientes`, `/clientes/{id}` | `{tax_id, razon_social, pais_id, ciudad, direccion_entrega, contacto_compras, correo}` |

### Exportaciones · HU-17 a HU-23
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/exportaciones?estado=&desde=&hasta=&cliente_id=&q=` | Consultar y filtrar (fechas AAAA-MM-DD) |
| POST | `/exportaciones` | `{cliente_id, pais_destino_id, puerto_salida, incoterm}` → consecutivo `EXP-AAAA-NNNN` |
| GET | `/exportaciones/{id}` | Detalle con productos, transporte, totales y estados siguientes |
| GET | `/exportaciones/{id}/historial` | Línea de tiempo: `[{tipo, estado, descripcion, usuario, rol, fecha}]` (fecha en UTC) |
| PUT | `/exportaciones/{id}/costos` | `{impuestos, flete}` |
| POST | `/exportaciones/{id}/productos` | `{producto_id, cantidad}`; valida stock; solo en borrador |
| DELETE | `/exportaciones/{id}/productos/{detalle_id}` | Quitar producto (borrador) |
| PATCH | `/exportaciones/{id}/estado` | `{estado}` según la máquina de estados |
| PUT | `/exportaciones/{id}/fechas` | `{fecha_embarque, fecha_estimada_llegada}` (llegada ≥ embarque) |
| PUT | `/exportaciones/{id}/transporte` | `{tipo, empresa, numero_guia, numero_contenedor}` |

Máquina de estados: `BORRADOR → CONFIRMADA → EN_TRANSITO → ENTREGADA`, y `BORRADOR/CONFIRMADA → CANCELADA`.
- Confirmar exige al menos un producto y descuenta el inventario (movimientos de SALIDA).
- Pasar a tránsito exige el transporte registrado.
- Cancelar una exportación confirmada devuelve el inventario (movimientos de ENTRADA).
- Cada cambio (creación, productos, costos, fechas, transporte y estado) queda en el historial con el usuario y la hora, en la misma transacción: si el cambio se rechaza, no deja rastro.

### Inventario · HU-24 a HU-26
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/inventario?q=&bajo_stock=true` | Consultar |
| GET | `/inventario/bajo-stock` | Productos con cantidad ≤ stock mínimo |
| GET / PUT | `/inventario/{producto_id}` | Consultar / cambiar `{ubicacion, stock_minimo}` |
| GET | `/inventario/movimientos?producto_id=&limite=` | Historial auditado |
| GET | `/inventario/proyeccion?dias=90` | Proyección de agotamiento por producto (ventana de 30 a 365 días): consumo diario, días y fecha para el mínimo y para agotarse, nivel `AGOTADO/ALTA/MEDIA/BAJA/SIN_CONSUMO` y serie de stock |
| POST | `/inventario/movimientos` | `{producto_id, tipo: ENTRADA|SALIDA|AJUSTE, cantidad, motivo}` |

### Analítica · HU-27 a HU-30
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dashboard` | Indicadores de exportaciones e inventario y últimas exportaciones |
| GET | `/estadisticas` | Por mes, por destino, productos más exportados, inventario por categoría |
| GET | `/busqueda?q=` | Búsqueda global (mínimo 2 caracteres) |
| GET | `/reportes/exportaciones?estado=&desde=&hasta=` | CSV para Excel (admin y auditor) |
| GET | `/reportes/inventario` | CSV para Excel (admin y auditor) |
| GET | `/salud` | Estado del servicio (sin autenticación) |
