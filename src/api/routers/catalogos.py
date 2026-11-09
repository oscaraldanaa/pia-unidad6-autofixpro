from __future__ import annotations

from fastapi import APIRouter, Depends

from ...application.dto import (
    CambiarEstadoClienteCmd, ItemCatalogoDTO, OrdenResumenDTO, RegistrarClienteCmd, RegistrarCuentaFlotillaCmd,
    RegistrarItemCatalogoCmd, RegistrarTecnicoCmd, RegistrarVehiculoCmd,
)
from ...infrastructure.bootstrap import Contenedor
from ..dependencias import get_contenedor
from ..errores import ErrorOut
from ..esquemas import ClienteIn, EstadoClienteIn, FlotillaIn, IdOut, ItemCatalogoIn, TecnicoIn, VehiculoIn
from ..seguridad import Rol, requiere_rol

router = APIRouter(prefix="/api/v1", tags=["Catálogos"])
_ERR = {401: {"model": ErrorOut}, 403: {"model": ErrorOut}, 404: {"model": ErrorOut}, 409: {"model": ErrorOut}}
_asesor = Depends(requiere_rol(Rol.ASESOR))


@router.post("/clientes", response_model=IdOut, status_code=201, responses=_ERR, dependencies=[_asesor],
             summary="Registrar cliente", description="Requiere un medio digital de contacto: teléfono o correo (RN-10).")
def registrar_cliente(body: ClienteIn, c: Contenedor = Depends(get_contenedor)):
    return IdOut(id=c.registrar_cliente.ejecutar(RegistrarClienteCmd(**body.model_dump())))


@router.patch("/clientes/{cliente_id}/estado", status_code=204, responses=_ERR, dependencies=[_asesor],
              summary="Dar de alta o baja a un cliente",
              description="Un cliente inactivo no puede abrir órdenes ni recibir asignación de trabajos (precondición `cliente_activo`).")
def estado_cliente(cliente_id: str, body: EstadoClienteIn, c: Contenedor = Depends(get_contenedor)):
    c.cambiar_estado_cliente.ejecutar(CambiarEstadoClienteCmd(cliente_id, body.activo))


@router.post("/catalogo", response_model=IdOut, status_code=201, responses=_ERR, dependencies=[_asesor],
             summary="Registrar recurso del catálogo")
def registrar_recurso(body: ItemCatalogoIn, c: Contenedor = Depends(get_contenedor)):
    return IdOut(id=c.registrar_item_catalogo.ejecutar(RegistrarItemCatalogoCmd(**body.model_dump())))


@router.get("/catalogo", response_model=list[ItemCatalogoDTO], summary="Consultar catálogo de recursos")
def consultar_catalogo(c: Contenedor = Depends(get_contenedor)):
    return c.consultar_catalogo.ejecutar()


@router.post("/vehiculos", response_model=IdOut, status_code=201, responses=_ERR, dependencies=[_asesor],
             summary="Registrar vehículo")
def registrar_vehiculo(body: VehiculoIn, c: Contenedor = Depends(get_contenedor)):
    return IdOut(id=c.registrar_vehiculo.ejecutar(RegistrarVehiculoCmd(**body.model_dump())))


@router.get("/vehiculos/{vehiculo_id}/historial", response_model=list[OrdenResumenDTO], responses=_ERR,
            summary="Historial de órdenes del vehículo")
def historial_vehiculo(vehiculo_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.consultar_historial_vehiculo.ejecutar(vehiculo_id)


@router.post("/tecnicos", response_model=IdOut, status_code=201, responses=_ERR, dependencies=[_asesor],
             summary="Registrar técnico")
def registrar_tecnico(body: TecnicoIn, c: Contenedor = Depends(get_contenedor)):
    return IdOut(id=c.registrar_tecnico.ejecutar(RegistrarTecnicoCmd(**body.model_dump())))


@router.post("/flotillas", response_model=IdOut, status_code=201, responses=_ERR, dependencies=[_asesor],
             summary="Registrar cuenta de flotilla (Panel B2B)",
             description="RN-09 / RN-14: asocia un autorizador corporativo y condiciones comerciales.")
def registrar_flotilla(body: FlotillaIn, c: Contenedor = Depends(get_contenedor)):
    return IdOut(id=c.registrar_cuenta_flotilla.ejecutar(RegistrarCuentaFlotillaCmd(**body.model_dump())))
