# Analisis exploratorios

Este directorio conserva experimentos y diagnosticos exploratorios. El flujo
canonico de evaluacion comparativa ya no reside aqui: sus productores estan en
`scripts/run_*_comparative_evaluation.py`, el agregador es
`scripts/aggregate_comparative_metrics.py` y su contrato se encuentra en
`configs/modeling/evaluacion_comparativa.yaml`.

Las variantes `18_lstm_secuencia_semanal.py`,
`21_lstm_comparacion_relleno.py`, `22_lstm_grilla_horaria.py` y
`23_lstm_decoder_compartido.py` no forman parte de la comparacion canonica.
El experimento `16_lstm_medicion_costo.py` tampoco pertenece a ese flujo.

En `analisis/salidas/` son historicos los artefactos que no siguen los
patrones canonicos con version declarada. Esto incluye las predicciones de las
variantes exploratorias, `test_final_predicciones.csv` y los antiguos
`lstm_predicciones.csv` y `lstm_multiples_dias.csv`, que estan superados. Se
conservan para trazabilidad y no deben resolverse automaticamente como entrada
de la comparacion vigente.
