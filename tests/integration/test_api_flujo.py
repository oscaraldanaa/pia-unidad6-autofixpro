"""API REST extremo a extremo: ciclo completo, roles, errores y auditoría."""
from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.builders import AHORA

ASESOR, TEC, CLI, COMPRAS, CAJA = ({"X-Rol": r} for r in ("asesor_servicio", "tecnico", "cliente", "compras", "caja"))
B = "/api/v1"


def _post(api, url, body, hdr, status=None):
    r = api.post(url, json=body, headers=hdr)
    if status:
        assert r.status_code == status, r.text
    return r


@pytest.fixture
def base(api):
    cli = _post(api, f"{B}/clientes", {"nombre": "Ana", "telefono": "8112345678", "email": "ana@mail.com"}, ASESOR, 201).json()["id"]
    veh = _post(api, f"{B}/vehiculos", {"placas": "ABC-123", "marca": "Nissan", "modelo": "Versa", "kilometraje": 50000}, ASESOR, 201).json()["id"]
    tec = _post(api, f"{B}/tecnicos", {"nombre": "Luis", "especialidad": "Frenos"}, ASESOR, 201).json()["id"]
    return cli, veh, tec


def _orden(api, base):
    cli, veh, _ = base
    return _post(api, f"{B}/ordenes", {"cliente_id": cli, "vehiculo_id": veh, "kilometraje": 50100,
                                       "combustible": "1/2", "motivo_ingreso": "Ruido al frenar",
                                       "danos_visibles": ["Rayón"]}, ASESOR, 201).json()


def _en_reparacion(api, base):
    _, _, tec = base
    o = _orden(api, base); oid = o["id"]
    _post(api, f"{B}/ordenes/{oid}/diagnostico", {"tecnico_id": tec, "hallazgos": ["Balatas gastadas"]}, TEC, 200)
    o = _post(api, f"{B}/ordenes/{oid}/cotizacion", {"conceptos": [
        {"tipo": "mano_de_obra", "descripcion": "Cambio de balatas", "precio_unitario": "500.00"},
        {"tipo": "refaccion", "descripcion": "Balatas", "precio_unitario": "800.50"},
        {"tipo": "refaccion", "descripcion": "Discos", "precio_unitario": "300.00"}]}, ASESOR, 201).json()
    ids = {c["descripcion"]: c["id"] for c in o["cotizacion"]["conceptos"]}
    o = _post(api, f"{B}/ordenes/{oid}/cotizacion/respuesta", {"decisiones": {
        ids["Cambio de balatas"]: True, ids["Balatas"]: True, ids["Discos"]: False}}, CLI, 200).json()
    o = _post(api, f"{B}/ordenes/{oid}/trabajos", {"tecnico_id": tec}, ASESOR, 200).json()
    return oid, ids, o


def test_ciclo_completo_hasta_cierre_con_notificaciones_y_auditoria(api, base, contenedor):
    cli, veh, tec = base
    oid, ids, o = _en_reparacion(api, base)
    assert o["estado"] == "En reparación" and o["total_autorizado"] == "1508.58"
    assert o["cotizacion"]["resultado"] == "parcial"

    # RN-07 / RN-03: refacción faltante → retraso notificado
    o = _post(api, f"{B}/ordenes/{oid}/refacciones-faltantes", {"concepto_id": ids["Balatas"]}, TEC, 201).json()
    assert o["estado"] == "En espera de refacción"
    sid = o["solicitudes_refaccion"][0]["id"]
    r = api.patch(f"{B}/ordenes/{oid}/refacciones-faltantes/{sid}/reposicion", headers=COMPRAS,
                  json={"nueva_fecha": (AHORA + timedelta(days=3)).isoformat(), "motivo": "Proveedor retrasó"})
    assert r.status_code == 200 and len(contenedor.notificador.enviados) == 1
    o = _post(api, f"{B}/ordenes/{oid}/refacciones-faltantes/{sid}/recepcion", {}, COMPRAS, 200).json()
    assert o["estado"] == "En reparación"

    # RN-06: fecha y cambio con justificación
    f1 = (AHORA + timedelta(days=30)).isoformat(); f2 = (AHORA + timedelta(days=35)).isoformat()
    assert api.put(f"{B}/ordenes/{oid}/fecha-entrega", json={"fecha_estimada": f1}, headers=ASESOR).status_code == 200
    r = api.put(f"{B}/ordenes/{oid}/fecha-entrega", json={"fecha_estimada": f2}, headers=ASESOR)
    assert r.status_code == 409 or r.status_code == 422                       # sin justificación
    r = api.put(f"{B}/ordenes/{oid}/fecha-entrega", json={"fecha_estimada": f2, "justificacion": "Espera"}, headers=ASESOR)
    assert r.status_code == 200 and len(r.json()["historial_fechas"]) == 1

    # RN-04: falla adicional
    o = _post(api, f"{B}/ordenes/{oid}/fallas-adicionales", {"tecnico_id": tec, "descripcion": "Líquido"}, TEC, 201).json()
    aid = o["solicitudes_ampliacion"][0]["id"]
    o = _post(api, f"{B}/ordenes/{oid}/fallas-adicionales/{aid}/cotizacion", {"conceptos": [
        {"tipo": "mano_de_obra", "descripcion": "Cambio líquido", "precio_unitario": "200.00"}]}, ASESOR, 201).json()
    cid = o["solicitudes_ampliacion"][0]["cotizacion"]["conceptos"][0]["id"]
    o = _post(api, f"{B}/ordenes/{oid}/fallas-adicionales/{aid}/respuesta", {"decisiones": {cid: True}, "canal": "sms"}, CLI, 200).json()
    assert len(o["trabajos"]) == 2 and o["total_autorizado"] == "1740.58"

    # RN-01/RF-14: no se puede entregar sin revisión
    assert api.post(f"{B}/ordenes/{oid}/listo-para-entrega", headers=ASESOR).status_code == 409
    for t in o["trabajos"]:
        _post(api, f"{B}/ordenes/{oid}/trabajos/{t['id']}/finalizacion", {}, TEC, 200)
        _post(api, f"{B}/ordenes/{oid}/trabajos/{t['id']}/revision", {}, ASESOR, 200)
    assert api.post(f"{B}/ordenes/{oid}/listo-para-entrega", headers=ASESOR).json()["estado"] == "Listo para entrega"

    # RF-15: cobro exacto
    assert api.post(f"{B}/ordenes/{oid}/cobro", json={"monto": "1.00"}, headers=CAJA).status_code == 409
    o = _post(api, f"{B}/ordenes/{oid}/cobro", {"monto": "1740.58"}, CAJA, 200).json()
    assert o["estado"] == "Cerrado" and o["monto_cobrado"] == "1740.58"

    # RN-02: consulta abierta + historial
    assert api.get(f"{B}/ordenes/{oid}").json()["estado"] == "Cerrado"
    assert [h["estado"] for h in api.get(f"{B}/vehiculos/{veh}/historial").json()] == ["Cerrado"]
    # RNF-01 / RN-11: auditoría y evidencia persistidas
    with contenedor.engine.connect() as cn:
        assert cn.execute(text("select count(*) from eventos_dominio where tipo='EstadoOrdenCambiado'")).scalar() >= 7
        ev = cn.execute(text("select ev_canal, ev_ip, ev_token from conceptos_cotizacion where ev_canal is not null")).all()
    assert ev and all(ip or tok for _, ip, tok in ev)           # siempre IP o token


def test_roles_rn12(api, base):
    cli, veh, _ = base
    body = {"cliente_id": cli, "vehiculo_id": veh, "kilometraje": 60000, "combustible": "lleno", "motivo_ingreso": "x"}
    assert api.post(f"{B}/ordenes", json=body).status_code == 401
    assert api.post(f"{B}/ordenes", json=body, headers={"X-Rol": "gerente"}).status_code == 401
    r = api.post(f"{B}/ordenes", json=body, headers=TEC)
    assert r.status_code == 403 and r.json()["regla"] == "RN-12"
    assert api.post(f"{B}/ordenes", json=body, headers=ASESOR).status_code == 201


def test_cliente_no_puede_cobrar_ni_caja_autorizar(api, base):
    oid, ids, _ = _en_reparacion(api, base)
    assert api.post(f"{B}/ordenes/{oid}/cobro", json={"monto": "1.00"}, headers=CLI).status_code == 403
    assert api.post(f"{B}/ordenes/{oid}/cotizacion/respuesta", json={"decisiones": {}}, headers=CAJA).status_code == 403


def test_errores_http(api, base):
    cli, veh, tec = base
    inexistente = "ORD-NOEXISTE"
    assert api.get(f"{B}/ordenes/{inexistente}").status_code == 404
    assert api.get(f"{B}/ordenes/{'x' * 40}").status_code == 422       # ID demasiado largo (ValorInvalido)
    o = _orden(api, base)
    r = api.post(f"{B}/ordenes/{o['id']}/cotizacion", headers=ASESOR,
                 json={"conceptos": [{"tipo": "refaccion", "descripcion": "x", "precio_unitario": "1.00"}]})
    assert r.status_code == 409 and "no es válido" in r.json()["detalle"]      # transición inválida
    assert api.post(f"{B}/ordenes", headers=ASESOR, json={"cliente_id": cli}).status_code == 422   # Pydantic
    assert api.post(f"{B}/clientes", headers=ASESOR, json={"nombre": "Sin contacto"}).status_code == 422  # RN-10
    assert api.post(f"{B}/vehiculos", headers=ASESOR, json={"placas": "ABC-123", "marca": "x", "modelo": "y", "kilometraje": 1}).status_code == 409
    assert api.get(f"{B}/vehiculos/{inexistente}/historial").status_code == 404


def test_rechazo_total_cancela_orden(api, base):
    _, _, tec = base
    oid = _orden(api, base)["id"]
    _post(api, f"{B}/ordenes/{oid}/diagnostico", {"tecnico_id": tec, "hallazgos": ["x"]}, TEC, 200)
    o = _post(api, f"{B}/ordenes/{oid}/cotizacion", {"conceptos": [
        {"tipo": "mano_de_obra", "descripcion": "mo", "precio_unitario": "10.00"}]}, ASESOR, 201).json()
    cid = o["cotizacion"]["conceptos"][0]["id"]
    o = _post(api, f"{B}/ordenes/{oid}/cotizacion/respuesta", {"decisiones": {cid: False}}, CLI, 200).json()
    assert o["estado"] == "Cancelado"
    assert api.post(f"{B}/ordenes/{oid}/cancelacion", json={"motivo": "x"}, headers=ASESOR).status_code == 409


def test_cancelacion_voluntaria(api, base):
    oid = _orden(api, base)["id"]
    assert api.post(f"{B}/ordenes/{oid}/cancelacion", json={"motivo": "Desistió"}, headers=ASESOR).json()["estado"] == "Cancelado"


def test_flotilla_reconocida_desde_el_ingreso(api):
    g = _post(api, f"{B}/clientes", {"nombre": "Gerente", "email": "g@flota.mx"}, ASESOR, 201).json()["id"]
    cuenta = _post(api, f"{B}/flotillas", {"razon_social": "Flota SA", "autorizador_corporativo_id": g,
                                          "descuento_pct": "10", "prioridad": 1, "dias_credito": 30}, ASESOR, 201).json()["id"]
    ch = _post(api, f"{B}/clientes", {"nombre": "Chofer", "telefono": "8111111111", "cuenta_flotilla_id": cuenta}, ASESOR, 201).json()["id"]
    v = _post(api, f"{B}/vehiculos", {"placas": "FLT-001", "marca": "Ford", "modelo": "Ranger", "kilometraje": 10,
                                      "cuenta_flotilla_id": cuenta}, ASESOR, 201).json()["id"]
    o = _post(api, f"{B}/ordenes", {"cliente_id": ch, "vehiculo_id": v, "kilometraje": 20, "combustible": "lleno",
                                    "motivo_ingreso": "Servicio"}, ASESOR, 201).json()
    assert o["es_flotilla"] and o["autorizador_id"] == g


def test_health_y_documentacion_openapi(api):
    assert api.get("/health").json()["estado"] == "ok"
    esquema = api.get("/openapi.json").json()
    assert esquema["info"]["title"] == "AutoFix Pro API" and len(esquema["paths"]) >= 20
    assert "/docs" in api.get("/docs").text or api.get("/docs").status_code == 200
    assert api.get("/redoc").status_code == 200
