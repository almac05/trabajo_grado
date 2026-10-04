# Verificación de hiperparámetros de XGBoost, árboles entrenados, parada temprana y estadísticos de la variable objetivo

**Alcance:** verificación de solo lectura sobre el freeze `freeze_20260823_203700`. No se modificó, reentrenó ni ejecutó nada del repositorio.

---

## 1. Hiperparámetros de XGBoost: código vs. lista del capítulo

**Archivos:** `scripts/run_xgboost_comparative_evaluation.py` (usa `xgb.XGBRegressor(**PARAMS_XGB)` sin modificar ningún valor) y `src/proyecto_grado/modeling/experimentos.py:204-216`, donde está definido `PARAMS_XGB`:

```python
PARAMS_XGB = {
    "objective": "reg:absoluteerror",
    "eval_metric": "mae",
    "max_depth": 5,
    "min_child_weight": 5,
    "learning_rate": 0.05,
    "n_estimators": 2000,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "early_stopping_rounds": 50,
    "random_state": 42,
}
```

| Hiperparámetro (lista del capítulo) | Valor en el capítulo | Valor en el código | ¿Coincide? |
|---|---|---|---|
| objective | reg:absoluteerror | reg:absoluteerror | Sí |
| max_depth | 5 | 5 | Sí |
| min_child_weight | 5 | 5 | Sí |
| learning_rate | 0,05 | 0.05 | Sí |
| n_estimators | 2.000 | 2000 | Sí |
| subsample | 0,8 | 0.8 | Sí |
| colsample_bytree | 0,8 | 0.8 | Sí |
| reg_lambda | 1,0 | 1.0 | Sí |
| early_stopping_rounds | 50 | 50 | Sí |
| random_state | 42 | 42 | Sí |

**Discrepancias:** ninguna entre los diez hiperparámetros listados y el código.

**Hiperparámetro presente en el código y ausente de la lista del capítulo:** `"eval_metric": "mae"` — fija explícitamente la métrica de validación usada por la parada temprana (coherente con `objective: reg:absoluteerror`, que optimiza la mediana condicional). No aparece en la lista de diez del capítulo.

`scripts/run_xgboost_comparative_evaluation.py:80` instancia el modelo como `xgb.XGBRegressor(**PARAMS_XGB)` sin overrides adicionales, y `METODO.semanas_entrenamiento` / `METODO.semanas_parada_temprana` (26 semanas y 2 semanas respectivamente, ver también `verificacion_config_redes_y_sesgo.md`) se leen del mismo `configs/modeling/evaluacion_comparativa.yaml`. No hay ningún otro archivo de configuración que redefina `PARAMS_XGB`.

---

## 2. Número de árboles efectivamente entrenados

**Sí quedó persistido**, en la columna `arboles` de `analisis/salidas/resumen__xgboost__freeze_20260823_203700.csv` (una fila por ajuste diario; `arboles = modelo.best_iteration + 1`, ver `scripts/run_xgboost_comparative_evaluation.py:109`). Este archivo cubre el conjunto propio de XGBoost, **137 ajustes en total** (68 ruta 1 + 69 ruta 3 — el mismo conjunto de 137 jornadas descrito en informes previos, no las 134 jornadas comunes a los seis métodos).

| | n (ajustes) | Mínimo | Q1 | Mediana | Q3 | Máximo |
|---|---|---|---|---|---|---|
| Global (ambas rutas) | 137 | 56 | 102,0 | 142,0 | 176,0 | 383 |
| Ruta 1 | 68 | 56 | 89,75 | 115,5 | 162,75 | 357 |
| Ruta 3 | 69 | 78 | 122,0 | 152,0 | 192,0 | 383 |

**¿Difiere la distribución entre rutas?** Sí, de forma sistemática: la ruta 3 entrena más árboles en cada estadístico (mínimo, Q1, mediana, Q3 y máximo son todos mayores que en la ruta 1) — media 170,2 en ruta 3 frente a 138,8 en ruta 1 (desviación estándar similar, ~70 en ambas). Es decir, con la misma configuración de hiperparámetros, el ajuste diario de XGBoost converge sistemáticamente con más árboles en la ruta 3.

**Sobre el rango "129 a 165" citado en el capítulo:** no se reproduce como ninguna agregación directa de esta columna. Se probaron explícitamente estas combinaciones y ninguna da [129, 165]:

| Agregación probada | Resultado |
|---|---|
| Rango global (mín–máx) | 56–383 |
| RIC global (Q1–Q3) | 102,0–176,0 |
| Rango ruta 1 (mín–máx) | 56–357 |
| RIC ruta 1 (Q1–Q3) | 89,75–162,75 |
| Rango ruta 3 (mín–máx) | 78–383 |
| RIC ruta 3 (Q1–Q3) | 122,0–192,0 |
| RIC régimen "ordinario" (LABORAL+SABADO+DOMINGO), global | 103,5–177,5 |
| RIC LABORAL, ruta 1 | 91,5–161,25 |
| RIC LABORAL, ruta 3 | 122,75–195,25 |
| Media ± desviación estándar, global | 81,9–223,4 |
| `arboles` en `barrido_ventana_entrenamiento.csv`, ventana=26 semanas (agregado por corte histórico, no por jornada) | 107–601 |
| `xgb_n_estimators_xgboost_20260729.csv` (ejecución anterior, distinto run/target) | media 226–242, min 46, max 664 |

**Conclusión:** el rango [129, 165] no se explica por ninguna de estas agregaciones estándar (mín/máx, RIC, media±SD) sobre ninguna partición (global, por ruta, por régimen, por tipo de día) de la columna `arboles` persistida para el freeze, ni en la ejecución anterior de XGBoost. No es reproducible desde los artefactos disponibles.

---

## 3. Parada temprana: ¿bloque de validación separado?

**Sí.** `scripts/run_xgboost_comparative_evaluation.py:66-73`:

```python
corte_parada = inicio_dia - pd.Timedelta(weeks=PARADA_SEMANAS)
train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
fit   = train[train["timestamp"] < corte_parada]
stop  = train[train["timestamp"] >= corte_parada]
...
if len(test) < MIN_FRANJAS or len(fit) < 500 or len(stop) == 0:
    continue
modelo.fit(fit[features], fit[TARGET],
           eval_set=[(stop[features], stop[TARGET])], verbose=False)
```

- El bloque de entrenamiento de 26 semanas (`train`) se subdivide en `fit` (ajuste del modelo) y `stop` (validación para la parada temprana), cortando en `corte_parada`.
- **Extensión del bloque de validación:** `PARADA_SEMANAS = METODO.semanas_parada_temprana = 2` semanas (última porción de las 26 semanas de entrenamiento, inmediatamente anterior a la jornada a predecir).
- El ajuste se descarta si el bloque de validación queda vacío (`len(stop) == 0`) o si el bloque de ajuste tiene menos de 500 observaciones — es decir, la existencia de un bloque de validación no vacío es una condición obligatoria para que el ajuste se ejecute.
- Esta misma extensión de 2 semanas (`semanas_parada_temprana: 2`) es la que usan también LSTM, GRU y CNN-LSTM (ver `configs/modeling/evaluacion_comparativa.yaml`), con el mismo criterio de corte relativo a la jornada objetivo.

---

## 4. Media 99,1 y mediana 76,0 pasajeros por franja de la variable objetivo

**Búsqueda realizada** sobre la variable objetivo (`pasajeros_total`, columna `real` en los artefactos de predicciones) bajo múltiples subconjuntos candidatos, calculando media y mediana directamente:

| Subconjunto | n | Media | Mediana |
|---|---|---|---|
| Dataset completo de modelado (`modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet`, todas las franjas válidas, ambas rutas) | 38.931 | 130,12 | 127,00 |
| Freeze, todas las filas crudas, ambas rutas (3117) | 3117 | 109,36 | 105,00 |
| Freeze, soporte común de 134 jornadas, ambas rutas (3038) | 3038 | 109,15 | 105,00 |
| Freeze, ruta 1, crudo | 1536 | 101,05 | 101,00 |
| Freeze, ruta 3, crudo | 1581 | 117,43 | 110,00 |
| Freeze, régimen `ordinario` (soporte común) | 2907 | 112,74 | 108,00 |
| Freeze, régimen `raro` (soporte común) | 131 | 29,35 | 26,00 |
| Freeze, tipo_dia LABORAL (soporte común) | 2215 | 127,37 | 121,00 |
| Freeze, tipo_dia SABADO, ambas rutas (crudo) | 485 | 80,88 | 77,00 |
| Freeze, tipo_dia SABADO, ruta 1 | 241 | 74,38 | 74,00 |
| Freeze, tipo_dia SABADO, ruta 3 | 244 | 87,30 | 80,50 |
| Freeze, tipo_dia DOMINGO (soporte común) | 207 | 30,96 | 27,00 |

**Resultado: no se reprodujo la combinación exacta media = 99,1 / mediana = 76,0 en ningún subconjunto probado**, ni sobre el dataset completo de modelado ni sobre ninguna partición del freeze por ruta, régimen o tipo de día. El subconjunto más cercano en mediana es SABADO (ambas rutas, mediana 77,0), pero su media (80,88) no se acerca a 99,1; ningún otro subconjunto acerca ambos valores simultáneamente.

**Conclusión:** esta media y mediana no se pudieron trazar a ningún artefacto ni subconjunto verificable del freeze `freeze_20260823_203700` ni del dataset base de modelado. Se recomienda verificar directamente en el borrador del capítulo sobre qué variable, período o filtro se calcularon — podrían corresponder a una variable distinta (por ejemplo, pasajeros por despacho en vez de pasajeros totales), a un período de entrenamiento en vez de evaluación, o a un cálculo no persistido como artefacto.
