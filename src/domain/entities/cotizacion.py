"""Cotización y sus conceptos (entidades internas del agregado OrdenServicio).

Diferencia con el diagrama DDD inicial: ``Cotizacion`` pasa de Value Object a
Entidad interna porque RN-05/RF-04 exigen autorizar o rechazar cada concepto
por separado y conservar su evidencia (ver ADR-001, sección "Ajustes").
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping

from ..shared import Entity, ReglaDeNegocioViolada, ValorInvalido, ValueObject
from ..value_objects import (
    ConceptoId, CotizacionId, Dinero, EvidenciaAutorizacion, Porcentaje, RecursoId,
)


class TipoConcepto(str, Enum):
    MANO_DE_OBRA = "mano_de_obra"
    REFACCION = "refaccion"


class EstadoConcepto(str, Enum):
    PENDIENTE = "pendiente"
    AUTORIZADO = "autorizado"
    RECHAZADO = "rechazado"


class TipoCotizacion(str, Enum):
    INICIAL = "inicial"
    COMPLEMENTARIA = "complementaria"


class ResultadoCotizacion(str, Enum):
    PENDIENTE = "pendiente"
    AUTORIZADA = "autorizada"
    PARCIAL = "parcial"
    RECHAZADA = "rechazada"


@dataclass(frozen=True)
class DesgloseMonetario(ValueObject):
    subtotal_bruto: Dinero
    descuento: Dinero
    subtotal: Dinero
    impuestos: Dinero
    total: Dinero


class ConceptoCotizacion(Entity[ConceptoId]):
    def __init__(
        self,
        id: ConceptoId,
        tipo: TipoConcepto,
        descripcion: str,
        precio_unitario: Dinero,
        cantidad: Decimal | int | str = 1,
        recurso_id: RecursoId | None = None,
    ) -> None:
        super().__init__(id)
        cantidad = Decimal(str(cantidad))
        if not descripcion.strip():
            raise ValorInvalido("La descripción del concepto es obligatoria")
        if cantidad <= 0:
            raise ValorInvalido("La cantidad debe ser mayor a cero")
        self._tipo = tipo
        self._descripcion = descripcion.strip()
        self._precio_unitario = precio_unitario
        self._cantidad = cantidad
        self._recurso_id = recurso_id
        self._estado = EstadoConcepto.PENDIENTE
        self._evidencia: EvidenciaAutorizacion | None = None

    tipo = property(lambda s: s._tipo)
    descripcion = property(lambda s: s._descripcion)
    precio_unitario = property(lambda s: s._precio_unitario)
    cantidad = property(lambda s: s._cantidad)
    recurso_id = property(lambda s: s._recurso_id)   # recurso del catálogo del que proviene (opcional)
    estado = property(lambda s: s._estado)
    evidencia = property(lambda s: s._evidencia)

    @property
    def importe(self) -> Dinero:
        return self._precio_unitario.por(self._cantidad)

    @property
    def autorizado(self) -> bool:
        return self._estado is EstadoConcepto.AUTORIZADO

    def _decidir(self, estado: EstadoConcepto, evidencia: EvidenciaAutorizacion) -> None:
        if self._estado is not EstadoConcepto.PENDIENTE:
            raise ReglaDeNegocioViolada("RN-05", "El concepto ya tiene una decisión registrada")
        self._estado = estado
        self._evidencia = evidencia


class Cotizacion(Entity[CotizacionId]):
    def __init__(
        self,
        id: CotizacionId,
        tipo: TipoCotizacion,
        conceptos: list[ConceptoCotizacion],
        emitida_en: datetime,
        tasa_impuesto: Porcentaje = Porcentaje.de(16),
        descuento: Porcentaje = Porcentaje.cero(),
    ) -> None:
        super().__init__(id)
        if not conceptos:
            raise ValorInvalido("Una cotización requiere al menos un concepto")
        ids = [c.id for c in conceptos]
        if len(set(ids)) != len(ids):
            raise ValorInvalido("Conceptos duplicados en la cotización")
        self._tipo = tipo
        self._conceptos = list(conceptos)
        self._emitida_en = emitida_en
        self._tasa_impuesto = tasa_impuesto
        self._descuento = descuento
        self._respondida = False

    tipo = property(lambda s: s._tipo)
    emitida_en = property(lambda s: s._emitida_en)
    respondida = property(lambda s: s._respondida)
    tasa_impuesto = property(lambda s: s._tasa_impuesto)
    descuento = property(lambda s: s._descuento)

    @property
    def conceptos(self) -> tuple[ConceptoCotizacion, ...]:
        return tuple(self._conceptos)

    @property
    def conceptos_autorizados(self) -> tuple[ConceptoCotizacion, ...]:
        return tuple(c for c in self._conceptos if c.autorizado)

    @property
    def conceptos_rechazados(self) -> tuple[ConceptoCotizacion, ...]:
        return tuple(c for c in self._conceptos if c.estado is EstadoConcepto.RECHAZADO)

    def _desglosar(self, conceptos: list[ConceptoCotizacion] | tuple[ConceptoCotizacion, ...]) -> DesgloseMonetario:
        bruto = Dinero.sumar(c.importe for c in conceptos)
        descuento = bruto.aplicar(self._descuento)
        subtotal = bruto - descuento
        impuestos = subtotal.aplicar(self._tasa_impuesto)
        return DesgloseMonetario(bruto, descuento, subtotal, impuestos, subtotal + impuestos)

    @property
    def desglose(self) -> DesgloseMonetario:
        return self._desglosar(self._conceptos)

    @property
    def desglose_autorizado(self) -> DesgloseMonetario:
        """Solo conceptos autorizados (RF-15: se cobra únicamente lo autorizado)."""
        return self._desglosar(self.conceptos_autorizados)

    @property
    def resultado(self) -> ResultadoCotizacion:
        if not self._respondida:
            return ResultadoCotizacion.PENDIENTE
        n_aut = len(self.conceptos_autorizados)
        if n_aut == len(self._conceptos):
            return ResultadoCotizacion.AUTORIZADA
        return ResultadoCotizacion.PARCIAL if n_aut else ResultadoCotizacion.RECHAZADA

    def responder(self, decisiones: Mapping[ConceptoId, bool], evidencia: EvidenciaAutorizacion) -> None:
        """RN-05: autorización/rechazo total o parcial con evidencia (RN-11)."""
        if self._respondida:
            raise ReglaDeNegocioViolada("RN-05", "La cotización ya fue respondida")
        if set(decisiones) != {c.id for c in self._conceptos}:
            raise ReglaDeNegocioViolada("RN-05", "Debe decidirse cada concepto de la cotización")
        for c in self._conceptos:
            c._decidir(EstadoConcepto.AUTORIZADO if decisiones[c.id] else EstadoConcepto.RECHAZADO, evidencia)
        self._respondida = True
