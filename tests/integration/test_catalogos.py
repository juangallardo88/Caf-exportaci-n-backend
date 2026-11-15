"""Integración: países, proveedores y clientes (HU-09 a HU-16)."""
from tests.conftest import PAIS_CO, PAIS_DE, cliente_valido, proveedor_valido


def _paises(client, admin):
    co = client.post("/api/paises", json=PAIS_CO, headers=admin).json
    de = client.post("/api/paises", json=PAIS_DE, headers=admin).json
    return co, de


# --- Países (HU-16) ---

def test_registrar_pais(client, admin):
    r = client.post("/api/paises", json={**PAIS_CO, "codigo_iso2": "co"}, headers=admin)
    assert r.status_code == 201 and r.json["codigo_iso2"] == "CO"


def test_pais_duplicado(client, admin):
    client.post("/api/paises", json=PAIS_CO, headers=admin)
    assert client.post("/api/paises", json=PAIS_CO, headers=admin).status_code == 409


# --- Proveedores (HU-09 a HU-12) ---

def test_registrar_proveedor(client, operador, admin):  # HU-09
    co, _ = _paises(client, admin)
    r = client.post("/api/proveedores", json=proveedor_valido(co["id"]), headers=operador)
    assert r.status_code == 201 and r.json["pais"] == "Colombia"


def test_nit_repetido_se_rechaza(client, admin):  # HU-09
    co, _ = _paises(client, admin)
    client.post("/api/proveedores", json=proveedor_valido(co["id"]), headers=admin)
    r = client.post("/api/proveedores", json=proveedor_valido(co["id"], razon_social="Otro"), headers=admin)
    assert r.status_code == 409 and "NIT" in r.json["error"]["mensaje"]


def test_proveedor_con_pais_inexistente(client, admin):
    r = client.post("/api/proveedores", json=proveedor_valido(999), headers=admin)
    assert r.status_code == 422


def test_consultar_proveedores_por_nombre_nit_y_pais(client, admin):  # HU-10
    co, de = _paises(client, admin)
    client.post("/api/proveedores", json=proveedor_valido(co["id"]), headers=admin)
    client.post("/api/proveedores", json=proveedor_valido(de["id"], nit="DE-998877", razon_social="Röstfabrik"),
                headers=admin)
    assert [p["nit"] for p in client.get("/api/proveedores?q=huila", headers=admin).json] == ["891100345-1"]
    assert len(client.get("/api/proveedores?q=998877", headers=admin).json) == 1
    assert len(client.get(f"/api/proveedores?pais_id={de['id']}", headers=admin).json) == 1


def test_editar_proveedor_y_validar_correo(client, admin):  # HU-11
    co, _ = _paises(client, admin)
    prov = client.post("/api/proveedores", json=proveedor_valido(co["id"]), headers=admin).json
    r = client.put(f"/api/proveedores/{prov['id']}",
                   json=proveedor_valido(co["id"], telefono="+57 300 111 2233"), headers=admin)
    assert r.status_code == 200 and r.json["telefono"] == "+57 300 111 2233"
    r = client.put(f"/api/proveedores/{prov['id']}", json=proveedor_valido(co["id"], correo="malo"), headers=admin)
    assert r.status_code == 422 and r.json["error"]["detalles"][0]["campo"] == "correo"


def test_eliminar_proveedor_y_no_aparece_en_busquedas(client, operador, admin):  # HU-12 + HU-10
    co, _ = _paises(client, admin)
    prov = client.post("/api/proveedores", json=proveedor_valido(co["id"]), headers=admin).json
    assert client.delete(f"/api/proveedores/{prov['id']}", headers=operador).status_code == 204
    assert client.get("/api/proveedores?q=huila", headers=admin).json == []
    assert client.get(f"/api/proveedores?pais_id={co['id']}", headers=admin).json == []


def test_eliminar_proveedor_inexistente(client, admin):  # HU-12
    r = client.delete("/api/proveedores/999", headers=admin)
    assert r.status_code == 404 and r.json["error"]["mensaje"] == "Proveedor no encontrado"


def test_auditor_no_elimina_proveedores(client, admin, auditor):
    co, _ = _paises(client, admin)
    prov = client.post("/api/proveedores", json=proveedor_valido(co["id"]), headers=admin).json
    assert client.delete(f"/api/proveedores/{prov['id']}", headers=auditor).status_code == 403


# --- Clientes (HU-13 a HU-15) ---

def test_registrar_cliente_internacional(client, admin):  # HU-13
    _, de = _paises(client, admin)
    r = client.post("/api/clientes", json=cliente_valido(de["id"]), headers=admin)
    assert r.status_code == 201 and r.json["pais"] == "Alemania"


def test_consultar_cliente_por_tax_id(client, admin):  # HU-14
    _, de = _paises(client, admin)
    client.post("/api/clientes", json=cliente_valido(de["id"]), headers=admin)
    assert client.get("/api/clientes?q=HRB-112233", headers=admin).json[0]["razon_social"].startswith("Hamburg")


def test_editar_cliente_y_ver_cambio_en_consulta(client, admin):  # HU-15 + HU-14
    _, de = _paises(client, admin)
    cli = client.post("/api/clientes", json=cliente_valido(de["id"]), headers=admin).json
    r = client.put(f"/api/clientes/{cli['id']}",
                   json=cliente_valido(de["id"], ciudad="Bremen", contacto_compras="Jonas Weber"), headers=admin)
    assert r.status_code == 200
    consultado = client.get(f"/api/clientes/{cli['id']}", headers=admin).json
    assert (consultado["ciudad"], consultado["contacto_compras"]) == ("Bremen", "Jonas Weber")


def test_editar_cliente_sin_razon_social(client, admin):  # HU-15
    _, de = _paises(client, admin)
    cli = client.post("/api/clientes", json=cliente_valido(de["id"]), headers=admin).json
    r = client.put(f"/api/clientes/{cli['id']}", json=cliente_valido(de["id"], razon_social=""), headers=admin)
    assert r.status_code == 422


def test_editar_cliente_con_tax_id_de_otro(client, admin):  # HU-15
    _, de = _paises(client, admin)
    client.post("/api/clientes", json=cliente_valido(de["id"]), headers=admin)
    otro = client.post("/api/clientes", json=cliente_valido(de["id"], tax_id="DE-HRB-445566",
                                                            razon_social="Berlin Coffee"), headers=admin).json
    r = client.put(f"/api/clientes/{otro['id']}", json=cliente_valido(de["id"]), headers=admin)
    assert r.status_code == 409 and "Tax ID" in r.json["error"]["mensaje"]
