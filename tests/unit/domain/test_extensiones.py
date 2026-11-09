"""Extensiones derivadas del paquete de datos: catálogo, cliente preferente, promoción y reglas compuestas."""
from decimal import Decimal

import pytest

from src.domain.entities import ItemCatalogo, OrdenServicio, TipoConcepto
from src.domain.shared import ReglaDeNegocioViolada, ValorInvalido
from src.domain.specifications import (
    ContextoOperacion, SobreCliente, SobreOrden, TotalMinimoSpec, beneficio_referencia, criterios, puede_procesarse,
)
from src.domain.value_objects import Dinero, RecursoId, TecnicoId
from tests.builders import AHORA, cliente, evidencia, mano_obra, recepcion, vehiculo
from src.domain.entities import Cliente
from src.domain.value_objects import ClienteId, DatosContacto


def item(cap=10, hab=True, precio="500"):
    return ItemCatalogo(RecursoId("AUT-P001"), "Frenos", Dinero.de(precio), cap, hab)


class TestItemCatalogo:
    def test_valida_cantidad_habilitado_y_capacidad(self):
        assert item().validar_cantidad(3) == Decimal(3)
        with pytest.raises(ValorInvalido):
            item().validar_cantidad(0)
        with pytest.raises(ReglaDeNegocioViolada) as e:
            item(hab=False).validar_cantidad(1)
        assert e.value.regla == "CAT-01"
        with pytest.raises(ReglaDeNegocioViolada) as e:
            item(cap=2).validar_cantidad(3)
        assert e.value.regla == "CAT-02"
        assert item(cap=2).validar_cantidad(2) == Decimal(2)           # el límite es válido

    def test_a_concepto_usa_precio_oficial_y_conserva_el_recurso(self):
        c = item(precio="430.00").a_concepto(2)
        assert c.importe == Dinero.de(860) and c.recurso_id == RecursoId("AUT-P001") and c.tipo is TipoConcepto.MANO_DE_OBRA

    def test_habilitar_deshabilitar(self):
        i = item(); i.deshabilitar(); assert not i.habilitado
        i.habilitar(); assert i.habilitado

    @pytest.mark.parametrize("kw", [dict(descripcion=" "), dict(precio=Dinero.cero()), dict(capacidad=-1), dict(capacidad=True)])
    def test_invariantes(self, kw):
        base = dict(id=RecursoId("R"), descripcion="x", precio=Dinero.de(1), capacidad=1)
        with pytest.raises(ValorInvalido):
            ItemCatalogo(**{**base, **kw})


def _ctx(preferente=False, activo=True, promo=False, autorizar=True, precio="800"):
    c = Cliente(ClienteId.generar(), "X", DatosContacto(telefono="8112345678"), activo=activo, es_preferente=preferente)
    o = OrdenServicio.registrar_ingreso(c, vehiculo(), recepcion(), ahora=AHORA, promocion_activa=promo)
    tec = TecnicoId.generar()
    if precio:
        o.registrar_diagnostico(tec, ["x"])
        k = mano_obra(precio)
        o.generar_cotizacion([k], ahora=AHORA)
        if autorizar:
            o.responder_cotizacion({k.id: True}, evidencia())
    return ContextoOperacion(c, o)


class TestReglasCompuestas:
    def test_puede_procesarse_and(self):
        assert puede_procesarse().es_satisfecha_por(_ctx())
        assert not puede_procesarse().es_satisfecha_por(_ctx(activo=False))
        assert not puede_procesarse().es_satisfecha_por(_ctx(autorizar=False))
        assert not puede_procesarse().es_satisfecha_por(_ctx(precio=None))      # sin detalle ni cotización

    def test_beneficio_and_not(self):
        assert beneficio_referencia().es_satisfecha_por(_ctx(preferente=True, precio="1500"))        # borde: >= 1500
        assert not beneficio_referencia().es_satisfecha_por(_ctx(preferente=True, precio="1499.99"))
        assert not beneficio_referencia().es_satisfecha_por(_ctx(preferente=False, precio="5000"))
        assert not beneficio_referencia().es_satisfecha_por(_ctx(preferente=True, precio="5000", promo=True))

    def test_total_de_referencia_excluye_impuestos_y_se_combina_con_or(self):
        ctx = _ctx(preferente=True, precio="1400")                       # con IVA serían 1624, pero el total es 1400
        assert ctx.orden.total_referencia == Dinero.de(1400)
        assert not SobreOrden(TotalMinimoSpec(Dinero.de(1500))).es_satisfecha_por(ctx)
        alguno = SobreOrden(TotalMinimoSpec(Dinero.de(1500))) | SobreCliente(__import__("src.domain.specifications", fromlist=["x"]).ClientePreferenteSpec())
        assert alguno.es_satisfecha_por(ctx)

    def test_criterios_explican_el_resultado(self):
        k = criterios(_ctx(preferente=True, activo=False, promo=True, precio="2000"))
        assert k == {"cliente_activo": False, "con_detalle": True, "autorizada": True, "cliente_preferente": True,
                     "total_minimo": True, "promocion_activa": True}

    def test_orden_nueva_total_cero_y_promocion(self):
        o = _ctx(promo=True, precio=None).orden
        assert o.total_referencia == Dinero.cero() and o.promocion_activa
