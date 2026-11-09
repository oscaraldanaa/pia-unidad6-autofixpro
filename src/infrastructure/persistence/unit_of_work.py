from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from ...application.ports import UnitOfWork
from .repositorios import (
    SqlClienteRepository, SqlCuentaFlotillaRepository, SqlItemCatalogoRepository, SqlOrdenServicioRepository,
    SqlTecnicoRepository, SqlVehiculoRepository,
)


class SqlUnitOfWork(UnitOfWork):
    """Una sesión/transacción por caso de uso; sin ``commit`` explícito se hace rollback."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> "SqlUnitOfWork":
        s = self._session = self._session_factory()
        self.ordenes = SqlOrdenServicioRepository(s)
        self.clientes = SqlClienteRepository(s)
        self.vehiculos = SqlVehiculoRepository(s)
        self.tecnicos = SqlTecnicoRepository(s)
        self.cuentas_flotilla = SqlCuentaFlotillaRepository(s)
        self.catalogo = SqlItemCatalogoRepository(s)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._session is not None
        try:
            self._session.rollback()   # no-op tras commit; descarta cambios si hubo error u omisión
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        assert self._session is not None
        self._session.commit()

    def rollback(self) -> None:
        assert self._session is not None
        self._session.rollback()
