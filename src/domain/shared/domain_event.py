"""Evento de dominio: hecho ocurrido, inmutable y nombrado en pasado."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .ids import generar_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: str = field(default_factory=lambda: generar_id("EVT"))
    ocurrido_en: datetime = field(default_factory=utc_now)
