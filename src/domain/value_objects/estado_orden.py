from enum import Enum


class EstadoOrden(str, Enum):
    """Estados del ciclo de vida (BRD §12, US-01..US-15, BPMN).

    Las transiciones permitidas se formalizarán como State Machine en la Fase 2.
    ``CANCELADO`` proviene del BPMN (rechazo total → cancelar y cerrar orden).
    """

    RECIBIDO = "Recibido"
    DIAGNOSTICADO = "Diagnosticado"
    COTIZADO = "Cotizado"
    AUTORIZADO = "Autorizado"
    EN_REPARACION = "En reparación"
    EN_ESPERA_REFACCION = "En espera de refacción"
    LISTO_PARA_ENTREGA = "Listo para entrega"
    CERRADO = "Cerrado"
    CANCELADO = "Cancelado"
