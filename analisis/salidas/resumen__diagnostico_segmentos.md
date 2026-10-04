# Diagnóstico por segmentos: método ganador en validación y en evaluación

Generado por `analisis/32_diagnostico_segmentos_metodos.py`. Diagnóstico descriptivo: no define ninguna regla de selección.

- Evaluación: 2026-04-02 a 2026-06-10, 134 jornadas comunes del freeze `freeze_20260922_203820` (3038 franjas). Nueve métodos: los ocho del freeze y la referencia combinada del script 25.
- Validación: 2025-12-25 a 2026-04-01, 192 jornadas (4637 franjas).
- Métricas ponderadas por observaciones. Sesgo = predicción − real. WAPE = 100·Σ|error| / Σreal.
- † = celda pequeña (n < 100 o menos de 5 jornadas).
- «Comunes» = métodos con predicciones en ambos periodos; la persistencia del ganador se evalúa sobre ese conjunto. La columna «9 métodos» es informativa.
- «A = B» indica empate exacto. La combinada es idéntica a la referencia de 26 s en régimen ordinario y a la de 52 s en régimen raro, por lo que empata con una de ellas en toda celda de un solo régimen.

## Disponibilidad de predicciones por franja en validación

| Método | Validación | Fuente |
|---|---|---|
| XGBoost | sí | `observaciones__barrido_ventana__validacion_hparam.csv` (26 semanas, script 31) |
| Referencia (26s) | sí | `observaciones__referencia_combinada_regimen__validacion.csv` (script 25) |
| Referencia (52s) | sí | `observaciones__referencia_combinada_regimen__validacion.csv` (script 25) |
| Combinada (26s/52s) | sí | `observaciones__referencia_combinada_regimen__validacion.csv` (script 25) |
| SARIMA | no | solo métricas agregadas por configuración (`busqueda_hiperparametros/configuraciones__sarima.csv`) |
| Prophet | no | solo métricas agregadas por configuración (`busqueda_hiperparametros/configuraciones__prophet.csv`) |
| LSTM | no | solo métricas agregadas por configuración (`busqueda_hiperparametros/configuraciones__lstm.csv`) |
| GRU | no | solo métricas agregadas por configuración (`busqueda_hiperparametros/configuraciones__gru.csv`) |
| CNN-LSTM | no | solo métricas agregadas por configuración (`busqueda_hiperparametros/configuraciones__cnn_lstm.csv`) |

## Verificación

MAE global recalculado frente al persistido por el freeze y por el script 25; XGBoost 26 s del script 31 frente al recalculado en el script 25 (diferencia máxima por franja: 0.00e+00).

| Periodo | Método | MAE recalculado | MAE persistido | Coincide |
|---|---|---|---|---|
| evaluacion | SARIMA | 48,0729 | 48,0729 | sí |
| evaluacion | Prophet | 30,6272 | 30,6272 | sí |
| evaluacion | XGBoost | 28,3442 | 28,3442 | sí |
| evaluacion | LSTM | 29,1061 | 29,1061 | sí |
| evaluacion | GRU | 29,5904 | 29,5904 | sí |
| evaluacion | CNN-LSTM | 29,6815 | 29,6815 | sí |
| evaluacion | Referencia (26s) | 28,3580 | 28,3580 | sí |
| evaluacion | Referencia (52s) | 29,3364 | 29,3364 | sí |
| evaluacion | Combinada (26s/52s) | 27,8133 | 27,8133 | sí |
| validacion | XGBoost | 29,0729 | 29,0729 | sí |
| validacion | Referencia (26s) | 29,0292 | 29,0292 | sí |
| validacion | Referencia (52s) | 30,5106 | 30,5106 | sí |
| validacion | Combinada (26s/52s) | 29,0044 | 29,0044 | sí |

## Umbrales de nivel de demanda (calculados en validación, por ruta)

Nivel esperado: cuartiles de la predicción de la referencia de 26 semanas, conocida antes de la franja. Nivel observado: cuartiles de la demanda real; **solo descriptivo, no utilizable para decidir en la operación**, porque la demanda real no se conoce de antemano. Intervalos cerrados por la derecha: N1 ≤ Q25 < N2 ≤ Q50 < N3 ≤ Q75 < N4.

| Base | Ruta | Q25 | Q50 | Q75 |
|---|---|---|---|---|
| prediccion referencia 26s (esperado) | 1 | 95,56 | 121,77 | 138,47 |
| prediccion referencia 26s (esperado) | 3 | 93,13 | 135,93 | 152,58 |
| demanda observada (descriptivo) | 1 | 69,00 | 103,00 | 138,00 |
| demanda observada (descriptivo) | 3 | 67,00 | 116,00 | 159,00 |

## Métricas por bloque horario, ambas rutas (MAE / sesgo / WAPE %)

### Validación

| Método | madrugada (04:00-04:59) | pico manana (05:00-06:59) | manana (07:00-09:59) | valle (10:00-13:59) | pico tarde (14:00-15:59) | cierre (16:00 en adelante) |
|---|---|---|---|---|---|---|
| n / jornadas | 235 / 159 | 641 / 163 | 1114 / 192 | 1451 / 192 | 699 / 192 | 497 / 176 |
| XGBoost | 22,34 / 10,02 / 24,0 | 35,54 / 6,28 / 20,6 | 28,11 / 5,78 / 24,9 | 26,77 / 6,75 / 26,6 | 33,00 / 6,67 / 28,5 | 27,28 / 11,95 / 35,6 |
| Referencia (26s) | 21,60 / 10,08 / 23,2 | 37,19 / 13,58 / 21,5 | 28,06 / 8,16 / 24,9 | 25,94 / 7,66 / 25,7 | 33,88 / 14,89 / 29,2 | 26,36 / 11,23 / 34,4 |
| Referencia (52s) | 27,58 / 21,16 / 29,6 | 40,01 / 21,42 / 23,2 | 28,77 / 12,10 / 25,5 | 26,63 / 11,21 / 26,4 | 34,98 / 18,64 / 30,2 | 28,59 / 17,38 / 37,3 |
| Combinada (26s/52s) | 21,60 / 10,08 / 23,2 | 37,19 / 13,58 / 21,5 | 28,07 / 8,17 / 24,9 | 25,92 / 7,67 / 25,7 | 33,88 / 14,94 / 29,2 | 26,20 / 11,05 / 34,2 |

### Evaluación

| Método | madrugada (04:00-04:59) | pico manana (05:00-06:59) | manana (07:00-09:59) | valle (10:00-13:59) | pico tarde (14:00-15:59) | cierre (16:00 en adelante) |
|---|---|---|---|---|---|---|
| n / jornadas | 152 / 105 | 424 / 109 | 752 / 134 | 971 / 134 | 457 / 133 | 282 / 108 |
| SARIMA | 38,64 / 8,84 / 41,3 | 67,07 / -50,85 / 38,5 | 43,49 / 2,45 / 41,0 | 43,64 / 6,10 / 45,1 | 53,42 / -4,16 / 49,6 | 43,42 / 27,74 / 59,3 |
| Prophet | 25,34 / 6,90 / 27,1 | 41,68 / -10,84 / 24,0 | 29,23 / 0,37 / 27,5 | 27,83 / 0,31 / 28,8 | 33,16 / 6,44 / 30,8 | 26,13 / 7,52 / 35,7 |
| XGBoost | 21,95 / 3,38 / 23,5 | 37,04 / -3,52 / 21,3 | 27,40 / 2,94 / 25,8 | 26,56 / 2,43 / 27,5 | 31,38 / 2,42 / 29,1 | 22,47 / 8,60 / 30,7 |
| LSTM | 27,26 / 0,73 / 29,1 | 36,86 / -2,28 / 21,2 | 28,02 / 4,67 / 26,4 | 26,67 / 2,30 / 27,6 | 31,62 / 7,96 / 29,3 | 25,65 / 12,49 / 35,0 |
| GRU | 26,64 / -1,26 / 28,5 | 37,20 / -2,93 / 21,4 | 28,88 / 4,62 / 27,2 | 27,27 / 2,67 / 28,2 | 31,53 / 6,98 / 29,3 | 26,46 / 12,14 / 36,1 |
| CNN-LSTM | 26,69 / -1,28 / 28,5 | 37,10 / -3,46 / 21,3 | 28,89 / 5,55 / 27,2 | 27,47 / 3,00 / 28,4 | 31,87 / 6,97 / 29,6 | 26,35 / 12,27 / 36,0 |
| Referencia (26s) | 22,28 / 2,86 / 23,8 | 34,99 / 2,08 / 20,1 | 27,61 / 6,16 / 26,0 | 26,74 / 5,02 / 27,7 | 31,75 / 10,70 / 29,5 | 23,72 / 11,74 / 32,4 |
| Referencia (52s) | 24,87 / 13,20 / 26,6 | 36,61 / 12,83 / 21,0 | 28,35 / 11,36 / 26,7 | 26,74 / 8,86 / 27,7 | 33,39 / 18,07 / 31,0 | 25,83 / 18,22 / 35,3 |
| Combinada (26s/52s) | 22,28 / 2,86 / 23,8 | 34,97 / 2,06 / 20,1 | 27,25 / 6,03 / 25,7 | 25,98 / 4,45 / 26,9 | 30,70 / 9,79 / 28,5 | 23,17 / 11,20 / 31,6 |

## Ganadores: bloque horario

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | madrugada (04:00-04:59) | 79 / 79 † | XGBoost (22,62) | 52 / 52 † | Combinada (26s/52s) = Referencia (26s) (21,64) | Combinada (26s/52s) = Referencia (26s) (21,64) | no | XGBoost (16,47) | Combinada (26s/52s) = Referencia (26s) (6,57) | Prophet (3,05) | no |
| 1 | pico manana (05:00-06:59) | 319 / 81 | XGBoost (24,15) | 211 / 55 | Combinada (26s/52s) (24,62) | GRU (24,44) | no | XGBoost (7,27) | XGBoost (0,52) | LSTM (-0,09) | sí |
| 1 | manana (07:00-09:59) | 561 / 97 | XGBoost (26,38) | 367 / 66 | XGBoost (26,46) | LSTM (26,25) | sí | XGBoost (5,84) | XGBoost (1,38) | GRU (1,07) | sí |
| 1 | valle (10:00-13:59) | 734 / 97 | Combinada (26s/52s) (23,92) | 477 / 66 | Combinada (26s/52s) (24,96) | Combinada (26s/52s) (24,96) | sí | XGBoost (7,83) | XGBoost (3,29) | Prophet (0,26) | sí |
| 1 | pico tarde (14:00-15:59) | 349 / 97 | XGBoost (34,15) | 223 / 65 | Combinada (26s/52s) (33,16) | CNN-LSTM (32,45) | no | XGBoost (5,53) | XGBoost (0,37) | XGBoost (0,37) | sí |
| 1 | cierre (16:00 en adelante) | 271 / 90 | Combinada (26s/52s) (28,35) | 153 / 57 | XGBoost (25,83) | XGBoost (25,83) | no | XGBoost (10,83) | XGBoost (9,39) | Prophet (9,05) | sí |
| 3 | madrugada (04:00-04:59) | 156 / 80 | Combinada (26s/52s) = Referencia (26s) (20,40) | 100 / 53 | XGBoost (21,62) | XGBoost (21,62) | no | Combinada (26s/52s) = Referencia (26s) (6,19) | XGBoost (0,49) | XGBoost (0,49) | no |
| 3 | pico manana (05:00-06:59) | 322 / 82 | XGBoost (46,83) | 213 / 54 | Combinada (26s/52s) = Referencia (26s) (45,23) | Combinada (26s/52s) = Referencia (26s) (45,23) | no | XGBoost (5,31) | Combinada (26s/52s) = Referencia (26s) (2,76) | Combinada (26s/52s) = Referencia (26s) (2,76) | no |
| 3 | manana (07:00-09:59) | 553 / 95 | Referencia (26s) (29,46) | 385 / 68 | Combinada (26s/52s) (27,98) | Combinada (26s/52s) (27,98) | no | XGBoost (5,73) | XGBoost (4,42) | Prophet (2,12) | sí |
| 3 | valle (10:00-13:59) | 717 / 95 | Referencia (26s) (27,94) | 494 / 68 | Combinada (26s/52s) (26,96) | Combinada (26s/52s) (26,96) | no | XGBoost (5,64) | XGBoost (1,60) | Prophet (0,36) | sí |
| 3 | pico tarde (14:00-15:59) | 350 / 95 | XGBoost (31,85) | 234 / 68 | XGBoost (28,18) | XGBoost (28,18) | sí | XGBoost (7,80) | XGBoost (4,36) | XGBoost (4,36) | sí |
| 3 | cierre (16:00 en adelante) | 226 / 86 | Referencia (26s) (23,61) | 129 / 51 | XGBoost (18,48) | XGBoost (18,48) | no | Referencia (26s) (10,44) | XGBoost (7,67) | Prophet (5,70) | no |
| ambas | madrugada (04:00-04:59) | 235 / 159 | Combinada (26s/52s) = Referencia (26s) (21,60) | 152 / 105 | XGBoost (21,95) | XGBoost (21,95) | no | XGBoost (10,02) | Combinada (26s/52s) = Referencia (26s) (2,86) | LSTM (0,73) | no |
| ambas | pico manana (05:00-06:59) | 641 / 163 | XGBoost (35,54) | 424 / 109 | Combinada (26s/52s) (34,97) | Combinada (26s/52s) (34,97) | no | XGBoost (6,28) | Combinada (26s/52s) (2,06) | Combinada (26s/52s) (2,06) | no |
| ambas | manana (07:00-09:59) | 1114 / 192 | Referencia (26s) (28,06) | 752 / 134 | Combinada (26s/52s) (27,25) | Combinada (26s/52s) (27,25) | no | XGBoost (5,78) | XGBoost (2,94) | Prophet (0,37) | sí |
| ambas | valle (10:00-13:59) | 1451 / 192 | Combinada (26s/52s) (25,92) | 971 / 134 | Combinada (26s/52s) (25,98) | Combinada (26s/52s) (25,98) | sí | XGBoost (6,75) | XGBoost (2,43) | Prophet (0,31) | sí |
| ambas | pico tarde (14:00-15:59) | 699 / 192 | XGBoost (33,00) | 457 / 133 | Combinada (26s/52s) (30,70) | Combinada (26s/52s) (30,70) | no | XGBoost (6,67) | XGBoost (2,42) | XGBoost (2,42) | sí |
| ambas | cierre (16:00 en adelante) | 497 / 176 | Combinada (26s/52s) (26,20) | 282 / 108 | XGBoost (22,47) | XGBoost (22,47) | no | Combinada (26s/52s) (11,05) | XGBoost (8,60) | Prophet (7,52) | no |

## Ganadores: tipo de dia

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | LABORAL | 1738 / 66 | XGBoost (29,31) | 1084 / 42 | Combinada (26s/52s) = Referencia (26s) (29,06) | Combinada (26s/52s) = Referencia (26s) (29,06) | no | XGBoost (7,90) | XGBoost (2,50) | Prophet (-0,47) | sí |
| 1 | SABADO | 348 / 14 | XGBoost (24,51) | 241 / 10 | XGBoost (24,43) | GRU (23,28) | sí | Combinada (26s/52s) = Referencia (26s) (9,11) | XGBoost (3,95) | CNN-LSTM (-1,05) | no |
| 1 | DOMINGO | 188 / 14 | XGBoost (10,88) | 97 / 9 † | XGBoost (10,73) | LSTM (9,68) | sí | XGBoost (0,62) | XGBoost (1,87) | LSTM (-0,09) | sí |
| 1 | FESTIVO | 10 / 1 † | Combinada (26s/52s) = Referencia (52s) (11,22) | 40 / 3 † | XGBoost (12,65) | XGBoost (12,65) | no | Combinada (26s/52s) = Referencia (52s) (10,04) | Combinada (26s/52s) = Referencia (52s) (0,59) | LSTM (-0,02) | sí |
| 1 | FESTIVO_PUENTE | 29 / 2 † | Referencia (26s) (9,83) | 21 / 2 † | Combinada (26s/52s) = Referencia (52s) (12,37) | LSTM (10,03) | no | Referencia (26s) (2,03) | Referencia (26s) (0,95) | Prophet (-0,65) | sí |
| 3 | LABORAL | 1764 / 66 | XGBoost (34,06) | 1131 / 43 | Combinada (26s/52s) = Referencia (26s) (32,63) | Combinada (26s/52s) = Referencia (26s) (32,63) | no | XGBoost (7,14) | XGBoost (1,54) | Prophet (-0,59) | sí |
| 3 | SABADO | 346 / 14 | Combinada (26s/52s) = Referencia (26s) (26,53) | 244 / 10 | Combinada (26s/52s) = Referencia (26s) (25,73) | Combinada (26s/52s) = Referencia (26s) (25,73) | sí | XGBoost (7,47) | XGBoost (2,99) | XGBoost (2,99) | sí |
| 3 | DOMINGO | 174 / 12 | Referencia (52s) (11,20) | 110 / 10 | XGBoost (9,71) | CNN-LSTM (8,76) | no | XGBoost (-0,14) | XGBoost (1,31) | XGBoost (1,31) | sí |
| 3 | FESTIVO | 9 / 1 † | Combinada (26s/52s) = Referencia (52s) (13,11) | 48 / 3 † | Combinada (26s/52s) = Referencia (52s) (13,52) | Combinada (26s/52s) = Referencia (52s) (13,52) | sí | Combinada (26s/52s) = Referencia (52s) (10,94) | Combinada (26s/52s) = Referencia (52s) (1,49) | Prophet (0,81) | sí |
| 3 | FESTIVO_PUENTE | 31 / 2 † | Referencia (26s) (9,93) | 22 / 2 † | Combinada (26s/52s) = Referencia (52s) (8,60) | LSTM (7,47) | no | Referencia (26s) (1,00) | Combinada (26s/52s) = Referencia (52s) (2,59) | CNN-LSTM (-0,31) | no |
| ambas | LABORAL | 3502 / 132 | XGBoost (31,70) | 2215 / 85 | Combinada (26s/52s) = Referencia (26s) (30,88) | Combinada (26s/52s) = Referencia (26s) (30,88) | no | XGBoost (7,52) | XGBoost (2,01) | Prophet (-0,53) | sí |
| ambas | SABADO | 694 / 28 | Combinada (26s/52s) = Referencia (26s) (25,76) | 485 / 20 | Combinada (26s/52s) = Referencia (26s) (25,14) | CNN-LSTM (24,71) | sí | XGBoost (8,45) | XGBoost (3,47) | LSTM (-2,37) | sí |
| ambas | DOMINGO | 362 / 26 | Referencia (52s) (11,08) | 207 / 19 | XGBoost (10,19) | CNN-LSTM (9,26) | no | XGBoost (0,26) | XGBoost (1,57) | CNN-LSTM (-1,01) | sí |
| ambas | FESTIVO | 19 / 2 † | Combinada (26s/52s) = Referencia (52s) (12,12) | 88 / 6 † | XGBoost (13,13) | XGBoost (13,13) | no | Combinada (26s/52s) = Referencia (52s) (10,47) | Combinada (26s/52s) = Referencia (52s) (1,08) | Prophet (-0,75) | sí |
| ambas | FESTIVO_PUENTE | 60 / 4 † | Referencia (26s) (9,88) | 43 / 4 † | Combinada (26s/52s) = Referencia (52s) (10,44) | LSTM (8,72) | no | Referencia (26s) (1,49) | Referencia (26s) (2,27) | Prophet (-1,35) | sí |

## Ganadores: regimen

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ordinario | 2274 / 94 | XGBoost (27,05) | 1422 / 61 | Combinada (26s/52s) = Referencia (26s) (27,12) | Combinada (26s/52s) = Referencia (26s) (27,12) | no | XGBoost (7,54) | XGBoost (2,70) | Prophet (0,67) | sí |
| 1 | raro | 39 / 3 † | Combinada (26s/52s) = Referencia (52s) (10,56) | 61 / 5 † | Combinada (26s/52s) = Referencia (52s) (13,20) | LSTM (11,83) | sí | Combinada (26s/52s) = Referencia (52s) (5,44) | Combinada (26s/52s) = Referencia (52s) (1,62) | LSTM (-1,52) | sí |
| 3 | ordinario | 2284 / 92 | Combinada (26s/52s) = Referencia (26s) (31,40) | 1485 / 63 | Combinada (26s/52s) = Referencia (26s) (29,82) | Combinada (26s/52s) = Referencia (26s) (29,82) | sí | XGBoost (6,63) | XGBoost (1,76) | Prophet (0,85) | sí |
| 3 | raro | 40 / 3 † | Referencia (26s) (10,86) | 70 / 5 † | Combinada (26s/52s) = Referencia (52s) (11,98) | Combinada (26s/52s) = Referencia (52s) (11,98) | no | Referencia (26s) (3,41) | Combinada (26s/52s) = Referencia (52s) (1,84) | Prophet (-0,08) | no |
| ambas | ordinario | 4558 / 186 | XGBoost (29,30) | 2907 / 124 | Combinada (26s/52s) = Referencia (26s) (28,50) | Combinada (26s/52s) = Referencia (26s) (28,50) | no | XGBoost (7,08) | XGBoost (2,22) | Prophet (0,76) | sí |
| ambas | raro | 79 / 6 † | Combinada (26s/52s) = Referencia (52s) (11,17) | 131 / 10 | Combinada (26s/52s) = Referencia (52s) (12,55) | Combinada (26s/52s) = Referencia (52s) (12,55) | sí | Combinada (26s/52s) = Referencia (52s) (5,56) | Combinada (26s/52s) = Referencia (52s) (1,74) | Prophet (-0,95) | sí |

## Ganadores: nivel de demanda esperada (cuartiles de la referencia 26s)

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | N1 (bajo) | 579 / 97 | Referencia (26s) (18,64) | 484 / 66 | Referencia (26s) (20,17) | LSTM (19,97) | sí | Referencia (26s) (4,68) | Referencia (26s) (4,18) | LSTM (-0,14) | sí |
| 1 | N2 (medio-bajo) | 578 / 81 | Combinada (26s/52s) (23,82) | 334 / 54 | XGBoost (25,73) | XGBoost (25,73) | no | Combinada (26s/52s) (7,19) | XGBoost (5,70) | SARIMA (1,90) | no |
| 1 | N3 (medio-alto) | 578 / 66 | Combinada (26s/52s) = Referencia (26s) (29,84) | 471 / 42 | Combinada (26s/52s) = Referencia (26s) (29,03) | Combinada (26s/52s) = Referencia (26s) (29,03) | sí | XGBoost (9,42) | XGBoost (0,59) | XGBoost (0,59) | sí |
| 1 | N4 (alto) | 578 / 66 | XGBoost (34,32) | 194 / 42 | Combinada (26s/52s) = Referencia (26s) (37,01) | Prophet (36,35) | no | XGBoost (6,68) | XGBoost (-1,87) | XGBoost (-1,87) | sí |
| 3 | N1 (bajo) | 581 / 95 | Referencia (26s) (17,25) | 429 / 68 | XGBoost (15,91) | XGBoost (15,91) | no | Referencia (26s) (5,14) | XGBoost (4,20) | LSTM (3,44) | no |
| 3 | N2 (medio-bajo) | 581 / 80 | Combinada (26s/52s) = Referencia (26s) (29,29) | 574 / 55 | Combinada (26s/52s) (30,36) | Combinada (26s/52s) (30,36) | no | Combinada (26s/52s) = Referencia (26s) (8,44) | XGBoost (3,60) | XGBoost (3,60) | no |
| 3 | N3 (medio-alto) | 581 / 76 | XGBoost (33,15) | 264 / 53 | XGBoost (31,93) | XGBoost (31,93) | sí | XGBoost (3,50) | XGBoost (1,14) | XGBoost (1,14) | sí |
| 3 | N4 (alto) | 581 / 80 | XGBoost (42,08) | 288 / 53 | Combinada (26s/52s) = Referencia (26s) (42,47) | Combinada (26s/52s) = Referencia (26s) (42,47) | no | XGBoost (6,72) | XGBoost (-4,25) | GRU (-0,33) | sí |
| ambas | N1 (bajo) | 1160 / 192 | Referencia (26s) (17,94) | 913 / 134 | XGBoost (18,30) | XGBoost (18,30) | no | Referencia (26s) (4,91) | XGBoost (4,55) | LSTM (1,54) | no |
| ambas | N2 (medio-bajo) | 1159 / 161 | Combinada (26s/52s) (26,56) | 908 / 109 | Combinada (26s/52s) (28,84) | Combinada (26s/52s) (28,84) | sí | Combinada (26s/52s) (7,82) | XGBoost (4,37) | XGBoost (4,37) | no |
| ambas | N3 (medio-alto) | 1159 / 142 | XGBoost (31,55) | 735 / 95 | Combinada (26s/52s) = Referencia (26s) (30,18) | Combinada (26s/52s) = Referencia (26s) (30,18) | no | XGBoost (6,45) | XGBoost (0,79) | XGBoost (0,79) | sí |
| ambas | N4 (alto) | 1159 / 146 | XGBoost (38,21) | 482 / 95 | Combinada (26s/52s) = Referencia (26s) (40,27) | Combinada (26s/52s) = Referencia (26s) (40,27) | no | XGBoost (6,70) | XGBoost (-3,29) | CNN-LSTM (1,70) | sí |

## Ganadores: bloque horario x regimen

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | madrugada (04:00-04:59) x ordinario | 79 / 79 † | XGBoost (22,62) | 52 / 52 † | Combinada (26s/52s) = Referencia (26s) (21,64) | Combinada (26s/52s) = Referencia (26s) (21,64) | no | XGBoost (16,47) | Combinada (26s/52s) = Referencia (26s) (6,57) | Prophet (3,05) | no |
| 1 | pico manana (05:00-06:59) x ordinario | 319 / 81 | XGBoost (24,15) | 210 / 54 | Combinada (26s/52s) = Referencia (26s) (24,73) | GRU (24,46) | no | XGBoost (7,27) | XGBoost (0,42) | LSTM (-0,03) | sí |
| 1 | pico manana (05:00-06:59) x raro | — | — | 1 / 1 † | Combinada (26s/52s) = Referencia (52s) (1,50) | Combinada (26s/52s) = Referencia (52s) (1,50) | — | — | Combinada (26s/52s) = Referencia (52s) (1,50) | Combinada (26s/52s) = Referencia (52s) (1,50) | — |
| 1 | manana (07:00-09:59) x ordinario | 547 / 94 | XGBoost (26,57) | 345 / 61 | Combinada (26s/52s) = Referencia (26s) (27,09) | LSTM (27,04) | no | XGBoost (5,70) | XGBoost (0,98) | XGBoost (0,98) | sí |
| 1 | manana (07:00-09:59) x raro | 14 / 3 † | Referencia (26s) (11,49) | 22 / 5 † | XGBoost (15,95) | Prophet (13,75) | no | Combinada (26s/52s) = Referencia (52s) (3,81) | Combinada (26s/52s) = Referencia (52s) (0,60) | Combinada (26s/52s) = Referencia (52s) (0,60) | sí |
| 1 | valle (10:00-13:59) x ordinario | 716 / 94 | Combinada (26s/52s) = Referencia (26s) (24,27) | 450 / 61 | Combinada (26s/52s) = Referencia (26s) (25,78) | Combinada (26s/52s) = Referencia (26s) (25,78) | sí | XGBoost (7,83) | XGBoost (3,42) | Prophet (0,81) | sí |
| 1 | valle (10:00-13:59) x raro | 18 / 3 † | Combinada (26s/52s) = Referencia (52s) (9,77) | 27 / 5 † | Combinada (26s/52s) = Referencia (52s) (11,37) | LSTM (10,69) | sí | Combinada (26s/52s) = Referencia (52s) (7,84) | XGBoost (1,17) | LSTM (0,05) | no |
| 1 | pico tarde (14:00-15:59) x ordinario | 344 / 94 | XGBoost (34,44) | 214 / 60 | Combinada (26s/52s) = Referencia (26s) (34,05) | CNN-LSTM (33,28) | no | XGBoost (5,50) | XGBoost (-0,10) | XGBoost (-0,10) | sí |
| 1 | pico tarde (14:00-15:59) x raro | 5 / 3 † | Combinada (26s/52s) = Referencia (52s) (11,21) | 9 / 5 † | Combinada (26s/52s) = Referencia (52s) (12,08) | GRU (8,61) | sí | Referencia (26s) (-1,65) | Combinada (26s/52s) = Referencia (52s) (-0,59) | Combinada (26s/52s) = Referencia (52s) (-0,59) | no |
| 1 | cierre (16:00 en adelante) x ordinario | 269 / 88 | Combinada (26s/52s) = Referencia (26s) (28,50) | 151 / 55 | XGBoost (26,17) | XGBoost (26,17) | no | XGBoost (10,81) | XGBoost (9,51) | Prophet (9,20) | sí |
| 1 | cierre (16:00 en adelante) x raro | 2 / 2 † | Combinada (26s/52s) = Referencia (52s) (8,42) | 2 / 2 † | XGBoost (0,43) | XGBoost (0,43) | no | Combinada (26s/52s) = Referencia (52s) (2,92) | XGBoost (-0,15) | XGBoost (-0,15) | no |
| 3 | madrugada (04:00-04:59) x ordinario | 156 / 80 | Combinada (26s/52s) = Referencia (26s) (20,40) | 100 / 53 | XGBoost (21,62) | XGBoost (21,62) | no | Combinada (26s/52s) = Referencia (26s) (6,19) | XGBoost (0,49) | XGBoost (0,49) | no |
| 3 | pico manana (05:00-06:59) x ordinario | 322 / 82 | XGBoost (46,83) | 213 / 54 | Combinada (26s/52s) = Referencia (26s) (45,23) | Combinada (26s/52s) = Referencia (26s) (45,23) | no | XGBoost (5,31) | Combinada (26s/52s) = Referencia (26s) (2,76) | Combinada (26s/52s) = Referencia (26s) (2,76) | no |
| 3 | manana (07:00-09:59) x ordinario | 539 / 92 | Combinada (26s/52s) = Referencia (26s) (29,84) | 360 / 63 | Combinada (26s/52s) = Referencia (26s) (28,91) | Combinada (26s/52s) = Referencia (26s) (28,91) | sí | XGBoost (5,46) | XGBoost (4,27) | SARIMA (1,92) | sí |
| 3 | manana (07:00-09:59) x raro | 14 / 3 † | Referencia (26s) (14,95) | 25 / 5 † | Combinada (26s/52s) = Referencia (52s) (14,53) | Combinada (26s/52s) = Referencia (52s) (14,53) | no | Referencia (26s) (6,55) | Combinada (26s/52s) = Referencia (52s) (0,56) | Combinada (26s/52s) = Referencia (52s) (0,56) | no |
| 3 | valle (10:00-13:59) x ordinario | 698 / 92 | Combinada (26s/52s) = Referencia (26s) (28,48) | 463 / 63 | Combinada (26s/52s) = Referencia (26s) (28,03) | Combinada (26s/52s) = Referencia (26s) (28,03) | sí | XGBoost (5,44) | XGBoost (1,56) | Prophet (0,52) | sí |
| 3 | valle (10:00-13:59) x raro | 19 / 3 † | Referencia (26s) (8,06) | 31 / 5 † | Combinada (26s/52s) = Referencia (52s) (11,04) | Prophet (10,34) | no | Referencia (26s) (1,72) | Combinada (26s/52s) = Referencia (52s) (0,70) | Combinada (26s/52s) = Referencia (52s) (0,70) | no |
| 3 | pico tarde (14:00-15:59) x ordinario | 344 / 92 | XGBoost (32,16) | 221 / 63 | XGBoost (29,27) | XGBoost (29,27) | sí | XGBoost (7,71) | XGBoost (4,08) | XGBoost (4,08) | sí |
| 3 | pico tarde (14:00-15:59) x raro | 6 / 3 † | Referencia (26s) (10,31) | 13 / 5 † | Combinada (26s/52s) = Referencia (52s) (9,31) | Prophet (6,06) | no | Referencia (26s) (0,34) | Combinada (26s/52s) = Referencia (52s) (8,08) | Prophet (3,56) | no |
| 3 | cierre (16:00 en adelante) x ordinario | 225 / 85 | Combinada (26s/52s) = Referencia (26s) (23,67) | 128 / 50 | XGBoost (18,49) | XGBoost (18,49) | no | Combinada (26s/52s) = Referencia (26s) (10,44) | XGBoost (7,87) | Prophet (6,07) | no |
| 3 | cierre (16:00 en adelante) x raro | 1 / 1 † | XGBoost (8,28) | 1 / 1 † | Combinada (26s/52s) = Referencia (52s) (12,00) | LSTM (10,26) | no | XGBoost (8,28) | Combinada (26s/52s) = Referencia (52s) (-12,00) | LSTM (-10,26) | no |
| ambas | madrugada (04:00-04:59) x ordinario | 235 / 159 | Combinada (26s/52s) = Referencia (26s) (21,60) | 152 / 105 | XGBoost (21,95) | XGBoost (21,95) | no | XGBoost (10,02) | Combinada (26s/52s) = Referencia (26s) (2,86) | LSTM (0,73) | no |
| ambas | pico manana (05:00-06:59) x ordinario | 641 / 163 | XGBoost (35,54) | 423 / 108 | Combinada (26s/52s) = Referencia (26s) (35,05) | Combinada (26s/52s) = Referencia (26s) (35,05) | no | XGBoost (6,28) | Combinada (26s/52s) = Referencia (26s) (2,06) | Combinada (26s/52s) = Referencia (26s) (2,06) | no |
| ambas | pico manana (05:00-06:59) x raro | — | — | 1 / 1 † | Combinada (26s/52s) = Referencia (52s) (1,50) | Combinada (26s/52s) = Referencia (52s) (1,50) | — | — | Combinada (26s/52s) = Referencia (52s) (1,50) | Combinada (26s/52s) = Referencia (52s) (1,50) | — |
| ambas | manana (07:00-09:59) x ordinario | 1086 / 186 | XGBoost (28,29) | 705 / 124 | Combinada (26s/52s) = Referencia (26s) (28,02) | Combinada (26s/52s) = Referencia (26s) (28,02) | no | XGBoost (5,58) | XGBoost (2,66) | Prophet (0,39) | sí |
| ambas | manana (07:00-09:59) x raro | 28 / 6 † | Referencia (26s) (13,22) | 47 / 10 † | XGBoost (15,30) | XGBoost (15,30) | no | Referencia (26s) (5,49) | Combinada (26s/52s) = Referencia (52s) (0,58) | Prophet (0,16) | no |
| ambas | valle (10:00-13:59) x ordinario | 1414 / 186 | Combinada (26s/52s) = Referencia (26s) (26,35) | 913 / 124 | Combinada (26s/52s) = Referencia (26s) (26,92) | Combinada (26s/52s) = Referencia (26s) (26,92) | sí | XGBoost (6,65) | XGBoost (2,47) | Prophet (0,66) | sí |
| ambas | valle (10:00-13:59) x raro | 37 / 6 † | Combinada (26s/52s) = Referencia (52s) (9,52) | 58 / 10 † | Combinada (26s/52s) = Referencia (52s) (11,19) | Combinada (26s/52s) = Referencia (52s) (11,19) | sí | Referencia (26s) (5,72) | XGBoost (1,73) | XGBoost (1,73) | no |
| ambas | pico tarde (14:00-15:59) x ordinario | 688 / 186 | XGBoost (33,30) | 435 / 123 | Combinada (26s/52s) = Referencia (26s) (31,72) | Combinada (26s/52s) = Referencia (26s) (31,72) | no | XGBoost (6,60) | XGBoost (2,02) | XGBoost (2,02) | sí |
| ambas | pico tarde (14:00-15:59) x raro | 11 / 6 † | Combinada (26s/52s) = Referencia (52s) (11,52) | 22 / 10 † | Combinada (26s/52s) = Referencia (52s) (10,44) | Combinada (26s/52s) = Referencia (52s) (10,44) | sí | Referencia (26s) (-0,57) | Combinada (26s/52s) = Referencia (52s) (4,53) | Combinada (26s/52s) = Referencia (52s) (4,53) | no |
| ambas | cierre (16:00 en adelante) x ordinario | 494 / 173 | Combinada (26s/52s) = Referencia (26s) (26,30) | 279 / 105 | XGBoost (22,64) | XGBoost (22,64) | no | Combinada (26s/52s) = Referencia (26s) (11,08) | XGBoost (8,76) | Prophet (7,76) | no |
| ambas | cierre (16:00 en adelante) x raro | 3 / 3 † | Combinada (26s/52s) = Referencia (52s) (9,69) | 3 / 3 † | XGBoost (6,22) | XGBoost (6,22) | no | Combinada (26s/52s) = Referencia (52s) (6,03) | Combinada (26s/52s) = Referencia (52s) (-4,56) | LSTM (-0,54) | sí |

## Ganadores: nivel de demanda observada (descriptivo, no operativo)

Este corte usa la demanda real de la franja, que no se conoce al momento de decidir. Se incluye solo para contrastarlo con el nivel esperado.

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | N1 (bajo) | 583 / 95 | Combinada (26s/52s) (31,97) | 407 / 64 | XGBoost (29,94) | LSTM (28,13) | no | XGBoost (29,04) | XGBoost (26,87) | LSTM (23,85) | sí |
| 1 | N2 (medio-bajo) | 574 / 83 | XGBoost (28,36) | 365 / 54 | XGBoost (23,70) | SARIMA (14,45) | sí | XGBoost (24,95) | XGBoost (17,95) | SARIMA (13,65) | sí |
| 1 | N3 (medio-alto) | 596 / 80 | XGBoost (16,54) | 388 / 51 | XGBoost (15,29) | Prophet (14,88) | sí | XGBoost (4,31) | XGBoost (-0,82) | CNN-LSTM (-0,07) | sí |
| 1 | N4 (alto) | 560 / 76 | Referencia (52s) (24,21) | 323 / 49 | Referencia (52s) (30,05) | Referencia (52s) (30,05) | sí | Referencia (52s) (-19,59) | Referencia (52s) (-26,81) | Referencia (52s) (-26,81) | sí |
| 3 | N1 (bajo) | 584 / 94 | Referencia (26s) (28,58) | 437 / 68 | XGBoost (24,68) | XGBoost (24,68) | no | Referencia (26s) (25,64) | XGBoost (21,50) | LSTM (21,26) | no |
| 3 | N2 (medio-bajo) | 590 / 83 | XGBoost (33,85) | 399 / 56 | XGBoost (27,08) | SARIMA (24,17) | sí | XGBoost (26,12) | XGBoost (19,37) | SARIMA (14,47) | sí |
| 3 | N3 (medio-alto) | 571 / 80 | XGBoost (19,27) | 350 / 52 | Combinada (26s/52s) = Referencia (26s) (19,11) | Combinada (26s/52s) = Referencia (26s) (19,11) | no | XGBoost (1,54) | Combinada (26s/52s) = Referencia (26s) (-0,60) | Combinada (26s/52s) = Referencia (26s) (-0,60) | no |
| 3 | N4 (alto) | 579 / 80 | Referencia (52s) (37,67) | 369 / 52 | Referencia (52s) (38,34) | Referencia (52s) (38,34) | sí | Referencia (52s) (-11,37) | Referencia (52s) (-15,12) | Referencia (52s) (-15,12) | sí |
| ambas | N1 (bajo) | 1167 / 189 | Combinada (26s/52s) (30,30) | 844 / 132 | XGBoost (27,22) | LSTM (26,96) | no | Combinada (26s/52s) (27,47) | XGBoost (24,09) | LSTM (22,51) | no |
| ambas | N2 (medio-bajo) | 1164 / 166 | XGBoost (31,14) | 764 / 110 | XGBoost (25,47) | SARIMA (19,52) | sí | XGBoost (25,54) | XGBoost (18,69) | SARIMA (14,08) | sí |
| ambas | N3 (medio-alto) | 1167 / 160 | XGBoost (17,87) | 738 / 103 | Combinada (26s/52s) = Referencia (26s) (17,54) | Combinada (26s/52s) = Referencia (26s) (17,54) | no | XGBoost (2,95) | Combinada (26s/52s) = Referencia (26s) (0,90) | LSTM (0,10) | no |
| ambas | N4 (alto) | 1139 / 156 | Referencia (52s) (31,05) | 692 / 101 | Referencia (52s) (34,47) | Referencia (52s) (34,47) | sí | Referencia (52s) (-15,41) | Referencia (52s) (-20,58) | Referencia (52s) (-20,58) | sí |

## Ganadores: franja de 30 minutos, ambas rutas (tabla secundaria)

El detalle por ruta está en `ganadores__diagnostico_segmentos.csv`.

| Ruta | Segmento | Val. n / jorn. | Val. menor MAE | Eval. n / jorn. | Eval. menor MAE (comunes) | Eval. menor MAE (9 métodos) | ¿Mantiene MAE? | Val. menor \|sesgo\| | Eval. menor \|sesgo\| (comunes) | Eval. menor \|sesgo\| (9 métodos) | ¿Mantiene sesgo? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ambas | 04:00 | 77 / 77 † | Referencia (52s) (11,54) | 47 / 47 † | XGBoost (10,88) | GRU (9,90) | no | XGBoost (0,81) | XGBoost (0,05) | XGBoost (0,05) | sí |
| ambas | 04:30 | 158 / 158 | XGBoost (26,33) | 105 / 105 | Combinada (26s/52s) = Referencia (26s) (26,90) | Combinada (26s/52s) = Referencia (26s) (26,90) | no | XGBoost (14,51) | Combinada (26s/52s) = Referencia (26s) (2,90) | CNN-LSTM (-1,28) | no |
| ambas | 05:00 | 158 / 158 | XGBoost (33,59) | 105 / 105 | Referencia (52s) (33,02) | Referencia (52s) (33,02) | no | XGBoost (2,33) | Combinada (26s/52s) = Referencia (26s) (-2,49) | Combinada (26s/52s) = Referencia (26s) (-2,49) | no |
| ambas | 05:30 | 160 / 160 | XGBoost (36,13) | 105 / 105 | Combinada (26s/52s) = Referencia (26s) (31,20) | Combinada (26s/52s) = Referencia (26s) (31,20) | no | XGBoost (11,94) | Combinada (26s/52s) = Referencia (26s) (-4,93) | LSTM (0,44) | no |
| ambas | 06:00 | 160 / 160 | XGBoost (38,13) | 105 / 105 | Combinada (26s/52s) = Referencia (26s) (40,10) | LSTM (40,06) | no | XGBoost (3,84) | XGBoost (-0,79) | LSTM (-0,23) | sí |
| ambas | 06:30 | 163 / 163 | XGBoost (34,32) | 109 / 109 | Combinada (26s/52s) (35,12) | Combinada (26s/52s) (35,12) | no | XGBoost (6,97) | XGBoost (-0,72) | GRU (0,71) | sí |
| ambas | 07:00 | 186 / 186 | Referencia (52s) (26,04) | 124 / 124 | Combinada (26s/52s) (29,43) | Combinada (26s/52s) (29,43) | no | Combinada (26s/52s) (5,94) | XGBoost (10,21) | SARIMA (1,65) | no |
| ambas | 07:30 | 188 / 188 | XGBoost (26,69) | 126 / 126 | XGBoost (26,30) | XGBoost (26,30) | sí | XGBoost (6,85) | XGBoost (-0,98) | XGBoost (-0,98) | sí |
| ambas | 08:00 | 186 / 186 | XGBoost (30,78) | 130 / 130 | XGBoost (24,96) | XGBoost (24,96) | sí | XGBoost (4,99) | XGBoost (1,43) | XGBoost (1,43) | sí |
| ambas | 08:30 | 189 / 189 | XGBoost (28,59) | 126 / 126 | Referencia (26s) (30,18) | Referencia (26s) (30,18) | no | XGBoost (5,78) | XGBoost (-1,01) | LSTM (-0,16) | sí |
| ambas | 09:00 | 182 / 182 | Referencia (52s) (28,99) | 123 / 123 | Referencia (26s) (26,05) | Referencia (26s) (26,05) | no | XGBoost (1,94) | XGBoost (-1,39) | XGBoost (-1,39) | sí |
| ambas | 09:30 | 183 / 183 | XGBoost (25,73) | 123 / 123 | XGBoost (25,61) | XGBoost (25,61) | sí | Combinada (26s/52s) (8,22) | Combinada (26s/52s) (9,31) | Prophet (4,09) | sí |
| ambas | 10:00 | 186 / 186 | Referencia (26s) (26,95) | 120 / 120 | XGBoost (25,81) | XGBoost (25,81) | no | Referencia (26s) (6,23) | XGBoost (2,73) | XGBoost (2,73) | no |
| ambas | 10:30 | 188 / 188 | Combinada (26s/52s) (22,60) | 122 / 122 | Referencia (26s) (24,78) | Referencia (26s) (24,78) | no | Referencia (26s) (3,57) | Referencia (26s) (2,38) | LSTM (0,05) | sí |
| ambas | 11:00 | 179 / 179 | Combinada (26s/52s) (22,23) | 126 / 126 | Combinada (26s/52s) (22,91) | Combinada (26s/52s) (22,91) | sí | Referencia (26s) (7,38) | Combinada (26s/52s) (5,31) | LSTM (0,91) | no |
| ambas | 11:30 | 179 / 179 | Combinada (26s/52s) (24,08) | 126 / 126 | XGBoost (24,85) | LSTM (24,66) | no | Combinada (26s/52s) (6,73) | XGBoost (0,61) | Prophet (0,25) | no |
| ambas | 12:00 | 182 / 182 | Referencia (26s) (27,84) | 124 / 124 | Combinada (26s/52s) (24,43) | Combinada (26s/52s) (24,43) | no | XGBoost (2,12) | XGBoost (-1,49) | XGBoost (-1,49) | sí |
| ambas | 12:30 | 179 / 179 | Referencia (26s) (28,44) | 119 / 119 | XGBoost (24,06) | Prophet (23,39) | no | XGBoost (3,28) | XGBoost (4,32) | SARIMA (0,17) | sí |
| ambas | 13:00 | 181 / 181 | Referencia (26s) (26,60) | 117 / 117 | XGBoost (28,37) | Prophet (28,19) | no | XGBoost (2,48) | XGBoost (1,73) | XGBoost (1,73) | sí |
| ambas | 13:30 | 177 / 177 | Referencia (26s) (28,27) | 117 / 117 | Combinada (26s/52s) (31,23) | Combinada (26s/52s) (31,23) | no | XGBoost (10,09) | Combinada (26s/52s) (0,40) | Combinada (26s/52s) (0,40) | no |
| ambas | 14:00 | 180 / 180 | XGBoost (29,50) | 117 / 117 | Combinada (26s/52s) (30,51) | GRU (29,28) | no | XGBoost (8,30) | XGBoost (5,53) | SARIMA (3,48) | sí |
| ambas | 14:30 | 178 / 178 | XGBoost (29,23) | 116 / 116 | Combinada (26s/52s) (31,13) | Combinada (26s/52s) (31,13) | no | XGBoost (5,57) | XGBoost (2,18) | XGBoost (2,18) | sí |
| ambas | 15:00 | 173 / 173 | Referencia (26s) (37,05) | 118 / 118 | Combinada (26s/52s) (32,00) | Combinada (26s/52s) (32,00) | no | XGBoost (5,27) | XGBoost (0,65) | XGBoost (0,65) | sí |
| ambas | 15:30 | 168 / 168 | XGBoost (35,92) | 106 / 106 | XGBoost (28,82) | XGBoost (28,82) | sí | XGBoost (7,53) | XGBoost (1,21) | Prophet (-0,15) | sí |
| ambas | 16:00 | 165 / 165 | Combinada (26s/52s) (33,31) | 102 / 102 | XGBoost (24,51) | XGBoost (24,51) | no | Combinada (26s/52s) (12,24) | XGBoost (4,96) | Prophet (0,92) | no |
| ambas | 16:30 | 156 / 156 | Combinada (26s/52s) (27,86) | 92 / 92 † | XGBoost (25,53) | XGBoost (25,53) | no | Combinada (26s/52s) (18,75) | XGBoost (14,68) | Prophet (11,54) | no |
| ambas | 17:00 | 121 / 121 | XGBoost (22,28) | 70 / 70 † | XGBoost (18,26) | XGBoost (18,26) | sí | Combinada (26s/52s) = Referencia (26s) (3,99) | XGBoost (5,66) | XGBoost (5,66) | no |
| ambas | 17:30 | 43 / 43 † | Combinada (26s/52s) = Referencia (26s) (9,38) | 15 / 15 † | XGBoost (11,72) | LSTM (11,51) | no | Combinada (26s/52s) = Referencia (26s) (1,00) | XGBoost (9,36) | LSTM (9,01) | no |
| ambas | 18:00 | 12 / 12 † | Combinada (26s/52s) = Referencia (26s) (6,38) | 3 / 3 † | Referencia (52s) (1,81) | Referencia (52s) (1,81) | no | Referencia (52s) (-0,35) | Combinada (26s/52s) = Referencia (26s) (-0,56) | Combinada (26s/52s) = Referencia (26s) (-0,56) | no |

## Resumen de persistencia por corte

| Corte | Segmentos en ambos periodos | Mantiene MAE | Mantiene MAE (sin †) | Mantiene \|sesgo\| | Mantiene \|sesgo\| (sin †) |
|---|---|---|---|---|---|
| Bloque horario | 18 | 4 | 4 de 17 | 11 | 11 de 17 |
| Franja de 30 minutos | 86 | 21 | 5 de 24 | 49 | 15 de 24 |
| Tipo de dia | 15 | 5 | 3 de 8 | 13 | 7 de 8 |
| Regimen | 6 | 3 | 1 de 3 | 5 | 3 de 3 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 12 | 4 | 4 de 12 | 7 | 7 de 12 |
| Nivel de demanda observada (descriptivo) | 12 | 7 | 7 de 12 | 8 | 8 de 12 |
| Bloque horario x regimen | 30 | 9 | 5 de 17 | 13 | 11 de 17 |

## Segmentos donde el ganador por menor MAE se mantiene entre periodos

53 segmentos (sobre los métodos comunes). Valor del ganador en cada periodo; n de validación / evaluación.

| Corte | Ruta | Segmento | Ganador | Valor val. | Valor eval. | n val. / eval. |
|---|---|---|---|---|---|---|
| Bloque horario | 1 | manana (07:00-09:59) | XGBoost | 26,38 | 26,46 | 561 / 367 |
| Bloque horario | 1 | valle (10:00-13:59) | Combinada (26s/52s) | 23,92 | 24,96 | 734 / 477 |
| Bloque horario | 3 | pico tarde (14:00-15:59) | XGBoost | 31,85 | 28,18 | 350 / 234 |
| Bloque horario | ambas | valle (10:00-13:59) | Combinada (26s/52s) | 25,92 | 25,98 | 1451 / 971 |
| Franja de 30 minutos | 1 | 07:30 † | XGBoost | 24,74 | 25,21 | 94 / 62 |
| Franja de 30 minutos | 1 | 09:30 † | XGBoost | 22,41 | 26,12 | 93 / 60 |
| Franja de 30 minutos | 1 | 11:00 † | Combinada (26s/52s) | 20,26 | 25,10 | 91 / 62 |
| Franja de 30 minutos | 1 | 17:00 † | Combinada (26s/52s) = Referencia (26s) | 25,54 | 20,68 | 68 / 39 |
| Franja de 30 minutos | 1 | 17:30 † | XGBoost | 7,98 | 9,72 | 28 / 11 |
| Franja de 30 minutos | 3 | 06:00 † | Combinada (26s/52s) = Referencia (26s) | 50,67 | 56,00 | 80 / 53 |
| Franja de 30 minutos | 3 | 07:30 † | XGBoost | 28,63 | 27,36 | 94 / 64 |
| Franja de 30 minutos | 3 | 10:30 † | Combinada (26s/52s) | 28,37 | 27,23 | 92 / 63 |
| Franja de 30 minutos | 3 | 11:00 † | Combinada (26s/52s) | 24,27 | 20,79 | 88 / 64 |
| Franja de 30 minutos | 3 | 14:00 † | Combinada (26s/52s) | 29,41 | 26,23 | 91 / 62 |
| Franja de 30 minutos | 3 | 14:30 † | XGBoost | 26,77 | 26,39 | 88 / 59 |
| Franja de 30 minutos | 3 | 15:30 † | XGBoost | 32,57 | 26,60 | 85 / 53 |
| Franja de 30 minutos | 3 | 17:00 † | XGBoost | 17,72 | 13,84 | 53 / 31 |
| Franja de 30 minutos | 3 | 17:30 † | Referencia (52s) | 8,95 | 12,78 | 15 / 4 |
| Franja de 30 minutos | 3 | 18:00 † | Referencia (52s) | 0,67 | 1,57 | 1 / 1 |
| Franja de 30 minutos | ambas | 07:30 | XGBoost | 26,69 | 26,30 | 188 / 126 |
| Franja de 30 minutos | ambas | 08:00 | XGBoost | 30,78 | 24,96 | 186 / 130 |
| Franja de 30 minutos | ambas | 09:30 | XGBoost | 25,73 | 25,61 | 183 / 123 |
| Franja de 30 minutos | ambas | 11:00 | Combinada (26s/52s) | 22,23 | 22,91 | 179 / 126 |
| Franja de 30 minutos | ambas | 15:30 | XGBoost | 35,92 | 28,82 | 168 / 106 |
| Franja de 30 minutos | ambas | 17:00 † | XGBoost | 22,28 | 18,26 | 121 / 70 |
| Tipo de dia | 1 | SABADO | XGBoost | 24,51 | 24,43 | 348 / 241 |
| Tipo de dia | 1 | DOMINGO † | XGBoost | 10,88 | 10,73 | 188 / 97 |
| Tipo de dia | 3 | SABADO | Combinada (26s/52s) = Referencia (26s) | 26,53 | 25,73 | 346 / 244 |
| Tipo de dia | 3 | FESTIVO † | Combinada (26s/52s) = Referencia (52s) | 13,11 | 13,52 | 9 / 48 |
| Tipo de dia | ambas | SABADO | Combinada (26s/52s) = Referencia (26s) | 25,76 | 25,14 | 694 / 485 |
| Regimen | 1 | raro † | Combinada (26s/52s) = Referencia (52s) | 10,56 | 13,20 | 39 / 61 |
| Regimen | 3 | ordinario | Combinada (26s/52s) = Referencia (26s) | 31,40 | 29,82 | 2284 / 1485 |
| Regimen | ambas | raro † | Combinada (26s/52s) = Referencia (52s) | 11,17 | 12,55 | 79 / 131 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 1 | N1 (bajo) | Referencia (26s) | 18,64 | 20,17 | 579 / 484 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 1 | N3 (medio-alto) | Combinada (26s/52s) = Referencia (26s) | 29,84 | 29,03 | 578 / 471 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 3 | N3 (medio-alto) | XGBoost | 33,15 | 31,93 | 581 / 264 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | ambas | N2 (medio-bajo) | Combinada (26s/52s) | 26,56 | 28,84 | 1159 / 908 |
| Nivel de demanda observada (descriptivo) | 1 | N2 (medio-bajo) | XGBoost | 28,36 | 23,70 | 574 / 365 |
| Nivel de demanda observada (descriptivo) | 1 | N3 (medio-alto) | XGBoost | 16,54 | 15,29 | 596 / 388 |
| Nivel de demanda observada (descriptivo) | 1 | N4 (alto) | Referencia (52s) | 24,21 | 30,05 | 560 / 323 |
| Nivel de demanda observada (descriptivo) | 3 | N2 (medio-bajo) | XGBoost | 33,85 | 27,08 | 590 / 399 |
| Nivel de demanda observada (descriptivo) | 3 | N4 (alto) | Referencia (52s) | 37,67 | 38,34 | 579 / 369 |
| Nivel de demanda observada (descriptivo) | ambas | N2 (medio-bajo) | XGBoost | 31,14 | 25,47 | 1164 / 764 |
| Nivel de demanda observada (descriptivo) | ambas | N4 (alto) | Referencia (52s) | 31,05 | 34,47 | 1139 / 692 |
| Bloque horario x regimen | 1 | valle (10:00-13:59) x ordinario | Combinada (26s/52s) = Referencia (26s) | 24,27 | 25,78 | 716 / 450 |
| Bloque horario x regimen | 1 | valle (10:00-13:59) x raro † | Combinada (26s/52s) = Referencia (52s) | 9,77 | 11,37 | 18 / 27 |
| Bloque horario x regimen | 1 | pico tarde (14:00-15:59) x raro † | Combinada (26s/52s) = Referencia (52s) | 11,21 | 12,08 | 5 / 9 |
| Bloque horario x regimen | 3 | manana (07:00-09:59) x ordinario | Combinada (26s/52s) = Referencia (26s) | 29,84 | 28,91 | 539 / 360 |
| Bloque horario x regimen | 3 | valle (10:00-13:59) x ordinario | Combinada (26s/52s) = Referencia (26s) | 28,48 | 28,03 | 698 / 463 |
| Bloque horario x regimen | 3 | pico tarde (14:00-15:59) x ordinario | XGBoost | 32,16 | 29,27 | 344 / 221 |
| Bloque horario x regimen | ambas | valle (10:00-13:59) x ordinario | Combinada (26s/52s) = Referencia (26s) | 26,35 | 26,92 | 1414 / 913 |
| Bloque horario x regimen | ambas | valle (10:00-13:59) x raro † | Combinada (26s/52s) = Referencia (52s) | 9,52 | 11,19 | 37 / 58 |
| Bloque horario x regimen | ambas | pico tarde (14:00-15:59) x raro † | Combinada (26s/52s) = Referencia (52s) | 11,52 | 10,44 | 11 / 22 |

## Segmentos donde el ganador por menor |sesgo| se mantiene entre periodos

106 segmentos (sobre los métodos comunes). Valor del ganador en cada periodo; n de validación / evaluación.

| Corte | Ruta | Segmento | Ganador | Valor val. | Valor eval. | n val. / eval. |
|---|---|---|---|---|---|---|
| Bloque horario | 1 | pico manana (05:00-06:59) | XGBoost | 7,27 | 0,52 | 319 / 211 |
| Bloque horario | 1 | manana (07:00-09:59) | XGBoost | 5,84 | 1,38 | 561 / 367 |
| Bloque horario | 1 | valle (10:00-13:59) | XGBoost | 7,83 | 3,29 | 734 / 477 |
| Bloque horario | 1 | pico tarde (14:00-15:59) | XGBoost | 5,53 | 0,37 | 349 / 223 |
| Bloque horario | 1 | cierre (16:00 en adelante) | XGBoost | 10,83 | 9,39 | 271 / 153 |
| Bloque horario | 3 | manana (07:00-09:59) | XGBoost | 5,73 | 4,42 | 553 / 385 |
| Bloque horario | 3 | valle (10:00-13:59) | XGBoost | 5,64 | 1,60 | 717 / 494 |
| Bloque horario | 3 | pico tarde (14:00-15:59) | XGBoost | 7,80 | 4,36 | 350 / 234 |
| Bloque horario | ambas | manana (07:00-09:59) | XGBoost | 5,78 | 2,94 | 1114 / 752 |
| Bloque horario | ambas | valle (10:00-13:59) | XGBoost | 6,75 | 2,43 | 1451 / 971 |
| Bloque horario | ambas | pico tarde (14:00-15:59) | XGBoost | 6,67 | 2,42 | 699 / 457 |
| Franja de 30 minutos | 1 | 05:00 † | Combinada (26s/52s) = Referencia (26s) | 4,26 | 0,06 | 78 / 52 |
| Franja de 30 minutos | 1 | 06:00 † | XGBoost | 11,23 | 4,66 | 80 / 52 |
| Franja de 30 minutos | 1 | 10:00 † | Combinada (26s/52s) | 7,66 | 5,01 | 94 / 60 |
| Franja de 30 minutos | 1 | 11:00 † | Combinada (26s/52s) | 5,14 | 5,24 | 91 / 62 |
| Franja de 30 minutos | 1 | 12:30 † | XGBoost | 3,10 | 7,73 | 92 / 58 |
| Franja de 30 minutos | 1 | 13:00 † | XGBoost | 7,80 | 2,69 | 89 / 58 |
| Franja de 30 minutos | 1 | 13:30 † | XGBoost | 8,99 | -0,58 | 90 / 58 |
| Franja de 30 minutos | 1 | 14:00 † | XGBoost | 7,04 | 0,29 | 89 / 55 |
| Franja de 30 minutos | 1 | 14:30 † | XGBoost | 5,62 | 6,26 | 90 / 57 |
| Franja de 30 minutos | 1 | 15:00 † | XGBoost | 6,65 | -2,64 | 87 / 58 |
| Franja de 30 minutos | 1 | 15:30 † | XGBoost | 2,63 | -2,57 | 83 / 53 |
| Franja de 30 minutos | 1 | 16:00 † | XGBoost | 8,56 | 6,00 | 84 / 54 |
| Franja de 30 minutos | 1 | 16:30 † | XGBoost | 23,96 | 15,05 | 80 / 47 |
| Franja de 30 minutos | 1 | 17:30 † | XGBoost | 0,47 | 6,50 | 28 / 11 |
| Franja de 30 minutos | 1 | 18:00 † | Referencia (52s) | -0,44 | -1,56 | 11 / 2 |
| Franja de 30 minutos | 3 | 04:00 † | XGBoost | 0,81 | 0,05 | 77 / 47 |
| Franja de 30 minutos | 3 | 05:30 † | XGBoost | 16,95 | -5,89 | 80 / 53 |
| Franja de 30 minutos | 3 | 06:00 † | XGBoost | -3,56 | -6,14 | 80 / 53 |
| Franja de 30 minutos | 3 | 06:30 † | XGBoost | 12,45 | -1,39 | 82 / 54 |
| Franja de 30 minutos | 3 | 07:30 † | XGBoost | 8,29 | 1,51 | 94 / 64 |
| Franja de 30 minutos | 3 | 08:30 † | XGBoost | 5,33 | 1,22 | 92 / 63 |
| Franja de 30 minutos | 3 | 09:30 † | Combinada (26s/52s) | 8,56 | 9,75 | 90 / 63 |
| Franja de 30 minutos | 3 | 10:00 † | XGBoost | 3,54 | -0,45 | 92 / 60 |
| Franja de 30 minutos | 3 | 10:30 † | Referencia (26s) | 4,41 | 2,50 | 92 / 63 |
| Franja de 30 minutos | 3 | 12:00 † | XGBoost | -1,71 | -2,01 | 92 / 62 |
| Franja de 30 minutos | 3 | 12:30 † | XGBoost | 3,46 | 1,08 | 87 / 61 |
| Franja de 30 minutos | 3 | 14:00 † | XGBoost | 9,53 | 10,18 | 91 / 62 |
| Franja de 30 minutos | 3 | 14:30 † | XGBoost | 5,51 | -1,77 | 88 / 59 |
| Franja de 30 minutos | 3 | 15:00 † | XGBoost | 3,88 | 3,82 | 86 / 60 |
| Franja de 30 minutos | 3 | 15:30 † | XGBoost | 12,31 | 5,00 | 85 / 53 |
| Franja de 30 minutos | 3 | 17:00 † | XGBoost | 5,18 | 2,42 | 53 / 31 |
| Franja de 30 minutos | 3 | 17:30 † | Referencia (52s) | 1,29 | 12,78 | 15 / 4 |
| Franja de 30 minutos | 3 | 18:00 † | Referencia (52s) | 0,67 | -1,57 | 1 / 1 |
| Franja de 30 minutos | ambas | 04:00 † | XGBoost | 0,81 | 0,05 | 77 / 47 |
| Franja de 30 minutos | ambas | 06:00 | XGBoost | 3,84 | -0,79 | 160 / 105 |
| Franja de 30 minutos | ambas | 06:30 | XGBoost | 6,97 | -0,72 | 163 / 109 |
| Franja de 30 minutos | ambas | 07:30 | XGBoost | 6,85 | -0,98 | 188 / 126 |
| Franja de 30 minutos | ambas | 08:00 | XGBoost | 4,99 | 1,43 | 186 / 130 |
| Franja de 30 minutos | ambas | 08:30 | XGBoost | 5,78 | -1,01 | 189 / 126 |
| Franja de 30 minutos | ambas | 09:00 | XGBoost | 1,94 | -1,39 | 182 / 123 |
| Franja de 30 minutos | ambas | 09:30 | Combinada (26s/52s) | 8,22 | 9,31 | 183 / 123 |
| Franja de 30 minutos | ambas | 10:30 | Referencia (26s) | 3,57 | 2,38 | 188 / 122 |
| Franja de 30 minutos | ambas | 12:00 | XGBoost | 2,12 | -1,49 | 182 / 124 |
| Franja de 30 minutos | ambas | 12:30 | XGBoost | 3,28 | 4,32 | 179 / 119 |
| Franja de 30 minutos | ambas | 13:00 | XGBoost | 2,48 | 1,73 | 181 / 117 |
| Franja de 30 minutos | ambas | 14:00 | XGBoost | 8,30 | 5,53 | 180 / 117 |
| Franja de 30 minutos | ambas | 14:30 | XGBoost | 5,57 | 2,18 | 178 / 116 |
| Franja de 30 minutos | ambas | 15:00 | XGBoost | 5,27 | 0,65 | 173 / 118 |
| Franja de 30 minutos | ambas | 15:30 | XGBoost | 7,53 | 1,21 | 168 / 106 |
| Tipo de dia | 1 | LABORAL | XGBoost | 7,90 | 2,50 | 1738 / 1084 |
| Tipo de dia | 1 | DOMINGO † | XGBoost | 0,62 | 1,87 | 188 / 97 |
| Tipo de dia | 1 | FESTIVO † | Combinada (26s/52s) = Referencia (52s) | 10,04 | 0,59 | 10 / 40 |
| Tipo de dia | 1 | FESTIVO_PUENTE † | Referencia (26s) | 2,03 | 0,95 | 29 / 21 |
| Tipo de dia | 3 | LABORAL | XGBoost | 7,14 | 1,54 | 1764 / 1131 |
| Tipo de dia | 3 | SABADO | XGBoost | 7,47 | 2,99 | 346 / 244 |
| Tipo de dia | 3 | DOMINGO | XGBoost | -0,14 | 1,31 | 174 / 110 |
| Tipo de dia | 3 | FESTIVO † | Combinada (26s/52s) = Referencia (52s) | 10,94 | 1,49 | 9 / 48 |
| Tipo de dia | ambas | LABORAL | XGBoost | 7,52 | 2,01 | 3502 / 2215 |
| Tipo de dia | ambas | SABADO | XGBoost | 8,45 | 3,47 | 694 / 485 |
| Tipo de dia | ambas | DOMINGO | XGBoost | 0,26 | 1,57 | 362 / 207 |
| Tipo de dia | ambas | FESTIVO † | Combinada (26s/52s) = Referencia (52s) | 10,47 | 1,08 | 19 / 88 |
| Tipo de dia | ambas | FESTIVO_PUENTE † | Referencia (26s) | 1,49 | 2,27 | 60 / 43 |
| Regimen | 1 | ordinario | XGBoost | 7,54 | 2,70 | 2274 / 1422 |
| Regimen | 1 | raro † | Combinada (26s/52s) = Referencia (52s) | 5,44 | 1,62 | 39 / 61 |
| Regimen | 3 | ordinario | XGBoost | 6,63 | 1,76 | 2284 / 1485 |
| Regimen | ambas | ordinario | XGBoost | 7,08 | 2,22 | 4558 / 2907 |
| Regimen | ambas | raro † | Combinada (26s/52s) = Referencia (52s) | 5,56 | 1,74 | 79 / 131 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 1 | N1 (bajo) | Referencia (26s) | 4,68 | 4,18 | 579 / 484 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 1 | N3 (medio-alto) | XGBoost | 9,42 | 0,59 | 578 / 471 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 1 | N4 (alto) | XGBoost | 6,68 | -1,87 | 578 / 194 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 3 | N3 (medio-alto) | XGBoost | 3,50 | 1,14 | 581 / 264 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | 3 | N4 (alto) | XGBoost | 6,72 | -4,25 | 581 / 288 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | ambas | N3 (medio-alto) | XGBoost | 6,45 | 0,79 | 1159 / 735 |
| Nivel de demanda esperada (cuartiles de la referencia 26s) | ambas | N4 (alto) | XGBoost | 6,70 | -3,29 | 1159 / 482 |
| Nivel de demanda observada (descriptivo) | 1 | N1 (bajo) | XGBoost | 29,04 | 26,87 | 583 / 407 |
| Nivel de demanda observada (descriptivo) | 1 | N2 (medio-bajo) | XGBoost | 24,95 | 17,95 | 574 / 365 |
| Nivel de demanda observada (descriptivo) | 1 | N3 (medio-alto) | XGBoost | 4,31 | -0,82 | 596 / 388 |
| Nivel de demanda observada (descriptivo) | 1 | N4 (alto) | Referencia (52s) | -19,59 | -26,81 | 560 / 323 |
| Nivel de demanda observada (descriptivo) | 3 | N2 (medio-bajo) | XGBoost | 26,12 | 19,37 | 590 / 399 |
| Nivel de demanda observada (descriptivo) | 3 | N4 (alto) | Referencia (52s) | -11,37 | -15,12 | 579 / 369 |
| Nivel de demanda observada (descriptivo) | ambas | N2 (medio-bajo) | XGBoost | 25,54 | 18,69 | 1164 / 764 |
| Nivel de demanda observada (descriptivo) | ambas | N4 (alto) | Referencia (52s) | -15,41 | -20,58 | 1139 / 692 |
| Bloque horario x regimen | 1 | pico manana (05:00-06:59) x ordinario | XGBoost | 7,27 | 0,42 | 319 / 210 |
| Bloque horario x regimen | 1 | manana (07:00-09:59) x ordinario | XGBoost | 5,70 | 0,98 | 547 / 345 |
| Bloque horario x regimen | 1 | manana (07:00-09:59) x raro † | Combinada (26s/52s) = Referencia (52s) | 3,81 | 0,60 | 14 / 22 |
| Bloque horario x regimen | 1 | valle (10:00-13:59) x ordinario | XGBoost | 7,83 | 3,42 | 716 / 450 |
| Bloque horario x regimen | 1 | pico tarde (14:00-15:59) x ordinario | XGBoost | 5,50 | -0,10 | 344 / 214 |
| Bloque horario x regimen | 1 | cierre (16:00 en adelante) x ordinario | XGBoost | 10,81 | 9,51 | 269 / 151 |
| Bloque horario x regimen | 3 | manana (07:00-09:59) x ordinario | XGBoost | 5,46 | 4,27 | 539 / 360 |
| Bloque horario x regimen | 3 | valle (10:00-13:59) x ordinario | XGBoost | 5,44 | 1,56 | 698 / 463 |
| Bloque horario x regimen | 3 | pico tarde (14:00-15:59) x ordinario | XGBoost | 7,71 | 4,08 | 344 / 221 |
| Bloque horario x regimen | ambas | manana (07:00-09:59) x ordinario | XGBoost | 5,58 | 2,66 | 1086 / 705 |
| Bloque horario x regimen | ambas | valle (10:00-13:59) x ordinario | XGBoost | 6,65 | 2,47 | 1414 / 913 |
| Bloque horario x regimen | ambas | pico tarde (14:00-15:59) x ordinario | XGBoost | 6,60 | 2,02 | 688 / 435 |
| Bloque horario x regimen | ambas | cierre (16:00 en adelante) x raro † | Combinada (26s/52s) = Referencia (52s) | 6,03 | -4,56 | 3 / 3 |

## Segmentos presentes en un solo periodo

- Solo validación: ninguno
- Solo evaluación: bloque_x_regimen / 1 / pico manana (05:00-06:59) x raro, bloque_x_regimen / ambas / pico manana (05:00-06:59) x raro
