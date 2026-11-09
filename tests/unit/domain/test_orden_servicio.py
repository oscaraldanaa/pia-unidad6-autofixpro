"""Agregado OrdenServicio y entidades: reglas del BRD (trazabilidad RN → prueba)."""
from datetime import timedelta
from decimal import Decimal

import pytest

from src.domain.entities import (
    Cliente, ConceptoCotizacion, EstadoConcepto, EstadoTrabajo, ResultadoCotizacion, Tecnico, TipoConcepto, Vehiculo,
)
from src.domain.events import (
    CotizacionParcialmenteAutorizada, FallaAdicionalDetectada, FechaModificada, OrdenRecibida, RefaccionSinExistencia,
    RetrasoPorRefaccion,
)
from src.domain.shared import ReglaDeNegocioViolada, ValorInvalido
from src.domain.state_machine import TransicionInvalida
from src.domain.value_objects import (
    ConceptoId, DatosContacto, Dinero, EstadoOrden as S, FechaEntrega, Kilometraje, Porcentaje, TecnicoId,
)
from tests.builders import AHORA, Escenario, cliente, cuenta_flotilla, evidencia, orden_recibida, recepcion, tecnico, vehiculo


class TestIngreso:
    def test_rn01_crea_orden_recibida_con_evento(self):
        o = orden_recibida()
        assert o.estado is S.RECIBIDO and not o.es_flotilla
        assert any(isinstance(e, OrdenRecibida) for e in o.recolectar_eventos())
        assert o.recolectar_eventos() == []                      # se limpian al recolectar

    def test_rn14_autorizador_es_el_cliente(self):
        c = cliente(); o = __import__("src.domain.entities", fromlist=["x"]).OrdenServicio.registrar_ingreso(c, vehiculo(), recepcion())
        assert o.autorizador_id == c.id

    def test_rn09_flotilla_usa_autorizador_corporativo(self):
        gerente, chofer = cliente("Gerente"), cliente("Chofer")
        cuenta = cuenta_flotilla(gerente.id)
        v = vehiculo(cuenta=cuenta.id)
        from src.domain.entities import OrdenServicio
        o = OrdenServicio.registrar_ingreso(chofer, v, recepcion(), cuenta)
        assert o.es_flotilla and o.autorizador_id == gerente.id
        with pytest.raises(ReglaDeNegocioViolada, match="RN-09"):
            OrdenServicio.registrar_ingreso(chofer, v, recepcion(), None)

    def test_flotilla_aplica_descuento_en_cotizaciones(self):
        from src.domain.entities import OrdenServicio
        g = cliente(); cuenta = cuenta_flotilla(g.id, "10")
        o = OrdenServicio.registrar_ingreso(cliente(), vehiculo(cuenta=cuenta.id), recepcion(), cuenta)
        o.registrar_diagnostico(TecnicoId.generar(), ["x"])
        mo = ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.MANO_DE_OBRA, "mo", Dinero.de(1000))
        o.generar_cotizacion([mo], Porcentaje.de(16))
        d = o.cotizacion_inicial.desglose
        assert (d.subtotal_bruto.monto, d.descuento.monto, d.subtotal.monto, d.impuestos.monto, d.total.monto) == (
            Decimal("1000.00"), Decimal("100.00"), Decimal("900.00"), Decimal("144.00"), Decimal("1044.00"))


class TestCotizacionYAutorizacion:
    def test_rn05_autorizacion_parcial_y_total_autorizado(self):
        esc = Escenario(); o = esc.autorizada()
        cot = o.cotizacion_inicial
        assert cot.resultado is ResultadoCotizacion.PARCIAL
        assert [c.estado for c in cot.conceptos] == [EstadoConcepto.AUTORIZADO, EstadoConcepto.AUTORIZADO, EstadoConcepto.RECHAZADO]
        assert o.total_autorizado == Dinero.de("1508.58")          # (500 + 800.50) * 1.16
        assert any(isinstance(e, CotizacionParcialmenteAutorizada) for e in o.recolectar_eventos())

    def test_rn11_cada_concepto_guarda_evidencia(self):
        esc = Escenario(); esc.autorizada()
        assert all(c.evidencia is not None for c in esc.orden.cotizacion_inicial.conceptos)

    def test_rn05_debe_decidirse_cada_concepto_y_una_sola_vez(self):
        esc = Escenario(); o = esc.cotizada()
        with pytest.raises(ReglaDeNegocioViolada):
            o.responder_cotizacion({esc.mo.id: True}, evidencia())
        o.responder_cotizacion({esc.mo.id: True, esc.rf.id: True, esc.extra.id: True}, evidencia())
        assert o.cotizacion_inicial.resultado is ResultadoCotizacion.AUTORIZADA
        with pytest.raises(ReglaDeNegocioViolada):
            o.cotizacion_inicial.responder({}, evidencia())

    def test_validaciones_de_cotizacion_y_conceptos(self):
        esc = Escenario(); esc.diagnosticada()
        with pytest.raises(ValorInvalido):
            esc.orden.generar_cotizacion([])
        with pytest.raises(ValorInvalido):
            esc.orden.generar_cotizacion([esc.mo, esc.mo])
        with pytest.raises(ValorInvalido):
            ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.REFACCION, " ", Dinero.de(1))
        with pytest.raises(ValorInvalido):
            ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.REFACCION, "x", Dinero.de(1), 0)
        with pytest.raises(ValorInvalido):
            esc.orden.registrar_diagnostico(esc.tec, ["  "])

    def test_rn13_solo_mano_de_obra_autorizada_genera_trabajos(self):
        esc = Escenario(); o = esc.en_reparacion()
        assert [t.concepto_id for t in o.trabajos] == [esc.mo.id]
        assert o.estado is S.EN_REPARACION

    def test_rn13_sin_mano_de_obra_autorizada_no_hay_trabajo(self):
        esc = Escenario(); esc.cotizada()
        esc.orden.responder_cotizacion({esc.mo.id: False, esc.rf.id: True, esc.extra.id: False}, evidencia())
        with pytest.raises(ReglaDeNegocioViolada, match="RN-13"):
            esc.orden.asignar_trabajos(esc.tec)
        assert esc.orden.estado is S.AUTORIZADO


class TestRefaccionesYFallas:
    def test_rn07_y_rn03_refaccion_faltante_y_retraso(self):
        esc = Escenario(); o = esc.en_reparacion(); o.recolectar_eventos()
        s = o.reportar_refaccion_sin_existencia(esc.rf.id, AHORA + timedelta(days=2), AHORA)
        assert o.estado is S.EN_ESPERA_REFACCION and s.pendiente
        o.actualizar_reposicion(s.id, AHORA + timedelta(days=4), "Proveedor retrasó")
        tipos = [type(e) for e in o.recolectar_eventos()]
        assert RefaccionSinExistencia in tipos and RetrasoPorRefaccion in tipos
        with pytest.raises(ValorInvalido):
            o.actualizar_reposicion(s.id, AHORA, " ")
        o.recibir_refaccion(s.id)
        assert o.estado is S.EN_REPARACION and not s.pendiente
        with pytest.raises(ReglaDeNegocioViolada):
            s.marcar_recibida()

    def test_rn07_solo_refacciones_autorizadas_y_sin_duplicar(self):
        esc = Escenario(); o = esc.en_reparacion()
        for malo in (esc.mo.id, esc.extra.id):                    # mano de obra / refacción rechazada
            with pytest.raises(ReglaDeNegocioViolada):
                o.reportar_refaccion_sin_existencia(malo)
        o.reportar_refaccion_sin_existencia(esc.rf.id)
        with pytest.raises(ReglaDeNegocioViolada, match="pendiente"):
            o.reportar_refaccion_sin_existencia(esc.rf.id)

    def test_rn04_falla_adicional_cotizacion_y_autorizacion(self):
        esc = Escenario(); o = esc.en_reparacion()
        s = o.registrar_falla_adicional(esc.tec, "Líquido contaminado", AHORA)
        assert any(isinstance(e, FallaAdicionalDetectada) for e in o.recolectar_eventos())
        with pytest.raises(ReglaDeNegocioViolada):                 # no se responde sin cotizar
            o.responder_ampliacion(s.id, {}, evidencia())
        nuevo = ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.MANO_DE_OBRA, "Cambio líquido", Dinero.de(200))
        o.enviar_cotizacion_complementaria(s.id, [nuevo], ahora=AHORA)
        with pytest.raises(ReglaDeNegocioViolada):
            o.enviar_cotizacion_complementaria(s.id, [nuevo])
        t0 = o.trabajos[0]
        o.finalizar_trabajo(t0.id); o.aprobar_revision_calidad(t0.id)
        with pytest.raises(TransicionInvalida):                    # ampliación pendiente bloquea la entrega
            o.marcar_lista_para_entrega()
        o.responder_ampliacion(s.id, {nuevo.id: True}, evidencia())
        assert len(o.trabajos) == 2
        assert o.total_autorizado == Dinero.de("1508.58") + Dinero.de("232.00")   # 200 + 16 % IVA

    def test_ampliacion_rechazada_no_crea_trabajo(self):
        esc = Escenario(); o = esc.en_reparacion()
        s = o.registrar_falla_adicional(esc.tec, "Falla")
        nuevo = ConceptoCotizacion(ConceptoId.generar(), TipoConcepto.MANO_DE_OBRA, "Arreglo", Dinero.de(100))
        o.enviar_cotizacion_complementaria(s.id, [nuevo])
        o.responder_ampliacion(s.id, {nuevo.id: False}, evidencia())
        assert len(o.trabajos) == 1
        with pytest.raises(ValorInvalido):
            o.registrar_falla_adicional(esc.tec, " ")

    def test_falla_solo_en_reparacion(self):
        with pytest.raises(ReglaDeNegocioViolada):
            Escenario().autorizada().registrar_falla_adicional(TecnicoId.generar(), "x")


class TestFechaEntrega:
    def test_rn06_historial_y_justificacion(self):
        o = orden_recibida()
        o.programar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=2)), AHORA)
        with pytest.raises(ReglaDeNegocioViolada):
            o.programar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=3)), AHORA)
        o.modificar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=5)), "Espera de refacción", AHORA)
        assert len(o.historial_fechas) == 1 and o.historial_fechas[0].justificacion == "Espera de refacción"
        assert any(isinstance(e, FechaModificada) for e in o.recolectar_eventos())
        with pytest.raises(ValorInvalido):
            o.modificar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=6)), " ", AHORA)
        with pytest.raises(ValorInvalido):                          # fecha en el pasado
            o.modificar_fecha_entrega(FechaEntrega(AHORA - timedelta(days=1)), "x", AHORA)

    def test_requiere_fecha_previa_y_orden_activa(self):
        o = orden_recibida()
        with pytest.raises(ReglaDeNegocioViolada):
            o.modificar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=1)), "x", AHORA)
        with pytest.raises(ValorInvalido):
            o.programar_fecha_entrega(FechaEntrega(AHORA - timedelta(days=1)), AHORA)
        o.cancelar("x")
        with pytest.raises(ReglaDeNegocioViolada):
            o.programar_fecha_entrega(FechaEntrega(AHORA + timedelta(days=1)), AHORA)


class TestCierre:
    def test_cobro_debe_igualar_total_autorizado(self):
        o = Escenario().lista()
        with pytest.raises(ReglaDeNegocioViolada, match="debe igualar"):
            o.registrar_cobro_y_cerrar(Dinero.de(1))
        o.registrar_cobro_y_cerrar(o.total_autorizado)
        assert o.estado is S.CERRADO and o.monto_cobrado == o.total_autorizado

    def test_calidad_en_orden(self):
        esc = Escenario(); o = esc.en_reparacion(); t = o.trabajos[0]
        with pytest.raises(ReglaDeNegocioViolada):
            o.aprobar_revision_calidad(t.id)                       # aún no finalizado
        o.finalizar_trabajo(t.id)
        with pytest.raises(ReglaDeNegocioViolada):
            o.finalizar_trabajo(t.id)
        assert t.estado is EstadoTrabajo.PENDIENTE_REVISION
        from src.domain.value_objects import TrabajoId
        with pytest.raises(ReglaDeNegocioViolada, match="No existe"):
            o.finalizar_trabajo(TrabajoId.generar())


class TestEntidades:
    def test_identidad_por_id(self):
        c = cliente()
        assert c == c and c != cliente() and len({c, c}) == 1 and "Cliente(" in repr(c)

    def test_cliente(self):
        c = cliente(); assert c.verificar_estatus_flotilla() is False
        c.desactivar(); assert not c.activo
        c.activar(); c.actualizar_contacto(DatosContacto(email="n@x.com")); assert c.contacto.email == "n@x.com"
        with pytest.raises(ValorInvalido):
            Cliente(c.id, " ", c.contacto)

    def test_vehiculo_km_no_disminuye(self):
        v = vehiculo(); v.actualizar_kilometraje(Kilometraje(60000))
        with pytest.raises(ReglaDeNegocioViolada):
            v.actualizar_kilometraje(Kilometraje(1))
        assert not v.es_de_flotilla
        with pytest.raises(ValorInvalido):
            Vehiculo(v.id, v.placas, " ", "x", Kilometraje(1))

    def test_tecnico(self):
        t = tecnico(); t.asignar()
        with pytest.raises(ReglaDeNegocioViolada):
            t.asignar()
        t.liberar(); assert t.disponible
        with pytest.raises(ValorInvalido):
            Tecnico(t.id, " ", "x")

    def test_cuenta_flotilla_valida(self):
        from src.domain.entities import CondicionesFlotilla, CuentaFlotilla
        from src.domain.value_objects import CuentaFlotillaId
        with pytest.raises(ValorInvalido):
            CuentaFlotilla(CuentaFlotillaId.generar(), " ", cliente().id)
        with pytest.raises(ValorInvalido):
            CondicionesFlotilla(prioridad=-1)
