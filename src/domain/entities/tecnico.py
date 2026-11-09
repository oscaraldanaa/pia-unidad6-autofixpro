from __future__ import annotations

from ..shared import Entity, ReglaDeNegocioViolada, ValorInvalido
from ..value_objects import TecnicoId


class Tecnico(Entity[TecnicoId]):
    def __init__(self, id: TecnicoId, nombre: str, especialidad: str, disponible: bool = True) -> None:
        super().__init__(id)
        if not nombre.strip():
            raise ValorInvalido("El nombre del técnico es obligatorio")
        self._nombre = nombre.strip()
        self._especialidad = especialidad.strip()
        self._disponible = disponible

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def especialidad(self) -> str:
        return self._especialidad

    @property
    def disponible(self) -> bool:
        return self._disponible

    def asignar(self) -> None:
        if not self._disponible:
            raise ReglaDeNegocioViolada("RN-12", "El técnico no está disponible")
        self._disponible = False

    def liberar(self) -> None:
        self._disponible = True
