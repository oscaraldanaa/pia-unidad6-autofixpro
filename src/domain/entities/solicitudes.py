from __future__ import annotations

from datetime import datetime
from enum import Enum

from ..shared import Entity, ReglaDeNegocioViolada
from ..value_objects import ConceptoId, SolicitudAmpliacionId, SolicitudRefaccionId, TecnicoId
from .cotizacion import Cotizacion


class EstadoSolicitudRefaccion(str, Enum):
    PENDIENTE = "pendiente"       # en la cola de Compras
    RECIBIDA = "recibida"


class SolicitudRefaccion(Entity[SolicitudRefaccionId]):
    """RN-07: refacción sin existencia → solicitud en cola de trabajo de Compras."""

    def __init__(self, id: SolicitudRefaccionId, concepto_id: ConceptoId, descripcion: str,
                 creada_en: datetime, reposicion_estimada: datetime | None = None) -> None:
        super().__init__(id)
        self._concepto_id = concepto_id
        self._descripcion = descripcion
        self._creada_en = creada_en
        self._reposicion_estimada = reposicion_estimada
        self._estado = EstadoSolicitudRefaccion.PENDIENTE

    concepto_id = property(lambda s: s._concepto_id)
    descripcion = property(lambda s: s._descripcion)
    creada_en = property(lambda s: s._creada_en)
    reposicion_estimada = property(lambda s: s._reposicion_estimada)
    estado = property(lambda s: s._estado)

    @property
    def pendiente(self) -> bool:
        return self._estado is EstadoSolicitudRefaccion.PENDIENTE

    def actualizar_reposicion(self, nueva_fecha: datetime) -> None:
        if not self.pendiente:
            raise ReglaDeNegocioViolada("RN-07", "La solicitud ya fue atendida")
        self._reposicion_estimada = nueva_fecha

    def marcar_recibida(self) -> None:
        if not self.pendiente:
            raise ReglaDeNegocioViolada("RN-07", "La solicitud ya fue atendida")
        self._estado = EstadoSolicitudRefaccion.RECIBIDA


class EstadoAmpliacion(str, Enum):
    PENDIENTE_COTIZACION = "pendiente_cotizacion"
    PENDIENTE_AUTORIZACION = "pendiente_autorizacion"
    RESUELTA = "resuelta"


class SolicitudAmpliacion(Entity[SolicitudAmpliacionId]):
    """RN-04: toda falla adicional requiere cotización suplementaria autorizada."""

    def __init__(self, id: SolicitudAmpliacionId, tecnico_id: TecnicoId, descripcion_falla: str,
                 detectada_en: datetime) -> None:
        super().__init__(id)
        self._tecnico_id = tecnico_id
        self._descripcion_falla = descripcion_falla
        self._detectada_en = detectada_en
        self._estado = EstadoAmpliacion.PENDIENTE_COTIZACION
        self._cotizacion: Cotizacion | None = None

    tecnico_id = property(lambda s: s._tecnico_id)
    descripcion_falla = property(lambda s: s._descripcion_falla)
    detectada_en = property(lambda s: s._detectada_en)
    estado = property(lambda s: s._estado)
    cotizacion = property(lambda s: s._cotizacion)

    def adjuntar_cotizacion(self, cotizacion: Cotizacion) -> None:
        if self._estado is not EstadoAmpliacion.PENDIENTE_COTIZACION:
            raise ReglaDeNegocioViolada("RN-04", "La ampliación ya tiene cotización complementaria")
        self._cotizacion = cotizacion
        self._estado = EstadoAmpliacion.PENDIENTE_AUTORIZACION

    def resolver(self) -> None:
        if self._estado is not EstadoAmpliacion.PENDIENTE_AUTORIZACION:
            raise ReglaDeNegocioViolada("RN-04", "La ampliación no está pendiente de autorización")
        self._estado = EstadoAmpliacion.RESUELTA
