"""DTOs de entrada (comandos) y salida. Solo tipos primitivos/Decimal/datetime."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..domain.entities import ConceptoCotizacion, Cotizacion, OrdenServicio


# ----------------------------------------------------------------- entrada
@dataclass(frozen=True)
class EvidenciaDTO:
    canal: str                      # sms | email | web
    ip: str | None = None
    token_verificacion: str | None = None


@dataclass(frozen=True)
class ConceptoNuevoDTO:
    """Concepto libre (descripcion + precio) o de catálogo (recurso_id: toma precio oficial y valida capacidad)."""

    tipo: str = "mano_de_obra"      # mano_de_obra | refaccion
    descripcion: str | None = None
    precio_unitario: Decimal | None = None
    cantidad: Decimal = Decimal(1)
    recurso_id: str | None = None


@dataclass(frozen=True)
class RegistrarClienteCmd:
    nombre: str
    telefono: str | None = None
    email: str | None = None
    cuenta_flotilla_id: str | None = None
    activo: bool = True
    es_preferente: bool = False


@dataclass(frozen=True)
class CambiarEstadoClienteCmd:
    cliente_id: str
    activo: bool


@dataclass(frozen=True)
class RegistrarItemCatalogoCmd:
    descripcion: str
    precio_mxn: Decimal
    capacidad: int
    habilitado: bool = True


@dataclass(frozen=True)
class RegistrarVehiculoCmd:
    placas: str
    marca: str
    modelo: str
    kilometraje: int
    vin: str | None = None
    cuenta_flotilla_id: str | None = None


@dataclass(frozen=True)
class RegistrarTecnicoCmd:
    nombre: str
    especialidad: str


@dataclass(frozen=True)
class RegistrarCuentaFlotillaCmd:
    razon_social: str
    autorizador_corporativo_id: str
    descuento_pct: Decimal = Decimal(0)
    prioridad: int = 0
    dias_credito: int = 0


@dataclass(frozen=True)
class RegistrarIngresoCmd:
    cliente_id: str
    vehiculo_id: str
    kilometraje: int
    combustible: str                # vacio | 1/4 | 1/2 | 3/4 | lleno
    motivo_ingreso: str
    danos_visibles: tuple[str, ...] = ()
    promocion_activa: bool = False


@dataclass(frozen=True)
class RegistrarDiagnosticoCmd:
    orden_id: str
    tecnico_id: str
    hallazgos: tuple[str, ...]


@dataclass(frozen=True)
class GenerarCotizacionCmd:
    orden_id: str
    conceptos: tuple[ConceptoNuevoDTO, ...]


@dataclass(frozen=True)
class ResponderCotizacionCmd:
    orden_id: str
    decisiones: dict[str, bool]     # concepto_id -> autorizado?
    evidencia: EvidenciaDTO


@dataclass(frozen=True)
class AsignarTrabajosCmd:
    orden_id: str
    tecnico_id: str


@dataclass(frozen=True)
class ReportarRefaccionSinExistenciaCmd:
    orden_id: str
    concepto_id: str
    reposicion_estimada: datetime | None = None


@dataclass(frozen=True)
class ActualizarReposicionCmd:
    orden_id: str
    solicitud_id: str
    nueva_fecha: datetime
    motivo: str


@dataclass(frozen=True)
class SolicitudRefaccionCmd:
    orden_id: str
    solicitud_id: str


@dataclass(frozen=True)
class RegistrarFallaAdicionalCmd:
    orden_id: str
    tecnico_id: str
    descripcion: str


@dataclass(frozen=True)
class EnviarCotizacionComplementariaCmd:
    orden_id: str
    solicitud_id: str
    conceptos: tuple[ConceptoNuevoDTO, ...]


@dataclass(frozen=True)
class ResponderAmpliacionCmd:
    orden_id: str
    solicitud_id: str
    decisiones: dict[str, bool]
    evidencia: EvidenciaDTO


@dataclass(frozen=True)
class DefinirFechaEntregaCmd:
    orden_id: str
    fecha_estimada: datetime
    justificacion: str | None = None   # obligatoria si ya existía una fecha (RN-06)


@dataclass(frozen=True)
class TrabajoCmd:
    orden_id: str
    trabajo_id: str


@dataclass(frozen=True)
class OrdenCmd:
    orden_id: str


@dataclass(frozen=True)
class RegistrarCobroCmd:
    orden_id: str
    monto: Decimal


@dataclass(frozen=True)
class CancelarOrdenCmd:
    orden_id: str
    motivo: str


# ----------------------------------------------------------------- salida
@dataclass(frozen=True)
class ConceptoDTO:
    id: str
    tipo: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    importe: Decimal
    estado: str


@dataclass(frozen=True)
class CotizacionDTO:
    id: str
    tipo: str
    resultado: str
    subtotal: Decimal
    descuento: Decimal
    impuestos: Decimal
    total: Decimal
    total_autorizado: Decimal
    conceptos: tuple[ConceptoDTO, ...]


@dataclass(frozen=True)
class TrabajoDTO:
    id: str
    concepto_id: str
    descripcion: str
    tecnico_id: str
    estado: str


@dataclass(frozen=True)
class SolicitudRefaccionDTO:
    id: str
    concepto_id: str
    descripcion: str
    estado: str
    reposicion_estimada: datetime | None


@dataclass(frozen=True)
class SolicitudAmpliacionDTO:
    id: str
    tecnico_id: str
    descripcion_falla: str
    estado: str
    cotizacion: CotizacionDTO | None


@dataclass(frozen=True)
class CambioFechaDTO:
    anterior: datetime
    nueva: datetime
    justificacion: str
    registrado_en: datetime


@dataclass(frozen=True)
class OrdenDetalleDTO:
    id: str
    estado: str
    cliente_id: str
    vehiculo_id: str
    autorizador_id: str
    es_flotilla: bool
    promocion_activa: bool
    creada_en: datetime
    kilometraje: int
    combustible: str
    danos_visibles: tuple[str, ...]
    motivo_ingreso: str
    hallazgos: tuple[str, ...]
    fecha_entrega: datetime | None
    cotizacion: CotizacionDTO | None
    trabajos: tuple[TrabajoDTO, ...]
    solicitudes_refaccion: tuple[SolicitudRefaccionDTO, ...]
    solicitudes_ampliacion: tuple[SolicitudAmpliacionDTO, ...]
    historial_fechas: tuple[CambioFechaDTO, ...]
    total_autorizado: Decimal
    monto_cobrado: Decimal | None


@dataclass(frozen=True)
class ItemCatalogoDTO:
    id: str
    descripcion: str
    precio_mxn: Decimal
    capacidad: int
    habilitado: bool


@dataclass(frozen=True)
class EvaluacionOperacionDTO:
    orden_id: str
    cliente_id: str
    total_referencia: Decimal
    puede_procesarse: bool
    beneficio_referencia: bool
    criterios: dict[str, bool]


@dataclass(frozen=True)
class OrdenResumenDTO:
    id: str
    estado: str
    creada_en: datetime
    motivo_ingreso: str


def _concepto(c: ConceptoCotizacion) -> ConceptoDTO:
    return ConceptoDTO(str(c.id), c.tipo.value, c.descripcion, c.cantidad, c.precio_unitario.monto,
                       c.importe.monto, c.estado.value)


def _cotizacion(c: Cotizacion) -> CotizacionDTO:
    d, a = c.desglose, c.desglose_autorizado
    return CotizacionDTO(str(c.id), c.tipo.value, c.resultado.value, d.subtotal.monto, d.descuento.monto,
                         d.impuestos.monto, d.total.monto, a.total.monto,
                         tuple(_concepto(x) for x in c.conceptos))


def a_orden_dto(o: OrdenServicio) -> OrdenDetalleDTO:
    r = o.datos_recepcion
    return OrdenDetalleDTO(
        id=str(o.id), estado=o.estado.value, cliente_id=str(o.cliente_id), vehiculo_id=str(o.vehiculo_id),
        autorizador_id=str(o.autorizador_id), es_flotilla=o.es_flotilla, promocion_activa=o.promocion_activa, creada_en=o.creada_en,
        kilometraje=r.kilometraje.km, combustible=r.combustible.value, danos_visibles=r.danos_visibles,
        motivo_ingreso=r.motivo_ingreso, hallazgos=o.hallazgos,
        fecha_entrega=o.fecha_entrega.fecha_estimada if o.fecha_entrega else None,
        cotizacion=_cotizacion(o.cotizacion_inicial) if o.cotizacion_inicial else None,
        trabajos=tuple(TrabajoDTO(str(t.id), str(t.concepto_id), t.descripcion, str(t.tecnico_id), t.estado.value)
                       for t in o.trabajos),
        solicitudes_refaccion=tuple(
            SolicitudRefaccionDTO(str(s.id), str(s.concepto_id), s.descripcion, s.estado.value,
                                  s.reposicion_estimada) for s in o.solicitudes_refaccion),
        solicitudes_ampliacion=tuple(
            SolicitudAmpliacionDTO(str(s.id), str(s.tecnico_id), s.descripcion_falla, s.estado.value,
                                   _cotizacion(s.cotizacion) if s.cotizacion else None)
            for s in o.solicitudes_ampliacion),
        historial_fechas=tuple(CambioFechaDTO(c.anterior.fecha_estimada, c.nueva.fecha_estimada,
                                              c.justificacion, c.registrado_en) for c in o.historial_fechas),
        total_autorizado=o.total_autorizado.monto,
        monto_cobrado=o.monto_cobrado.monto if o.monto_cobrado else None,
    )
