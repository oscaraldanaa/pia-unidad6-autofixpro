"""Puertos (interfaces) que la infraestructura implementa. Dependen solo del dominio."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Iterable

from ..domain.entities import Cliente, CuentaFlotilla, ItemCatalogo, OrdenServicio, Tecnico, Vehiculo
from ..domain.shared import DomainEvent
from ..domain.value_objects import (
    ClienteId, CuentaFlotillaId, DatosContacto, OrdenServicioId, Placas, RecursoId, TecnicoId, VehiculoId,
)


class OrdenServicioRepository(ABC):
    @abstractmethod
    def guardar(self, orden: OrdenServicio) -> None: ...
    @abstractmethod
    def buscar_por_id(self, id: OrdenServicioId) -> OrdenServicio | None: ...
    @abstractmethod
    def obtener(self, id: OrdenServicioId) -> OrdenServicio:
        """Como ``buscar_por_id`` pero lanza ``EntidadNoEncontrada``."""
    @abstractmethod
    def listar_por_vehiculo(self, vehiculo_id: VehiculoId) -> list[OrdenServicio]: ...
    @abstractmethod
    def listar_por_cliente(self, cliente_id: ClienteId) -> list[OrdenServicio]: ...


class ClienteRepository(ABC):
    @abstractmethod
    def guardar(self, cliente: Cliente) -> None: ...
    @abstractmethod
    def buscar_por_id(self, id: ClienteId) -> Cliente | None: ...
    @abstractmethod
    def obtener(self, id: ClienteId) -> Cliente: ...


class VehiculoRepository(ABC):
    @abstractmethod
    def guardar(self, vehiculo: Vehiculo) -> None: ...
    @abstractmethod
    def buscar_por_id(self, id: VehiculoId) -> Vehiculo | None: ...
    @abstractmethod
    def buscar_por_placas(self, placas: Placas) -> Vehiculo | None: ...
    @abstractmethod
    def obtener(self, id: VehiculoId) -> Vehiculo: ...


class TecnicoRepository(ABC):
    @abstractmethod
    def guardar(self, tecnico: Tecnico) -> None: ...
    @abstractmethod
    def buscar_por_id(self, id: TecnicoId) -> Tecnico | None: ...
    @abstractmethod
    def obtener(self, id: TecnicoId) -> Tecnico: ...
    @abstractmethod
    def listar_disponibles(self) -> list[Tecnico]: ...


class CuentaFlotillaRepository(ABC):
    @abstractmethod
    def guardar(self, cuenta: CuentaFlotilla) -> None: ...
    @abstractmethod
    def buscar_por_id(self, id: CuentaFlotillaId) -> CuentaFlotilla | None: ...
    @abstractmethod
    def obtener(self, id: CuentaFlotillaId) -> CuentaFlotilla: ...


class ItemCatalogoRepository(ABC):
    @abstractmethod
    def guardar(self, item: ItemCatalogo) -> None: ...
    @abstractmethod
    def buscar_por_id(self, id: RecursoId) -> ItemCatalogo | None: ...
    @abstractmethod
    def obtener(self, id: RecursoId) -> ItemCatalogo: ...
    @abstractmethod
    def listar(self) -> list[ItemCatalogo]: ...


class UnitOfWork(ABC):
    """Una transacción por caso de uso. Se usa como context manager."""

    ordenes: OrdenServicioRepository
    clientes: ClienteRepository
    vehiculos: VehiculoRepository
    tecnicos: TecnicoRepository
    cuentas_flotilla: CuentaFlotillaRepository
    catalogo: ItemCatalogoRepository

    @abstractmethod
    def __enter__(self) -> "UnitOfWork": ...
    @abstractmethod
    def __exit__(self, exc_type, exc, tb) -> None: ...
    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]


class EventBus(ABC):
    @abstractmethod
    def publicar(self, eventos: Iterable[DomainEvent]) -> None: ...
    @abstractmethod
    def suscribir(self, tipo_evento: type, manejador: Callable[[DomainEvent], None]) -> None: ...


class Notificador(ABC):
    """Canal configurable (SMS, correo, portal) hacia el cliente (RN-03, RN-06)."""

    @abstractmethod
    def enviar(self, destinatario: DatosContacto, asunto: str, mensaje: str) -> None: ...
