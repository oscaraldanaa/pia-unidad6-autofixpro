from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..shared import ValorInvalido, ValueObject


class NivelCombustible(str, Enum):
    VACIO = "vacio"
    UN_CUARTO = "1/4"
    MEDIO = "1/2"
    TRES_CUARTOS = "3/4"
    LLENO = "lleno"


@dataclass(frozen=True)
class Kilometraje(ValueObject):
    km: int

    def _validar(self) -> None:
        if isinstance(self.km, bool) or not isinstance(self.km, int) or self.km < 0:
            raise ValorInvalido("El kilometraje debe ser un entero >= 0")
