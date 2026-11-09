"""Modelos de persistencia (tablas). Separados de las entidades de dominio."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .tipos import UTCDateTime

ID = String(36)
DINERO = Numeric(14, 2)
PCT = Numeric(5, 2)
_CASCADE = dict(cascade="all, delete-orphan", lazy="selectin")


class CuentaFlotillaRecord(Base):
    __tablename__ = "cuentas_flotilla"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    autorizador_corporativo_id: Mapped[str] = mapped_column(ID, ForeignKey("clientes.id"))
    descuento: Mapped[Decimal] = mapped_column(PCT, default=0)
    prioridad: Mapped[int] = mapped_column(Integer, default=0)
    dias_credito: Mapped[int] = mapped_column(Integer, default=0)


class ClienteRecord(Base):
    __tablename__ = "clientes"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    es_preferente: Mapped[bool] = mapped_column(Boolean, default=False)
    cuenta_flotilla_id: Mapped[str | None] = mapped_column(ID, index=True)  # sin FK: evita ciclo con la cuenta


class VehiculoRecord(Base):
    __tablename__ = "vehiculos"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    placas: Mapped[str] = mapped_column(String(10), unique=True)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True)
    marca: Mapped[str] = mapped_column(String(80))
    modelo: Mapped[str] = mapped_column(String(80))
    kilometraje: Mapped[int] = mapped_column(Integer)
    cuenta_flotilla_id: Mapped[str | None] = mapped_column(ID, ForeignKey("cuentas_flotilla.id"))


class ItemCatalogoRecord(Base):
    __tablename__ = "catalogo"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    precio: Mapped[Decimal] = mapped_column(DINERO)
    capacidad: Mapped[int] = mapped_column(Integer)
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)


class TecnicoRecord(Base):
    __tablename__ = "tecnicos"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    especialidad: Mapped[str] = mapped_column(String(100))
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)


class OrdenServicioRecord(Base):
    __tablename__ = "ordenes_servicio"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ID, ForeignKey("clientes.id"), index=True)
    vehiculo_id: Mapped[str] = mapped_column(ID, ForeignKey("vehiculos.id"), index=True)
    autorizador_id: Mapped[str] = mapped_column(ID, ForeignKey("clientes.id"))
    estado: Mapped[str] = mapped_column(String(40), index=True)
    creada_en: Mapped[datetime] = mapped_column(UTCDateTime)
    # datos de recepción (RN-01)
    kilometraje: Mapped[int] = mapped_column(Integer)
    combustible: Mapped[str] = mapped_column(String(10))
    danos_visibles: Mapped[list] = mapped_column(JSON)
    motivo_ingreso: Mapped[str] = mapped_column(Text)
    # flotilla (RN-09)
    es_flotilla: Mapped[bool] = mapped_column(Boolean, default=False)
    promocion_activa: Mapped[bool] = mapped_column(Boolean, default=False)
    flotilla_descuento: Mapped[Decimal | None] = mapped_column(PCT)
    flotilla_prioridad: Mapped[int | None] = mapped_column(Integer)
    flotilla_dias_credito: Mapped[int | None] = mapped_column(Integer)
    # diagnóstico, fecha y cobro
    hallazgos: Mapped[list] = mapped_column(JSON)
    tecnico_diagnostico_id: Mapped[str | None] = mapped_column(ID)
    fecha_entrega: Mapped[datetime | None] = mapped_column(UTCDateTime)
    monto_cobrado: Mapped[Decimal | None] = mapped_column(DINERO)

    cotizaciones: Mapped[list["CotizacionRecord"]] = relationship(**_CASCADE)
    trabajos: Mapped[list["TrabajoRecord"]] = relationship(order_by="TrabajoRecord.posicion", **_CASCADE)
    solicitudes_refaccion: Mapped[list["SolicitudRefaccionRecord"]] = relationship(
        order_by="SolicitudRefaccionRecord.posicion", **_CASCADE)
    solicitudes_ampliacion: Mapped[list["SolicitudAmpliacionRecord"]] = relationship(
        order_by="SolicitudAmpliacionRecord.posicion", **_CASCADE)
    cambios_fecha: Mapped[list["CambioFechaRecord"]] = relationship(order_by="CambioFechaRecord.posicion", **_CASCADE)


class CotizacionRecord(Base):
    __tablename__ = "cotizaciones"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    orden_id: Mapped[str] = mapped_column(ID, ForeignKey("ordenes_servicio.id"), index=True)
    solicitud_ampliacion_id: Mapped[str | None] = mapped_column(ID, index=True)  # None = cotización inicial
    tipo: Mapped[str] = mapped_column(String(20))
    emitida_en: Mapped[datetime] = mapped_column(UTCDateTime)
    tasa_impuesto: Mapped[Decimal] = mapped_column(PCT)
    descuento: Mapped[Decimal] = mapped_column(PCT)
    respondida: Mapped[bool] = mapped_column(Boolean, default=False)
    conceptos: Mapped[list["ConceptoRecord"]] = relationship(order_by="ConceptoRecord.posicion", **_CASCADE)


class ConceptoRecord(Base):
    __tablename__ = "conceptos_cotizacion"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    cotizacion_id: Mapped[str] = mapped_column(ID, ForeignKey("cotizaciones.id"), index=True)
    posicion: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(Text)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    precio_unitario: Mapped[Decimal] = mapped_column(DINERO)
    estado: Mapped[str] = mapped_column(String(20))
    recurso_id: Mapped[str | None] = mapped_column(ID, index=True)   # recurso del catálogo (opcional)
    # evidencia de autorización (RN-11)
    ev_sello_tiempo: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ev_canal: Mapped[str | None] = mapped_column(String(10))
    ev_ip: Mapped[str | None] = mapped_column(String(45))
    ev_token: Mapped[str | None] = mapped_column(String(200))


class TrabajoRecord(Base):
    __tablename__ = "trabajos_reparacion"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    orden_id: Mapped[str] = mapped_column(ID, ForeignKey("ordenes_servicio.id"), index=True)
    posicion: Mapped[int] = mapped_column(Integer)
    concepto_id: Mapped[str] = mapped_column(ID)
    descripcion: Mapped[str] = mapped_column(Text)
    tecnico_id: Mapped[str] = mapped_column(ID, ForeignKey("tecnicos.id"))
    estado: Mapped[str] = mapped_column(String(40))


class SolicitudRefaccionRecord(Base):
    __tablename__ = "solicitudes_refaccion"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    orden_id: Mapped[str] = mapped_column(ID, ForeignKey("ordenes_servicio.id"), index=True)
    posicion: Mapped[int] = mapped_column(Integer)
    concepto_id: Mapped[str] = mapped_column(ID)
    descripcion: Mapped[str] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(UTCDateTime)
    reposicion_estimada: Mapped[datetime | None] = mapped_column(UTCDateTime)
    estado: Mapped[str] = mapped_column(String(20), index=True)


class SolicitudAmpliacionRecord(Base):
    __tablename__ = "solicitudes_ampliacion"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    orden_id: Mapped[str] = mapped_column(ID, ForeignKey("ordenes_servicio.id"), index=True)
    posicion: Mapped[int] = mapped_column(Integer)
    tecnico_id: Mapped[str] = mapped_column(ID, ForeignKey("tecnicos.id"))
    descripcion_falla: Mapped[str] = mapped_column(Text)
    detectada_en: Mapped[datetime] = mapped_column(UTCDateTime)
    estado: Mapped[str] = mapped_column(String(30))


class CambioFechaRecord(Base):
    """Historial de fechas estimadas (RN-06)."""

    __tablename__ = "cambios_fecha_entrega"
    orden_id: Mapped[str] = mapped_column(ID, ForeignKey("ordenes_servicio.id"), primary_key=True)
    posicion: Mapped[int] = mapped_column(Integer, primary_key=True)
    anterior: Mapped[datetime] = mapped_column(UTCDateTime)
    nueva: Mapped[datetime] = mapped_column(UTCDateTime)
    justificacion: Mapped[str] = mapped_column(Text)
    registrado_en: Mapped[datetime] = mapped_column(UTCDateTime)


class EventoDominioRecord(Base):
    """Bitácora de eventos de dominio (RNF-01: trazabilidad y auditoría)."""

    __tablename__ = "eventos_dominio"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(80), index=True)
    orden_id: Mapped[str | None] = mapped_column(ID, index=True)
    ocurrido_en: Mapped[datetime] = mapped_column(UTCDateTime)
    payload: Mapped[dict] = mapped_column(JSON)
