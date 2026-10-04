# Barrido de ventana de XGBoost en validación con hiperparámetros seleccionados

Generado por `analisis/31_barrido_ventana_validacion_hparam.py`.

- Periodo: validación de la búsqueda, 2025-12-25 a 2026-04-01 (extremos inclusivos).
- Jornadas por ventana: 192 (ruta 1: 97, ruta 3: 95).
- Hiperparámetros: trial seleccionado de `seleccion__xgboost.json` sobre los fijos `XGBOOST_FIJOS`: `max_depth=4`, `min_child_weight=7`, `learning_rate=0.01609`, `subsample=0.68`, `colsample_bytree=0.6029`, `reg_lambda=3.748`, `reg_alpha=0.09875`.
- Protocolo: reentrenamiento diario, 2 semanas finales de la ventana para parada temprana, mismo ajuste que la búsqueda (`ajustar_predecir_xgboost`).
- Métricas ponderadas por observaciones (sobre todas las franjas). Sesgo = predicción − real.

**Verificación:** con 26 semanas el barrido reproduce la evaluación del trial seleccionado en la búsqueda: MAE 29.072856 frente a 29.072856; sesgo 7.163164 frente a 7.163164 (coincide).

## MAE ponderado por ventana

| Ventana | Global | Ruta 1 | Ruta 3 | Sesgo global |
|---|---|---|---|---|
| 8 | 30,79 | 28,39 | 33,17 | 0,94 |
| 13 | 29,39 | 27,27 | 31,50 | 2,53 |
| 26 (mínimo) | 29,07 | 26,83 | 31,31 | 7,16 |
| 52 | 29,61 | 27,41 | 31,80 | 11,27 |
| Completo | 31,03 | 28,84 | 33,21 | 15,58 |

Menor MAE global: ventana de 26 semanas (29,07).

## Sesgo ponderado por ventana y tipo de día, ruta 1

| Ventana | LABORAL (66) | SABADO (14) | DOMINGO (14) | FESTIVO (1) | FESTIVO_PUENTE (2) |
|---|---|---|---|---|---|
| 8 | -1,34 | 7,74 | 5,00 | 29,27 | 58,71 |
| 13 | 2,20 | 7,84 | 2,76 | 34,82 | 6,93 |
| 26 | 7,90 | 9,43 | 0,62 | 12,99 | 8,41 |
| 52 | 12,54 | 10,28 | -0,24 | 31,42 | 6,20 |
| Completo | 17,53 | 15,40 | 0,32 | 16,12 | 4,26 |

## Sesgo ponderado por ventana y tipo de día, ruta 3

| Ventana | LABORAL (66) | SABADO (14) | DOMINGO (12) | FESTIVO (1) | FESTIVO_PUENTE (2) |
|---|---|---|---|---|---|
| 8 | -2,55 | 7,20 | 4,04 | 34,90 | 66,72 |
| 13 | 0,64 | 5,91 | 1,14 | 24,62 | 16,23 |
| 26 | 7,14 | 7,47 | -0,14 | 35,96 | 7,43 |
| 52 | 12,85 | 9,87 | -1,06 | 35,58 | 6,94 |
| Completo | 17,52 | 12,94 | 0,50 | 32,11 | 9,50 |

## Patrón de sesgo frente al barrido original

Barrido original: `barrido_ventana_diario.csv` (2026-04-02 a 2026-06-10, `PARAMS_XGB`, 137 jornadas, dataset anterior a la corrección PASAJEROS_REALES). Dirección = signo del cambio del sesgo entre 8 semanas y registro completo. «Ventana |sesgo| mín.» = ventana con el sesgo más cercano a cero.

| Ruta | Tipo de día | Jornadas (val. / orig.) | Sesgo 8 → completo (val.) | Sesgo 8 → completo (orig.) | Dirección (val. / orig.) | Ventana |sesgo| mín. (val. / orig.) |
|---|---|---|---|---|---|---|
| 1 | LABORAL | 66 / 44 | -1,34 → 17,53 | -0,93 → 16,95 | sube / sube | 8 / 8 |
| 1 | SABADO | 14 / 10 | 7,74 → 15,40 | 1,01 → 13,12 | sube / sube | 8 / 8 |
| 1 | DOMINGO | 14 / 9 | 5,00 → 0,32 | 1,93 → 2,41 | baja / sube | 52 / 13 |
| 1 | FESTIVO | 1 / 3 | 29,27 → 16,12 | 51,56 → 2,20 | baja / baja | 26 / 26 |
| 1 | FESTIVO_PUENTE | 2 / 2 | 58,71 → 4,26 | 8,06 → 3,05 | baja / baja | Completo / 13 |
| 3 | LABORAL | 66 / 44 | -2,55 → 17,52 | -1,97 → 17,35 | sube / sube | 13 / 13 |
| 3 | SABADO | 14 / 10 | 7,20 → 12,94 | 4,46 → 12,43 | sube / sube | 13 / 13 |
| 3 | DOMINGO | 12 / 10 | 4,04 → 0,50 | 3,23 → 2,71 | baja / baja | 26 / 13 |
| 3 | FESTIVO | 1 / 3 | 34,90 → 32,11 | 68,21 → 5,24 | baja / baja | 13 / 52 |
| 3 | FESTIVO_PUENTE | 2 / 2 | 66,72 → 9,50 | 8,92 → 2,76 | baja / baja | 52 / Completo |
