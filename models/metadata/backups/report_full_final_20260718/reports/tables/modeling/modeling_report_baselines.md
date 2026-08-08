# Reporte inicial de modelado - baselines

run_id: `report_full_trace_20260718`
predicciones: `C:\Users\regis\proyecto_grado\reports\tables\modeling\predictions_baselines.parquet`

## Metricas test final

| model | route | n | mae | rmse | smape | wape | bias_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| historical_average_route_day_type_slot | 1 | 1544 | 36.082 | 45.146 | 35.929 | 35.684 | 27.86 |
| historical_average_route_day_type_slot | 3 | 1583 | 38.414 | 49.957 | 34.15 | 32.581 | 27.098 |
| naive | 1 | 1394 | 43.56 | 55.867 | 42.672 | 41.198 | 1.247 |
| naive | 3 | 1443 | 55.279 | 73.231 | 46.058 | 44.314 | 0.299 |
| seasonal_naive_daily | 1 | 1292 | 47.505 | 60.917 | 50.796 | 46.85 | 4.766 |
| seasonal_naive_daily | 3 | 1336 | 53.069 | 68.102 | 51.101 | 45.501 | 6.352 |
| seasonal_naive_weekly | 1 | 1381 | 42.846 | 55.666 | 44.939 | 41.29 | 1.518 |
| seasonal_naive_weekly | 3 | 1423 | 47.451 | 62.552 | 44.095 | 39.23 | 1.545 |

## Figuras

- `C:\Users\regis\proyecto_grado\reports\figures\modeling\observed_vs_predicted_baselines.png`
- `C:\Users\regis\proyecto_grado\reports\figures\modeling\metrics_comparison_baselines.png`
- `C:\Users\regis\proyecto_grado\reports\figures\modeling\error_by_hour_baselines.png`
- `C:\Users\regis\proyecto_grado\reports\figures\modeling\residuals_baselines.png`
- `C:\Users\regis\proyecto_grado\reports\figures\modeling\backtesting_folds.png`
