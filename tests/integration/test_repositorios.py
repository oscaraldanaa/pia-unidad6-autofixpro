"""Repositorios SQLAlchemy: persistencia y reconstitución fiel del agregado."""
from datetime import timedelta

import pytest
from sqlalchemy import text

from src.domain.entities import ConceptoCotizacion, OrdenServicio, TipoConcepto
from src.domain.shared import EntidadNoEncontrada
from src.domain.value_objects import (
    ConceptoId, Dinero, FechaEntrega, OrdenServicioId, Placas, TecnicoId, VehiculoId,
)
from tests.builders import AHORA, Escenario, cliente, cuenta_flotilla, evidencia, recepcion, tecnico, vehiculo


def _guardar_base(uow, esc: Escenario):
    c, v = cliente(), vehiculo()
    t = tecnico()
    uow.clientes.guardar(c); uow.vehiculos.guardar(v); uow.tecnicos.guardar(t)
    esc.orden = OrdenServicio.registrar_ingreso(c, v, recepcion(), ahora=AHORA)
    esc.tec = t.id
    return c, v, t


def test_roundtrip_completo_del_agregado(contenedor):
    esc = Escenario()
    with contenedor.uow_factory() as uow:
        _guardar_base(uow, esc)
        o = esc.autorizada()
        o.asignar_trabajos(esc.tec)
        s = o.reportar_refaccion_sin_existencia(esc.rf.id, AHORA + timedelta(days=2), AHORA)
        o.actualizar_reposicion(s.id, AHORA + timedelta(days=3), "Retraso proveedor")
        o.recibir_refaccion(s.id)
        o.programar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=4)), AHORA)
        o.modificar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=6)), "Espera", AHORA)
        a = o.registrar_falla_adicional(esc.tec, "Líquido", AHORA)
        extra = ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.MANO_DE_OBRA, "Cambio líquido", Dinero.de(200))
        o.enviar_cotizacion_complementaria(a.id, [extra], ahora=AHORA)
        o.responder_ampliacion(a.id, {extra.id: True}, evidencia())
        uow.ordenes.guardar(o); uow.commit()
        original = o

    with contenedor.uow_factory() as uow:
        r = uow.ordenes.obtener(original.id)
    assert r.estado == original.estado and r.total_autorizado == original.total_autorizado
    assert [(c.estado, c.evidencia) for c in r.cotizacion_inicial.conceptos] == \
           [(c.estado, c.evidencia) for c in original.cotizacion_inicial.conceptos]
    assert [t.estado for t in r.trabajos] == [t.estado for t in original.trabajos] and len(r.trabajos) == 2
    assert r.fecha_entrega == original.fecha_entrega and len(r.historial_fechas) == 1
    assert r.solicitudes_ampliacion[0].cotizacion.resultado == original.solicitudes_ampliacion[0].cotizacion.resultado
    assert r.solicitudes_refaccion[0].reposicion_estimada == AHORA + timedelta(days=3)
    assert r.datos_recepcion == original.datos_recepcion and r.hallazgos == original.hallazgos


def test_la_orden_reconstituida_sigue_aplicando_reglas(contenedor):
    esc = Escenario()
    with contenedor.uow_factory() as uow:
        _guardar_base(uow, esc); o = esc.en_reparacion(); uow.ordenes.guardar(o); uow.commit()
    with contenedor.uow_factory() as uow:
        r = uow.ordenes.obtener(o.id)
        t = r.trabajos[0]
        r.finalizar_trabajo(t.id); r.aprobar_revision_calidad(t.id); r.marcar_lista_para_entrega()
        r.registrar_cobro_y_cerrar(r.total_autorizado)
        uow.ordenes.guardar(r); uow.commit()
    with contenedor.uow_factory() as uow:
        assert uow.ordenes.obtener(o.id).monto_cobrado == r.total_autorizado


def test_actualizar_orden_no_duplica_hijos_ni_historial(contenedor):
    esc = Escenario()
    with contenedor.uow_factory() as uow:
        _guardar_base(uow, esc); o = esc.en_reparacion()
        o.programar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=4)), AHORA)
        o.modificar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=5)), "a", AHORA)
        for _ in range(3):
            uow.ordenes.guardar(o)
        uow.commit()
    with contenedor.engine.connect() as cn:
        assert cn.execute(text("select count(*) from cambios_fecha_entrega")).scalar() == 1
        assert cn.execute(text("select count(*) from trabajos_reparacion")).scalar() == 1
        assert cn.execute(text("select count(*) from conceptos_cotizacion")).scalar() == 3


def test_sin_commit_hay_rollback(contenedor):
    with contenedor.uow_factory() as uow:
        uow.clientes.guardar(cliente("Fantasma"))
    with contenedor.uow_factory() as uow:
        assert uow.clientes.buscar_por_id(cliente().id) is None
    with contenedor.engine.connect() as cn:
        assert cn.execute(text("select count(*) from clientes")).scalar() == 0


def test_rollback_explicito_ante_excepcion(contenedor):
    with pytest.raises(RuntimeError):
        with contenedor.uow_factory() as uow:
            uow.clientes.guardar(cliente()); uow.rollback(); raise RuntimeError("boom")
    with contenedor.engine.connect() as cn:
        assert cn.execute(text("select count(*) from clientes")).scalar() == 0


def test_catalogos_y_busquedas(contenedor):
    g = cliente("Gerente"); cuenta = cuenta_flotilla(g.id); v = vehiculo("FLT-1", cuenta.id)
    ch = cliente("Chofer", cuenta=cuenta.id); t1, t2 = tecnico(), tecnico(False)
    with contenedor.uow_factory() as uow:
        uow.clientes.guardar(g); uow.cuentas_flotilla.guardar(cuenta); uow.vehiculos.guardar(v)
        uow.clientes.guardar(ch); uow.tecnicos.guardar(t1); uow.tecnicos.guardar(t2)
        uow.commit()
    with contenedor.uow_factory() as uow:
        assert uow.cuentas_flotilla.obtener(cuenta.id).autorizador_corporativo_id == g.id
        assert uow.cuentas_flotilla.obtener(cuenta.id).condiciones.descuento.valor == 10
        assert uow.vehiculos.buscar_por_placas(Placas("flt-1")).cuenta_flotilla_id == cuenta.id
        assert uow.vehiculos.buscar_por_placas(Placas("zzz-999")) is None
        assert uow.clientes.obtener(ch.id).es_corporativo and uow.clientes.obtener(ch.id).activo
        assert [t.id for t in uow.tecnicos.listar_disponibles()] == [t1.id]
        assert uow.tecnicos.obtener(t2.id).disponible is False


def test_listados_y_no_encontrado(contenedor):
    esc = Escenario()
    with contenedor.uow_factory() as uow:
        c, v, _ = _guardar_base(uow, esc); uow.ordenes.guardar(esc.orden); uow.commit()
    with contenedor.uow_factory() as uow:
        assert [o.id for o in uow.ordenes.listar_por_vehiculo(v.id)] == [esc.orden.id]
        assert [o.id for o in uow.ordenes.listar_por_cliente(c.id)] == [esc.orden.id]
        assert uow.ordenes.listar_por_vehiculo(VehiculoId.generar()) == []
        assert uow.ordenes.buscar_por_id(OrdenServicioId.generar()) is None
        for repo, id_ in ((uow.ordenes, OrdenServicioId.generar()), (uow.clientes, c.id.generar()),
                          (uow.vehiculos, VehiculoId.generar()), (uow.tecnicos, TecnicoId.generar())):
            with pytest.raises(EntidadNoEncontrada):
                repo.obtener(id_)
        from src.domain.value_objects import CuentaFlotillaId
        with pytest.raises(EntidadNoEncontrada):
            uow.cuentas_flotilla.obtener(CuentaFlotillaId.generar())
