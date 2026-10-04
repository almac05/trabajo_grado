# Verificación de ventana de entrenamiento, configuración de redes y sesgo del predictor de registro completo

**Alcance:** verificación de solo lectura sobre el freeze `freeze_20260823_203700`. No se modificó, reentrenó ni ejecutó nada del repositorio.

---

## 1. Ventana de entrenamiento efectivamente usada por método, vs. configuración

**Archivos verificados:** `configs/modeling/evaluacion_comparativa.yaml` (declaración) y `scripts/run_{sarima,prophet,xgboost,lstm,gru,cnn_lstm}_comparative_evaluation.py` (uso efectivo en código).

En los seis scripts, la ventana se lee siempre de la misma forma — sin overrides, constantes hardcodeadas alternativas ni ramas condicionales que la modifiquen:

```python
METODO = CONFIG.metodo("<Nombre>")
SEMANAS_ENTRENAMIENTO = METODO.semanas_entrenamiento
...
inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)
```

| Método | `semanas_entrenamiento` en `evaluacion_comparativa.yaml` | Línea de uso en el script | ¿Coincide? |
|---|---|---|---|
| SARIMA | 26 | `scripts/run_sarima_comparative_evaluation.py:96` | Sí |
| Prophet | 26 | `scripts/run_prophet_comparative_evaluation.py:95` | Sí |
| XGBoost | 26 | `scripts/run_xgboost_comparative_evaluation.py:65` | Sí |
| LSTM | 52 | `scripts/run_lstm_comparative_evaluation.py:177` | Sí |
| GRU | 52 | `scripts/run_gru_comparative_evaluation.py:177` | Sí |
| CNN-LSTM | 52 | `scripts/run_cnn_lstm_comparative_evaluation.py:180` | Sí |

**Conclusión:** la ventana de entrenamiento efectivamente usada coincide exactamente con `semanas_entrenamiento` del archivo de configuración para los seis métodos. El propio YAML lo documenta como decisión deliberada (línea 21-23): *"La asimetria es deliberada y documenta el protocolo efectivo vigente: los metodos clasicos usan 26 semanas y las redes neuronales usan 52. No debe interpretarse como una invitacion a unificar las ventanas."*

Nota aparte (no es una discrepancia, es otro concepto): en LSTM, GRU y CNN-LSTM esta ventana de 52 semanas es la ventana de **entrenamiento** del modelo en cada corte; es distinta de la ventana de **entrada/lookback** de la secuencia recurrente, que es de 1 jornada anterior completa (28 pasos) — ver también la respuesta previa sobre lookback.

---

## 2. Configuración completa de LSTM, GRU y CNN-LSTM

**Archivos:** `scripts/run_lstm_comparative_evaluation.py`, `scripts/run_gru_comparative_evaluation.py`, `scripts/run_cnn_lstm_comparative_evaluation.py`. Las tres redes comparten exactamente los mismos hiperparámetros de entrenamiento; solo cambia la capa recurrente (LSTM vs. GRU) y CNN-LSTM añade una capa convolucional previa.

| Hiperparámetro | Valor | Idéntico en las 3 redes |
|---|---|---|
| Capas recurrentes | 1 capa (`nn.LSTM`/`nn.GRU`, `batch_first=True`) | Sí |
| Unidades por capa (hidden size) | `UNIDADES = 64` | Sí |
| Capa de salida | `Linear(unidades + n_calendario → unidades)` + `ReLU` + `Linear(unidades → PASOS=28)` | Sí |
| Tasa de aprendizaje | `LR = 0.001` (optimizador `torch.optim.Adam`) | Sí |
| Tamaño de lote (batch) | **No hay minibatching**: cada jornada se entrena con un único modelo por (ruta, jornada, corte), y dentro de ese ajuste se usa *full-batch* — todo el conjunto de entrenamiento de esa ventana en un solo paso por época (no hay `DataLoader` ni parámetro `batch_size` en el código) | Sí |
| Épocas máximas | `EPOCAS = 3000` (techo; en la práctica casi siempre se detiene antes por parada temprana) | Sí |
| Criterio de parada temprana | Se separan las últimas `PARADA_SEMANAS = 2` semanas antes de la jornada a predecir como conjunto de validación. En cada época se calcula la pérdida de validación (MAE enmascarado); si no mejora respecto del mejor valor visto durante `PACIENCIA = 30` épocas consecutivas, se detiene el entrenamiento y se restaura el `state_dict` de la época con menor pérdida de validación | Sí |
| Semilla | `SEMILLA = 42` (`torch.manual_seed(42)` antes de instanciar cada modelo) | Sí |
| Función de pérdida | MAE enmascarado: `(|pred-real|·máscara).sum() / máscara.sum()`, excluyendo posiciones rellenadas | Sí |
| Dispositivo | `cuda` si disponible, si no `cpu` | Sí |
| Longitud de secuencia (PASOS) | `PASOS = 28` franjas (una jornada operativa) | Sí |
| Variables de calendario concatenadas | `dia_semana, es_fin_semana, es_festivo, dia_semana_sin, dia_semana_cos` | Sí |

---

## 3. CNN-LSTM: filtros y núcleo convolucional

**Archivo:** `scripts/run_cnn_lstm_comparative_evaluation.py`, líneas 51-53 y 114-137.

- **Número de filtros:** `FILTROS = 32` (canales de salida de la capa convolucional).
- **Tamaño del núcleo (kernel):** `NUCLEO = 3` (ventana de 3 franjas = hora y media, con `padding = NUCLEO // 2 = 1`, que preserva la longitud de la secuencia).
- **Arquitectura exacta de la capa convolucional:** `nn.Conv1d(in_channels=2, out_channels=32, kernel_size=3, padding=1)` seguida de `nn.ReLU()`. La salida (32 canales × 28 pasos) se transpone y se pasa como entrada a una capa `nn.LSTM(input_size=32, hidden_size=64, batch_first=True)` — es decir, la convolución sustituye a los 2 canales crudos de entrada (demanda + máscara) por una representación de 32 canales antes de entrar a la LSTM; el resto de la arquitectura (capa de salida, hiperparámetros de entrenamiento) es idéntico a LSTM/GRU.

---

## 4. Verificación del sesgo de 18,1 pasajeros atribuido al "promedio sobre el registro completo"

**Búsqueda realizada:** se buscó el valor 18,1 (con tolerancia ±0,05) en todos los artefactos agregados del freeze — `analisis/salidas/metricas__comparacion_modelos__freeze_20260823_203700__{global,tipo_dia,regimen}.csv`, `referencia_metricas_pre_consolidacion.csv`, `barrido_ventana_diario.csv`, `barrido_ventana_entrenamiento.csv` — bajo distintas agregaciones candidatas para "ventana = registro completo" (código `999` en los barridos de XGBoost, la única fuente persistida con una variante de ventana "completa").

**Resultado: no se reprodujo el valor 18,1 como una agregación de sesgo para el registro completo en ningún artefacto.** Agregaciones probadas explícitamente, todas calculadas por mí a partir de `analisis/salidas/barrido_ventana_diario.csv` y `barrido_ventana_entrenamiento.csv` (ventana=999, ponderando por `n`):

| Agregación candidata | Resultado |
|---|---|
| Sesgo medio, ventana completa, LABORAL, ruta 1 (ponderado por n) | 16,95 |
| Sesgo medio, ventana completa, LABORAL, ruta 3 (ponderado por n) | 17,35 |
| Sesgo medio, ventana completa, LABORAL, ambas rutas combinadas (ponderado por n) | 17,15 |
| Sesgo medio, ventana completa, todas las jornadas y rutas (ponderado por n) | 14,93 |
| Sesgo medio, ventana completa, todas las jornadas y rutas (media simple, no ponderada) | 13,61 |
| Sesgo medio, ventana completa, régimen `ordinario` (media simple sobre jornadas) | 14,36 |
| Sesgo medio, ventana completa, régimen `ordinario`, agregado por corte histórico de `barrido_ventana_entrenamiento.csv` (ponderado por n) | 8,73 |
| Sesgo medio, ventana completa, régimen `raro`, agregado por corte (ponderado por n) | 7,01 |

Ninguna de estas agregaciones razonables da 18,1. Lo único que se acerca son **valores de jornadas individuales** (no agregados) con ventana completa: XGBoost, ruta 1, 2026-04-13, LABORAL → sesgo = 18,19 (`barrido_ventana_diario.csv`, fila `1,2026-04-13,LABORAL,ordinario,999,...`); y ruta 3, 2026-04-14, LABORAL → sesgo = 18,19. Son coincidencias de una sola jornada, no un promedio, por lo que no corresponden a lo que el capítulo describe como "el sesgo atribuido al promedio sobre el registro completo".

**Conclusión:** el valor de 18,1 no se pudo trazar a ninguna agregación persistida ni recalculada del sesgo bajo ventana de entrenamiento completa. Se recomienda revisar la fuente de esa cifra en el borrador del capítulo — podría tratarse de un cálculo manual no persistido, de una definición de "registro completo" distinta a la ventana `999` de los scripts `analisis/`, o de una cifra de una ejecución que no dejó artefacto en el repositorio.
