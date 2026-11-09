"""Patrón Specification: reglas de negocio como objetos componibles."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ..shared import ReglaDeNegocioViolada

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    @abstractmethod
    def es_satisfecha_por(self, candidato: T) -> bool: ...

    # Combinadores: AND / OR / NOT (métodos y operadores & | ~)
    def y(self, otra: "Specification[T]") -> "Specification[T]":
        return AndSpecification(self, otra)

    def o(self, otra: "Specification[T]") -> "Specification[T]":
        return OrSpecification(self, otra)

    def no(self) -> "Specification[T]":
        return NotSpecification(self)

    __and__ = y
    __or__ = o
    __invert__ = no

    def verificar(self, candidato: T, regla: str, mensaje: str) -> None:
        """Lanza ``ReglaDeNegocioViolada`` si el candidato no cumple la especificación."""
        if not self.es_satisfecha_por(candidato):
            raise ReglaDeNegocioViolada(regla, mensaje)


class AndSpecification(Specification[T]):
    def __init__(self, izquierda: Specification[T], derecha: Specification[T]) -> None:
        self._i, self._d = izquierda, derecha

    def es_satisfecha_por(self, candidato: T) -> bool:
        return self._i.es_satisfecha_por(candidato) and self._d.es_satisfecha_por(candidato)


class OrSpecification(Specification[T]):
    def __init__(self, izquierda: Specification[T], derecha: Specification[T]) -> None:
        self._i, self._d = izquierda, derecha

    def es_satisfecha_por(self, candidato: T) -> bool:
        return self._i.es_satisfecha_por(candidato) or self._d.es_satisfecha_por(candidato)


class NotSpecification(Specification[T]):
    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    def es_satisfecha_por(self, candidato: T) -> bool:
        return not self._spec.es_satisfecha_por(candidato)
