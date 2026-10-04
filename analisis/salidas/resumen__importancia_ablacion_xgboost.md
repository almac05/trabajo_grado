# Importancia, ablación de rezagos y redundancia de las variables de XGBoost

Generado por `analisis/34_importancia_ablacion_xgboost.py`.

- Freeze `freeze_20260922_203820`, 134 jornadas comunes, un ajuste diario por jornada y ruta: ruta 1: 66 ajustes, ruta 3: 68 ajustes.
- Protocolo de la reevaluación del freeze: 26 semanas de entrenamiento, las 2 últimas para parada temprana, configuración seleccionada por la búsqueda (trial 8).
- Verificación: el reajuste reproduce las predicciones del freeze (diferencia máxima 1.5e-05); el MAE global de XGBoost completo y de la referencia de 26 s coincide con `metricas__comparacion_modelos__freeze_20260922_203820__global.csv`.

## 1. Importancia por ganancia total

Ganancia total de cada variable como porcentaje de la ganancia total del ajuste, promediada sobre los ajustes diarios de cada ruta (entre paréntesis, desviación estándar entre ajustes).

### Por concepto

| Concepto | Ruta 1 (%) | Ruta 3 (%) |
|---|---|---|
| Hora | 19,9 (0,8) | 29,0 (1,6) |
| Dia de la semana | 25,9 (1,4) | 17,3 (1,3) |
| Festivo y fin de semana | 22,0 (1,9) | 14,3 (1,3) |
| Rezagos de demanda | 17,1 (2,1) | 30,3 (1,1) |
| Rezagos de productividad | 15,1 (1,7) | 9,0 (2,4) |
| Horario operativo (constante) | 0,0 (0,0) | 0,0 (0,0) |

### Por variable

| Variable | Ruta 1 (%) | Ruta 3 (%) |
|---|---|---|
| `dia_semana` | 19,5 (1,2) | 12,8 (1,0) |
| `es_festivo` | 11,3 (1,3) | 9,2 (1,0) |
| `es_fin_semana` | 10,7 (0,8) | 5,1 (0,5) |
| `pasajeros_total_lag_336` | 8,3 (1,2) | 18,8 (1,0) |
| `hora_del_dia` | 8,0 (0,4) | 6,6 (0,4) |
| `hora_sin` | 7,9 (0,5) | 13,5 (1,1) |
| `pasajeros_por_despacho_lag_336` | 7,7 (0,4) | 2,9 (0,8) |
| `dia_semana_sin` | 5,0 (0,3) | 3,1 (0,2) |
| `pasajeros_total_lag_48` | 4,7 (0,8) | 6,3 (0,6) |
| `pasajeros_total_lag_96` | 4,1 (0,8) | 5,3 (0,9) |
| `hora_cos` | 4,0 (0,3) | 8,9 (0,4) |
| `pasajeros_por_despacho_lag_48` | 4,0 (0,7) | 3,3 (0,8) |
| `pasajeros_por_despacho_lag_96` | 3,4 (0,8) | 2,9 (0,8) |
| `dia_semana_cos` | 1,5 (0,2) | 1,3 (0,2) |
| `dentro_horario_operativo` | 0,0 (0,0) | 0,0 (0,0) |

## 2. Ablación: XGBoost sin los seis rezagos

Mismo protocolo y misma configuración de hiperparámetros, sin reajustarlos, con las 9 variables restantes (calendario, hora y codificaciones cíclicas; una de ellas, `dentro_horario_operativo`, es constante). Árboles por ajuste (mediana): completo 436, sin rezagos 514.

| Desagregación | Ruta | Régimen | Método | n / jornadas | MAE | MedAE | Sesgo | WAPE % |
|---|---|---|---|---|---|---|---|---|
| global | ambas | todos | XGBoost completo | 3038 / 134 | 28,34 | 21,96 | 2,34 | 26,0 |
| global | ambas | todos | XGBoost sin rezagos | 3038 / 134 | 27,70 | 21,32 | 5,79 | 25,4 |
| global | ambas | todos | Referencia (26s) | 3038 / 134 | 28,36 | 21,88 | 6,26 | 26,0 |
| por_ruta | 1 | todos | XGBoost completo | 1483 / 66 | 26,92 | 21,84 | 2,81 | 26,8 |
| por_ruta | 1 | todos | XGBoost sin rezagos | 1483 / 66 | 26,24 | 20,23 | 6,15 | 26,1 |
| por_ruta | 1 | todos | Referencia (26s) | 1483 / 66 | 26,96 | 21,75 | 6,12 | 26,8 |
| por_ruta | 3 | todos | XGBoost completo | 1555 / 68 | 29,70 | 22,07 | 1,89 | 25,3 |
| por_ruta | 3 | todos | XGBoost sin rezagos | 1555 / 68 | 29,09 | 22,41 | 5,46 | 24,8 |
| por_ruta | 3 | todos | Referencia (26s) | 1555 / 68 | 29,69 | 22,31 | 6,39 | 25,3 |
| por_regimen | ambas | ordinario | XGBoost completo | 2907 / 124 | 29,03 | 22,80 | 2,22 | 25,8 |
| por_regimen | ambas | ordinario | XGBoost sin rezagos | 2907 / 124 | 28,41 | 22,39 | 6,01 | 25,2 |
| por_regimen | ambas | ordinario | Referencia (26s) | 2907 / 124 | 28,50 | 22,47 | 6,04 | 25,3 |
| por_regimen | ambas | raro | XGBoost completo | 131 / 10 | 13,05 | 12,52 | 5,03 | 44,5 |
| por_regimen | ambas | raro | XGBoost sin rezagos | 131 / 10 | 11,88 | 9,84 | 1,07 | 40,5 |
| por_regimen | ambas | raro | Referencia (26s) | 131 / 10 | 25,18 | 12,00 | 11,03 | 85,8 |

## 3. Redundancia entre predictoras (Spearman)

Figura: `figura_spearman__importancia_ablacion_xgboost.png`. Matriz completa: `spearman__importancia_ablacion_xgboost.csv`. Franjas de 2025-10-02 a 2026-06-11. Describe la redundancia entre variables que codifican la misma información, no su relación con la demanda.

Pares con |ρ| ≥ 0,7 en alguna ruta:

| Variable 1 | Variable 2 | ρ ruta 1 | ρ ruta 3 |
|---|---|---|---|
| `hora_del_dia` | `hora_sin` | −0,98 | −0,97 |
| `dia_semana` | `es_fin_semana` | 0,74 | 0,74 |
| `dia_semana_sin` | `es_fin_semana` | −0,74 | −0,74 |
