from __future__ import annotations

import ipaddress
from uuid import uuid4

from fastapi import Request

from ..application.dto import EvidenciaDTO
from ..infrastructure.bootstrap import Contenedor


def get_contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


def construir_evidencia(request: Request, canal: str, token: str | None) -> EvidenciaDTO:
    """RN-11: IP real del request (si es válida) o token de verificación."""
    host = request.client.host if request.client else None
    try:
        ip = str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        ip = None
    if ip is None and not token:
        token = uuid4().hex
    return EvidenciaDTO(canal=canal, ip=ip, token_verificacion=token)
