"""Ejecuta los 120 casos y las 20 transiciones del paquete contra la API real (TestClient).

Se siembra todo por HTTP con los roles del BRD; los IDs de los CSV (AUT-C001…) se mapean a los IDs
internos del sistema. Cada orden de evaluación y de transición es independiente."""
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass, field

from sqlalchemy import text

from . import oraculo
from .loader import Dataset, Operacion

B = "/api/v1"
ROL = {"asesor": "asesor_servicio", "tecnico": "tecnico", "cliente": "cliente", "caja": "caja"}


@dataclass
class ResultadoTransicion:
    fila: dict
    resultado: str
    estado_final: str
    pasos: list[str] = field(default_factory=list)
    detalle: str = ""
    eventos: str = ""
    esperado: oraculo.Esperado | None = None

    @property
    def coincide(self) -> bool:
        e = self.esperado
        return bool(e) and self.resultado == e.resultado and self.estado_final == e.estado_final \
            and (e.codigo_http is None or any(p.startswith(str(e.codigo_http)) for p in self.pasos))


class EjecutorDataset:
    def __init__(self, api, contenedor, ds: Dataset) -> None:
        self.api, self.c, self.ds = api, contenedor, ds
        self.cliente: dict[str, str] = {}
        self.recurso: dict[str, str] = {}
        self.orden_eval: dict[str, str] = {}
        self.orden_trans: dict[str, str] = {}
        self.tecnico = ""
        self._evaluaciones: dict[str, dict] = {}

    # ---------------------------------------------------------------- HTTP
    def _http(self, metodo: str, url: str, rol: str | None = None, **kw):
        r = self.api.request(metodo, f"{B}{url}", headers={"X-Rol": ROL[rol]} if rol else None, **kw)
        return r.status_code, (r.json() if r.content else {})

    def _ok(self, metodo: str, url: str, rol: str | None = None, **kw) -> dict:
        codigo, cuerpo = self._http(metodo, url, rol, **kw)
        assert codigo < 300, f"{metodo} {url} -> {codigo}: {cuerpo}"
        return cuerpo

    # ---------------------------------------------------------------- siembra
    def _abrir_orden(self, op: Operacion, etiqueta: str, num: int) -> str:
        veh = self._ok("POST", "/vehiculos", "asesor", json={
            "placas": f"PIA-{etiqueta}{num:03d}", "marca": "PIA", "modelo": "Dataset", "kilometraje": 0})["id"]
        return self._ok("POST", "/ordenes", "asesor", json={
            "cliente_id": self.cliente[op.actor_id], "vehiculo_id": veh, "kilometraje": 0, "combustible": "1/2",
            "motivo_ingreso": op.referencia, "promocion_activa": op.promocion_activa})["id"]

    def preparar(self) -> None:
        self.tecnico = self._ok("POST", "/tecnicos", "asesor", json={"nombre": "Técnico PIA", "especialidad": "General"})["id"]
        for r in self.ds.recursos.values():
            self.recurso[r.recurso_id] = self._ok("POST", "/catalogo", "asesor", json={
                "descripcion": r.descripcion, "precio_mxn": str(r.precio), "capacidad": r.capacidad,
                "habilitado": r.habilitado})["id"]
        for n, a in enumerate(self.ds.actores.values(), start=1):
            self.cliente[a.actor_id] = self._ok("POST", "/clientes", "asesor", json={
                "nombre": a.nombre, "telefono": f"81{n:09d}", "es_preferente": a.es_preferente})["id"]
        # 1) órdenes de evaluación (reglas compuestas): cotizadas y autorizadas según el CSV
        for op in self.ds.operaciones.values():
            oid = self.orden_eval[op.operacion_id] = self._abrir_orden(op, "E", int(op.operacion_id[-3:]))
            if not op.lineas:
                continue
            self._ok("POST", f"/ordenes/{oid}/diagnostico", "tecnico",
                     json={"tecnico_id": self.tecnico, "hallazgos": ["Diagnóstico del paquete PIA"]})
            o = self._ok("POST", f"/ordenes/{oid}/cotizacion", "asesor", json={"conceptos": [
                {"tipo": "mano_de_obra", "descripcion": self.ds.recursos[l.recurso_id].descripcion,
                 "precio_unitario": str(self.ds.recursos[l.recurso_id].precio), "cantidad": l.cantidad}
                for l in op.lineas]})
            if op.autorizado:
                self._ok("POST", f"/ordenes/{oid}/cotizacion/respuesta", "cliente",
                         json={"decisiones": {c["id"]: True for c in o["cotizacion"]["conceptos"]}})
        # 2) órdenes frescas en RECIBIDA para cada prueba de transición
        for t in self.ds.transiciones:
            op = self.ds.operaciones[t["operacion_id"]]
            self.orden_trans[t["caso_id"]] = self._abrir_orden(op, "S", int(t["caso_id"][-3:]))
        # 3) bajas de actores inactivos (después de abrir órdenes: un cliente inactivo no puede ingresar vehículos)
        for a in self.ds.actores.values():
            if not a.activo:
                code, _ = self._http("PATCH", f"/clientes/{self.cliente[a.actor_id]}/estado", "asesor", json={"activo": False})
                assert code == 204

    # ---------------------------------------------------------------- casos de regla
    def evaluacion(self, operacion_id: str) -> dict:
        if operacion_id not in self._evaluaciones:
            self._evaluaciones[operacion_id] = self._ok("GET", f"/ordenes/{self.orden_eval[operacion_id]}/evaluacion")
        return self._evaluaciones[operacion_id]

    def ejecutar_casos(self) -> list[dict]:
        filas = []
        for caso in self.ds.casos:
            op = self.ds.operaciones[caso["operacion_id"]]
            ev = self.evaluacion(op.operacion_id)
            if caso["tipo_prueba"] == "validar_operacion":
                valor, esperado = ev["puede_procesarse"], oraculo.puede_procesarse(self.ds, op)
                k = ev["criterios"]
                evidencia = (f"cliente_activo={int(k['cliente_activo'])}; con_detalle={int(k['con_detalle'])} "
                             f"({len(op.lineas)} líneas); autorizada={int(k['autorizada'])}")
            elif caso["tipo_prueba"] == "evaluar_beneficio":
                valor, esperado = ev["beneficio_referencia"], oraculo.beneficio_referencia(self.ds, op)
                k = ev["criterios"]
                evidencia = (f"cliente_preferente={int(k['cliente_preferente'])}; total={ev['total_referencia']} "
                             f"(>=1500: {int(k['total_minimo'])}); promocion_activa={int(k['promocion_activa'])}")
            else:
                raise ValueError(caso["tipo_prueba"])
            filas.append({**caso, "resultado_alumno": "VERDADERO" if valor else "FALSO",
                          "valor_oraculo": "VERDADERO" if esperado else "FALSO", "coincide": int(valor == esperado),
                          "evidencia": evidencia, "total_calculado_csv": str(self.ds.total(op)),
                          "orden_id_sistema": self.orden_eval[op.operacion_id], "http": 200})
        return filas

    # ---------------------------------------------------------------- transiciones
    def ejecutar_transiciones(self) -> list[ResultadoTransicion]:
        return [self._transicion(t) for t in self.ds.transiciones]

    def _transicion(self, t: dict) -> ResultadoTransicion:
        op, oid, accion = self.ds.operaciones[t["operacion_id"]], self.orden_trans[t["caso_id"]], t["accion_sugerida"]
        r = ResultadoTransicion(t, "EXITO", "", esperado=oraculo.transicion(self.ds, op, accion))

        def paso(nombre: str, metodo: str, url: str, rol: str, **kw) -> dict | None:
            codigo, cuerpo = self._http(metodo, f"/ordenes/{oid}{url}", rol, **kw)
            r.pasos.append(f"{codigo} {nombre}")
            if codigo >= 300:
                r.resultado = "RECHAZADA"
                r.detalle = f"{cuerpo.get('regla')}: {cuerpo.get('detalle')}"
                return None
            return cuerpo

        diag = {"tecnico_id": self.tecnico, "hallazgos": ["Diagnóstico del paquete PIA"]}
        if accion == "aprobar":
            paso("diagnosticar", "POST", "/diagnostico", "tecnico", json=diag)
        elif accion == "repetir_aprobacion":
            paso("diagnosticar", "POST", "/diagnostico", "tecnico", json=diag) and \
                paso("diagnosticar (repetido)", "POST", "/diagnostico", "tecnico", json=diag)
        elif accion == "saltar_estado":
            paso("cobro prematuro", "POST", "/cobro", "caja", json={"monto": "1.00"})
        elif accion == "cancelar":
            paso("cancelar", "POST", "/cancelacion", "asesor", json={"motivo": "Cancelación solicitada por el paquete PIA"})
        elif accion == "completar":
            self._completar(op, paso, diag)
        else:
            raise ValueError(accion)
        r.estado_final = oraculo.ESTADOS[self._ok("GET", f"/ordenes/{oid}")["estado"]]
        with self.c.engine.connect() as cn:
            r.eventos = ",".join(cn.execute(text(
                "SELECT tipo FROM eventos_dominio WHERE orden_id=:o ORDER BY ocurrido_en, id"), {"o": oid}).scalars())
        return r

    def _completar(self, op: Operacion, paso, diag: dict) -> None:
        if not paso("diagnosticar", "POST", "/diagnostico", "tecnico", json=diag):
            return
        o = paso("cotizar", "POST", "/cotizacion", "asesor", json={"conceptos": [
            {"tipo": "mano_de_obra", "recurso_id": self.recurso[l.recurso_id], "cantidad": l.cantidad}
            for l in op.lineas]})
        if o is None:
            return
        if op.autorizado:     # sin autorización en el CSV no se registra respuesta del cliente
            if not paso("autorizar", "POST", "/cotizacion/respuesta", "cliente",
                        json={"decisiones": {c["id"]: True for c in o["cotizacion"]["conceptos"]}}):
                return
        o = paso("asignar", "POST", "/trabajos", "asesor", json={"tecnico_id": self.tecnico})
        if o is None:
            return
        for tr in o["trabajos"]:
            if not (paso("finalizar", "POST", f"/trabajos/{tr['id']}/finalizacion", "tecnico")
                    and paso("revisar", "POST", f"/trabajos/{tr['id']}/revision", "asesor")):
                return
        o = paso("listo para entrega", "POST", "/listo-para-entrega", "asesor")
        if o:
            paso("cobrar", "POST", "/cobro", "caja", json={"monto": o["total_autorizado"]})

    # ---------------------------------------------------------------- salida
    def escribir(self, destino: pathlib.Path, casos: list[dict], trans: list[ResultadoTransicion]) -> None:
        destino.mkdir(parents=True, exist_ok=True)
        extra_c = ["valor_oraculo", "coincide", "evidencia", "total_calculado_csv", "orden_id_sistema", "http"]
        _escribir(destino / "casos_prueba_resultados.csv", self.ds.columnas_casos + extra_c, casos)
        filas = [{**x.fila, "resultado_alumno": x.resultado, "estado_final": x.estado_final,
                  "estado_final_esperado": x.esperado.estado_final, "resultado_esperado": x.esperado.resultado,
                  "coincide": int(x.coincide), "pasos_http": " | ".join(x.pasos), "excepcion": x.detalle,
                  "eventos_dominio": x.eventos} for x in trans]
        extra_t = ["estado_final", "estado_final_esperado", "resultado_esperado", "coincide", "pasos_http",
                   "excepcion", "eventos_dominio"]
        _escribir(destino / "transiciones_prueba_resultados.csv", self.ds.columnas_transiciones + extra_t, filas)


def _escribir(ruta: pathlib.Path, columnas: list[str], filas: list[dict]) -> None:
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
