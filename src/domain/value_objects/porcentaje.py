from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..shared import ValorInvalido, ValueObject


@dataclass(frozen=True)
class Porcentaje(ValueObject):
    """Porcentaje entre 0 y 100 (p. ej. IVA 16, descuento de flotilla 5)."""

    valor: Decimal

    def __post_init__(self) -> None:
        if isinstance(self.valor, float) or isinstance(self.valor, bool):
            raise ValorInvalido("Porcentaje no admite float; use Decimal, int o str")
        object.__setattr__(self, "valor", Decimal(str(self.valor)))
        super().__post_init__()

    def _validar(self) -> None:
        if not (Decimal(0) <= self.valor <= Decimal(100)):
            raise ValorInvalido("El porcentaje debe estar entre 0 y 100")

    @classmethod
    def de(cls, valor: Decimal | int | str) -> "Porcentaje":
        return cls(Decimal(str(valor)))

    @classmethod
    def cero(cls) -> "Porcentaje":
        return cls(Decimal(0))

    @property
    def factor(self) -> Decimal:
        return self.valor / Decimal(100)
