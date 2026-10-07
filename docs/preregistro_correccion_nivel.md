# Preregistro: corrección de nivel del predictor mixto

**Fecha:** 2026-10-06. Este documento se compromete antes de ejecutar cualquier cálculo de la fase 2. Ningún resultado de los candidatos 2 a 7 ni del candidato 9 existe en el momento de escribirlo.

## 0. Conocimiento previo declarado

- El diseño se motiva en lo observado en la extensión (2026-06-11 a 2026-10-03, `docs/verificaciones/evaluacion_extension_20260611_20261003.md`): sesgo positivo persistente de XGBoost y de las referencias tras la caída de la demanda, y Prophet como mejor método en MAE en ese período.
- Por eso la extensión **no** sirve para decidir nada: solo se usa como exploración, declarando que ya fue observada.
- Del período de evaluación (2026-04-02 a 2026-06-10) ya se conocen, con el dataset original del freeze, las métricas de XGBoost, Prophet, las referencias y el predictor mixto (candidato 1). No se conocen las de los candidatos corregidos ni la del promedio.
- El período de validación (2025-12-25 a 2026-04-01) es el mismo en que se seleccionaron los hiperparámetros y se calibraron los parámetros del módulo de recomendación. En ese período, los resultados del módulo son dentro de muestra respecto de su calibración.

## 1. Datos y predicciones base

- **Dataset:** `data/actualizacion_20261004/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (escenario `sin_oferta`, franjas de 30 min). Se registra su SHA-256.
- **Protocolo:** el del freeze `freeze_20260922_203820` (`proyecto_grado.modeling.hparam_search.reevaluacion.ejecutar_metodo`), sin modificarlo:
  - Reentrenamiento diario; jornada operativa desde las 04:00.
  - Ventana de entrenamiento de 26 semanas para XGBoost y Prophet; parada temprana de 2 semanas para XGBoost.
  - `min_franjas = 8`, paso de muestreo 1, rutas 1 y 3, objetivo `pasajeros_total`, tipos de baja frecuencia `FESTIVO` y `FESTIVO_PUENTE`, todo según `configs/modeling/evaluacion_comparativa.yaml`.
  - Hiperparámetros: los seleccionados por la búsqueda (`analisis/salidas/busqueda_hiperparametros`).
- **Rango:** una sola corrida continua, jornada a jornada, del **2025-11-27 al 2026-10-03**, extremos incluidos.
- **Métodos:** XGBoost, Prophet, referencia de 26 semanas y referencia de 52 semanas. Las redes (LSTM, GRU, CNN-LSTM) y SARIMA quedan fuera.
- **Referencias:** media histórica por tipo de día y franja con la fórmula del protocolo (media del tipo de día y la hora en la ventana; si falta, media de la ventana).
  - 26 semanas: la columna `pred_media` de la corrida de XGBoost.
  - 52 semanas: como GRU queda fuera, se calcula con la misma fórmula y una ventana de 52 semanas sobre las franjas de la corrida de XGBoost. La referencia de 26 semanas se genera y persiste, pero no es candidata ni entra en la selección.
- **Régimen:** raro si el tipo de día es `FESTIVO` o `FESTIVO_PUENTE`; ordinario en otro caso.
- **Soporte:** las jornadas de ruta predichas a la vez por XGBoost y por Prophet, con sus franjas. Los nueve candidatos se evalúan sobre exactamente las mismas franjas. Por no exigir el soporte de las redes, el soporte de cada período puede diferir del de los freezes anteriores; se informa su tamaño.
- **Arranque:** las jornadas del 2025-11-27 al 2025-12-24 solo alimentan las ventanas de corrección; no se evalúan ni se reportan.

## 2. Candidatos

En todos, salvo el 8 y el 9 en el régimen ordinario, la predicción del régimen raro es la referencia de 52 semanas. En todos, las franjas de régimen raro **no** se corrigen.

| # | Régimen ordinario | Régimen raro |
|---|---|---|
| 1 | XGBoost (mixto sin corrección) | Ref. 52 s |
| 2 | XGBoost × factor multiplicativo, ventana 7 días | Ref. 52 s |
| 3 | XGBoost × factor multiplicativo, ventana 14 días | Ref. 52 s |
| 4 | XGBoost × factor multiplicativo, ventana 28 días | Ref. 52 s |
| 5 | XGBoost − error medio, ventana 7 días | Ref. 52 s |
| 6 | XGBoost − error medio, ventana 14 días | Ref. 52 s |
| 7 | XGBoost − error medio, ventana 28 días | Ref. 52 s |
| 8 | Prophet | Ref. 52 s |
| 9 | (XGBoost + Prophet) / 2 | Ref. 52 s |

### Corrección (candidatos 2 a 7)

Para la jornada operativa *d* de la ruta *r* y una ventana de *k* ∈ {7, 14, 28} días:

- **Franjas de la ventana, W(r, d, k):** las franjas del soporte de la ruta *r*, de régimen ordinario, con jornada operativa en [*d* − *k*, *d* − 1] (días del calendario, extremos incluidos). Solo jornadas anteriores a *d*, ya cerradas.
- **Multiplicativa:** factor = Σ real / Σ pred_xgboost sobre W; predicción corregida = pred_xgboost × factor.
- **Aditiva:** error medio = media de (pred_xgboost − real) sobre W; predicción corregida = pred_xgboost − error medio.
- La corrección se calcula con la predicción de XGBoost sin corregir (no se encadenan correcciones) y se aplica a todas las franjas ordinarias de la jornada *d*.

## 3. Métricas

- Por franja: error = predicción − real.
- **MAE** = media de |error|; **sesgo** = media del error. Se informan además MedAE, RMSE y WAPE (100·Σ|error|/Σreal).
- **Agregado:** ambas rutas y ambos regímenes, todas las franjas del soporte del período. La selección y la confirmación usan solo el MAE y el sesgo agregados.
- Como descriptivos, sin intervenir en ninguna decisión: cortes por ruta y por régimen, con jornadas y franjas de cada celda.

## 4. Períodos y reglas de decisión

| Período | Fechas (incluidas) | Uso |
|---|---|---|
| Validación | 2025-12-25 a 2026-04-01 | Selección |
| Evaluación | 2026-04-02 a 2026-06-10 | Confirmación |
| Extensión | 2026-06-11 a 2026-10-03 | Exploración (ya observado) |

- **Selección (validación):** sea *M* el menor MAE agregado entre los nueve candidatos. Son finalistas los candidatos con MAE < 1,01 · *M* (diferencia relativa al mínimo menor del 1 %). Gana el finalista con menor |sesgo| agregado. Si solo hay un finalista, gana ese.
- **Confirmación (evaluación):** el elegido se confirma si cumple las dos condiciones frente al candidato 1:
  1. MAE agregado del elegido ≤ MAE agregado del candidato 1.
  2. |sesgo| agregado del elegido < |sesgo| agregado del candidato 1.

  Si el elegido es el candidato 1, la confirmación se reporta como «no aplica».
- **Exploración (extensión):** se reportan las métricas de los nueve candidatos, declarando que el período ya fue observado. No se extrae ninguna decisión de él.

## 5. Módulo de recomendación

- **Demandas:** las predicciones del candidato 1 y del elegido (una sola si coinciden), junto con la práctica real.
- **Parámetros:** los calibrados originales (`reports/tables/dispatch/parametros__recomendacion_despacho__freeze_20260922_203820.csv` y la capacidad conjunta de su manifiesto), sin recalibrar; política de festivos y servicio mínimo de `configs/dispatch/recomendacion.yaml`.
- **Tope:** sin tope (`usar_tope = false`), como el análisis 38.
- **Despachos reales:** el conjunto apto de la actualización (`data/actualizacion_20261004/processed/model_ready/despachos_model_ready_freeze_20261005_011520.parquet`), con el mismo tratamiento del script 42: se excluyen y se cuentan los despachos anteriores al primer bloque.
- **Salida:** la Tabla 2 (proporciones de franjas normales, sobrecargadas y subutilizadas, despachos y % de misma clase que la real), a escala de franja y de bloque horario, por ruta y para ambas rutas, en los tres períodos. Se informa también el ajuste de factibilidad.

## 6. Decisiones operativas que el encargo no fijaba

Se fijan aquí para que no se decidan después de ver resultados:

1. **Ventana sin franjas:** si W(r, d, k) está vacía, no se corrige la jornada (factor 1, ajuste 0). Se cuenta cuántas jornadas quedan así por candidato y período.
2. **Denominador no positivo:** si Σ pred_xgboost sobre W ≤ 0, el factor multiplicativo no se aplica (factor 1). Se cuenta.
3. **Sin truncamiento:** las predicciones corregidas no se truncan en cero, como no se truncan las de los métodos base. Se cuenta el número de franjas con predicción negativa por candidato y período. El módulo las recibe tal cual (rige el servicio mínimo).
4. **Empates exactos** en |sesgo| entre finalistas: gana el de menor número de candidato.
5. **La ventana** se mide en días del calendario y no en jornadas con datos: una ventana de 7 días puede contener menos de 7 jornadas de ruta.
6. **Las franjas de la ventana** son las del soporte (jornadas predichas por XGBoost y Prophet); en el arranque, el soporte se define igual.

## 7. Controles de implementación

No cambian el diseño; si alguno falla, se detiene la ejecución y se reporta.

- **Reproducción:** en la extensión, las predicciones de XGBoost y Prophet de la corrida continua deben coincidir con `predicciones__xgboost__extension_20260611_20261003.csv` y `predicciones__prophet__extension_20260611_20261003.csv` (mismo dataset y protocolo), con diferencia máxima < 1e-4 pasajeros.
- **Referencia de 52 s:** en las franjas comunes, debe coincidir con `pred_media` de `predicciones__gru__extension_20260611_20261003.csv`.
- **Candidato 1:** en la extensión, sobre el soporte común de ese análisis, debe reproducir el predictor mixto de `observaciones__extension_20260611_20261003.csv`.
- **Causalidad:** se verifica por construcción que ninguna corrección de la jornada *d* usa franjas con jornada ≥ *d*.

## 8. Ejecución y salidas (fase 2)

- Solo archivos nuevos: una configuración en `configs/modeling/`, un script de predicciones y otro de evaluación en `analisis/` (numerados a continuación del 42). No se modifica ningún archivo existente.
- Sufijo propio de las salidas: `correccion_nivel_20251127_20261003`, en `analisis/salidas/`, sin sobrescribir nada. Incluyen el manifiesto con el SHA-256 del dataset y los resultados de los controles.
- Reporte nuevo en `docs/verificaciones/` con:
  - las métricas de los nueve candidatos en los tres períodos;
  - el candidato elegido y los finalistas;
  - el resultado de la confirmación;
  - la Tabla 2 del módulo;
  - los conteos de la sección 6.
- Cualquier desviación de este documento que resulte necesaria durante la ejecución se detiene y se reporta antes de continuar.
