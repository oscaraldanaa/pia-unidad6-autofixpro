# AutoFix Pro — Sistema de Gestión y Trazabilidad Operativa

**PIA — Componentes de Lógica de Negocio · FIME-UANL · Equipo 6**
Hugo Arturo Villarreal Ortiz (2142659) · Enrique Canales Belmares (2142832) · Oscar Alexis Aldana Almanza (2144189)

| | |
|---|---|
| Repositorio | `<URL-DEL-REPOSITORIO-GITHUB>` |
| Sistema desplegado | `<URL-DEL-DESPLIEGUE>` · Swagger UI en `<URL-DEL-DESPLIEGUE>/docs` |

AutoFix Pro es un taller automotriz. Su problema de negocio (BRD §2) es la **falta de evidencia auditable de las autorizaciones del cliente**, la poca visibilidad del avance y la mala comunicación de retrasos. Este sistema digitaliza el proceso completo — recepción → diagnóstico → cotización/autorización → reparación → entrega y cobro — y **hace cumplir por código** las reglas de negocio RN-01 a RN-14.

---

## 1. Contenido

1. [Arquitectura](#2-arquitectura) · 2. [Estructura del repositorio](#3-estructura-del-repositorio) · 3. [Requisitos](#4-requisitos) · 4. [Instalación y ejecución local](#5-instalación-y-ejecución-local) · 5. [Ejecución con Docker](#6-ejecución-con-docker-compose) · 6. [Pruebas](#7-pruebas-y-cobertura) · 7. [API REST](#8-api-rest) · 8. [Demo en vivo](#9-guía-para-la-demo-en-vivo) · 9. [Datos del PIA](#10-paquete-de-datos-del-pia-datapia) · 10. [Trazabilidad](#11-trazabilidad-análisis--código--pruebas) · 11. [CI/CD](#12-cicd) · 12. [Despliegue](#13-despliegue) · 13. [Solución de problemas](#14-solución-de-problemas)

---

## 2. Arquitectura

DDD táctico + Clean Architecture (detalle y alternativas en [`docs/architecture/ADR-001-DDD-y-Clean-Architecture.md`](docs/architecture/ADR-001-DDD-y-Clean-Architecture.md)). **La dependencia siempre apunta hacia adentro**; una prueba automatizada (`tests/unit/test_arquitectura.py`) la verifica.

```
 ┌──────────────────────────────────────────────────────────────┐
 │ api (FastAPI)  controllers REST, esquemas, roles, OpenAPI     │
 ├──────────────────────────────────────────────────────────────┤
 │ infrastructure  SQLAlchemy, repositorios, UnitOfWork, bus,    │──implementa──┐
 │                 notificador, config 12-Factor, bootstrap      │              │
 ├──────────────────────────────────────────────────────────────┤              ▼
 │ application     casos de uso, DTOs, PUERTOS (interfaces)      │◄─────── puertos
 ├──────────────────────────────────────────────────────────────┤
 │ domain          entidades, VO, agregado, Specification,       │  (Python puro)
 │                 State Machine, eventos                        │
 └──────────────────────────────────────────────────────────────┘
```

**Patrones aplicados:** Aggregate/Repository, **State Machine** (`src/domain/state_machine`), **Specification** (`src/domain/specifications`), Domain Events + Observer, Unit of Work, CQRS ligero, Factory Method, Ports & Adapters.
**SOLID:** SRP (un VO/entidad por responsabilidad), OCP (nuevas reglas = nuevas Specifications/handlers), DIP (casos de uso dependen de puertos, no de SQLAlchemy), ISP (puertos pequeños), LSP (jerarquías `Entity`/`ValueObject`).

### Ciclo de vida de la orden (State Machine)

```
Recibido → Diagnosticado → Cotizado → Autorizado → En reparación ⇄ En espera de refacción
                              │            │             │
                              ▼            ▼             ▼
                          Cancelado    Cancelado   Listo para entrega → Cerrado
```
Transición inválida ⇒ `TransicionInvalida` (HTTP 409). Cada transición válida emite `EstadoOrdenCambiado`.
Equivalencia con el enunciado: RECIBIDA=Recibido · DIAGNOSTICADA=Diagnosticado · EN_REPARACION · ENTREGADA=Cerrado · CANCELADA=Cancelado.

---

## 3. Estructura del repositorio

```
mi-proyecto-cln/
├── docs/
│   ├── BRD.md                    ← (agregar el BRD final del equipo)
│   ├── architecture/             ADR-001, dataset-vs-brd.md y diagramas (DDD, BPMN, UML)
│   ├── trazabilidad.md           matriz BRD → regla → componente → prueba
│   ├── evidencia/                resultados de los 120 casos y 20 transiciones del paquete
│   └── api/openapi.json          especificación OpenAPI generada
├── src/
│   ├── domain/                   entities · value_objects · events · specifications · state_machine · shared
│   ├── application/              use_cases · ports · dto · handlers
│   ├── infrastructure/           persistence (modelos, mappers, repositorios, UoW) · config · messaging · bootstrap
│   └── api/                      main · routers · esquemas · seguridad · errores
├── tests/                        unit/ (domain, application, arquitectura) · integration/ (repositorios, API)
├── data/pia/                     paquete de datos del PIA (CSV) + INSTRUCCIONES_ALUMNO.txt
├── scripts/                      demo_flujo.py · exportar_openapi.py · ejecutar_dataset.py
├── docker/mysql-init/            crea la BD de pruebas
├── .github/workflows/ci.yml      CI/CD
├── Dockerfile · docker-compose.yml · .env.example · requirements*.txt · pyproject.toml
└── README.md
```

---

## 4. Requisitos

- Python **3.12+** (ejecución local) · Docker + Docker Compose v2 (ejecución en contenedores) · Git.

## 5. Instalación y ejecución local

```bash
git clone <URL-DEL-REPOSITORIO-GITHUB> && cd mi-proyecto-cln
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # Windows: copy .env.example .env
python -m uvicorn src.api.main:app --reload            # o: python -m src.api
```
Por defecto usa **SQLite** (`autofixpro.db`) y crea las tablas al arrancar. Abre <http://localhost:8000/docs>.

### Variables de entorno (12-Factor, factor III)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | URL de SQLAlchemy (SQLite o MySQL) | `sqlite:///./autofixpro.db` · `mysql+pymysql://user:pass@db:3306/autofixpro` |
| `APP_ENV` | `development` · `test` · `production` | `development` |
| `LOG_LEVEL` | Nivel de logs | `INFO` |
| `API_HOST` / `API_PORT` | Dirección y puerto (también puerto publicado en Docker) | `0.0.0.0` / `8000` |
| `TASA_IVA` | % aplicado a cotizaciones (supuesto a validar) | `16` |
| `CANAL_NOTIFICACIONES` | Canal de avisos (`log` implementado) | `log` |
| `SQL_ECHO` | Imprime el SQL (depuración) | `false` |
| `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` | Solo para el contenedor MySQL | ver `.env.example` |
| `TEST_DATABASE_URL` | BD para la suite de pruebas (si no se define, SQLite en memoria) | `mysql+pymysql://…/autofixpro_test` |

> `.env` está en `.gitignore`. `.env.example` no contiene secretos reales: **cambie los `CAMBIAR_*`**. Si la contraseña tiene caracteres especiales (`@ : / #`) debe ir codificada en URL.

---

## 6. Ejecución con Docker Compose

Levanta **MySQL 8 + aplicación**; las pruebas viven en un contenedor aparte (perfil `test`).

```bash
cp .env.example .env            # editar contraseñas
docker compose up --build -d    # db + app
docker compose ps               # esperar a que db esté "healthy"
curl http://localhost:8000/health
# Swagger UI → http://localhost:8000/docs
```
Contenedor de pruebas (usa la BD `<MYSQL_DATABASE>_test`, no toca los datos de la app):
```bash
docker compose --profile test run --rm tests
```
Otros comandos útiles:
```bash
docker compose logs -f app          # ver notificaciones y errores
docker compose down                 # detener (conserva datos)
docker compose down -v              # detener y BORRAR la base de datos
```
> El script `docker/mysql-init/01-crear-bd-pruebas.sh` solo corre al crear el volumen. Si ya tenía uno, use `docker compose down -v` una vez.

---

## 7. Pruebas y cobertura

```bash
pytest                                     # toda la suite; falla si la cobertura < 80 %
pytest tests/unit                          # solo unitarias (rápidas, sin BD)
pytest tests/integration                   # repositorios SQL + API
pytest --cov-report=html && open htmlcov/index.html
TEST_DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/autofixpro_test" pytest --no-cov   # contra MySQL
docker compose --profile test run --rm tests                                                    # en contenedor
```
Estado actual: **108 pruebas, cobertura ≈ 98 %** (umbral exigido: 80 %, configurado en `pyproject.toml`).

| Nivel | Qué valida |
|---|---|
| `unit/domain` | Value Objects (invariantes), Specifications (AND/OR/NOT), State Machine, reglas del agregado y entidades |
| `unit/application` | Casos de uso con repositorios en memoria (`tests/fakes.py`): publicación de eventos tras commit, rollback, handlers de notificación |
| `unit/test_arquitectura.py` | El dominio no importa SQLAlchemy/FastAPI/capas externas |
| `integration/test_repositorios.py` | Persistencia SQL, reconstitución fiel del agregado, no duplicación de hijos, rollback |
| `integration/test_dataset_pia.py` | Paquete de datos del PIA: integridad de los CSV, 120 casos de regla y 20 transiciones contra la API, con oráculo independiente |
| `integration/test_api_catalogo.py` | Catálogo, validación de cantidad/capacidad/habilitado, baja de clientes, endpoint de evaluación |
| `integration/test_api_flujo.py` | Ciclo completo por HTTP, roles (401/403), errores (404/409/422), auditoría y evidencia RN-11 |

---

## 8. API REST

Swagger UI: `/docs` · ReDoc: `/redoc` · OpenAPI: `/openapi.json` (copia en `docs/api/openapi.json`; regenerar con `python scripts/exportar_openapi.py`).

**Autenticación simplificada (RN-12):** cabecera `X-Rol` con uno de los cinco roles del BRD. En Swagger use el botón **Authorize**. Las consultas (`GET`) son abiertas (portal del cliente, RN-02).

| Endpoint (`/api/v1`) | Rol | US / RN |
|---|---|---|
| `POST /clientes` · `/vehiculos` · `/tecnicos` · `/flotillas` | asesor | RN-10, RN-09 |
| `PATCH /clientes/{id}/estado` — alta/baja | asesor | EXT-01 |
| `POST /catalogo` · `GET /catalogo` | asesor · público | CAT-01/02 |
| `GET /ordenes/{id}/evaluacion` — `puede_procesarse` y `beneficio_referencia` | público | Specification |
| `POST /ordenes` — ingreso y apertura de OT | asesor | US-01 · RN-01/09/14 |
| `GET /ordenes/{id}` — estado | público | US-12 · RN-02 |
| `POST /ordenes/{id}/diagnostico` | técnico | US-02 |
| `POST /ordenes/{id}/cotizacion` | asesor | US-03 · RN-05 |
| `POST /ordenes/{id}/cotizacion/respuesta` | cliente | US-04 · RN-05/11 |
| `POST /ordenes/{id}/trabajos` — asignar | asesor | US-05 · RN-13 |
| `POST /ordenes/{id}/refacciones-faltantes` | técnico, asesor | US-06 · RN-07 |
| `PATCH …/refacciones-faltantes/{sid}/reposicion` | compras, asesor | US-07 · RN-03 |
| `POST …/refacciones-faltantes/{sid}/recepcion` | compras | RN-07 |
| `POST /ordenes/{id}/fallas-adicionales` | técnico | US-08 · RN-04 |
| `POST …/fallas-adicionales/{sid}/cotizacion` | asesor | US-09 |
| `POST …/fallas-adicionales/{sid}/respuesta` | cliente | US-10 · RN-13 |
| `PUT /ordenes/{id}/fecha-entrega` | asesor | US-11 · RN-06 |
| `POST …/trabajos/{tid}/finalizacion` · `/revision` | técnico · asesor | US-13 |
| `POST /ordenes/{id}/listo-para-entrega` | asesor | US-14 |
| `POST /ordenes/{id}/cobro` | caja | US-15 |
| `POST /ordenes/{id}/cancelacion` | asesor | — |
| `GET /vehiculos/{id}/historial` · `GET /health` | público | — |

**Códigos:** `401` falta/rol desconocido · `403` rol sin permiso · `404` no existe · `409` regla de negocio o transición inválida (incluye `regla: "RN-xx"`) · `422` dato inválido.
**Evidencia (RN-11):** al responder una cotización el servidor registra el sello de tiempo y la IP del request (o un token de verificación si no hay IP válida).
Importes como `Decimal`; en JSON salen como cadena (`"1508.58"`).
**Identificadores:** son `str` (no UUID) con prefijo legible por tipo, p. ej. `ORD-9F2C41AB07D3E856`, `CLI-…`, `VEH-…`, `TEC-…`, `COT-…`; máximo 36 caracteres, sin espacios (`src/domain/value_objects/identificadores.py`).

---

## 9. Guía para la demo en vivo

**Preparación (5 min antes):** `docker compose up --build -d` (o ejecución local), abrir `/docs`, tener `docker compose logs -f app` en otra terminal y `htmlcov/index.html` o el resultado de `pytest` listo.

**Opción A — guion automático** (recomendado; muestra todos los pasos con ✔/✘):
```bash
python scripts/demo_flujo.py --url http://localhost:8000 --pausas
```
`--pausas` espera Enter en cada paso para que el equipo comente.

**Opción B — manual en Swagger** (Authorize con el rol de cada paso): ver tabla de la sección 8.

**Qué demostrar y qué regla/patrón lo respalda**

| Paso | Muestra | Respalda |
|---|---|---|
| Ingreso con datos completos | Orden en *Recibido* | RN-01 |
| Técnico intenta abrir orden → **403** | Control por rol | RN-12 |
| Cotizar sin diagnóstico → **409** con estados permitidos | **State Machine** | RN-01 |
| Cliente autoriza **parcialmente** | Total autorizado ≠ total cotizado; evidencia con IP y sello de tiempo | RN-05, RN-11 |
| Asignación | Solo se crean trabajos de lo autorizado | RN-13 |
| Refacción faltante + reposición | Estado *En espera*; **notificación en logs** | RN-07, RN-03 |
| Cambio de fecha con justificación | Historial conservado + aviso | RN-06 |
| Falla adicional → cotización complementaria | Nada se ejecuta sin autorización | RN-04 |
| Entrega sin revisar → **409** | **Specification** compuesta (`OrdenListaParaEntregaSpec`) | RF-14 |
| Cobro distinto al autorizado → **409**; exacto → *Cerrado* | Solo se cobra lo autorizado | RF-15 |
| `GET` de estado sin rol | Portal del cliente | RN-02 |

**Evidencia de auditoría en BD** (RNF-01): `SELECT tipo, ocurrido_en FROM eventos_dominio ORDER BY ocurrido_en;` y `SELECT ev_canal, ev_ip, ev_sello_tiempo FROM conceptos_cotizacion WHERE ev_canal IS NOT NULL;`

**Preguntas técnicas probables y dónde responderlas**
- *¿Por qué `Cotizacion` es entidad y no VO como en el diagrama?* → ADR-001 §2.5 (decisión por concepto con evidencia).
- *¿Cómo se garantiza que el dominio no dependa del framework?* → `tests/unit/test_arquitectura.py`.
- *¿Dónde viven las reglas de transición?* → `src/domain/state_machine/orden_state_machine.py` (tabla declarativa + guardas Specification).
- *¿Qué pasa si falla una notificación?* → el bus la aísla; la operación ya confirmada no se revierte (`infrastructure/messaging.py`).
- *¿Cómo se persiste el agregado?* → modelos separados + mappers (`infrastructure/persistence/mappers.py`), `merge` por clave primaria con cascade.

---

## 10. Paquete de datos del PIA (`data/pia`)

El docente entrega 40 actores, 20 recursos, 60 operaciones, 117 líneas de detalle, 120 casos de regla y 20 pruebas de transición.
Se cargan con `Decimal`, se siembran **por la API real con los roles del BRD** y se contrastan con un oráculo independiente
(`tests/dataset/oraculo.py`).

```bash
python scripts/ejecutar_dataset.py          # genera docs/evidencia/*.csv y resumen.md (código de salida ≠ 0 si algo no coincide)
pytest tests/integration/test_dataset_pia.py
```

| Resultado | Detalle |
|---|---|
| `validar_operacion` (`puede_procesarse`) | 43 VERDADERO · 17 FALSO |
| `evaluar_beneficio` (`beneficio_referencia`) | 9 VERDADERO · 51 FALSO |
| Transiciones | 4 aprobar · 4 cancelar · 4 repetir_aprobación (2.º rechazado) · 4 saltar_estado (rechazado) · 4 completar (2 ENTREGADA, 2 bloqueadas) |

Las diferencias entre el paquete y el análisis propio (promociones, cliente preferente, catálogo con capacidad, estados extra,
interpretación de las acciones, códigos `EXT-01`/`CAT-01`/`CAT-02`) están documentadas en
[`docs/architecture/dataset-vs-brd.md`](docs/architecture/dataset-vs-brd.md). **El oráculo y la interpretación de las acciones son del equipo**:
la solución oficial es del docente y debe contrastarse con `docs/evidencia/`.

---

## 11. Trazabilidad (análisis → código → pruebas)

| Regla BRD | User Story | Dominio / aplicación | Prueba |
|---|---|---|---|
| RN-01 datos completos | US-01 | `DatosRecepcion`, `OrdenServicio.registrar_ingreso` | `test_value_objects`, `test_orden_servicio::TestIngreso` |
| RN-02 consulta en tiempo real | US-12 | `ConsultarEstadoOrden`, `GET /ordenes/{id}` | `test_api_flujo` |
| RN-03 aviso de retraso | US-07 | `actualizar_reposicion` → `RetrasoPorRefaccion` → `NotificarRetrasoPorRefaccion` | `test_casos_de_uso`, `test_api_flujo` |
| RN-04 falla adicional | US-08/09/10 | `SolicitudAmpliacion`, cotización complementaria | `TestRefaccionesYFallas` |
| RN-05 autorización total/parcial | US-04 | `Cotizacion.responder` | `TestCotizacionYAutorizacion` |
| RN-06 historial de fechas | US-11 | `CambioFechaEntrega`, `modificar_fecha_entrega` | `TestFechaEntrega` |
| RN-07 solicitud a Compras | US-06 | `SolicitudRefaccion`, evento `RefaccionSinExistencia` | `test_rn07_*` |
| RN-09 flotilla | US-17 | `CuentaFlotilla`, descuento en `Cotizacion` | `TestIngreso`, `test_flotilla_*` |
| RN-10 medio digital | — | `DatosContacto` | `TestContactoYVehiculo` |
| RN-11 sello de tiempo + IP/token | — | `EvidenciaAutorizacion`, `construir_evidencia` | `test_rn11_*`, `test_ciclo_completo…` |
| RN-12 cinco roles | — | `src/api/seguridad.py` | `test_roles_rn12` |
| RN-13 solo lo autorizado | US-05 | `_construir_trabajos` | `test_rn13_*` |
| RN-14 único autorizador | — | `OrdenServicio.autorizador_id` | `test_rn14_*` |
| RF-14/RF-15 entrega y cobro | US-14/15 | `OrdenListaParaEntregaSpec`, `registrar_cobro_y_cerrar` | `test_guardas_con_specification`, `TestCierre` |

La matriz completa (con pruebas y casos del paquete) está en [`docs/trazabilidad.md`](docs/trazabilidad.md).

**Pendiente de la fase de análisis:** RN-08 / RF-16 (reportes e indicadores gerenciales) y la notificación por SMS/correo reales (hoy canal `log`) no están implementados; el BRD los marca con umbrales «a validar».

---

## 12. CI/CD

`.github/workflows/ci.yml` (en cada push/PR a `main`):
1. **test** — instala dependencias, ejecuta `pytest` con cobertura (falla < 80 %), sube `coverage.xml`.
2. **test-mysql** — corre la suite contra un servicio MySQL 8.
3. **docker** — valida `docker-compose.yml`, construye imágenes `runtime` y `test`; en `main` publica en GitHub Container Registry (`ghcr.io/<owner>/<repo>`).
4. **deploy** — en `main`, si existe el secreto `DEPLOY_HOOK_URL`, dispara el despliegue (Render/Railway).

## 13. Despliegue

La imagen `runtime` respeta la variable `PORT` y expone `/health`, por lo que sirve en Render, Railway o Fly.io:
1. Crear una base MySQL gestionada y copiar su URL como `mysql+pymysql://usuario:clave@host:3306/base`.
2. Crear un *Web Service* desde el repositorio (Dockerfile, `target: runtime` — en Render, "Docker" usa el último stage; para fijar el stage use `docker build --target runtime` o un `render.yaml`).
3. Definir variables: `DATABASE_URL`, `APP_ENV=production`, `LOG_LEVEL=INFO`.
4. Health check: `/health`. Verificar `<URL>/docs` y guardar la URL en este README.
5. (Opcional) Copiar el *Deploy Hook* a un secreto de GitHub llamado `DEPLOY_HOOK_URL`.

## 14. Solución de problemas

| Síntoma | Causa / solución |
|---|---|
| `docker compose` dice «Defina MYSQL_PASSWORD…» | Falta `.env`: `cp .env.example .env` |
| `app` reinicia con error de conexión | MySQL aún inicia; espere a `healthy` (`docker compose ps`) |
| `Access denied for user … _test` | El volumen de MySQL ya existía: `docker compose down -v` y vuelva a levantar |
| `401 Falta la cabecera X-Rol` | Pulse **Authorize** en Swagger o envíe `-H "X-Rol: asesor_servicio"` |
| `409 … no es válido en estado …` | Orden en otro estado; consulte `GET /ordenes/{id}` |
| Contraseña con `@` o `#` rompe `DATABASE_URL` | Codifíquela en URL (`@` → `%40`) |
| `cryptography` requerido | MySQL 8 usa `caching_sha2_password`: `pip install -r requirements.txt` |

## Alcance y supuestos

- IVA 16 % y descuento de flotilla 0 % por defecto: valores **a validar** con el stakeholder (BRD §6.2, §14).
- Autenticación por cabecera `X-Rol` (suficiente para el alcance del PIA); en producción real se sustituiría por JWT/OAuth2 manteniendo `requiere_rol`.
- El esquema se crea con `create_all`; migraciones (Alembic) quedan como trabajo futuro.
