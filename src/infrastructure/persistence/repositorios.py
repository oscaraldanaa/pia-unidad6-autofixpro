"""Repositorios concretos (adaptadores SQLAlchemy) de los puertos de ``application``."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...application.ports import (
    ClienteRepository, CuentaFlotillaRepository, ItemCatalogoRepository, OrdenServicioRepository, TecnicoRepository,
    VehiculoRepository,
)
from ...domain.entities import Cliente, CuentaFlotilla, ItemCatalogo, OrdenServicio, Tecnico, Vehiculo
from ...domain.shared import EntidadNoEncontrada
from ...domain.value_objects import (
    ClienteId, CuentaFlotillaId, OrdenServicioId, Placas, RecursoId, TecnicoId, VehiculoId,
)
from . import mappers as mp
from . import modelos as m


class _SqlBase:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _guardar(self, record) -> None:
        self._s.merge(record)   # upsert por clave primaria (incluye hijos con cascade)
        self._s.flush()


class SqlOrdenServicioRepository(_SqlBase, OrdenServicioRepository):
    def guardar(self, orden: OrdenServicio) -> None:
        self._guardar(mp.orden_a_record(orden))

    def buscar_por_id(self, id: OrdenServicioId) -> OrdenServicio | None:
        r = self._s.get(m.OrdenServicioRecord, str(id))
        return mp.record_a_orden(r) if r else None

    def obtener(self, id: OrdenServicioId) -> OrdenServicio:
        orden = self.buscar_por_id(id)
        if orden is None:
            raise EntidadNoEncontrada(f"No existe la orden de servicio {id}")
        return orden

    def _listar(self, columna, valor) -> list[OrdenServicio]:
        stmt = select(m.OrdenServicioRecord).where(columna == str(valor)).order_by(m.OrdenServicioRecord.creada_en)
        return [mp.record_a_orden(r) for r in self._s.scalars(stmt)]

    def listar_por_vehiculo(self, vehiculo_id: VehiculoId) -> list[OrdenServicio]:
        return self._listar(m.OrdenServicioRecord.vehiculo_id, vehiculo_id)

    def listar_por_cliente(self, cliente_id: ClienteId) -> list[OrdenServicio]:
        return self._listar(m.OrdenServicioRecord.cliente_id, cliente_id)


class SqlClienteRepository(_SqlBase, ClienteRepository):
    def guardar(self, cliente: Cliente) -> None:
        self._guardar(mp.cliente_a_record(cliente))

    def buscar_por_id(self, id: ClienteId) -> Cliente | None:
        r = self._s.get(m.ClienteRecord, str(id))
        return mp.record_a_cliente(r) if r else None

    def obtener(self, id: ClienteId) -> Cliente:
        c = self.buscar_por_id(id)
        if c is None:
            raise EntidadNoEncontrada(f"No existe el cliente {id}")
        return c


class SqlVehiculoRepository(_SqlBase, VehiculoRepository):
    def guardar(self, vehiculo: Vehiculo) -> None:
        self._guardar(mp.vehiculo_a_record(vehiculo))

    def buscar_por_id(self, id: VehiculoId) -> Vehiculo | None:
        r = self._s.get(m.VehiculoRecord, str(id))
        return mp.record_a_vehiculo(r) if r else None

    def buscar_por_placas(self, placas: Placas) -> Vehiculo | None:
        r = self._s.scalars(select(m.VehiculoRecord).where(m.VehiculoRecord.placas == placas.valor)).first()
        return mp.record_a_vehiculo(r) if r else None

    def obtener(self, id: VehiculoId) -> Vehiculo:
        v = self.buscar_por_id(id)
        if v is None:
            raise EntidadNoEncontrada(f"No existe el vehículo {id}")
        return v


class SqlTecnicoRepository(_SqlBase, TecnicoRepository):
    def guardar(self, tecnico: Tecnico) -> None:
        self._guardar(mp.tecnico_a_record(tecnico))

    def buscar_por_id(self, id: TecnicoId) -> Tecnico | None:
        r = self._s.get(m.TecnicoRecord, str(id))
        return mp.record_a_tecnico(r) if r else None

    def obtener(self, id: TecnicoId) -> Tecnico:
        t = self.buscar_por_id(id)
        if t is None:
            raise EntidadNoEncontrada(f"No existe el técnico {id}")
        return t

    def listar_disponibles(self) -> list[Tecnico]:
        stmt = select(m.TecnicoRecord).where(m.TecnicoRecord.disponible.is_(True)).order_by(m.TecnicoRecord.nombre)
        return [mp.record_a_tecnico(r) for r in self._s.scalars(stmt)]


class SqlCuentaFlotillaRepository(_SqlBase, CuentaFlotillaRepository):
    def guardar(self, cuenta: CuentaFlotilla) -> None:
        self._guardar(mp.cuenta_a_record(cuenta))

    def buscar_por_id(self, id: CuentaFlotillaId) -> CuentaFlotilla | None:
        r = self._s.get(m.CuentaFlotillaRecord, str(id))
        return mp.record_a_cuenta(r) if r else None

    def obtener(self, id: CuentaFlotillaId) -> CuentaFlotilla:
        c = self.buscar_por_id(id)
        if c is None:
            raise EntidadNoEncontrada(f"No existe la cuenta de flotilla {id}")
        return c


class SqlItemCatalogoRepository(_SqlBase, ItemCatalogoRepository):
    def guardar(self, item: ItemCatalogo) -> None:
        self._guardar(mp.item_a_record(item))

    def buscar_por_id(self, id: RecursoId) -> ItemCatalogo | None:
        r = self._s.get(m.ItemCatalogoRecord, str(id))
        return mp.record_a_item(r) if r else None

    def obtener(self, id: RecursoId) -> ItemCatalogo:
        i = self.buscar_por_id(id)
        if i is None:
            raise EntidadNoEncontrada(f"No existe el recurso {id} en el catálogo")
        return i

    def listar(self) -> list[ItemCatalogo]:
        return [mp.record_a_item(r) for r in self._s.scalars(select(m.ItemCatalogoRecord).order_by(m.ItemCatalogoRecord.id))]
