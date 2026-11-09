"""Casos de uso de comando sobre la Orden de Servicio (US-01..US-15)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable

from ...domain.entities import ConceptoCotizacion, OrdenServicio, TipoConcepto
from ...domain.shared import ReglaDeNegocioViolada, ValorInvalido
from ...domain.specifications import ClienteActivoSpec, MontoMinimoSpec, TecnicoDisponibleSpec
from ...domain.value_objects import (
    ClienteId, ConceptoId, DatosRecepcion, Dinero, FechaEntrega, Kilometraje, NivelCombustible,
    OrdenServicioId, Porcentaje, RecursoId, SolicitudAmpliacionId, SolicitudRefaccionId, TecnicoId, TrabajoId, VehiculoId,
)
from ..dto import (
    ActualizarReposicionCmd, AsignarTrabajosCmd, CancelarOrdenCmd, ConceptoNuevoDTO, DefinirFechaEntregaCmd,
    EnviarCotizacionComplementariaCmd, GenerarCotizacionCmd, OrdenCmd, OrdenDetalleDTO,
    RegistrarCobroCmd, RegistrarDiagnosticoCmd, RegistrarFallaAdicionalCmd, RegistrarIngresoCmd,
    ReportarRefaccionSinExistenciaCmd, ResponderAmpliacionCmd, ResponderCotizacionCmd, SolicitudRefaccionCmd,
    TrabajoCmd, a_orden_dto,
)
from ..ports import EventBus, UnitOfWorkFactory
from .base import CasoDeUso, decisiones_a_dominio


def _conceptos(dtos: tuple[ConceptoNuevoDTO, ...], uow) -> list[ConceptoCotizacion]:
    """Concepto de catálogo (precio oficial + validación de habilitado/capacidad) o libre."""
    conceptos = []
    for d in dtos:
        if d.recurso_id:
            item = uow.catalogo.obtener(RecursoId.desde_str(d.recurso_id))
            conceptos.append(item.a_concepto(d.cantidad, TipoConcepto(d.tipo)))
        elif d.descripcion and d.precio_unitario is not None:
            conceptos.append(ConceptoCotizacion(ConceptoId.generar(), TipoConcepto(d.tipo), d.descripcion,
                                                Dinero.de(d.precio_unitario), d.cantidad))
        else:
            raise ValorInvalido("Cada concepto requiere recurso_id o (descripción y precio)")
    return conceptos


class RegistrarIngresoVehiculo(CasoDeUso):
    """US-01 / RF-01 / RF-17. Reconoce flotilla (RN-09) y exige cliente activo (Specification)."""

    def ejecutar(self, cmd: RegistrarIngresoCmd) -> OrdenDetalleDTO:
        with self._uow_factory() as uow:
            cliente = uow.clientes.obtener(ClienteId.desde_str(cmd.cliente_id))
            vehiculo = uow.vehiculos.obtener(VehiculoId.desde_str(cmd.vehiculo_id))
            ClienteActivoSpec().verificar(cliente, "RN-01", "El cliente está inactivo y no puede abrir órdenes")
            cuenta = uow.cuentas_flotilla.obtener(vehiculo.cuenta_flotilla_id) if vehiculo.cuenta_flotilla_id else None
            datos = DatosRecepcion(Kilometraje(cmd.kilometraje), NivelCombustible(cmd.combustible),
                                   tuple(cmd.danos_visibles), cmd.motivo_ingreso)
            orden = OrdenServicio.registrar_ingreso(cliente, vehiculo, datos, cuenta, ahora=self._reloj(),
                                                    promocion_activa=cmd.promocion_activa)
            vehiculo.actualizar_kilometraje(datos.kilometraje)
            uow.vehiculos.guardar(vehiculo)
            uow.ordenes.guardar(orden)
            eventos, dto = orden.recolectar_eventos(), a_orden_dto(orden)
            uow.commit()
        self._bus.publicar(eventos)
        return dto


class RegistrarDiagnostico(CasoDeUso):
    def ejecutar(self, cmd: RegistrarDiagnosticoCmd) -> OrdenDetalleDTO:
        def accion(orden, uow):
            tecnico = uow.tecnicos.obtener(TecnicoId.desde_str(cmd.tecnico_id))
            orden.registrar_diagnostico(tecnico.id, cmd.hallazgos)
        return self._sobre_orden(cmd.orden_id, accion)


class GenerarCotizacion(CasoDeUso):
    def __init__(self, uow_factory: UnitOfWorkFactory, bus: EventBus,
                 tasa_impuesto: Porcentaje = Porcentaje.de(16), **kw) -> None:
        super().__init__(uow_factory, bus, **kw)
        self._tasa = tasa_impuesto

    def ejecutar(self, cmd: GenerarCotizacionCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, uow: o.generar_cotizacion(
            _conceptos(cmd.conceptos, uow), self._tasa, self._reloj()))


class ResponderCotizacion(CasoDeUso):
    """US-04 / RF-04 / RF-18: autorización o rechazo total/parcial con evidencia."""

    def ejecutar(self, cmd: ResponderCotizacionCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.responder_cotizacion(
            decisiones_a_dominio(cmd.decisiones), self._evidencia(cmd.evidencia)))


class AsignarTrabajos(CasoDeUso):
    """US-05 / RF-05. Precondiciones (Specification): cliente activo y técnico disponible."""

    def ejecutar(self, cmd: AsignarTrabajosCmd) -> OrdenDetalleDTO:
        def accion(orden, uow):
            tecnico = uow.tecnicos.obtener(TecnicoId.desde_str(cmd.tecnico_id))
            cliente = uow.clientes.obtener(orden.cliente_id)
            ClienteActivoSpec().verificar(cliente, "EXT-01", "El cliente está inactivo: no se asignan trabajos")
            TecnicoDisponibleSpec().verificar(tecnico, "RN-12", f"El técnico {tecnico.nombre} no está disponible")
            orden.asignar_trabajos(tecnico.id)
        return self._sobre_orden(cmd.orden_id, accion)


class ReportarRefaccionSinExistencia(CasoDeUso):
    """US-06 / RF-06 (RN-07)."""

    def ejecutar(self, cmd: ReportarRefaccionSinExistenciaCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.reportar_refaccion_sin_existencia(
            ConceptoId.desde_str(cmd.concepto_id), cmd.reposicion_estimada, self._reloj()))


class ActualizarReposicion(CasoDeUso):
    """US-07 / RF-07 (RN-03): dispara la notificación de retraso."""

    def ejecutar(self, cmd: ActualizarReposicionCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.actualizar_reposicion(
            SolicitudRefaccionId.desde_str(cmd.solicitud_id), cmd.nueva_fecha, cmd.motivo))


class RecibirRefaccion(CasoDeUso):
    def ejecutar(self, cmd: SolicitudRefaccionCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.recibir_refaccion(
            SolicitudRefaccionId.desde_str(cmd.solicitud_id)))


class RegistrarFallaAdicional(CasoDeUso):
    """US-08 / RF-08 (RN-04)."""

    def ejecutar(self, cmd: RegistrarFallaAdicionalCmd) -> OrdenDetalleDTO:
        def accion(orden, uow):
            tecnico = uow.tecnicos.obtener(TecnicoId.desde_str(cmd.tecnico_id))
            orden.registrar_falla_adicional(tecnico.id, cmd.descripcion, self._reloj())
        return self._sobre_orden(cmd.orden_id, accion)


class EnviarCotizacionComplementaria(CasoDeUso):
    """US-09 / RF-09."""

    def __init__(self, uow_factory: UnitOfWorkFactory, bus: EventBus,
                 tasa_impuesto: Porcentaje = Porcentaje.de(16), **kw) -> None:
        super().__init__(uow_factory, bus, **kw)
        self._tasa = tasa_impuesto

    def ejecutar(self, cmd: EnviarCotizacionComplementariaCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, uow: o.enviar_cotizacion_complementaria(
            SolicitudAmpliacionId.desde_str(cmd.solicitud_id), _conceptos(cmd.conceptos, uow), self._tasa,
            self._reloj()))


class ResponderAmpliacion(CasoDeUso):
    """US-10 / RF-10 (RN-13)."""

    def ejecutar(self, cmd: ResponderAmpliacionCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.responder_ampliacion(
            SolicitudAmpliacionId.desde_str(cmd.solicitud_id), decisiones_a_dominio(cmd.decisiones),
            self._evidencia(cmd.evidencia)))


class DefinirFechaEntrega(CasoDeUso):
    """US-11 / RF-11: programa la primera fecha o modifica la vigente con justificación (RN-06)."""

    def ejecutar(self, cmd: DefinirFechaEntregaCmd) -> OrdenDetalleDTO:
        def accion(orden, _):
            fecha = FechaEntrega(cmd.fecha_estimada)
            if orden.fecha_entrega is None:
                orden.programar_fecha_entrega(fecha, self._reloj())
            else:
                orden.modificar_fecha_entrega(fecha, cmd.justificacion or "", self._reloj())
        return self._sobre_orden(cmd.orden_id, accion)


class FinalizarTrabajo(CasoDeUso):
    """US-13 / RF-13."""

    def ejecutar(self, cmd: TrabajoCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.finalizar_trabajo(TrabajoId.desde_str(cmd.trabajo_id)))


class AprobarRevisionCalidad(CasoDeUso):
    def ejecutar(self, cmd: TrabajoCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id,
                                 lambda o, _: o.aprobar_revision_calidad(TrabajoId.desde_str(cmd.trabajo_id)))


class MarcarListaParaEntrega(CasoDeUso):
    """US-14 / RF-14: la guarda de la State Machine usa OrdenListaParaEntregaSpec."""

    def ejecutar(self, cmd: OrdenCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.marcar_lista_para_entrega())


class RegistrarCobroYCerrar(CasoDeUso):
    """US-15 / RF-15."""

    def ejecutar(self, cmd: RegistrarCobroCmd) -> OrdenDetalleDTO:
        def accion(orden, _):
            monto = Dinero.de(cmd.monto)
            MontoMinimoSpec(Dinero.de("0.01")).verificar(monto, "RN-04", "El cobro debe ser mayor a cero")
            orden.registrar_cobro_y_cerrar(monto)
        return self._sobre_orden(cmd.orden_id, accion)


class CancelarOrden(CasoDeUso):
    def ejecutar(self, cmd: CancelarOrdenCmd) -> OrdenDetalleDTO:
        return self._sobre_orden(cmd.orden_id, lambda o, _: o.cancelar(cmd.motivo))
