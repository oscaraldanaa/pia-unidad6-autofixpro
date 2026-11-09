from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from src.api.main import crear_app
from src.infrastructure.bootstrap import Contenedor, crear_contenedor
from src.infrastructure.config import Settings
from src.infrastructure.persistence import Base, crear_tablas


@pytest.fixture
def contenedor() -> Contenedor:
    """BD aislada por prueba. Usa TEST_DATABASE_URL (MySQL en CI/Docker) o SQLite en memoria."""
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    c = crear_contenedor(Settings(database_url=url, app_env="test"), crear_esquema=False)
    Base.metadata.drop_all(c.engine)
    crear_tablas(c.engine)
    yield c
    Base.metadata.drop_all(c.engine)
    c.engine.dispose()


@pytest.fixture
def api(contenedor) -> TestClient:
    return TestClient(crear_app(contenedor))
