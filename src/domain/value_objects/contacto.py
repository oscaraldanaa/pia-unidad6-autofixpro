from __future__ import annotations

import re
from dataclasses import dataclass

from ..shared import ValorInvalido, ValueObject

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class DatosContacto(ValueObject):
    """Medio digital del cliente. RN-10: al menos SMS/teléfono o correo."""

    telefono: str | None = None
    email: str | None = None

    def _validar(self) -> None:
        if not self.telefono and not self.email:
            raise ValorInvalido("RN-10: se requiere teléfono (SMS) o correo electrónico")
        if self.telefono:
            digitos = re.sub(r"[\s\-+()]", "", self.telefono)
            if not digitos.isdigit() or not (8 <= len(digitos) <= 15):
                raise ValorInvalido(f"Teléfono inválido: {self.telefono!r}")
        if self.email and not _EMAIL.match(self.email):
            raise ValorInvalido(f"Correo inválido: {self.email!r}")
