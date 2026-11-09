"""Genera docs/api/openapi.json a partir de la aplicación. Uso: python scripts/exportar_openapi.py"""
import json
import pathlib
import sys

raiz = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(raiz))

from src.api.main import crear_app  # noqa: E402

destino = raiz / "docs" / "api" / "openapi.json"
destino.write_text(json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OpenAPI escrito en {destino.relative_to(raiz)}")
