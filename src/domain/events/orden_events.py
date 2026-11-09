"""Eventos de dominio del agregado OrdenServicio (ver diagrama DDD)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..shared import DomainEvent
from ..value_objects import (
    ConceptoId, OrdenServicioId, SolicitudAmpliacionId, SolicitudRefaccionId, TecnicoId,
)


@dataclass(frozen=True, kw_only=True)
class OrdenEvent(DomainEvent):
    orden_id: OrdenServicioId


@dataclass(frozen=True, kw_only=True)
class OrdenRecibida(OrdenEvent):
    es_flotilla: bool


@dataclass(frozen=True, kw_only=True)
class DiagnosticoRegistrado(OrdenEvent):
    tecnico_id: TecnicoId


@dataclass(frozen=True, kw_only=True)
class CotizacionGenerada(OrdenEvent): ...


@dataclass(frozen=True, kw_only=True)
class CotizacionAutorizada(OrdenEvent): ...


@dataclass(frozen=True, kw_only=True)
class CotizacionParcialmenteAutorizada(OrdenEvent):
    conceptos_autorizados: tuple[ConceptoId, ...]
    conceptos_rechazados: tuple[ConceptoId, ...]


@dataclass(frozen=True, kw_only=True)
class CotizacionRechazada(OrdenEvent): ...


@dataclass(frozen=True, kw_only=True)
class TrabajosAsignados(OrdenEvent):
    tecnico_id: TecnicoId


@dataclass(frozen=True, kw_only=True)
class RefaccionSinExistencia(OrdenEvent):
    """RN-07: dispara la solicitud en la cola de trabajo de Compras."""

    solicitud_id: SolicitudRefaccionId


@dataclass(frozen=True, kw_only=True)
class RetrasoPorRefaccion(OrdenEvent):
    """RN-03: dispara la notificación automática al cliente."""

    solicitud_id: SolicitudRefaccionId
    motivo: str
    nueva_fecha_reposicion: datetime


@dataclass(frozen=True, kw_only=True)
class RefaccionRecibida(OrdenEvent):
    solicitud_id: SolicitudRefaccionId


@dataclass(frozen=True, kw_only=True)
class FallaAdicionalDetectada(OrdenEvent):
    solicitud_id: SolicitudAmpliacionId
    tecnico_id: TecnicoId


@dataclass(frozen=True, kw_only=True)
class CotizacionComplementariaEnviada(OrdenEvent):
    solicitud_id: SolicitudAmpliacionId


@dataclass(frozen=True, kw_only=True)
class AmpliacionResuelta(OrdenEvent):
    solicitud_id: SolicitudAmpliacionId
    resultado: str


@dataclass(frozen=True, kw_only=True)
class FechaModificada(OrdenEvent):
    anterior: datetime
    nueva: datetime
    justificacion: str


@dataclass(frozen=True, kw_only=True)
class OrdenListaParaEntrega(OrdenEvent): ...


@dataclass(frozen=True, kw_only=True)
class OrdenCerrada(OrdenEvent): ...


@dataclass(frozen=True, kw_only=True)
class EstadoOrdenCambiado(OrdenEvent):
    """Emitido por la State Machine en cada transición válida (auditoría RNF-01)."""

    anterior: str
    nuevo: str
    disparador: str


@dataclass(frozen=True, kw_only=True)
class OrdenCancelada(OrdenEvent):
    motivo: str
