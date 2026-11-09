"""Raíz de agregado: frontera de consistencia y acumulador de eventos."""
from __future__ import annotations

from typing import TypeVar

from .domain_event import DomainEvent
from .entity import Entity

TId = TypeVar("TId")


class AggregateRoot(Entity[TId]):
    def __init__(self, id: TId) -> None:
        super().__init__(id)
        self._eventos: list[DomainEvent] = []

    def _registrar_evento(self, evento: DomainEvent) -> None:
        self._eventos.append(evento)

    def recolectar_eventos(self) -> list[DomainEvent]:
        """Devuelve y limpia los eventos pendientes (los publica la capa de aplicación)."""
        eventos, self._eventos = self._eventos, []
        return eventos
