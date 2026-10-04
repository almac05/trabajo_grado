# Informe de verificación — trazabilidad de cifras del capítulo de implementación y comparación de modelos

**Rama auditada:** `consolidacion-evaluacion`
**Fecha del informe:** 2026-09-17
**Alcance:** verificación de solo lectura. No se ejecutó ningún entrenamiento, no se modificó ni creó ningún archivo del repositorio salvo este informe.

---

## 1. Inventario de ejecuciones

Existen **dos árboles de artefactos paralelos y no equivalentes** en el repositorio: el flujo "oficial" versionado bajo `reports/tables/modeling/` (y sus copias en `models/metadata/backups/`), que solo cubre predictores baseline; y el árbol `analisis/salidas/`, que contiene las ejecuciones reales de XGBoost, Prophet, SARIMA, LSTM, GRU y CNN-LSTM. Las cifras del capítulo de comparación de modelos provienen de este segundo árbol.

### 1.1. Ejecución más reciente y completa: freeze `freeze_20260823_203700`

Ruta base: `analisis/salidas/`. Generada por `scripts/aggregate_comparative_metrics.py` sobre un dataset con hash `218b7e6dc1677e27254f5ddfa0f6b381c7808c4a432782fb8f043137479a9d1c`. **Trackeada en git**, commit `4c79457` ("Consolida el flujo comparativo de seis metodos", 2026-08-30 17:05:48 -0500). Periodo de evaluación: **2026-04-02 04:00 → 2026-06-10 04:00**.

| Artefacto | Método(s) | Filas | Generado (timestamp interno) |
|---|---|---|---|
| `analisis/salidas/predicciones__xgboost__freeze_20260823_203700.csv` | XGBoost | 3117 | 2026-08-26T13:31:32.09 |
| `analisis/salidas/predicciones__prophet__freeze_20260823_203700.csv` | Prophet | 3117 | 2026-08-26T13:35:36.32 |
| `analisis/salidas/predicciones__sarima__freeze_20260823_203700.csv` | SARIMA | 3117 | 2026-08-26T15:22:02.70 |
| `analisis/salidas/predicciones__lstm__freeze_20260823_203700.csv` | LSTM | 3038 | 2026-08-26T14:42:54.83 |
| `analisis/salidas/predicciones__gru__freeze_20260823_203700.csv` | GRU | 3038 | 2026-08-26T14:51:49.35 |
| `analisis/salidas/predicciones__cnn_lstm__freeze_20260823_203700.csv` | CNN-LSTM | 3038 | 2026-08-26T14:59:02.03 |
| `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__global.csv` | 6 métodos + "Referencia (26s)"/"Referencia (52s)" | agregado por ruta | 2026-08-30 (fecha de archivo) |
| `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__tipo_dia.csv` | ídem | agregado por ruta × tipo_dia | 2026-08-30 |
| `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__regimen.csv` | ídem | agregado por ruta × régimen | 2026-08-30 |
| `analisis/salidas/referencia_metricas_pre_consolidacion.csv` | 6 métodos + "Referencia" (valores sin redondear) | agregado | 2026-08-28 10:04 |
| `analisis/salidas/referencia_jornadas_pre_consolidacion.csv` | — (jornadas de soporte común) | **134** (66 ruta 1 + 68 ruta 3) | 2026-08-28 10:05 |
| `analisis/salidas/resumen__xgboost__freeze_20260823_203700.csv` | XGBoost, por jornada | **137** (68 ruta 1 + 69 ruta 3) | 2026-08-30 16:57 |
| `analisis/salidas/resumen__prophet/sarima/lstm/gru/cnn_lstm__freeze_20260823_203700.csv` | ídem por método | — | 2026-08-30 |
| `analisis/salidas/inventario_artefactos_predicciones.csv` | metadatos de curaduría | — | clasifica variantes vigentes vs. superadas |
| `analisis/salidas/cuadro_sarima_por_dia_semana.csv` | SARIMA | 5 días (Lun–Vie) | — |
| `analisis/salidas/cuadro_amplitud_metodos.csv` | SARIMA, Prophet, XGBoost | — | — |
| `analisis/salidas/cuadro_jornadas_festivas.csv` | XGBoost vs. media histórica | — | — |

Esta ejecución es la **más reciente y completa**: es la única que cubre los seis métodos simultáneamente sobre el mismo split temporal y está confirmada en el historial de git.

### 1.2. Flujo legado "baselines multitarget" (`reports/tables/modeling/` y `models/metadata/backups/`)

Modelos incluidos: `naive`, `seasonal_naive_daily`, `seasonal_naive_weekly`, `historical_average_route_day_type_slot`, `rolling_average_4w/8w/12w/26w`. **No incluye XGBoost, Prophet, SARIMA, LSTM, GRU ni CNN-LSTM.**

| Carpeta backup | JSON asociado | Trackeado en git |
|---|---|---|
| `models/metadata/backups/baselines_pasajeros_reales_v2/` + `models/metadata/modeling_multitarget_baselines_pasajeros_reales_v2.json` | mismo `run_id` | **NO** (`??` en `git status`, sin commit) |
| `models/metadata/backups/baseline_regcheck/` | `modeling_multitarget_baseline_regcheck.json` | sí |
| `models/metadata/backups/evaluate_multitarget_20260720_1435/` | `modeling_multitarget_multitarget_20260720_1435.json` | sí |
| `models/metadata/backups/full_days_20260720_1530/` | `modeling_multitarget_full_days_20260720_1530.json` | sí |
| `models/metadata/backups/evaluate_common_support_20260720/`, `evaluate_full_20260718/`, `evaluate_full_trace_20260718/`, `report_full_final_20260718/`, `report_full_trace_20260718/`, `baselines_20260720_164609/`, `baselines_20260720_164946/` | `run_baselines_*.json` correspondientes | sí |
| `models/metadata/backups/sample_*` | — | fixtures de pytest (`.pytest_tmp/`), ignorados |

El JSON `models/metadata/modeling_multitarget_baselines_pasajeros_reales_v2.json` (**untracked**) tiene `test_start_aligned: "2026-04-02 04:00:00"` y `test_end_exclusive_aligned: "2026-06-10 04:00:00"` — el **mismo split temporal** que el freeze de 1.1, pero en un artefacto no confirmado en el historial de git.

### 1.3. XGBoost independiente (ejecución antigua)

`models/metadata/xgboost_xgboost_20260729.json` con tablas en `reports/tables/modeling/*_xgboost_20260729.*`, fecha 2026-07-29. Anterior al freeze de agosto; no contiene las cifras de los conjuntos A ni B evaluados abajo.

### Cronología resumida

1. 2026-07-18 a 2026-07-20 — barridos de baselines multitarget (`models/metadata/backups/evaluate_*`, `baselines_*`, `full_days_*`).
2. 2026-07-29 — ejecución XGBoost independiente (`xgboost_xgboost_20260729.json`).
3. 2026-08-23 — `correccion_sesgo_apc_20260823.json`.
4. 2026-08-26 — predicciones base de los 6 métodos generadas (`predicciones__*__freeze_20260823_203700.csv`).
5. 2026-08-28 — agregación previa (`*_pre_consolidacion.csv`).
6. 2026-08-30 — commit `4c79457`, consolidación final del flujo comparativo de seis métodos. **Ejecución más reciente y completa.**
7. Untracked, sin fecha de commit — `baselines_pasajeros_reales_v2` (mismo periodo de test, pero no incorporado al historial).

---

## 2. Contraste de los dos conjuntos de cifras

### Conjunto A: XGBoost MAE 26,93 y 29,69; sesgo 3,05 y 2,66; Prophet sesgo 0,91 y −0,12; 134 jornadas comunes; 3038 observaciones

**Coincide de forma exacta** con la ejecución de 1.1 (freeze `freeze_20260823_203700`, commit `4c79457`):

- `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__global.csv`, líneas verificadas:
  ```
  XGBoost,1,1483,100.6,26.93,34.65,26.77,3.05,...
  XGBoost,3,1555,117.31,29.69,39.38,25.31,2.66,...
  ```
- `analisis/salidas/referencia_metricas_pre_consolidacion.csv` (sin redondear): `mae=26.93319807552259 / 29.693137338906748`, `sesgo=3.053963347269049 / 2.661705471382637`, Prophet `sesgo=0.9133748437440949 / -0.11733229887546168`.
- n = 1483 + 1555 = **3038** observaciones (exacto).
- 134 jornadas comunes = `analisis/salidas/referencia_jornadas_pre_consolidacion.csv` (66 ruta 1 + 68 ruta 3, exacto).

**Conclusión: el Conjunto A corresponde exactamente a la ejecución freeze `freeze_20260823_203700` / commit `4c79457` (2026-08-30), periodo 2026-04-02 a 2026-06-10.**

### Conjunto B: XGBoost MAE 25,39 y 27,76; sesgo 3,22 y 2,73; Prophet sesgo 1,13 y 0,45; 137 jornadas; período 2 de abril–10 de junio de 2026

**No se encontró en ningún artefacto del repositorio.** Se buscaron los valores exactos (25.39, 27.76, 3.22, 2.73, 1.13, 0.45) en todos los CSV, JSON y Markdown versionados y no versionados del árbol de trabajo; las únicas coincidencias de esas cadenas numéricas están en datasets de ejemplo de librerías de terceros (`.venv/Lib/site-packages/matplotlib/...`, `numpy/...`), sin relación con el proyecto.

Lo único parcialmente coincidente es el **período** (2026-04-02 a 2026-06-10, idéntico al de A) y el número **137**, que sí es real pero corresponde a un conteo distinto: `analisis/salidas/resumen__xgboost__freeze_20260823_203700.csv` tiene 137 filas de agregación diaria (68 ruta 1 + 69 ruta 3) **sin filtrar por soporte común entre métodos** — a diferencia de las 134 jornadas de `referencia_jornadas_pre_consolidacion.csv`, que sí exigen que todos los métodos tengan predicción en la misma jornada.

Al recalcular el MAE/sesgo ponderado por `n` desde ese mismo archivo de 137 filas se obtiene ruta 1 MAE≈26,93 / sesgo≈3,04 y ruta 3 MAE≈29,76 / sesgo≈2,75 — **prácticamente idéntico al Conjunto A, no al B**. Es decir: el "137" es trazable como conteo, pero en ningún artefacto está asociado a los valores de MAE/sesgo del Conjunto B.

**Conclusión: el Conjunto B no es reproducible desde los artefactos actuales del repositorio.** Comparte el período declarado con la ejecución A pero sus cifras de error y de sesgo no aparecen en ningún archivo versionado ni sin versionar. No hay causa identificable en el repositorio (no hay una segunda ejecución del freeze, ni una variante de criterio de inclusión de jornadas que produzca esos valores exactos). Posibles explicaciones no verificables desde aquí: una versión de cálculo manual o de una hoja de cálculo externa no persistida como artefacto, una ejecución anterior descartada y no incluida en `analisis/salidas/`, o un error de trascripción en el capítulo. Ninguna de estas hipótesis puede confirmarse ni descartarse solo con lo que hay en el repositorio.

---

## 3. Modelos efectivamente evaluados en la ejecución más reciente

En el freeze `freeze_20260823_203700` (commit `4c79457`) se entrenaron y evaluaron **seis métodos**: SARIMA, Prophet, XGBoost, LSTM, GRU y CNN-LSTM, más dos variantes de predictor de referencia ("Referencia (26s)" y "Referencia (52s)").

- **LSTM, GRU y CNN-LSTM sí existen en la ejecución más reciente**, con predicciones propias:
  - `analisis/salidas/predicciones__lstm__freeze_20260823_203700.csv` (3038 filas)
  - `analisis/salidas/predicciones__gru__freeze_20260823_203700.csv` (3038 filas)
  - `analisis/salidas/predicciones__cnn_lstm__freeze_20260823_203700.csv` (3038 filas)
  - Métricas agregadas en `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__{global,tipo_dia,regimen}.csv`.
  - Código: `scripts/run_lstm_comparative_evaluation.py`, `scripts/run_gru_comparative_evaluation.py`, `scripts/run_cnn_lstm_comparative_evaluation.py`, `scripts/aggregate_comparative_metrics.py`, con soporte en `src/proyecto_grado/modeling/evaluation_config.py` y `evaluation_aggregation.py`. Configuración de la corrida en `configs/modeling/evaluacion_comparativa.yaml`. Los scripts exploratorios `analisis/18_`, `21_`, `22_`, `23_*.py` usan `SEMANAS_ENTRENAMIENTO = 52`.
  - Nota: LSTM/GRU/CNN-LSTM tienen 3038 filas (menos que las 3117 de SARIMA/Prophet/XGBoost), consistente con requerir historial previo para construir secuencias de entrada.

- **Importante**: estos tres métodos **no existen en absoluto** en el flujo "oficial" `reports/tables/modeling/metrics_comparison_multitarget.csv` ni en ninguno de sus backups bajo `models/metadata/backups/`. Ese pipeline solo corrió baselines (naive, seasonal naive, historical average, rolling average). Las cifras de LSTM/GRU/CNN-LSTM del capítulo dependen exclusivamente del árbol `analisis/salidas/`, separado del pipeline versionado en `reports/`.

---

## 4. Métricas disponibles y desagregaciones

Sí existen RMSE y MAPE (o su equivalente parcial) además de MAE y sesgo, en ambos árboles de artefactos, con nombres de columna distintos:

| Árbol | Columnas de métrica |
|---|---|
| `reports/tables/modeling/metrics_comparison_multitarget.csv` y afines | `mae, rmse, smape, wape, bias_mean, bias_abs, bias_to_mae_ratio` |
| `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__*.csv` | `mae, rmse, wape, sesgo, mape_parcial, n_mape` |

Desagregaciones disponibles:

- **Global** por ruta: `metricas__...__global.csv`, `error_analysis_by_route(_multitarget).csv`.
- **Por tipo de día**: `metricas__...__tipo_dia.csv`, `error_analysis_by_day_type(_multitarget).csv`.
- **Por franja horaria**: `error_analysis_by_hour(_multitarget).csv` (columna `hora_del_dia`); no hay equivalente por franja horaria en el árbol `analisis/salidas/`.
- **Por régimen/escenario**: `metricas__...__regimen.csv`, `error_analysis_by_scenario*`.
- Adicionalmente, en `reports/tables/modeling/`: `error_analysis_by_target*`, `error_analysis_by_dispatch_history_level*` (solo baselines).

Nota: el árbol `analisis/salidas/` (el que contiene los 6 métodos) **no tiene desagregación explícita por franja horaria**, solo por tipo de día y régimen; el desglose por hora únicamente existe para el pipeline de baselines en `reports/tables/modeling/`.

---

## 5. Predictor de referencia

Existen **dos implementaciones distintas y no equivalentes**, en dos ubicaciones separadas del repositorio:

1. **`src/proyecto_grado/modeling/baselines.py`** (pipeline oficial, `reports/tables/modeling/`): clase `RollingAverageBaseline`, constante `ROLLING_AVERAGE_VARIANTS` con ventanas de **4, 8, 12 y 26 semanas**. Promedia por `(ruta, tipo_dia, franja)` dentro de la ventana `W`, con fallback a `2W` si no hay suficientes datos. Incluye también `naive` (lag de 48 franjas / mismo horario del día anterior), `seasonal_naive_daily`, `seasonal_naive_weekly` y `historical_average_route_day_type_slot`.

2. **Scripts exploratorios en `analisis/*.py`** (los que alimentan el capítulo comparativo): usan otro conjunto de ventanas —
   - `analisis/02_historico_limitado.py`: horizontes `[13, 26, 52, 78, None]`.
   - `analisis/03_barrido_horizontes.py`: ventanas `[8, 10, 13, 26, 52, 78, None]`.
   - `analisis/13_barrido_ventana_diario.py`: ventanas `[8, 13, 26, 52, None]`.
   - `analisis/09_predictor_trivial.py`: ventana fija de **26 semanas** ("misma ventana que usó XGBoost").

En la **ejecución más reciente** (freeze de seis métodos), el predictor de referencia reportado en `metricas__comparacion_modelos__freeze_20260823_203700__global.csv` (y `_tipo_dia.csv`) tiene **exactamente dos variantes: "Referencia (26s)" y "Referencia (52s)"** — no las cuatro (4/8/12/26) de `baselines.py`, ni el conjunto completo (8/13/26/52/78) de los scripts de barrido. Es decir, el módulo `src/proyecto_grado/modeling/baselines.py` **no es la fuente** de las columnas de referencia que aparecen en las tablas comparativas finales; esas provienen de un cálculo separado en el árbol `analisis/`.

---

## 6. Trazabilidad de cifras concretas

| Cifra pedida | ¿Se reproduce? | Archivo / consulta |
|---|---|---|
| MAE por tipo de día, ambas rutas | **Sí** | `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__tipo_dia.csv` (filtrar `metodo=XGBoost`, columnas `route`, `tipo_dia`, `mae`). Ejemplo verificado: ruta 1 LABORAL 29,65 / SABADO 24,39 / DOMINGO 11,66 / FESTIVO 12,66 / FESTIVO_PUENTE 13,81; ruta 3 LABORAL 33,46 / SABADO 25,98 / DOMINGO 10,30 / FESTIVO 12,95 / FESTIVO_PUENTE 10,83. También en `referencia_metricas_pre_consolidacion.csv` (sin redondear) y en `reports/tables/modeling/error_analysis_by_day_type_multitarget.csv` (pero este último **solo para baselines**, no XGBoost). |
| Sesgo por ventana de entrenamiento (8, 13, 26, 52 semanas y registro completo) por tipo de día | **No, como tabla única.** Existen fragmentos incompatibles entre sí: `models/metadata/bias_analysis_rolling_bias_20260720.json` / `modeling_multitarget_rolling_bias_20260720.json` y `reports/tables/modeling/bias_by_slot_rolling_bias_20260720.csv` cubren solo baselines con ventanas **4/8/12/26** (no 13 ni 52), desagregado por `tipo_dia` y `hora_del_dia`. Los scripts de `analisis/` usan ventanas **8/13/26/52/78/completo** pero no se localizó un CSV persistido que cruce esas ventanas con tipo_dia para XGBoost/SARIMA/Prophet. El cruce exacto "8, 13, 26, 52, completo × tipo_dia" pedido **no existe como artefacto único** en el repositorio. |
| MAE de SARIMA por día de la semana | **Sí** | `analisis/salidas/cuadro_sarima_por_dia_semana.csv`: Lunes 90,26 (ruta1) / 112,23 (ruta3); Martes 53,95 / 73,85; Miércoles 34,70 / 46,91; Jueves 35,75 / 49,88; Viernes 41,11 / 48,90. **Nota: el archivo solo cubre Lunes–Viernes; no incluye sábado ni domingo.** |
| Amplitud media predicha frente a la observada por método | **Parcial** | `analisis/salidas/cuadro_amplitud_metodos.csv`, columnas `metodo, route, amplitud_predicha, amplitud_observada, proporcion`. Verificado: SARIMA ruta1 26,81/136,12 (0,197); Prophet ruta1 72,61/136,12 (0,533); XGBoost ruta1 69,17/136,12 (0,508); valores análogos para ruta 3. **Solo cubre SARIMA, Prophet y XGBoost — no LSTM, GRU ni CNN-LSTM.** |
| Franjas sin precedente en jornadas festivas del conjunto de evaluación | **Parcial / por interpretación** | No existe el término literal "sin precedente" en el repositorio. El concepto más cercano es la columna `celdas_sin_media` en `analisis/salidas/cuadro_jornadas_festivas.csv` y `resumen__xgboost__freeze_20260823_203700.csv`, que cuenta franjas horarias festivas sin dato de referencia histórica (ejemplo verificado: ruta 1, 2026-04-02, FESTIVO, n=15, celdas_sin_media=8). Si el capítulo usa "sin precedente" como sinónimo de esta columna, es trazable; si se refiere a otro criterio, no se encontró artefacto correspondiente. |

---

## 7. Discrepancias — valores que no se pudieron reproducir desde los artefactos

1. **Conjunto B completo** (XGBoost MAE 25,39/27,76; sesgo 3,22/2,73; Prophet sesgo 1,13/0,45; 137 jornadas) — no aparece en ningún artefacto del repositorio. Solo el conteo "137" es trazable, y como conteo *no* filtrado por soporte común, no como el conjunto de cifras de error/sesgo que lo acompaña.
2. **Sesgo por ventana de entrenamiento (8/13/26/52/completo) desagregado por tipo de día** — no existe como tabla única coherente; las fuentes disponibles usan conjuntos de ventanas distintos entre sí (4/8/12/26 en el pipeline oficial de baselines; 8/13/26/52/78 en los scripts exploratorios de `analisis/`, sin cruce completo con tipo_dia persistido).
3. **MAE de SARIMA por día de la semana para sábado y domingo** — el único artefacto encontrado (`cuadro_sarima_por_dia_semana.csv`) cubre solo Lunes–Viernes.
4. **Amplitud media predicha vs. observada para LSTM, GRU y CNN-LSTM** — `cuadro_amplitud_metodos.csv` solo cubre SARIMA, Prophet y XGBoost, aunque estos tres métodos sí tienen predicciones y métricas de error completas en el mismo freeze.
5. **"Franjas sin precedente" como término exacto** — no aparece en el repositorio; se infiere una correspondencia con `celdas_sin_media`, pero no está confirmada.
6. El artefacto `models/metadata/backups/baselines_pasajeros_reales_v2/` y su JSON comparten el período de evaluación del freeze principal pero **no están confirmados en el historial de git** (aparecen como `??` en `git status`); cualquier cifra que dependa de ellos no tiene commit asociado.

---

### Nota metodológica

Este informe no reejecutó ningún entrenamiento ni modificó archivo alguno del repositorio. Los conteos, columnas y valores citados fueron leídos directamente de los archivos indicados; donde no fue posible confirmar una cifra, se declara explícitamente en la sección 7 en lugar de aproximarla.
