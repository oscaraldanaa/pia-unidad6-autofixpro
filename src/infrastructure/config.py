"""Configuración por variables de entorno (12-Factor App, factor III)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


def _cargar_dotenv() -> None:
    try:  # opcional: en contenedores las variables llegan del entorno
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite:///./autofixpro.db"
    sql_echo: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    tasa_iva: Decimal = Decimal("16")
    canal_notificaciones: str = "log"

    @property
    def es_produccion(self) -> bool:
        return self.app_env.lower() == "production"


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        _cargar_dotenv()
        env = os.environ
    d = Settings()
    return Settings(
        app_env=env.get("APP_ENV", d.app_env),
        database_url=env.get("DATABASE_URL", d.database_url),
        sql_echo=env.get("SQL_ECHO", "false").lower() in ("1", "true", "yes"),
        log_level=env.get("LOG_LEVEL", d.log_level).upper(),
        api_host=env.get("API_HOST", d.api_host),
        api_port=int(env.get("API_PORT", d.api_port)),
        tasa_iva=Decimal(env.get("TASA_IVA", str(d.tasa_iva))),
        canal_notificaciones=env.get("CANAL_NOTIFICACIONES", d.canal_notificaciones),
    )
