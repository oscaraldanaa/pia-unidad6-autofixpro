# Evidencia de ejecución del paquete de datos PIA

- Casos de regla ejecutados: **120** · coinciden con el oráculo: **120**
- Transiciones ejecutadas: **20** · coinciden con lo esperado: **20**
- Datos: 40 actores, 20 recursos, 60 operaciones, 117 líneas de detalle

## Resultados de reglas

| Regla | Resultado | Casos |
|---|---|---|
| evaluar_beneficio | FALSO | 51 |
| evaluar_beneficio | VERDADERO | 9 |
| validar_operacion | FALSO | 17 |
| validar_operacion | VERDADERO | 43 |

## Resultados de transiciones

| Acción | Resultado | Estado final | Casos |
|---|---|---|---|
| aprobar | EXITO | DIAGNOSTICADA | 4 |
| cancelar | EXITO | CANCELADA | 4 |
| completar | EXITO | ENTREGADA | 2 |
| completar | RECHAZADA | AUTORIZADA* | 1 |
| completar | RECHAZADA | COTIZADA* | 1 |
| repetir_aprobacion | RECHAZADA | DIAGNOSTICADA | 4 |
| saltar_estado | RECHAZADA | RECIBIDA | 4 |

## Hallazgos de calidad de datos

- **operaciones sin detalle** (2): AUT-O013, AUT-O039
- **operaciones con actor inactivo** (9): AUT-O001, AUT-O002, AUT-O003, AUT-O004, AUT-O040, AUT-O041, AUT-O042, AUT-O043, AUT-O044
- **operaciones sin autorizacion** (7): AUT-O008, AUT-O016, AUT-O024, AUT-O032, AUT-O040, AUT-O048, AUT-O056
- **operaciones con promocion** (6): AUT-O009, AUT-O018, AUT-O027, AUT-O036, AUT-O045, AUT-O054
- **operaciones con recurso deshabilitado** (6): AUT-O005, AUT-O015, AUT-O020, AUT-O035, AUT-O040, AUT-O055
- **operaciones con cantidad sobre capacidad** (0): —
- **referencias huerfanas** (0): —

Detalle por caso (evidencia, orden interna, pasos HTTP y eventos de dominio) en los dos CSV de esta carpeta.
