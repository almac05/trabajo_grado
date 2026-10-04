# Verificación: ¿existe un proceso de búsqueda/ajuste de hiperparámetros?

**Alcance:** verificación de solo lectura sobre todo el repositorio (rama `consolidacion-evaluacion`). No se modificó, reentrenó ni ejecutó nada.

---

## Resultado: no existe ningún proceso de búsqueda de hiperparámetros en el repositorio

Se buscó explícitamente en `src/`, `scripts/`, `analisis/`, `notebooks/` y `tests/`:

- **Librerías de búsqueda:** `GridSearchCV`, `RandomizedSearchCV`, `optuna`, `hyperopt`, `ray.tune`, `BayesSearchCV`, `skopt` — **cero coincidencias** en todo el código del proyecto (la única coincidencia de la palabra "barrido" fue el comentario de `experimentos.py:201`, que se refiere al barrido de *ventana de entrenamiento*, no de hiperparámetros del modelo — ver más abajo).
- **Bucles manuales de barrido sobre hiperparámetros del modelo** (`for` sobre `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_lambda`, `min_child_weight`, unidades/capas de las redes, tasa de aprendizaje de las redes, `ParameterGrid`, `itertools.product`): **cero coincidencias**. Los únicos barridos persistidos en el repositorio (`analisis/salidas/barrido_*.csv`, `reports/tables/modeling/*rolling_bias*`) recorren exclusivamente la **ventana de entrenamiento** (semanas de historia), no los hiperparámetros del algoritmo.
- **Notebooks de experimentación:** las carpetas `notebooks/01_eda/`, `notebooks/02_preprocessing/`, `notebooks/03_modeling/` y `notebooks/04_evaluation/` existen pero **están vacías** — cada una contiene únicamente un `.gitkeep`, sin ningún `.ipynb`. No hay ningún archivo `.ipynb` en todo el repositorio.

**Los mismos valores de hiperparámetros aparecen repetidos como literales fijos en cuatro lugares del código, sin que ninguno derive de una búsqueda:**

| Archivo | Constante | Valores |
|---|---|---|
| `src/proyecto_grado/modeling/experimentos.py:204-216` | `PARAMS_XGB` | max_depth=5, min_child_weight=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0 (+ objective, eval_metric, n_estimators, early_stopping_rounds, random_state) |
| `src/proyecto_grado/modeling/xgboost_models.py:24-31` | `DEFAULT_XGBOOST_PARAMS` | mismos valores de max_depth, min_child_weight, learning_rate, subsample, colsample_bytree, reg_lambda |
| `scripts/run_xgboost_test_final.py:44-53` | `PARAMS` | mismos valores |
| `analisis/01_xgboost_un_fold.py:151-157` | (literal en línea, script exploratorio "paso a paso") | mismos valores |

Esta repetición idéntica en cuatro lugares, sin rastro de ningún proceso de búsqueda que los haya producido, es consistente con que los valores fueron elegidos manualmente una sola vez y luego copiados a los demás scripts, no derivados de un ajuste sistemático.

**El propio código documenta explícitamente que no hubo optimización de estos hiperparámetros.** Comentario en `src/proyecto_grado/modeling/experimentos.py:201-203`, inmediatamente antes de `PARAMS_XGB`:

> *"Configuracion adoptada tras el barrido de ventanas. Valores conservadores, sin optimizacion: la parada temprana detiene el entrenamiento muy por debajo del techo de arboles, lo que indica que el modelo converge por si solo."*

Es decir: lo único que se barrió sistemáticamente (y quedó persistido, ver `verificacion_config_redes_y_sesgo.md` y `tabla_ventana.md`) fue la **ventana de entrenamiento** (semanas de historia: 8/10/13/26/52/78/completo). Los hiperparámetros propios del algoritmo (`max_depth`, `min_child_weight`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_lambda`, y para las redes: unidades, número de capas, tasa de aprendizaje, tamaño de lote) se fijaron a mano, de forma "conservadora", sin búsqueda ni comparación entre alternativas.

Para LSTM, GRU y CNN-LSTM no hay siquiera un comentario equivalente: sus hiperparámetros (`UNIDADES = 64`, `LR = 0.001`, `EPOCAS = 3000`, `PACIENCIA = 30`, `FILTROS = 32`, `NUCLEO = 3` en CNN-LSTM) aparecen como constantes fijas al inicio de cada script (`scripts/run_{lstm,gru,cnn_lstm}_comparative_evaluation.py`), sin ningún proceso de búsqueda ni justificación documentada en el código más allá de ser el mismo valor en las tres redes.

---

## Commit y fecha desde los que estos valores permanecen sin cambios

`git log --follow` sobre `src/proyecto_grado/modeling/experimentos.py` y `src/proyecto_grado/modeling/xgboost_models.py` muestra que **ambos archivos fueron creados en un único commit y nunca modificados después**:

```
commit 6c771d0331b07c65704dc3693f39548729c748a0
Date:   2026-08-07 19:25:37 -0500
feat: modulo experimentos, barridos de ventana y test final XGBoost
```

`git diff 6c771d0 HEAD -- src/proyecto_grado/modeling/experimentos.py` no produce ninguna salida (diff vacío): **los valores de `PARAMS_XGB` no han cambiado desde el 7 de agosto de 2026 (commit `6c771d0`) hasta el estado actual de la rama `consolidacion-evaluacion`.**

`scripts/run_xgboost_test_final.py` fue introducido en ese mismo commit `6c771d0` con los mismos valores. `analisis/01_xgboost_un_fold.py` (el script exploratorio "paso a paso") es posterior en el árbol `analisis/`, pero reproduce los mismos números sin ninguna evidencia de que provengan de una búsqueda independiente.

**Conclusión:** no existe ningún proceso de búsqueda o ajuste de hiperparámetros (ni por librerías estándar, ni por bucles manuales, ni en notebooks) para XGBoost ni para las redes neuronales en este repositorio. Los valores de `PARAMS_XGB` están fijos y sin cambios desde el commit `6c771d0` (2026-08-07); el propio código los documenta como "conservadores" y explícitamente "sin optimización".
