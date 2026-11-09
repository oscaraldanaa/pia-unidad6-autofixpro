"""Traducción dominio <-> registros SQLAlchemy.

El dominio no conoce SQLAlchemy. Para reconstituir entidades desde la BD se
crea la instancia sin ejecutar ``__init__`` (los datos ya fueron validados al
guardarse) y se restauran sus atributos privados.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...domain.entities import (
    Cliente, ConceptoCotizacion, CondicionesFlotilla, Cotizacion, CuentaFlotilla, EstadoAmpliacion, ItemCatalogo,
    EstadoConcepto, EstadoSolicitudRefaccion, EstadoTrabajo, OrdenServicio, SolicitudAmpliacion,
    SolicitudRefaccion, Tecnico, TipoConcepto, TipoCotizacion, TrabajoReparacion, Vehiculo,
)
from ...domain.shared import AggregateRoot
from ...domain.value_objects import (
    CambioFechaEntrega, CanalAutorizacion, ClienteId, ConceptoId, CotizacionId, CuentaFlotillaId,
    DatosContacto, DatosRecepcion, Dinero, EstadoOrden, EvidenciaAutorizacion, FechaEntrega, Kilometraje,
    NivelCombustible, OrdenServicioId, Placas, Porcentaje, RecursoId, SolicitudAmpliacionId, SolicitudRefaccionId,
    TecnicoId, TrabajoId, VehiculoId, Vin,
)
from . import modelos as m


def _rehidratar(cls: type, id: Any, **attrs: Any):
    obj = cls.__new__(cls)
    obj._id = id
    if isinstance(obj, AggregateRoot):
        obj._eventos = []
    for k, v in attrs.items():
        setattr(obj, f"_{k}", v)
    return obj


def _id_opt(cls, valor: str | None):
    return cls.desde_str(valor) if valor else None


# ------------------------------------------------------------------ catálogos
def cliente_a_record(c: Cliente) -> m.ClienteRecord:
    return m.ClienteRecord(id=str(c.id), nombre=c.nombre, telefono=c.contacto.telefono, email=c.contacto.email,
                           activo=c.activo, es_preferente=c.es_preferente,
                           cuenta_flotilla_id=str(c.cuenta_flotilla_id) if c.cuenta_flotilla_id else None)


def record_a_cliente(r: m.ClienteRecord) -> Cliente:
    return _rehidratar(Cliente, ClienteId.desde_str(r.id), nombre=r.nombre,
                       contacto=DatosContacto(r.telefono, r.email),
                       cuenta_flotilla_id=_id_opt(CuentaFlotillaId, r.cuenta_flotilla_id), activo=r.activo,
                       es_preferente=r.es_preferente)


def vehiculo_a_record(v: Vehiculo) -> m.VehiculoRecord:
    return m.VehiculoRecord(id=str(v.id), placas=v.placas.valor, vin=v.vin.valor if v.vin else None, marca=v.marca,
                            modelo=v.modelo, kilometraje=v.kilometraje.km,
                            cuenta_flotilla_id=str(v.cuenta_flotilla_id) if v.cuenta_flotilla_id else None)


def record_a_vehiculo(r: m.VehiculoRecord) -> Vehiculo:
    return _rehidratar(Vehiculo, VehiculoId.desde_str(r.id), placas=Placas(r.placas), marca=r.marca, modelo=r.modelo,
                       kilometraje=Kilometraje(r.kilometraje), vin=Vin(r.vin) if r.vin else None,
                       cuenta_flotilla_id=_id_opt(CuentaFlotillaId, r.cuenta_flotilla_id))


def item_a_record(i: ItemCatalogo) -> m.ItemCatalogoRecord:
    return m.ItemCatalogoRecord(id=str(i.id), descripcion=i.descripcion, precio=i.precio.monto,
                                capacidad=i.capacidad, habilitado=i.habilitado)


def record_a_item(r: m.ItemCatalogoRecord) -> ItemCatalogo:
    return _rehidratar(ItemCatalogo, RecursoId.desde_str(r.id), descripcion=r.descripcion,
                       precio=Dinero(Decimal(r.precio)), capacidad=r.capacidad, habilitado=r.habilitado)


def tecnico_a_record(t: Tecnico) -> m.TecnicoRecord:
    return m.TecnicoRecord(id=str(t.id), nombre=t.nombre, especialidad=t.especialidad, disponible=t.disponible)


def record_a_tecnico(r: m.TecnicoRecord) -> Tecnico:
    return _rehidratar(Tecnico, TecnicoId.desde_str(r.id), nombre=r.nombre, especialidad=r.especialidad,
                       disponible=r.disponible)


def cuenta_a_record(c: CuentaFlotilla) -> m.CuentaFlotillaRecord:
    cond = c.condiciones
    return m.CuentaFlotillaRecord(id=str(c.id), razon_social=c.razon_social,
                                  autorizador_corporativo_id=str(c.autorizador_corporativo_id),
                                  descuento=cond.descuento.valor, prioridad=cond.prioridad, dias_credito=cond.dias_credito)


def record_a_cuenta(r: m.CuentaFlotillaRecord) -> CuentaFlotilla:
    return _rehidratar(CuentaFlotilla, CuentaFlotillaId.desde_str(r.id), razon_social=r.razon_social,
                       autorizador_corporativo_id=ClienteId.desde_str(r.autorizador_corporativo_id),
                       condiciones=CondicionesFlotilla(Porcentaje(Decimal(r.descuento)), r.prioridad, r.dias_credito))


# ------------------------------------------------------------------ cotizaciones
def _cotizacion_a_record(c: Cotizacion, orden_id: str, solicitud_id: str | None) -> m.CotizacionRecord:
    conceptos = []
    for i, k in enumerate(c.conceptos):
        ev = k.evidencia
        conceptos.append(m.ConceptoRecord(
            id=str(k.id), posicion=i, tipo=k.tipo.value, descripcion=k.descripcion, cantidad=k.cantidad,
            precio_unitario=k.precio_unitario.monto, estado=k.estado.value,
            recurso_id=str(k.recurso_id) if k.recurso_id else None,
            ev_sello_tiempo=ev.sello_tiempo if ev else None, ev_canal=ev.canal.value if ev else None,
            ev_ip=ev.ip if ev else None, ev_token=ev.token_verificacion if ev else None))
    return m.CotizacionRecord(id=str(c.id), orden_id=orden_id, solicitud_ampliacion_id=solicitud_id, tipo=c.tipo.value,
                              emitida_en=c.emitida_en, tasa_impuesto=c.tasa_impuesto.valor,
                              descuento=c.descuento.valor, respondida=c.respondida, conceptos=conceptos)


def _record_a_cotizacion(r: m.CotizacionRecord) -> Cotizacion:
    conceptos = []
    for k in r.conceptos:
        ev = (EvidenciaAutorizacion(k.ev_sello_tiempo, CanalAutorizacion(k.ev_canal), k.ev_ip, k.ev_token)
              if k.ev_sello_tiempo else None)
        conceptos.append(_rehidratar(
            ConceptoCotizacion, ConceptoId.desde_str(k.id), tipo=TipoConcepto(k.tipo), descripcion=k.descripcion,
            precio_unitario=Dinero(Decimal(k.precio_unitario)), cantidad=Decimal(k.cantidad).normalize(),
            estado=EstadoConcepto(k.estado), evidencia=ev,
            recurso_id=_id_opt(RecursoId, k.recurso_id)))
    return _rehidratar(Cotizacion, CotizacionId.desde_str(r.id), tipo=TipoCotizacion(r.tipo), conceptos=conceptos,
                       emitida_en=r.emitida_en, tasa_impuesto=Porcentaje(Decimal(r.tasa_impuesto)),
                       descuento=Porcentaje(Decimal(r.descuento)), respondida=r.respondida)


# ------------------------------------------------------------------ orden de servicio
def orden_a_record(o: OrdenServicio) -> m.OrdenServicioRecord:
    oid = str(o.id)
    rec, cond = o.datos_recepcion, o.condiciones_flotilla
    cotizaciones = []
    if o.cotizacion_inicial:
        cotizaciones.append(_cotizacion_a_record(o.cotizacion_inicial, oid, None))
    for s in o.solicitudes_ampliacion:
        if s.cotizacion:
            cotizaciones.append(_cotizacion_a_record(s.cotizacion, oid, str(s.id)))
    return m.OrdenServicioRecord(
        id=oid, cliente_id=str(o.cliente_id), vehiculo_id=str(o.vehiculo_id), autorizador_id=str(o.autorizador_id),
        estado=o.estado.value, creada_en=o.creada_en, kilometraje=rec.kilometraje.km, combustible=rec.combustible.value,
        danos_visibles=list(rec.danos_visibles), motivo_ingreso=rec.motivo_ingreso, es_flotilla=cond is not None, promocion_activa=o.promocion_activa,
        flotilla_descuento=cond.descuento.valor if cond else None, flotilla_prioridad=cond.prioridad if cond else None,
        flotilla_dias_credito=cond.dias_credito if cond else None, hallazgos=list(o.hallazgos),
        tecnico_diagnostico_id=str(o.tecnico_diagnostico_id) if o.tecnico_diagnostico_id else None,
        fecha_entrega=o.fecha_entrega.fecha_estimada if o.fecha_entrega else None,
        monto_cobrado=o.monto_cobrado.monto if o.monto_cobrado else None,
        cotizaciones=cotizaciones,
        trabajos=[m.TrabajoRecord(id=str(t.id), posicion=i, concepto_id=str(t.concepto_id), descripcion=t.descripcion,
                                  tecnico_id=str(t.tecnico_id), estado=t.estado.value)
                  for i, t in enumerate(o.trabajos)],
        solicitudes_refaccion=[m.SolicitudRefaccionRecord(
            id=str(s.id), posicion=i, concepto_id=str(s.concepto_id), descripcion=s.descripcion, creada_en=s.creada_en,
            reposicion_estimada=s.reposicion_estimada, estado=s.estado.value)
            for i, s in enumerate(o.solicitudes_refaccion)],
        solicitudes_ampliacion=[m.SolicitudAmpliacionRecord(
            id=str(s.id), posicion=i, tecnico_id=str(s.tecnico_id), descripcion_falla=s.descripcion_falla,
            detectada_en=s.detectada_en, estado=s.estado.value) for i, s in enumerate(o.solicitudes_ampliacion)],
        cambios_fecha=[m.CambioFechaRecord(orden_id=oid, posicion=i, anterior=c.anterior.fecha_estimada,
                                           nueva=c.nueva.fecha_estimada, justificacion=c.justificacion,
                                           registrado_en=c.registrado_en)
                       for i, c in enumerate(o.historial_fechas)])


def record_a_orden(r: m.OrdenServicioRecord) -> OrdenServicio:
    cot_por_solicitud = {c.solicitud_ampliacion_id: _record_a_cotizacion(c) for c in r.cotizaciones}
    ampliaciones = []
    for s in r.solicitudes_ampliacion:
        sol = _rehidratar(SolicitudAmpliacion, SolicitudAmpliacionId.desde_str(s.id),
                          tecnico_id=TecnicoId.desde_str(s.tecnico_id), descripcion_falla=s.descripcion_falla,
                          detectada_en=s.detectada_en, estado=EstadoAmpliacion(s.estado),
                          cotizacion=cot_por_solicitud.get(s.id))
        ampliaciones.append(sol)
    condiciones = (CondicionesFlotilla(Porcentaje(Decimal(r.flotilla_descuento)), r.flotilla_prioridad,
                                       r.flotilla_dias_credito) if r.es_flotilla else None)
    return _rehidratar(
        OrdenServicio, OrdenServicioId.desde_str(r.id),
        cliente_id=ClienteId.desde_str(r.cliente_id), vehiculo_id=VehiculoId.desde_str(r.vehiculo_id),
        autorizador_id=ClienteId.desde_str(r.autorizador_id),
        datos_recepcion=DatosRecepcion(Kilometraje(r.kilometraje), NivelCombustible(r.combustible),
                                       tuple(r.danos_visibles), r.motivo_ingreso),
        creada_en=r.creada_en, condiciones_flotilla=condiciones, promocion_activa=r.promocion_activa,
        estado=EstadoOrden(r.estado),
        hallazgos=tuple(r.hallazgos), tecnico_diagnostico=_id_opt(TecnicoId, r.tecnico_diagnostico_id),
        cotizacion_inicial=cot_por_solicitud.get(None), solicitudes_ampliacion=ampliaciones,
        solicitudes_refaccion=[_rehidratar(
            SolicitudRefaccion, SolicitudRefaccionId.desde_str(s.id), concepto_id=ConceptoId.desde_str(s.concepto_id),
            descripcion=s.descripcion, creada_en=s.creada_en, reposicion_estimada=s.reposicion_estimada,
            estado=EstadoSolicitudRefaccion(s.estado)) for s in r.solicitudes_refaccion],
        trabajos=[_rehidratar(
            TrabajoReparacion, TrabajoId.desde_str(t.id), concepto_id=ConceptoId.desde_str(t.concepto_id),
            descripcion=t.descripcion, tecnico_id=TecnicoId.desde_str(t.tecnico_id), estado=EstadoTrabajo(t.estado))
            for t in r.trabajos],
        fecha_entrega=FechaEntrega(r.fecha_entrega) if r.fecha_entrega else None,
        historial_fechas=[CambioFechaEntrega(FechaEntrega(c.anterior), FechaEntrega(c.nueva), c.justificacion,
                                             c.registrado_en) for c in r.cambios_fecha],
        monto_cobrado=Dinero(Decimal(r.monto_cobrado)) if r.monto_cobrado is not None else None)
