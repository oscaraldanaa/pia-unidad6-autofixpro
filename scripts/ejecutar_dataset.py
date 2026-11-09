"""Ejecuta el paquete de datos del PIA (data/pia/*.csv) contra el sistema y genera la evidencia.

Uso:  python scripts/ejecutar_dataset.py [--db sqlite://] [--salida docs/evidencia]
Genera: casos_prueba_resultados.csv, transiciones_prueba_resultados.csv y resumen.md
"""
import argparse
import pathlib
import sys
from collections import Counter

raiz = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(raiz))

from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import crear_app  # noqa: E402
from src.infrastructure.bootstrap import crear_contenedor  # noqa: E402
from src.infrastructure.config import Settings  # noqa: E402
from tests.dataset.loader import cargar  # noqa: E402
from tests.dataset.runner import EjecutorDataset  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--db", default="sqlite://", help="URL de BD (por defecto SQLite en memoria; use una BD vacía)")
p.add_argument("--salida", default=str(raiz / "docs" / "evidencia"))
args = p.parse_args()

ds = cargar()
contenedor = crear_contenedor(Settings(database_url=args.db, app_env="test"))
ej = EjecutorDataset(TestClient(crear_app(contenedor)), contenedor, ds)
ej.preparar()
casos, trans = ej.ejecutar_casos(), ej.ejecutar_transiciones()
salida = pathlib.Path(args.salida)
ej.escribir(salida, casos, trans)

ok_c, ok_t = sum(c["coincide"] for c in casos), sum(t.coincide for t in trans)
por_tipo = Counter((c["tipo_prueba"], c["resultado_alumno"]) for c in casos)
por_accion = Counter((t.fila["accion_sugerida"], t.resultado, t.estado_final) for t in trans)
integ = ds.integridad()

md = ["# Evidencia de ejecución del paquete de datos PIA", "",
      f"- Casos de regla ejecutados: **{len(casos)}** · coinciden con el oráculo: **{ok_c}**",
      f"- Transiciones ejecutadas: **{len(trans)}** · coinciden con lo esperado: **{ok_t}**",
      f"- Datos: {len(ds.actores)} actores, {len(ds.recursos)} recursos, {len(ds.operaciones)} operaciones, "
      f"{sum(len(o.lineas) for o in ds.operaciones.values())} líneas de detalle", "",
      "## Resultados de reglas", "", "| Regla | Resultado | Casos |", "|---|---|---|"]
md += [f"| {t} | {r} | {n} |" for (t, r), n in sorted(por_tipo.items())]
md += ["", "## Resultados de transiciones", "", "| Acción | Resultado | Estado final | Casos |", "|---|---|---|---|"]
md += [f"| {a} | {r} | {e} | {n} |" for (a, r, e), n in sorted(por_accion.items())]
md += ["", "## Hallazgos de calidad de datos", ""]
md += [f"- **{k.replace('_', ' ')}** ({len(v)}): {', '.join(v) if v else '—'}" for k, v in integ.items()]
md += ["", "Detalle por caso (evidencia, orden interna, pasos HTTP y eventos de dominio) en los dos CSV de esta carpeta."]
(salida / "resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md[:6]))
print(f"\nEvidencia escrita en {salida}")
sys.exit(0 if (ok_c == len(casos) and ok_t == len(trans)) else 1)
