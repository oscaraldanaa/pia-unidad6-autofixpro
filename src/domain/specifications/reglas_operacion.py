"""Reglas de evaluación de una operación (orden + cliente) compuestas con AND/OR/NOT.

``puede_procesarse``  = cliente activo AND con al menos un concepto AND con autorización.
``beneficio_referencia`` = cliente preferente AND total >= mínimo AND NOT promoción activa.
Las hojas operan sobre Cliente u Orden; los adaptadores ``SobreCliente``/``SobreOrden`` las
elevan al contexto común ``ContextoOperacion``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..value_objects import Dinero
from .base import Specification
from .reglas_catalogo import ClienteActivoSpec


@dataclass(frozen=True)
class ContextoOperacion:
    cliente: Any   # entities.Cliente
    orden: Any     # entities.OrdenServicio


class ClientePreferenteSpec(Specification[Any]):
    def es_satisfecha_por(self, cliente: Any) -> bool:
        return cliente.es_preferente


class OrdenConDetalleSpec(Specification[Any]):
    """La operación tiene al menos una línea (concepto) cotizada."""

    def es_satisfecha_por(self, orden: Any) -> bool:
        cot = orden.cotizacion_inicial
        return cot is not None and len(cot.conceptos) >= 1


class OrdenAutorizadaSpec(Specification[Any]):
    """El cliente autorizó la cotización (total o parcialmente, RN-05)."""

    def es_satisfecha_por(self, orden: Any) -> bool:
        from ..entities.cotizacion import ResultadoCotizacion  # import diferido (evita ciclo)
        cot = orden.cotizacion_inicial
        return cot is not None and cot.resultado in (ResultadoCotizacion.AUTORIZADA, ResultadoCotizacion.PARCIAL)


class PromocionActivaSpec(Specification[Any]):
    def es_satisfecha_por(self, orden: Any) -> bool:
        return orden.promocion_activa


class TotalMinimoSpec(Specification[Any]):
    """``total_referencia`` (sin descuento ni impuestos) >= mínimo."""

    def __init__(self, minimo: Dinero) -> None:
        self._minimo = minimo

    def es_satisfecha_por(self, orden: Any) -> bool:
        return orden.total_referencia >= self._minimo


class SobreCliente(Specification[ContextoOperacion]):
    def __init__(self, spec: Specification[Any]) -> None:
        self._spec = spec

    def es_satisfecha_por(self, ctx: ContextoOperacion) -> bool:
        return self._spec.es_satisfecha_por(ctx.cliente)


class SobreOrden(Specification[ContextoOperacion]):
    def __init__(self, spec: Specification[Any]) -> None:
        self._spec = spec

    def es_satisfecha_por(self, ctx: ContextoOperacion) -> bool:
        return self._spec.es_satisfecha_por(ctx.orden)


MINIMO_BENEFICIO = Dinero.de(1500)


def puede_procesarse() -> Specification[ContextoOperacion]:
    return SobreCliente(ClienteActivoSpec()) & SobreOrden(OrdenConDetalleSpec()) & SobreOrden(OrdenAutorizadaSpec())


def beneficio_referencia(minimo: Dinero = MINIMO_BENEFICIO) -> Specification[ContextoOperacion]:
    return SobreCliente(ClientePreferenteSpec()) & SobreOrden(TotalMinimoSpec(minimo)) & ~SobreOrden(PromocionActivaSpec())


def criterios(ctx: ContextoOperacion, minimo: Dinero = MINIMO_BENEFICIO) -> dict[str, bool]:
    """Valor de cada hoja (evidencia de por qué una regla compuesta dio verdadero o falso)."""
    return {
        "cliente_activo": SobreCliente(ClienteActivoSpec()).es_satisfecha_por(ctx),
        "con_detalle": SobreOrden(OrdenConDetalleSpec()).es_satisfecha_por(ctx),
        "autorizada": SobreOrden(OrdenAutorizadaSpec()).es_satisfecha_por(ctx),
        "cliente_preferente": SobreCliente(ClientePreferenteSpec()).es_satisfecha_por(ctx),
        "total_minimo": SobreOrden(TotalMinimoSpec(minimo)).es_satisfecha_por(ctx),
        "promocion_activa": SobreOrden(PromocionActivaSpec()).es_satisfecha_por(ctx),
    }
