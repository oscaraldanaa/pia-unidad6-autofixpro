"""Especificaciones sobre Cliente, Técnico y Dinero."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..value_objects import Dinero
from .base import Specification

if TYPE_CHECKING:  # evita ciclo specifications <-> entities
    from ..entities.cliente import Cliente
    from ..entities.tecnico import Tecnico


class ClienteActivoSpec(Specification['Cliente']):
    def es_satisfecha_por(self, candidato: 'Cliente') -> bool:
        return candidato.activo


class TecnicoDisponibleSpec(Specification['Tecnico']):
    def es_satisfecha_por(self, candidato: 'Tecnico') -> bool:
        return candidato.disponible


class MontoMinimoSpec(Specification[Dinero]):
    """El importe es mayor o igual que ``minimo`` (misma moneda)."""

    def __init__(self, minimo: Dinero) -> None:
        self._minimo = minimo

    def es_satisfecha_por(self, candidato: Dinero) -> bool:
        return candidato >= self._minimo
