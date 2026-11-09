from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import total_ordering
from typing import Iterable

from ..shared import ValorInvalido, ValueObject
from .porcentaje import Porcentaje

_CENTAVOS = Decimal("0.01")


@total_ordering
@dataclass(frozen=True)
class Dinero(ValueObject):
    """Importe monetario con ``Decimal`` (nunca float), 2 decimales y moneda."""

    monto: Decimal
    moneda: str = "MXN"

    def __post_init__(self) -> None:
        if isinstance(self.monto, (float, bool)):
            raise ValorInvalido("Dinero no admite float; use Decimal, int o str")
        try:
            monto = Decimal(str(self.monto)).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
        except Exception as exc:  # InvalidOperation
            raise ValorInvalido(f"Monto inválido: {self.monto!r}") from exc
        object.__setattr__(self, "monto", monto)
        object.__setattr__(self, "moneda", str(self.moneda).upper())
        super().__post_init__()

    def _validar(self) -> None:
        if self.monto < 0:
            raise ValorInvalido("El importe no puede ser negativo")
        if len(self.moneda) != 3 or not self.moneda.isalpha():
            raise ValorInvalido("La moneda debe ser un código ISO de 3 letras")

    # --- fábricas ---
    @classmethod
    def de(cls, monto: Decimal | int | str, moneda: str = "MXN") -> "Dinero":
        return cls(Decimal(str(monto)), moneda)

    @classmethod
    def cero(cls, moneda: str = "MXN") -> "Dinero":
        return cls(Decimal(0), moneda)

    @classmethod
    def sumar(cls, importes: Iterable["Dinero"], moneda: str = "MXN") -> "Dinero":
        total = cls.cero(moneda)
        for i in importes:
            total = total + i
        return total

    # --- aritmética ---
    def _mismo_tipo(self, otro: "Dinero") -> None:
        if not isinstance(otro, Dinero):
            raise TypeError("Operación válida solo entre Dinero")
        if otro.moneda != self.moneda:
            raise ValorInvalido(f"Monedas distintas: {self.moneda} vs {otro.moneda}")

    def __add__(self, otro: "Dinero") -> "Dinero":
        self._mismo_tipo(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def __sub__(self, otro: "Dinero") -> "Dinero":
        self._mismo_tipo(otro)
        return Dinero(self.monto - otro.monto, self.moneda)  # falla si queda negativo

    def por(self, factor: Decimal | int | str) -> "Dinero":
        if isinstance(factor, float):
            raise ValorInvalido("El factor no puede ser float")
        return Dinero(self.monto * Decimal(str(factor)), self.moneda)

    def aplicar(self, porcentaje: Porcentaje) -> "Dinero":
        """Importe que representa ``porcentaje`` de este monto."""
        return self.por(porcentaje.factor)

    def __lt__(self, otro: "Dinero") -> bool:
        self._mismo_tipo(otro)
        return self.monto < otro.monto

    def __str__(self) -> str:
        return f"{self.monto:,.2f} {self.moneda}"
