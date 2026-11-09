"""Paquete de datos del PIA (data/pia): 120 casos de regla + 20 transiciones ejecutados contra la API real."""
import csv

import pytest
from fastapi.testclient import TestClient

from src.api.main import crear_app
from src.infrastructure.bootstrap import crear_contenedor
from src.infrastructure.config import Settings
from tests.dataset import oraculo
from tests.dataset.loader import cargar
from tests.dataset.runner import EjecutorDataset


@pytest.fixture(scope="module")
def corrida():
    ds = cargar()
    c = crear_contenedor(Settings(database_url="sqlite://", app_env="test"))
    ej = EjecutorDataset(TestClient(crear_app(c)), c, ds)
    ej.preparar()
    casos, trans = ej.ejecutar_casos(), ej.ejecutar_transiciones()
    yield ds, ej, casos, trans
    c.engine.dispose()


def test_integridad_del_paquete():
    ds = cargar()
    assert (len(ds.actores), len(ds.recursos), len(ds.operaciones), len(ds.casos), len(ds.transiciones)) == (40, 20, 60, 120, 20)
    h = ds.integridad()
    assert h["operaciones_sin_detalle"] == ["AUT-O013", "AUT-O039"]
    assert h["operaciones_con_recurso_deshabilitado"] == [f"AUT-O{n:03d}" for n in (5, 15, 20, 35, 40, 55)]
    assert h["operaciones_con_cantidad_sobre_capacidad"] == [] and h["referencias_huerfanas"] == []
    assert len(h["operaciones_con_actor_inactivo"]) == 9 and len(h["operaciones_sin_autorizacion"]) == 7


def test_total_con_decimal_suma_precio_por_cantidad():
    ds = cargar()
    from decimal import Decimal
    assert ds.total("AUT-O001") == Decimal("7909.00")        # 927×3 + 1282×4
    assert ds.total("AUT-O013") == Decimal("0")


def test_los_120_casos_de_regla_coinciden_con_el_oraculo(corrida):
    _, _, casos, _ = corrida
    assert len(casos) == 120
    fallos = [(c["caso_id"], c["resultado_alumno"], c["valor_oraculo"]) for c in casos if not c["coincide"]]
    assert not fallos, fallos
    por_tipo = {}
    for c in casos:
        por_tipo.setdefault((c["tipo_prueba"], c["resultado_alumno"]), 0)
        por_tipo[(c["tipo_prueba"], c["resultado_alumno"])] += 1
    assert por_tipo == {("validar_operacion", "VERDADERO"): 43, ("validar_operacion", "FALSO"): 17,
                        ("evaluar_beneficio", "VERDADERO"): 9, ("evaluar_beneficio", "FALSO"): 51}


def test_total_del_sistema_coincide_con_el_calculo_de_los_csv(corrida):
    ds, ej, _, _ = corrida
    from decimal import Decimal
    for op in ds.operaciones.values():
        assert Decimal(ej.evaluacion(op.operacion_id)["total_referencia"]) == ds.total(op)


def test_las_20_transiciones_coinciden_y_registran_eventos_o_excepcion(corrida):
    _, _, _, trans = corrida
    assert len(trans) == 20 and all(t.coincide for t in trans), [t.fila["caso_id"] for t in trans if not t.coincide]
    for t in trans:
        accion = t.fila["accion_sugerida"]
        assert t.eventos.startswith("OrdenRecibida")                       # trazabilidad por evento
        if t.resultado == "RECHAZADA":
            assert t.detalle and t.pasos[-1].startswith(("409", "422"))    # excepción registrada
        if accion == "cancelar":
            assert "OrdenCancelada" in t.eventos
        if accion == "aprobar":
            assert t.eventos.endswith("DiagnosticoRegistrado") or "DiagnosticoRegistrado" in t.eventos


def test_completar_cubre_los_cuatro_desenlaces(corrida):
    _, _, _, trans = corrida
    comp = {(t.resultado, t.estado_final) for t in trans if t.fila["accion_sugerida"] == "completar"}
    assert ("EXITO", "ENTREGADA") in comp and ("RECHAZADA", "COTIZADA*") in comp and ("RECHAZADA", "AUTORIZADA*") in comp


def test_escritura_de_evidencia(corrida, tmp_path):
    ds, ej, casos, trans = corrida
    ej.escribir(tmp_path, casos, trans)
    with (tmp_path / "casos_prueba_resultados.csv").open(encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    assert len(filas) == 120 and set(ds.columnas_casos) <= set(filas[0]) and {f["resultado_alumno"] for f in filas} == {"VERDADERO", "FALSO"}
    with (tmp_path / "transiciones_prueba_resultados.csv").open(encoding="utf-8-sig") as f:
        assert len(list(csv.DictReader(f))) == 20


def test_oraculo_rechaza_accion_desconocida():
    ds = cargar()
    with pytest.raises(ValueError):
        oraculo.transicion(ds, ds.operaciones["AUT-O001"], "inventada")


def test_sembrar_en_bd_es_idempotente_y_genera_mapa_de_ids(tmp_path):
    from sqlalchemy import text
    from tests.dataset.sembrador import YaCargado, escribir_mapa, sembrar
    c = crear_contenedor(Settings(database_url="sqlite://", app_env="test"))
    ej = sembrar(c, cargar())
    with c.engine.connect() as cn:
        n = {t: cn.execute(text(f"select count(*) from {t}")).scalar()
             for t in ("clientes", "catalogo", "ordenes_servicio", "vehiculos", "tecnicos")}
    assert n == {"clientes": 40, "catalogo": 20, "ordenes_servicio": 80, "vehiculos": 80, "tecnicos": 1}
    with pytest.raises(YaCargado):
        sembrar(c, cargar())
    filas = list(csv.DictReader((lambda r: (escribir_mapa(ej, r), r.open(encoding="utf-8-sig"))[1])(tmp_path / "mapa.csv")))
    assert len(filas) == 40 + 20 + 60 + 20 + 1
    assert next(f for f in filas if f["id_paquete"] == "AUT-O005")["id_sistema"].startswith("ORD-")
    c.engine.dispose()
