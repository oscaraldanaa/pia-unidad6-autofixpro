from __future__ import annotations

from datetime import datetime
from typing import Callable

from ...domain.entities import OrdenServicio
from ...domain.shared import utc_now
from ...domain.value_objects import (
    CanalAutorizacion, ConceptoId, EvidenciaAutorizacion, OrdenServicioId,
)
from ..dto import EvidenciaDTO, OrdenDetalleDTO, a_orden_dto
from ..ports import EventBus, UnitOfWork, UnitOfWorkFactory


class CasoDeUso:
    """Base: abre una Unit of Work por ejecución y publica los eventos tras el commit."""

    def __init__(self, uow_factory: UnitOfWorkFactory, bus: EventBus,
                 reloj: Callable[[], datetime] = utc_now) -> None:
        self._uow_factory = uow_factory
        self._bus = bus
        self._reloj = reloj

    def _sobre_orden(self, orden_id: str, accion: Callable[[OrdenServicio, UnitOfWork], None]) -> OrdenDetalleDTO:
        """Cargar agregado → ejecutar acción de dominio → guardar → commit → publicar eventos."""
        with self._uow_factory() as uow:
            orden = uow.ordenes.obtener(OrdenServicioId.desde_str(orden_id))
            accion(orden, uow)
            uow.ordenes.guardar(orden)
            eventos = orden.recolectar_eventos()
            dto = a_orden_dto(orden)
            uow.commit()
        self._bus.publicar(eventos)
        return dto

    def _evidencia(self, dto: EvidenciaDTO) -> EvidenciaAutorizacion:
        """RN-11: el sello de tiempo lo pone el servidor, no el cliente."""
        return EvidenciaAutorizacion(self._reloj(), CanalAutorizacion(dto.canal), dto.ip, dto.token_verificacion)


def decisiones_a_dominio(decisiones: dict[str, bool]) -> dict[ConceptoId, bool]:
    return {ConceptoId.desde_str(k): v for k, v in decisiones.items()}
