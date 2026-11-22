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


# --- Historial de la exportación ---------------------------------------------------

def test_historial_registra_cada_paso_con_su_usuario(client, admin, operador, base, exportacion):
    eid = exportacion["id"]
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 10},
                headers=operador)
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cafe"]["id"], "cantidad": 5},
                headers=operador)
    client.put(f"/api/exportaciones/{eid}/costos", json={"impuestos": 500, "flete": 1200.5}, headers=operador)
    client.put(f"/api/exportaciones/{eid}/fechas",
               json={"fecha_embarque": "2026-12-01", "fecha_estimada_llegada": "2026-12-28"}, headers=operador)
    client.put(f"/api/exportaciones/{eid}/transporte", json=TRANSPORTE, headers=operador)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "EN_TRANSITO"}, headers=operador)

    eventos = client.get(f"/api/exportaciones/{eid}/historial", headers=admin).json
    assert [e["tipo"] for e in eventos] == ["CREADA", "PRODUCTOS", "PRODUCTOS", "COSTOS", "FECHAS", "TRANSPORTE",
                                            "ESTADO", "ESTADO"]
    textos = [e["descripcion"] for e in eventos]
    assert textos[0].startswith(f"Creó la exportación {exportacion['consecutivo']}")
    assert textos[1] == "Agregó 10 sacos de Café Excelso Supremo a US$ 280,00 c/u"
    assert textos[2] == "Sumó 5 sacos de Café Excelso Supremo (ahora 15 sacos)"
    assert textos[3] == "Actualizó los costos: impuestos US$ 500,00 · flete US$ 1.200,50"
    assert textos[4] == "Registró las fechas: embarque 01/12/2026 · llegada estimada 28/12/2026"
    assert textos[5] == "Registró el transporte: Marítimo · Maersk · guía MAEU-CTG-221907 · contenedor MSKU 778120-5"
    assert textos[6] == "Confirmó la exportación: se descontaron 15 sacos del inventario"
    assert [e["estado"] for e in eventos if e["tipo"] == "ESTADO"] == ["CONFIRMADA", "EN_TRANSITO"]
    assert eventos[0]["usuario"] == "Usuario Administrador"  # la creó el admin (fixture)
    assert eventos[1]["usuario"] == "Usuario Operador" and eventos[6]["usuario"] == "Usuario Administrador"
    assert all(e["fecha"] for e in eventos)


def test_historial_registra_quitar_producto_y_cancelacion_con_devolucion(client, admin, base, exportacion):
    eid = exportacion["id"]
    detalle = client.post(f"/api/exportaciones/{eid}/productos",
                          json={"producto_id": base["cafe"]["id"], "cantidad": 4}, headers=admin).json
    client.post(f"/api/exportaciones/{eid}/productos", json={"producto_id": base["cacao"]["id"], "cantidad": 2},
                headers=admin)
    linea_cacao = next(p for p in client.get(f"/api/exportaciones/{eid}", headers=admin).json["productos"]
                       if p["sku"] == "CAC-FIN-60")
    client.delete(f"/api/exportaciones/{eid}/productos/{linea_cacao['id']}", headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CANCELADA"}, headers=admin)
    textos = [e["descripcion"] for e in client.get(f"/api/exportaciones/{eid}/historial", headers=admin).json]
    assert "Quitó Cacao Fino de Aroma (2 sacos)" in textos
    assert textos[-1] == "Canceló la exportación: se devolvieron 4 sacos al inventario"
    assert detalle["total"] > 0


def test_un_cambio_rechazado_no_deja_rastro_en_el_historial(client, admin, base, exportacion):
    eid = exportacion["id"]
    r = client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)
    assert r.status_code == 422  # sin productos no se puede confirmar
    assert [e["tipo"] for e in client.get(f"/api/exportaciones/{eid}/historial", headers=admin).json] == ["CREADA"]


def test_el_auditor_consulta_el_historial(client, auditor, exportacion):
    r = client.get(f"/api/exportaciones/{exportacion['id']}/historial", headers=auditor)
    assert r.status_code == 200 and len(r.json) == 1


def test_historial_de_exportacion_inexistente(client, admin):
    assert client.get("/api/exportaciones/999/historial", headers=admin).status_code == 404


def test_historial_requiere_sesion(client, exportacion):
    assert client.get(f"/api/exportaciones/{exportacion['id']}/historial").status_code == 401
