from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ...infrastructure.bootstrap import Contenedor
from ..dependencias import get_contenedor

router = APIRouter(tags=["Salud"])


@router.get("/health", summary="Estado del servicio y de la base de datos")
def health(c: Contenedor = Depends(get_contenedor)):
    with c.engine.connect() as cn:
        cn.execute(text("SELECT 1"))
    return {"estado": "ok", "entorno": c.settings.app_env}
