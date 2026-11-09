# ADR-001: Domain-Driven Design y Clean Architecture como base del sistema AutoFix Pro

| Campo | Valor |
|---|---|
| **Estado** | Aceptada |
| **Fecha** | 2026-11-05 |
| **Equipo** | Equipo 6 — Componentes de Lógica de Negocio (FIME-UANL) |
| **Contexto del curso** | Producto Integrador de Aprendizaje (PIA) |
| **Artefactos de origen** | BRD, User Stories/Gherkin, BPMN, Glosario, Diagrama DDD, Modelo de Dominio |

## 1. Contexto

AutoFix Pro es un taller automotriz cuyo problema central (BRD §2) es la **falta de evidencia
auditable de las autorizaciones del cliente**, la baja visibilidad del estado de la reparación y la
mala comunicación de retrasos. El valor del sistema no está en operaciones CRUD, sino en **hacer
cumplir reglas de negocio** (RN-01 a RN-14) sobre un ciclo de vida con muchos estados:

`Recibido → Diagnosticado → Cotizado → Autorizado → En reparación ⇄ En espera de refacción → Listo para entrega → Cerrado`
(más `Cancelado` cuando el cliente rechaza toda la cotización, según el BPMN).

Características del dominio que condicionan la arquitectura:

- **Reglas densas y cruzadas**: un técnico no puede ejecutar nada no autorizado (RN-13); toda falla
  adicional exige cotización complementaria autorizada (RN-04); solo se cobra lo autorizado (RF-15).
- **Ciclo de vida con transiciones restringidas** y varios actores (5 roles, RN-12).
- **Efectos secundarios desacoplables**: notificar retrasos (RN-03), encolar solicitudes a Compras
  (RN-07), registrar auditoría (RNF-01).
- **Lenguaje de negocio ya definido** en el glosario (Orden de Servicio, Concepto autorizado,
  Solicitud de ampliación, Autorizador corporativo…).
- **Requisitos del PIA**: DDD, Specification, State Machine, API REST documentada, cobertura ≥ 80 %,
  estructura `domain / application / infrastructure / api`, trazabilidad análisis → código → pruebas.

## 2. Decisión

### 2.1 Domain-Driven Design (táctico) como modelo del núcleo

Se modela el dominio con los bloques tácticos de DDD, reutilizando el lenguaje del glosario
(*ubiquitous language*) para nombrar clases y métodos:

| Bloque DDD | Aplicación en AutoFix Pro |
|---|---|
| **Aggregate Root** | `OrdenServicio`: única puerta de entrada para modificar cotizaciones, trabajos, solicitudes de refacción/ampliación y fechas. Garantiza las invariantes en una sola transacción. |
| **Entidades** (identidad por ID) | `Cliente`, `Vehiculo`, `Tecnico`, `CuentaFlotilla` (agregados propios); dentro de `OrdenServicio`: `Cotizacion`, `ConceptoCotizacion`, `TrabajoReparacion`, `SolicitudRefaccion`, `SolicitudAmpliacion`. |
| **Value Objects** (inmutables, por valor) | `Dinero` (`Decimal`, 2 decimales, moneda), `Porcentaje`, identificadores tipados (`OrdenServicioId`, …), `Kilometraje`, `NivelCombustible`, `DatosRecepcion`, `DatosContacto`, `Placas`, `Vin`, `FechaEntrega`, `CambioFechaEntrega`, `EvidenciaAutorizacion`, `CondicionesFlotilla`. |
| **Domain Events** | `OrdenRecibida`, `DiagnosticoRegistrado`, `CotizacionParcialmenteAutorizada`, `RefaccionSinExistencia`, `RetrasoPorRefaccion`, `FallaAdicionalDetectada`, `FechaModificada`, `OrdenCerrada`, etc. Los emite el agregado; la capa de aplicación los despacha. |
| **Domain Services** *(Fase 2)* | `ValidadorFlotilla`, `CalcularCotizacion` (del diagrama DDD) para lógica que no pertenece a una sola entidad. |
| **Repositories** *(puertos en Fase 2)* | Uno por agregado (`OrdenServicioRepository`, `ClienteRepository`, `VehiculoRepository`, `TecnicoRepository`), definidos como interfaces en `application`. |

Reglas de diseño adoptadas:

1. **Referencia entre agregados solo por ID** (`OrdenServicio` guarda `ClienteId`, `VehiculoId`, `TecnicoId`).
2. **Dinero siempre con `Decimal`**, nunca `float`; el constructor rechaza `float` y montos negativos.
3. **Invariantes en el constructor** de cada Value Object (p. ej. `EvidenciaAutorizacion` exige sello de
   tiempo con zona horaria e IP o token — RN-11; `DatosContacto` exige un medio digital — RN-10).
4. **Estado privado**: el agregado expone propiedades de solo lectura y métodos con nombre de negocio
   (`registrar_diagnostico`, `responder_cotizacion`, `registrar_falla_adicional`…), no setters.

### 2.2 Clean Architecture (regla de dependencia hacia adentro)

```
 api  ─────────►  application  ─────────►  domain
   │                   ▲                      ▲
   └──► infrastructure ┴──────────────────────┘   (implementa puertos definidos en application/domain)
```

| Capa (carpeta) | Responsabilidad | Puede depender de |
|---|---|---|
| `src/domain/` | Entidades, VO, agregados, eventos, servicios y especificaciones de dominio. Python estándar puro. | Nada (solo stdlib) |
| `src/application/` | Casos de uso (commands/queries), DTOs, **puertos** (interfaces de repositorio, `UnitOfWork`, notificador), despacho de eventos. | `domain` |
| `src/infrastructure/` | Adaptadores: repositorios SQL, `SqlUnitOfWork`, notificaciones SMS/correo, configuración por variables de entorno. | `application`, `domain` |
| `src/api/` | Controllers REST, esquemas de request/response, OpenAPI/Swagger, inyección de dependencias. | `application` |

Esto corresponde 1:1 con las tres capas del *Diagrama DDD Integral* (Dominio · Aplicación · Infraestructura),
añadiendo `api` como capa de entrega según la estructura mínima exigida por el PIA.
**El dominio no importa FastAPI, SQLAlchemy ni ningún framework**; se verificará con una prueba
automatizada de arquitectura en la Fase de calidad.

### 2.3 Patrones seleccionados y su justificación

| Patrón | Problema que resuelve | Dónde se aplica |
|---|---|---|
| **Aggregate + Repository** | Consistencia transaccional y persistencia sin acoplar el dominio. | `OrdenServicio` y su `OrdenServicioRepository`. |
| **State Machine** *(Fase 2)* | Transiciones válidas entre estados (RN-01, RN-13; BPMN). Evita `if` dispersos. | Ciclo de vida de `OrdenServicio` y `TrabajoReparacion`. En Fase 1 las precondiciones son guardas (`_requerir_estado`) que se sustituirán sin cambiar la API del agregado. |
| **Specification** *(Fase 2)* | Reglas de negocio componibles y reutilizables (and/or/not). | `OrdenListaParaEntregaSpec`, `ConceptoEjecutableSpec`, `OrdenEsDeFlotillaSpec`, elegibilidad de cobro. |
| **Domain Events + Observer** | Desacoplar efectos secundarios (notificaciones, cola de Compras, auditoría). | Eventos emitidos por el agregado, manejadores en `application`. |
| **Unit of Work** | Una transacción por caso de uso. | `UnitOfWork` (puerto) / `SqlUnitOfWork` (adaptador). |
| **CQRS ligero** | Separar escritura (commands con reglas) de lectura (consulta de estado, reportes RF-16). | `RegistrarIngresoOrden…Command`, `ConsultarEstadoOrdenHandler`. |
| **Factory Method** | Creación válida desde el nacimiento. | `OrdenServicio.registrar_ingreso(...)` aplica RN-01, RN-09 y RN-14. |
| **Ports & Adapters** | Sustituir infraestructura (DB, SMS) por dobles en pruebas. | Interfaces en `application`, implementaciones en `infrastructure`. |

### 2.4 SOLID (cómo se manifiesta)

- **S** — Cada clase tiene una razón de cambio: `Dinero` (aritmética monetaria), `EvidenciaAutorizacion` (validez de autorización), `Cotizacion` (cálculo y decisión por concepto), `OrdenServicio` (orquestar invariantes del ciclo de vida).
- **O** — Nuevas reglas se agregan como Specifications y nuevos eventos/manejadores sin modificar el agregado ni los casos de uso existentes.
- **L** — Los identificadores tipados y las clases base `Entity`/`ValueObject` son sustituibles sin romper contratos.
- **I** — Puertos pequeños y específicos (un repositorio por agregado, notificador separado del repositorio).
- **D** — `application` depende de abstracciones (puertos); `infrastructure` las implementa y se inyecta desde `api`.

### 2.5 Ajustes respecto al Diagrama DDD y al Modelo de Dominio previos

Al pasar a código se refinaron tres puntos (decisión consciente, no omisión):

1. **`Cotizacion` pasa de Value Object a Entidad interna del agregado.** RN-05/RF-04 exigen autorizar o
   rechazar *cada concepto* con su propia evidencia (RN-11) y existen cotizaciones complementarias
   (RN-04). Un VO inmutable no puede registrar esas decisiones a lo largo del tiempo.
   Sus totales (subtotal, descuento, impuestos, total) siguen siendo Value Objects (`DesgloseMonetario`).
2. **`Tecnico.registrarFallaAdicional()` se mueve a `OrdenServicio.registrar_falla_adicional(tecnico_id, …)`.**
   Registrar la falla modifica la orden; `Tecnico` es otro agregado y no debe mutar la orden (regla 1 de §2.1).
3. **Se nombra `OrdenServicio`** (término del glosario y del diagrama) para la Orden de Trabajo/Reparación,
   y se añade `CuentaFlotilla` (RN-09, RN-14) y el estado `Cancelado` (BPMN: rechazo total).

## 3. Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| **MVC / CRUD con modelo anémico** (lógica en servicios o controladores) | Las reglas RN-04, RN-05, RN-13 quedarían dispersas y duplicadas; difícil probar y trazar contra el BRD. Riesgo alto de ejecutar trabajo no autorizado, justo el problema de negocio. |
| **Arquitectura en capas tradicional** (UI → Servicio → DAO) | El dominio dependería de la base de datos/ORM; las pruebas unitarias requerirían infraestructura y no se alcanzaría fácilmente el 80 % de cobertura aislada. |
| **Microservicios** | El alcance (un taller, cinco roles, un proceso) no justifica la complejidad operativa; se opta por un **monolito modular** cuyos límites (agregados, puertos) permiten extraer servicios después. |
| **Event Sourcing completo** | Aporta auditoría natural, pero añade complejidad de proyecciones y curva de aprendizaje desproporcionada para el plazo (entrega 6-nov-2026). La auditoría (RNF-01) se cubre con `EvidenciaAutorizacion`, historial de fechas y eventos de dominio persistidos. |
| **Cotización como Value Object** (diagrama original) | Ver §2.5: no permite decisión por concepto con evidencia independiente. |

## 4. Consecuencias

**Positivas**

- Trazabilidad directa BRD → dominio → pruebas (tabla §5); cada RN tiene un lugar único en el código.
- Dominio 100 % testeable sin base de datos ni red (cobertura ≥ 80 % alcanzable con pruebas unitarias rápidas).
- Cambios de infraestructura (DB, canal de notificación) no tocan las reglas.
- El lenguaje del glosario aparece en el código, facilitando la defensa técnica.

**Negativas / costos**

- Más clases y capas que un CRUD; requiere disciplina para no filtrar dependencias hacia `domain`.
- El agregado `OrdenServicio` es grande; hay que vigilar su rendimiento al persistir/cargar (carga completa por orden) y su cohesión.
- Mapeo dominio ↔ persistencia (ORM) añade código de adaptación en `infrastructure`.
- En Fase 1 las transiciones son guardas; hasta implementar la State Machine existe riesgo de duplicar condiciones.

**Decisiones derivadas (ADRs pendientes)**

- ADR-002: State Machine para el ciclo de vida de la orden.
- ADR-003: Specification para reglas compuestas.
- ADR-004: Framework y persistencia (API REST/OpenAPI, base de datos, ORM).
- ADR-005: Despliegue, Docker Compose y configuración 12-Factor.

## 5. Trazabilidad inicial (Fase 1)

| Regla (BRD) | Requisito / US | Elemento de dominio |
|---|---|---|
| RN-01 | RF-01 · US-01 | `DatosRecepcion`, `Kilometraje`, `OrdenServicio.registrar_ingreso()` |
| RN-02 | RF-12 · US-12 | `OrdenServicio.estado` + `EstadoOrden` (consulta en Fase 2, `ConsultarEstadoOrdenHandler`) |
| RN-03 | RF-07 · US-07 | `OrdenServicio.actualizar_reposicion()` → evento `RetrasoPorRefaccion` |
| RN-04 | RF-08/09/10 · US-08/09/10 | `SolicitudAmpliacion`, `registrar_falla_adicional()`, `enviar_cotizacion_complementaria()`, `responder_ampliacion()` |
| RN-05 | RF-03/04 · US-03/04 | `Cotizacion`, `ConceptoCotizacion`, `Cotizacion.responder()` (autorización total/parcial) |
| RN-06 | RF-11 · US-11 | `FechaEntrega`, `CambioFechaEntrega`, `OrdenServicio.modificar_fecha_entrega()` |
| RN-07 | RF-06 · US-06 | `SolicitudRefaccion`, `reportar_refaccion_sin_existencia()` → evento `RefaccionSinExistencia` |
| RN-08 | RF-16 · US-16 | Fase 2/3: query handlers de reportes (`application`) |
| RN-09 | RF-17 · US-17 | `CuentaFlotilla`, `CondicionesFlotilla`, `OrdenServicio.registrar_ingreso()` |
| RN-10 | RF-04 | `DatosContacto` (medio digital), `CanalAutorizacion` |
| RN-11 | RF-18 | `EvidenciaAutorizacion` (sello de tiempo + IP/token) |
| RN-12 | RNF-03 | Control de roles en `application`/`api` (Fase 2/3); `Tecnico.asignar()` |
| RN-13 | RF-05/10 | `OrdenServicio._crear_trabajos()`: un `TrabajoReparacion` solo nace de un concepto autorizado |
| RN-14 | — | `OrdenServicio.autorizador_id` (cliente o autorizador corporativo) |

## 6. Referencias

- BRD AutoFix Pro (8-sep-2026), User Stories, BPMN avanzado, Glosario, Diagrama DDD y Modelo de Dominio.
- Evans, E. *Domain-Driven Design*. Vernon, V. *Implementing Domain-Driven Design*.
- Martin, R. C. *Clean Architecture*.
