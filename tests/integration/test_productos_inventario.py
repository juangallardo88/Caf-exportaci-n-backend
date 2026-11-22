"""Integración: productos (HU-04 a HU-08) e inventario (HU-24 a HU-26)."""
from tests.conftest import producto_valido


def test_registrar_producto_crea_inventario_y_movimiento(client, operador):  # HU-04
    r = client.post("/api/productos", json=producto_valido(), headers=operador)
    assert r.status_code == 201 and r.json["stock"] == 100
    movimientos = client.get(f"/api/inventario/movimientos?producto_id={r.json['id']}", headers=operador).json
    assert movimientos[0]["tipo"] == "ENTRADA" and movimientos[0]["cantidad"] == 100


def test_sku_duplicado(client, admin):  # HU-04
    client.post("/api/productos", json=producto_valido(), headers=admin)
    assert client.post("/api/productos", json=producto_valido(nombre="Otro"), headers=admin).status_code == 409


def test_consultar_y_filtrar_productos(client, admin, base):  # HU-05
    assert len(client.get("/api/productos", headers=admin).json) == 2
    assert [p["sku"] for p in client.get("/api/productos?categoria=CACAO", headers=admin).json] == ["CAC-FIN-60"]


def test_editar_producto(client, admin, base):  # HU-06
    datos = {k: v for k, v in producto_valido(precio=295).items()
             if k not in ("stock_inicial", "stock_minimo", "ubicacion")}
    r = client.put(f"/api/productos/{base['cafe']['id']}", json=datos, headers=admin)
    assert r.status_code == 200 and r.json["precio"] == 295


def test_eliminar_producto_lo_oculta(client, admin, base):  # HU-07
    assert client.delete(f"/api/productos/{base['cafe']['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/productos/{base['cafe']['id']}", headers=admin).status_code == 404
    assert len(client.get("/api/productos", headers=admin).json) == 1


def test_disponibilidad(client, admin, base):  # HU-08
    estados = {p["sku"]: p["estado_stock"] for p in client.get("/api/productos/disponibilidad", headers=admin).json}
    assert estados == {"CAF-SUP-70": "DISPONIBLE", "CAC-FIN-60": "BAJO"}


def test_consultar_inventario_de_un_producto(client, auditor, base):  # HU-24
    r = client.get(f"/api/inventario/{base['cafe']['id']}", headers=auditor)
    assert r.status_code == 200
    assert (r.json["cantidad"], r.json["ubicacion"], r.json["stock_minimo"]) == (100, "Bodega Buenaventura", 20)


def test_consultar_inventario_inexistente(client, admin):  # HU-24
    r = client.get("/api/inventario/999", headers=admin)
    assert r.status_code == 404 and r.json["error"]["mensaje"] == "Producto no encontrado"


def test_entrada_aumenta_el_inventario(client, operador, base):  # HU-25 + HU-24
    r = client.post("/api/inventario/movimientos", json={
        "producto_id": base["cafe"]["id"], "tipo": "ENTRADA", "cantidad": 50, "motivo": "Compra a cooperativa",
    }, headers=operador)
    assert r.status_code == 201 and r.json["cantidad"] == 150
    assert client.get(f"/api/inventario/{base['cafe']['id']}", headers=operador).json["cantidad"] == 150


def test_salida_mayor_al_stock_se_rechaza(client, operador, base):  # HU-25
    r = client.post("/api/inventario/movimientos", json={
        "producto_id": base["cacao"]["id"], "tipo": "SALIDA", "cantidad": 31, "motivo": "Despacho",
    }, headers=operador)
    assert r.status_code == 422 and "Stock insuficiente" in r.json["error"]["mensaje"]
    assert client.get(f"/api/inventario/{base['cacao']['id']}", headers=operador).json["cantidad"] == 30


def test_movimiento_queda_auditado_con_usuario(client, operador, base):  # HU-25
    client.post("/api/inventario/movimientos", json={
        "producto_id": base["cafe"]["id"], "tipo": "AJUSTE", "cantidad": -2, "motivo": "Merma por humedad",
    }, headers=operador)
    ultimo = client.get("/api/inventario/movimientos?limite=1", headers=operador).json[0]
    assert (ultimo["tipo"], ultimo["cantidad"], ultimo["usuario"]) == ("AJUSTE", -2, "Usuario Operador")


def test_productos_con_bajo_stock(client, admin, base):  # HU-26
    bajo = client.get("/api/inventario/bajo-stock", headers=admin).json
    assert [p["sku"] for p in bajo] == ["CAC-FIN-60"]


def test_cambiar_stock_minimo_actualiza_alerta(client, admin, base):  # HU-26
    client.put(f"/api/inventario/{base['cafe']['id']}", json={"ubicacion": "Bodega Cartagena", "stock_minimo": 150},
               headers=admin)
    assert len(client.get("/api/inventario/bajo-stock", headers=admin).json) == 2


def test_auditor_consulta_inventario_pero_no_lo_modifica(client, auditor, base):  # HU-24 + HU-03
    assert client.get("/api/inventario", headers=auditor).status_code == 200
    r = client.post("/api/inventario/movimientos", json={
        "producto_id": base["cafe"]["id"], "tipo": "ENTRADA", "cantidad": 5, "motivo": "Intento del auditor",
    }, headers=auditor)
    assert r.status_code == 403


# --- Proyección de agotamiento -----------------------------------------------------

def test_proyeccion_estima_dias_para_el_minimo(client, admin, base):
    # Café: 100 de stock, mínimo 20. Una salida de 45 hoy → 0,5 sacos/día en 90 días
    client.post("/api/inventario/movimientos", json={
        "producto_id": base["cafe"]["id"], "tipo": "SALIDA", "cantidad": 45, "motivo": "Venta nacional"},
        headers=admin)
    proyeccion = {p["sku"]: p for p in client.get("/api/inventario/proyeccion", headers=admin).json}
    cafe = proyeccion["CAF-SUP-70"]
    assert cafe["stock"] == 55 and cafe["consumo_diario"] == 0.5 and cafe["salidas_ventana"] == 45
    assert cafe["dias_para_minimo"] == 70 and cafe["dias_para_agotarse"] == 110
    assert cafe["nivel"] == "BAJA" and len(cafe["serie"]) == 91
    # Hace 90 días el producto no existía; hoy entró con 100 y salieron 45
    assert cafe["serie"][0]["stock"] == 0 and cafe["serie"][-1]["stock"] == 55
    # El cacao no tuvo salidas: no se puede proyectar
    assert proyeccion["CAC-FIN-60"]["nivel"] == "SIN_CONSUMO"


def test_proyeccion_ordena_de_lo_mas_urgente(client, admin, base):
    client.post("/api/inventario/movimientos", json={
        "producto_id": base["cacao"]["id"], "tipo": "SALIDA", "cantidad": 20, "motivo": "Muestras"}, headers=admin)
    client.post("/api/inventario/movimientos", json={
        "producto_id": base["cafe"]["id"], "tipo": "SALIDA", "cantidad": 10, "motivo": "Muestras"}, headers=admin)
    niveles = [(p["sku"], p["nivel"]) for p in client.get("/api/inventario/proyeccion", headers=admin).json]
    assert niveles == [("CAC-FIN-60", "ALTA"), ("CAF-SUP-70", "BAJA")]


def test_proyeccion_ventana_configurable_y_limitada(client, auditor, base):
    assert len(client.get("/api/inventario/proyeccion?dias=30", headers=auditor).json[0]["serie"]) == 31
    assert client.get("/api/inventario/proyeccion?dias=5000", headers=auditor).json[0]["dias_ventana"] == 365
