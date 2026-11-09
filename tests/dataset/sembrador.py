"""Carga el paquete de datos del PIA en una base de datos real (la configurada en DATABASE_URL)."""
from __future__ import annotations

import csv
import pathlib

from fastapi.testclient import TestClient

from src.api.main import crear_app
from src.domain.value_objects import Placas

from .loader import Dataset
from .runner import EjecutorDataset


class YaCargado(Exception):
    """La base ya contiene los datos del paquete (las placas PIA-E001 existen)."""


def sembrar(contenedor, ds: Dataset) -> EjecutorDataset:
    with contenedor.uow_factory() as uow:
        if uow.vehiculos.buscar_por_placas(Placas("PIA-E001")):
            raise YaCargado("La base de datos ya contiene los datos del paquete PIA.")
    ejecutor = EjecutorDataset(TestClient(crear_app(contenedor)), contenedor, ds)
    ejecutor.preparar()
    return ejecutor


def escribir_mapa(ej: EjecutorDataset, ruta: pathlib.Path) -> int:
    """CSV con la equivalencia entre los IDs del paquete (AUT-…) y los IDs del sistema (ORD-…, CLI-…)."""
    filas = []
    for a in ej.ds.actores.values():
        filas.append(("cliente", a.actor_id, ej.cliente[a.actor_id], f"{a.nombre} · activo={int(a.activo)} · preferente={int(a.es_preferente)}"))
    for r in ej.ds.recursos.values():
        filas.append(("recurso", r.recurso_id, ej.recurso[r.recurso_id], f"{r.descripcion} · {r.precio} MXN · capacidad {r.capacidad}"))
    for op in ej.ds.operaciones.values():
        filas.append(("orden_evaluacion", op.operacion_id, ej.orden_eval[op.operacion_id],
                      f"{op.referencia} · cotizada{' y autorizada' if op.autorizado else ''} · {len(op.lineas)} líneas"
                      if op.lineas else f"{op.referencia} · sin detalle (queda en Recibido)"))
    for t in ej.ds.transiciones:
        filas.append(("orden_transicion", t["caso_id"], ej.orden_trans[t["caso_id"]],
                      f"{t['operacion_id']} · en Recibido, lista para probar «{t['accion_sugerida']}»"))
    filas.append(("tecnico", "—", ej.tecnico, "Técnico PIA (usar en diagnóstico y asignación)"))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tipo", "id_paquete", "id_sistema", "detalle"])
        w.writerows(filas)
    return len(filas)
