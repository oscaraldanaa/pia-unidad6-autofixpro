"""Regla de dependencia de Clean Architecture (ADR-001 §2.2)."""
import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
PROHIBIDOS = {
    "domain": {"sqlalchemy", "fastapi", "pydantic", "src.application", "src.infrastructure", "src.api",
               "application", "infrastructure", "api"},
    "application": {"sqlalchemy", "fastapi", "pydantic", "src.infrastructure", "src.api", "infrastructure", "api"},
    "infrastructure": {"fastapi", "src.api", "api"},
}


def _importaciones(ruta: pathlib.Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    paquete = ruta.relative_to(SRC.parent).with_suffix("").parts[:-1]
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for a in nodo.names:
                yield a.name
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:  # relativo: resolver contra el paquete actual
                base = list(paquete[: len(paquete) - nodo.level + 1])
                yield ".".join(base + ([nodo.module] if nodo.module else []))
            elif nodo.module:
                yield nodo.module


def test_las_capas_respetan_la_regla_de_dependencia():
    violaciones = []
    for capa, prohibidos in PROHIBIDOS.items():
        for archivo in (SRC / capa).rglob("*.py"):
            for imp in _importaciones(archivo):
                if any(imp == p or imp.startswith(p + ".") for p in prohibidos):
                    violaciones.append(f"{archivo.relative_to(SRC)} importa {imp}")
    assert not violaciones, "\n".join(violaciones)
