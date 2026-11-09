"""Patrón Specification: composición AND / OR / NOT y reglas concretas."""
import pytest

from src.domain.shared import ReglaDeNegocioViolada
from src.domain.specifications import (
    ClienteActivoSpec, MontoMinimoSpec, OrdenEsDeFlotillaSpec, OrdenListaParaEntregaSpec,
    RefaccionesDisponiblesSpec, SinAmpliacionesPendientesSpec, Specification, TecnicoDisponibleSpec,
    TieneTrabajosSpec, TodosTrabajosRevisadosSpec,
)
from src.domain.value_objects import Dinero
from tests.builders import Escenario, cliente, tecnico


class Siempre(Specification[int]):
    def es_satisfecha_por(self, c): return True


class Nunca(Specification[int]):
    def es_satisfecha_por(self, c): return False


def test_operadores_logicos():
    assert (Siempre() & Siempre()).es_satisfecha_por(1)
    assert not (Siempre() & Nunca()).es_satisfecha_por(1)
    assert (Siempre() | Nunca()).es_satisfecha_por(1)
    assert not (Nunca() | Nunca()).es_satisfecha_por(1)
    assert (~Nunca()).es_satisfecha_por(1)
    assert Siempre().y(Siempre()).o(Nunca()).no().es_satisfecha_por(1) is False   # métodos equivalentes


def test_verificar_lanza_regla():
    Siempre().verificar(1, "RN-01", "ok")
    with pytest.raises(ReglaDeNegocioViolada) as e:
        Nunca().verificar(1, "RN-07", "falla")
    assert e.value.regla == "RN-07"


def test_specs_de_catalogo():
    assert ClienteActivoSpec().es_satisfecha_por(cliente())
    assert not ClienteActivoSpec().es_satisfecha_por(cliente(activo=False))
    assert TecnicoDisponibleSpec().es_satisfecha_por(tecnico())
    assert not TecnicoDisponibleSpec().es_satisfecha_por(tecnico(False))
    minimo = MontoMinimoSpec(Dinero.de(100))
    assert minimo.es_satisfecha_por(Dinero.de(100)) and not minimo.es_satisfecha_por(Dinero.de(99))
    # composición: cliente activo Y NO técnico indisponible no mezcla tipos; se compone por tipo
    assert (TecnicoDisponibleSpec() | ~TecnicoDisponibleSpec()).es_satisfecha_por(tecnico(False))


def test_specs_de_orden_y_composicion_lista_para_entrega():
    esc = Escenario()
    orden = esc.en_reparacion()
    assert TieneTrabajosSpec().es_satisfecha_por(orden)
    assert not TodosTrabajosRevisadosSpec().es_satisfecha_por(orden)
    assert SinAmpliacionesPendientesSpec().es_satisfecha_por(orden)
    assert RefaccionesDisponiblesSpec().es_satisfecha_por(orden)
    assert not OrdenEsDeFlotillaSpec().es_satisfecha_por(orden)
    spec = OrdenListaParaEntregaSpec()
    assert not spec.es_satisfecha_por(orden)
    t = orden.trabajos[0]
    orden.finalizar_trabajo(t.id); orden.aprobar_revision_calidad(t.id)
    assert spec.es_satisfecha_por(orden)
    orden.reportar_refaccion_sin_existencia(esc.rf.id)
    assert not spec.es_satisfecha_por(orden)          # refacción pendiente en Compras
