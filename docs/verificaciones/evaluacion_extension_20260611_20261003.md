# Evaluación fuera de muestra del sistema congelado: jornadas del 11 de junio al 3 de octubre de 2026

El período del 2026-06-11 al 2026-10-03 no intervino en ninguna decisión: ni en la búsqueda de hiperparámetros, ni en la selección de métodos, ni en la calibración del módulo de recomendación. Se evaluó todo el sistema congelado sobre el dataset de `data/actualizacion_20261004/`.

**Archivos nuevos:** `configs/modeling/evaluacion_extension_20260611_20261003.yaml`, `analisis/41_predicciones_extension.py` y `analisis/42_evaluacion_extension.py`, con sus salidas en `analisis/salidas/` (sufijo `__extension_20260611_20261003`). No se modificó ningún archivo, freeze ni configuración existentes, y no se hizo ningún commit.

## Resumen

| Conclusión del período de evaluación | ¿Se mantiene del 11 de junio al 3 de octubre? |
|---|---|
| XGBoost y la referencia de 26 s son equivalentes en MAE (diferencia < 2 %) | **No.** XGBoost es un 6,3 % mejor (29,83 frente a 31,84). |
| XGBoost tiene menor \|sesgo\| que las dos referencias y las tres redes | **No.** Sí frente a las referencias (14,4 frente a 20,2 y 29,7), pero no frente a las redes (9,8 a 11,0). |
| El predictor mixto supera a XGBoost en régimen raro | **Sí**, en MAE (8,33 frente a 14,48), MedAE, WAPE y \|sesgo\|, pero con solo 8 jornadas de ruta raras. |
| ¿El sesgo de las referencias es mayor que en evaluación? | **Sí**, en el global y en régimen ordinario: 26 s de +6,3 a +20,2, 52 s de +12,5 a +29,7 y combinada de +5,9 a +20,2. En régimen raro, el de 26 s baja (de +11,0 a +1,1) y el de 52 s sube levemente (de +1,7 a +2,3). |

**Contexto:**
- La demanda media por franja cae de 109,1 a 90,5 pasajeros (−17 %), y los despachos por día laboral caen entre un 27 % y un 28 % (ver `comparacion_periodos_rutas_1_3_20261004.md`).
- Los métodos que se apoyan en la media histórica o en ventanas largas sobreestiman: las dos referencias, la combinada, XGBoost y las redes, que usan 52 semanas.
- Prophet pasa del penúltimo puesto en MAE al primero (27,66).
- En la recomendación, la sobreestimación de la predicción mixta lleva a recomendar un 16 % más de despachos que los reales, y las franjas subutilizadas suben del 23 % al 47 %.

## 1. Montaje: todo congelado

- **Protocolo:** el mismo que generó `freeze_20260922_203820` (`hparam_search.reevaluacion.ejecutar_metodo`), sin modificarlo:
  - Reentrenamiento diario.
  - Ventanas de 26 semanas para SARIMA, Prophet y XGBoost, y de 52 para LSTM, GRU y CNN-LSTM.
  - Parada temprana de 2 semanas para XGBoost y las redes.
  - `min_franjas = 8` y paso de muestreo 1.
  - Referencias: media por tipo de día y franja con la ventana de su método (26 s desde XGBoost, 52 s desde GRU).
- **Hiperparámetros:** las configuraciones seleccionadas por la búsqueda (`analisis/salidas/busqueda_hiperparametros/seleccion__*.json`).
- **Configuración:** el YAML nuevo solo declara el período, el dataset y el sufijo. El resto del contrato sale sin cambios de `configs/modeling/evaluacion_comparativa.yaml`.
- **Verificación de reproducción:** antes de predecir, se volvió a ejecutar XGBoost en el período de evaluación original con el dataset original y se comparó con el freeze.
  - Las 3.117 franjas coinciden.
  - La referencia de 26 s y la demanda real son idénticas.
  - `pred_xgboost` difiere como máximo en 1,5·10⁻⁵, por el redondeo a float32 con que el freeze guardó esa columna.
- **Predictores derivados:**
  - Referencia combinada: 26 s en régimen ordinario y 52 s en raro. En el freeze coincide franja a franja con la del script 25.
  - Predictor mixto: XGBoost en régimen ordinario y referencia de 52 s en raro.
- **Comprobación de las métricas:** la misma función reproduce exactamente las métricas publicadas del período de evaluación, incluidas las del script 33.
- **Soporte común:** 212 jornadas de ruta y 4.729 franjas, las mismas para los diez predictores.
- **Duración:** 39 minutos de cómputo: SARIMA 12,1 min, Prophet 3,2, XGBoost 2,1, LSTM 5,5, GRU 7,2 y CNN-LSTM 8,8.

## 2. Composición del período

| Tipo de día | Días del calendario | Jornadas ruta en el dataset | Jornadas ruta en el soporte común |
|---|---|---|---|
| DOMINGO | 16 | 32 | 25 |
| FESTIVO | 1 | 2 | 0 |
| FESTIVO_PUENTE | 4 | 8 | 8 |
| LABORAL | 77 | 154 | 147 |
| SABADO | 17 | 34 | 32 |
| Total | 115 | 230 | 212 |

- **Días del calendario:** 115 (del 11 de junio al 3 de octubre).
- **Régimen raro:** 4 lunes festivos (`FESTIVO_PUENTE`: 15 y 29 de junio, 20 de julio y 17 de agosto), las 8 jornadas de ruta en el soporte común, y el festivo del viernes 7 de agosto.
- **El 7 de agosto** queda fuera del soporte en las dos rutas, como 7 domingos de la ruta 1 y 2 de la ruta 3. En esas jornadas solo hubo entre 3 y 7 franjas con despachos, menos que el mínimo de 8 del protocolo.
- **Las 9 jornadas siguientes** a esas tampoco las predicen las redes, porque necesitan la jornada previa completa. Por eso el soporte común baja de 221 a 212 jornadas.
- **Tamaño del régimen raro:** se apoya en 8 jornadas de ruta (82 franjas), frente a 10 en el período de evaluación. Sus conclusiones son frágiles.

## 3. Métricas globales: evaluación → extensión

Evaluación: 134 jornadas y 3038 franjas, demanda media 109,1. Extensión: 212 jornadas y 4729 franjas, demanda media 90,5.

| Método | MAE | MedAE | RMSE | WAPE (%) | Sesgo |
|---|---|---|---|---|---|
| SARIMA | 48,07 → 39,84 | 40,47 → 33,69 | 61,81 → 51,22 | 44,04 → 44,04 | −2,15 → 0,01 |
| Prophet | 30,63 → 27,66 | 24,79 → 22,82 | 39,78 → 35,91 | 28,06 → 30,58 | 0,69 → 0,01 |
| XGBoost | 28,34 → 29,83 | 21,96 → 24,37 | 37,32 → 38,17 | 25,97 → 32,97 | 2,34 → 14,41 |
| LSTM | 29,11 → 32,34 | 23,06 → 24,87 | 38,56 → 43,02 | 26,67 → 35,75 | 3,97 → 10,95 |
| GRU | 29,59 → 32,11 | 23,44 → 24,71 | 39,12 → 42,58 | 27,11 → 35,49 | 3,70 → 9,84 |
| CNN-LSTM | 29,68 → 32,87 | 23,55 → 25,72 | 39,24 → 43,37 | 27,19 → 36,34 | 3,97 → 10,24 |
| Referencia (26s) | 28,36 → 31,84 | 21,88 → 25,05 | 37,31 → 41,06 | 25,98 → 35,20 | 6,26 → 20,19 |
| Referencia (52s) | 29,34 → 37,39 | 22,91 → 30,51 | 38,49 → 47,33 | 26,88 → 41,33 | 12,50 → 29,74 |
| Combinada (26s/52s) | 27,81 → 31,82 | 21,63 → 25,03 | 36,54 → 41,04 | 25,48 → 35,17 | 5,86 → 20,21 |
| Mixto (XGBoost ordinario / 52s raro) | 28,32 → 29,72 | 21,97 → 24,20 | 37,32 → 38,12 | 25,95 → 32,85 | 2,20 → 14,26 |

Sesgo = predicción − real; WAPE = 100·Σ|error|/Σreal.

**Ordenamiento por MAE:**
- Evaluación: Combinada (26s/52s) (27,81) < Mixto (XGBoost ordinario / 52s raro) (28,32) < XGBoost (28,34) < Referencia (26s) (28,36) < LSTM (29,11) < Referencia (52s) (29,34) < GRU (29,59) < CNN-LSTM (29,68) < Prophet (30,63) < SARIMA (48,07).
- Extensión: Prophet (27,66) < Mixto (XGBoost ordinario / 52s raro) (29,72) < XGBoost (29,83) < Combinada (26s/52s) (31,82) < Referencia (26s) (31,84) < GRU (32,11) < LSTM (32,34) < CNN-LSTM (32,87) < Referencia (52s) (37,39) < SARIMA (39,84).

**Lectura:**
- Prophet mejora y pasa al primer puesto, mientras que la referencia combinada, que era la mejor, cae al cuarto.
- El predictor mixto y XGBoost quedan segundo y tercero, separados por solo 0,1.
- Las tres redes quedan por detrás de la referencia de 26 s.
- El sesgo global casi nulo de SARIMA (+0,01) y de Prophet (+0,01) resulta de compensar errores de signo opuesto:

  | Mes | SARIMA | Prophet |
  |---|---|---|
  | Junio | +3,4 | +1,0 |
  | Octubre | −7,6 | −3,5 |

- El sesgo de XGBoost es positivo en todos los meses:

  | Mes | Junio | Julio | Agosto | Septiembre | Octubre |
  |---|---|---|---|---|---|
  | Sesgo de XGBoost | +8,8 | +15,5 | +18,4 | +14,7 | +5,5 |

  Es máximo cuando la demanda media es más baja: 84,5 pasajeros por franja en agosto, frente a 98,0 en junio.

## 4. Métricas de la extensión por ruta, régimen y tipo de día

### Por ruta

| Ruta | Jornadas / franjas | Método | MAE | MedAE | RMSE | WAPE (%) | Sesgo |
|---|---|---|---|---|---|---|---|
| 1 | 103 / 2321 | SARIMA | 33,42 | 29,78 | 41,21 | 40,79 | 3,91 |
| 1 | 103 / 2321 | Prophet | 25,97 | 21,99 | 33,38 | 31,70 | −0,49 |
| 1 | 103 / 2321 | XGBoost | 28,88 | 23,62 | 36,50 | 35,24 | 15,40 |
| 1 | 103 / 2321 | LSTM | 28,76 | 22,52 | 37,32 | 35,10 | 10,91 |
| 1 | 103 / 2321 | GRU | 28,46 | 23,06 | 36,75 | 34,73 | 9,06 |
| 1 | 103 / 2321 | CNN-LSTM | 29,13 | 23,26 | 37,38 | 35,55 | 9,36 |
| 1 | 103 / 2321 | Referencia (26s) | 30,14 | 24,52 | 38,04 | 36,78 | 18,89 |
| 1 | 103 / 2321 | Referencia (52s) | 35,09 | 29,90 | 43,61 | 42,83 | 27,77 |
| 1 | 103 / 2321 | Combinada (26s/52s) | 30,09 | 24,49 | 37,99 | 36,73 | 18,91 |
| 1 | 103 / 2321 | Mixto (XGBoost ordinario / 52s raro) | 28,80 | 23,59 | 36,47 | 35,15 | 15,31 |
| 3 | 109 / 2408 | SARIMA | 46,03 | 38,68 | 59,29 | 46,63 | −3,74 |
| 3 | 109 / 2408 | Prophet | 29,29 | 24,07 | 38,19 | 29,68 | 0,49 |
| 3 | 109 / 2408 | XGBoost | 30,74 | 24,74 | 39,72 | 31,15 | 13,46 |
| 3 | 109 / 2408 | LSTM | 35,79 | 27,18 | 47,87 | 36,26 | 11,00 |
| 3 | 109 / 2408 | GRU | 35,63 | 27,14 | 47,53 | 36,10 | 10,60 |
| 3 | 109 / 2408 | CNN-LSTM | 36,48 | 27,91 | 48,45 | 36,96 | 11,10 |
| 3 | 109 / 2408 | Referencia (26s) | 33,49 | 26,00 | 43,78 | 33,93 | 21,44 |
| 3 | 109 / 2408 | Referencia (52s) | 39,60 | 31,66 | 50,65 | 40,12 | 31,64 |
| 3 | 109 / 2408 | Combinada (26s/52s) | 33,49 | 25,94 | 43,77 | 33,93 | 21,47 |
| 3 | 109 / 2408 | Mixto (XGBoost ordinario / 52s raro) | 30,61 | 24,71 | 39,64 | 31,01 | 13,26 |

### Por régimen

| Régimen | Jornadas / franjas | Método | MAE | MedAE | RMSE | WAPE (%) | Sesgo |
|---|---|---|---|---|---|---|---|
| ordinario | 204 / 4647 | SARIMA | 39,35 | 33,11 | 50,83 | 42,96 | −1,18 |
| ordinario | 204 / 4647 | Prophet | 27,93 | 23,12 | 36,16 | 30,49 | 0,08 |
| ordinario | 204 / 4647 | XGBoost | 30,10 | 24,69 | 38,43 | 32,86 | 14,47 |
| ordinario | 204 / 4647 | LSTM | 32,59 | 25,12 | 43,26 | 35,58 | 10,96 |
| ordinario | 204 / 4647 | GRU | 32,17 | 24,71 | 42,66 | 35,12 | 9,58 |
| ordinario | 204 / 4647 | CNN-LSTM | 32,95 | 25,85 | 43,40 | 35,97 | 10,00 |
| ordinario | 204 / 4647 | Referencia (26s) | 32,24 | 25,68 | 41,38 | 35,19 | 20,53 |
| ordinario | 204 / 4647 | Referencia (52s) | 37,90 | 31,12 | 47,72 | 41,38 | 30,22 |
| ordinario | 204 / 4647 | Combinada (26s/52s) | 32,24 | 25,68 | 41,38 | 35,19 | 20,53 |
| ordinario | 204 / 4647 | Mixto (XGBoost ordinario / 52s raro) | 30,10 | 24,69 | 38,43 | 32,86 | 14,47 |
| raro | 8 / 82 | SARIMA | 67,63 | 69,12 | 69,63 | 256,03 | 67,63 |
| raro | 8 / 82 | Prophet | 12,52 | 9,33 | 16,39 | 47,39 | −3,85 |
| raro | 8 / 82 | XGBoost | 14,48 | 14,11 | 18,98 | 54,81 | 10,82 |
| raro | 8 / 82 | LSTM | 18,19 | 11,51 | 26,05 | 68,86 | 10,40 |
| raro | 8 / 82 | GRU | 28,80 | 23,43 | 37,96 | 109,01 | 24,84 |
| raro | 8 / 82 | CNN-LSTM | 28,42 | 16,48 | 41,94 | 107,59 | 23,80 |
| raro | 8 / 82 | Referencia (26s) | 9,63 | 6,67 | 14,54 | 36,45 | 1,06 |
| raro | 8 / 82 | Referencia (52s) | 8,33 | 6,99 | 10,77 | 31,52 | 2,35 |
| raro | 8 / 82 | Combinada (26s/52s) | 8,33 | 6,99 | 10,77 | 31,52 | 2,35 |
| raro | 8 / 82 | Mixto (XGBoost ordinario / 52s raro) | 8,33 | 6,99 | 10,77 | 31,52 | 2,35 |

### Por tipo de día

| Tipo de día | Jornadas / franjas | Método | MAE | MedAE | RMSE | WAPE (%) | Sesgo |
|---|---|---|---|---|---|---|---|
| DOMINGO | 25 / 278 | SARIMA | 66,29 | 64,89 | 69,53 | 238,32 | 66,29 |
| DOMINGO | 25 / 278 | Prophet | 14,39 | 10,66 | 19,86 | 51,72 | 3,92 |
| DOMINGO | 25 / 278 | XGBoost | 9,10 | 8,11 | 11,50 | 32,71 | 2,40 |
| DOMINGO | 25 / 278 | LSTM | 10,16 | 8,31 | 13,04 | 36,51 | 2,76 |
| DOMINGO | 25 / 278 | GRU | 13,36 | 8,43 | 23,20 | 48,01 | 5,39 |
| DOMINGO | 25 / 278 | CNN-LSTM | 14,30 | 8,87 | 24,61 | 51,41 | 6,42 |
| DOMINGO | 25 / 278 | Referencia (26s) | 9,81 | 9,05 | 11,90 | 35,27 | 4,12 |
| DOMINGO | 25 / 278 | Referencia (52s) | 11,09 | 10,55 | 12,91 | 39,88 | 6,69 |
| DOMINGO | 25 / 278 | Combinada (26s/52s) | 9,81 | 9,05 | 11,90 | 35,27 | 4,12 |
| DOMINGO | 25 / 278 | Mixto (XGBoost ordinario / 52s raro) | 9,10 | 8,11 | 11,50 | 32,71 | 2,40 |
| FESTIVO_PUENTE | 8 / 82 | SARIMA | 67,63 | 69,12 | 69,63 | 256,03 | 67,63 |
| FESTIVO_PUENTE | 8 / 82 | Prophet | 12,52 | 9,33 | 16,39 | 47,39 | −3,85 |
| FESTIVO_PUENTE | 8 / 82 | XGBoost | 14,48 | 14,11 | 18,98 | 54,81 | 10,82 |
| FESTIVO_PUENTE | 8 / 82 | LSTM | 18,19 | 11,51 | 26,05 | 68,86 | 10,40 |
| FESTIVO_PUENTE | 8 / 82 | GRU | 28,80 | 23,43 | 37,96 | 109,01 | 24,84 |
| FESTIVO_PUENTE | 8 / 82 | CNN-LSTM | 28,42 | 16,48 | 41,94 | 107,59 | 23,80 |
| FESTIVO_PUENTE | 8 / 82 | Referencia (26s) | 9,63 | 6,67 | 14,54 | 36,45 | 1,06 |
| FESTIVO_PUENTE | 8 / 82 | Referencia (52s) | 8,33 | 6,99 | 10,77 | 31,52 | 2,35 |
| FESTIVO_PUENTE | 8 / 82 | Combinada (26s/52s) | 8,33 | 6,99 | 10,77 | 31,52 | 2,35 |
| FESTIVO_PUENTE | 8 / 82 | Mixto (XGBoost ordinario / 52s raro) | 8,33 | 6,99 | 10,77 | 31,52 | 2,35 |
| LABORAL | 147 / 3652 | SARIMA | 37,97 | 30,76 | 50,47 | 37,94 | −10,45 |
| LABORAL | 147 / 3652 | Prophet | 29,87 | 25,80 | 38,18 | 29,84 | 0,85 |
| LABORAL | 147 / 3652 | XGBoost | 33,18 | 28,41 | 41,39 | 33,15 | 17,01 |
| LABORAL | 147 / 3652 | LSTM | 35,71 | 28,89 | 46,33 | 35,68 | 14,94 |
| LABORAL | 147 / 3652 | GRU | 34,97 | 27,94 | 45,37 | 34,95 | 13,14 |
| LABORAL | 147 / 3652 | CNN-LSTM | 35,36 | 28,30 | 45,73 | 35,33 | 13,52 |
| LABORAL | 147 / 3652 | Referencia (26s) | 35,61 | 29,62 | 44,69 | 35,59 | 23,86 |
| LABORAL | 147 / 3652 | Referencia (52s) | 42,15 | 36,57 | 51,74 | 42,12 | 34,54 |
| LABORAL | 147 / 3652 | Combinada (26s/52s) | 35,61 | 29,62 | 44,69 | 35,59 | 23,86 |
| LABORAL | 147 / 3652 | Mixto (XGBoost ordinario / 52s raro) | 33,18 | 28,41 | 41,39 | 33,15 | 17,01 |
| SABADO | 32 / 717 | SARIMA | 35,90 | 33,73 | 43,59 | 49,08 | 19,86 |
| SABADO | 32 / 717 | Prophet | 23,32 | 18,46 | 29,96 | 31,89 | −5,35 |
| SABADO | 32 / 717 | XGBoost | 22,56 | 19,78 | 28,16 | 30,84 | 6,25 |
| SABADO | 32 / 717 | LSTM | 25,39 | 19,93 | 33,62 | 34,72 | −6,10 |
| SABADO | 32 / 717 | GRU | 25,16 | 20,63 | 33,19 | 34,40 | −6,96 |
| SABADO | 32 / 717 | CNN-LSTM | 27,91 | 22,19 | 36,33 | 38,16 | −6,51 |
| SABADO | 32 / 717 | Referencia (26s) | 23,73 | 20,58 | 29,48 | 32,45 | 9,91 |
| SABADO | 32 / 717 | Referencia (52s) | 26,63 | 23,45 | 32,56 | 36,41 | 17,38 |
| SABADO | 32 / 717 | Combinada (26s/52s) | 23,73 | 20,58 | 29,48 | 32,45 | 9,91 |
| SABADO | 32 / 717 | Mixto (XGBoost ordinario / 52s raro) | 22,56 | 19,78 | 28,16 | 30,84 | 6,25 |

`FESTIVO` no aparece porque su única fecha (7 de agosto) quedó fuera del soporte común.

## 5. Contraste de conclusiones

1. **Equivalencia en MAE entre XGBoost y la referencia de 26 s: no se mantiene, a favor de XGBoost.**
   - En evaluación la diferencia era del −0,05 % (28,34 frente a 28,36).
   - En la extensión es del −6,3 % (29,83 frente a 31,84), más del triple del umbral del 2 %.
   - La referencia histórica pierde más precisión que XGBoost cuando cae la demanda.
2. **Menor |sesgo| de XGBoost que las referencias y las redes: no se mantiene.**
   - XGBoost sigue con menos sesgo que las referencias: 14,4 frente a 20,2 y 29,7.
   - Pero queda por encima de LSTM (11,0), GRU (9,8) y CNN-LSTM (10,2).
   - En el período de evaluación era 2,3 frente a 3,7–4,0 de las redes.
3. **El predictor mixto supera a XGBoost en régimen raro: se mantiene.**
   - MAE 8,33 frente a 14,48, MedAE 6,99 frente a 14,11, WAPE 31,5 % frente a 54,8 % y sesgo +2,3 frente a +10,8.
   - También queda por delante en el global (29,72 frente a 29,83).
   - La muestra rara es de 8 jornadas de ruta.
4. **El sesgo de las referencias es mayor que en evaluación: sí, en el global y en régimen ordinario.**

   | Referencia | Global | Régimen ordinario | Régimen raro |
   |---|---|---|---|
   | 26 s | +6,26 → +20,19 | +6,04 → +20,53 | +11,03 → +1,06 (baja) |
   | 52 s | +12,50 → +29,74 | +12,99 → +30,22 | +1,74 → +2,35 |
   | Combinada | +5,86 → +20,21 | +6,04 → +20,53 | +1,74 → +2,35 |

## 6. Módulo de recomendación, sin recalibrar

- **Parámetros:** los calibrados originalmente con los datos del 2025-12-25 al 2026-04-01 (`reports/tables/dispatch/parametros__recomendacion_despacho__freeze_20260922_203820.csv`), con capacidad conjunta de 153 despachos, política `divisor_propio` y servicio mínimo 1.
- **Despachos reales:** del conjunto apto de la actualización.
- **Demandas evaluadas:** la de la predicción mixta, la demanda real (cota superior) y la referencia de 26 s, sobre las 4.729 franjas del soporte común.
- **Tope:** se presentan los dos ajustes de tope, porque el análisis 38 se hizo sin tope y la configuración por defecto lo activa.
- **Exclusiones:**
  - 1 despacho de la ruta 3 a las 03:30 del 24 de junio, anterior al primer bloque horario.
  - 24 franjas reales, con un despacho cada una, que están fuera de las franjas predichas.

### Tabla 2, ambas rutas, sin tope (como el análisis 38)

| Escala | Origen | Unidades | % normal | % sobrecargada | % subutilizada | Despachos | % misma clase que la real |
|---|---|---|---|---|---|---|---|
| franja | práctica real | 4729 | 54,6 | 22,1 | 23,3 | 9.176 | — |
| franja | predicción mixta | 4729 | 37,3 | 16,1 | 46,5 | 10.683 | 55,6 |
| franja | demanda real (cota) | 4729 | 70,8 | 13,6 | 15,7 | 9.388 | 78,0 |
| franja | referencia 26 s | 4729 | 36,3 | 11,9 | 51,7 | 11.406 | 52,9 |
| bloque | práctica real | 1163 | 70,2 | 9,2 | 20,6 | 9.176 | — |
| bloque | predicción mixta | 1163 | 53,9 | 6,4 | 39,7 | 10.683 | 62,4 |
| bloque | demanda real (cota) | 1163 | 85,4 | 2,8 | 11,9 | 9.388 | 81,9 |
| bloque | referencia 26 s | 1163 | 44,4 | 5,2 | 50,5 | 11.406 | 54,4 |

### Tabla 2, ambas rutas, con tope (configuración por defecto)

| Escala | Origen | Unidades | % normal | % sobrecargada | % subutilizada | Despachos | % misma clase que la real |
|---|---|---|---|---|---|---|---|
| franja | práctica real | 4729 | 54,6 | 22,1 | 23,3 | 9.176 | — |
| franja | predicción mixta | 4729 | 35,0 | 12,6 | 52,4 | 11.267 | 52,3 |
| franja | demanda real (cota) | 4729 | 71,9 | 0,3 | 27,8 | 10.016 | 73,5 |
| franja | referencia 26 s | 4729 | 33,7 | 9,2 | 57,1 | 11.946 | 49,7 |
| bloque | práctica real | 1163 | 70,2 | 9,2 | 20,6 | 9.176 | — |
| bloque | predicción mixta | 1163 | 45,9 | 4,2 | 49,9 | 11.267 | 56,9 |
| bloque | demanda real (cota) | 1163 | 80,7 | 0,2 | 19,1 | 10.016 | 81,9 |
| bloque | referencia 26 s | 1163 | 36,8 | 2,4 | 60,8 | 11.946 | 48,9 |

### Tabla 2 por ruta, sin tope (% normal / % sobrecargada / % subutilizada)

| Escala | Ruta | Práctica real | Predicción mixta | Demanda real (cota) | Referencia 26 s |
|---|---|---|---|---|---|
| franja | 1 | 53,6 / 23,3 / 23,1 | 34,1 / 15,0 / 50,9 | 69,6 / 15,5 / 15,0 | 33,0 / 11,9 / 55,1 |
| franja | 3 | 55,5 / 20,9 / 23,6 | 40,4 / 17,2 / 42,3 | 71,9 / 11,8 / 16,4 | 39,5 / 12,0 / 48,5 |
| bloque | 1 | 68,0 / 10,7 / 21,3 | 46,5 / 5,1 / 48,4 | 83,6 / 4,4 / 12,1 | 36,5 / 4,7 / 58,7 |
| bloque | 3 | 72,4 / 7,8 / 19,8 | 61,1 / 7,6 / 31,3 | 87,1 / 1,2 / 11,7 | 51,9 / 5,6 / 42,5 |

### Ajuste de factibilidad

| Tope | Variante | Fechas | Jornadas ajustadas | Despachos retirados | No factibles |
|---|---|---|---|---|---|
| no | mixta | 109 | 0 | 0 | 0 |
| no | real | 109 | 0 | 0 | 0 |
| no | ref26 | 109 | 0 | 0 | 0 |
| sí | mixta | 109 | 0 | 0 | 0 |
| sí | real | 109 | 0 | 0 | 0 |
| sí | ref26 | 109 | 0 | 0 | 0 |

**Ninguna de las 109 fechas necesitó el ajuste de factibilidad** con ninguna variante: con la reducción de la operación, los totales recomendados nunca alcanzan la capacidad de 153 despachos.

**Lectura frente al análisis 38** (período de evaluación, sin tope, escala franja):

| Escala franja | Normal | Sobrecargada | Subutilizada |
|---|---|---|---|
| Práctica real, evaluación | 61,0 % | 16,2 % | 22,8 % |
| Práctica real, extensión | 54,6 % | 22,1 % | 23,3 % |
| Predicción mixta, evaluación | 42,7 % | 23,5 % | 33,8 % |
| Predicción mixta, extensión | 37,3 % | 16,1 % | 46,5 % |

- **Práctica real:** empeora en la extensión, con más franjas sobrecargadas (22,1 % frente a 16,2 %).
- **Predicción mixta:** recomienda 10.683 despachos frente a 9.176 reales (+16 %), y casi la mitad de las franjas quedarían subutilizadas. Es la consecuencia de su sesgo de +14 pasajeros por franja.
- **Referencia de 26 s:** sobreestima más y empeora aún más: 11.406 despachos y un 51,7 % de franjas subutilizadas.
- **Cota superior con demanda real:** mejora la práctica real (70,8 % de franjas normales frente a 54,6 %), como en evaluación (77,8 %).
- **Conclusión:** la regla funciona con la demanda correcta; lo que falla en este período es el pronóstico.

## Salidas

En `analisis/salidas/`, con el sufijo `__extension_20260611_20261003`:
- **Predicciones (script 41):**
  - `predicciones__<metodo>__...csv` y `resumen__<metodo>__...csv` de los seis métodos.
  - `jornadas_comunes__...csv`.
  - `manifiesto__predicciones__...json`, con los hiperparámetros, las ventanas, la verificación de reproducción y el SHA-256 del dataset.
- **Evaluación (script 42):**
  - `metricas__...csv`: los dos períodos y los cuatro cortes, con jornadas y franjas.
  - `contraste__...json`, `jornadas_tipo_dia__...csv` y `observaciones__...csv`: la tabla franja a franja de los diez predictores.
  - `clasificacion_recomendacion__...csv`: la Tabla 2 por ruta y bloque.
  - `proporciones_recomendacion__...csv`, `ajuste_factibilidad__...csv` y `manifiesto__...json`.
