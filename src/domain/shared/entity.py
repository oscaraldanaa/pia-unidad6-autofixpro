"""Clase base de Entidades: identidad por ID, no por atributos."""
from __future__ import annotations

from typing import Generic, TypeVar

TId = TypeVar("TId")


class Entity(Generic[TId]):
    def __init__(self, id: TId) -> None:
        self._id = id

    @property
    def id(self) -> TId:
        return self._id

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and self._id == other._id  # type: ignore[attr-defined]

    def __hash__(self) -> int:
        return hash((type(self), self._id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id})"
