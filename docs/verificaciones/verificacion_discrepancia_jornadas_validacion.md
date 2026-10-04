# Verificación: discrepancia de jornadas en el período de validación (2025-12-25 a 2026-04-01)

Verificación de solo lectura. No se modificó ningún archivo. Todos los
conteos se recalcularon directamente contra el parquet y los artefactos
existentes con `.venv/Scripts/python.exe`.

## Resumen del hallazgo

La discrepancia (98 jornadas/ruta, 196 total, 4 festivas/ruta según el
informe de la búsqueda **vs.** 192 jornadas y 6 en régimen excepcional según
`analisis/25_referencia_combinada_regimen.py`) se explica por dos filtros
que el informe de composición del período **no aplicó** pero que sí aplican
todos los flujos de evaluación (`hparam_search`, `referencia_combinada`):
el umbral de 8 franjas (`min_franjas`) y, solo para las redes neuronales, la
exigencia de que la jornada previa también tenga al menos 8 franjas.

## 1. Jornadas según el calendario vs. jornadas efectivamente evaluadas

**Calendario** (criterio: `FK_RUTA == ruta` y `pasajeros_total.notna()`, sin
umbral de franjas mínimas — este fue el criterio usado en el informe de
composición del período que reportó "98 jornadas por ruta"):

| Ruta | LABORAL | SABADO | DOMINGO | FESTIVO | FESTIVO_PUENTE | Total |
|---|---|---|---|---|---|---|
| 1 | 66 | 14 | 14 | 2 | 2 | 98 |
| 3 | 66 | 14 | 14 | 2 | 2 | 98 |

Total calendario: 196 jornadas (98×2), 8 festivas (4 por ruta: 2 FESTIVO + 2
FESTIVO_PUENTE).

**Candidatas tras el umbral `min_franjas = 8`** (criterio usado por
`_dias_candidatos` en `hparam_search/runner.py`, idéntico al de los seis
scripts de evaluación comparativa): se excluyen las jornadas con menos de 8
franjas operativas registradas.

| Ruta | Jornada excluida | tipo_dia | franjas | Motivo |
|---|---|---|---|---|
| 1 | 2026-01-01 | FESTIVO | 1 | `n_franjas (1) < min_franjas (8)` |
| 3 | 2026-01-01 | FESTIVO | 5 | `n_franjas (5) < min_franjas (8)` |
| 3 | 2026-02-01 | DOMINGO | 7 | `n_franjas (7) < min_franjas (8)` |
| 3 | 2026-03-08 | DOMINGO | 7 | `n_franjas (7) < min_franjas (8)` |

Candidatas resultantes: Ruta 1 = 97, Ruta 3 = 95 → **192 en total**. Esto
coincide exactamente con el `n_jornadas = 192` reportado por SARIMA, Prophet
y XGBoost en `configuraciones__{sarima,prophet,xgboost}.csv`, y con el total
de 192 reportado por `25_referencia_combinada_regimen.py`.

De las 8 jornadas festivas del calendario, se pierde 2026-01-01 en ambas
rutas (2 de 8), quedando **6 jornadas en régimen excepcional** — coincide
exactamente con lo reportado por `referencia_combinada`.

**Exclusión adicional, solo para LSTM/GRU/CNN-LSTM** (criterio: la jornada
inmediatamente anterior en el calendario debe tener también ≥ 8 franjas, ya
que la secuencia de entrada de la red se construye con la jornada previa
completa — `construir_ejemplos`/predicción en `hparam_search/fits.py` y en
los tres scripts de evaluación comparativa de redes):

| Ruta | Jornada excluida | tipo_dia | Motivo |
|---|---|---|---|
| 1 | 2026-01-02 | LABORAL | día previo 2026-01-01 tiene 1 franja < 8 |
| 3 | 2026-01-02 | LABORAL | día previo 2026-01-01 tiene 5 franjas < 8 |
| 3 | 2026-02-02 | LABORAL | día previo 2026-02-01 tiene 7 franjas < 8 |
| 3 | 2026-03-09 | LABORAL | día previo 2026-03-08 tiene 7 franjas < 8 |

Jornadas resultantes para las redes: Ruta 1 = 96, Ruta 3 = 92 → **188 en
total**, coincide exactamente con `n_jornadas = 188` reportado por LSTM, GRU
y CNN-LSTM en sus respectivos `configuraciones__*.csv`. Se verificó además
que, para las 192/188 jornadas candidatas restantes, ningún otro guardia
(`len(train) < 500`, `len(fit) < 500`, `len(stop) == 0`, ejemplos de ajuste
< 50 o de parada < 3) excluyó jornadas adicionales: la ventana de 26/52
semanas está lejos del inicio del dataset (2024-04-16) y siempre aporta
sobradas observaciones.

No hay evidencia de exclusiones por "ausencia de predicción" (fallos de
convergencia de SARIMA u otra excepción): las 10 configuraciones de SARIMA en
`configuraciones__sarima.csv` reportan `n_jornadas = 192` de forma uniforme,
así que ningún ajuste individual falló de forma distinta entre
configuraciones. Tampoco hay exclusión por restricción a soporte común entre
métodos: `evaluar_configuracion` (usado por la búsqueda) calcula el MAE de
cada método de forma independiente, sin intersectar con los demás; la
intersección de soporte común solo se aplica en el freeze de reevaluación
(`freeze_20260922_203820`), un paso distinto y posterior.

## 2. ¿"98 jornadas por ruta" es calendario o evaluación?

Es una cifra **calendario**, no el número de jornadas sobre las que se
calcularon los errores. Se obtuvo agrupando por `dia_op` exigiendo solo al
menos un registro con `pasajeros_total` no nulo, sin aplicar el umbral de 8
franjas que sí aplican los flujos de evaluación.

El número real de jornadas sobre las que se calculó el error de cada
configuración probada en la búsqueda es:

- **SARIMA, Prophet, XGBoost:** 192 jornadas (97 Ruta 1 + 95 Ruta 3), igual
  para las 10 configuraciones de cada método (confirmado en sus
  `configuraciones__<metodo>.csv`, columna `n_jornadas`).
- **LSTM, GRU, CNN-LSTM:** 188 jornadas (96 Ruta 1 + 92 Ruta 3), igual para
  las 10 configuraciones de cada método.

## 3. ¿Los seis métodos se evaluaron sobre el mismo conjunto de jornadas?

**No.** Hay dos conjuntos distintos, por diseño (ventana de 26 semanas para
los métodos clásicos vs. 52 semanas para las redes, y el requisito adicional
de jornada previa completa solo en las redes):

| Método | Jornadas (validación) | Ruta 1 | Ruta 3 |
|---|---|---|---|
| SARIMA | 192 | 97 | 95 |
| Prophet | 192 | 97 | 95 |
| XGBoost | 192 | 97 | 95 |
| LSTM | 188 | 96 | 92 |
| GRU | 188 | 96 | 92 |
| CNN-LSTM | 188 | 96 | 92 |

Dentro de cada familia (clásicos vs. redes) el conjunto de jornadas es
idéntico entre métodos, porque comparten exactamente la misma ventana de
entrenamiento y los mismos criterios de inclusión/exclusión; la única
diferencia es la familia a la que pertenece el método. Esto es consistente
con el diseño documentado en `configs/modeling/evaluacion_comparativa.yaml`
("la asimetría es deliberada... no debe interpretarse como una invitación a
unificar las ventanas").

## 4. ¿Por qué `25_referencia_combinada_regimen.py` lee las predicciones de GRU para la "Referencia (52s)"?

Porque reutiliza la misma convención ya establecida en
`configs/modeling/evaluacion_comparativa.yaml` (`referencias: "Referencia
(52s)": metodo_fuente: gru`), donde GRU fue designado como la fuente
canónica de esa referencia. La columna `pred_media` (media histórica por
tipo_dia/hora) es idéntica entre LSTM, GRU y CNN-LSTM para una misma
jornada/ruta/franja, porque las tres comparten exactamente la misma ventana
de entrenamiento (52 semanas) y la misma fórmula de promedio — el valor no
depende en absoluto de la arquitectura de red, solo de la ventana. Se
verificó directamente contra los tres archivos de predicciones del freeze
`freeze_20260922_203820`:

```
max |pred_media_lstm - pred_media_gru|     = 0.0
max |pred_media_lstm - pred_media_cnn_lstm| = 0.0
```

Es decir, `25_referencia_combinada_regimen.py` podría haber leído
indistintamente `predicciones__lstm__...` o `predicciones__cnn_lstm__...`
para la Referencia (52s) sin cambiar ningún resultado; se usó GRU por
consistencia y trazabilidad directa con la convención ya fijada en el
config, no por ninguna propiedad especial de ese método.

## Archivos usados para esta verificación (solo lectura)

- `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet`
- `configs/modeling/evaluacion_comparativa.yaml`, `src/proyecto_grado/modeling/evaluation_config.py`
- `src/proyecto_grado/modeling/hparam_search/runner.py` (`_preparar_ruta`, `_dias_candidatos`)
- `src/proyecto_grado/modeling/hparam_search/fits.py` (`construir_ejemplos`)
- `analisis/salidas/busqueda_hiperparametros/configuraciones__{sarima,prophet,xgboost,lstm,gru,cnn_lstm}.csv`
- `analisis/salidas/predicciones__{lstm,gru,cnn_lstm}__freeze_20260922_203820.csv`
- `analisis/25_referencia_combinada_regimen.py`
