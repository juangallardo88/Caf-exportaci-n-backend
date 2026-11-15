"""Integración: dashboard, estadísticas, búsqueda y reportes (HU-27 a HU-30), más CORS y errores."""


def _exportacion_confirmada(client, admin, base, exportacion, cantidad=10):
    eid = exportacion["id"]
    client.put(f"/api/exportaciones/{eid}/costos", json={"impuestos": 100, "flete": 300}, headers=admin)
    client.post(f"/api/exportaciones/{eid}/productos",
                json={"producto_id": base["cafe"]["id"], "cantidad": cantidad}, headers=admin)
    client.patch(f"/api/exportaciones/{eid}/estado", json={"estado": "CONFIRMADA"}, headers=admin)


def test_dashboard_resume_exportaciones_e_inventario(client, admin, base, exportacion):  # HU-27
    _exportacion_confirmada(client, admin, base, exportacion)
    d = client.get("/api/dashboard", headers=admin).json
    assert d["exportaciones"]["total"] == 1 and d["exportaciones"]["activas"] == 1
    assert d["exportaciones"]["valor_exportado"] == 3200  # 10 x 280 + 100 + 300
    assert d["inventario"]["bajo_stock"] == 1 and d["clientes"] == 1


def test_borradores_no_suman_valor_exportado(client, admin, base, exportacion):  # HU-27
    client.post(f"/api/exportaciones/{exportacion['id']}/productos",
                json={"producto_id": base["cafe"]["id"], "cantidad": 10}, headers=admin)
    assert client.get("/api/dashboard", headers=admin).json["exportaciones"]["valor_exportado"] == 0


def test_estadisticas(client, admin, base, exportacion):  # HU-28
    _exportacion_confirmada(client, admin, base, exportacion)
    e = client.get("/api/estadisticas", headers=admin).json
    assert e["por_destino"][0] == {"pais": "Alemania", "cantidad": 1, "valor": 3200}
    assert e["top_productos"][0]["unidades"] == 10
    assert {c["categoria"] for c in e["inventario_por_categoria"]} == {"CAFE", "CACAO"}
    assert len(e["por_mes"]) == 1


def test_busqueda_global(client, admin, base, exportacion):  # HU-29
    r = client.get("/api/busqueda?q=hamburg", headers=admin).json
    assert len(r["clientes"]) == 1 and len(r["exportaciones"]) == 1 and r["productos"] == []


def test_busqueda_exige_dos_caracteres(client, admin):  # HU-29
    assert client.get("/api/busqueda?q=a", headers=admin).status_code == 400


def test_busqueda_no_interpreta_comodines(client, admin, base):  # HU-29
    assert client.get("/api/busqueda?q=%25%25", headers=admin).json["productos"] == []


def test_reporte_csv_de_exportaciones(client, admin, base, exportacion):  # HU-30
    _exportacion_confirmada(client, admin, base, exportacion)
    r = client.get("/api/reportes/exportaciones?estado=CONFIRMADA", headers=admin)
    assert r.status_code == 200 and r.mimetype == "text/csv"
    lineas = r.data.decode("utf-8-sig").splitlines()
    assert lineas[0].startswith("Consecutivo;Cliente")
    assert lineas[1].endswith(";3200,00") and len(lineas) == 2


def test_reporte_csv_de_inventario(client, auditor, base):  # HU-30
    lineas = client.get("/api/reportes/inventario", headers=auditor).data.decode("utf-8-sig").splitlines()
    assert len(lineas) == 3 and "BAJO" in lineas[1] + lineas[2]


def test_operador_no_genera_reportes(client, operador):  # HU-30 + HU-03
    assert client.get("/api/reportes/inventario", headers=operador).status_code == 403


def test_cors_permite_solo_el_frontend(client):
    permitido = client.get("/api/salud", headers={"Origin": "https://cafe-exportacion.vercel.app"})
    otro = client.get("/api/salud", headers={"Origin": "https://sitio-malicioso.com"})
    assert permitido.headers["Access-Control-Allow-Origin"] == "https://cafe-exportacion.vercel.app"
    assert "Access-Control-Allow-Origin" not in otro.headers


def test_json_invalido_da_error_claro(client, admin):
    r = client.post("/api/paises", data="no es json", headers={**admin, "Content-Type": "application/json"})
    assert r.status_code == 400 and r.json["error"]["codigo"] == "SOLICITUD_INVALIDA"


def test_ruta_inexistente(client):
    assert client.get("/api/no-existe").json["error"]["codigo"] == "HTTP_404"
