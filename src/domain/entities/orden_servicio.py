"""Agregado raíz OrdenServicio (Orden de Trabajo / OT).

Frontera de consistencia: cotizaciones, trabajos, solicitudes de refacción,
solicitudes de ampliación y fechas de entrega solo se modifican a través de
esta raíz. Todo cambio de estado pasa por la State Machine
(``ORDEN_STATE_MACHINE``), cuyas guardas son Specifications; cada transición
válida registra el evento ``EstadoOrdenCambiado``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence

from ..events import (
    AmpliacionResuelta, CotizacionAutorizada, CotizacionComplementariaEnviada, CotizacionGenerada,
    CotizacionParcialmenteAutorizada, CotizacionRechazada, DiagnosticoRegistrado, EstadoOrdenCambiado,
    FallaAdicionalDetectada, FechaModificada, OrdenCancelada, OrdenCerrada, OrdenListaParaEntrega,
    OrdenRecibida, RefaccionRecibida, RefaccionSinExistencia, RetrasoPorRefaccion, TrabajosAsignados,
)
from ..shared import AggregateRoot, ReglaDeNegocioViolada, ValorInvalido, utc_now
from ..value_objects import (
    CambioFechaEntrega, ClienteId, ConceptoId, CotizacionId, DatosRecepcion, Dinero, EstadoOrden,
    EvidenciaAutorizacion, FechaEntrega, OrdenServicioId, Porcentaje, SolicitudAmpliacionId,
    SolicitudRefaccionId, TecnicoId, TrabajoId, VehiculoId,
)
from ..state_machine import ORDEN_STATE_MACHINE, DisparadorOrden
from .cliente import Cliente
from .cotizacion import (
    ConceptoCotizacion, Cotizacion, ResultadoCotizacion, TipoConcepto, TipoCotizacion,
)
from .cuenta_flotilla import CondicionesFlotilla, CuentaFlotilla
from .solicitudes import EstadoAmpliacion, SolicitudAmpliacion, SolicitudRefaccion
from .trabajo_reparacion import TrabajoReparacion
from .vehiculo import Vehiculo

_IVA_POR_DEFECTO = Porcentaje.de(16)  # supuesto a validar con el stakeholder


class OrdenServicio(AggregateRoot[OrdenServicioId]):
    def __init__(
        self,
        id: OrdenServicioId,
        cliente_id: ClienteId,
        vehiculo_id: VehiculoId,
        autorizador_id: ClienteId,
        datos_recepcion: DatosRecepcion,
        creada_en: datetime,
        condiciones_flotilla: CondicionesFlotilla | None = None,
        promocion_activa: bool = False,
    ) -> None:
        super().__init__(id)
        self._cliente_id = cliente_id
        self._vehiculo_id = vehiculo_id
        self._autorizador_id = autorizador_id          # RN-14: único responsable de autorizar
        self._datos_recepcion = datos_recepcion
        self._creada_en = creada_en
        self._condiciones_flotilla = condiciones_flotilla
        self._promocion_activa = promocion_activa
        self._estado = EstadoOrden.RECIBIDO
        self._hallazgos: tuple[str, ...] = ()
        self._tecnico_diagnostico: TecnicoId | None = None
        self._cotizacion_inicial: Cotizacion | None = None
        self._solicitudes_ampliacion: list[SolicitudAmpliacion] = []
        self._solicitudes_refaccion: list[SolicitudRefaccion] = []
        self._trabajos: list[TrabajoReparacion] = []
        self._fecha_entrega: FechaEntrega | None = None
        self._historial_fechas: list[CambioFechaEntrega] = []
        self._monto_cobrado: Dinero | None = None

    # ------------------------------------------------------------------ fábrica
    @classmethod
    def registrar_ingreso(
        cls,
        cliente: Cliente,
        vehiculo: Vehiculo,
        datos_recepcion: DatosRecepcion,
        cuenta_flotilla: CuentaFlotilla | None = None,
        id: OrdenServicioId | None = None,
        ahora: datetime | None = None,
        promocion_activa: bool = False,
    ) -> "OrdenServicio":
        """RN-01 (datos completos), RN-09 (reconocer flotilla), RN-14 (único autorizador)."""
        if vehiculo.es_de_flotilla:
            if cuenta_flotilla is None or cuenta_flotilla.id != vehiculo.cuenta_flotilla_id:
                raise ReglaDeNegocioViolada("RN-09", "El vehículo es de flotilla: se requiere su cuenta B2B")
            autorizador = cuenta_flotilla.autorizador_corporativo_id
            condiciones = cuenta_flotilla.condiciones
        else:
            autorizador, condiciones = cliente.id, None
        orden = cls(id or OrdenServicioId.generar(), cliente.id, vehiculo.id, autorizador,
                    datos_recepcion, ahora or utc_now(), condiciones, promocion_activa)
        orden._registrar_evento(OrdenRecibida(orden_id=orden.id, es_flotilla=condiciones is not None))
        return orden

    # ------------------------------------------------------------------ consultas
    cliente_id = property(lambda s: s._cliente_id)
    vehiculo_id = property(lambda s: s._vehiculo_id)
    autorizador_id = property(lambda s: s._autorizador_id)
    datos_recepcion = property(lambda s: s._datos_recepcion)
    creada_en = property(lambda s: s._creada_en)
    estado = property(lambda s: s._estado)
    hallazgos = property(lambda s: s._hallazgos)
    cotizacion_inicial = property(lambda s: s._cotizacion_inicial)
    fecha_entrega = property(lambda s: s._fecha_entrega)
    monto_cobrado = property(lambda s: s._monto_cobrado)
    condiciones_flotilla = property(lambda s: s._condiciones_flotilla)
    promocion_activa = property(lambda s: s._promocion_activa)
    tecnico_diagnostico_id = property(lambda s: s._tecnico_diagnostico)

    @property
    def es_flotilla(self) -> bool:
        return self._condiciones_flotilla is not None

    @property
    def trabajos(self) -> tuple[TrabajoReparacion, ...]:
        return tuple(self._trabajos)

    @property
    def solicitudes_refaccion(self) -> tuple[SolicitudRefaccion, ...]:
        return tuple(self._solicitudes_refaccion)

    @property
    def solicitudes_ampliacion(self) -> tuple[SolicitudAmpliacion, ...]:
        return tuple(self._solicitudes_ampliacion)

    @property
    def historial_fechas(self) -> tuple[CambioFechaEntrega, ...]:
        return tuple(self._historial_fechas)

    @property
    def total_referencia(self) -> Dinero:
        """Suma(precio × cantidad) de la cotización inicial, sin descuento ni impuestos."""
        cot = self._cotizacion_inicial
        return cot.desglose.subtotal_bruto if cot else Dinero.cero()

    @property
    def total_autorizado(self) -> Dinero:
        """RF-15: suma (con descuento e impuestos) de los conceptos autorizados."""
        cotizaciones = [self._cotizacion_inicial] if self._cotizacion_inicial else []
        cotizaciones += [s.cotizacion for s in self._solicitudes_ampliacion if s.cotizacion]
        return Dinero.sumar(c.desglose_autorizado.total for c in cotizaciones)

    # ------------------------------------------------------------------ diagnóstico (RF-02)
    def registrar_diagnostico(self, tecnico_id: TecnicoId, hallazgos: Sequence[str]) -> None:
        limpios = tuple(h.strip() for h in hallazgos if h and h.strip())
        if not limpios:
            raise ValorInvalido("El diagnóstico requiere al menos un hallazgo")
        self._transicionar(DisparadorOrden.DIAGNOSTICAR)
        self._hallazgos, self._tecnico_diagnostico = limpios, tecnico_id
        self._registrar_evento(DiagnosticoRegistrado(orden_id=self.id, tecnico_id=tecnico_id))

    # ------------------------------------------------------------------ cotización (RF-03, RF-04)
    def generar_cotizacion(self, conceptos: Sequence[ConceptoCotizacion],
                           tasa_impuesto: Porcentaje = _IVA_POR_DEFECTO, ahora: datetime | None = None) -> None:
        cotizacion = Cotizacion(
            CotizacionId.generar(), TipoCotizacion.INICIAL, list(conceptos), ahora or utc_now(),
            tasa_impuesto, self._descuento())
        self._transicionar(DisparadorOrden.COTIZAR)
        self._cotizacion_inicial = cotizacion
        self._registrar_evento(CotizacionGenerada(orden_id=self.id))

    def responder_cotizacion(self, decisiones: Mapping[ConceptoId, bool], evidencia: EvidenciaAutorizacion) -> None:
        """RN-05 / RN-11. Rechazo total cancela la orden (BPMN)."""
        self._requerir_estado("RN-05", EstadoOrden.COTIZADO)
        cot = self._cotizacion_inicial
        assert cot is not None
        cot.responder(decisiones, evidencia)
        if cot.resultado is ResultadoCotizacion.RECHAZADA:
            self._transicionar(DisparadorOrden.RECHAZAR_COTIZACION)
            self._registrar_evento(CotizacionRechazada(orden_id=self.id))
            return
        self._transicionar(DisparadorOrden.AUTORIZAR)
        if cot.resultado is ResultadoCotizacion.AUTORIZADA:
            self._registrar_evento(CotizacionAutorizada(orden_id=self.id))
        else:
            self._registrar_evento(CotizacionParcialmenteAutorizada(
                orden_id=self.id,
                conceptos_autorizados=tuple(c.id for c in cot.conceptos_autorizados),
                conceptos_rechazados=tuple(c.id for c in cot.conceptos_rechazados)))

    # ------------------------------------------------------------------ asignación (RF-05)
    def asignar_trabajos(self, tecnico_id: TecnicoId) -> None:
        self._requerir_estado("RN-13", EstadoOrden.AUTORIZADO)
        assert self._cotizacion_inicial is not None
        nuevos = self._construir_trabajos(self._cotizacion_inicial, tecnico_id)
        if not nuevos:
            raise ReglaDeNegocioViolada("RN-13", "No hay trabajos de mano de obra autorizados para asignar")
        self._transicionar(DisparadorOrden.INICIAR_REPARACION)
        self._trabajos.extend(nuevos)
        self._registrar_evento(TrabajosAsignados(orden_id=self.id, tecnico_id=tecnico_id))

    # ------------------------------------------------------------------ refacciones (RF-06, RF-07)
    def reportar_refaccion_sin_existencia(self, concepto_id: ConceptoId, reposicion_estimada: datetime | None = None,
                                          ahora: datetime | None = None) -> SolicitudRefaccion:
        self._requerir_estado("RN-07", EstadoOrden.EN_REPARACION, EstadoOrden.EN_ESPERA_REFACCION)
        concepto = next((c for c in self._conceptos_autorizados() if c.id == concepto_id), None)
        if concepto is None or concepto.tipo is not TipoConcepto.REFACCION:
            raise ReglaDeNegocioViolada("RN-07", "El concepto no es una refacción autorizada de esta orden")
        if any(s.pendiente and s.concepto_id == concepto_id for s in self._solicitudes_refaccion):
            raise ReglaDeNegocioViolada("RN-07", "Ya existe una solicitud pendiente para esta refacción")
        solicitud = SolicitudRefaccion(SolicitudRefaccionId.generar(), concepto_id, concepto.descripcion,
                                       ahora or utc_now(), reposicion_estimada)
        self._solicitudes_refaccion.append(solicitud)
        if self._estado is EstadoOrden.EN_REPARACION:
            self._transicionar(DisparadorOrden.ESPERAR_REFACCION)
        self._registrar_evento(RefaccionSinExistencia(orden_id=self.id, solicitud_id=solicitud.id))
        return solicitud

    def actualizar_reposicion(self, solicitud_id: SolicitudRefaccionId, nueva_fecha: datetime, motivo: str) -> None:
        """RN-03: notificar al cliente motivo y nuevo tiempo estimado."""
        self._requerir_estado("RN-03", EstadoOrden.EN_ESPERA_REFACCION)
        if not motivo.strip():
            raise ValorInvalido("RN-03: el motivo del retraso es obligatorio")
        self._solicitud_refaccion(solicitud_id).actualizar_reposicion(nueva_fecha)
        self._registrar_evento(RetrasoPorRefaccion(orden_id=self.id, solicitud_id=solicitud_id,
                                                   motivo=motivo.strip(), nueva_fecha_reposicion=nueva_fecha))

    def recibir_refaccion(self, solicitud_id: SolicitudRefaccionId) -> None:
        self._requerir_estado("RN-07", EstadoOrden.EN_ESPERA_REFACCION)
        self._solicitud_refaccion(solicitud_id).marcar_recibida()
        self._registrar_evento(RefaccionRecibida(orden_id=self.id, solicitud_id=solicitud_id))
        if not any(s.pendiente for s in self._solicitudes_refaccion):
            self._transicionar(DisparadorOrden.REANUDAR_REPARACION)

    # ------------------------------------------------------------------ fallas adicionales (RF-08..RF-10)
    def registrar_falla_adicional(self, tecnico_id: TecnicoId, descripcion: str,
                                  ahora: datetime | None = None) -> SolicitudAmpliacion:
        self._requerir_estado("RN-04", EstadoOrden.EN_REPARACION)
        if not descripcion.strip():
            raise ValorInvalido("La descripción de la falla adicional es obligatoria")
        solicitud = SolicitudAmpliacion(SolicitudAmpliacionId.generar(), tecnico_id, descripcion.strip(),
                                        ahora or utc_now())
        self._solicitudes_ampliacion.append(solicitud)
        self._registrar_evento(FallaAdicionalDetectada(orden_id=self.id, solicitud_id=solicitud.id,
                                                       tecnico_id=tecnico_id))
        return solicitud

    def enviar_cotizacion_complementaria(self, solicitud_id: SolicitudAmpliacionId,
                                         conceptos: Sequence[ConceptoCotizacion],
                                         tasa_impuesto: Porcentaje = _IVA_POR_DEFECTO,
                                         ahora: datetime | None = None) -> None:
        self._requerir_estado("RN-04", EstadoOrden.EN_REPARACION, EstadoOrden.EN_ESPERA_REFACCION)
        solicitud = self._solicitud_ampliacion(solicitud_id)
        solicitud.adjuntar_cotizacion(Cotizacion(
            CotizacionId.generar(), TipoCotizacion.COMPLEMENTARIA, list(conceptos), ahora or utc_now(),
            tasa_impuesto, self._descuento()))
        self._registrar_evento(CotizacionComplementariaEnviada(orden_id=self.id, solicitud_id=solicitud_id))

    def responder_ampliacion(self, solicitud_id: SolicitudAmpliacionId, decisiones: Mapping[ConceptoId, bool],
                             evidencia: EvidenciaAutorizacion) -> None:
        """RN-04 / RN-13: solo lo autorizado habilita trabajo al técnico."""
        self._requerir_estado("RN-04", EstadoOrden.EN_REPARACION, EstadoOrden.EN_ESPERA_REFACCION)
        solicitud = self._solicitud_ampliacion(solicitud_id)
        if solicitud.estado is not EstadoAmpliacion.PENDIENTE_AUTORIZACION or solicitud.cotizacion is None:
            raise ReglaDeNegocioViolada("RN-04", "La ampliación no tiene una cotización pendiente de autorización")
        solicitud.cotizacion.responder(decisiones, evidencia)
        solicitud.resolver()
        self._trabajos.extend(self._construir_trabajos(solicitud.cotizacion, solicitud.tecnico_id))
        self._registrar_evento(AmpliacionResuelta(orden_id=self.id, solicitud_id=solicitud_id,
                                                  resultado=solicitud.cotizacion.resultado.value))

    # ------------------------------------------------------------------ fecha de entrega (RF-11)
    def programar_fecha_entrega(self, fecha: FechaEntrega, ahora: datetime | None = None) -> None:
        self._requerir_activa("RN-06")
        if self._fecha_entrega is not None:
            raise ReglaDeNegocioViolada("RN-06", "Ya hay fecha programada; use modificar_fecha_entrega")
        if not fecha.es_valida(ahora or utc_now()):
            raise ValorInvalido("La fecha de entrega no puede estar en el pasado")
        self._fecha_entrega = fecha

    def modificar_fecha_entrega(self, nueva: FechaEntrega, justificacion: str, ahora: datetime | None = None) -> None:
        self._requerir_activa("RN-06")
        if self._fecha_entrega is None:
            raise ReglaDeNegocioViolada("RN-06", "No hay fecha previa; use programar_fecha_entrega")
        momento = ahora or utc_now()
        if not nueva.es_valida(momento):
            raise ValorInvalido("La fecha de entrega no puede estar en el pasado")
        cambio = CambioFechaEntrega(self._fecha_entrega, nueva, justificacion, momento)
        self._historial_fechas.append(cambio)
        self._fecha_entrega = nueva
        self._registrar_evento(FechaModificada(orden_id=self.id, anterior=cambio.anterior.fecha_estimada,
                                               nueva=nueva.fecha_estimada, justificacion=cambio.justificacion))

    # ------------------------------------------------------------------ calidad, entrega y cobro (RF-13..RF-15)
    def finalizar_trabajo(self, trabajo_id: TrabajoId) -> None:
        self._requerir_estado("RN-01", EstadoOrden.EN_REPARACION)
        self._trabajo(trabajo_id).finalizar()

    def aprobar_revision_calidad(self, trabajo_id: TrabajoId) -> None:
        self._requerir_estado("RN-01", EstadoOrden.EN_REPARACION)
        self._trabajo(trabajo_id).aprobar_revision()

    def marcar_lista_para_entrega(self) -> None:
        self._transicionar(DisparadorOrden.PREPARAR_ENTREGA)  # guarda: OrdenListaParaEntregaSpec
        self._registrar_evento(OrdenListaParaEntrega(orden_id=self.id))

    def registrar_cobro_y_cerrar(self, monto: Dinero) -> None:
        """RF-15: se cobra únicamente lo autorizado y entregado."""
        self._requerir_estado("RN-01", EstadoOrden.LISTO_PARA_ENTREGA)
        if monto != self.total_autorizado:
            raise ReglaDeNegocioViolada(
                "RN-04", f"El cobro ({monto}) debe igualar el total autorizado ({self.total_autorizado})")
        self._transicionar(DisparadorOrden.CERRAR)
        self._monto_cobrado = monto
        self._registrar_evento(OrdenCerrada(orden_id=self.id))

    def cancelar(self, motivo: str) -> None:
        """Cancelación voluntaria; solo antes de iniciar la reparación (State Machine)."""
        if not motivo or not motivo.strip():
            raise ValorInvalido("El motivo de cancelación es obligatorio")
        self._transicionar(DisparadorOrden.CANCELAR)
        self._registrar_evento(OrdenCancelada(orden_id=self.id, motivo=motivo.strip()))

    # ------------------------------------------------------------------ internos
    def _transicionar(self, disparador: DisparadorOrden) -> None:
        """Único punto donde cambia ``_estado``: valida con la State Machine y emite el evento."""
        anterior = self._estado
        nuevo = ORDEN_STATE_MACHINE.destino(anterior, disparador, self)  # lanza TransicionInvalida
        self._estado = nuevo
        self._registrar_evento(EstadoOrdenCambiado(
            orden_id=self.id, anterior=anterior.value, nuevo=nuevo.value, disparador=disparador.value))

    def _requerir_estado(self, regla: str, *permitidos: EstadoOrden) -> None:
        if self._estado not in permitidos:
            esperados = ", ".join(e.value for e in permitidos)
            raise ReglaDeNegocioViolada(regla, f"Operación inválida en estado '{self._estado.value}' (se requiere: {esperados})")

    def _requerir_activa(self, regla: str) -> None:
        if self._estado in (EstadoOrden.CERRADO, EstadoOrden.CANCELADO):
            raise ReglaDeNegocioViolada(regla, f"La orden está {self._estado.value.lower()}")

    def _descuento(self) -> Porcentaje:
        return self._condiciones_flotilla.descuento if self._condiciones_flotilla else Porcentaje.cero()

    def _conceptos_autorizados(self) -> list[ConceptoCotizacion]:
        cotizaciones = [self._cotizacion_inicial] if self._cotizacion_inicial else []
        cotizaciones += [s.cotizacion for s in self._solicitudes_ampliacion if s.cotizacion]
        return [c for cot in cotizaciones for c in cot.conceptos_autorizados]

    @staticmethod
    def _construir_trabajos(cotizacion: Cotizacion, tecnico_id: TecnicoId) -> list[TrabajoReparacion]:
        """RN-13: un trabajo nace solo de un concepto de mano de obra autorizado."""
        return [TrabajoReparacion(TrabajoId.generar(), c.id, c.descripcion, tecnico_id)
                for c in cotizacion.conceptos_autorizados if c.tipo is TipoConcepto.MANO_DE_OBRA]

    def _trabajo(self, trabajo_id: TrabajoId) -> TrabajoReparacion:
        return self._buscar(self._trabajos, trabajo_id, "trabajo")

    def _solicitud_refaccion(self, id: SolicitudRefaccionId) -> SolicitudRefaccion:
        return self._buscar(self._solicitudes_refaccion, id, "solicitud de refacción")

    def _solicitud_ampliacion(self, id: SolicitudAmpliacionId) -> SolicitudAmpliacion:
        return self._buscar(self._solicitudes_ampliacion, id, "solicitud de ampliación")

    @staticmethod
    def _buscar(coleccion, id, nombre):
        for e in coleccion:
            if e.id == id:
                return e
        raise ReglaDeNegocioViolada("RN-01", f"No existe {nombre} {id} en esta orden")
