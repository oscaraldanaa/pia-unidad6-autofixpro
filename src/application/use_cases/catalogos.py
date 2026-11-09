"""Alta de clientes, vehículos, técnicos y cuentas de flotilla."""
from __future__ import annotations

from ...domain.entities import Cliente, CondicionesFlotilla, CuentaFlotilla, ItemCatalogo, Tecnico, Vehiculo
from ...domain.shared import ReglaDeNegocioViolada
from ...domain.value_objects import (
    ClienteId, CuentaFlotillaId, DatosContacto, Dinero, Kilometraje, Placas, Porcentaje, RecursoId, TecnicoId,
    VehiculoId, Vin,
)
from ..dto import (
    CambiarEstadoClienteCmd, ItemCatalogoDTO, RegistrarClienteCmd, RegistrarCuentaFlotillaCmd,
    RegistrarItemCatalogoCmd, RegistrarTecnicoCmd, RegistrarVehiculoCmd,
)
from .base import CasoDeUso


class RegistrarCliente(CasoDeUso):
    def ejecutar(self, cmd: RegistrarClienteCmd) -> str:
        with self._uow_factory() as uow:
            cuenta_id = CuentaFlotillaId.desde_str(cmd.cuenta_flotilla_id) if cmd.cuenta_flotilla_id else None
            if cuenta_id:
                uow.cuentas_flotilla.obtener(cuenta_id)
            cliente = Cliente(ClienteId.generar(), cmd.nombre, DatosContacto(cmd.telefono, cmd.email), cuenta_id,
                              cmd.activo, cmd.es_preferente)
            uow.clientes.guardar(cliente)
            uow.commit()
        return str(cliente.id)


class RegistrarVehiculo(CasoDeUso):
    def ejecutar(self, cmd: RegistrarVehiculoCmd) -> str:
        with self._uow_factory() as uow:
            placas = Placas(cmd.placas)
            if uow.vehiculos.buscar_por_placas(placas):
                raise ReglaDeNegocioViolada("RN-01", f"Ya existe un vehículo con placas {placas.valor}")
            cuenta_id = CuentaFlotillaId.desde_str(cmd.cuenta_flotilla_id) if cmd.cuenta_flotilla_id else None
            if cuenta_id:
                uow.cuentas_flotilla.obtener(cuenta_id)
            vehiculo = Vehiculo(VehiculoId.generar(), placas, cmd.marca, cmd.modelo, Kilometraje(cmd.kilometraje),
                                Vin(cmd.vin) if cmd.vin else None, cuenta_id)
            uow.vehiculos.guardar(vehiculo)
            uow.commit()
        return str(vehiculo.id)


class RegistrarTecnico(CasoDeUso):
    def ejecutar(self, cmd: RegistrarTecnicoCmd) -> str:
        with self._uow_factory() as uow:
            tecnico = Tecnico(TecnicoId.generar(), cmd.nombre, cmd.especialidad)
            uow.tecnicos.guardar(tecnico)
            uow.commit()
        return str(tecnico.id)


class RegistrarCuentaFlotilla(CasoDeUso):
    def ejecutar(self, cmd: RegistrarCuentaFlotillaCmd) -> str:
        with self._uow_factory() as uow:
            autorizador = uow.clientes.obtener(ClienteId.desde_str(cmd.autorizador_corporativo_id))
            cuenta = CuentaFlotilla(
                CuentaFlotillaId.generar(), cmd.razon_social, autorizador.id,
                CondicionesFlotilla(Porcentaje.de(cmd.descuento_pct), cmd.prioridad, cmd.dias_credito))
            uow.cuentas_flotilla.guardar(cuenta)
            uow.commit()
        return str(cuenta.id)


class CambiarEstadoCliente(CasoDeUso):
    """Da de alta/baja a un cliente (afecta la precondición ``cliente_activo``)."""

    def ejecutar(self, cmd: CambiarEstadoClienteCmd) -> None:
        with self._uow_factory() as uow:
            cliente = uow.clientes.obtener(ClienteId.desde_str(cmd.cliente_id))
            cliente.activar() if cmd.activo else cliente.desactivar()
            uow.clientes.guardar(cliente)
            uow.commit()


def _item_dto(i: ItemCatalogo) -> ItemCatalogoDTO:
    return ItemCatalogoDTO(str(i.id), i.descripcion, i.precio.monto, i.capacidad, i.habilitado)


class RegistrarItemCatalogo(CasoDeUso):
    def ejecutar(self, cmd: RegistrarItemCatalogoCmd) -> str:
        with self._uow_factory() as uow:
            item = ItemCatalogo(RecursoId.generar(), cmd.descripcion, Dinero.de(cmd.precio_mxn), cmd.capacidad,
                                cmd.habilitado)
            uow.catalogo.guardar(item)
            uow.commit()
        return str(item.id)


class ConsultarCatalogo(CasoDeUso):
    def ejecutar(self) -> list[ItemCatalogoDTO]:
        with self._uow_factory() as uow:
            return [_item_dto(i) for i in uow.catalogo.listar()]
