"""Demo guiada del ciclo completo de AutoFix Pro contra la API en ejecución.

Uso:  python scripts/demo_flujo.py [--url http://localhost:8000] [--pausas]
"""
import argparse
import random
import string
import sys
from datetime import datetime, timedelta, timezone

import httpx

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://localhost:8000")
p.add_argument("--pausas", action="store_true", help="pausa para comentar cada paso en la defensa")
args = p.parse_args()
api = httpx.Client(base_url=args.url, timeout=15)
ROL = {"asesor": "asesor_servicio", "tecnico": "tecnico", "cliente": "cliente", "compras": "compras", "caja": "caja"}
B = "/api/v1"


def paso(titulo: str, regla: str = "") -> None:
    print(f"\n\033[1m▶ {titulo}\033[0m  {regla}")
    if args.pausas:
        input("   (Enter para ejecutar) ")


def llamar(metodo, url, rol=None, esperado=(200, 201), **kw):
    r = api.request(metodo, url, headers={"X-Rol": ROL[rol]} if rol else None, **kw)
    ok = r.status_code in esperado
    print(f"   {'✔' if ok else '✘'} {metodo} {url.replace(B, '')} -> {r.status_code}", end="")
    d = r.json() if r.content else {}
    if isinstance(d, dict) and "estado" in d and "id" in d:
        print(f"   estado: {d['estado']}", end="")
    if isinstance(d, dict) and "detalle" in d:
        print(f"   «{d['detalle']}»", end="")
    print()
    if not ok:
        sys.exit(f"Respuesta inesperada: {r.text}")
    return d


sufijo = "".join(random.choices(string.ascii_uppercase, k=3)) + "-" + "".join(random.choices(string.digits, k=3))
paso("0. Salud del servicio"); llamar("GET", "/health")

paso("1. Catálogos: cliente, vehículo y técnico", "(RN-10: medio digital de contacto)")
cli = llamar("POST", f"{B}/clientes", "asesor", json={"nombre": "Ana López", "telefono": "8112345678", "email": "ana@example.com"})["id"]
veh = llamar("POST", f"{B}/vehiculos", "asesor", json={"placas": sufijo, "marca": "Nissan", "modelo": "Versa", "kilometraje": 50000})["id"]
tec = llamar("POST", f"{B}/tecnicos", "asesor", json={"nombre": "Luis Pérez", "especialidad": "Frenos"})["id"]

paso("2. Recepción del vehículo y apertura de la OT", "(US-01 · RN-01)")
oid = llamar("POST", f"{B}/ordenes", "asesor", json={"cliente_id": cli, "vehiculo_id": veh, "kilometraje": 50120,
             "combustible": "1/2", "motivo_ingreso": "Ruido al frenar", "danos_visibles": ["Rayón en puerta derecha"]})["id"]

paso("3. Un técnico NO puede abrir órdenes → 403", "(RN-12: cinco roles)")
llamar("POST", f"{B}/ordenes", "tecnico", esperado=(403,), json={"cliente_id": cli, "vehiculo_id": veh, "kilometraje": 50200, "combustible": "lleno", "motivo_ingreso": "x"})

paso("4. Transición inválida: cotizar sin diagnóstico → 409", "(State Machine)")
llamar("POST", f"{B}/ordenes/{oid}/cotizacion", "asesor", esperado=(409,), json={"conceptos": [{"tipo": "mano_de_obra", "descripcion": "x", "precio_unitario": "1.00"}]})

paso("5. Diagnóstico del técnico", "(US-02)")
llamar("POST", f"{B}/ordenes/{oid}/diagnostico", "tecnico", json={"tecnico_id": tec, "hallazgos": ["Balatas gastadas", "Disco con desgaste leve"]})

paso("6. Cotización con mano de obra y refacciones", "(US-03 · RN-05)")
o = llamar("POST", f"{B}/ordenes/{oid}/cotizacion", "asesor", json={"conceptos": [
    {"tipo": "mano_de_obra", "descripcion": "Cambio de balatas", "precio_unitario": "500.00"},
    {"tipo": "refaccion", "descripcion": "Balatas delanteras", "precio_unitario": "800.50"},
    {"tipo": "refaccion", "descripcion": "Discos", "precio_unitario": "300.00"}]})
ids = {c["descripcion"]: c["id"] for c in o["cotizacion"]["conceptos"]}
print(f"   total cotizado: {o['cotizacion']['total']}")

paso("7. El cliente autoriza PARCIALMENTE (rechaza los discos)", "(US-04 · RN-05 · RN-11: IP/token + sello de tiempo)")
o = llamar("POST", f"{B}/ordenes/{oid}/cotizacion/respuesta", "cliente", json={"canal": "web", "decisiones": {
    ids["Cambio de balatas"]: True, ids["Balatas delanteras"]: True, ids["Discos"]: False}})
print(f"   total autorizado (lo único que se cobrará): {o['total_autorizado']}")

paso("8. Asignación de trabajos autorizados al técnico", "(US-05 · RN-13)")
llamar("POST", f"{B}/ordenes/{oid}/trabajos", "asesor", json={"tecnico_id": tec})

paso("9. Refacción sin existencia → solicitud a Compras", "(US-06 · RN-07)")
o = llamar("POST", f"{B}/ordenes/{oid}/refacciones-faltantes", "tecnico", json={"concepto_id": ids["Balatas delanteras"]})
sol = o["solicitudes_refaccion"][0]["id"]
paso("10. Compras informa el retraso → notificación automática al cliente (ver logs de la app)", "(US-07 · RN-03)")
llamar("PATCH", f"{B}/ordenes/{oid}/refacciones-faltantes/{sol}/reposicion", "compras", json={
    "nueva_fecha": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(), "motivo": "El proveedor retrasó la entrega"})
llamar("POST", f"{B}/ordenes/{oid}/refacciones-faltantes/{sol}/recepcion", "compras", json={})

paso("11. Fecha estimada: programar y luego cambiar con justificación", "(US-11 · RN-06)")
f1 = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(); f2 = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
llamar("PUT", f"{B}/ordenes/{oid}/fecha-entrega", "asesor", json={"fecha_estimada": f1})
o = llamar("PUT", f"{B}/ordenes/{oid}/fecha-entrega", "asesor", json={"fecha_estimada": f2, "justificacion": "Espera de refacción"})
print(f"   historial de fechas: {len(o['historial_fechas'])} cambio(s)")

paso("12. Falla adicional → cotización complementaria → autorización", "(US-08/09/10 · RN-04 · RN-13)")
o = llamar("POST", f"{B}/ordenes/{oid}/fallas-adicionales", "tecnico", json={"tecnico_id": tec, "descripcion": "Líquido de frenos contaminado"})
aid = o["solicitudes_ampliacion"][0]["id"]
o = llamar("POST", f"{B}/ordenes/{oid}/fallas-adicionales/{aid}/cotizacion", "asesor", json={"conceptos": [{"tipo": "mano_de_obra", "descripcion": "Cambio de líquido", "precio_unitario": "200.00"}]})
cid = o["solicitudes_ampliacion"][0]["cotizacion"]["conceptos"][0]["id"]
o = llamar("POST", f"{B}/ordenes/{oid}/fallas-adicionales/{aid}/respuesta", "cliente", json={"canal": "sms", "decisiones": {cid: True}})

paso("13. No se puede entregar sin revisión de calidad → 409", "(Specification OrdenListaParaEntregaSpec)")
llamar("POST", f"{B}/ordenes/{oid}/listo-para-entrega", "asesor", esperado=(409,))

paso("14. Finalizar y revisar cada trabajo; marcar lista para entrega", "(US-13/14)")
for t in o["trabajos"]:
    llamar("POST", f"{B}/ordenes/{oid}/trabajos/{t['id']}/finalizacion", "tecnico")
    llamar("POST", f"{B}/ordenes/{oid}/trabajos/{t['id']}/revision", "asesor")
o = llamar("POST", f"{B}/ordenes/{oid}/listo-para-entrega", "asesor")

paso("15. Caja: cobro incorrecto → 409; cobro exacto → Cerrado", "(US-15 · solo se cobra lo autorizado)")
llamar("POST", f"{B}/ordenes/{oid}/cobro", "caja", esperado=(409,), json={"monto": "1.00"})
o = llamar("POST", f"{B}/ordenes/{oid}/cobro", "caja", json={"monto": o["total_autorizado"]})

paso("16. Consulta pública del estado (portal del cliente, sin rol)", "(US-12 · RN-02)")
o = llamar("GET", f"{B}/ordenes/{oid}")
print(f"\n✅ Orden {oid} cerrada. Cobrado: {o['monto_cobrado']} · Trabajos: {len(o['trabajos'])} · Fechas modificadas: {len(o['historial_fechas'])}")
print(f"   Swagger UI: {args.url}/docs")
