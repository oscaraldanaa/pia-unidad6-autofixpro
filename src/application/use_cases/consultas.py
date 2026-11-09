"""Casos de uso de lectura (CQRS ligero)."""
from __future__ import annotations

from ...domain.specifications import ContextoOperacion, beneficio_referencia, criterios, puede_procesarse
from ...domain.value_objects import OrdenServicioId, VehiculoId
from ..dto import EvaluacionOperacionDTO, OrdenDetalleDTO, OrdenResumenDTO, a_orden_dto
from .base import CasoDeUso


class ConsultarEstadoOrden(CasoDeUso):
    """US-12 / RF-12 / RN-02."""

    def ejecutar(self, orden_id: str) -> OrdenDetalleDTO:
        with self._uow_factory() as uow:
            return a_orden_dto(uow.ordenes.obtener(OrdenServicioId.desde_str(orden_id)))


class ConsultarHistorialVehiculo(CasoDeUso):
    def ejecutar(self, vehiculo_id: str) -> list[OrdenResumenDTO]:
        with self._uow_factory() as uow:
            vehiculo = uow.vehiculos.obtener(VehiculoId.desde_str(vehiculo_id))
            return [OrdenResumenDTO(str(o.id), o.estado.value, o.creada_en, o.datos_recepcion.motivo_ingreso)
                    for o in uow.ordenes.listar_por_vehiculo(vehiculo.id)]


class EvaluarOperacion(CasoDeUso):
    """Evalúa con Specifications compuestas (AND/OR/NOT) ``puede_procesarse`` y ``beneficio_referencia``."""

    def ejecutar(self, orden_id: str) -> EvaluacionOperacionDTO:
        with self._uow_factory() as uow:
            orden = uow.ordenes.obtener(OrdenServicioId.desde_str(orden_id))
            ctx = ContextoOperacion(uow.clientes.obtener(orden.cliente_id), orden)
            return EvaluacionOperacionDTO(
                orden_id=str(orden.id), cliente_id=str(orden.cliente_id), total_referencia=orden.total_referencia.monto,
                puede_procesarse=puede_procesarse().es_satisfecha_por(ctx),
                beneficio_referencia=beneficio_referencia().es_satisfecha_por(ctx), criterios=criterios(ctx))
