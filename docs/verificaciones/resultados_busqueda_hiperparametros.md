# Resultados de la búsqueda de hiperparámetros (seis métodos)

## Protocolo

- **Período de validación:** 2025‑12‑25 a 2026‑04‑01 (termina antes del inicio
  del período de evaluación comparativa, 2026‑04‑02, y no interviene en
  ninguna decisión de ese período). Composición: 98 jornadas por ruta,
  incluyendo 4 jornadas festivas (2 FESTIVO, 2 FESTIVO_PUENTE).
- **Búsqueda:** aleatoria, `n_iter = 10` configuraciones por método, semilla
  `42` (independiente por método).
- **Criterio de selección:** MAE agregado sobre el período de validación
  (único criterio). El sesgo y el desglose por ruta/tipo de día se reportan
  como información adicional, no intervienen en la elección.
- **Protocolo de particiones/reentrenamiento:** idéntico al de la evaluación
  comparativa (ventana deslizante de 26 semanas para SARIMA/Prophet/XGBoost y
  52 semanas para LSTM/GRU/CNN‑LSTM, reentrenamiento diario), aplicado al
  período de validación en vez del período de evaluación.
- **Artefactos completos:** `analisis/salidas/busqueda_hiperparametros/`
  (`espacio__<metodo>.json`, `configuraciones__<metodo>.csv`,
  `seleccion__<metodo>.json` por método). Este archivo es un resumen legible;
  las tablas completas están en los CSV.
- No se modificó ningún script ni artefacto de la evaluación comparativa
  (período 2026‑04‑02 a 2026‑06‑10) ni el freeze existente.

## Resumen comparativo — configuración seleccionada por método

| Método | MAE (validación) | Sesgo | Hiperparámetros seleccionados |
|---|---|---|---|
| SARIMA | 46.77 | −2.01 | p=0, q=0, P=1, Q=1 (d=0, D=0, s=27 fijos) |
| Prophet | 30.53 | +0.65 | changepoint_prior_scale=0.171, seasonality_prior_scale=0.785, holidays_prior_scale=1.880, seasonality_mode=multiplicative, changepoint_range=0.946 |
| XGBoost | 29.07 | +7.16 | max_depth=4, min_child_weight=7, learning_rate=0.0161, subsample=0.680, colsample_bytree=0.603, reg_lambda=3.748, reg_alpha=0.099 |
| LSTM | 28.92 | +5.62 | unidades=64, lr=0.00714, paciencia=30 (pasos=28 fijo) |
| GRU | 28.93 | +5.07 | unidades=128, lr=0.00442, paciencia=30 (pasos=28 fijo) |
| **CNN‑LSTM** | **28.66** | +4.38 | unidades=128, lr=0.00442, paciencia=30, filtros=32, núcleo=3 (pasos=28 fijo) |

CNN‑LSTM obtiene el MAE más bajo, pero LSTM, GRU, CNN‑LSTM y XGBoost quedan
muy próximos entre sí (28.7–29.1). SARIMA queda claramente por detrás (46.8).
XGBoost y las tres redes muestran sesgo positivo (sobre‑predicen en
promedio, +4 a +7); Prophet y SARIMA quedan cerca de cero o negativo.

---

## SARIMA

**Espacio buscado:** p∈[0,2], q∈[0,2], P∈[0,1], Q∈[0,1] (acotado tras medir
un costo de ajuste MLE muy superior al calibrado con órdenes P,Q=2 y s=27;
ver `espacio__sarima.json`). **Fijos:** d=0, D=0, s=27.

| trial | p | q | P | Q | MAE | Sesgo | RMSE | WAPE | s/config |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 2 | 1 | 0 | 54.17 | −32.95 | 70.69 | 47.96 | 1342.0 |
| 1 | 1 | 2 | 0 | 1 | 57.03 | −42.06 | 76.96 | 50.49 | 1093.6 |
| **2** | **0** | **0** | **1** | **1** | **46.77** | **−2.01** | **60.09** | **41.41** | 1011.4 |
| 3 | 2 | 2 | 1 | 1 | 55.19 | −39.68 | 74.38 | 48.86 | 1520.5 |
| 4 | 1 | 0 | 1 | 0 | 86.73 | −85.56 | 103.59 | 76.78 | 368.1 |
| 5 | 1 | 1 | 0 | 1 | 58.73 | −44.90 | 78.87 | 51.99 | 568.3 |
| 6 | 2 | 1 | 0 | 1 | 55.69 | −35.73 | 74.85 | 49.31 | 718.2 |
| 7 | 1 | 1 | 0 | 0 | 67.33 | −55.46 | 89.00 | 59.61 | 52.8 |
| 8 | 0 | 1 | 1 | 0 | 52.78 | −25.54 | 69.06 | 46.72 | 266.5 |
| 9 | 2 | 2 | 0 | 1 | 60.23 | −47.52 | 80.48 | 53.32 | 703.4 |

**Seleccionada (trial 2):** p=0, q=0, P=1, Q=1. MAE por ruta: ruta 1 = 39.50,
ruta 3 = 54.01. MAE por tipo de día: DOMINGO 80.40, FESTIVO 99.12,
FESTIVO_PUENTE 70.05, LABORAL 43.69, SABADO 41.37. El modelo seleccionado es,
en esencia, puramente estacional (sin componentes autorregresivos/de media
móvil no estacionales); el desempeño en jornadas festivas es notablemente
peor que en laborales, consistente con la ausencia de un mecanismo explícito
para tipo de día en SARIMA.

## Prophet

**Espacio buscado:** changepoint_prior_scale ∈ [0.001, 0.5] (log‑uniforme),
seasonality_prior_scale ∈ [0.01, 10] (log‑uniforme), holidays_prior_scale ∈
[0.01, 10] (log‑uniforme), seasonality_mode ∈ {additive, multiplicative},
changepoint_range ∈ [0.8, 0.95]. **Fijos:** daily/weekly_seasonality=True,
yearly_seasonality=False, calendario de festivos.

| trial | changepoint_prior_scale | seasonality_prior_scale | holidays_prior_scale | seasonality_mode | changepoint_range | MAE | Sesgo | RMSE | WAPE |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.1227 | 0.2073 | 3.7652 | additive | 0.814 | 31.00 | +0.13 | 39.90 | 27.44 |
| 1 | 0.4297 | 1.9205 | 2.2814 | multiplicative | 0.819 | 30.64 | −0.19 | 39.66 | 27.13 |
| 2 | 0.0164 | 0.1295 | 6.0297 | multiplicative | 0.923 | 30.90 | −0.11 | 40.07 | 27.36 |
| 3 | 0.0157 | 0.0481 | 0.4611 | multiplicative | 0.810 | 31.72 | +0.50 | 41.00 | 28.08 |
| **4** | **0.1713** | **0.7852** | **1.8805** | **multiplicative** | **0.946** | **30.53** | **+0.65** | **39.39** | **27.03** |
| 5 | 0.2573 | 2.1635 | 0.0384 | additive | 0.870 | 30.89 | −0.04 | 39.72 | 27.35 |
| 6 | 0.0013 | 0.0290 | 1.1198 | multiplicative | 0.945 | 34.20 | +2.05 | 44.05 | 30.28 |
| 7 | 0.0076 | 0.1292 | 0.2563 | multiplicative | 0.828 | 31.02 | −0.35 | 40.22 | 27.46 |
| 8 | 0.0022 | 0.2674 | 0.0479 | multiplicative | 0.866 | 32.42 | +0.69 | 41.81 | 28.71 |
| 9 | 0.1768 | 1.2612 | 0.0865 | multiplicative | 0.925 | 30.76 | +0.51 | 39.72 | 27.24 |

**Seleccionada (trial 4):** ver tabla resumen. MAE por ruta: ruta 1 = 27.67,
ruta 3 = 33.38. MAE por tipo de día: DOMINGO 17.52, FESTIVO 30.66,
FESTIVO_PUENTE 13.26, LABORAL 32.59, SABADO 28.43.

## XGBoost

**Espacio buscado:** max_depth ∈ [3,9], min_child_weight ∈ [1,10],
learning_rate ∈ [0.01, 0.3] (log‑uniforme), subsample ∈ [0.6, 1.0],
colsample_bytree ∈ [0.6, 1.0], reg_lambda ∈ [0.1, 10] (log‑uniforme),
reg_alpha ∈ [0.001, 1] (log‑uniforme). **Fijos:** objective=reg:absoluteerror,
eval_metric=mae, n_estimators=2000 (techo), early_stopping_rounds=50,
random_state=42.

| trial | max_depth | min_child_weight | learning_rate | subsample | colsample_bytree | reg_lambda | reg_alpha | MAE | Sesgo |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 3 | 8 | 0.0445 | 0.943 | 0.879 | 0.154 | 0.845 | 29.12 | +6.75 |
| 1 | 8 | 8 | 0.1449 | 0.651 | 0.780 | 0.552 | 0.603 | 29.77 | +7.70 |
| 2 | 8 | 7 | 0.1642 | 0.777 | 0.691 | 1.286 | 0.0016 | 29.76 | +7.54 |
| 3 | 9 | 9 | 0.0857 | 0.903 | 0.742 | 8.738 | 0.478 | 29.64 | +7.77 |
| 4 | 7 | 8 | 0.0194 | 0.787 | 0.618 | 0.204 | 0.112 | 29.25 | +7.76 |
| 5 | 9 | 8 | 0.2686 | 0.730 | 0.748 | 0.869 | 0.0037 | 30.30 | +7.64 |
| 6 | 6 | 2 | 0.0504 | 0.691 | 0.868 | 0.749 | 0.315 | 29.40 | +7.93 |
| 7 | 7 | 8 | 0.0289 | 0.933 | 0.922 | 0.596 | 0.0073 | 29.31 | +8.09 |
| **8** | **4** | **7** | **0.0161** | **0.680** | **0.603** | **3.748** | **0.099** | **29.07** | **+7.16** |
| 9 | 6 | 8 | 0.1423 | 0.784 | 0.827 | 0.190 | 0.0022 | 29.35 | +7.82 |

**Seleccionada (trial 8):** MAE por ruta: ruta 1 = 26.83, ruta 3 = 31.31.
MAE por tipo de día: DOMINGO 11.13, FESTIVO 23.87, FESTIVO_PUENTE 13.55,
LABORAL 31.70, SABADO 26.66. Todas las configuraciones probadas muestran
sesgo positivo consistente (+6.7 a +8.1), independiente de los
hiperparámetros — sugiere un sesgo estructural del método en este período,
no corregible solo por tuning.

## LSTM

**Espacio buscado:** unidades ∈ {32,64,128}, lr ∈ [1e‑4, 1e‑2]
(log‑uniforme), paciencia ∈ {15,30,50}. **Fijos:** pasos=28, épocas
techo=3000, semilla de inicialización=42.

| trial | unidades | lr | paciencia | MAE | Sesgo | s/config |
|---|---|---|---|---|---|---|
| 0 | 32 | 0.000755 | 50 | 30.86 | +5.70 | 707.8 |
| 1 | 64 | 0.002482 | 50 | 29.46 | +4.99 | 416.4 |
| 2 | 32 | 0.008938 | 15 | 29.56 | +7.06 | 266.9 |
| 3 | 128 | 0.003734 | 50 | 29.22 | +5.92 | 581.2 |
| 4 | 64 | 0.000796 | 15 | 33.76 | +8.02 | 361.0 |
| **5** | **64** | **0.007137** | **30** | **28.92** | **+5.62** | 325.0 |
| 6 | 128 | 0.004421 | 30 | 28.93 | +5.88 | 570.2 |
| 7 | 64 | 0.000285 | 30 | 34.18 | +8.27 | 683.6 |
| 8 | 32 | 0.000134 | 30 | 34.68 | +8.84 | 1079.7 |
| 9 | 128 | 0.001834 | 50 | 29.35 | +5.51 | 851.5 |

**Seleccionada (trial 5):** MAE por ruta: ruta 1 = 26.54, ruta 3 = 31.36.
MAE por tipo de día: DOMINGO 10.16, FESTIVO 21.38, FESTIVO_PUENTE 19.06,
LABORAL 31.88, SABADO 25.27.

## GRU

**Espacio buscado:** idéntico a LSTM (unidades, lr, paciencia).

| trial | unidades | lr | paciencia | MAE | Sesgo | s/config |
|---|---|---|---|---|---|---|
| 0 | 32 | 0.000755 | 50 | 30.04 | +6.65 | 818.7 |
| 1 | 64 | 0.002482 | 50 | 29.29 | +5.15 | 461.6 |
| 2 | 32 | 0.008938 | 15 | 29.38 | +6.22 | 333.2 |
| 3 | 128 | 0.003734 | 50 | 29.23 | +5.11 | 501.1 |
| 4 | 64 | 0.000796 | 15 | 33.15 | +9.08 | 463.6 |
| 5 | 64 | 0.007137 | 30 | 28.93 | +5.12 | 359.5 |
| **6** | **128** | **0.004421** | **30** | **28.93** | **+5.07** | 483.6 |
| 7 | 64 | 0.000285 | 30 | 32.82 | +8.39 | 854.9 |
| 8 | 32 | 0.000134 | 30 | 32.44 | +9.10 | 1767.7 |
| 9 | 128 | 0.001834 | 50 | 29.17 | +4.84 | 660.7 |

**Seleccionada (trial 6):** MAE por ruta: ruta 1 = 26.62, ruta 3 = 31.28.
MAE por tipo de día: DOMINGO 10.04, FESTIVO 17.35, FESTIVO_PUENTE 33.38,
LABORAL 31.62, SABADO 25.53. Nota: el trial 9 tuvo un MAE global apenas por
encima (29.17 vs 28.93 del trial 6) pero con menor sesgo global (+4.84);
el criterio de selección es únicamente el MAE, por lo que el trial 6 es el
seleccionado.

## CNN‑LSTM

**Espacio buscado:** unidades ∈ {32,64,128}, lr ∈ [1e‑4, 1e‑2]
(log‑uniforme), paciencia ∈ {15,30,50}, filtros ∈ {16,32,64},
núcleo ∈ {3,5}. **Fijos:** pasos=28, épocas techo=3000, semilla de
inicialización=42.

| trial | unidades | lr | paciencia | filtros | núcleo | MAE | Sesgo | s/config |
|---|---|---|---|---|---|---|---|---|
| 0 | 32 | 0.000755 | 50 | 32 | 5 | 30.35 | +4.41 | 616.3 |
| 1 | 32 | 0.000154 | 50 | 32 | 5 | 32.53 | +5.75 | 907.6 |
| 2 | 128 | 0.003734 | 50 | 32 | 3 | 28.90 | +4.72 | 702.0 |
| 3 | 128 | 0.000552 | 30 | 16 | 5 | 31.07 | +4.85 | 994.6 |
| **4** | **128** | **0.004421** | **30** | **32** | **3** | **28.66** | **+4.38** | 626.5 |
| 5 | 64 | 0.001286 | 15 | 64 | 3 | 31.76 | +5.85 | 456.2 |
| 6 | 128 | 0.001834 | 50 | 16 | 5 | 28.83 | +4.54 | 838.2 |
| 7 | 128 | 0.008738 | 30 | 32 | 5 | 28.89 | +5.22 | 541.8 |
| 8 | 128 | 0.000245 | 50 | 32 | 3 | 31.58 | +3.92 | 1298.6 |
| 9 | 64 | 0.000204 | 15 | 64 | 5 | 34.92 | +9.30 | 595.9 |

**Seleccionada (trial 4):** MAE por ruta: ruta 1 = 26.54, ruta 3 = 30.84.
MAE por tipo de día: DOMINGO 10.20, FESTIVO 28.91, FESTIVO_PUENTE 10.49,
LABORAL 31.66, SABADO 25.22. Mejor MAE global de los seis métodos.

---

## Advertencia sobre el espacio de SARIMA

El espacio original propuesto para SARIMA (p,q∈[0,3], P,Q∈[0,2]) resultó
computacionalmente intratable: combinaciones con P=2 o Q=2 sobre el período
estacional s=27 dispararon el costo del ajuste MLE muy por encima de lo
calibrado (~121 s/ajuste sostenido, frente a 9.55 s/ajuste en el punto de
referencia). El espacio se acotó a p,q∈[0,2], P,Q∈[0,1] (documentado en
`espacio__sarima.json` y en el comentario de
`src/proyecto_grado/modeling/hparam_search/spaces.py`) antes de correr la
búsqueda reportada aquí. Los resultados de SARIMA reflejan ese espacio
acotado, no el propuesto originalmente.
