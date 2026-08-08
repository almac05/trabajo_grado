# Paquete de revision de modelado Montebello

Creado: 2026-07-18 18:11:17

## Proposito

Este paquete recopila los artefactos necesarios para revisar externamente el estado actual de la fase de modelado predictivo: configuraciones, codigo, scripts, metricas, backtesting, predicciones, analisis de errores, figuras, metadatos y pruebas.

No contiene datasets crudos ni archivos model-ready completos. Los archivos originales del proyecto no fueron modificados para crear este paquete.

## Estructura

- `configs/`: configuraciones reproducibles de objetivo, backtesting y modelos.
- `src/`: codigo fuente del paquete `proyecto_grado.modeling`.
- `scripts/`: entrypoints de construccion, backtesting, evaluacion y reporte.
- `reports/tables/`: metricas, predicciones, folds y analisis de errores.
- `reports/figures/`: figuras de comparacion, errores, residuals y folds.
- `models/metadata/`: metadata del dataset y corrida disponible.
- `logs/`: logs de modelado si existian; incluye marcador si no se encontraron.
- `tests/`: pruebas unitarias relacionadas con metricas, splits, baselines y anti-fuga.
- `muestras/`: muestra CSV de predicciones para inspeccion rapida.

## Dataset y snapshot

- Snapshot: `freeze_20260610_192142`
- Fuente declarada: `C:\Users\regis\proyecto_grado\data\processed\model_ready\despachos_model_ready_freeze_20260610_192142.parquet`
- Hash fuente SHA-256: `a85ce076cb840d4ea9660f416e986329896163ece324e9d8ddc8449512e0f53a`
- Granularidad: `30` minutos
- Objetivo: `pasajeros_total`
- Rutas: `[1, 3]`

## Modelos incluidos

- `historical_average_route_day_type_slot`
- `naive`
- `seasonal_naive_daily`
- `seasonal_naive_weekly`

## Metricas incluidas

- `mae`
- `rmse`
- `smape`
- `wape`
- `bias_mean`

## Como revisar

Orden recomendado:

1. `informe_codex.txt`
2. `reports/tables/modeling/metrics_comparison.csv`
3. `reports/tables/modeling/metrics_by_fold.csv`
4. `muestras/predictions_sample.csv`
5. `reports/tables/modeling/error_analysis_by_route.csv`, `error_analysis_by_hour.csv`, `error_analysis_by_day_type.csv`
6. `reports/figures/modeling/`
7. `src/proyecto_grado/modeling/`, `configs/`, `scripts/`

Las predicciones completas estan en `reports/tables/modeling/predictions_baselines.parquet` si el archivo original era menor o igual a 50 MB. En este paquete, el parquet completo fue copiado: `True`. La muestra CSV contiene `5000` filas.

## Limitaciones conocidas

- Solo hay baselines simples; no hay LSTM, GRU, Prophet, SARIMA, Random Forest ni XGBoost.
- No hay analisis especifico por horizonte distinto a una franja.
- No hay tabla especifica de error por nivel de demanda ni outliers de residual.
- Los gaps se conservan y no se interpretan automaticamente como demanda cero.
- La demanda modelada corresponde a pasajeros observados/atendidos, no demanda no atendida.
- No se encontraron logs externos especificos en `logs/`.
