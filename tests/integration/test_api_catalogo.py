"""Catálogo, validación de cantidades/capacidad, baja de clientes y evaluación de reglas por API."""
import pytest

ASESOR, TEC, CLI = ({"X-Rol": r} for r in ("asesor_servicio", "tecnico", "cliente"))
B = "/api/v1"


def _p(api, url, body, hdr, code):
    r = api.post(f"{B}{url}", json=body, headers=hdr)
    assert r.status_code == code, r.text
    return r.json()


@pytest.fixture
def mundo(api):
    cli = _p(api, "/clientes", {"nombre": "Ana", "telefono": "8112345678", "es_preferente": True}, ASESOR, 201)["id"]
    veh = _p(api, "/vehiculos", {"placas": "ABC-123", "marca": "N", "modelo": "V", "kilometraje": 0}, ASESOR, 201)["id"]
    tec = _p(api, "/tecnicos", {"nombre": "Luis", "especialidad": "x"}, ASESOR, 201)["id"]
    rec = _p(api, "/catalogo", {"descripcion": "Frenos 02", "precio_mxn": "430.00", "capacidad": 5}, ASESOR, 201)["id"]
    off = _p(api, "/catalogo", {"descripcion": "Afinación 11", "precio_mxn": "1069.00", "capacidad": 43, "habilitado": False}, ASESOR, 201)["id"]
    oid = _p(api, "/ordenes", {"cliente_id": cli, "vehiculo_id": veh, "kilometraje": 10, "combustible": "lleno",
                               "motivo_ingreso": "x", "promocion_activa": False}, ASESOR, 201)["id"]
    _p(api, f"/ordenes/{oid}/diagnostico", {"tecnico_id": tec, "hallazgos": ["x"]}, TEC, 200)
    return dict(cli=cli, tec=tec, rec=rec, off=off, oid=oid)


def _cotizar(api, m, conceptos, code):
    return api.post(f"{B}/ordenes/{m['oid']}/cotizacion", json={"conceptos": conceptos}, headers=ASESOR)


def test_catalogo_se_registra_y_se_consulta(api, mundo):
    cat = api.get(f"{B}/catalogo").json()
    assert {(i["descripcion"], i["capacidad"], i["habilitado"]) for i in cat} == {("Frenos 02", 5, True), ("Afinación 11", 43, False)}
    assert api.post(f"{B}/catalogo", json={"descripcion": "x", "precio_mxn": "1.00", "capacidad": 1}, headers=TEC).status_code == 403


def test_concepto_de_catalogo_usa_precio_oficial_y_cantidad_valida(api, mundo):
    r = _cotizar(api, mundo, [{"recurso_id": mundo["rec"], "cantidad": 2}], 201)
    assert r.status_code == 201
    c = r.json()["cotizacion"]["conceptos"][0]
    assert (c["descripcion"], c["precio_unitario"], c["importe"]) == ("Frenos 02", "430.00", "860.00")


@pytest.mark.parametrize("concepto, codigo, regla", [
    ({"recurso_id": "REC-NOEXISTE", "cantidad": 1}, 404, None),
    ({"recurso_id": "@OFF", "cantidad": 1}, 409, "CAT-01"),                 # deshabilitado
    ({"recurso_id": "@REC", "cantidad": 6}, 409, "CAT-02"),                 # excede capacidad (5)
    ({"recurso_id": "@REC", "cantidad": 0}, 422, None),                     # cantidad inválida
    ({"descripcion": "sin precio"}, 422, None),                             # ni catálogo ni precio
])
def test_validaciones_de_cantidades_y_disponibilidad(api, mundo, concepto, codigo, regla):
    concepto = {k: (mundo["rec"] if v == "@REC" else mundo["off"] if v == "@OFF" else v) for k, v in concepto.items()}
    r = _cotizar(api, mundo, [concepto], codigo)
    assert r.status_code == codigo, r.text
    if regla:
        assert r.json()["regla"] == regla
    assert api.get(f"{B}/ordenes/{mundo['oid']}").json()["estado"] == "Diagnosticado"      # sin cambios parciales


def test_baja_de_cliente_bloquea_ingresos_y_asignaciones(api, mundo):
    c = _cotizar(api, mundo, [{"recurso_id": mundo["rec"], "cantidad": 1}], 201).json()
    _p(api, f"/ordenes/{mundo['oid']}/cotizacion/respuesta",
       {"decisiones": {c["cotizacion"]["conceptos"][0]["id"]: True}}, CLI, 200)
    assert api.patch(f"{B}/clientes/{mundo['cli']}/estado", json={"activo": False}, headers=TEC).status_code == 403
    assert api.patch(f"{B}/clientes/{mundo['cli']}/estado", json={"activo": False}, headers=ASESOR).status_code == 204
    r = api.post(f"{B}/ordenes/{mundo['oid']}/trabajos", json={"tecnico_id": mundo["tec"]}, headers=ASESOR)
    assert r.status_code == 409 and r.json()["regla"] == "EXT-01"
    veh2 = _p(api, "/vehiculos", {"placas": "XYZ-999", "marca": "N", "modelo": "V", "kilometraje": 0}, ASESOR, 201)["id"]
    r = api.post(f"{B}/ordenes", json={"cliente_id": mundo["cli"], "vehiculo_id": veh2, "kilometraje": 1,
                                       "combustible": "lleno", "motivo_ingreso": "x"}, headers=ASESOR)
    assert r.status_code == 409
    assert api.patch(f"{B}/clientes/{mundo['cli']}/estado", json={"activo": True}, headers=ASESOR).status_code == 204
    assert api.post(f"{B}/ordenes/{mundo['oid']}/trabajos", json={"tecnico_id": mundo["tec"]}, headers=ASESOR).status_code == 200


def test_endpoint_de_evaluacion_con_criterios(api, mundo):
    ev = api.get(f"{B}/ordenes/{mundo['oid']}/evaluacion").json()
    assert ev["puede_procesarse"] is False and ev["criterios"]["autorizada"] is False and ev["total_referencia"] == "0.00"
    c = _cotizar(api, mundo, [{"recurso_id": mundo["rec"], "cantidad": 4}], 201).json()          # 4 × 430 = 1720
    _p(api, f"/ordenes/{mundo['oid']}/cotizacion/respuesta", {"decisiones": {c["cotizacion"]["conceptos"][0]["id"]: True}}, CLI, 200)
    ev = api.get(f"{B}/ordenes/{mundo['oid']}/evaluacion").json()
    assert ev["puede_procesarse"] and ev["beneficio_referencia"] and ev["total_referencia"] == "1720.00"
    assert api.get(f"{B}/ordenes/ORD-NOEXISTE/evaluacion").status_code == 404
