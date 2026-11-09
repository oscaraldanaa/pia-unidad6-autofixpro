from __future__ import annotations

import re
from dataclasses import dataclass

from ..shared import ValorInvalido, ValueObject

_VIN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")  # el estándar excluye I, O y Q


@dataclass(frozen=True)
class Placas(ValueObject):
    valor: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "valor", str(self.valor).strip().upper().replace(" ", ""))
        super().__post_init__()

    def _validar(self) -> None:
        if not (4 <= len(self.valor) <= 10) or not self.valor.replace("-", "").isalnum():
            raise ValorInvalido(f"Placas inválidas: {self.valor!r}")


@dataclass(frozen=True)
class Vin(ValueObject):
    valor: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "valor", str(self.valor).strip().upper())
        super().__post_init__()

    def _validar(self) -> None:
        if not _VIN.match(self.valor):
            raise ValorInvalido("El VIN debe tener 17 caracteres alfanuméricos (sin I, O, Q)")
