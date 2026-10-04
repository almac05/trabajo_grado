# Predictor mixto: XGBoost en régimen ordinario, referencia de 52 semanas en régimen raro

Generado por `analisis/33_predictor_mixto_xgboost_ref52.py`.

- Validación: 2025-12-25 a 2026-04-01. Evaluación: 2026-04-02 a 2026-06-10, 134 jornadas comunes del freeze `freeze_20260922_203820`. Fuente: observaciones del script 25 en ambos periodos.
- Régimen raro = FESTIVO o FESTIVO_PUENTE. Dentro de cada régimen el mixto coincide con XGBoost (ordinario) o con la referencia de 52 s, que es igual a la combinada (raro).
- Métricas sobre observaciones. Sesgo = predicción − real. WAPE = 100·Σ|error| / Σreal. ◆ = menor MAE del grupo (incluye empates).
- Verificación: MAE y n de XGBoost y de las tres referencias reproducen los del script 25 (sí); XGBoost de validación frente al del script 31: diferencia máxima 0.0e+00.

## Validacion

### Global

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| ambas | todos | Mixto (XGBoost ordinario / 52s raro) ◆ | 4637 / 192 | 28,99 | 22,47 | 7,06 | 25,7 |
| ambas | todos | XGBoost | 4637 / 192 | 29,07 | 22,66 | 7,16 | 25,7 |
| ambas | todos | Referencia (26s) | 4637 / 192 | 29,03 | 22,16 | 10,19 | 25,7 |
| ambas | todos | Referencia (52s) | 4637 / 192 | 30,51 | 23,36 | 15,12 | 27,0 |
| ambas | todos | Combinada (26s/52s) | 4637 / 192 | 29,00 | 22,12 | 10,19 | 25,7 |

### Por ruta

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| 1 | todos | Mixto (XGBoost ordinario / 52s raro) ◆ | 2313 / 97 | 26,77 | 21,12 | 7,50 | 25,9 |
| 1 | todos | XGBoost | 2313 / 97 | 26,83 | 21,24 | 7,57 | 25,9 |
| 1 | todos | Referencia (26s) | 2313 / 97 | 27,00 | 20,83 | 9,73 | 26,1 |
| 1 | todos | Referencia (52s) | 2313 / 97 | 28,21 | 21,58 | 14,04 | 27,2 |
| 1 | todos | Combinada (26s/52s) | 2313 / 97 | 26,93 | 20,78 | 9,68 | 26,0 |
| 3 | todos | Mixto (XGBoost ordinario / 52s raro) | 2324 / 95 | 31,20 | 24,14 | 6,62 | 25,5 |
| 3 | todos | XGBoost | 2324 / 95 | 31,31 | 24,48 | 6,76 | 25,6 |
| 3 | todos | Referencia (26s) ◆ | 2324 / 95 | 31,05 | 23,94 | 10,65 | 25,4 |
| 3 | todos | Referencia (52s) | 2324 / 95 | 32,80 | 25,49 | 16,20 | 26,8 |
| 3 | todos | Combinada (26s/52s) | 2324 / 95 | 31,07 | 23,86 | 10,69 | 25,4 |

### Por régimen

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| ambas | ordinario | Mixto (XGBoost ordinario / 52s raro) ◆ | 4558 / 186 | 29,30 | 23,01 | 7,08 | 25,6 |
| ambas | ordinario | XGBoost ◆ | 4558 / 186 | 29,30 | 23,01 | 7,08 | 25,6 |
| ambas | ordinario | Referencia (26s) | 4558 / 186 | 29,31 | 22,44 | 10,27 | 25,6 |
| ambas | ordinario | Referencia (52s) | 4558 / 186 | 30,85 | 23,84 | 15,29 | 27,0 |
| ambas | ordinario | Combinada (26s/52s) | 4558 / 186 | 29,31 | 22,44 | 10,27 | 25,6 |
| ambas | raro | Mixto (XGBoost ordinario / 52s raro) ◆ | 79 / 6 | 11,17 | 10,33 | 5,56 | 41,7 |
| ambas | raro | XGBoost | 79 / 6 | 16,03 | 13,05 | 11,74 | 59,9 |
| ambas | raro | Referencia (26s) | 79 / 6 | 12,62 | 10,00 | 5,91 | 47,1 |
| ambas | raro | Referencia (52s) ◆ | 79 / 6 | 11,17 | 10,33 | 5,56 | 41,7 |
| ambas | raro | Combinada (26s/52s) ◆ | 79 / 6 | 11,17 | 10,33 | 5,56 | 41,7 |

### Por ruta y régimen

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| 1 | ordinario | Mixto (XGBoost ordinario / 52s raro) ◆ | 2274 / 94 | 27,05 | 21,46 | 7,54 | 25,8 |
| 1 | ordinario | XGBoost ◆ | 2274 / 94 | 27,05 | 21,46 | 7,54 | 25,8 |
| 1 | ordinario | Referencia (26s) | 2274 / 94 | 27,21 | 21,05 | 9,76 | 25,9 |
| 1 | ordinario | Referencia (52s) | 2274 / 94 | 28,51 | 22,01 | 14,18 | 27,2 |
| 1 | ordinario | Combinada (26s/52s) | 2274 / 94 | 27,21 | 21,05 | 9,76 | 25,9 |
| 1 | raro | Mixto (XGBoost ordinario / 52s raro) ◆ | 39 / 3 | 10,56 | 10,88 | 5,44 | 39,5 |
| 1 | raro | XGBoost | 39 / 3 | 13,86 | 11,56 | 9,58 | 51,9 |
| 1 | raro | Referencia (26s) | 39 / 3 | 14,43 | 10,50 | 8,48 | 54,0 |
| 1 | raro | Referencia (52s) ◆ | 39 / 3 | 10,56 | 10,88 | 5,44 | 39,5 |
| 1 | raro | Combinada (26s/52s) ◆ | 39 / 3 | 10,56 | 10,88 | 5,44 | 39,5 |
| 3 | ordinario | Mixto (XGBoost ordinario / 52s raro) | 2284 / 92 | 31,54 | 24,75 | 6,63 | 25,4 |
| 3 | ordinario | XGBoost | 2284 / 92 | 31,54 | 24,75 | 6,63 | 25,4 |
| 3 | ordinario | Referencia (26s) ◆ | 2284 / 92 | 31,40 | 24,33 | 10,78 | 25,3 |
| 3 | ordinario | Referencia (52s) | 2284 / 92 | 33,17 | 25,91 | 16,39 | 26,8 |
| 3 | ordinario | Combinada (26s/52s) ◆ | 2284 / 92 | 31,40 | 24,33 | 10,78 | 25,3 |
| 3 | raro | Mixto (XGBoost ordinario / 52s raro) | 40 / 3 | 11,76 | 9,12 | 5,66 | 43,8 |
| 3 | raro | XGBoost | 40 / 3 | 18,14 | 16,36 | 13,85 | 67,6 |
| 3 | raro | Referencia (26s) ◆ | 40 / 3 | 10,86 | 9,75 | 3,41 | 40,5 |
| 3 | raro | Referencia (52s) | 40 / 3 | 11,76 | 9,12 | 5,66 | 43,8 |
| 3 | raro | Combinada (26s/52s) | 40 / 3 | 11,76 | 9,12 | 5,66 | 43,8 |

## Evaluacion

### Global

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| ambas | todos | Mixto (XGBoost ordinario / 52s raro) | 3038 / 134 | 28,32 | 21,97 | 2,20 | 25,9 |
| ambas | todos | XGBoost | 3038 / 134 | 28,34 | 21,96 | 2,34 | 26,0 |
| ambas | todos | Referencia (26s) | 3038 / 134 | 28,36 | 21,88 | 6,26 | 26,0 |
| ambas | todos | Referencia (52s) | 3038 / 134 | 29,34 | 22,91 | 12,50 | 26,9 |
| ambas | todos | Combinada (26s/52s) ◆ | 3038 / 134 | 27,81 | 21,63 | 5,86 | 25,5 |

### Por ruta

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| 1 | todos | Mixto (XGBoost ordinario / 52s raro) | 1483 / 66 | 26,89 | 21,81 | 2,66 | 26,7 |
| 1 | todos | XGBoost | 1483 / 66 | 26,92 | 21,84 | 2,81 | 26,8 |
| 1 | todos | Referencia (26s) | 1483 / 66 | 26,96 | 21,75 | 6,12 | 26,8 |
| 1 | todos | Referencia (52s) | 1483 / 66 | 27,78 | 21,71 | 11,41 | 27,6 |
| 1 | todos | Combinada (26s/52s) ◆ | 1483 / 66 | 26,55 | 21,49 | 5,82 | 26,4 |
| 3 | todos | Mixto (XGBoost ordinario / 52s raro) | 1555 / 68 | 29,69 | 22,16 | 1,76 | 25,3 |
| 3 | todos | XGBoost | 1555 / 68 | 29,70 | 22,07 | 1,89 | 25,3 |
| 3 | todos | Referencia (26s) | 1555 / 68 | 29,69 | 22,31 | 6,39 | 25,3 |
| 3 | todos | Referencia (52s) | 1555 / 68 | 30,82 | 23,81 | 13,54 | 26,3 |
| 3 | todos | Combinada (26s/52s) ◆ | 1555 / 68 | 29,02 | 21,68 | 5,89 | 24,7 |

### Por régimen

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| ambas | ordinario | Mixto (XGBoost ordinario / 52s raro) | 2907 / 124 | 29,03 | 22,80 | 2,22 | 25,8 |
| ambas | ordinario | XGBoost | 2907 / 124 | 29,03 | 22,80 | 2,22 | 25,8 |
| ambas | ordinario | Referencia (26s) ◆ | 2907 / 124 | 28,50 | 22,47 | 6,04 | 25,3 |
| ambas | ordinario | Referencia (52s) | 2907 / 124 | 30,09 | 23,80 | 12,99 | 26,7 |
| ambas | ordinario | Combinada (26s/52s) ◆ | 2907 / 124 | 28,50 | 22,47 | 6,04 | 25,3 |
| ambas | raro | Mixto (XGBoost ordinario / 52s raro) ◆ | 131 / 10 | 12,55 | 10,20 | 1,74 | 42,8 |
| ambas | raro | XGBoost | 131 / 10 | 13,05 | 12,52 | 5,03 | 44,5 |
| ambas | raro | Referencia (26s) | 131 / 10 | 25,18 | 12,00 | 11,03 | 85,8 |
| ambas | raro | Referencia (52s) ◆ | 131 / 10 | 12,55 | 10,20 | 1,74 | 42,8 |
| ambas | raro | Combinada (26s/52s) ◆ | 131 / 10 | 12,55 | 10,20 | 1,74 | 42,8 |

### Por ruta y régimen

| Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|
| 1 | ordinario | Mixto (XGBoost ordinario / 52s raro) | 1422 / 61 | 27,48 | 22,65 | 2,70 | 26,5 |
| 1 | ordinario | XGBoost | 1422 / 61 | 27,48 | 22,65 | 2,70 | 26,5 |
| 1 | ordinario | Referencia (26s) ◆ | 1422 / 61 | 27,12 | 22,00 | 6,00 | 26,2 |
| 1 | ordinario | Referencia (52s) | 1422 / 61 | 28,41 | 22,83 | 11,83 | 27,4 |
| 1 | ordinario | Combinada (26s/52s) ◆ | 1422 / 61 | 27,12 | 22,00 | 6,00 | 26,2 |
| 1 | raro | Mixto (XGBoost ordinario / 52s raro) ◆ | 61 / 5 | 13,20 | 9,60 | 1,62 | 45,0 |
| 1 | raro | XGBoost | 61 / 5 | 13,93 | 13,47 | 5,33 | 47,4 |
| 1 | raro | Referencia (26s) | 61 / 5 | 23,20 | 11,50 | 8,92 | 79,0 |
| 1 | raro | Referencia (52s) ◆ | 61 / 5 | 13,20 | 9,60 | 1,62 | 45,0 |
| 1 | raro | Combinada (26s/52s) ◆ | 61 / 5 | 13,20 | 9,60 | 1,62 | 45,0 |
| 3 | ordinario | Mixto (XGBoost ordinario / 52s raro) | 1485 / 63 | 30,52 | 22,99 | 1,76 | 25,1 |
| 3 | ordinario | XGBoost | 1485 / 63 | 30,52 | 22,99 | 1,76 | 25,1 |
| 3 | ordinario | Referencia (26s) ◆ | 1485 / 63 | 29,82 | 22,89 | 6,08 | 24,6 |
| 3 | ordinario | Referencia (52s) | 1485 / 63 | 31,71 | 24,74 | 14,10 | 26,1 |
| 3 | ordinario | Combinada (26s/52s) ◆ | 1485 / 63 | 29,82 | 22,89 | 6,08 | 24,6 |
| 3 | raro | Mixto (XGBoost ordinario / 52s raro) ◆ | 70 / 5 | 11,98 | 10,53 | 1,84 | 40,8 |
| 3 | raro | XGBoost | 70 / 5 | 12,28 | 12,09 | 4,77 | 41,9 |
| 3 | raro | Referencia (26s) | 70 / 5 | 26,91 | 13,00 | 12,86 | 91,7 |
| 3 | raro | Referencia (52s) ◆ | 70 / 5 | 11,98 | 10,53 | 1,84 | 40,8 |
| 3 | raro | Combinada (26s/52s) ◆ | 70 / 5 | 11,98 | 10,53 | 1,84 | 40,8 |
