"""Identificadores tipados de texto (``str``) para cada entidad del dominio."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from ..shared import ValorInvalido, ValueObject
from ..shared.ids import LONGITUD_MAXIMA, generar_id

T = TypeVar("T", bound="EntityId")


@dataclass(frozen=True)
class EntityId(ValueObject):
    value: str
    PREFIJO: ClassVar[str] = "ID"

    def _validar(self) -> None:
        if not isinstance(self.value, str):
            raise ValorInvalido(f"{type(self).__name__} requiere un str, recibió {type(self.value).__name__}")
        if not self.value or self.value != self.value.strip() or any(c.isspace() for c in self.value):
            raise ValorInvalido(f"{type(self).__name__} inválido: no puede ser vacío ni contener espacios")
        if len(self.value) > LONGITUD_MAXIMA:
            raise ValorInvalido(f"{type(self).__name__} excede {LONGITUD_MAXIMA} caracteres")

    @classmethod
    def generar(cls: type[T]) -> T:
        return cls(generar_id(cls.PREFIJO))

    @classmethod
    def desde_str(cls: type[T], texto: str) -> T:
        return cls(texto)

    def __str__(self) -> str:
        return self.value


class OrdenServicioId(EntityId): PREFIJO = "ORD"
class ClienteId(EntityId): PREFIJO = "CLI"
class VehiculoId(EntityId): PREFIJO = "VEH"
class TecnicoId(EntityId): PREFIJO = "TEC"
class CuentaFlotillaId(EntityId): PREFIJO = "FLT"
class CotizacionId(EntityId): PREFIJO = "COT"
class ConceptoId(EntityId): PREFIJO = "CON"
class TrabajoId(EntityId): PREFIJO = "TRA"
class SolicitudRefaccionId(EntityId): PREFIJO = "REF"
class SolicitudAmpliacionId(EntityId): PREFIJO = "AMP"
class RecursoId(EntityId): PREFIJO = "REC"
