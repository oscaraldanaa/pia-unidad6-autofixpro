"""Constructores de objetos de dominio para las pruebas."""
from __future__ import annotations

from datetime import datetime, timezone

from src.domain.entities import (
    Cliente, ConceptoCotizacion, CondicionesFlotilla, CuentaFlotilla, OrdenServicio, Tecnico, TipoConcepto, Vehiculo,
)
from src.domain.value_objects import (
    CanalAutorizacion, ClienteId, ConceptoId, CuentaFlotillaId, DatosContacto, DatosRecepcion, Dinero,
    EvidenciaAutorizacion, Kilometraje, NivelCombustible, Placas, Porcentaje, TecnicoId, VehiculoId,
)

AHORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def cliente(nombre="Ana", activo=True, cuenta=None) -> Cliente:
    return Cliente(ClienteId.generar(), nombre, DatosContacto(telefono="8112345678", email="ana@mail.com"),
                   cuenta, activo)


def vehiculo(placas="ABC-123", cuenta=None) -> Vehiculo:
    return Vehiculo(VehiculoId.generar(), Placas(placas), "Nissan", "Versa", Kilometraje(50000),
                    cuenta_flotilla_id=cuenta)


def tecnico(disponible=True) -> Tecnico:
    return Tecnico(TecnicoId.generar(), "Luis", "Frenos", disponible)


def recepcion(km=50100) -> DatosRecepcion:
    return DatosRecepcion(Kilometraje(km), NivelCombustible.MEDIO, ("Rayón puerta",), "Ruido al frenar")


def evidencia(ip="187.1.2.3") -> EvidenciaAutorizacion:
    return EvidenciaAutorizacion(AHORA, CanalAutorizacion.WEB, ip=ip)


def mano_obra(precio="500") -> ConceptoCotizacion:
    return ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.MANO_DE_OBRA, "Cambio de balatas", Dinero.de(precio))


def refaccion(precio="800.50") -> ConceptoCotizacion:
    return ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.REFACCION, "Balatas", Dinero.de(precio))


def orden_recibida(**kw) -> OrdenServicio:
    return OrdenServicio.registrar_ingreso(cliente(), vehiculo(), recepcion(), ahora=AHORA, **kw)


class Escenario:
    """Orden con mano de obra + refacción; permite avanzar paso a paso."""

    def __init__(self) -> None:
        self.orden = orden_recibida()
        self.tec = TecnicoId.generar()
        self.mo, self.rf, self.extra = mano_obra(), refaccion(), refaccion("300")

    def diagnosticada(self):
        self.orden.registrar_diagnostico(self.tec, ["Balatas gastadas"]); return self.orden

    def cotizada(self):
        self.diagnosticada()
        self.orden.generar_cotizacion([self.mo, self.rf, self.extra], ahora=AHORA); return self.orden

    def autorizada(self):
        self.cotizada()
        self.orden.responder_cotizacion({self.mo.id: True, self.rf.id: True, self.extra.id: False}, evidencia())
        return self.orden

    def en_reparacion(self):
        self.autorizada(); self.orden.asignar_trabajos(self.tec); return self.orden

    def lista(self):
        self.en_reparacion()
        for t in self.orden.trabajos:
            self.orden.finalizar_trabajo(t.id); self.orden.aprobar_revision_calidad(t.id)
        self.orden.marcar_lista_para_entrega(); return self.orden


def cuenta_flotilla(autorizador: ClienteId, descuento="10") -> CuentaFlotilla:
    return CuentaFlotilla(CuentaFlotillaId.generar(), "Transportes SA", autorizador,
                          CondicionesFlotilla(Porcentaje.de(descuento), 1, 30))
