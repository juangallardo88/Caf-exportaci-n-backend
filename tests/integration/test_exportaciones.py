"""Integración: exportaciones, detalle, estados, fechas y transporte (HU-17 a HU-23)."""

TRANSPORTE = {"tipo": "MARITIMO", "empresa": "Maersk", "numero_guia": "MAEU-CTG-221907",
              "numero_contenedor": "MSKU 778120-5"}


def _stock(client, headers, producto_id):
    return client.get(f"/api/inventario/{producto_id}", headers=headers).json["cantidad"]


def test_crear_exportacion_con_consecutivo(client, admin, exportacion):  # HU-17
    assert exportacion["consecutivo"].startswith("EXP-") and exportacion["consecutivo"].endswith("-0001")
    assert exportacion["estado"] == "BORRADOR" and exportacion["total"] == 0


def test_consecutivos_no_se_repiten(client, admin, base, exportacion):  # HU-17
    segunda = client.post("/api/exportaciones", json={
        "cliente_id": base["cliente"]["id"], "pais_destino_id": base["de"]["id"],
        "puerto_salida": "Cartagena", "incoterm": "CIF"}, headers=admin).json
    assert segunda["consecutivo"].endswith("-0002")


def test_incoterm_invalido(client, admin, base):  # HU-17
    r = client.post("/api/exportaciones", json={
        "cliente_id": base["cliente"]["id"], "pais_destino_id": base["de"]["id"],
        "puerto_salida": "Cartagena", "incoterm": "XYZ"}, headers=admin)
    assert r.status_code == 422


def test_agregar_producto_calcula_totales(client, admin, base, exportacion):  # HU-18
    eid = exportacion["id"]
    client.put(f"/api/exportaciones/{eid}/costos", json={"impuestos": 500, "flete": 1200}, headers=admin)
    r = client.post(f"/api/exportaciones/{eid}/productos",
                    json={"producto_id": base["cafe"]["id"], "cantidad": 10}, headers=admin)
    assert r.status_code == 201
    assert (r.json["subtotal"], r.json["total"]) == (2800, 4500)


def test_agregar_mas_del_stock_disponible(client, admin, base, exportacion):  # HU-18
    r = client.post(f"/api/exportaciones/{exportacion['id']}/productos",
                    json={"producto_id": base["cacao"]["id"], "cantidad": 31}, headers=admin)
    assert r.status_code == 422 and "Stock insuficiente" in r.json["error"]["mensaje"]


def test_agregar_el_mismo_producto_suma_cantidades(client, admin, base, exportacion):  # HU-18
    url = f"/api/exportaciones/{exportacion['id']}/productos"
    client.post(url, json={"producto_id": base["cafe"]["id"], "cantidad": 10}, headers=admin)
    r = client.post(url, json={"producto_id": base["cafe"]["id"], "cantidad": 5}, headers=admin)
    assert len(r.json["productos"]) == 1 and r.json["productos"][0]["cantidad"] == 15


def test_consultar_exportaciones_por_estado(client, admin, exportacion):  # HU-19
    assert len(client.get("/api/exportaciones?estado=BORRADOR", headers=admin).json) == 1
    assert client.get("/api/exportaciones?estado=ENTREGADA", headers=admin).json == []


def test_ver_detalle_con_productos_y_transporte(client, admin, base, exportacion):  # HU-20 + HU-18 + HU-23
    eid = exportacion["id"]
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 4},
                headers=admin)
    client.put(f"/api/exportaciones/{eid}/transporte", json=TRANSPORTE, headers=admin)
    d = client.get(f"/api/exportaciones/{eid}", headers=admin).json
    assert d["cliente"] == "Hamburg Kaffee Import GmbH" and d["pais_destino"] == "Alemania"
    assert d["productos"][0]["subtotal"] == 1120 and d["transporte"]["empresa"] == "Maersk"
    assert d["estados_siguientes"] == ["CANCELADA", "CONFIRMADA"]


def test_ver_exportacion_inexistente(client, admin):  # HU-20
    r = client.get("/api/exportaciones/999", headers=admin)
    assert r.status_code == 404 and r.json["error"]["mensaje"] == "Exportación no encontrada"


def test_confirmar_descuenta_inventario(client, admin, base, exportacion):  # HU-21 + HU-25
    eid = exportacion["id"]
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 40},
                headers=admin)
    r = client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    assert r.status_code == 200 and r.json["estado"] == "CONFIRMADA"
    assert _stock(client, admin, base["cafe"]["id"]) == 60


def test_confirmar_sin_productos(client, admin, exportacion):  # HU-21
    r = client.patch(f"/api/exportaciones/{exportacion['id']}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    assert r.status_code == 422


def test_transicion_invalida(client, admin, exportacion):  # HU-21
    r = client.patch(f"/api/exportaciones/{exportacion['id']}/estado", json={"estado": "ENTREGADA"}, headers=admin)
    assert r.status_code == 422 and "No se puede pasar" in r.json["error"]["mensaje"]


def test_en_transito_exige_transporte(client, admin, base, exportacion):  # HU-21 + HU-23
    eid = exportacion["id"]
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 1},
                headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    assert client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "EN_TRANSITO"},
                        headers=admin).status_code == 422
    client.put(f"/api/exportaciones/{eid}/transporte", json=TRANSPORTE, headers=admin)
    assert client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "EN_TRANSITO"},
                        headers=admin).json["estado"] == "EN_TRANSITO"


def test_cancelar_confirmada_devuelve_inventario(client, admin, base, exportacion):  # HU-21 + HU-25
    eid = exportacion["id"]
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 40},
                headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CANCELADA"}, headers=admin)
    assert _stock(client, admin, base["cafe"]["id"]) == 100


def test_no_se_modifican_productos_despues_de_confirmar(client, admin, base, exportacion):  # HU-18 + HU-21
    eid = exportacion["id"]
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 1},
                headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    r = client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 1},
                    headers=admin)
    assert r.status_code == 422


def test_registrar_fechas_validas(client, admin, exportacion):  # HU-22
    r = client.put(f"/api/exportaciones/{exportacion['id']}/fechas",
                   json={"fecha_embarque": "2026-11-25", "fecha_estimada_llegada": "2026-12-16"}, headers=admin)
    assert r.status_code == 200
    assert (r.json["fecha_embarque"], r.json["fecha_estimada_llegada"]) == ("2026-11-25", "2026-12-16")


def test_fecha_de_llegada_anterior_al_embarque(client, admin, exportacion):  # HU-22
    r = client.put(f"/api/exportaciones/{exportacion['id']}/fechas",
                   json={"fecha_embarque": "2026-12-10", "fecha_estimada_llegada": "2026-12-01"}, headers=admin)
    assert r.status_code == 422 and "anterior" in r.json["error"]["detalles"][0]["mensaje"]


def test_fecha_inexistente(client, admin, exportacion):  # HU-22
    r = client.put(f"/api/exportaciones/{exportacion['id']}/fechas",
                   json={"fecha_embarque": "2026-02-31", "fecha_estimada_llegada": "2026-03-10"}, headers=admin)
    assert r.status_code == 422


def test_filtrar_exportaciones_por_rango_de_fechas(client, admin, exportacion):  # HU-22 + HU-19
    client.put(f"/api/exportaciones/{exportacion['id']}/fechas",
               json={"fecha_embarque": "2026-11-25", "fecha_estimada_llegada": "2026-12-16"}, headers=admin)
    dentro = client.get("/api/exportaciones?desde=2026-11-01&hasta=2026-11-30", headers=admin).json
    fuera = client.get("/api/exportaciones?desde=2026-12-01&hasta=2026-12-31", headers=admin).json
    assert len(dentro) == 1 and fuera == []


def test_registrar_transporte_sin_empresa(client, admin, exportacion):  # HU-23
    r = client.put(f"/api/exportaciones/{exportacion['id']}/transporte",
                   json={**TRANSPORTE, "empresa": ""}, headers=admin)
    assert r.status_code == 422
