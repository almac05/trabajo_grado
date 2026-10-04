# Pasajeros por despacho: distribución, carga por franja y capacidad de la flota

Generado por `analisis/36_pasajeros_por_despacho.py`.

- Fuente: `data/processed/model_ready/despachos_model_ready_freeze_20260823_203700.parquet`, columna `PASAJEROS_REALES`, una fila por despacho. Validación 2025-12-25 a 2026-04-01; evaluación 2026-04-02 a 2026-06-10 (todas las jornadas con despachos; jornada = inicio − 4 h).
- Verificación frente al dataset de modelado (38931 franjas): diferencia máxima en pasajeros por franja 0, en despachos 0; franjas con tipo de día distinto: 0.
- Bloques del diagnóstico por segmentos, por hora de inicio del despacho. Régimen raro = FESTIVO o FESTIVO_PUENTE.
- IC 95 % por bootstrap por jornada (1000 réplicas).
- **Criterio de «apreciable» (propio de este diagnóstico):** entre periodos, IC 95 % de la diferencia que excluye el cero y magnitud ≥ 10 % del valor de validación; entre bloques, rango entre bloques ≥ 10 % del valor de la ruta completa.

## Distribución por despacho: validacion

| Ruta | Celda | Despachos / jornadas | Q1 | Mediana | Q3 | P90 | IC 95 % mediana |
|---|---|---|---|---|---|---|---|
| 1 | ruta completa | 5362 / 98 | 35,0 | 44,0 | 53,0 | 62,0 | [43,0; 45,0] |
| 3 | ruta completa | 5816 / 98 | 38,0 | 48,0 | 59,0 | 69,0 | [47,0; 49,0] |
| 1 | régimen ordinario | 5315 / 94 | 36,0 | 44,0 | 53,0 | 63,0 | [43,0; 45,0] |
| 1 | régimen raro | 47 / 4 | 18,0 | 22,0 | 27,0 | 30,0 | [20,5; 26,0] |
| 3 | régimen ordinario | 5765 / 94 | 39,0 | 49,0 | 59,0 | 69,0 | [47,0; 50,0] |
| 3 | régimen raro | 51 / 4 | 16,5 | 23,0 | 28,0 | 34,0 | [21,0; 25,0] |
| 1 | madrugada (04:00-04:59) | 215 / 80 | 31,0 | 37,0 | 43,5 | 48,0 | [36,0; 39,0] |
| 1 | pico manana (05:00-06:59) | 887 / 81 | 35,0 | 42,0 | 48,5 | 55,0 | [41,0; 43,0] |
| 1 | manana (07:00-09:59) | 1363 / 98 | 35,0 | 43,0 | 52,0 | 61,0 | [42,0; 45,0] |
| 1 | valle (10:00-13:59) | 1601 / 97 | 33,0 | 43,0 | 51,0 | 59,0 | [42,0; 44,0] |
| 1 | pico tarde (14:00-15:59) | 800 / 97 | 45,0 | 54,0 | 65,0 | 74,0 | [52,0; 56,0] |
| 1 | cierre (16:00 en adelante) | 496 / 90 | 35,0 | 45,0 | 54,0 | 65,0 | [43,0; 47,0] |
| 3 | madrugada (04:00-04:59) | 370 / 80 | 31,0 | 37,0 | 46,0 | 53,0 | [35,0; 39,0] |
| 3 | pico manana (05:00-06:59) | 1357 / 82 | 39,0 | 52,0 | 67,0 | 80,0 | [51,0; 54,0] |
| 3 | manana (07:00-09:59) | 1397 / 98 | 37,0 | 48,0 | 57,0 | 66,0 | [46,0; 50,0] |
| 3 | valle (10:00-13:59) | 1619 / 98 | 39,0 | 48,0 | 57,0 | 66,0 | [47,0; 49,0] |
| 3 | pico tarde (14:00-15:59) | 733 / 96 | 43,0 | 52,0 | 60,0 | 67,0 | [50,0; 53,0] |
| 3 | cierre (16:00 en adelante) | 340 / 86 | 35,0 | 46,0 | 56,0 | 65,0 | [44,0; 47,0] |

## Distribución por despacho: evaluacion

| Ruta | Celda | Despachos / jornadas | Q1 | Mediana | Q3 | P90 | IC 95 % mediana |
|---|---|---|---|---|---|---|---|
| 1 | ruta completa | 3598 / 69 | 34,0 | 43,0 | 51,0 | 60,0 | [42,0; 44,0] |
| 3 | ruta completa | 3885 / 69 | 37,0 | 47,0 | 58,0 | 68,0 | [46,0; 49,0] |
| 1 | régimen ordinario | 3519 / 64 | 35,0 | 43,0 | 51,0 | 61,0 | [42,0; 44,0] |
| 1 | régimen raro | 79 / 5 | 18,0 | 22,0 | 27,0 | 32,2 | [19,0; 25,0] |
| 3 | régimen ordinario | 3800 / 64 | 37,0 | 48,0 | 58,0 | 69,0 | [47,0; 49,0] |
| 3 | régimen raro | 85 / 5 | 20,0 | 24,0 | 28,0 | 31,6 | [24,0; 25,0] |
| 1 | madrugada (04:00-04:59) | 148 / 54 | 32,0 | 39,0 | 45,0 | 48,0 | [35,0; 41,0] |
| 1 | pico manana (05:00-06:59) | 601 / 57 | 36,0 | 43,0 | 48,0 | 54,0 | [41,0; 44,0] |
| 1 | manana (07:00-09:59) | 924 / 69 | 34,0 | 43,0 | 51,0 | 58,0 | [41,0; 44,0] |
| 1 | valle (10:00-13:59) | 1082 / 69 | 32,0 | 41,0 | 49,0 | 58,0 | [39,0; 42,0] |
| 1 | pico tarde (14:00-15:59) | 531 / 68 | 44,0 | 52,0 | 62,0 | 72,0 | [50,0; 54,0] |
| 1 | cierre (16:00 en adelante) | 312 / 59 | 33,0 | 41,0 | 49,0 | 56,0 | [39,0; 44,0] |
| 3 | madrugada (04:00-04:59) | 250 / 54 | 31,0 | 37,0 | 44,0 | 50,0 | [35,0; 39,0] |
| 3 | pico manana (05:00-06:59) | 926 / 55 | 40,0 | 53,0 | 67,0 | 79,0 | [51,0; 55,0] |
| 3 | manana (07:00-09:59) | 927 / 69 | 35,0 | 47,0 | 56,0 | 65,0 | [45,0; 49,0] |
| 3 | valle (10:00-13:59) | 1106 / 69 | 37,0 | 47,0 | 56,0 | 65,0 | [45,0; 48,0] |
| 3 | pico tarde (14:00-15:59) | 473 / 69 | 39,0 | 49,0 | 58,0 | 65,0 | [47,0; 51,0] |
| 3 | cierre (16:00 en adelante) | 203 / 52 | 34,0 | 43,0 | 52,0 | 59,0 | [39,0; 45,0] |

## Variación entre bloques horarios

Rango de cada cuantil entre los seis bloques, como porcentaje del valor de la ruta completa.

| Periodo | Ruta | Cuantil | Ruta completa | Mínimo (bloque) | Máximo (bloque) | Rango %  | ¿Apreciable? |
|---|---|---|---|---|---|---|---|
| evaluacion | 1 | q1 | 34,0 | 32,0 (madrugada (04:00-04:59)) | 44,0 (pico tarde (14:00-15:59)) | 35,3 | sí |
| evaluacion | 1 | mediana | 43,0 | 39,0 (madrugada (04:00-04:59)) | 52,0 (pico tarde (14:00-15:59)) | 30,2 | sí |
| evaluacion | 1 | q3 | 51,0 | 45,0 (madrugada (04:00-04:59)) | 62,0 (pico tarde (14:00-15:59)) | 33,3 | sí |
| evaluacion | 1 | p90 | 60,0 | 48,0 (madrugada (04:00-04:59)) | 72,0 (pico tarde (14:00-15:59)) | 40,0 | sí |
| evaluacion | 3 | q1 | 37,0 | 31,0 (madrugada (04:00-04:59)) | 40,0 (pico manana (05:00-06:59)) | 24,3 | sí |
| evaluacion | 3 | mediana | 47,0 | 37,0 (madrugada (04:00-04:59)) | 53,0 (pico manana (05:00-06:59)) | 34,0 | sí |
| evaluacion | 3 | q3 | 58,0 | 44,0 (madrugada (04:00-04:59)) | 67,0 (pico manana (05:00-06:59)) | 39,7 | sí |
| evaluacion | 3 | p90 | 68,0 | 50,0 (madrugada (04:00-04:59)) | 79,0 (pico manana (05:00-06:59)) | 42,6 | sí |
| validacion | 1 | q1 | 35,0 | 31,0 (madrugada (04:00-04:59)) | 45,0 (pico tarde (14:00-15:59)) | 40,0 | sí |
| validacion | 1 | mediana | 44,0 | 37,0 (madrugada (04:00-04:59)) | 54,0 (pico tarde (14:00-15:59)) | 38,6 | sí |
| validacion | 1 | q3 | 53,0 | 43,5 (madrugada (04:00-04:59)) | 65,0 (pico tarde (14:00-15:59)) | 40,6 | sí |
| validacion | 1 | p90 | 62,0 | 48,0 (madrugada (04:00-04:59)) | 74,0 (pico tarde (14:00-15:59)) | 41,9 | sí |
| validacion | 3 | q1 | 38,0 | 31,0 (madrugada (04:00-04:59)) | 43,0 (pico tarde (14:00-15:59)) | 31,6 | sí |
| validacion | 3 | mediana | 48,0 | 37,0 (madrugada (04:00-04:59)) | 52,0 (pico manana (05:00-06:59)) | 31,2 | sí |
| validacion | 3 | q3 | 59,0 | 46,0 (madrugada (04:00-04:59)) | 67,0 (pico manana (05:00-06:59)) | 35,6 | sí |
| validacion | 3 | p90 | 69,0 | 53,0 (madrugada (04:00-04:59)) | 80,0 (pico manana (05:00-06:59)) | 39,1 | sí |

## Comparación entre periodos (validación → evaluación)

◆ = diferencia apreciable según el criterio indicado. El detalle con IC está en `comparacion_periodos__pasajeros_por_despacho.csv`.

| Ruta | Celda | Q1 | Mediana | Q3 | P90 |
|---|---|---|---|---|---|
| 1 | madrugada (04:00-04:59) | 31,0 → 32,0 (+3,2 %) | 37,0 → 39,0 (+5,4 %) | 43,5 → 45,0 (+3,4 %) | 48,0 → 48,0 (+0,0 %) |
| 1 | pico manana (05:00-06:59) | 35,0 → 36,0 (+2,9 %) | 42,0 → 43,0 (+2,4 %) | 48,5 → 48,0 (−1,0 %) | 55,0 → 54,0 (−1,8 %) |
| 1 | manana (07:00-09:59) | 35,0 → 34,0 (−2,9 %) | 43,0 → 43,0 (+0,0 %) | 52,0 → 51,0 (−1,9 %) | 61,0 → 58,0 (−4,9 %) |
| 1 | valle (10:00-13:59) | 33,0 → 32,0 (−3,0 %) | 43,0 → 41,0 (−4,7 %) | 51,0 → 49,0 (−3,9 %) | 59,0 → 58,0 (−1,7 %) |
| 1 | pico tarde (14:00-15:59) | 45,0 → 44,0 (−2,2 %) | 54,0 → 52,0 (−3,7 %) | 65,0 → 62,0 (−4,6 %) | 74,0 → 72,0 (−2,7 %) |
| 1 | cierre (16:00 en adelante) | 35,0 → 33,0 (−5,7 %) | 45,0 → 41,0 (−8,9 %) | 54,0 → 49,0 (−9,3 %) | 65,0 → 56,0 (−13,8 %) **◆** |
| 1 | régimen ordinario | 36,0 → 35,0 (−2,8 %) | 44,0 → 43,0 (−2,3 %) | 53,0 → 51,0 (−3,8 %) | 63,0 → 61,0 (−3,2 %) |
| 1 | régimen raro | 18,0 → 18,0 (+0,0 %) | 22,0 → 22,0 (+0,0 %) | 27,0 → 27,0 (+0,0 %) | 30,0 → 32,2 (+7,3 %) |
| 1 | ruta completa | 35,0 → 34,0 (−2,9 %) | 44,0 → 43,0 (−2,3 %) | 53,0 → 51,0 (−3,8 %) | 62,0 → 60,0 (−3,2 %) |
| 3 | madrugada (04:00-04:59) | 31,0 → 31,0 (+0,0 %) | 37,0 → 37,0 (+0,0 %) | 46,0 → 44,0 (−4,3 %) | 53,0 → 50,0 (−5,7 %) |
| 3 | pico manana (05:00-06:59) | 39,0 → 40,0 (+2,6 %) | 52,0 → 53,0 (+1,9 %) | 67,0 → 67,0 (+0,0 %) | 80,0 → 79,0 (−1,2 %) |
| 3 | manana (07:00-09:59) | 37,0 → 35,0 (−5,4 %) | 48,0 → 47,0 (−2,1 %) | 57,0 → 56,0 (−1,8 %) | 66,0 → 65,0 (−1,5 %) |
| 3 | valle (10:00-13:59) | 39,0 → 37,0 (−5,1 %) | 48,0 → 47,0 (−2,1 %) | 57,0 → 56,0 (−1,8 %) | 66,0 → 65,0 (−1,5 %) |
| 3 | pico tarde (14:00-15:59) | 43,0 → 39,0 (−9,3 %) | 52,0 → 49,0 (−5,8 %) | 60,0 → 58,0 (−3,3 %) | 67,0 → 65,0 (−3,0 %) |
| 3 | cierre (16:00 en adelante) | 35,0 → 34,0 (−2,9 %) | 46,0 → 43,0 (−6,5 %) | 56,0 → 52,0 (−7,1 %) | 65,0 → 59,0 (−9,2 %) |
| 3 | régimen ordinario | 39,0 → 37,0 (−5,1 %) | 49,0 → 48,0 (−2,0 %) | 59,0 → 58,0 (−1,7 %) | 69,0 → 69,0 (+0,0 %) |
| 3 | régimen raro | 16,5 → 20,0 (+21,2 %) | 23,0 → 24,0 (+4,3 %) | 28,0 → 28,0 (+0,0 %) | 34,0 → 31,6 (−7,1 %) |
| 3 | ruta completa | 38,0 → 37,0 (−2,6 %) | 48,0 → 47,0 (−2,1 %) | 59,0 → 58,0 (−1,7 %) | 69,0 → 68,0 (−1,4 %) |

## Clasificación de franjas por pasajeros por despacho

Umbrales: Q1 y Q3 de validación (por despacho) de la ruta y el bloque. La misma clasificación aplicada a las franjas de validación es la línea base: como la franja promedia varios despachos, ni siquiera sin cambio alguno cabe esperar un 25 % en cada extremo.

| Ruta | Bloque | Franjas eval. | % sobrecargada | % normal | % subutilizada | Línea base validación (sobre / normal / sub) |
|---|---|---|---|---|---|---|
| 1 | todos | 1552 | 15,7 | 60,1 | 24,2 | 18,3 / 60,8 / 20,9 |
| 1 | madrugada (04:00-04:59) | 64 | 20,3 | 65,6 | 14,1 | 11,8 / 68,2 / 20,0 |
| 1 | pico manana (05:00-06:59) | 219 | 16,9 | 66,7 | 16,4 | 15,4 / 66,8 / 17,9 |
| 1 | manana (07:00-09:59) | 381 | 16,5 | 58,8 | 24,7 | 19,6 / 58,2 / 22,2 |
| 1 | valle (10:00-13:59) | 496 | 19,0 | 56,9 | 24,2 | 20,2 / 60,4 / 19,5 |
| 1 | pico tarde (14:00-15:59) | 232 | 9,5 | 60,8 | 29,7 | 16,0 / 60,2 / 23,8 |
| 1 | cierre (16:00 en adelante) | 160 | 9,4 | 60,6 | 30,0 | 18,8 / 58,7 / 22,5 |
| 3 | todos | 1581 | 15,7 | 60,0 | 24,2 | 20,1 / 59,9 / 20,0 |
| 3 | madrugada (04:00-04:59) | 102 | 19,6 | 65,7 | 14,7 | 29,5 / 59,0 / 11,5 |
| 3 | pico manana (05:00-06:59) | 217 | 18,0 | 74,7 | 7,4 | 20,5 / 68,9 / 10,6 |
| 3 | manana (07:00-09:59) | 391 | 17,1 | 56,0 | 26,9 | 19,3 / 57,9 / 22,8 |
| 3 | valle (10:00-13:59) | 501 | 17,0 | 56,5 | 26,5 | 19,6 / 59,0 / 21,5 |
| 3 | pico tarde (14:00-15:59) | 238 | 9,7 | 57,1 | 33,2 | 16,8 / 58,2 / 25,0 |
| 3 | cierre (16:00 en adelante) | 132 | 11,4 | 62,1 | 26,5 | 22,5 / 57,7 / 19,8 |

## Capacidad de la flota en evaluación

Vehículos activos = placas distintas con al menos un despacho. Los mismos vehículos operan en ambas rutas, por lo que la fila «ambas» es la flota total.

| Ruta | Jornadas | Máx. despachos en una jornada (fecha, tipo) | Mediana despachos jornada laboral | Vehículos activos en el periodo | Máx. vehículos en una jornada | Mediana vehículos jornada laboral |
|---|---|---|---|---|---|---|
| 1 | 69 | 76 (2026-05-26, LABORAL) | 67 | 41 | 39 | 36 |
| 3 | 69 | 81 (2026-04-27, LABORAL) | 72 | 42 | 41 | 36 |
| ambas | 69 | 154 (2026-04-07, LABORAL) | 139 | 42 | 41 | 37 |
