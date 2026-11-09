from decimal import Decimal

from src.infrastructure.config import load_settings
from src.infrastructure.persistence import crear_engine


def test_valores_por_defecto_y_variables_de_entorno():
    s = load_settings({})
    assert s.database_url.startswith("sqlite") and s.tasa_iva == Decimal("16") and not s.es_produccion
    s = load_settings({"DATABASE_URL": "mysql+pymysql://u:p@db/x", "APP_ENV": "production", "API_PORT": "9000",
                       "TASA_IVA": "8", "SQL_ECHO": "true", "LOG_LEVEL": "debug"})
    assert s.es_produccion and s.api_port == 9000 and s.tasa_iva == Decimal("8") and s.sql_echo and s.log_level == "DEBUG"


def test_engine_sqlite_en_memoria_activa_llaves_foraneas():
    from sqlalchemy import text
    e = crear_engine("sqlite://")
    with e.connect() as cn:
        assert cn.execute(text("PRAGMA foreign_keys")).scalar() == 1
