# XGBoost sin rezagos y predictor mixto en el periodo de validación

Generado por `analisis/35_ablacion_rezagos_validacion.py`.

- Validación: 2025-12-25 a 2026-04-01, 4637 franjas, ruta 1: 97 jornadas (3 de régimen raro), ruta 3: 95 jornadas (3 de régimen raro). Mismas jornadas y franjas que el script 25.
- XGBoost sin rezagos: configuración seleccionada (trial 8) sin reajustar, 26 semanas, 2 de parada temprana, variables de `seleccionar_features` sin los seis rezagos (`dentro_horario_operativo`, `hora_del_dia`, `dia_semana`, `es_fin_semana`, `es_festivo`, `hora_sin`, `hora_cos`, `dia_semana_sin`, `dia_semana_cos`). Árboles por ajuste (mediana): 420.
- Mixto completo / sin rezagos: XGBoost completo en régimen ordinario, XGBoost sin rezagos en régimen raro. Mixto XGBoost / 52s: XGBoost completo en ordinario, referencia de 52 semanas en raro. Combinada: 26 s en ordinario, 52 s en raro.
- Dentro de cada régimen, cada mixto coincide con uno de sus componentes; en régimen ordinario los dos mixtos son idénticos a XGBoost completo.
- Sesgo = predicción − real. WAPE = 100·Σ|error| / Σreal. ◆ = menor MAE del grupo.
- Verificación: el reajuste de XGBoost completo en la primera jornada de cada ruta reproduce lo persistido (diferencia máxima ruta 1: 1.8e-06, ruta 3: 1.4e-06); el MAE global de XGBoost completo, la combinada y la referencia de 26 s coincide con `metricas__referencia_combinada_regimen__validacion.csv` (sí).

## Global

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| ambas | todos | XGBoost completo | 4637 / 192 | 29,07 | 22,66 | 7,16 | 25,7 |
| ambas | todos | XGBoost sin rezagos | 4637 / 192 | 29,16 | 22,74 | 10,14 | 25,8 |
| ambas | todos | Mixto completo / sin rezagos | 4637 / 192 | 29,06 | 22,64 | 7,16 | 25,7 |
| ambas | todos | Mixto XGBoost / 52s ◆ | 4637 / 192 | 28,99 | 22,47 | 7,06 | 25,7 |
| ambas | todos | Combinada (26s/52s) | 4637 / 192 | 29,00 | 22,12 | 10,19 | 25,7 |
| ambas | todos | Referencia (26s) | 4637 / 192 | 29,03 | 22,16 | 10,19 | 25,7 |

## Por ruta

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| 1 | todos | XGBoost completo | 2313 / 97 | 26,83 | 21,24 | 7,57 | 25,9 |
| 1 | todos | XGBoost sin rezagos | 2313 / 97 | 27,05 | 21,22 | 9,96 | 26,1 |
| 1 | todos | Mixto completo / sin rezagos | 2313 / 97 | 26,83 | 21,26 | 7,58 | 25,9 |
| 1 | todos | Mixto XGBoost / 52s ◆ | 2313 / 97 | 26,77 | 21,12 | 7,50 | 25,9 |
| 1 | todos | Combinada (26s/52s) | 2313 / 97 | 26,93 | 20,78 | 9,68 | 26,0 |
| 1 | todos | Referencia (26s) | 2313 / 97 | 27,00 | 20,83 | 9,73 | 26,1 |
| 3 | todos | XGBoost completo | 2324 / 95 | 31,31 | 24,48 | 6,76 | 25,6 |
| 3 | todos | XGBoost sin rezagos | 2324 / 95 | 31,26 | 24,40 | 10,32 | 25,6 |
| 3 | todos | Mixto completo / sin rezagos | 2324 / 95 | 31,28 | 24,44 | 6,74 | 25,6 |
| 3 | todos | Mixto XGBoost / 52s | 2324 / 95 | 31,20 | 24,14 | 6,62 | 25,5 |
| 3 | todos | Combinada (26s/52s) | 2324 / 95 | 31,07 | 23,86 | 10,69 | 25,4 |
| 3 | todos | Referencia (26s) ◆ | 2324 / 95 | 31,05 | 23,94 | 10,65 | 25,4 |

## Por régimen

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| ambas | ordinario | XGBoost completo ◆ | 4558 / 186 | 29,30 | 23,01 | 7,08 | 25,6 |
| ambas | ordinario | XGBoost sin rezagos | 4558 / 186 | 29,40 | 23,14 | 10,12 | 25,7 |
| ambas | ordinario | Mixto completo / sin rezagos ◆ | 4558 / 186 | 29,30 | 23,01 | 7,08 | 25,6 |
| ambas | ordinario | Mixto XGBoost / 52s ◆ | 4558 / 186 | 29,30 | 23,01 | 7,08 | 25,6 |
| ambas | ordinario | Combinada (26s/52s) | 4558 / 186 | 29,31 | 22,44 | 10,27 | 25,6 |
| ambas | ordinario | Referencia (26s) | 4558 / 186 | 29,31 | 22,44 | 10,27 | 25,6 |
| ambas | raro | XGBoost completo | 79 / 6 | 16,03 | 13,05 | 11,74 | 59,9 |
| ambas | raro | XGBoost sin rezagos | 79 / 6 | 15,34 | 14,31 | 11,39 | 57,3 |
| ambas | raro | Mixto completo / sin rezagos | 79 / 6 | 15,34 | 14,31 | 11,39 | 57,3 |
| ambas | raro | Mixto XGBoost / 52s ◆ | 79 / 6 | 11,17 | 10,33 | 5,56 | 41,7 |
| ambas | raro | Combinada (26s/52s) ◆ | 79 / 6 | 11,17 | 10,33 | 5,56 | 41,7 |
| ambas | raro | Referencia (26s) | 79 / 6 | 12,62 | 10,00 | 5,91 | 47,1 |

## Por ruta y régimen

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| 1 | ordinario | XGBoost completo ◆ | 2274 / 94 | 27,05 | 21,46 | 7,54 | 25,8 |
| 1 | ordinario | XGBoost sin rezagos | 2274 / 94 | 27,27 | 21,48 | 9,96 | 26,0 |
| 1 | ordinario | Mixto completo / sin rezagos ◆ | 2274 / 94 | 27,05 | 21,46 | 7,54 | 25,8 |
| 1 | ordinario | Mixto XGBoost / 52s ◆ | 2274 / 94 | 27,05 | 21,46 | 7,54 | 25,8 |
| 1 | ordinario | Combinada (26s/52s) | 2274 / 94 | 27,21 | 21,05 | 9,76 | 25,9 |
| 1 | ordinario | Referencia (26s) | 2274 / 94 | 27,21 | 21,05 | 9,76 | 25,9 |
| 1 | raro | XGBoost completo | 39 / 3 | 13,86 | 11,56 | 9,58 | 51,9 |
| 1 | raro | XGBoost sin rezagos | 39 / 3 | 14,20 | 12,74 | 10,03 | 53,2 |
| 1 | raro | Mixto completo / sin rezagos | 39 / 3 | 14,20 | 12,74 | 10,03 | 53,2 |
| 1 | raro | Mixto XGBoost / 52s ◆ | 39 / 3 | 10,56 | 10,88 | 5,44 | 39,5 |
| 1 | raro | Combinada (26s/52s) ◆ | 39 / 3 | 10,56 | 10,88 | 5,44 | 39,5 |
| 1 | raro | Referencia (26s) | 39 / 3 | 14,43 | 10,50 | 8,48 | 54,0 |
| 3 | ordinario | XGBoost completo | 2284 / 92 | 31,54 | 24,75 | 6,63 | 25,4 |
| 3 | ordinario | XGBoost sin rezagos | 2284 / 92 | 31,51 | 24,63 | 10,28 | 25,4 |
| 3 | ordinario | Mixto completo / sin rezagos | 2284 / 92 | 31,54 | 24,75 | 6,63 | 25,4 |
| 3 | ordinario | Mixto XGBoost / 52s | 2284 / 92 | 31,54 | 24,75 | 6,63 | 25,4 |
| 3 | ordinario | Combinada (26s/52s) ◆ | 2284 / 92 | 31,40 | 24,33 | 10,78 | 25,3 |
| 3 | ordinario | Referencia (26s) ◆ | 2284 / 92 | 31,40 | 24,33 | 10,78 | 25,3 |
| 3 | raro | XGBoost completo | 40 / 3 | 18,14 | 16,36 | 13,85 | 67,6 |
| 3 | raro | XGBoost sin rezagos | 40 / 3 | 16,45 | 14,76 | 12,72 | 61,3 |
| 3 | raro | Mixto completo / sin rezagos | 40 / 3 | 16,45 | 14,76 | 12,72 | 61,3 |
| 3 | raro | Mixto XGBoost / 52s | 40 / 3 | 11,76 | 9,12 | 5,66 | 43,8 |
| 3 | raro | Combinada (26s/52s) | 40 / 3 | 11,76 | 9,12 | 5,66 | 43,8 |
| 3 | raro | Referencia (26s) ◆ | 40 / 3 | 10,86 | 9,75 | 3,41 | 40,5 |
