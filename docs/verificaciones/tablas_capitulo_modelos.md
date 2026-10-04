# Tablas definitivas del capítulo de implementación y comparación de modelos

**Origen único:** freeze `freeze_20260823_203700`, commit `4c79457` ("Consolida el flujo comparativo de seis metodos", 2026-08-30). Periodo de evaluación: 2026-04-02 04:00 → 2026-06-10 04:00. Verificación de solo lectura: no se modificó ni reejecutó nada del repositorio.

Formato: coma decimal, dos decimales. Donde una tabla exige un cálculo que no está persistido tal cual, se indica explícitamente la operación aplicada y sobre qué artefacto crudo se aplicó.

---

## Tabla 1 — Desempeño global por ruta (los seis métodos + dos referencias)

**Archivo fuente:** `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__global.csv`. **Operación:** ninguna, valores copiados tal cual (ya vienen redondeados a 2 decimales).

**Aviso importante sobre el `n`:** el propio script que genera este archivo, `scripts/aggregate_comparative_metrics.py`, declara en su docstring: *"La comparacion se restringe a la interseccion de jornadas y calcula las metricas sobre observaciones, no promediando por jornada."* Es decir, **esta tabla ya está calculada sobre el soporte común de 134 jornadas (3038 observaciones)** para los ocho renglones (seis métodos + dos referencias) — no existe una versión "sin restringir" persistida de esta tabla global.

Confirmado por conteo directo de los archivos de predicciones crudos (`analisis/salidas/predicciones__<metodo>__freeze_20260823_203700.csv`):

| Método | Filas crudas disponibles (ambas rutas) | Filas usadas en esta tabla (n) |
|---|---|---|
| SARIMA | 3117 (route1=1536, route3=1581) | 3038 (1483+1555) |
| Prophet | 3117 (route1=1536, route3=1581) | 3038 (1483+1555) |
| XGBoost | 3117 (route1=1536, route3=1581) | 3038 (1483+1555) |
| LSTM | 3038 (1483+1555) — techo estructural (ventana de entrada) | 3038 (1483+1555) |
| GRU | 3038 (1483+1555) — techo estructural | 3038 (1483+1555) |
| CNN-LSTM | 3038 (1483+1555) — techo estructural | 3038 (1483+1555) |

SARIMA, Prophet y XGBoost tienen **3117** observaciones disponibles en sus archivos de predicciones crudos, pero el freeze publicado ya las recorta a **3038** (el techo que imponen LSTM/GRU/CNN-LSTM por su ventana de entrada) para que la comparación de los seis métodos sea homogénea.

| Método | Ruta | n | MAE | RMSE | Sesgo | WAPE |
|---|---|---|---|---|---|---|
| SARIMA | 1 | 1483 | 46,03 | 59,37 | -19,62 | 45,75 |
| SARIMA | 3 | 1555 | 60,27 | 81,32 | -32,62 | 51,38 |
| Prophet | 1 | 1483 | 27,92 | 35,34 | 0,91 | 27,75 |
| Prophet | 3 | 1555 | 32,24 | 42,38 | -0,12 | 27,48 |
| XGBoost | 1 | 1483 | 26,93 | 34,65 | 3,05 | 26,77 |
| XGBoost | 3 | 1555 | 29,69 | 39,38 | 2,66 | 25,31 |
| LSTM | 1 | 1483 | 28,77 | 37,03 | 3,91 | 28,60 |
| LSTM | 3 | 1555 | 33,34 | 44,67 | 5,59 | 28,42 |
| GRU | 1 | 1483 | 28,42 | 36,65 | 4,68 | 28,25 |
| GRU | 3 | 1555 | 33,11 | 44,33 | 4,58 | 28,22 |
| CNN-LSTM | 1 | 1483 | 29,76 | 38,46 | 4,44 | 29,59 |
| CNN-LSTM | 3 | 1555 | 34,85 | 46,83 | 5,69 | 29,71 |
| Referencia (26s) | 1 | 1483 | 26,96 | 34,71 | 6,12 | 26,80 |
| Referencia (26s) | 3 | 1555 | 29,69 | 39,62 | 6,39 | 25,31 |
| Referencia (52s) | 1 | 1483 | 27,78 | 35,89 | 11,41 | 27,62 |
| Referencia (52s) | 3 | 1555 | 30,82 | 40,83 | 13,54 | 26,27 |

---

## Tabla 2 — Efecto del soporte común

Dado que la Tabla 1 **ya está** restringida a las 134 jornadas comunes, no existe en los artefactos una segunda versión "sin restringir" con la que contrastarla directamente. Para ilustrar el efecto, se recalcularon aquí (operación propia, no un valor persistido) las mismas métricas usando **todas** las observaciones disponibles en `analisis/salidas/predicciones__<metodo>__freeze_20260823_203700.csv`, sin exigir que la jornada exista en los ocho métodos/referencias a la vez. Esto solo es posible para SARIMA, Prophet y XGBoost, porque LSTM, GRU y CNN-LSTM no tienen observaciones adicionales fuera de las 3038 (su archivo crudo ya es idéntico al soporte común). Fórmulas verificadas contra la Tabla 1: MAE = media(|real−pred|), sesgo = media(pred−real), RMSE = raíz(media((real−pred)²)), WAPE = 100·Σ|real−pred| / Σreal.

**Archivo fuente:** `analisis/salidas/predicciones__{sarima,prophet,xgboost}__freeze_20260823_203700.csv`. **Operación:** agregación directa (media/raíz cuadrática media) sobre las columnas `real` y `pred_<metodo>`, sin filtrar por soporte común.

| Método | Ruta | n (sin restringir) | MAE | RMSE | Sesgo | WAPE |
|---|---|---|---|---|---|---|
| SARIMA | 1 | 1536 | 46,59 | 60,19 | -20,63 | 46,11 |
| SARIMA | 3 | 1581 | 59,94 | 80,94 | -32,50 | 51,04 |
| Prophet | 1 | 1536 | 27,98 | 35,40 | 0,97 | 27,68 |
| Prophet | 3 | 1581 | 32,25 | 42,33 | 0,04 | 27,46 |
| XGBoost | 1 | 1536 | 26,93 | 34,69 | 3,04 | 26,65 |
| XGBoost | 3 | 1581 | 29,76 | 39,37 | 2,75 | 25,34 |

**¿Cambia el ordenamiento entre métodos?** No. Tanto en la versión restringida (Tabla 1) como en la versión sin restringir, para ambas rutas el orden por MAE entre estos tres métodos es idéntico: **XGBoost < Prophet < SARIMA**. Las diferencias entre ambas versiones son marginales (≤0,3 en MAE, ≤0,4 en WAPE), consistentes con que solo ~53 filas por ruta (3,4 %–3,5 %) quedan fuera del soporte común. No se puede evaluar el efecto sobre LSTM/GRU/CNN-LSTM/referencias porque no tienen observaciones adicionales que retirar.

---

## Tabla 3 — MAE por tipo de día, por ruta

**Archivo fuente:** `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__tipo_dia.csv`. **Operación:** ninguna, valores copiados tal cual. Número de jornadas por tipo obtenido por intersección de `analisis/salidas/referencia_jornadas_pre_consolidacion.csv` (134 jornadas comunes) con la columna `tipo_dia` de `predicciones__xgboost__freeze_20260823_203700.csv` (un `tipo_dia` por jornada, invariante entre métodos).

**Jornadas por tipo (soporte común, 134 en total):**

| Ruta | DOMINGO | FESTIVO | FESTIVO_PUENTE | LABORAL | SABADO | Total |
|---|---|---|---|---|---|---|
| 1 | 9 | 3 | 2 | 42 | 10 | 66 |
| 3 | 10 | 3 | 2 | 43 | 10 | 68 |

**MAE por método, ruta y tipo de día:**

| Método | Ruta | DOMINGO | FESTIVO | FESTIVO_PUENTE | LABORAL | SABADO |
|---|---|---|---|---|---|---|
| SARIMA | 1 | 22,38 | 55,41 | 10,25 | 49,79 | 40,19 |
| SARIMA | 3 | 53,19 | 58,83 | 13,85 | 65,97 | 41,55 |
| Prophet | 1 | 18,52 | 15,01 | 17,75 | 29,50 | 27,63 |
| Prophet | 3 | 16,51 | 16,19 | 10,61 | 35,48 | 29,43 |
| XGBoost | 1 | 11,66 | 12,66 | 13,81 | 29,65 | 24,39 |
| XGBoost | 3 | 10,30 | 12,95 | 10,83 | 33,46 | 25,98 |
| LSTM | 1 | 13,67 | 13,15 | 42,85 | 30,86 | 26,86 |
| LSTM | 3 | 10,53 | 42,57 | 93,87 | 35,63 | 25,74 |
| GRU | 1 | 10,44 | 21,05 | 71,97 | 30,07 | 25,69 |
| GRU | 3 | 12,55 | 35,99 | 65,95 | 35,74 | 26,61 |
| CNN-LSTM | 1 | 12,97 | 33,18 | 74,55 | 30,86 | 27,13 |
| CNN-LSTM | 3 | 12,29 | 45,71 | 118,37 | 36,68 | 26,86 |
| Referencia (26s) | 1 | 11,89 | 28,20 | 13,67 | 29,06 | 24,54 |
| Referencia (26s) | 3 | 10,07 | 33,19 | 13,20 | 32,63 | 25,73 |
| Referencia (52s) | 1 | 11,52 | 13,64 | 12,37 | 30,51 | 25,74 |
| Referencia (52s) | 3 | 10,71 | 13,52 | 8,60 | 34,76 | 27,01 |

Nota: FESTIVO y FESTIVO_PUENTE tienen muy pocas jornadas (2–3 por ruta), por lo que sus MAE son volátiles — se explica el deterioro fuerte de LSTM/GRU/CNN-LSTM en esas categorías (ver Tabla 6 sobre régimen "raro").

---

## Tabla 4 — Sesgo por tipo de día, por ruta

**Archivo fuente:** mismo que Tabla 3 (`metricas__comparacion_modelos__freeze_20260823_203700__tipo_dia.csv`, columna `sesgo`). **Operación:** ninguna.

| Método | Ruta | DOMINGO | FESTIVO | FESTIVO_PUENTE | LABORAL | SABADO |
|---|---|---|---|---|---|---|
| SARIMA | 1 | 17,92 | 54,49 | 2,04 | -34,21 | 16,68 |
| SARIMA | 3 | 50,85 | 54,39 | -10,90 | -51,98 | 0,42 |
| Prophet | 1 | 4,91 | -4,34 | -7,20 | 0,74 | 1,66 |
| Prophet | 3 | 4,91 | -1,82 | -9,91 | -0,59 | 1,02 |
| XGBoost | 1 | 2,87 | -1,38 | 9,51 | 2,84 | 4,26 |
| XGBoost | 3 | 1,58 | 3,60 | 6,18 | 2,24 | 4,58 |
| LSTM | 1 | 4,79 | -4,74 | 42,59 | 3,21 | 4,78 |
| LSTM | 3 | 2,35 | 23,49 | 92,19 | 4,28 | 1,81 |
| GRU | 1 | 1,03 | 18,04 | 71,97 | 4,00 | 1,16 |
| GRU | 3 | 4,01 | 28,19 | 63,03 | 4,29 | -3,72 |
| CNN-LSTM | 1 | 4,18 | 25,55 | 74,55 | 1,33 | 8,94 |
| CNN-LSTM | 3 | 3,59 | 40,76 | 117,03 | 2,23 | 5,78 |
| Referencia (26s) | 1 | 4,92 | 13,11 | 0,95 | 6,04 | 6,27 |
| Referencia (26s) | 3 | 3,10 | 17,14 | 3,52 | 5,94 | 8,08 |
| Referencia (52s) | 1 | 4,94 | 0,59 | 3,57 | 12,45 | 11,85 |
| Referencia (52s) | 3 | 4,19 | 1,49 | 2,59 | 15,02 | 14,26 |

---

## Tabla 5 — Métricas por régimen

**Archivo fuente:** `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__regimen.csv`. **Operación:** ninguna.

**Valores de la variable `regimen`:** toma exactamente dos valores, definidos en `configs/modeling/evaluacion_comparativa.yaml` (`tipos_baja_frecuencia: [FESTIVO, FESTIVO_PUENTE]`) y aplicados en `src/proyecto_grado/modeling/evaluation_aggregation.py:257-259`:
- **`raro`** = jornadas con `tipo_dia` ∈ {FESTIVO, FESTIVO_PUENTE}.
- **`ordinario`** = el resto (LABORAL, SABADO, DOMINGO).

| Método | Ruta | Régimen | n | MAE | RMSE | Sesgo | WAPE |
|---|---|---|---|---|---|---|---|
| SARIMA | 1 | ordinario | 1422 | 46,29 | 59,73 | -22,03 | 44,66 |
| SARIMA | 1 | raro | 61 | 39,86 | 50,25 | 36,43 | 135,77 |
| SARIMA | 3 | ordinario | 1485 | 61,01 | 82,30 | -35,76 | 50,23 |
| SARIMA | 3 | raro | 70 | 44,69 | 56,73 | 33,87 | 152,31 |
| Prophet | 1 | ordinario | 1422 | 28,43 | 35,86 | 1,18 | 27,43 |
| Prophet | 1 | raro | 61 | 15,95 | 19,93 | -5,32 | 54,34 |
| Prophet | 3 | ordinario | 1485 | 33,08 | 43,14 | 0,08 | 27,24 |
| Prophet | 3 | raro | 70 | 14,43 | 20,77 | -4,36 | 49,19 |
| XGBoost | 1 | ordinario | 1422 | 27,53 | 35,23 | 3,08 | 26,56 |
| XGBoost | 1 | raro | 61 | 13,06 | 16,21 | 2,37 | 44,47 |
| XGBoost | 3 | ordinario | 1485 | 30,51 | 40,17 | 2,58 | 25,12 |
| XGBoost | 3 | raro | 70 | 12,28 | 14,63 | 4,41 | 41,86 |
| LSTM | 1 | ordinario | 1422 | 29,01 | 37,17 | 3,58 | 27,98 |
| LSTM | 1 | raro | 61 | 23,37 | 33,61 | 11,56 | 79,61 |
| LSTM | 3 | ordinario | 1485 | 32,15 | 42,54 | 3,73 | 26,47 |
| LSTM | 3 | raro | 70 | 58,70 | 77,16 | 45,08 | 200,04 |
| GRU | 1 | ordinario | 1422 | 27,99 | 36,05 | 3,31 | 27,00 |
| GRU | 1 | raro | 61 | 38,58 | 48,68 | 36,61 | 131,41 |
| GRU | 3 | ordinario | 1485 | 32,53 | 43,01 | 2,95 | 26,78 |
| GRU | 3 | raro | 70 | 45,41 | 66,35 | 39,14 | 154,75 |
| CNN-LSTM | 1 | ordinario | 1422 | 29,01 | 37,45 | 2,81 | 27,98 |
| CNN-LSTM | 1 | raro | 61 | 47,42 | 57,26 | 42,42 | 161,52 |
| CNN-LSTM | 3 | ordinario | 1485 | 33,26 | 43,73 | 2,91 | 27,38 |
| CNN-LSTM | 3 | raro | 70 | 68,55 | 90,32 | 64,73 | 233,61 |
| Referencia (26s) | 1 | ordinario | 1422 | 27,12 | 34,69 | 6,00 | 26,17 |
| Referencia (26s) | 1 | raro | 61 | 23,20 | 35,23 | 8,92 | 79,00 |
| Referencia (26s) | 3 | ordinario | 1485 | 29,82 | 39,44 | 6,08 | 24,56 |
| Referencia (26s) | 3 | raro | 70 | 26,91 | 43,25 | 12,86 | 91,71 |
| Referencia (52s) | 1 | ordinario | 1422 | 28,41 | 36,47 | 11,83 | 27,41 |
| Referencia (52s) | 1 | raro | 61 | 13,20 | 17,23 | 1,62 | 44,97 |
| Referencia (52s) | 3 | ordinario | 1485 | 31,71 | 41,65 | 14,10 | 26,11 |
| Referencia (52s) | 3 | raro | 70 | 11,98 | 14,98 | 1,84 | 40,81 |

---

## Tabla 6 — Inventario de barridos de ventana de entrenamiento persistidos

**No se reconstruyó ni se ejecutó nada.** Esto es un inventario de lo que ya existe en disco.

| Archivo | Método | Ventanas (semanas) | Desagregación | Alcance |
|---|---|---|---|---|
| `analisis/salidas/barrido_ventana_entrenamiento.csv` | XGBoost (`xgb.XGBRegressor`, `analisis/03_barrido_horizontes.py`) | 8, 10, 13, 26, 52, 78, 999* | `corte` (fecha de corte), `regimen` (ordinario/raro) | 72 filas |
| `analisis/salidas/barrido_horizontes.csv` | XGBoost | 8, 10, 13, 26, 52, 78, 999* | `corte`, `regimen` | 72 filas |
| `analisis/salidas/barrido_ventana_diario.csv` | XGBoost (`analisis/13_barrido_ventana_diario.py`) | 8, 13, 26, 52, 999* | `route`, `dia_op` (jornada individual), `tipo_dia`, `regimen` | 686 filas — es el único archivo con `sesgo` y `tipo_dia` cruzados con ventana, pero **solo para XGBoost** y **por jornada individual**, no agregado |
| `analisis/salidas/barrido_disponibilidad_real_r1.csv` / `_r3.csv` | XGBoost | 8, 10, 13, 26, 52, 78, 999* | `corte`, `regimen` | variante de disponibilidad real de datos, por ruta |
| `analisis/salidas/barrido_sin_calendario_anual.csv` | XGBoost | 8, 10, 13, 26, 52, 78, 999* | `corte`, `regimen` | variante sin variable de calendario anual |
| `reports/tables/modeling/bias_by_slot_rolling_bias_20260720.csv` y JSON asociados (`models/metadata/*rolling_bias_20260720*`) | Solo baselines (`naive`, `seasonal_naive_daily/weekly`, `historical_average_route_day_type_slot`, `rolling_average_4w/8w/12w/26w`) | 4, 8, 12, 26 | `route`, `tipo_dia`, `hora_del_dia` | pipeline "oficial" `reports/`, no incluye XGBoost/Prophet/SARIMA/LSTM/GRU/CNN-LSTM |

*El valor `999` es el código usado en estos scripts para "ventana completa / todo el histórico disponible" (no una ventana literal de 999 semanas).

**Conclusión del inventario:**
- El único artefacto que cruza ventana de entrenamiento con `tipo_dia` y `sesgo` es `barrido_ventana_diario.csv`, y es **exclusivo de XGBoost** con ventanas {8, 13, 26, 52, completo}. Al estar desagregado por jornada individual (`dia_op`), podría agregarse por `tipo_dia` mediante un promedio ponderado por `n` — esa agregación **no requeriría reentrenar nada**, sería una operación puramente aritmética sobre datos ya persistidos, pero no se ejecutó aquí porque se pidió únicamente inventariar.
- **No existe ningún artefacto persistido** que cruce ventana de entrenamiento con `tipo_dia` para Prophet, SARIMA, LSTM, GRU o CNN-LSTM.
- **Para obtener el cruce ventana × tipo de día de los seis métodos** haría falta: (1) para XGBoost, agregar `barrido_ventana_diario.csv` por `tipo_dia` (solo cálculo, sin reentrenar); (2) para Prophet, SARIMA, LSTM, GRU y CNN-LSTM, **sí sería necesario reentrenar y volver a predecir** cada método con cada ventana de entrenamiento (8, 13, 26, 52, completo) sobre el mismo split de evaluación del freeze, y luego agregar por tipo de día — trabajo no persistido actualmente en ningún artefacto.
- El módulo baseline "oficial" (`bias_by_slot_rolling_bias_20260720.csv`) usa un conjunto de ventanas distinto (4/8/12/26) y modelos distintos (baselines, no los seis métodos), por lo que no puede sustituir al cruce pedido.

---

## Tabla 7 — Verificación de desplazamiento de columnas

Valores del capítulo a verificar: **Prophet laboral R1 = 29,65** y **XGBoost laboral R1 = 29,85**.

**Archivo de referencia:** `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__tipo_dia.csv`, filtrado a `route=1, tipo_dia=LABORAL`:

| Método | MAE LABORAL, ruta 1 |
|---|---|
| SARIMA | 49,79 |
| Prophet | **29,50** |
| XGBoost | **29,65** |
| GRU | 30,07 |
| LSTM | 30,86 |
| CNN-LSTM | 30,86 |
| Referencia (26s) | 29,06 |
| Referencia (52s) | 30,51 |

**Hallazgo 1 — "Prophet laboral R1 29,65":** el valor 29,65 **no es el MAE de Prophet** (que es 29,50); es **exactamente el MAE de XGBoost** para la misma celda (ruta 1, LABORAL). Esto es consistente con un **desplazamiento de una fila entre métodos**: al leer la tabla ordenada como SARIMA → Prophet → XGBoost → LSTM → GRU → CNN-LSTM → Referencia (26s) → Referencia (52s), el valor correspondiente a la fila de XGBoost quedó etiquetado con el nombre del método anterior (Prophet). Se verificó también contra los valores sin redondear de `analisis/salidas/referencia_metricas_pre_consolidacion.csv` (Prophet = 29,4965…; XGBoost = 29,6471…), confirmando que no es un problema de redondeo sino de asignación de etiqueta/fila.

**Hallazgo 2 — "XGBoost laboral R1 29,85":** **no se encontró ningún valor persistido, redondeado o sin redondear, que coincida con 29,85** (tolerancia ±0,01) para ningún método, en ninguna desagregación (global, tipo_dia, régimen) del freeze `freeze_20260823_203700`, ni en la tabla `barrido_ventana_diario.csv`, ni en ejecuciones anteriores de XGBoost (`xgboost_20260729`). El valor más cercano en la celda ruta 1/LABORAL es Referencia (52s) = 30,51 y GRU = 30,07; ninguno redondea a 29,85. **Esta segunda cifra no se explica por un desplazamiento de fila ni de columna dentro de las tablas disponibles — no es reproducible desde los artefactos del repositorio.**

**Conclusión:** de los dos valores señalados, uno (Prophet 29,65) se explica por un desplazamiento de una fila entre métodos consecutivos en la tabla de tipo de día; el otro (XGBoost 29,85) no tiene explicación por desplazamiento ni por ningún otro criterio verificable desde los artefactos — se recomienda revisarlo directamente contra el borrador del capítulo, ya que podría tratarse de una transcripción manual sin fuente persistida.
