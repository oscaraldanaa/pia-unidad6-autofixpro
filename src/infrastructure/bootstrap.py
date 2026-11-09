"""Raíz de composición: ensambla adaptadores, casos de uso y manejadores."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from ..application import use_cases as uc
from ..application.handlers import NotificarCambioFechaEntrega, NotificarRetrasoPorRefaccion
from ..application.ports import EventBus, Notificador, UnitOfWorkFactory
from ..domain.events import FechaModificada, OrdenEvent, RetrasoPorRefaccion
from ..domain.value_objects import Porcentaje
from .config import Settings, load_settings
from .messaging import InProcessEventBus, LogNotificador
from .persistence import SqlUnitOfWork, crear_engine, crear_session_factory, crear_tablas
from .persistence.auditoria import AuditoriaEventosSql


@dataclass
class Contenedor:
    settings: Settings
    engine: Engine
    uow_factory: UnitOfWorkFactory
    bus: EventBus
    notificador: Notificador
    # catálogos
    registrar_cliente: uc.RegistrarCliente
    registrar_vehiculo: uc.RegistrarVehiculo
    registrar_tecnico: uc.RegistrarTecnico
    registrar_cuenta_flotilla: uc.RegistrarCuentaFlotilla
    cambiar_estado_cliente: uc.CambiarEstadoCliente
    registrar_item_catalogo: uc.RegistrarItemCatalogo
    consultar_catalogo: uc.ConsultarCatalogo
    # órdenes
    registrar_ingreso: uc.RegistrarIngresoVehiculo
    registrar_diagnostico: uc.RegistrarDiagnostico
    generar_cotizacion: uc.GenerarCotizacion
    responder_cotizacion: uc.ResponderCotizacion
    asignar_trabajos: uc.AsignarTrabajos
    reportar_refaccion: uc.ReportarRefaccionSinExistencia
    actualizar_reposicion: uc.ActualizarReposicion
    recibir_refaccion: uc.RecibirRefaccion
    registrar_falla_adicional: uc.RegistrarFallaAdicional
    enviar_cotizacion_complementaria: uc.EnviarCotizacionComplementaria
    responder_ampliacion: uc.ResponderAmpliacion
    definir_fecha_entrega: uc.DefinirFechaEntrega
    finalizar_trabajo: uc.FinalizarTrabajo
    aprobar_revision_calidad: uc.AprobarRevisionCalidad
    marcar_lista_para_entrega: uc.MarcarListaParaEntrega
    registrar_cobro: uc.RegistrarCobroYCerrar
    cancelar_orden: uc.CancelarOrden
    # consultas
    consultar_estado: uc.ConsultarEstadoOrden
    consultar_historial_vehiculo: uc.ConsultarHistorialVehiculo
    evaluar_operacion: uc.EvaluarOperacion


def crear_contenedor(settings: Settings | None = None, crear_esquema: bool = True) -> Contenedor:
    settings = settings or load_settings()
    engine = crear_engine(settings.database_url, settings.sql_echo)
    if crear_esquema:
        crear_tablas(engine)
    sf = crear_session_factory(engine)
    uow_factory: UnitOfWorkFactory = lambda: SqlUnitOfWork(sf)  # noqa: E731

    notificador = LogNotificador()
    bus = InProcessEventBus()
    bus.suscribir(OrdenEvent, AuditoriaEventosSql(sf))
    bus.suscribir(RetrasoPorRefaccion, NotificarRetrasoPorRefaccion(uow_factory, notificador))
    bus.suscribir(FechaModificada, NotificarCambioFechaEntrega(uow_factory, notificador))

    a = (uow_factory, bus)
    iva = Porcentaje.de(settings.tasa_iva)
    return Contenedor(
        settings, engine, uow_factory, bus, notificador,
        uc.RegistrarCliente(*a), uc.RegistrarVehiculo(*a), uc.RegistrarTecnico(*a), uc.RegistrarCuentaFlotilla(*a),
        uc.CambiarEstadoCliente(*a), uc.RegistrarItemCatalogo(*a), uc.ConsultarCatalogo(*a),
        uc.RegistrarIngresoVehiculo(*a), uc.RegistrarDiagnostico(*a), uc.GenerarCotizacion(*a, tasa_impuesto=iva),
        uc.ResponderCotizacion(*a), uc.AsignarTrabajos(*a), uc.ReportarRefaccionSinExistencia(*a),
        uc.ActualizarReposicion(*a), uc.RecibirRefaccion(*a), uc.RegistrarFallaAdicional(*a),
        uc.EnviarCotizacionComplementaria(*a, tasa_impuesto=iva), uc.ResponderAmpliacion(*a),
        uc.DefinirFechaEntrega(*a), uc.FinalizarTrabajo(*a), uc.AprobarRevisionCalidad(*a),
        uc.MarcarListaParaEntrega(*a), uc.RegistrarCobroYCerrar(*a), uc.CancelarOrden(*a),
        uc.ConsultarEstadoOrden(*a), uc.ConsultarHistorialVehiculo(*a), uc.EvaluarOperacion(*a))
