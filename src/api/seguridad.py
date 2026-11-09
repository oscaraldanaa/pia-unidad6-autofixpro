"""Control de acceso por rol (RN-12 / RNF-03).

Autenticación simplificada para el alcance del PIA: el rol llega en la cabecera
``X-Rol`` (botón *Authorize* de Swagger). En producción se reemplazaría por
JWT/OAuth2 conservando la misma dependencia ``requiere_rol``.
"""
from __future__ import annotations

from enum import Enum

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


class Rol(str, Enum):
    """Los cinco roles del BRD (§7); no se admiten roles adicionales (RN-12)."""

    CLIENTE = "cliente"
    ASESOR = "asesor_servicio"
    TECNICO = "tecnico"
    COMPRAS = "compras"
    CAJA = "caja"


_cabecera_rol = APIKeyHeader(
    name="X-Rol", auto_error=False,
    description="Rol del usuario: cliente | asesor_servicio | tecnico | compras | caja")


def requiere_rol(*permitidos: Rol):
    def dependencia(valor: str | None = Security(_cabecera_rol)) -> Rol:
        if not valor:
            raise HTTPException(401, detail={"detalle": "Falta la cabecera X-Rol", "regla": "RN-12"})
        try:
            rol = Rol(valor)
        except ValueError:
            raise HTTPException(401, detail={"detalle": f"Rol desconocido: {valor!r}", "regla": "RN-12"})
        if rol not in permitidos:
            raise HTTPException(403, detail={
                "detalle": f"El rol '{rol.value}' no puede ejecutar esta acción "
                           f"(permitidos: {', '.join(r.value for r in permitidos)})",
                "regla": "RN-12"})
        return rol

    return dependencia
