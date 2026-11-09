"""Traducción de excepciones de dominio a respuestas HTTP."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..domain.shared import DomainError, EntidadNoEncontrada, ReglaDeNegocioViolada, ValorInvalido


class ErrorOut(BaseModel):
    detalle: str
    regla: str | None = None


def _json(status: int, detalle: str, regla: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detalle": detalle, "regla": regla})


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(EntidadNoEncontrada)
    async def _no_encontrada(_: Request, exc: EntidadNoEncontrada):
        return _json(404, str(exc))

    @app.exception_handler(ReglaDeNegocioViolada)  # incluye TransicionInvalida
    async def _regla(_: Request, exc: ReglaDeNegocioViolada):
        return _json(409, exc.mensaje, exc.regla)

    @app.exception_handler(ValorInvalido)
    async def _valor(_: Request, exc: ValorInvalido):
        return _json(422, str(exc))

    @app.exception_handler(DomainError)
    async def _dominio(_: Request, exc: DomainError):
        return _json(400, str(exc))

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        d = exc.detail if isinstance(exc.detail, dict) else {"detalle": str(exc.detail), "regla": None}
        return JSONResponse(status_code=exc.status_code, content=d)
