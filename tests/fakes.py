"""Dobles en memoria de los puertos de application (permiten probar casos de uso sin BD)."""
from __future__ import annotations

from src.application.ports import (
    ClienteRepository, CuentaFlotillaRepository, EventBus, ItemCatalogoRepository, Notificador,
    OrdenServicioRepository, TecnicoRepository, UnitOfWork, VehiculoRepository,
)
from src.domain.shared import EntidadNoEncontrada


class _Mem:
    def __init__(self, nombre: str) -> None:
        self.datos: dict = {}
        self._nombre = nombre

    def guardar(self, e): self.datos[e.id] = e
    def buscar_por_id(self, id): return self.datos.get(id)

    def obtener(self, id):
        if id not in self.datos:
            raise EntidadNoEncontrada(f"No existe {self._nombre} {id}")
        return self.datos[id]


class MemOrdenes(_Mem, OrdenServicioRepository):
    def listar_por_vehiculo(self, v): return [o for o in self.datos.values() if o.vehiculo_id == v]
    def listar_por_cliente(self, c): return [o for o in self.datos.values() if o.cliente_id == c]


class MemClientes(_Mem, ClienteRepository): ...
class MemCuentas(_Mem, CuentaFlotillaRepository): ...


class MemVehiculos(_Mem, VehiculoRepository):
    def buscar_por_placas(self, placas): return next((v for v in self.datos.values() if v.placas == placas), None)


class MemTecnicos(_Mem, TecnicoRepository):
    def listar_disponibles(self): return [t for t in self.datos.values() if t.disponible]


class MemCatalogo(_Mem, ItemCatalogoRepository):
    def listar(self): return list(self.datos.values())


class MemUoW(UnitOfWork):
    """Comparte repositorios entre ejecuciones; registra commits y rollbacks."""

    def __init__(self) -> None:
        self.ordenes, self.clientes = MemOrdenes("orden"), MemClientes("cliente")
        self.vehiculos, self.tecnicos = MemVehiculos("vehículo"), MemTecnicos("técnico")
        self.cuentas_flotilla = MemCuentas("cuenta")
        self.catalogo = MemCatalogo("recurso")
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self): return self
    def __exit__(self, et, ev, tb):
        if et:
            self.rollback()
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


class BusEspia(EventBus):
    def __init__(self) -> None:
        self.publicados: list = []
        self.suscripciones: list = []

    def publicar(self, eventos): self.publicados.extend(eventos)
    def suscribir(self, tipo, manejador): self.suscripciones.append((tipo, manejador))


class NotificadorEspia(Notificador):
    def __init__(self) -> None:
        self.enviados: list = []

    def enviar(self, destinatario, asunto, mensaje): self.enviados.append((destinatario, asunto, mensaje))
