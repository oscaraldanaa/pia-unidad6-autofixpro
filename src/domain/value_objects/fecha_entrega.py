from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..shared import ValorInvalido, ValueObject


@dataclass(frozen=True)
class FechaEntrega(ValueObject):
    fecha_estimada: datetime

    def _validar(self) -> None:
        if self.fecha_estimada.tzinfo is None:
            raise ValorInvalido("La fecha estimada debe incluir zona horaria")

    def es_valida(self, ahora: datetime) -> bool:
        return self.fecha_estimada >= ahora


@dataclass(frozen=True)
class CambioFechaEntrega(ValueObject):
    """RN-06: todo cambio conserva fecha anterior, nueva y justificación."""

    anterior: FechaEntrega
    nueva: FechaEntrega
    justificacion: str
    registrado_en: datetime

    def _validar(self) -> None:
        if not self.justificacion or not self.justificacion.strip():
            raise ValorInvalido("RN-06: el cambio de fecha requiere justificación explícita")
        if self.anterior == self.nueva:
            raise ValorInvalido("RN-06: la nueva fecha debe ser distinta de la anterior")
