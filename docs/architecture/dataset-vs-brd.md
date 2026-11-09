# Adaptación del paquete de datos del PIA (`data/pia`) al análisis propio del equipo

El paquete (`INSTRUCCIONES_ALUMNO.txt`) es un **modelo de pruebas propuesto**: indica que, si difiere del
BRD/BPMN/DDD del equipo, hay que *documentar las diferencias y adaptar fixtures y oráculos, sin reemplazar los
requerimientos propios*. Este documento registra esas diferencias y las decisiones tomadas.
Ejecución y evidencia: `python scripts/ejecutar_dataset.py` → `docs/evidencia/` · pruebas: `tests/integration/test_dataset_pia.py`.

## 1. Mapeo de conceptos

| Paquete de datos | AutoFix Pro (BRD/DDD) | ¿Qué se hizo? |
|---|---|---|
| `actor` (propietario) | `Cliente` | `actor_id` → cliente interno (el mapeo lo lleva el ejecutor). |
| `actor.activo` | `Cliente.activo` | **Extensión** (el BRD no define baja de clientes). |
| `actor.es_preferente` | `Cliente.es_preferente` | **Extensión** para la regla `beneficio_referencia`. |
| `actor.ciudad` | — | No mapeado (sin uso en reglas del BRD). |
| `recurso` (catálogo) | `ItemCatalogo` | **Extensión** apoyada en BRD §12 «inventario»: precio oficial, capacidad/stock, habilitado. |
| `operacion` | `OrdenServicio` (OT) | `estado_inicial=RECIBIDA` ↔ *Recibido*. `referencia` → `motivo_ingreso`. |
| `operacion.promocion_activa` | `OrdenServicio.promocion_activa` | **Extensión** (el BRD no habla de promociones). |
| `operacion.autorizado` | Cotización autorizada por el cliente (RN-05) | Derivado: `1` → el cliente autoriza todos los conceptos; `0` → no se registra respuesta. |
| `operacion.fecha_solicitud` | — | No mapeada: la OT toma la fecha real de registro; la API no admite fechas retroactivas. |
| `detalle_operaciones` | `ConceptoCotizacion` (`mano_de_obra`, con `recurso_id`) | `cantidad × precio_mxn` con `Decimal`. |

**Datos que el paquete no trae y el ejecutor genera:** un vehículo por orden (placas `PIA-E001`/`PIA-S001`), teléfono sintético por cliente (RN-10 exige medio digital) y un técnico único.

## 2. Flujo de estados

| Flujo de referencia | AutoFix Pro | Nota |
|---|---|---|
| RECIBIDA | Recibido | |
| DIAGNOSTICADA | Diagnosticado | |
| — | **Cotizado**, **Autorizado** | Estados del BRD §12; el flujo de referencia los omite. |
| EN_REPARACION | En reparación | |
| — | En espera de refacción, Listo para entrega | Estados del BRD (RN-07, US-14). |
| ENTREGADA | Cerrado | tras revisión de calidad, listo para entrega y cobro (RF-15). |
| CANCELADA | Cancelado | por cancelación voluntaria o rechazo total de la cotización. |

Al reportar resultados los estados exclusivos de AutoFix Pro se marcan con `*` (p. ej. `COTIZADA*`).

## 3. Diferencias y decisiones

| # | Diferencia | Decisión |
|---|---|---|
| D1 | El paquete define `total = Σ precio × cantidad` (sin impuestos); nuestras cotizaciones suman IVA 16 % y descuento de flotilla. | La regla usa `OrdenServicio.total_referencia` (= subtotal bruto, sin IVA ni descuento). El total con IVA sigue siendo el de RN-05. |
| D2 | «Autorización» es un booleano en el paquete; en el BRD se autoriza **por concepto** con evidencia (RN-05, RN-11). | `OrdenAutorizadaSpec`: autorizada o parcialmente autorizada. El ejecutor autoriza todos los conceptos cuando `autorizado=1`. |
| D3 | Las operaciones con actor **inactivo** existen en el paquete (9). Nuestro ingreso bloquea clientes inactivos (RN-01 + `ClienteActivoSpec`). | El ejecutor abre las órdenes con el cliente activo y **después** lo da de baja (`PATCH /clientes/{id}/estado`), como ocurriría en la realidad. Además, `AsignarTrabajos` exige cliente activo (**EXT-01**, precondición `cliente_activo`). |
| D4 | «Disponibilidad/capacidad»: el paquete rechaza cantidades sobre `capacidad_o_stock`; el BRD (RN-07) **no rechaza** una refacción sin existencia: genera solicitud a Compras. | Recursos de catálogo (servicios con capacidad) → rechazo `409 CAT-02`; recurso deshabilitado → `409 CAT-01`. Las refacciones sin existencia siguen el flujo RN-07 (no se rechazan). Ninguna línea del paquete excede la capacidad: CAT-02 se prueba con datos propios. |
| D5 | Dos operaciones (`AUT-O013`, `AUT-O039`) no tienen detalle. | Nuestra cotización exige ≥ 1 concepto: no pueden cotizarse (`422`). `puede_procesarse` = FALSO. |
| D6 | Seis operaciones usan el recurso deshabilitado `AUT-P011`. | Se pueden evaluar las reglas (se cotizan con precio libre), pero `completar` falla al cotizar con catálogo (`409 CAT-01`). |
| D7 | Las acciones sugeridas (`aprobar`, `completar`, …) no están definidas en el paquete; la solución es del docente. | Interpretación propia (sección 4); el oráculo es nuestro y está en `tests/dataset/oraculo.py`, independiente del dominio. **Debe contrastarse con la solución oficial.** |
| D8 | Códigos HTTP: el paquete pide 200/201, 400/409/422 y 404 «según el contrato del equipo». | 200/201 éxito · 404 no existe · 409 regla de negocio o transición inválida · 422 dato inválido · 400 error de dominio genérico · 401/403 rol (RN-12). |

## 4. Interpretación de `transiciones_prueba.csv`

| Acción | Qué ejecuta el sistema | Resultado esperado |
|---|---|---|
| `aprobar` | Diagnóstico (primer paso válido desde RECIBIDA) | Éxito → DIAGNOSTICADA, evento `EstadoOrdenCambiado` |
| `repetir_aprobacion` | Dos diagnósticos seguidos | 2.º rechazado: `409 TransicionInvalida`; queda DIAGNOSTICADA |
| `saltar_estado` | Cobro/entrega sin pasar por los estados previos | `409`; sigue RECIBIDA |
| `cancelar` | Cancelación desde RECIBIDA | Éxito → CANCELADA, evento `OrdenCancelada` |
| `completar` | Ciclo completo: diagnóstico → cotización (catálogo) → autorización → asignación → calidad → listo → cobro | ENTREGADA; o bloqueo documentado: sin detalle (`422`, cotizar), recurso deshabilitado (`409`, cotizar), sin autorización (`409`, asignar), cliente inactivo (`409` EXT-01, asignar) |

## 5. Códigos de regla añadidos (extensiones, no provienen del BRD)

| Código | Significado | Dónde |
|---|---|---|
| `EXT-01` | Cliente inactivo: no se asignan trabajos | `AsignarTrabajos` + `ClienteActivoSpec` |
| `CAT-01` | Recurso del catálogo deshabilitado | `ItemCatalogo.validar_cantidad` |
| `CAT-02` | Cantidad mayor que la capacidad/stock | `ItemCatalogo.validar_cantidad` |

## 6. Hallazgos de calidad de datos

Se detectan automáticamente (`Dataset.integridad()`, resumen en `docs/evidencia/resumen.md`): 2 operaciones sin detalle,
9 con actor inactivo, 7 sin autorización, 6 con promoción, 6 con recurso deshabilitado, 0 sobre capacidad, 0 referencias huérfanas.
`fecha_solicitud` no es monótona respecto a `operacion_id` (a partir de `AUT-O024` las fechas vuelven a empezar en 2026-10-01).
