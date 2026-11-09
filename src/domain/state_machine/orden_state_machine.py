"""Ciclo de vida de OrdenServicio (BRD §12, US-01..US-15, BPMN).

Equivalencia con los nombres de la Fase 2:
RECIBIDA=RECIBIDO · DIAGNOSTICADA=DIAGNOSTICADO · EN_REPARACION · ENTREGADA=CERRADO
(pasando por LISTO_PARA_ENTREGA) · CANCELADA=CANCELADO. Se conservan además los
estados del BRD (COTIZADO, AUTORIZADO, EN_ESPERA_REFACCION, LISTO_PARA_ENTREGA).
"""
from __future__ import annotations

from enum import Enum

from ..specifications import OrdenListaParaEntregaSpec, RefaccionesDisponiblesSpec
from ..value_objects import EstadoOrden as S
from .base import StateMachine, Transicion


class DisparadorOrden(str, Enum):
    DIAGNOSTICAR = "diagnosticar"
    COTIZAR = "cotizar"
    AUTORIZAR = "autorizar"
    RECHAZAR_COTIZACION = "rechazar_cotizacion"
    INICIAR_REPARACION = "iniciar_reparacion"
    ESPERAR_REFACCION = "esperar_refaccion"
    REANUDAR_REPARACION = "reanudar_reparacion"
    PREPARAR_ENTREGA = "preparar_entrega"
    CERRAR = "cerrar"
    CANCELAR = "cancelar"


D = DisparadorOrden

TRANSICIONES_ORDEN = [
    Transicion(S.RECIBIDO, D.DIAGNOSTICAR, S.DIAGNOSTICADO),
    Transicion(S.DIAGNOSTICADO, D.COTIZAR, S.COTIZADO, regla="RN-05"),
    Transicion(S.COTIZADO, D.AUTORIZAR, S.AUTORIZADO, regla="RN-05"),
    Transicion(S.COTIZADO, D.RECHAZAR_COTIZACION, S.CANCELADO, regla="RN-05"),
    Transicion(S.AUTORIZADO, D.INICIAR_REPARACION, S.EN_REPARACION, regla="RN-13"),
    Transicion(S.EN_REPARACION, D.ESPERAR_REFACCION, S.EN_ESPERA_REFACCION, regla="RN-07"),
    Transicion(S.EN_ESPERA_REFACCION, D.REANUDAR_REPARACION, S.EN_REPARACION,
               guardia=RefaccionesDisponiblesSpec(), regla="RN-07",
               mensaje_guardia="Aún hay refacciones pendientes en Compras"),
    Transicion(S.EN_REPARACION, D.PREPARAR_ENTREGA, S.LISTO_PARA_ENTREGA,
               guardia=OrdenListaParaEntregaSpec(), regla="RN-01",
               mensaje_guardia="Todos los trabajos deben estar revisados, sin ampliaciones ni refacciones pendientes"),
    Transicion(S.LISTO_PARA_ENTREGA, D.CERRAR, S.CERRADO),
    # Cancelación: solo antes de iniciar la reparación
    Transicion(S.RECIBIDO, D.CANCELAR, S.CANCELADO),
    Transicion(S.DIAGNOSTICADO, D.CANCELAR, S.CANCELADO),
    Transicion(S.COTIZADO, D.CANCELAR, S.CANCELADO),
    Transicion(S.AUTORIZADO, D.CANCELAR, S.CANCELADO),
]

ORDEN_STATE_MACHINE: StateMachine[S, DisparadorOrden] = StateMachine(TRANSICIONES_ORDEN)
