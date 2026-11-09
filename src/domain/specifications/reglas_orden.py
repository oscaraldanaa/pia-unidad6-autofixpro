"""Especificaciones sobre el agregado OrdenServicio.

Se tipan con ``Any``/duck typing sobre propiedades públicas para evitar una
importación circular con el agregado (que usa estas specs en su State Machine).
"""
from __future__ import annotations

from typing import Any

from .base import Specification


class TieneTrabajosSpec(Specification[Any]):
    def es_satisfecha_por(self, orden: Any) -> bool:
        return len(orden.trabajos) > 0


class TodosTrabajosRevisadosSpec(Specification[Any]):
    """Control de calidad completo (US-14)."""

    def es_satisfecha_por(self, orden: Any) -> bool:
        from ..entities.trabajo_reparacion import EstadoTrabajo  # import diferido (evita ciclo)

        return all(t.estado is EstadoTrabajo.REVISADO for t in orden.trabajos)


class SinAmpliacionesPendientesSpec(Specification[Any]):
    """RN-04: no hay fallas adicionales sin cotizar o sin autorizar."""

    def es_satisfecha_por(self, orden: Any) -> bool:
        from ..entities.solicitudes import EstadoAmpliacion  # import diferido (evita ciclo)

        return all(s.estado is EstadoAmpliacion.RESUELTA for s in orden.solicitudes_ampliacion)


class RefaccionesDisponiblesSpec(Specification[Any]):
    """RN-07: ninguna solicitud de refacción sigue pendiente en Compras."""

    def es_satisfecha_por(self, orden: Any) -> bool:
        return not any(s.pendiente for s in orden.solicitudes_refaccion)


class OrdenEsDeFlotillaSpec(Specification[Any]):
    """RN-09."""

    def es_satisfecha_por(self, orden: Any) -> bool:
        return orden.es_flotilla


class OrdenListaParaEntregaSpec(Specification[Any]):
    """Composición: con trabajos, todos revisados, sin ampliaciones ni refacciones pendientes."""

    def __init__(self) -> None:
        self._spec = (TieneTrabajosSpec() & TodosTrabajosRevisadosSpec()
                      & SinAmpliacionesPendientesSpec() & RefaccionesDisponiblesSpec())

    def es_satisfecha_por(self, orden: Any) -> bool:
        return self._spec.es_satisfecha_por(orden)
