"""Oráculo INDEPENDIENTE del sistema: deriva los resultados esperados solo a partir de los CSV
y de las reglas de INSTRUCCIONES_ALUMNO.txt (y de nuestra interpretación documentada de las acciones)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .loader import Dataset, Operacion

# Estados del sistema -> nombres del flujo de referencia del paquete (los marcados * no existen en el flujo de referencia)
ESTADOS = {
    "Recibido": "RECIBIDA", "Diagnosticado": "DIAGNOSTICADA", "En reparación": "EN_REPARACION",
    "Cerrado": "ENTREGADA", "Cancelado": "CANCELADA",
    "Cotizado": "COTIZADA*", "Autorizado": "AUTORIZADA*", "En espera de refacción": "EN_ESPERA_REFACCION*",
    "Listo para entrega": "LISTA_PARA_ENTREGA*",
}
MINIMO_BENEFICIO = Decimal("1500")


def puede_procesarse(ds: Dataset, op: Operacion) -> bool:
    return ds.actores[op.actor_id].activo and len(op.lineas) >= 1 and op.autorizado


def beneficio_referencia(ds: Dataset, op: Operacion) -> bool:
    return ds.actores[op.actor_id].es_preferente and ds.total(op) >= MINIMO_BENEFICIO and not op.promocion_activa


@dataclass(frozen=True)
class Esperado:
    resultado: str                 # EXITO | RECHAZADA
    estado_final: str
    paso_bloqueante: str | None = None
    codigo_http: int | None = None


def transicion(ds: Dataset, op: Operacion, accion: str) -> Esperado:
    if accion == "aprobar":                 # avanzar un paso válido: RECIBIDA -> DIAGNOSTICADA
        return Esperado("EXITO", "DIAGNOSTICADA")
    if accion == "repetir_aprobacion":      # el segundo intento es inválido
        return Esperado("RECHAZADA", "DIAGNOSTICADA", "aprobar (2.º intento)", 409)
    if accion == "saltar_estado":           # RECIBIDA -> ENTREGADA directo
        return Esperado("RECHAZADA", "RECIBIDA", "cobro/entrega prematura", 409)
    if accion == "cancelar":
        return Esperado("EXITO", "CANCELADA")
    if accion == "completar":               # recorrer el ciclo hasta ENTREGADA
        if not op.lineas:
            return Esperado("RECHAZADA", "DIAGNOSTICADA", "cotizar", 422)
        if any(not ds.recursos[l.recurso_id].habilitado for l in op.lineas):
            return Esperado("RECHAZADA", "DIAGNOSTICADA", "cotizar", 409)
        if not op.autorizado:
            return Esperado("RECHAZADA", "COTIZADA*", "asignar", 409)
        if not ds.actores[op.actor_id].activo:
            return Esperado("RECHAZADA", "AUTORIZADA*", "asignar", 409)
        return Esperado("EXITO", "ENTREGADA")
    raise ValueError(f"Acción desconocida: {accion}")
