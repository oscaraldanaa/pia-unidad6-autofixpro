"""Carga el paquete de datos del PIA (data/pia/*.csv) en la base de datos configurada.

Usa DATABASE_URL de tu .env (por defecto sqlite:///./autofixpro.db) o el parámetro --db.
Deja en la base: 40 clientes, 20 recursos de catálogo, 1 técnico, 60 órdenes de las operaciones
(cotizadas y autorizadas según el CSV) y 20 órdenes en RECIBIDA para probar las transiciones.
Además escribe docs/evidencia/mapa_ids.csv (ID del paquete -> ID del sistema).

Uso:  python scripts/cargar_datos.py [--db sqlite:///./autofixpro.db]
"""
import argparse
import pathlib
import sys

raiz = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(raiz))

from src.infrastructure.bootstrap import crear_contenedor  # noqa: E402
from src.infrastructure.config import load_settings  # noqa: E402
from tests.dataset.loader import cargar  # noqa: E402
from tests.dataset.sembrador import YaCargado, escribir_mapa, sembrar  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--db", help="URL de la base (por defecto la de DATABASE_URL / .env)")
args = p.parse_args()

settings = load_settings()
if args.db:
    settings = type(settings)(**{**settings.__dict__, "database_url": args.db})
print(f"Base de datos: {settings.database_url.split('@')[-1]}")
contenedor = crear_contenedor(settings)
try:
    ej = sembrar(contenedor, cargar())
except YaCargado as e:
    sys.exit(f"{e} No se cargó nada. Para volver a cargar use una base vacía (borre el archivo .db).")
n = escribir_mapa(ej, raiz / "docs" / "evidencia" / "mapa_ids.csv")
print(f"Listo: {len(ej.cliente)} clientes, {len(ej.recurso)} recursos, {len(ej.orden_eval)} órdenes de operaciones, "
      f"{len(ej.orden_trans)} órdenes para transiciones.")
print(f"Equivalencia de IDs (AUT-… -> ORD-…): docs/evidencia/mapa_ids.csv ({n} filas)")
