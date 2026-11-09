"""Manejadores de eventos de dominio (efectos secundarios desacoplados del agregado)."""
from __future__ import annotations

from ..domain.events import FechaModificada, RetrasoPorRefaccion
from .ports import Notificador, UnitOfWorkFactory


class _NotificaAutorizador:
    def __init__(self, uow_factory: UnitOfWorkFactory, notificador: Notificador) -> None:
        self._uow_factory = uow_factory
        self._notificador = notificador

    def _notificar(self, orden_id, asunto: str, mensaje: str) -> None:
        with self._uow_factory() as uow:
            orden = uow.ordenes.obtener(orden_id)
            destinatario = uow.clientes.obtener(orden.autorizador_id)   # RN-14
        self._notificador.enviar(destinatario.contacto, asunto, mensaje)


class NotificarRetrasoPorRefaccion(_NotificaAutorizador):
    """RN-03: motivo y nuevo tiempo estimado al cliente."""

    def __call__(self, evento: RetrasoPorRefaccion) -> None:
        self._notificar(evento.orden_id, "Retraso en su reparación",
                        f"{evento.motivo}. Nueva fecha estimada de reposición: "
                        f"{evento.nueva_fecha_reposicion:%Y-%m-%d %H:%M} UTC.")


class NotificarCambioFechaEntrega(_NotificaAutorizador):
    """RN-06: comunica cambio de fecha y justificación."""

    def __call__(self, evento: FechaModificada) -> None:
        self._notificar(evento.orden_id, "Cambio en la fecha estimada de entrega",
                        f"Nueva fecha: {evento.nueva:%Y-%m-%d %H:%M} UTC (antes {evento.anterior:%Y-%m-%d %H:%M}). "
                        f"Motivo: {evento.justificacion}.")
