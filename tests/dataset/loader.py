"""Carga del paquete de datos del PIA (CSV UTF-8 con BOM) con importes en ``Decimal``."""
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DIR_DATOS = RAIZ / "data" / "pia"


@dataclass(frozen=True)
class Actor:
    actor_id: str
    nombre: str
    es_preferente: bool
    activo: bool
    ciudad: str


@dataclass(frozen=True)
class Recurso:
    recurso_id: str
    descripcion: str
    precio: Decimal
    capacidad: int
    habilitado: bool


@dataclass(frozen=True)
class Linea:
    recurso_id: str
    cantidad: int


@dataclass(frozen=True)
class Operacion:
    operacion_id: str
    actor_id: str
    estado_inicial: str
    fecha_solicitud: date
    promocion_activa: bool
    autorizado: bool
    referencia: str
    lineas: tuple[Linea, ...] = ()


@dataclass
class Dataset:
    actores: dict[str, Actor]
    recursos: dict[str, Recurso]
    operaciones: dict[str, Operacion]
    casos: list[dict]            # filas originales de casos_prueba.csv
    transiciones: list[dict]     # filas originales de transiciones_prueba.csv
    columnas_casos: list[str] = field(default_factory=list)
    columnas_transiciones: list[str] = field(default_factory=list)

    def total(self, op: Operacion | str) -> Decimal:
        """total = suma(precio_mxn × cantidad), con Decimal (INSTRUCCIONES, paso 3)."""
        op = self.operaciones[op] if isinstance(op, str) else op
        return sum((self.recursos[l.recurso_id].precio * l.cantidad for l in op.lineas), Decimal("0"))

    def integridad(self) -> dict[str, list[str]]:
        """Hallazgos de calidad de datos relevantes para las pruebas."""
        ops = self.operaciones.values()
        usados_deshabilitados = sorted({o.operacion_id for o in ops for l in o.lineas
                                        if not self.recursos[l.recurso_id].habilitado})
        return {
            "operaciones_sin_detalle": sorted(o.operacion_id for o in ops if not o.lineas),
            "operaciones_con_actor_inactivo": sorted(o.operacion_id for o in ops if not self.actores[o.actor_id].activo),
            "operaciones_sin_autorizacion": sorted(o.operacion_id for o in ops if not o.autorizado),
            "operaciones_con_promocion": sorted(o.operacion_id for o in ops if o.promocion_activa),
            "operaciones_con_recurso_deshabilitado": usados_deshabilitados,
            "operaciones_con_cantidad_sobre_capacidad": sorted(
                {o.operacion_id for o in ops for l in o.lineas if l.cantidad > self.recursos[l.recurso_id].capacidad}),
            "referencias_huerfanas": sorted(
                {o.operacion_id for o in ops if o.actor_id not in self.actores}
                | {o.operacion_id for o in ops for l in o.lineas if l.recurso_id not in self.recursos}),
        }


def _leer(ruta: pathlib.Path) -> tuple[list[str], list[dict]]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        return list(lector.fieldnames or []), list(lector)


def cargar(directorio: pathlib.Path = DIR_DATOS) -> Dataset:
    _, actores = _leer(directorio / "actores.csv")
    _, recursos = _leer(directorio / "catalogo.csv")
    _, ops = _leer(directorio / "operaciones.csv")
    _, det = _leer(directorio / "detalle_operaciones.csv")
    cols_c, casos = _leer(directorio / "casos_prueba.csv")
    cols_t, trans = _leer(directorio / "transiciones_prueba.csv")

    lineas: dict[str, list[Linea]] = {}
    for d in det:
        lineas.setdefault(d["operacion_id"], []).append(Linea(d["recurso_id"], int(d["cantidad"])))
    return Dataset(
        actores={a["actor_id"]: Actor(a["actor_id"], a["nombre"], a["es_preferente"] == "1", a["activo"] == "1",
                                      a["ciudad"]) for a in actores},
        recursos={r["recurso_id"]: Recurso(r["recurso_id"], r["descripcion"], Decimal(r["precio_mxn"]),
                                           int(r["capacidad_o_stock"]), r["habilitado"] == "1") for r in recursos},
        operaciones={o["operacion_id"]: Operacion(
            o["operacion_id"], o["actor_id"], o["estado_inicial"], date.fromisoformat(o["fecha_solicitud"]),
            o["promocion_activa"] == "1", o["autorizado"] == "1", o["referencia"],
            tuple(lineas.get(o["operacion_id"], ()))) for o in ops},
        casos=casos, transiciones=trans, columnas_casos=cols_c, columnas_transiciones=cols_t)
