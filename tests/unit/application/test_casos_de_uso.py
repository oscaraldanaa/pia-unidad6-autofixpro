"""Casos de uso con repositorios en memoria (Dependency Inversion)."""
from datetime import timedelta
from decimal import Decimal

import pytest

from src.application import use_cases as uc
from src.application.dto import *
from src.application.handlers import NotificarCambioFechaEntrega, NotificarRetrasoPorRefaccion
from src.domain.events import FechaModificada, RetrasoPorRefaccion
from src.domain.shared import EntidadNoEncontrada, ReglaDeNegocioViolada
from src.domain.state_machine import TransicionInvalida
from src.domain.value_objects import ClienteId, OrdenServicioId
from tests.builders import AHORA
from tests.fakes import BusEspia, MemUoW, NotificadorEspia


@pytest.fixture
def mundo():
    uow, bus = MemUoW(), BusEspia()
    f = lambda: uow  # noqa: E731
    reloj = lambda: AHORA  # noqa: E731
    k = dict(reloj=reloj)
    casos = dict(
        cliente=uc.RegistrarCliente(f, bus, **k), vehiculo=uc.RegistrarVehiculo(f, bus, **k),
        tecnico=uc.RegistrarTecnico(f, bus, **k), flotilla=uc.RegistrarCuentaFlotilla(f, bus, **k),
        ingreso=uc.RegistrarIngresoVehiculo(f, bus, **k), diag=uc.RegistrarDiagnostico(f, bus, **k),
        cotizar=uc.GenerarCotizacion(f, bus, **k), responder=uc.ResponderCotizacion(f, bus, **k),
        asignar=uc.AsignarTrabajos(f, bus, **k), estado=uc.ConsultarEstadoOrden(f, bus, **k),
        historial=uc.ConsultarHistorialVehiculo(f, bus, **k), cancelar=uc.CancelarOrden(f, bus, **k),
        fecha=uc.DefinirFechaEntrega(f, bus, **k), cobro=uc.RegistrarCobroYCerrar(f, bus, **k))
    return uow, bus, casos


def _base(c):
    cli = c["cliente"].ejecutar(RegistrarClienteCmd("Ana", telefono="8112345678"))
    veh = c["vehiculo"].ejecutar(RegistrarVehiculoCmd("ABC-123", "Nissan", "Versa", 1000))
    tec = c["tecnico"].ejecutar(RegistrarTecnicoCmd("Luis", "Frenos"))
    return cli, veh, tec


def test_ingreso_publica_eventos_tras_commit_y_actualiza_km(mundo):
    uow, bus, c = mundo
    cli, veh, _ = _base(c)
    commits = uow.commits
    o = c["ingreso"].ejecutar(RegistrarIngresoCmd(cli, veh, 1500, "1/2", "Ruido", ("rayón",)))
    assert o.estado == "Recibido" and uow.commits == commits + 1
    assert {type(e).__name__ for e in bus.publicados} == {"OrdenRecibida"}
    assert uow.vehiculos.obtener(uow.vehiculos.datos and next(iter(uow.vehiculos.datos))).kilometraje.km == 1500


def test_cliente_inactivo_no_puede_abrir_orden(mundo):
    uow, _, c = mundo
    cli, veh, _ = _base(c)
    uow.clientes.obtener(ClienteId.desde_str(cli)).desactivar()
    with pytest.raises(ReglaDeNegocioViolada, match="inactivo"):
        c["ingreso"].ejecutar(RegistrarIngresoCmd(cli, veh, 1500, "1/2", "x"))


def test_placas_duplicadas_y_entidades_inexistentes(mundo):
    _, _, c = mundo
    _base(c)
    with pytest.raises(ReglaDeNegocioViolada, match="placas"):
        c["vehiculo"].ejecutar(RegistrarVehiculoCmd("abc-123", "X", "Y", 1))
    with pytest.raises(EntidadNoEncontrada):
        c["estado"].ejecutar(str(OrdenServicioId.generar()))
    with pytest.raises(EntidadNoEncontrada):
        c["ingreso"].ejecutar(RegistrarIngresoCmd(str(ClienteId.generar()), str(ClienteId.generar()), 1, "lleno", "x"))


def test_tecnico_no_disponible_no_recibe_trabajos(mundo):
    uow, _, c = mundo
    cli, veh, tec = _base(c)
    o = c["ingreso"].ejecutar(RegistrarIngresoCmd(cli, veh, 1500, "1/2", "Ruido"))
    c["diag"].ejecutar(RegistrarDiagnosticoCmd(o.id, tec, ("x",)))
    o = c["cotizar"].ejecutar(GenerarCotizacionCmd(o.id, (ConceptoNuevoDTO("mano_de_obra", "Balatas", Decimal("500")),)))
    cid = o.cotizacion.conceptos[0].id
    c["responder"].ejecutar(ResponderCotizacionCmd(o.id, {cid: True}, EvidenciaDTO("web", ip="1.2.3.4")))
    next(iter(uow.tecnicos.datos.values()))._disponible = False
    with pytest.raises(ReglaDeNegocioViolada, match="disponible"):
        c["asignar"].ejecutar(AsignarTrabajosCmd(o.id, tec))
    assert uow.rollbacks >= 1


def test_transicion_invalida_no_publica_eventos_ni_guarda(mundo):
    uow, bus, c = mundo
    cli, veh, tec = _base(c)
    o = c["ingreso"].ejecutar(RegistrarIngresoCmd(cli, veh, 1500, "1/2", "Ruido"))
    publicados = len(bus.publicados)
    with pytest.raises(TransicionInvalida):
        c["cotizar"].ejecutar(GenerarCotizacionCmd(o.id, (ConceptoNuevoDTO("mano_de_obra", "x", Decimal("1")),)))
    assert len(bus.publicados) == publicados
    assert c["estado"].ejecutar(o.id).estado == "Recibido"


def test_flotilla_cancelacion_historial_y_cobro_minimo(mundo):
    uow, _, c = mundo
    gerente = c["cliente"].ejecutar(RegistrarClienteCmd("Gerente", email="g@f.mx"))
    cuenta = c["flotilla"].ejecutar(RegistrarCuentaFlotillaCmd("Flota SA", gerente, Decimal("5"), 1, 30))
    veh = c["vehiculo"].ejecutar(RegistrarVehiculoCmd("FLT-001", "Ford", "Ranger", 10, cuenta_flotilla_id=cuenta))
    chofer = c["cliente"].ejecutar(RegistrarClienteCmd("Chofer", telefono="8111111111", cuenta_flotilla_id=cuenta))
    o = c["ingreso"].ejecutar(RegistrarIngresoCmd(chofer, veh, 20, "lleno", "Revisión"))
    assert o.es_flotilla and o.autorizador_id == gerente
    o = c["cancelar"].ejecutar(CancelarOrdenCmd(o.id, "Desistió"))
    assert o.estado == "Cancelado"
    assert [h.estado for h in c["historial"].ejecutar(veh)] == ["Cancelado"]
    with pytest.raises(ReglaDeNegocioViolada, match="mayor a cero"):
        c["cobro"].ejecutar(RegistrarCobroCmd(o.id, Decimal("0")))


def test_manejadores_notifican_al_autorizador(mundo):
    uow, _, c = mundo
    cli, veh, _ = _base(c)
    o = c["ingreso"].ejecutar(RegistrarIngresoCmd(cli, veh, 1500, "1/2", "x"))
    notif = NotificadorEspia()
    oid = OrdenServicioId.desde_str(o.id)
    NotificarRetrasoPorRefaccion(lambda: uow, notif)(
        RetrasoPorRefaccion(orden_id=oid, solicitud_id=None, motivo="Proveedor", nueva_fecha_reposicion=AHORA))
    NotificarCambioFechaEntrega(lambda: uow, notif)(
        FechaModificada(orden_id=oid, anterior=AHORA, nueva=AHORA + timedelta(days=1), justificacion="Retraso"))
    asuntos = [a for _, a, _ in notif.enviados]
    assert asuntos == ["Retraso en su reparación", "Cambio en la fecha estimada de entrega"]
    assert notif.enviados[0][0].telefono == "8112345678"
