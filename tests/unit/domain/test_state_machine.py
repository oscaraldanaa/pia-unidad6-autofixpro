"""State Machine del ciclo de vida de la orden."""
import pytest

from src.domain.events import EstadoOrdenCambiado, OrdenCancelada
from src.domain.shared import ValorInvalido
from src.domain.state_machine import (
    ORDEN_STATE_MACHINE as SM, DisparadorOrden as D, StateMachine, Transicion, TransicionInvalida,
)
from src.domain.value_objects import EstadoOrden as S
from tests.builders import Escenario, orden_recibida


def test_camino_feliz_emite_un_evento_por_transicion():
    orden = Escenario().lista()
    orden.registrar_cobro_y_cerrar(orden.total_autorizado)
    cambios = [(e.anterior, e.nuevo) for e in orden.recolectar_eventos() if isinstance(e, EstadoOrdenCambiado)]
    assert [n for _, n in cambios] == ["Diagnosticado", "Cotizado", "Autorizado", "En reparación",
                                       "Listo para entrega", "Cerrado"]
    assert orden.estado is S.CERRADO


@pytest.mark.parametrize("accion", [
    lambda o, e: o.generar_cotizacion([e.mo]),                       # saltar diagnóstico
    lambda o, e: o.asignar_trabajos(e.tec),                          # sin autorización (RN-13)
    lambda o, e: o.marcar_lista_para_entrega(),
    lambda o, e: o.registrar_cobro_y_cerrar(None),
])
def test_transiciones_invalidas_desde_recibido(accion):
    esc = Escenario()
    with pytest.raises(Exception) as exc:
        accion(esc.orden, esc)
    assert type(exc.value).__name__ in ("TransicionInvalida", "ReglaDeNegocioViolada")
    assert esc.orden.estado is S.RECIBIDO                             # no hubo cambio parcial


def test_no_se_puede_diagnosticar_dos_veces():
    esc = Escenario(); esc.diagnosticada()
    with pytest.raises(TransicionInvalida) as e:
        esc.orden.registrar_diagnostico(esc.tec, ["otro"])
    assert e.value.estado is S.DIAGNOSTICADO and e.value.disparador is D.DIAGNOSTICAR


def test_rechazo_total_cancela_y_estado_final_no_admite_nada():
    esc = Escenario(); orden = esc.cotizada()
    orden.responder_cotizacion({esc.mo.id: False, esc.rf.id: False, esc.extra.id: False}, __import__("tests.builders", fromlist=["x"]).evidencia())
    assert orden.estado is S.CANCELADO
    with pytest.raises(TransicionInvalida):
        orden.registrar_diagnostico(esc.tec, ["x"])
    assert SM.disparadores_permitidos(S.CANCELADO) == []


def test_cancelar_solo_antes_de_reparar():
    o = orden_recibida(); o.cancelar("Cliente desistió")
    assert o.estado is S.CANCELADO
    assert any(isinstance(e, OrdenCancelada) for e in o.recolectar_eventos())
    with pytest.raises(ValorInvalido):
        orden_recibida().cancelar(" ")
    with pytest.raises(TransicionInvalida):
        Escenario().en_reparacion().cancelar("tarde")


def test_guardas_con_specification():
    esc = Escenario(); o = esc.en_reparacion()
    assert not SM.puede(S.EN_REPARACION, D.PREPARAR_ENTREGA, o)
    assert SM.puede(S.EN_REPARACION, D.ESPERAR_REFACCION, o)
    with pytest.raises(TransicionInvalida, match="revisados"):
        o.marcar_lista_para_entrega()
    s = o.reportar_refaccion_sin_existencia(esc.rf.id)
    assert not SM.puede(S.EN_ESPERA_REFACCION, D.REANUDAR_REPARACION, o)   # solicitud pendiente
    o.recibir_refaccion(s.id)
    assert o.estado is S.EN_REPARACION


def test_tabla_no_admite_duplicados_y_destino_directo():
    t = Transicion(S.RECIBIDO, D.DIAGNOSTICAR, S.DIAGNOSTICADO)
    with pytest.raises(ValueError):
        StateMachine([t, t])
    assert SM.destino(S.RECIBIDO, D.DIAGNOSTICAR) is S.DIAGNOSTICADO
