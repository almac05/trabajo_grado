# Tablas de verificación: barrido de ventana y referencias por régimen

Generado por `analisis/30_figuras_reunion_ventana.py`. Figuras en `reports/figures/reunion/`.

**Alcance del barrido (figuras 4 y 5):** XGBoost con su configuración anterior a la búsqueda de hiperparámetros (`PARAMS_XGB` de `analisis/13_barrido_ventana_diario.py`), reentrenamiento diario, sobre **137 jornadas** (68 de ruta 1 y 69 de ruta 3) entre el 2026-04-02 y el 2026-06-10. Objetivo del barrido: `pasajeros_total`, anterior a la adopción de `PASAJEROS_REALES`. No es comparable celda a celda con el freeze 20260922_203820 (134 jornadas comunes).

Fuente: `analisis/salidas/barrido_ventana_diario.csv`. Operación: promedio ponderado por `n` (observaciones de la jornada), `sum(métrica × n) / sum(n)`. Ventana «Completo» = código 999.

## MAE ponderado global por ventana y ruta (figura 5)

| Ventana | Ruta 1 (68 jornadas) | Ruta 3 (69 jornadas) | Ambas rutas (137 jornadas) |
|---|---|---|---|
| 8 | 28,93 | 32,81 | 30,89 |
| 13 | 26,95 | 30,54 | 28,77 |
| 26 | 27,12 | 30,09 | 28,63 |
| 52 | 27,61 | 30,27 | 28,96 |
| Completo | 29,90 | 32,70 | 31,32 |

## Sesgo ponderado por ventana y tipo de día, ruta 1 (figura 4)

| Ventana | Laboral (44) | Sábado (10) | Domingo (9) | Festivo (3) | Festivo puente (2) |
|---|---|---|---|---|---|
| 8 | -0,93 | 1,01 | 1,93 | 51,56 | 8,06 |
| 13 | 1,08 | 1,02 | 1,62 | 6,60 | 2,95 |
| 26 | 2,74 | 3,94 | 2,80 | 1,48 | 10,83 |
| 52 | 9,65 | 8,37 | 2,08 | 2,86 | 8,65 |
| Completo | 16,95 | 13,12 | 2,41 | 2,20 | 3,05 |

## Sesgo ponderado por ventana y tipo de día, ruta 3 (figura 4)

| Ventana | Laboral (44) | Sábado (10) | Domingo (10) | Festivo (3) | Festivo puente (2) |
|---|---|---|---|---|---|
| 8 | -1,97 | 4,46 | 3,23 | 68,21 | 8,92 |
| 13 | 0,14 | 1,76 | 0,93 | 17,94 | 6,11 |
| 26 | 1,97 | 4,61 | 2,02 | 4,26 | 4,84 |
| 52 | 9,66 | 6,27 | 1,73 | 4,08 | 2,98 |
| Completo | 17,35 | 12,43 | 2,71 | 5,24 | 2,76 |

## Referencias por régimen, freeze 20260922_203820 (figura 6)

Fuente: `analisis/salidas/metricas__comparacion_modelos__freeze_20260922_203820__regimen.csv`.

| Método | Régimen | MAE | Sesgo |
|---|---|---|---|
| Referencia (26 semanas) | Días normales | 28,50 | 6,04 |
| Referencia (26 semanas) | Festivos | 25,18 | 11,03 |
| Referencia (52 semanas) | Días normales | 30,09 | 12,99 |
| Referencia (52 semanas) | Festivos | 12,55 | 1,74 |
