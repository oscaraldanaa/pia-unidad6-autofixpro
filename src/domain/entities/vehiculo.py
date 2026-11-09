from __future__ import annotations

from ..shared import Entity, ReglaDeNegocioViolada, ValorInvalido
from ..value_objects import CuentaFlotillaId, Kilometraje, Placas, VehiculoId, Vin


class Vehiculo(Entity[VehiculoId]):
    def __init__(
        self,
        id: VehiculoId,
        placas: Placas,
        marca: str,
        modelo: str,
        kilometraje: Kilometraje,
        vin: Vin | None = None,
        cuenta_flotilla_id: CuentaFlotillaId | None = None,
    ) -> None:
        super().__init__(id)
        if not marca.strip() or not modelo.strip():
            raise ValorInvalido("Marca y modelo del vehículo son obligatorios")
        self._placas = placas
        self._marca = marca.strip()
        self._modelo = modelo.strip()
        self._kilometraje = kilometraje
        self._vin = vin
        self._cuenta_flotilla_id = cuenta_flotilla_id

    @property
    def placas(self) -> Placas:
        return self._placas

    @property
    def marca(self) -> str:
        return self._marca

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def vin(self) -> Vin | None:
        return self._vin

    @property
    def kilometraje(self) -> Kilometraje:
        return self._kilometraje

    @property
    def cuenta_flotilla_id(self) -> CuentaFlotillaId | None:
        return self._cuenta_flotilla_id

    @property
    def es_de_flotilla(self) -> bool:
        return self._cuenta_flotilla_id is not None

    def actualizar_kilometraje(self, nuevo: Kilometraje) -> None:
        if nuevo.km < self._kilometraje.km:
            raise ReglaDeNegocioViolada("RN-01", "El kilometraje no puede disminuir")
        self._kilometraje = nuevo
