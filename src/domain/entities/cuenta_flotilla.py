from __future__ import annotations

from dataclasses import dataclass, field

from ..shared import Entity, ValorInvalido, ValueObject
from ..value_objects import ClienteId, CuentaFlotillaId, Porcentaje


@dataclass(frozen=True)
class CondicionesFlotilla(ValueObject):
    """Condiciones B2B (RN-09). Tarifas y SLA reales están por validar con el
    stakeholder (BRD §6.2), por lo que los valores por defecto son neutros."""

    descuento: Porcentaje = field(default_factory=Porcentaje.cero)
    prioridad: int = 0
    dias_credito: int = 0

    def _validar(self) -> None:
        if self.prioridad < 0 or self.dias_credito < 0:
            raise ValorInvalido("Prioridad y días de crédito no pueden ser negativos")


class CuentaFlotilla(Entity[CuentaFlotillaId]):
    """Cuenta corporativa con autorizador corporativo (RN-09, RN-14)."""

    def __init__(
        self,
        id: CuentaFlotillaId,
        razon_social: str,
        autorizador_corporativo_id: ClienteId,
        condiciones: CondicionesFlotilla | None = None,
    ) -> None:
        super().__init__(id)
        if not razon_social or not razon_social.strip():
            raise ValorInvalido("La razón social es obligatoria")
        self._razon_social = razon_social.strip()
        self._autorizador_corporativo_id = autorizador_corporativo_id
        self._condiciones = condiciones or CondicionesFlotilla()

    @property
    def razon_social(self) -> str:
        return self._razon_social

    @property
    def autorizador_corporativo_id(self) -> ClienteId:
        return self._autorizador_corporativo_id

    @property
    def condiciones(self) -> CondicionesFlotilla:
        return self._condiciones
