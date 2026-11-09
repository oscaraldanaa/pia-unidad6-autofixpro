# Matriz de trazabilidad BRD → regla → componente → prueba

Pruebas en `tests/` (`pytest`). «Dataset» = casos de `data/pia` que ejercitan la regla (evidencia en `docs/evidencia/`).

| BRD / US | Regla implementada | Componente | Prueba(s) | Dataset |
|---|---|---|---|---|
| RN-01 · RF-01 · US-01 | OT con datos completos y kilometraje que no disminuye | `DatosRecepcion`, `OrdenServicio.registrar_ingreso`, `Vehiculo.actualizar_kilometraje` | `test_value_objects::TestRecepcionYEvidencia::test_rn01_motivo_obligatorio`, `test_orden_servicio::TestIngreso::test_rn01_crea_orden_recibida_con_evento` | — |
| RN-02 · RF-12 · US-12 | Consulta del estado sin llamar al taller | `ConsultarEstadoOrden`, `GET /ordenes/{id}` | `test_api_flujo::test_ciclo_completo_hasta_cierre_con_notificaciones_y_auditoria` | transiciones (estado final) |
| RN-03 · RF-07 · US-07 | Aviso automático de retraso | evento `RetrasoPorRefaccion` → `NotificarRetrasoPorRefaccion` | `test_orden_servicio::TestRefaccionesYFallas::test_rn07_y_rn03_…`, `test_casos_de_uso::test_manejadores_notifican_al_autorizador` | — |
| RN-04 · RF-08/09/10 · US-08/09/10 | Falla adicional → cotización complementaria → autorización | `SolicitudAmpliacion`, `registrar_falla_adicional`, `responder_ampliacion` | `test_rn04_falla_adicional_cotizacion_y_autorizacion`, `test_ampliacion_rechazada_no_crea_trabajo` | — |
| RN-05 · RF-03/04 · US-03/04 | Autorización/rechazo total o parcial por concepto | `Cotizacion.responder`, `ResultadoCotizacion` | `TestCotizacionYAutorizacion::*` | `AUT-T*` (autorización) |
| RN-06 · RF-11 · US-11 | Cambio de fecha con justificación e historial | `CambioFechaEntrega`, `modificar_fecha_entrega` | `TestFechaEntrega::test_rn06_historial_y_justificacion` | — |
| RN-07 · RF-06 · US-06 | Refacción sin existencia → solicitud a Compras | `SolicitudRefaccion`, `reportar_refaccion_sin_existencia` | `test_rn07_solo_refacciones_autorizadas_y_sin_duplicar` | — |
| RN-08 · RF-16 · US-16 | Reportes e indicadores | **Pendiente** | — | — |
| RN-09 · RF-17 · US-17 | Flotilla reconocida desde el ingreso; descuento B2B | `CuentaFlotilla`, `CondicionesFlotilla` | `TestIngreso::test_rn09_*`, `test_flotilla_*` | — |
| RN-10 | Medio digital de contacto | `DatosContacto` | `test_rn10_requiere_medio_digital` | (contacto sintético) |
| RN-11 · RF-18 | Sello de tiempo + IP/token en cada autorización | `EvidenciaAutorizacion`, `construir_evidencia` | `test_rn11_evidencia`, `test_rn11_cada_concepto_guarda_evidencia` | — |
| RN-12 · RNF-03 | Solo los cinco roles; permisos por acción | `src/api/seguridad.py` | `test_api_flujo::test_roles_rn12`, `test_cliente_no_puede_cobrar_ni_caja_autorizar` | — |
| RN-13 · RF-05 | Solo se ejecuta lo autorizado | `OrdenServicio._construir_trabajos` | `test_rn13_*` | `completar` (AUT-S001/S016) |
| RN-14 | Un único responsable de autorizar | `OrdenServicio.autorizador_id` | `test_rn14_autorizador_es_el_cliente` | — |
| RF-14 · RF-15 · US-14/15 | Entrega solo con trabajos revisados; cobro = total autorizado | `OrdenListaParaEntregaSpec`, `registrar_cobro_y_cerrar` | `test_state_machine::test_guardas_con_specification`, `TestCierre` | `completar` → ENTREGADA |
| State Machine | Transiciones válidas/inválidas con evento o excepción | `ORDEN_STATE_MACHINE`, `TransicionInvalida`, `EstadoOrdenCambiado` | `test_state_machine.py` (7 pruebas) | 20 `AUT-S*` |
| Specification (AND/OR/NOT) | `puede_procesarse`, `beneficio_referencia` | `specifications/reglas_operacion.py`, `GET /ordenes/{id}/evaluacion` | `test_specifications.py`, `test_extensiones::TestReglasCompuestas`, `test_api_catalogo::test_endpoint_de_evaluacion_con_criterios` | 60 `AUT-T*` + 60 `AUT-B*` |
| Dataset · cantidades/capacidad/importes | Catálogo habilitado y con capacidad; importes con `Decimal` | `ItemCatalogo`, `Dinero` | `test_extensiones::TestItemCatalogo`, `test_api_catalogo::test_validaciones_de_cantidades_y_disponibilidad`, `test_dataset_pia::test_total_*` | `AUT-S` completar (P011) |
| Dataset · precondiciones | `cliente_activo` (EXT-01), `tecnico_disponible`, `refacciones_disponibles` | `ClienteActivoSpec`, `TecnicoDisponibleSpec`, `RefaccionesDisponiblesSpec` | `test_baja_de_cliente_bloquea_ingresos_y_asignaciones`, `test_tecnico_no_disponible_no_recibe_trabajos`, `test_guardas_con_specification` | `AUT-S001` |
| Clean Architecture | Dominio sin dependencias de framework | — | `unit/test_arquitectura.py` | — |
| Auditoría · RNF-01 | Eventos persistidos | `AuditoriaEventosSql` → `eventos_dominio` | `test_ciclo_completo_…` | columna `eventos_dominio` de la evidencia |
