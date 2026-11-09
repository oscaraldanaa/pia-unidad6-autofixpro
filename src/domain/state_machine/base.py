"""Máquina de estados genérica y declarativa (tabla de transiciones)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Iterable, TypeVar

from ..shared import ReglaDeNegocioViolada
from ..specifications.base import Specification

E = TypeVar("E", bound=Enum)  # estados
D = TypeVar("D", bound=Enum)  # disparadores


class TransicionInvalida(ReglaDeNegocioViolada):
    """El disparador no es válido en el estado actual, o su guarda no se cumple."""

    def __init__(self, regla: str, mensaje: str, estado: Enum, disparador: Enum) -> None:
        super().__init__(regla, mensaje)
        self.estado = estado
        self.disparador = disparador


@dataclass(frozen=True)
class Transicion(Generic[E, D]):
    origen: E
    disparador: D
    destino: E
    guardia: Specification[Any] | None = None   # precondición (Specification)
    regla: str = "RN-01"                         # regla BRD que se reporta si falla
    mensaje_guardia: str = "No se cumple la precondición de la transición"


class StateMachine(Generic[E, D]):
    def __init__(self, transiciones: Iterable[Transicion[E, D]]) -> None:
        self._tabla: dict[tuple[E, D], Transicion[E, D]] = {}
        for t in transiciones:
            clave = (t.origen, t.disparador)
            if clave in self._tabla:
                raise ValueError(f"Transición duplicada: {clave}")
            self._tabla[clave] = t

    def disparadores_permitidos(self, estado: E) -> list[D]:
        return [d for (e, d) in self._tabla if e == estado]

    def puede(self, estado: E, disparador: D, contexto: Any = None) -> bool:
        t = self._tabla.get((estado, disparador))
        return t is not None and (t.guardia is None or t.guardia.es_satisfecha_por(contexto))

    def destino(self, estado: E, disparador: D, contexto: Any = None) -> E:
        """Valida la transición y devuelve el estado destino (sin mutar nada)."""
        t = self._tabla.get((estado, disparador))
        if t is None:
            permitidos = ", ".join(d.value for d in self.disparadores_permitidos(estado)) or "ninguno"
            raise TransicionInvalida(
                "RN-01",
                f"'{disparador.value}' no es válido en estado '{estado.value}' (permitidos: {permitidos})",
                estado, disparador)
        if t.guardia is not None and not t.guardia.es_satisfecha_por(contexto):
            raise TransicionInvalida(t.regla, t.mensaje_guardia, estado, disparador)
        return t.destino
