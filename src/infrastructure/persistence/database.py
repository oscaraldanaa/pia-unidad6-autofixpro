"""Engine, sesiones y creación de esquema. Compatible con SQLite y MySQL."""
from __future__ import annotations

import warnings

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite no maneja Decimal nativo; los importes tienen 2 decimales y se redondean al leer.
warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal objects natively.*")


class Base(DeclarativeBase):
    pass


def crear_engine(database_url: str, echo: bool = False) -> Engine:
    if database_url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool          # una sola conexión para BD en memoria
        engine = create_engine(database_url, echo=echo, **kwargs)

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):                     # SQLite: activar llaves foráneas
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
        return engine
    return create_engine(database_url, echo=echo, pool_pre_ping=True)


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


def crear_tablas(engine: Engine) -> None:
    from . import modelos  # noqa: F401  (registra los modelos en Base.metadata)
    Base.metadata.create_all(engine)
