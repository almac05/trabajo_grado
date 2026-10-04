# Inventario de scripts que generan figuras

Fecha del inventario: 2026-09-27. Rama `consolidacion-evaluacion`, último commit `e504b29`.
Alcance: solo lectura. No se modificó ni se ejecutó ningún script.

## 1. Método

- Búsqueda de `savefig`, `write_image`, `write_html`, `imsave`, `export_png`, `to_image(`, `.save(` y `to_file(` en todos los `.py` e `.ipynb` de `scripts/`, `analisis/`, `src/`, `notebooks/`, `docs/`, `tests/`, `backups/`, `revision_modelado/`, `build/`, `models/metadata/` y la raíz.
- Los notebooks (`notebooks/0*/`) solo contienen `.gitkeep`: ningún notebook genera figuras.
- Los aciertos de `.save(` en `build_baseline.py`, `build_fleet_availability.py` y `build_productivity.py` se descartaron: solo guardan tablas.
- Las fechas son el `mtime` del sistema de archivos. El estado en git se tomó de `git status --porcelain`: `M` = cambio sin preparar, `MM` = cambios preparados y sin preparar, `??` = sin seguimiento.
- El documento de la tesis no está en el repositorio. Para asociar cada figura del documento con un PNG, se supuso la variante a 30 minutos (`g30min`), que es la granularidad de modelado.

## 2. Scripts que generan figuras

| # | Script (punto de entrada → módulo que dibuja) | Figuras que produce | Fuente de datos | mtime del script | Cambios sin comprometer |
|---|---|---|---|---|---|
| 1 | `scripts/run_eda_temporal.py` → `src/proyecto_grado/eda/temporal_analysis.py` (cálculos) | `reports/figures/eda/curva_intraday_{1,3}_{laboral,sabado,domingo,festivo,festivo_puente}_g{15,30,60}min.png` (30), `heatmap_demanda_hora_dia_{1,3}_g{15,30,60}min.png` (6), `boxplot_tipo_dia_{1,3}_g{15,30,60}min.png` (6), `acf_pacf_{1,3}_g{15,30,60}min.png` (6), `tendencia_mensual_{1,3}.png` (2) | `data/processed/time_series/ts_ruta{1,3}_g{15,30,60}min.parquet` (mtime 2026-08-24 20:40), columna `pasajeros_total`, filtrada a `gap_tipo == 'operativo'`. La matriz de correlación usa `data/processed/model_ready/despachos_model_ready.parquet` | script: 2026-05-07 18:38; módulo: 2026-08-31 09:43 | Script: no. `temporal_analysis.py`: **sí (M)**; el cambio solo afecta `correlacion_features` (excluye PASAJEROS, PASAJEROS_REALES y ALARMAS), no a las figuras |
| 2 | `src/proyecto_grado/analytics/report.py` (`build_post_etl_report`, con `__main__`) → `src/proyecto_grado/analytics/plots.py` | `reports/figures/eda/etl_rows_by_stage.png`, `qc_flags_top.png`, `demand_by_route.png`, `demand_by_hour_weekday.png` | Datasets de la ETL; los KPI salen de `model_ready` (`kpis.py`, columna `PASAJEROS_REALES`) | plots.py: 2026-05-02 13:04; report.py: 2026-09-27 12:59 | plots.py: no. **report.py, kpis.py y etl_diagnostics.py: sí (M)**. Los cuatro PNG tienen mtime 2026-09-27 12:59, igual que `report.py`: se regeneraron hoy con el código sin comprometer |
| 3 | `scripts/plot_contraccion_flota.py` | `reports/figures/baseline/contraccion_flota_mensual.png` (2×2: vehículos activos, despachos, pasajeros, productividad por despacho) | `reports/tables/baseline/diagnostico_flota_mensual.csv` (mtime 2026-08-31 09:07), producido por `scripts/diagnostico_reduccion_flota.py` desde `despachos_model_ready.parquet` | 2026-08-07 17:53 | Script: no. **Su productor de datos `diagnostico_reduccion_flota.py`: sí (M)** (pasa de `PASAJEROS` a `PASAJEROS_REALES`) |
| 4 | `analisis/07_acf_operativo.py` | `analisis/salidas/acf_operativo_r{1,3}.png` (ACF + PACF, rezagos 1–60) | `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (2026-08-23 20:38), `pasajeros_total` no nulo | 2026-08-23 20:23 | No |
| 5 | `analisis/24_acf_demanda_regiones.py` | `reports/figures/modeling/acf_demanda_operativa_20260823.png` (+ tabla `analisis/salidas/acf_demanda_operativa_20260823.csv`) | Mismo parquet de modelado que el #4 | 2026-09-24 11:30 | **Sí: sin seguimiento (??)** |
| 6 | `scripts/estimate_operational_hours.py` → `src/proyecto_grado/features/operational_hours.py::plot_heatmap` | `reports/figures/operational_heatmap_{1,3}_{15,30,60}min.png` (probabilidad de operación por franja × tipo de día; no muestra demanda) | `data/processed/time_series/ts_ruta*_g*min.parquet` | 2026-05-03 18:11 (ambos) | No |
| 7 | `scripts/build_modeling_report.py` → `src/proyecto_grado/modeling/error_analysis.py` | `reports/figures/modeling/{observed_vs_predicted,metrics_comparison,error_by_hour,residuals}_baselines.png`, `backtesting_folds.png` | `reports/tables/modeling/predictions_baselines.parquet` (o `predictions_multitarget_<run_id>.parquet`), CSV de métricas y folds | script: 2026-08-07 17:53; módulo: 2026-07-26 10:19 | No |
| 8 | `scripts/run_baseline_reference.py` | `reports/figures/modeling/{mae_vs_ventana_regimen,sesgo_vs_ventana_regimen,comparacion_pareada_folds,plano_mae_sesgo,referencia_comparacion}_<sufijo>.png` (vigentes: sufijo `rolling_bias_20260720`) | `reports/tables/modeling/predictions_multitarget_<run_id>.parquet` | 2026-08-07 17:53 | No |
| 9 | `scripts/run_bias_analysis.py` | `reports/figures/modeling/{bias_por_fold,bias_mensual,bias_por_hora,mae_vs_ventana}_<run_id>.png` (vigentes: `rolling_bias_20260720`) | Parquet de predicciones, CSV de folds y `diagnostico_flota_mensual.csv` | 2026-08-07 17:53 | No |
| 10 | `scripts/run_xgboost_backtesting.py` → `src/proyecto_grado/modeling/xgboost_report.py` | `reports/figures/modeling/xgb_importancia_xgboost_l{1,2}_<run_id>.png`, `xgb_regimen_<run_id>.png`, `xgb_evolucion_error_<run_id>.png` (vigentes: `xgboost_20260729`) | Resultados de backtesting de XGBoost | script: 2026-08-07 19:42; módulo: 2026-08-07 17:53 | No |
| 11 | `scripts/build_xgboost_figures.py` | `reports/figures/modeling/xgb_cruce_ventanas.png`, `xgb_sesgo_por_hora.png` | `analisis/salidas/barrido_disponibilidad_real_r{1,3}.csv` y el artefacto de predicciones de XGBoost indicado en `configs/modeling/evaluacion_comparativa.yaml` | 2026-08-31 08:06 | **Sí (MM)** |
| 12 | Copias fuera del flujo vigente: `backups/modeling_refactor_20260720_141525/src/proyecto_grado/modeling/error_analysis.py` y `revision_modelado/src/proyecto_grado/modeling/error_analysis.py` | Mismas figuras que el #7, en sus propios árboles `reports/figures/modeling/` | Igual que el #7 | — | Son copias de respaldo o revisión; no se usan en el flujo actual |

**Fechas de los PNG vigentes relevantes**

- `reports/figures/eda/{curva_intraday,heatmap_demanda_hora_dia,boxplot_tipo_dia,acf_pacf,tendencia_mensual}_*`: 2026-08-31 08:44.
- `reports/figures/eda/{demand_by_*,qc_flags_top,etl_rows_by_stage}.png`: 2026-09-27 12:59.
- `reports/figures/baseline/contraccion_flota_mensual.png`: **2026-06-29 20:18**.
- `analisis/salidas/acf_operativo_r{1,3}.png`: 2026-08-08 15:12.
- `reports/figures/modeling/acf_demanda_operativa_20260823.png`: 2026-09-24 11:31.
- `reports/figures/operational_heatmap_*`: 2026-05-03 18:02.

Directorios históricos: `reports/figures/eda_20260425/`, `reports/figures/eda_20260507_sin_corregir/` y `reports/figures_v1_sin_corregir/` son snapshots anteriores. Ningún script escribe en ellos.

## 3. Asociación de las figuras del documento con su script

| Figura del documento | PNG vigente | Script de origen | Observaciones |
|---|---|---|---|
| Perfil intradía, día laboral, Ruta 1 | `reports/figures/eda/curva_intraday_1_laboral_g30min.png` | `scripts/run_eda_temporal.py::plot_curva_intraday` | Media y banda p25–p75. **Agrupa por `hora_del_dia` (hora entera, `ts.dt.hour`), no por franja de 30 minutos**: cada punto combina las dos franjas de la hora. Tiene título incrustado (`Ruta 1 \| LABORAL \| 30 min`) y marcadores de pico y valle. Lee `data/processed/time_series/` (2026-08-24), no el parquet de modelado del 2026-08-23. |
| Perfil intradía, día laboral, Ruta 3 | `reports/figures/eda/curva_intraday_3_laboral_g30min.png` | Ídem | Las mismas observaciones. |
| Mapas de calor de demanda por hora y día de la semana | `reports/figures/eda/heatmap_demanda_hora_dia_{1,3}_g30min.png` | `scripts/run_eda_temporal.py::plot_heatmap_hora_dia` | Media de `pasajeros_total` por día de la semana × hora, solo franjas operativas. Tiene título incrustado. Ver duplicado D2. |
| Diagramas de caja por tipo de día, Rutas 1 y 3 | `reports/figures/eda/boxplot_tipo_dia_{1,3}_g30min.png` | `scripts/run_eda_temporal.py::plot_boxplot_tipo_dia` | Pasajeros por franja de 30 minutos, franjas operativas. Tiene título incrustado. |
| ACF y PACF | `reports/figures/eda/acf_pacf_{1,3}_g30min.png` **o** `analisis/salidas/acf_operativo_r{1,3}.png` | `scripts/run_eda_temporal.py::plot_acf_pacf` **o** `analisis/07_acf_operativo.py` | Dos candidatos equivalentes (ver D1). Sin ver el documento no se puede saber cuál está insertado. |
| Evolución de la flota, los despachos y la demanda | `reports/figures/baseline/contraccion_flota_mensual.png` | `scripts/plot_contraccion_flota.py` (datos de `scripts/diagnostico_reduccion_flota.py`) | **Desactualizada**: el PNG (2026-06-29) es anterior a su CSV fuente (2026-08-31 09:07). El CSV se regeneró con el cambio sin comprometer a `PASAJEROS_REALES`: `diagnostico_reduccion_flota.py` y el CSV tienen el mismo mtime. Por lo tanto, **el panel de pasajeros de la figura casi seguro refleja el conteo crudo `PASAJEROS`**. Tiene títulos por panel, sin `suptitle`. |
| ACF con regiones sombreadas | `reports/figures/modeling/acf_demanda_operativa_20260823.png` | `analisis/24_acf_demanda_regiones.py` | Solo ACF, ambas rutas en una figura, rezagos 1–35, regiones 12–16 y 26–29 sombreadas, anotación del máximo en 26–29. Tiene `suptitle` incrustado. Script sin seguimiento en git. |

**¿`07_acf_operativo.py` u otro script ya producía una figura equivalente a la de `24_acf_demanda_regiones.py`?** No existe una figura equivalente. `07_acf_operativo.py` usa la misma serie y el mismo criterio operativo (`FK_RUTA == ruta` y `pasajeros_total` no nulo en el parquet de modelado), y su panel ACF contiene la misma información de base en un rango mayor (rezagos 1–60). Pero no sombrea regiones, no anota el máximo, no pone las dos rutas en una sola figura y además incluye la PACF. `run_eda_temporal.py::plot_acf_pacf` tampoco sombrea regiones, y usa otra fuente (`data/processed/time_series/`) y rezagos 1–48. La figura del script 24 es, por lo tanto, una **extensión** del panel ACF del script 07, como declara su docstring, y no un duplicado.

## 4. Figuras sin script de origen

- Todas las figuras del documento enumeradas en la consigna tienen script de origen identificado.
- Fuera de la lista: `docs/taller_final_plan_entrega.html` referencia `reports/figures/prediction_plot.png`. Ese archivo no existe y ningún script lo produce.

## 5. Casos en que dos scripts producen figuras equivalentes

| Id | Figuras | Scripts | Grado de equivalencia |
|---|---|---|---|
| D1 | `reports/figures/eda/acf_pacf_{r}_g30min.png` y `analisis/salidas/acf_operativo_r{r}.png` | `run_eda_temporal.py` y `analisis/07_acf_operativo.py` | **Equivalentes en contenido** (ACF + PACF lado a lado por ruta, a 30 minutos, franjas operativas). Diferencias: fuente (`data/processed/time_series/` filtrada por `gap_tipo == 'operativo'` frente al parquet de modelado con `pasajeros_total` no nulo), número de rezagos (48 frente a 60), método de PACF, y título y leyenda ADF (el script 07 no incrusta título). Las series pueden no coincidir fila a fila. No se verificó porque no se ejecutó nada. |
| D2 | `reports/figures/eda/heatmap_demanda_hora_dia_{r}_g30min.png` y `reports/figures/eda/demand_by_hour_weekday.png` | `run_eda_temporal.py` y `analytics/plots.py` (vía `report.py`) | **Parcialmente equivalentes**: ambos son mapas día de la semana × hora. El primero es por ruta, con la media por franja operativa. El segundo agrega ambas rutas, suma pasajeros de `model_ready` y trae el título `Distribucion horaria de la demanda por dia`. |
| D3 | `reports/figures/eda/tendencia_mensual_{r}.png` y el panel de pasajeros de `contraccion_flota_mensual.png` | `run_eda_temporal.py` y `plot_contraccion_flota.py` | **Solapamiento parcial**: ambos muestran la demanda mensual. El primero es por ruta, con tendencia OLS y serie de `time_series`. El segundo es total, desde `model_ready`. |
| D4 | `reports/figures/modeling/mae_vs_ventana_rolling_bias_20260720.png` y `mae_vs_ventana_regimen_rolling_bias_20260720.png` | `run_bias_analysis.py` y `run_baseline_reference.py` | Misma relación MAE frente a ventana. La segunda se desagrega por régimen. |
| D5 | Figuras de `error_analysis.py` | `src/`, `backups/…` y `revision_modelado/…` | Copias del mismo módulo. Solo la de `src/` pertenece al flujo vigente. |

El mapa de calor operativo (`operational_heatmap_*`) **no** es equivalente a los mapas de demanda: representa la probabilidad de operación, no pasajeros.

## 6. Observaciones para la regeneración pendiente

1. **Perfil intradía por franja de 30 minutos**: la figura existente no la cumple, porque agrupa por hora entera, y lee `data/processed/time_series/`, no el parquet de modelado vigente. Reproducir lo pedido requiere un script nuevo.
2. **Figura de flota**: es la única cuya fecha es anterior a la de su fuente directa. Regenerarla con `plot_contraccion_flota.py` sin cambiar código incluiría el conteo depurado, porque el CSV ya lo contiene, pero conservaría los títulos por panel.
3. **Figuras EDA del 2026-08-31**: son posteriores tanto a las series de `data/processed/time_series/` (2026-08-24) como a la adopción de `PASAJEROS_REALES` en `time_series_builder.py` (commit `e6115bf`, 2026-08-24). Por fechas, están calculadas con el conteo depurado. Todas llevan título incrustado.
4. **Figuras regeneradas hoy**: los cuatro PNG de `analytics/plots.py` se regeneraron hoy (12:59) con código sin comprometer.
