from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ...domain.events import OrdenEvent
from ...domain.value_objects import EntityId
from . import modelos as m


def _serializar(v: Any) -> Any:
    if isinstance(v, EntityId):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, (tuple, list)):
        return [_serializar(x) for x in v]
    return v


class AuditoriaEventosSql:
    """Persiste cada evento de orden en ``eventos_dominio`` (evidencia auditable)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def __call__(self, evento: OrdenEvent) -> None:
        payload = {f.name: _serializar(getattr(evento, f.name)) for f in fields(evento)
                   if f.name not in ("event_id", "ocurrido_en", "orden_id")}
        with self._sf() as s:
            s.add(m.EventoDominioRecord(id=str(evento.event_id), tipo=type(evento).__name__,
                                        orden_id=str(evento.orden_id), ocurrido_en=evento.ocurrido_en,
                                        payload=json.loads(json.dumps(payload, default=str))))
            s.commit()
