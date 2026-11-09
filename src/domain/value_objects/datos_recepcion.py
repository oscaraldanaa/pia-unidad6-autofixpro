from __future__ import annotations

from dataclasses import dataclass

from ..shared import ValorInvalido, ValueObject
from .kilometraje import Kilometraje, NivelCombustible


@dataclass(frozen=True)
class DatosRecepcion(ValueObject):
    """RN-01: kilometraje, combustible, daños visibles y motivo de ingreso.

    ``danos_visibles`` es el inventario de daños; una tupla vacía significa que
    el asesor inspeccionó y no encontró daños.
    """

    kilometraje: Kilometraje
    combustible: NivelCombustible
    danos_visibles: tuple[str, ...]
    motivo_ingreso: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "danos_visibles", tuple(self.danos_visibles))
        super().__post_init__()

    def _validar(self) -> None:
        if not self.motivo_ingreso or not self.motivo_ingreso.strip():
            raise ValorInvalido("RN-01: el motivo de ingreso es obligatorio")
        if any(not d or not d.strip() for d in self.danos_visibles):
            raise ValorInvalido("RN-01: los daños visibles no pueden ser textos vacíos")
