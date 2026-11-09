"""Clase base de Value Objects.

Los VO son inmutables y se comparan por valor. Cada subclase se declara como
``@dataclass(frozen=True)`` (eq/hash por valor) y valida su invariante en
``_validar``, que se ejecuta al construir la instancia.
"""
from __future__ import annotations


class ValueObject:
    def __post_init__(self) -> None:  # invocado por dataclass
        self._validar()

    def _validar(self) -> None:
        """Las subclases lanzan ``ValorInvalido`` si el valor no es consistente."""
