from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ...application.dto import (
    ActualizarReposicionCmd, AsignarTrabajosCmd, CancelarOrdenCmd, ConceptoNuevoDTO, DefinirFechaEntregaCmd,
    EnviarCotizacionComplementariaCmd, EvaluacionOperacionDTO, GenerarCotizacionCmd, OrdenCmd, OrdenDetalleDTO, RegistrarCobroCmd,
    RegistrarDiagnosticoCmd, RegistrarFallaAdicionalCmd, RegistrarIngresoCmd, ReportarRefaccionSinExistenciaCmd,
    ResponderAmpliacionCmd, ResponderCotizacionCmd, SolicitudRefaccionCmd, TrabajoCmd,
)
from ...infrastructure.bootstrap import Contenedor
from ..dependencias import construir_evidencia, get_contenedor
from ..errores import ErrorOut
from ..esquemas import (
    AsignacionIn, CancelacionIn, CobroIn, CotizacionIn, DiagnosticoIn, FallaIn, FechaEntregaIn, IngresoIn,
    RefaccionFaltanteIn, ReposicionIn, RespuestaIn,
)
from ..seguridad import Rol, requiere_rol

router = APIRouter(prefix="/api/v1/ordenes", tags=["Órdenes de servicio"], responses={
    401: {"model": ErrorOut, "description": "Falta X-Rol"},
    403: {"model": ErrorOut, "description": "Rol sin permiso (RN-12)"},
    404: {"model": ErrorOut, "description": "Orden o entidad no encontrada"},
    409: {"model": ErrorOut, "description": "Regla de negocio o transición de estado inválida"},
})
Out = OrdenDetalleDTO


def _rol(*roles: Rol):
    return [Depends(requiere_rol(*roles))]


def _conceptos(body: CotizacionIn) -> tuple[ConceptoNuevoDTO, ...]:
    return tuple(ConceptoNuevoDTO(c.tipo, c.descripcion, c.precio_unitario, c.cantidad, c.recurso_id)
                 for c in body.conceptos)


@router.post("", response_model=Out, status_code=201, dependencies=_rol(Rol.ASESOR),
             summary="Registrar ingreso del vehículo y abrir la OT",
             description="**US-01 · RF-01 · RN-01.** Crea la orden en estado *Recibido*. Si el vehículo pertenece a una "
                         "flotilla se asocia la cuenta B2B y su autorizador corporativo (**RN-09, RN-14**).")
def registrar_ingreso(body: IngresoIn, c: Contenedor = Depends(get_contenedor)):
    return c.registrar_ingreso.ejecutar(RegistrarIngresoCmd(
        body.cliente_id, body.vehiculo_id, body.kilometraje, body.combustible, body.motivo_ingreso,
        tuple(body.danos_visibles), body.promocion_activa))


@router.get("/{orden_id}", response_model=Out, summary="Consultar estado de la orden",
            description="**US-12 · RF-12 · RN-02.** Consulta abierta (portal del cliente / administración).")
def consultar(orden_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.consultar_estado.ejecutar(orden_id)


@router.get("/{orden_id}/evaluacion", response_model=EvaluacionOperacionDTO, summary="Evaluar reglas compuestas de la operación",
            description="Specifications con AND/OR/NOT: `puede_procesarse` (cliente activo AND con detalle AND autorizada) y "
                        "`beneficio_referencia` (cliente preferente AND total ≥ 1500 AND NOT promoción). "
                        "Devuelve además el valor de cada criterio.")
def evaluacion(orden_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.evaluar_operacion.ejecutar(orden_id)


@router.post("/{orden_id}/diagnostico", response_model=Out, dependencies=_rol(Rol.TECNICO),
             summary="Registrar diagnóstico", description="**US-02 · RF-02.** Recibido → Diagnosticado.")
def diagnostico(orden_id: str, body: DiagnosticoIn, c: Contenedor = Depends(get_contenedor)):
    return c.registrar_diagnostico.ejecutar(RegistrarDiagnosticoCmd(orden_id, body.tecnico_id, tuple(body.hallazgos)))


@router.post("/{orden_id}/cotizacion", response_model=Out, status_code=201, dependencies=_rol(Rol.ASESOR),
             summary="Generar cotización", description="**US-03 · RF-03 · RN-05.** Diagnosticado → Cotizado.")
def cotizar(orden_id: str, body: CotizacionIn, c: Contenedor = Depends(get_contenedor)):
    return c.generar_cotizacion.ejecutar(GenerarCotizacionCmd(orden_id, _conceptos(body)))


@router.post("/{orden_id}/cotizacion/respuesta", response_model=Out, dependencies=_rol(Rol.CLIENTE),
             summary="Autorizar o rechazar la cotización (total o parcial)",
             description="**US-04 · RF-04 · RF-18 · RN-05 · RN-11.** Cada concepto se decide por separado. "
                         "Rechazo total cancela la orden. Se registra sello de tiempo e IP/token.")
def responder_cotizacion(orden_id: str, body: RespuestaIn, request: Request,
                         c: Contenedor = Depends(get_contenedor)):
    ev = construir_evidencia(request, body.canal, body.token_verificacion)
    return c.responder_cotizacion.ejecutar(ResponderCotizacionCmd(orden_id, body.decisiones, ev))


@router.post("/{orden_id}/trabajos", response_model=Out, dependencies=_rol(Rol.ASESOR),
             summary="Asignar trabajos autorizados al técnico",
             description="**US-05 · RF-05 · RN-13.** Autorizado → En reparación. Exige técnico disponible.")
def asignar(orden_id: str, body: AsignacionIn, c: Contenedor = Depends(get_contenedor)):
    return c.asignar_trabajos.ejecutar(AsignarTrabajosCmd(orden_id, body.tecnico_id))


@router.post("/{orden_id}/refacciones-faltantes", response_model=Out, status_code=201,
             dependencies=_rol(Rol.TECNICO, Rol.ASESOR),
             summary="Reportar refacción sin existencia",
             description="**US-06 · RF-06 · RN-07.** Genera la solicitud a Compras. En reparación → En espera de refacción.")
def refaccion_faltante(orden_id: str, body: RefaccionFaltanteIn, c: Contenedor = Depends(get_contenedor)):
    return c.reportar_refaccion.ejecutar(
        ReportarRefaccionSinExistenciaCmd(orden_id, body.concepto_id, body.reposicion_estimada))


@router.patch("/{orden_id}/refacciones-faltantes/{solicitud_id}/reposicion", response_model=Out,
              dependencies=_rol(Rol.COMPRAS, Rol.ASESOR),
              summary="Actualizar tiempo de reposición (notifica al cliente)",
              description="**US-07 · RF-07 · RN-03.** Emite la notificación de retraso con motivo y nueva fecha.")
def reposicion(orden_id: str, solicitud_id: str, body: ReposicionIn, c: Contenedor = Depends(get_contenedor)):
    return c.actualizar_reposicion.ejecutar(
        ActualizarReposicionCmd(orden_id, solicitud_id, body.nueva_fecha, body.motivo))


@router.post("/{orden_id}/refacciones-faltantes/{solicitud_id}/recepcion", response_model=Out,
             dependencies=_rol(Rol.COMPRAS), summary="Registrar recepción de la refacción",
             description="Si no quedan solicitudes pendientes: En espera de refacción → En reparación.")
def recepcion(orden_id: str, solicitud_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.recibir_refaccion.ejecutar(SolicitudRefaccionCmd(orden_id, solicitud_id))


@router.post("/{orden_id}/fallas-adicionales", response_model=Out, status_code=201, dependencies=_rol(Rol.TECNICO),
             summary="Registrar falla adicional", description="**US-08 · RF-08 · RN-04.** Crea la solicitud de ampliación.")
def falla(orden_id: str, body: FallaIn, c: Contenedor = Depends(get_contenedor)):
    return c.registrar_falla_adicional.ejecutar(RegistrarFallaAdicionalCmd(orden_id, body.tecnico_id, body.descripcion))


@router.post("/{orden_id}/fallas-adicionales/{solicitud_id}/cotizacion", response_model=Out, status_code=201,
             dependencies=_rol(Rol.ASESOR), summary="Enviar cotización complementaria",
             description="**US-09 · RF-09 · RN-04/RN-05.**")
def cotizacion_complementaria(orden_id: str, solicitud_id: str, body: CotizacionIn,
                              c: Contenedor = Depends(get_contenedor)):
    return c.enviar_cotizacion_complementaria.ejecutar(
        EnviarCotizacionComplementariaCmd(orden_id, solicitud_id, _conceptos(body)))


@router.post("/{orden_id}/fallas-adicionales/{solicitud_id}/respuesta", response_model=Out,
             dependencies=_rol(Rol.CLIENTE), summary="Autorizar o rechazar la ampliación",
             description="**US-10 · RF-10 · RN-13.** Solo lo autorizado habilita trabajo al técnico.")
def respuesta_ampliacion(orden_id: str, solicitud_id: str, body: RespuestaIn, request: Request,
                         c: Contenedor = Depends(get_contenedor)):
    ev = construir_evidencia(request, body.canal, body.token_verificacion)
    return c.responder_ampliacion.ejecutar(ResponderAmpliacionCmd(orden_id, solicitud_id, body.decisiones, ev))


@router.put("/{orden_id}/fecha-entrega", response_model=Out, dependencies=_rol(Rol.ASESOR),
            summary="Programar o modificar la fecha estimada de entrega",
            description="**US-11 · RF-11 · RN-06.** La primera vez programa; después exige justificación, "
                        "conserva el historial y notifica al cliente.")
def fecha_entrega(orden_id: str, body: FechaEntregaIn, c: Contenedor = Depends(get_contenedor)):
    return c.definir_fecha_entrega.ejecutar(DefinirFechaEntregaCmd(orden_id, body.fecha_estimada, body.justificacion))


@router.post("/{orden_id}/trabajos/{trabajo_id}/finalizacion", response_model=Out, dependencies=_rol(Rol.TECNICO),
             summary="Finalizar trabajo (pasa a revisión de calidad)", description="**US-13 · RF-13.**")
def finalizar(orden_id: str, trabajo_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.finalizar_trabajo.ejecutar(TrabajoCmd(orden_id, trabajo_id))


@router.post("/{orden_id}/trabajos/{trabajo_id}/revision", response_model=Out, dependencies=_rol(Rol.ASESOR),
             summary="Aprobar revisión de calidad")
def revision(orden_id: str, trabajo_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.aprobar_revision_calidad.ejecutar(TrabajoCmd(orden_id, trabajo_id))


@router.post("/{orden_id}/listo-para-entrega", response_model=Out, dependencies=_rol(Rol.ASESOR),
             summary="Marcar la orden como lista para entrega",
             description="**US-14 · RF-14.** Guarda de la State Machine: `OrdenListaParaEntregaSpec`.")
def listo(orden_id: str, c: Contenedor = Depends(get_contenedor)):
    return c.marcar_lista_para_entrega.ejecutar(OrdenCmd(orden_id))


@router.post("/{orden_id}/cobro", response_model=Out, dependencies=_rol(Rol.CAJA),
             summary="Registrar cobro y cerrar la orden",
             description="**US-15 · RF-15.** El monto debe igualar el total autorizado. Listo para entrega → Cerrado.")
def cobro(orden_id: str, body: CobroIn, c: Contenedor = Depends(get_contenedor)):
    return c.registrar_cobro.ejecutar(RegistrarCobroCmd(orden_id, body.monto))


@router.post("/{orden_id}/cancelacion", response_model=Out, dependencies=_rol(Rol.ASESOR),
             summary="Cancelar la orden", description="Solo antes de iniciar la reparación.")
def cancelar(orden_id: str, body: CancelacionIn, c: Contenedor = Depends(get_contenedor)):
    return c.cancelar_orden.ejecutar(CancelarOrdenCmd(orden_id, body.motivo))
