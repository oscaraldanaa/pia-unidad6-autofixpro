from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..shared import ValorInvalido, ValueObject


class CanalAutorizacion(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WEB = "web"


@dataclass(frozen=True)
class EvidenciaAutorizacion(ValueObject):
    """RN-11 / RF-18: sello de tiempo + IP o token de verificación."""

    sello_tiempo: datetime
    canal: CanalAutorizacion
    ip: str | None = None
    token_verificacion: str | None = None

    def _validar(self) -> None:
        if self.sello_tiempo.tzinfo is None:
            raise ValorInvalido("RN-11: el sello de tiempo debe incluir zona horaria")
        if not self.ip and not self.token_verificacion:
            raise ValorInvalido("RN-11: se requiere IP o token de verificación")
        if self.ip:
            try:
                ipaddress.ip_address(self.ip)
            except ValueError as exc:
                raise ValorInvalido(f"IP inválida: {self.ip!r}") from exc
