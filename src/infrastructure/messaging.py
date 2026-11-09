from __future__ import annotations

import logging
from typing import Callable, Iterable

from ..application.ports import EventBus, Notificador
from ..domain.shared import DomainEvent
from ..domain.value_objects import DatosContacto

log = logging.getLogger(__name__)


class InProcessEventBus(EventBus):
    """Bus síncrono en memoria. Un manejador que falla no revierte la operación ya confirmada."""

    def __init__(self) -> None:
        self._manejadores: list[tuple[type, Callable[[DomainEvent], None]]] = []

    def suscribir(self, tipo_evento: type, manejador: Callable[[DomainEvent], None]) -> None:
        self._manejadores.append((tipo_evento, manejador))

    def publicar(self, eventos: Iterable[DomainEvent]) -> None:
        for evento in eventos:
            for tipo, manejador in self._manejadores:
                if isinstance(evento, tipo):
                    try:
                        manejador(evento)
                    except Exception:  # noqa: BLE001
                        log.exception("Falló el manejador %s para %s", manejador, type(evento).__name__)


class LogNotificador(Notificador):
    """Canal 'log': registra la notificación (sustituible por SMS/correo)."""

    def __init__(self) -> None:
        self.enviados: list[tuple[DatosContacto, str, str]] = []

    def enviar(self, destinatario: DatosContacto, asunto: str, mensaje: str) -> None:
        self.enviados.append((destinatario, asunto, mensaje))
        medio = destinatario.email or destinatario.telefono
        log.info("NOTIFICACIÓN a %s | %s | %s", medio, asunto, mensaje)
