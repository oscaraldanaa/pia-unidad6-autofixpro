from __future__ import annotations

from enum import Enum

from ..shared import Entity, ReglaDeNegocioViolada
from ..value_objects import ConceptoId, TecnicoId, TrabajoId


class EstadoTrabajo(str, Enum):
    EN_REPARACION = "En reparación"
    PENDIENTE_REVISION = "Pendiente de revisión"
    REVISADO = "Revisado"


class TrabajoReparacion(Entity[TrabajoId]):
    """Trabajo habilitado únicamente a partir de un concepto autorizado (RN-13)."""

    def __init__(self, id: TrabajoId, concepto_id: ConceptoId, descripcion: str, tecnico_id: TecnicoId) -> None:
        super().__init__(id)
        self._concepto_id = concepto_id
        self._descripcion = descripcion
        self._tecnico_id = tecnico_id
        self._estado = EstadoTrabajo.EN_REPARACION

    concepto_id = property(lambda s: s._concepto_id)
    descripcion = property(lambda s: s._descripcion)
    tecnico_id = property(lambda s: s._tecnico_id)
    estado = property(lambda s: s._estado)

    def finalizar(self) -> None:
        if self._estado is not EstadoTrabajo.EN_REPARACION:
            raise ReglaDeNegocioViolada("RN-01", "Solo un trabajo en reparación puede finalizarse")
        self._estado = EstadoTrabajo.PENDIENTE_REVISION

    def aprobar_revision(self) -> None:
        if self._estado is not EstadoTrabajo.PENDIENTE_REVISION:
            raise ReglaDeNegocioViolada("RN-01", "Solo un trabajo pendiente de revisión puede aprobarse")
        self._estado = EstadoTrabajo.REVISADO
