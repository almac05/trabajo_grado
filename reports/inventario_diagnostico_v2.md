# Inventario de figuras y tablas para diagnóstico/EDA v2

Generado: 2026-07-05 11:21:44 (America/Bogota).

Alcance aplicado: inspección de solo lectura sobre `reports/figures/`, `reports/tables/` (todos los subdirectorios), `data/processed/` y búsqueda en `scripts/`, `src/` y `notebooks/` de llamadas a matplotlib/seaborn/Altair/Plotly y a `savefig`/`to_csv`/`to_parquet`. No se regeneró ni sobrescribió ningún artefacto existente; solo se escribió este inventario.

Las descripciones marcadas como `(inferido - confirmar)` no pudieron verificarse directamente desde una función de escritura, columnas o estructura de datos. Para PNG se reportan dimensiones y DPI cuando el encabezado PNG lo expone.

**Conteo rápido**

| Tipo | Cantidad |
| --- | --- |
| Figuras PNG persistidas | 61 |
| Figuras solo en código/dashboard | 20 |
| Tablas CSV/Parquet/XLSX inspeccionadas | 78 |
| Reportes textuales adicionales en reports/tables | 4 |
| JSON adicionales en reports/tables | 3 |

## Chequeos especiales

### 1) Mapa KPI -> fuente

| KPI | Archivo(s) fuente | Valor(es) actual(es) exactos | ¿persistido o solo consola? | Última modificación | ¿posible desactualización? |
| --- | --- | --- | --- | --- | --- |
| CV headway | reports/tables/baseline/headway_summary.csv; headway_by_hour.csv; headway_by_franja.csv | Ruta 1: cv_headway=0.722, headway_mean=10.97, headway_p95=24.17; Ruta 3: cv_headway=0.774, headway_mean=10.56, headway_p95=24.7 | Persistido | 2026-06-08 17:28:37 | Sí: tablas headway son anteriores al freeze model-ready más reciente. |
| Bunching | reports/tables/baseline/headway_summary.csv; headway_by_hour.csv; headway_by_franja.csv | Ruta 1: bunching_pct=3.82; Ruta 3: bunching_pct=4.71 | Persistido | 2026-06-08 17:28:37 | Sí: tablas headway son anteriores al freeze model-ready más reciente. |
| Espera excesiva | reports/tables/baseline/headway_summary.csv; headway_by_hour.csv; headway_by_franja.csv | Ruta 1: excess_wait_pct=2.79; Ruta 3: excess_wait_pct=3.09 | Persistido | 2026-06-08 17:28:37 | Sí: tablas headway son anteriores al freeze model-ready más reciente. |
| Disponibilidad / patio vacío | reports/tables/baseline/fleet_availability_summary.csv; fleet_availability_by_day.csv | n_dias_analizados=30; disp_promedio_pico_manana=2.67; pct_vacio_pico_manana=34.1; pct_vacio_pico_tarde=0.0; pct_vacio_cierre=5.6 | Persistido | 2026-07-02 19:38:55 | No frente al freeze; sí hay reportes TXT más viejos con valores de otra corrida. |
| Intervalos largos por franja | reports/tables/baseline/fleet_availability_summary.csv; fleet_availability_by_day.csv | total_headways_largos=447; pct_largos_pico_manana=19.5; pct_largos_pico_tarde=15.7; pct_largos_cierre=14.3; pct_largos_otros=50.6 | Persistido | 2026-07-02 19:38:55 | No frente al freeze; revisar que el texto citado use la corrida de 30 días. |
| Contracción de flota | reports/tables/baseline/diagnostico_flota_comparacion.csv; diagnostico_flota_mensual.csv; reports/figures/baseline/contraccion_flota_mensual.png | Vehículos activos: 63.0 -> 42.0; variacion_absoluta=-21.0; variacion_pct=-33.3; Despachos totales: 5266.0 -> 3179.0; variacion_absoluta=-2087.0; variacion_pct=-39.6; Pasajeros totales: 247688.0 -> 145868.0; variacion_absoluta=-101820.0; variacion_pct=-41.1 | Persistido | 2026-06-23 10:49:46 | No: artefactos posteriores al freeze más reciente. |
| Productividad por despacho | reports/tables/baseline/productivity_summary.csv; productivity_weekly_series.csv; diagnostico_flota_comparacion.csv | Ruta 1: productividad_promedio_bruta=44.4, productividad_p50=44.51, tendencia_slope_mensual_est=0.02; Ruta 3: productividad_promedio_bruta=48.5, productividad_p50=48.65, tendencia_slope_mensual_est=0.025; Productividad pas/despacho: 47.04 -> 45.88; variacion_absoluta=-1.16; variacion_pct=-2.5 | Persistido | 2026-06-23 10:40:24 | No: artefactos posteriores al freeze más reciente. |
| Intensidad de uso | reports/tables/baseline/diagnostico_flota_comparacion.csv; diagnostico_flota_mensual.csv | Despachos por vehículo (intensidad de uso): 83.59 -> 75.69; variacion_absoluta=-7.9; variacion_pct=-9.5 | Persistido | 2026-06-23 10:49:46 | No: artefactos posteriores al freeze más reciente. |
| Rotación entre despachos de una misma placa | scripts/diagnostico_rotacion.py; data/processed/model_ready/despachos_model_ready.parquet | No hay CSV/PNG persistido; el script imprime top placas, gaps entre despachos, distribución de despachos/día y cambios de ruta. | Solo consola | 2026-06-22 20:20:15 | Sí: no hay artefacto persistido ni valores citables actuales. |
| Ajuste oferta-demanda | reports/tables/baseline/demand_supply_summary.csv; demand_supply_by_franja.csv; load_factor_distribution.csv | Ruta 1: load_factor_mean=1.544, sobrecarga_pct=96.34, optimo_pct=3.41; Ruta 3: load_factor_mean=1.642, sobrecarga_pct=96.24, optimo_pct=3.53 (NO utilizable como KPI por metodología) | Persistido, pero metodológicamente inválido | 2026-06-08 16:01:01 | Sí: anterior al freeze y no mide ocupación simultánea. |
| Demanda recuperable | reports/tables/baseline/BASELINE_REPORT.txt; scripts/build_baseline_consolidado.py | Solo fórmula: demanda_recuperable = (despachos_recomendados - despachos_reales) x productividad_estable (~46 pas/desp); no hay cálculo persistido. | Solo texto conceptual | 2026-06-29 11:51:32 | Sí: no existe tabla/figura calculada. |

### 2) Detección de desactualización frente al freeze model-ready

Freeze de referencia: `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.csv` modificado `2026-06-10 19:21:47`. Se listan artefactos de `reports/tables/baseline/` y `reports/figures/` con modificación anterior a ese freeze.

| Artefacto | Modificado | Implicación |
| --- | --- | --- |
| reports/tables/baseline/demand_supply_by_franja.csv | 2026-06-08 16:01:01 | Anterior al freeze y además basado en load_factor no utilizable para ocupación simultánea. |
| reports/tables/baseline/demand_supply_summary.csv | 2026-06-08 16:01:01 | Anterior al freeze y además basado en load_factor no utilizable para ocupación simultánea. |
| reports/tables/baseline/headway_by_franja.csv | 2026-06-08 17:28:37 | Anterior al freeze; depende de despachos/model_ready, por tanto puede recalcularse con el freeze más reciente. |
| reports/tables/baseline/headway_by_hour.csv | 2026-06-08 17:28:37 | Anterior al freeze; depende de despachos/model_ready, por tanto puede recalcularse con el freeze más reciente. |
| reports/tables/baseline/headway_summary.csv | 2026-06-08 17:28:37 | Anterior al freeze; depende de despachos/model_ready, por tanto puede recalcularse con el freeze más reciente. |
| reports/tables/baseline/load_factor_distribution.csv | 2026-06-08 16:01:01 | Anterior al freeze y además basado en load_factor no utilizable para ocupación simultánea. |
| reports/figures/eda/acf_pacf_1_g15min.png | 2026-05-07 18:35:41 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/acf_pacf_1_g30min.png | 2026-05-07 18:35:41 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/acf_pacf_1_g60min.png | 2026-05-07 18:35:42 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/acf_pacf_3_g15min.png | 2026-05-07 18:35:43 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/acf_pacf_3_g30min.png | 2026-05-07 18:35:43 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/acf_pacf_3_g60min.png | 2026-05-07 18:35:44 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/boxplot_tipo_dia_1_g15min.png | 2026-05-07 18:35:36 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/boxplot_tipo_dia_1_g30min.png | 2026-05-07 18:35:37 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/boxplot_tipo_dia_1_g60min.png | 2026-05-07 18:35:37 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/boxplot_tipo_dia_3_g15min.png | 2026-05-07 18:35:38 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/boxplot_tipo_dia_3_g30min.png | 2026-05-07 18:35:39 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/boxplot_tipo_dia_3_g60min.png | 2026-05-07 18:35:39 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_domingo_g15min.png | 2026-05-07 18:35:26 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_domingo_g30min.png | 2026-05-07 18:35:27 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_domingo_g60min.png | 2026-05-07 18:35:29 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_festivo_g15min.png | 2026-05-07 18:35:26 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_festivo_g30min.png | 2026-05-07 18:35:28 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_festivo_g60min.png | 2026-05-07 18:35:29 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_festivo_puente_g15min.png | 2026-05-07 18:35:27 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_festivo_puente_g30min.png | 2026-05-07 18:35:28 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_festivo_puente_g60min.png | 2026-05-07 18:35:30 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_laboral_g15min.png | 2026-05-07 18:35:27 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_laboral_g30min.png | 2026-05-07 18:35:28 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_laboral_g60min.png | 2026-05-07 18:35:30 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_sabado_g15min.png | 2026-05-07 18:35:27 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_sabado_g30min.png | 2026-05-07 18:35:29 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_1_sabado_g60min.png | 2026-05-07 18:35:30 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_domingo_g15min.png | 2026-05-07 18:35:30 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_domingo_g30min.png | 2026-05-07 18:35:32 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_domingo_g60min.png | 2026-05-07 18:35:34 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_festivo_g15min.png | 2026-05-07 18:35:31 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_festivo_g30min.png | 2026-05-07 18:35:32 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_festivo_g60min.png | 2026-05-07 18:35:34 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_festivo_puente_g15min.png | 2026-05-07 18:35:31 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_festivo_puente_g30min.png | 2026-05-07 18:35:33 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_festivo_puente_g60min.png | 2026-05-07 18:35:34 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_laboral_g15min.png | 2026-05-07 18:35:31 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_laboral_g30min.png | 2026-05-07 18:35:33 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_laboral_g60min.png | 2026-05-07 18:35:35 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_sabado_g15min.png | 2026-05-07 18:35:32 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_sabado_g30min.png | 2026-05-07 18:35:33 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/curva_intraday_3_sabado_g60min.png | 2026-05-07 18:35:35 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/demand_by_hour_weekday.png | 2026-04-25 11:18:42 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/demand_by_route.png | 2026-04-25 11:18:42 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/etl_rows_by_stage.png | 2026-04-25 11:18:41 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g15min.png | 2026-05-07 18:35:35 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g30min.png | 2026-05-07 18:35:36 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g60min.png | 2026-05-07 18:35:37 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g15min.png | 2026-05-07 18:35:38 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g30min.png | 2026-05-07 18:35:38 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g60min.png | 2026-05-07 18:35:39 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/qc_flags_top.png | 2026-04-25 11:18:42 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/tendencia_mensual_1.png | 2026-05-07 18:35:40 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/eda/tendencia_mensual_3.png | 2026-05-07 18:35:40 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/operational_heatmap_1_15min.png | 2026-05-03 18:02:13 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/operational_heatmap_1_30min.png | 2026-05-03 18:02:14 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/operational_heatmap_1_60min.png | 2026-05-03 18:02:14 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/operational_heatmap_3_15min.png | 2026-05-03 18:02:15 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/operational_heatmap_3_30min.png | 2026-05-03 18:02:15 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |
| reports/figures/operational_heatmap_3_60min.png | 2026-05-03 18:02:15 | Anterior al freeze; figura EDA/operativa calculada con insumos previos y potencialmente recalculable. |

### 3) Disponibilidad de flota - verificación puntual

Archivo verificado: `reports/tables/baseline/fleet_availability_summary.csv` modificado `2026-07-02 19:38:55`.

Valores persistidos: `n_dias_analizados=30`, `pct_vacio_pico_manana=34.1`, `pct_largos_pico_manana=19.5`, `pct_largos_otros=50.6`.

`fleet_availability_by_day.csv` tiene `30` filas, consistente con la corrida de `30` días. `scripts/build_fleet_availability.py` acepta `--n-dias` y su default en código es `15`; por lo tanto, la corrida persistida de 30 días fue ejecutada con un parámetro distinto al default (inferido - confirmar). `scripts/diagnostico_disponibilidad_multidia.py` también acepta `--n-dias`, con default `8`, y su CSV histórico `reports/tables/baseline/diagnostico_disponibilidad_multidia.csv` tiene `12` filas y modificado `2026-06-22 20:58:42`.

Conclusión frente a la cita `30 días / 34,1% / 19,5% / 50,6%`: el CSV persistido actual SÍ coincide. Advertencia: `reports/tables/baseline/fleet_availability_report.txt` y `reports/tables/baseline/BASELINE_REPORT.txt` conservan valores de una corrida anterior de 15 días, por lo que esos textos están desalineados con los CSV actuales.

### 4) Artefactos solo-consola

Archivos con `print`/`logging` y sin llamadas de persistencia (`to_csv`, `to_parquet`, `savefig`) detectados en `scripts/`, `src/` y `notebooks/`:

| Archivo | Evidencia |
| --- | --- |
| scripts/build_baseline.py | print/logging sin to_csv/to_parquet/savefig |
| scripts/build_baseline_consolidado.py | print/logging sin to_csv/to_parquet/savefig |
| scripts/build_fleet_availability.py | print/logging sin to_csv/to_parquet/savefig |
| scripts/build_productivity.py | print/logging sin to_csv/to_parquet/savefig |
| scripts/diagnostico_rotacion.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/etl/config.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/etl/extract.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/etl/gps.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/etl/pipeline.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/etl/transforms.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/etl/utils.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/features/time_series_builder.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/features/validators.py | print/logging sin to_csv/to_parquet/savefig |
| src/proyecto_grado/utils/pruebas.py | print/logging sin to_csv/to_parquet/savefig |

Caso específico de rotación: `scripts/diagnostico_rotacion.py` no contiene `to_csv`, `to_parquet` ni `savefig`; la rotación/gaps entre despachos por placa se imprime en consola y no se persiste en ningún CSV/Parquet/PNG dentro del alcance inspeccionado.

Archivos que imprimen/loguean y también persisten salidas:

| Archivo | Evidencia |
| --- | --- |
| scripts/build_time_series.py | imprime/loguea y también persiste artefactos |
| scripts/diagnostico_disponibilidad_flota.py | imprime/loguea y también persiste artefactos |
| scripts/diagnostico_disponibilidad_multidia.py | imprime/loguea y también persiste artefactos |
| scripts/diagnostico_reduccion_flota.py | imprime/loguea y también persiste artefactos |
| scripts/estimate_operational_hours.py | imprime/loguea y también persiste artefactos |
| scripts/plot_contraccion_flota.py | imprime/loguea y también persiste artefactos |
| scripts/run_eda_temporal.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/analytics/demand_supply.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/analytics/fleet_availability.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/analytics/headway.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/analytics/report.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/analytics/vehicle_productivity.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/eda/temporal_analysis.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/etl/db.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/etl/model_ready.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/etl/qc.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/etl/trip_end.py | imprime/loguea y también persiste artefactos |
| src/proyecto_grado/features/operational_hours.py | imprime/loguea y también persiste artefactos |

### 5) Advertencia metodológica sobre load_factor

Las tablas `reports/tables/baseline/demand_supply_summary.csv`, `reports/tables/baseline/demand_supply_by_franja.csv` y `reports/tables/baseline/load_factor_distribution.csv` están basadas en `load_factor = pasajeros_total_bin / (despachos_count x capacidad_vehiculo)`. NO deben usarse como KPI de ajuste oferta-demanda ni como ocupación simultánea: en este proyecto `PASAJEROS` representa abordajes acumulados por recorrido, no pasajeros simultáneos a bordo.

### 6) Huecos para el capítulo

| KPI/hueco | Estado | Fuente para calcularlo |
| --- | --- | --- |
| Rotación entre despachos por placa | No hay tabla/figura persistida; solo consola en `scripts/diagnostico_rotacion.py`. | `data/processed/model_ready/despachos_model_ready.parquet` permite calcular gaps entre `HORA_FIN_FINAL` e inicio siguiente por `PLACA` y día. |
| Ajuste oferta-demanda distribucional despachos-vs-abordajes | Las tablas `load_factor` existen, pero no son utilizables para este KPI por la advertencia metodológica. | `data/processed/time_series/ts_ruta1_g30min.parquet` y `ts_ruta3_g30min.parquet` permiten contrastar `despachos_count` vs `pasajeros_total` por franja; `headway_by_hour.csv` puede complementar regularidad. |
| Demanda recuperable | Solo hay fórmula conceptual en `BASELINE_REPORT.txt`; no hay tabla/figura calculada. | `productivity_summary.csv`, `despachos_model_ready.parquet` y futuras predicciones/backtesting de despachos recomendados. |
| Artefactos de modelado/evaluación | No se encontraron métricas, predicciones, backtesting ni simulación retrospectiva persistidos. | `data/processed/time_series/*.parquet` y `data/processed/model_ready/despachos_model_ready.parquet` serían los insumos base. |

## Figuras persistidas

| Ruta | Fuente | Qué muestra | Formato/dim | Modificado |
| --- | --- | --- | --- | --- |
| reports/figures/baseline/contraccion_flota_mensual.png | scripts/plot_contraccion_flota.py:124-216 | Serie mensual multi-KPI de contracción de flota: vehículos activos, despachos, pasajeros y productividad. | 2540x1536px; dpi 200x200 | 2026-06-29 20:18:03 |
| reports/figures/eda/acf_pacf_1_g15min.png | scripts/run_eda_temporal.py | ACF/PACF de pasajeros para Ruta 1 a 15 min. | 2373x984px; dpi 200x200 | 2026-05-07 18:35:41 |
| reports/figures/eda/acf_pacf_1_g30min.png | scripts/run_eda_temporal.py | ACF/PACF de pasajeros para Ruta 1 a 30 min. | 2373x984px; dpi 200x200 | 2026-05-07 18:35:41 |
| reports/figures/eda/acf_pacf_1_g60min.png | scripts/run_eda_temporal.py | ACF/PACF de pasajeros para Ruta 1 a 60 min. | 2373x984px; dpi 200x200 | 2026-05-07 18:35:42 |
| reports/figures/eda/acf_pacf_3_g15min.png | scripts/run_eda_temporal.py | ACF/PACF de pasajeros para Ruta 3 a 15 min. | 2373x984px; dpi 200x200 | 2026-05-07 18:35:43 |
| reports/figures/eda/acf_pacf_3_g30min.png | scripts/run_eda_temporal.py | ACF/PACF de pasajeros para Ruta 3 a 30 min. | 2373x984px; dpi 200x200 | 2026-05-07 18:35:43 |
| reports/figures/eda/acf_pacf_3_g60min.png | scripts/run_eda_temporal.py | ACF/PACF de pasajeros para Ruta 3 a 60 min. | 2373x984px; dpi 200x200 | 2026-05-07 18:35:44 |
| reports/figures/eda/boxplot_tipo_dia_1_g15min.png | scripts/run_eda_temporal.py | Boxplot de pasajeros por tipo de día para Ruta 1 a 15 min. | 1773x974px; dpi 200x200 | 2026-05-07 18:35:36 |
| reports/figures/eda/boxplot_tipo_dia_1_g30min.png | scripts/run_eda_temporal.py | Boxplot de pasajeros por tipo de día para Ruta 1 a 30 min. | 1773x974px; dpi 200x200 | 2026-05-07 18:35:37 |
| reports/figures/eda/boxplot_tipo_dia_1_g60min.png | scripts/run_eda_temporal.py | Boxplot de pasajeros por tipo de día para Ruta 1 a 60 min. | 1774x974px; dpi 200x200 | 2026-05-07 18:35:37 |
| reports/figures/eda/boxplot_tipo_dia_3_g15min.png | scripts/run_eda_temporal.py | Boxplot de pasajeros por tipo de día para Ruta 3 a 15 min. | 1774x974px; dpi 200x200 | 2026-05-07 18:35:38 |
| reports/figures/eda/boxplot_tipo_dia_3_g30min.png | scripts/run_eda_temporal.py | Boxplot de pasajeros por tipo de día para Ruta 3 a 30 min. | 1774x974px; dpi 200x200 | 2026-05-07 18:35:39 |
| reports/figures/eda/boxplot_tipo_dia_3_g60min.png | scripts/run_eda_temporal.py | Boxplot de pasajeros por tipo de día para Ruta 3 a 60 min. | 1773x974px; dpi 200x200 | 2026-05-07 18:35:39 |
| reports/figures/eda/curva_intraday_1_domingo_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=DOMINGO, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:26 |
| reports/figures/eda/curva_intraday_1_domingo_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=DOMINGO, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_domingo_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=DOMINGO, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:29 |
| reports/figures/eda/curva_intraday_1_festivo_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=FESTIVO, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:26 |
| reports/figures/eda/curva_intraday_1_festivo_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=FESTIVO, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:28 |
| reports/figures/eda/curva_intraday_1_festivo_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=FESTIVO, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:29 |
| reports/figures/eda/curva_intraday_1_festivo_puente_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=FESTIVO_PUENTE, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_festivo_puente_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=FESTIVO_PUENTE, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:28 |
| reports/figures/eda/curva_intraday_1_festivo_puente_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=FESTIVO_PUENTE, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_1_laboral_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=LABORAL, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_laboral_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=LABORAL, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:28 |
| reports/figures/eda/curva_intraday_1_laboral_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=LABORAL, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_1_sabado_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=SABADO, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_sabado_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=SABADO, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:29 |
| reports/figures/eda/curva_intraday_1_sabado_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 1, tipo_día=SABADO, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_3_domingo_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=DOMINGO, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_3_domingo_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=DOMINGO, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:32 |
| reports/figures/eda/curva_intraday_3_domingo_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=DOMINGO, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:34 |
| reports/figures/eda/curva_intraday_3_festivo_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=FESTIVO, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:31 |
| reports/figures/eda/curva_intraday_3_festivo_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=FESTIVO, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:32 |
| reports/figures/eda/curva_intraday_3_festivo_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=FESTIVO, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:34 |
| reports/figures/eda/curva_intraday_3_festivo_puente_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=FESTIVO_PUENTE, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:31 |
| reports/figures/eda/curva_intraday_3_festivo_puente_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=FESTIVO_PUENTE, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:33 |
| reports/figures/eda/curva_intraday_3_festivo_puente_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=FESTIVO_PUENTE, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:34 |
| reports/figures/eda/curva_intraday_3_laboral_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=LABORAL, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:31 |
| reports/figures/eda/curva_intraday_3_laboral_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=LABORAL, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:33 |
| reports/figures/eda/curva_intraday_3_laboral_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=LABORAL, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:35 |
| reports/figures/eda/curva_intraday_3_sabado_g15min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=SABADO, granularidad 15 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:32 |
| reports/figures/eda/curva_intraday_3_sabado_g30min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=SABADO, granularidad 30 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:33 |
| reports/figures/eda/curva_intraday_3_sabado_g60min.png | scripts/run_eda_temporal.py | Perfil intradía de demanda para Ruta 3, tipo_día=SABADO, granularidad 60 min. | 1973x973px; dpi 200x200 | 2026-05-07 18:35:35 |
| reports/figures/eda/demand_by_hour_weekday.png | src/proyecto_grado/analytics/plots.py | Heatmap de demanda acumulada por día de semana y hora. | 2185x1137px; dpi 220x220 | 2026-04-25 11:18:42 |
| reports/figures/eda/demand_by_route.png | src/proyecto_grado/analytics/plots.py | Comparación de pasajeros acumulados por ruta. | 1553x939px; dpi 220x220 | 2026-04-25 11:18:42 |
| reports/figures/eda/etl_rows_by_stage.png | src/proyecto_grado/analytics/plots.py | Conteo de registros conservados por etapa del ETL. | 1773x939px; dpi 220x220 | 2026-04-25 11:18:41 |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g15min.png | scripts/run_eda_temporal.py | Demanda promedio por hora y día de semana para Ruta 1 a 15 min. | 2185x973px; dpi 200x200 | 2026-05-07 18:35:35 |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g30min.png | scripts/run_eda_temporal.py | Demanda promedio por hora y día de semana para Ruta 1 a 30 min. | 2185x973px; dpi 200x200 | 2026-05-07 18:35:36 |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g60min.png | scripts/run_eda_temporal.py | Demanda promedio por hora y día de semana para Ruta 1 a 60 min. | 2185x973px; dpi 200x200 | 2026-05-07 18:35:37 |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g15min.png | scripts/run_eda_temporal.py | Demanda promedio por hora y día de semana para Ruta 3 a 15 min. | 2185x973px; dpi 200x200 | 2026-05-07 18:35:38 |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g30min.png | scripts/run_eda_temporal.py | Demanda promedio por hora y día de semana para Ruta 3 a 30 min. | 2185x973px; dpi 200x200 | 2026-05-07 18:35:38 |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g60min.png | scripts/run_eda_temporal.py | Demanda promedio por hora y día de semana para Ruta 3 a 60 min. | 2186x973px; dpi 200x200 | 2026-05-07 18:35:39 |
| reports/figures/eda/qc_flags_top.png | src/proyecto_grado/analytics/plots.py | Principales flags de calidad del ETL por frecuencia. | 2039x1203px; dpi 220x220 | 2026-04-25 11:18:42 |
| reports/figures/eda/tendencia_mensual_1.png | scripts/run_eda_temporal.py | Tendencia mensual de demanda total para Ruta 1. | 2173x973px; dpi 200x200 | 2026-05-07 18:35:40 |
| reports/figures/eda/tendencia_mensual_3.png | scripts/run_eda_temporal.py | Tendencia mensual de demanda total para Ruta 3. | 2173x973px; dpi 200x200 | 2026-05-07 18:35:40 |
| reports/figures/operational_heatmap_1_15min.png | src/proyecto_grado/features/operational_hours.py:354-372 | Mapa de calor de cobertura operativa para Ruta 1 a 15 min. | 1394x2267px; dpi 120x120 | 2026-05-03 18:02:13 |
| reports/figures/operational_heatmap_1_30min.png | src/proyecto_grado/features/operational_hours.py:354-372 | Mapa de calor de cobertura operativa para Ruta 1 a 30 min. | 1334x1067px; dpi 120x120 | 2026-05-03 18:02:14 |
| reports/figures/operational_heatmap_1_60min.png | src/proyecto_grado/features/operational_hours.py:354-372 | Mapa de calor de cobertura operativa para Ruta 1 a 60 min. | 1328x947px; dpi 120x120 | 2026-05-03 18:02:14 |
| reports/figures/operational_heatmap_3_15min.png | src/proyecto_grado/features/operational_hours.py:354-372 | Mapa de calor de cobertura operativa para Ruta 3 a 15 min. | 1394x2267px; dpi 120x120 | 2026-05-03 18:02:15 |
| reports/figures/operational_heatmap_3_30min.png | src/proyecto_grado/features/operational_hours.py:354-372 | Mapa de calor de cobertura operativa para Ruta 3 a 30 min. | 1334x1067px; dpi 120x120 | 2026-05-03 18:02:15 |
| reports/figures/operational_heatmap_3_60min.png | src/proyecto_grado/features/operational_hours.py:354-372 | Mapa de calor de cobertura operativa para Ruta 3 a 60 min. | 1328x947px; dpi 120x120 | 2026-05-03 18:02:15 |

## Figuras solo en código

| Ubicación | Librería | Título/ejes observables | Qué muestra | Formato | Modificado |
| --- | --- | --- | --- | --- | --- |
| src/proyecto_grado/dashboard/app.py:407 (plot_row_counts_inline) | Streamlit + seaborn/matplotlib | Registros conservados por etapa del ETL; x: etapa; y: filas | Conteo interactivo de filas por etapa ETL. | st.pyplot; figsize 8.5x4.4 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:432 (plot_qc_flags_inline) | Streamlit + seaborn/matplotlib | Principales alertas de calidad del ETL; x: registros; y: flag | Top de flags QC en el dashboard. | st.pyplot; figsize 9.2x5.4 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:449 (plot_finalization_pie) | Streamlit + matplotlib | Clasificación de fin de recorrido; gráfico circular | Distribución porcentual de FIN_TIPO. | st.pyplot; figsize 6.4x4.6 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:469 (plot_demand_by_route_inline) | Streamlit + seaborn/matplotlib | Demanda por ruta; x: ruta; y: métrica seleccionada | Comparación interactiva de pasajeros totales o promedio por despacho. | st.pyplot; figsize 8x4.5 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:488 (plot_hour_weekday_heatmap_inline) | Streamlit + seaborn/matplotlib | Distribución horaria de demanda por día; x: hora; y: día semana | Heatmap interactivo de demanda por hora y día. | st.pyplot; figsize 11x5.2 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:631 (plot_time_series_trend_inline) | Streamlit + Altair | Evolución temporal con atípicos contextuales; x: fecha; y: métrica | Serie temporal filtrable con media móvil y atípicos. | Altair; height 520 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:796 (plot_time_series_heatmap_inline) | Streamlit + seaborn/matplotlib | Patrón promedio por día y hora; x: hora; y: día semana | Heatmap de la métrica temporal seleccionada. | st.pyplot; figsize 11x5.2 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:832 (plot_time_series_distribution_inline) | Streamlit + seaborn/matplotlib | Distribución de demanda por franja; x: franja/hora; y: métrica | Boxplot de métrica temporal seleccionada por franja. | st.pyplot; figsize 10.5x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:857 (plot_outlier_heatmap_inline) | Streamlit + seaborn/matplotlib | Concentración de atípicos; x: hora; y: día semana | Conteo de atípicos contextuales por día y hora. | st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:890 (plot_gap_heatmap_inline) | Streamlit + seaborn/matplotlib | Franjas imputadas como gap; x: hora; y: día semana | Porcentaje de gaps por día y hora. | st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:957 (plot_gaps_comparison_bars) | Streamlit + matplotlib | Gaps horario operativo vs 24h; x: tipo día; y: % gaps | Comparación de gaps dentro del horario operativo frente a 24h. | st.pyplot; figsize 10x5 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:995 (plot_gap_type_heatmap_inline) | Streamlit + seaborn/matplotlib | gap_anomalo/fuera_operacion por día y hora | Heatmap para tipo de gap seleccionado. | st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:1034 (render_operational_hours_section) | Streamlit + Altair | Horario operativo estimado; x: hora; y: tipo de día | Bandas de inicio-fin operativo estimado por tipo de día. | Altair; height max(210, n_tipos*42) | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:1153 (plot_granularity_comparison_inline) | Streamlit + seaborn/matplotlib | Impacto de granularidad; subplots n_franjas, pct_gaps y métrica | Comparación entre granularidades 15/30/60 para una ruta. | st.pyplot; figsize 13x4.2 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:1848 (plot_eda_intraday_inline) | Streamlit + matplotlib | Perfil intradía EDA; x: hora; y: pasajeros promedio | Perfil intradía interactivo con banda p25-p75 o tipos de día superpuestos. | st.pyplot; figsize 11x5.2 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:1939 (plot_eda_weekly_heatmap_inline) | Streamlit + seaborn/matplotlib | Demanda promedio por día y hora; x: hora; y: día semana | Heatmap EDA por ruta y granularidad. | st.pyplot; figsize 11x5 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:1983 (plot_eda_monthly_trend_inline) | Streamlit + matplotlib | Tendencia mensual; x: periodo; y: pasajeros | Barras mensuales con tendencia visual y meses atípicos. | st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:2044 (plot_eda_autocorrelation_inline) | Streamlit + matplotlib | ACF/PACF; x: lag; y: correlación | ACF/PACF interactivo desde artefactos EDA. | st.pyplot; figsize 12x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/dashboard/app.py:2100 (plot_eda_outliers_inline) | Streamlit + matplotlib | Atípicos sobre serie operativa; x: fecha; y: pasajeros | Serie de pasajeros con atípicos resaltados. | st.pyplot; figsize 12x4.8 | 2026-05-13 16:39:54 |
| src/proyecto_grado/etl/gps.py:84 (validar_radio_con_nulos) | matplotlib plt.show | Distancia mínima al patio; x: distancia; y: frecuencia | Histograma de distancias GPS mínimas al patio para validar radio en registros nulos. | plt.show; figsize 10x4 | 2026-05-02 13:05:44 |

## Tablas pequeñas clave

### `reports/tables/baseline/headway_summary.csv`
```csv
FK_RUTA,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,50658.0,10.97,7.92,0.722,9.15,24.17,3.82,2.79
3,53223.0,10.56,8.17,0.774,8.58,24.7,4.71,3.09
```

### `reports/tables/baseline/fleet_availability_summary.csv`
```csv
n_dias_analizados,total_headways_largos,pct_largos_pico_manana,pct_largos_pico_tarde,pct_largos_cierre,pct_largos_otros,disp_promedio_pico_manana,disp_promedio_pico_tarde,disp_promedio_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre
30,447,19.5,15.7,14.3,50.6,2.67,7.11,3.15,34.1,0.0,5.6
```

### `reports/tables/baseline/diagnostico_flota_comparacion.csv`
```csv
indicador,primer_mes,ultimo_mes,variacion_absoluta,variacion_pct
Vehículos activos,63.0,42.0,-21.0,-33.3
Despachos totales,5266.0,3179.0,-2087.0,-39.6
Pasajeros totales,247688.0,145868.0,-101820.0,-41.1
Productividad pas/despacho,47.04,45.88,-1.16,-2.5
Despachos por vehículo (intensidad de uso),83.59,75.69,-7.9,-9.5
```

### `reports/tables/baseline/productivity_summary.csv`
```csv
FK_RUTA,n_semanas_validas,productividad_promedio_bruta,productividad_p50,productividad_std,tendencia_slope_semanal,tendencia_slope_mensual_est,primera_semana_estimada,ultima_semana_estimada,caida_total_periodo
1,111,44.4,44.51,2.53,0.005,0.02,44.15,44.66,-0.51
3,111,48.5,48.65,2.47,0.006,0.025,48.18,48.83,-0.65
```

### `reports/tables/eda/duration_by_route.csv`
```csv
FK_RUTA,count,mean,median,p95
1,51041,160.56265126728186,157.3,199.06666666666666
3,53609,161.33999359560272,161.03333333333333,213.38333333333333
```

### `reports/tables/eda/finalization_summary.csv`
```csv
FIN_TIPO,count,pct
COMPLETO,90450,86.30478135167886
TRUNCADO_RETORNO,11327,10.807896720513725
TRUNCADO_INDETERMINADO,1886,1.7995668062937131
TRUNCADO_ABANDONO,1115,1.0639008425331336
SIN_GPS,25,0.023854278980563533
```

### `reports/tables/baseline/diagnostico_flota_mensual.csv` (primeras 3 filas)
```csv
mes,vehiculos_activos,despachos_total,pasajeros_total,productividad_por_despacho,despachos_por_vehiculo
2024-04-01,63,2514,128555,51.14,39.9
2024-05-01,63,5266,247688,47.04,83.59
2024-06-01,63,4783,215341,45.02,75.92
```

### `reports/tables/baseline/diagnostico_flota_mensual.csv` (últimas 3 filas)
```csv
mes,vehiculos_activos,despachos_total,pasajeros_total,productividad_por_despacho,despachos_por_vehiculo
2026-04-01,42,3395,154566,45.53,80.83
2026-05-01,42,3179,145868,45.88,75.69
2026-06-01,37,1039,48278,46.47,28.08
```

## Inventario de tablas persistidas

### `data/processed/eda/atipicos_1_g15min.parquet`

- Descripción: Franjas operativas atípicas de pasajeros detectadas por IQR y/o z-score por tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `447 x 12`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 05:15:00,2024-04-16,5,LABORAL,193.0,True,True,3.3730902868662835,ambos,-30.5,165.5,1.3611863942263773
2024-04-16 06:00:00,2024-04-16,6,LABORAL,229.0,True,True,4.412851945512669,ambos,-30.5,165.5,1.3611863942263773
2024-04-16 15:45:00,2024-04-16,15,LABORAL,166.0,True,False,2.5932690428814946,IQR,-30.5,165.5,1.3611863942263773
```

### `data/processed/eda/atipicos_1_g30min.parquet`

- Descripción: Franjas operativas atípicas de pasajeros detectadas por IQR y/o z-score por tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `121 x 12`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 06:00:00,2024-04-16,6,LABORAL,315.0,True,True,3.109452696887395,ambos,-51.0,293.0,0.6545139827987234
2024-04-18 05:30:00,2024-04-18,5,LABORAL,352.0,True,True,3.780123371921941,ambos,-51.0,293.0,0.6545139827987234
2024-04-21 16:30:00,2024-04-21,16,DOMINGO,96.0,False,True,3.5337838880850665,zscore,-51.0,293.0,0.6545139827987234
```

### `data/processed/eda/atipicos_1_g60min.parquet`

- Descripción: Franjas operativas atípicas de pasajeros detectadas por IQR y/o z-score por tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `27 x 12`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-18 05:00:00,2024-04-18,5,LABORAL,621.0,True,True,3.515931492375089,ambos,-129.0,575.0,0.2696225284601558
2024-04-23 05:00:00,2024-04-23,5,LABORAL,583.0,True,True,3.133436443919811,ambos,-129.0,575.0,0.2696225284601558
2024-05-12 08:00:00,2024-05-12,8,DOMINGO,149.0,False,True,3.1651734197074894,zscore,-129.0,575.0,0.2696225284601558
```

### `data/processed/eda/atipicos_3_g15min.parquet`

- Descripción: Franjas operativas atípicas de pasajeros detectadas por IQR y/o z-score por tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `771 x 12`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 05:45:00,2024-04-16,5,LABORAL,195.0,True,False,2.403213563430973,IQR,-42.5,193.5,2.339411961040143
2024-04-16 06:00:00,2024-04-16,6,LABORAL,219.0,True,False,2.943209219353117,IQR,-42.5,193.5,2.339411961040143
2024-04-16 06:15:00,2024-04-16,6,LABORAL,197.0,True,False,2.448213201424485,IQR,-42.5,193.5,2.339411961040143
```

### `data/processed/eda/atipicos_3_g30min.parquet`

- Descripción: Franjas operativas atípicas de pasajeros detectadas por IQR y/o z-score por tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `341 x 12`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 05:30:00,2024-04-16,5,LABORAL,362.0,True,False,2.5418418751459644,IQR,-98.0,358.0,1.8143123171056132
2024-04-16 06:00:00,2024-04-16,6,LABORAL,416.0,True,True,3.233583665955704,ambos,-98.0,358.0,1.8143123171056132
2024-04-17 05:30:00,2024-04-17,5,LABORAL,407.0,True,True,3.118293367487414,ambos,-98.0,358.0,1.8143123171056132
```

### `data/processed/eda/atipicos_3_g60min.parquet`

- Descripción: Franjas operativas atípicas de pasajeros detectadas por IQR y/o z-score por tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `124 x 12`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 06:00:00,2024-04-16,6,LABORAL,757.0,True,True,3.102023615176226,ambos,-182.0,674.0,1.244355243351731
2024-04-17 05:00:00,2024-04-17,5,LABORAL,709.0,True,False,2.7629220810346795,IQR,-182.0,674.0,1.244355243351731
2024-04-17 06:00:00,2024-04-17,6,LABORAL,740.0,True,False,2.9819251551677617,IQR,-182.0,674.0,1.244355243351731
```

### `data/processed/eda/autocorr_1_g15min.parquet`

- Descripción: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `49 x 13`
- Fecha de última modificación: `2026-05-07 18:35:16`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-14.17501571665056,1.973028235955265e-26,True,1,15
1,0.20534829989383094,0.2053482998938309,-0.010815662560168499,0.010815662560168499,True,True,False,-14.17501571665056,1.973028235955265e-26,True,1,15
2,0.2962102386664353,0.26522635943606726,-0.011262506046542664,0.011262506046542664,True,True,False,-14.17501571665056,1.973028235955265e-26,True,1,15
```

### `data/processed/eda/autocorr_1_g30min.parquet`

- Descripción: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `49 x 13`
- Fecha de última modificación: `2026-05-07 18:35:18`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-18.875286567668546,0.0,True,1,30
1,0.5023068295883818,0.5023068295883816,-0.014415007424512238,0.014415007424512294,True,True,True,-18.875286567668546,0.0,True,1,30
2,0.4777079302953831,0.3014570579970273,-0.017681899037881754,0.017681899037881754,True,True,True,-18.875286567668546,0.0,True,1,30
```

### `data/processed/eda/autocorr_1_g60min.parquet`

- Descripción: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `49 x 13`
- Fecha de última modificación: `2026-05-07 18:35:19`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-15.94627957524435,7.443246455064352e-29,True,1,60
1,0.6485654045609283,0.6485654045609283,-0.019585934486457957,0.019585934486457957,True,True,True,-15.94627957524435,7.443246455064352e-29,True,1,60
2,0.3858760096143572,-0.05999879077265652,-0.026576851370178678,0.026576851370178678,True,True,True,-15.94627957524435,7.443246455064352e-29,True,1,60
```

### `data/processed/eda/autocorr_3_g15min.parquet`

- Descripción: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `49 x 13`
- Fecha de última modificación: `2026-05-07 18:35:23`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-14.126387294892552,2.3754431556336704e-26,True,3,15
1,0.3794979168029455,0.37949791680294553,-0.010796282874383056,0.010796282874383056,True,True,True,-14.126387294892552,2.3754431556336704e-26,True,3,15
2,0.4138003143638548,0.3151723474460383,-0.012252888494627578,0.012252888494627578,True,True,True,-14.126387294892552,2.3754431556336704e-26,True,3,15
```

### `data/processed/eda/autocorr_3_g30min.parquet`

- Descripción: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `49 x 13`
- Fecha de última modificación: `2026-05-07 18:35:24`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-21.771769223092672,0.0,True,3,30
1,0.6261132018639527,0.6261132018639528,-0.014296407741527406,0.014296407741527406,True,True,True,-21.771769223092672,0.0,True,3,30
2,0.4875072641952538,0.15705971896302243,-0.019095396033233403,0.019095396033233403,True,True,True,-21.771769223092672,0.0,True,3,30
```

### `data/processed/eda/autocorr_3_g60min.parquet`

- Descripción: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `49 x 13`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-16.15433919123102,4.5347226513403795e-29,True,3,60
1,0.61981324202494,0.6198132420249399,-0.019634029514386864,0.019634029514386864,True,True,True,-16.15433919123102,4.5347226513403795e-29,True,3,60
2,0.2547623688933479,-0.21013227910224286,-0.02610910263531152,0.02610910263531152,True,True,False,-16.15433919123102,4.5347226513403795e-29,True,3,60
```

### `data/processed/eda/correlacion_features.parquet`

- Descripción: Ranking de correlaciones Spearman entre PASAJEROS y variables numéricas/codificadas.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `13 x 4`
- Fecha de última modificación: `2026-05-07 18:35:25`
- Columnas y tipos: `feature: str; correlacion_spearman: float64; abs_correlacion: float64; rank: int64`
- Muestra (`head(3)`):

```csv
feature,correlacion_spearman,abs_correlacion,rank
DURACION_MIN_FINAL,0.3351661329697794,0.3351661329697794,1
PLACA,0.2679366847239228,0.2679366847239228,2
DISTANCIA,0.24304526041464544,0.24304526041464544,3
```

### `data/processed/eda/perfil_intraday_1_g15min.parquet`

- Descripción: Perfil intradía por ruta/granularidad/tipo de día con media, mediana, cuantiles y horas pico/valle.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `72 x 12`
- Fecha de última modificación: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,12.5,12.5,12.25,12.75,12.95,False,True,1.3982180248568763,"8,9,12,16","4,5,7,17"
DOMINGO,5,29.48611111111111,29.0,23.0,35.0,41.45,False,True,1.3982180248568763,"8,9,12,16","4,5,7,17"
DOMINGO,6,30.236220472440944,29.0,26.0,35.0,45.0,False,False,1.3982180248568763,"8,9,12,16","4,5,7,17"
```

### `data/processed/eda/perfil_intraday_1_g30min.parquet`

- Descripción: Perfil intradía por ruta/granularidad/tipo de día con media, mediana, cuantiles y horas pico/valle.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `72 x 12`
- Fecha de última modificación: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,12.5,12.5,12.25,12.75,12.95,False,True,1.5040803420533355,"8,9,11,12","4,5,13,17"
DOMINGO,5,33.698412698412696,30.0,24.0,38.0,67.8,False,True,1.5040803420533355,"8,9,11,12","4,5,13,17"
DOMINGO,6,39.183673469387756,35.0,27.25,50.0,67.29999999999998,False,False,1.5040803420533355,"8,9,11,12","4,5,13,17"
```

### `data/processed/eda/perfil_intraday_1_g60min.parquet`

- Descripción: Perfil intradía por ruta/granularidad/tipo de día con media, mediana, cuantiles y horas pico/valle.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `72 x 12`
- Fecha de última modificación: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,12.5,12.5,12.25,12.75,12.95,False,True,2.039453222651428,"7,8,9,10","4,5,16,17"
DOMINGO,5,46.15217391304348,41.5,32.25,61.5,76.75,False,True,2.039453222651428,"7,8,9,10","4,5,16,17"
DOMINGO,6,64.0,62.0,34.5,90.25,117.05,False,False,2.039453222651428,"7,8,9,10","4,5,16,17"
```

### `data/processed/eda/perfil_intraday_3_g15min.parquet`

- Descripción: Perfil intradía por ruta/granularidad/tipo de día con media, mediana, cuantiles y horas pico/valle.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `72 x 12`
- Fecha de última modificación: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,26.166666666666668,26.5,20.0,31.25,38.05,False,True,1.1775643255524622,"8,9,10,16","4,5,7,13"
DOMINGO,5,29.77391304347826,27.0,23.0,33.0,57.0,False,True,1.1775643255524622,"8,9,10,16","4,5,7,13"
DOMINGO,6,30.352459016393443,29.0,25.0,34.0,50.94999999999999,False,False,1.1775643255524622,"8,9,10,16","4,5,7,13"
```

### `data/processed/eda/perfil_intraday_3_g30min.parquet`

- Descripción: Perfil intradía por ruta/granularidad/tipo de día con media, mediana, cuantiles y horas pico/valle.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `72 x 12`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,32.04081632653061,30.0,22.0,38.0,57.599999999999994,False,True,1.2554425167815582,"8,9,10,11","4,13,14,17"
DOMINGO,5,38.47191011235955,33.0,25.0,50.0,65.0,False,False,1.2554425167815582,"8,9,10,11","4,13,14,17"
DOMINGO,6,38.175257731958766,34.0,27.0,49.0,63.599999999999966,False,False,1.2554425167815582,"8,9,10,11","4,13,14,17"
```

### `data/processed/eda/perfil_intraday_3_g60min.parquet`

- Descripción: Perfil intradía por ruta/granularidad/tipo de día con media, mediana, cuantiles y horas pico/valle.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `72 x 12`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,36.51162790697674,34.0,28.0,51.0,58.9,False,True,1.7223785356471522,"5,6,8,10","4,13,16,17"
DOMINGO,5,68.48,66.5,55.25,85.25,111.24999999999996,True,False,1.7223785356471522,"5,6,8,10","4,13,16,17"
DOMINGO,6,66.125,67.5,49.25,86.0,109.25,True,False,1.7223785356471522,"5,6,8,10","4,13,16,17"
```

### `data/processed/eda/perfil_mensual_1.parquet`

- Descripción: Demanda mensual/semanal por ruta con tendencia OLS y meses atípicos.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `133 x 6`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `periodo: str; demanda_total: float64; tipo_periodo: str; es_atipico: bool; tendencia_slope: float64; tendencia_intercept: float64`
- Muestra (`head(3)`):

```csv
periodo,demanda_total,tipo_periodo,es_atipico,tendencia_slope,tendencia_intercept
2024-04,60975.0,mes,False,-1.9902526077837601,3801.2737875099074
2024-05,118783.0,mes,False,-1.9902526077837601,3801.2737875099074
2024-06,103512.0,mes,False,-1.9902526077837601,3801.2737875099074
```

### `data/processed/eda/perfil_mensual_3.parquet`

- Descripción: Demanda mensual/semanal por ruta con tendencia OLS y meses atípicos.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `133 x 6`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `periodo: str; demanda_total: float64; tipo_periodo: str; es_atipico: bool; tendencia_slope: float64; tendencia_intercept: float64`
- Muestra (`head(3)`):

```csv
periodo,demanda_total,tipo_periodo,es_atipico,tendencia_slope,tendencia_intercept
2024-04,67580.0,mes,False,-1.73687526212746,4157.428792757541
2024-05,128905.0,mes,False,-1.73687526212746,4157.428792757541
2024-06,111829.0,mes,False,-1.73687526212746,4157.428792757541
```

### `data/processed/eda/perfil_semanal_1_g15min.parquet`

- Descripción: Perfil semanal de demanda por día de semana con totales, promedios y variabilidad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `7 x 7`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,345166.0,72.08980785296575,0.5108319281331668,Lunes,False,False
1,428368.0,78.87460872767446,0.4420362152469957,Martes,True,False
2,389507.0,74.10711567732116,0.4609696365610281,Miercoles,False,False
```

### `data/processed/eda/perfil_semanal_1_g30min.parquet`

- Descripción: Perfil semanal de demanda por día de semana con totales, promedios y variabilidad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `7 x 7`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,345166.0,129.13056490834268,0.4896075386658852,Lunes,False,False
1,428368.0,148.7905522750955,0.3733647652750276,Martes,True,False
2,389507.0,138.5652792600498,0.4049842296939777,Miercoles,False,False
```

### `data/processed/eda/perfil_semanal_1_g60min.parquet`

- Descripción: Perfil semanal de demanda por día de semana con totales, promedios y variabilidad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `7 x 7`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,345166.0,240.19902574808629,0.49398977664300275,Lunes,False,False
1,428368.0,281.26592252133946,0.3664258260470872,Martes,True,False
2,389507.0,261.2387659289068,0.38868653649705415,Miercoles,False,False
```

### `data/processed/eda/perfil_semanal_3_g15min.parquet`

- Descripción: Perfil semanal de demanda por día de semana con totales, promedios y variabilidad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `7 x 7`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,403349.0,83.33657024793388,0.5498174469187028,Lunes,False,False
1,494851.0,90.73175650898423,0.5004783029389859,Martes,True,False
2,449067.0,85.2928774928775,0.5196555980570245,Miercoles,False,False
```

### `data/processed/eda/perfil_semanal_3_g30min.parquet`

- Descripción: Perfil semanal de demanda por día de semana con totales, promedios y variabilidad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `7 x 7`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,403349.0,147.96368305209097,0.5713464260290211,Lunes,False,False
1,494851.0,169.00648907103826,0.47694548394131697,Martes,True,False
2,449067.0,156.90670859538784,0.49951468980180175,Miercoles,False,False
```

### `data/processed/eda/perfil_semanal_3_g60min.parquet`

- Descripción: Perfil semanal de demanda por día de semana con totales, promedios y variabilidad.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py
- Forma: `7 x 7`
- Fecha de última modificación: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,403349.0,282.6552207428171,0.5673528462150763,Lunes,False,False
1,494851.0,328.5863213811421,0.44306640858941193,Martes,True,False
2,449067.0,302.4020202020202,0.4792637853814676,Miercoles,False,False
```

### `data/processed/model_ready/despachos_model_ready.csv`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `109559 x 18`
- Fecha de última modificación: `2026-06-10 19:21:42`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready.parquet`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `109559 x 18`
- Fecha de última modificación: `2026-06-10 19:21:43`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready_freeze_20260503_114750.csv`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `105490 x 18`
- Fecha de última modificación: `2026-05-03 11:47:52`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready_freeze_20260503_114750.parquet`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `105490 x 18`
- Fecha de última modificación: `2026-05-03 11:47:51`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready_freeze_20260610_191955.csv`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `109559 x 18`
- Fecha de última modificación: `2026-06-10 19:19:57`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready_freeze_20260610_191955.parquet`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `109559 x 18`
- Fecha de última modificación: `2026-06-10 19:19:55`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.csv`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `109559 x 18`
- Fecha de última modificación: `2026-06-10 19:21:47`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.parquet`

- Descripción: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA.
- Fuente: src/proyecto_grado/etl/model_ready.py:110-111,262-264
- Forma: `109559 x 18`
- Fecha de última modificación: `2026-06-10 19:21:43`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

### `data/processed/operational_hours.parquet`

- Descripción: Horario operativo estimado por ruta, tipo de día y granularidad.
- Fuente: src/proyecto_grado/features/operational_hours.py:289-290
- Forma: `30 x 14`
- Fecha de última modificación: `2026-05-03 18:02:13`
- Columnas y tipos: `tipo_dia: str; ruta: int64; granularidad_min: int64; hora_inicio_op: str; hora_fin_op: str; hora_inicio_op_min: int64; hora_fin_op_min: int64; duracion_operativa_h: float64; n_dias_muestra: int64; n_dias_usado: int64; umbral_usado: float64; fallback_laboral: bool; franjas_anomalas_count: int64; pct_cobertura_dentro_horario: float64`
- Muestra (`head(3)`):

```csv
tipo_dia,ruta,granularidad_min,hora_inicio_op,hora_fin_op,hora_inicio_op_min,hora_fin_op_min,duracion_operativa_h,n_dias_muestra,n_dias_usado,umbral_usado,fallback_laboral,franjas_anomalas_count,pct_cobertura_dentro_horario
LABORAL,1,15,04:30,18:00,270,1080,13.75,501,501,0.1,False,1,1.0
SABADO,1,15,04:30,17:45,270,1065,13.5,106,106,0.1,False,2,1.0
DOMINGO,1,15,05:15,17:00,315,1020,12.0,105,105,0.1,False,10,1.0
```

### `data/processed/time_series/ts_ruta1_g15min.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `71727 x 19`
- Fecha de última modificación: `2026-05-03 18:02:18`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:30:00,120.0,2,60.0,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,1,True,operativo
2024-04-16 04:45:00,109.0,2,54.5,59.45,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,1,True,operativo
2024-04-16 05:00:00,87.0,2,43.5,43.95,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,15,1,True,operativo
```

### `data/processed/time_series/ts_ruta1_g30min.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `35864 x 19`
- Fecha de última modificación: `2026-05-03 18:02:21`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:30:00,229.0,4,57.25,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,30,1,True,operativo
2024-04-16 05:00:00,280.0,5,56.0,71.8,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,30,1,True,operativo
2024-04-16 05:30:00,261.0,5,52.2,58.0,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,30,1,True,operativo
```

### `data/processed/time_series/ts_ruta1_g60min.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `17933 x 19`
- Fecha de última modificación: `2026-05-03 18:02:23`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:00:00,229.0,4,57.25,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,60,1,True,operativo
2024-04-16 05:00:00,541.0,10,54.1,69.04999999999998,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,60,1,True,operativo
2024-04-16 06:00:00,554.0,11,50.36363636363637,68.0,False,6,1,False,4,16,2,MANANA,False,LABORAL,60,1,True,operativo
```

### `data/processed/time_series/ts_ruta3_g15min.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `71732 x 19`
- Fecha de última modificación: `2026-05-03 18:02:20`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:15:00,49.0,1,49.0,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,3,True,operativo
2024-04-16 04:30:00,90.0,2,45.0,48.6,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,3,True,operativo
2024-04-16 04:45:00,42.0,1,42.0,42.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,3,True,operativo
```

### `data/processed/time_series/ts_ruta3_g30min.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `35867 x 19`
- Fecha de última modificación: `2026-05-03 18:02:23`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:00:00,49.0,1,49.0,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,30,3,True,operativo
2024-04-16 04:30:00,132.0,3,44.0,48.3,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,30,3,True,operativo
2024-04-16 05:00:00,294.0,5,58.8,75.8,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,30,3,True,operativo
```

### `data/processed/time_series/ts_ruta3_g60min.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `17934 x 19`
- Fecha de última modificación: `2026-05-03 18:02:24`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:00:00,181.0,4,45.25,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,60,3,True,operativo
2024-04-16 05:00:00,656.0,10,65.6,86.55,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,60,3,True,operativo
2024-04-16 06:00:00,757.0,11,68.81818181818181,91.5,False,6,1,False,4,16,2,MANANA,False,LABORAL,60,3,True,operativo
```

### `data/processed/time_series/ts_ruta_1.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `17933 x 16`
- Fecha de última modificación: `2026-05-03 12:22:57`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; FK_RUTA: int64`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,FK_RUTA
2024-04-16 04:00:00,229.0,4,57.25,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,1
2024-04-16 05:00:00,541.0,10,54.1,69.04999999999998,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,1
2024-04-16 06:00:00,554.0,11,50.36363636363637,68.0,False,6,1,False,4,16,2,MANANA,False,LABORAL,1
```

### `data/processed/time_series/ts_ruta_3.parquet`

- Descripción: Serie temporal agregada por ruta y granularidad con demanda, despachos, gaps y calendario operativo.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `17934 x 16`
- Fecha de última modificación: `2026-05-03 12:22:57`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; FK_RUTA: int64`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,FK_RUTA
2024-04-16 04:00:00,181.0,4,45.25,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,3
2024-04-16 05:00:00,656.0,10,65.6,86.55,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,3
2024-04-16 06:00:00,757.0,11,68.81818181818181,91.5,False,6,1,False,4,16,2,MANANA,False,LABORAL,3
```

### `reports/tables/baseline/demand_supply_by_franja.csv`

- Descripción: Tabla basada en load_factor estimado; NO utilizable como ocupación simultánea ni KPI válido de ajuste oferta-demanda.
- Fuente: src/proyecto_grado/analytics/demand_supply.py:114-116
- Forma: `40 x 11`
- Fecha de última modificación: `2026-06-08 16:01:01`
- Columnas y tipos: `FK_RUTA: int64; franja_horaria: str; tipo_dia: str; n_bins: float64; load_factor_mean: float64; load_factor_p50: float64; load_factor_p95: float64; sobrecarga_pct: float64; subcarga_pct: float64; optimo_pct: float64; desajuste_abs_mean: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,franja_horaria,tipo_dia,n_bins,load_factor_mean,load_factor_p50,load_factor_p95,sobrecarga_pct,subcarga_pct,optimo_pct,desajuste_abs_mean
1,MADRUGADA,DOMINGO,46.0,1.071,1.089,1.491,78.26,0.0,21.74,9.5
1,MADRUGADA,FESTIVO,5.0,1.204,1.143,1.423,100.0,0.0,0.0,14.8
1,MADRUGADA,FESTIVO_PUENTE,10.0,0.974,0.946,1.21,70.0,0.0,30.0,7.7
```

### `reports/tables/baseline/demand_supply_summary.csv`

- Descripción: Tabla basada en load_factor estimado; NO utilizable como ocupación simultánea ni KPI válido de ajuste oferta-demanda.
- Fuente: src/proyecto_grado/analytics/demand_supply.py:114-116
- Forma: `2 x 9`
- Fecha de última modificación: `2026-06-08 16:01:01`
- Columnas y tipos: `FK_RUTA: int64; n_bins: float64; load_factor_mean: float64; load_factor_p50: float64; load_factor_p95: float64; sobrecarga_pct: float64; subcarga_pct: float64; optimo_pct: float64; desajuste_abs_mean: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,n_bins,load_factor_mean,load_factor_p50,load_factor_p95,sobrecarga_pct,subcarga_pct,optimo_pct,desajuste_abs_mean
1,10008.0,1.544,1.545,2.179,96.34,0.25,3.41,86.3
3,9958.0,1.642,1.661,2.321,96.24,0.22,3.53,113.2
```

### `reports/tables/baseline/diagnostico_disponibilidad_flota.csv`

- Descripción: Serie de disponibilidad de vehículos en patio para un día diagnóstico puntual.
- Fuente: scripts/diagnostico_disponibilidad_flota.py o scripts/diagnostico_disponibilidad_multidia.py
- Forma: `193 x 2`
- Fecha de última modificación: `2026-06-22 20:52:17`
- Columnas y tipos: `timestamp: str; vehiculos_en_patio: int64`
- Muestra (`head(3)`):

```csv
timestamp,vehiculos_en_patio
2024-05-31 04:00:00,0
2024-05-31 04:05:00,0
2024-05-31 04:10:00,0
```

### `reports/tables/baseline/diagnostico_disponibilidad_multidia.csv`

- Descripción: Disponibilidad y headways largos por franjas críticas en una corrida multidía antigua.
- Fuente: scripts/diagnostico_disponibilidad_flota.py o scripts/diagnostico_disponibilidad_multidia.py
- Forma: `12 x 13`
- Fecha de última modificación: `2026-06-22 20:58:42`
- Columnas y tipos: `fecha: str; disp_pico_manana: float64; disp_pico_tarde: float64; disp_cierre: float64; pct_vacio_pico_manana: float64; pct_vacio_pico_tarde: float64; pct_vacio_cierre: float64; headways_largos_pico_manana: int64; headways_largos_pico_tarde: int64; headways_largos_cierre: int64; headways_largos_otros: int64; n_despachos: int64; n_vehiculos: int64`
- Muestra (`head(3)`):

```csv
fecha,disp_pico_manana,disp_pico_tarde,disp_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre,headways_largos_pico_manana,headways_largos_pico_tarde,headways_largos_cierre,headways_largos_otros,n_despachos,n_vehiculos
2024-04-16,3.17,6.67,3.83,33.3,0.0,0.0,1,0,0,4,204,57
2024-06-05,3.31,10.0,4.17,35.4,0.0,0.0,3,0,2,3,222,57
2024-07-24,1.73,9.67,3.83,60.4,0.0,0.0,3,1,1,4,188,56
```

### `reports/tables/baseline/diagnostico_flota_comparacion.csv`

- Descripción: Comparación inicio vs fin del periodo para flota activa, despachos, pasajeros, productividad e intensidad.
- Fuente: scripts/diagnostico_reduccion_flota.py:157-160
- Forma: `5 x 5`
- Fecha de última modificación: `2026-06-23 10:49:46`
- Columnas y tipos: `indicador: str; primer_mes: float64; ultimo_mes: float64; variacion_absoluta: float64; variacion_pct: float64`
- Muestra (`head(3)`):

```csv
indicador,primer_mes,ultimo_mes,variacion_absoluta,variacion_pct
Vehículos activos,63.0,42.0,-21.0,-33.3
Despachos totales,5266.0,3179.0,-2087.0,-39.6
Pasajeros totales,247688.0,145868.0,-101820.0,-41.1
```

### `reports/tables/baseline/diagnostico_flota_mensual.csv`

- Descripción: Serie mensual de vehículos activos, despachos, pasajeros, productividad por despacho e intensidad de uso.
- Fuente: scripts/diagnostico_reduccion_flota.py:157-160
- Forma: `27 x 6`
- Fecha de última modificación: `2026-06-23 10:49:46`
- Columnas y tipos: `mes: str; vehiculos_activos: int64; despachos_total: int64; pasajeros_total: int64; productividad_por_despacho: float64; despachos_por_vehiculo: float64`
- Muestra (`head(3)`):

```csv
mes,vehiculos_activos,despachos_total,pasajeros_total,productividad_por_despacho,despachos_por_vehiculo
2024-04-01,63,2514,128555,51.14,39.9
2024-05-01,63,5266,247688,47.04,83.59
2024-06-01,63,4783,215341,45.02,75.92
```

### `reports/tables/baseline/diagnostico_timeline_vehiculos.csv`

- Descripción: Timeline reconstruido de estados EN_RUTA/EN_PATIO por vehículo para diagnóstico puntual.
- Fuente: scripts/diagnostico_disponibilidad_flota.py o scripts/diagnostico_disponibilidad_multidia.py
- Forma: `384 x 5`
- Fecha de última modificación: `2026-06-22 20:52:17`
- Columnas y tipos: `PLACA: str; estado: str; inicio: str; fin: str; ruta: float64`
- Muestra (`head(3)`):

```csv
PLACA,estado,inicio,fin,ruta
SRE698,EN_RUTA,2024-05-31 05:37:25,2024-05-31 07:21:54,3.0
SRE698,EN_PATIO,2024-05-31 07:21:54,2024-05-31 07:24:56,
SRE698,EN_RUTA,2024-05-31 07:24:56,2024-05-31 09:55:57,1.0
```

### `reports/tables/baseline/diagnostico_vehiculos_estado.csv`

- Descripción: Último mes activo por placa y meses desde última operación.
- Fuente: scripts/diagnostico_reduccion_flota.py:157-160
- Forma: `67 x 3`
- Fecha de última modificación: `2026-06-23 10:49:46`
- Columnas y tipos: `PLACA: str; ultimo_mes_activo: str; meses_desde_ultimo: float64`
- Muestra (`head(3)`):

```csv
PLACA,ultimo_mes_activo,meses_desde_ultimo
SRE698,2026-06-01,0.0
VBV580,2026-05-01,1.0
VBW125,2026-06-01,0.0
```

### `reports/tables/baseline/fleet_availability_by_day.csv`

- Descripción: Disponibilidad de vehículos en patio y headways largos por día laboral analizado.
- Fuente: src/proyecto_grado/analytics/fleet_availability.py:219-224; scripts/build_fleet_availability.py
- Forma: `30 x 13`
- Fecha de última modificación: `2026-07-02 19:38:55`
- Columnas y tipos: `fecha: str; disp_pico_manana: float64; disp_pico_tarde: float64; disp_cierre: float64; pct_vacio_pico_manana: float64; pct_vacio_pico_tarde: float64; pct_vacio_cierre: float64; headways_largos_pico_manana: int64; headways_largos_pico_tarde: int64; headways_largos_cierre: int64; headways_largos_otros: int64; n_despachos: int64; n_vehiculos: int64`
- Muestra (`head(3)`):

```csv
fecha,disp_pico_manana,disp_pico_tarde,disp_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre,headways_largos_pico_manana,headways_largos_pico_tarde,headways_largos_cierre,headways_largos_otros,n_despachos,n_vehiculos
2024-04-16,3.17,6.67,3.83,33.3,0.0,0.0,1,0,0,4,204,57
2024-05-07,2.29,9.17,3.5,33.3,0.0,0.0,0,1,4,10,189,53
2024-05-27,1.54,7.12,4.0,45.8,0.0,0.0,6,2,1,6,189,49
```

### `reports/tables/baseline/fleet_availability_summary.csv`

- Descripción: Resumen agregado de disponibilidad de vehículos en patio y distribución de headways largos.
- Fuente: src/proyecto_grado/analytics/fleet_availability.py:219-224; scripts/build_fleet_availability.py
- Forma: `1 x 12`
- Fecha de última modificación: `2026-07-02 19:38:55`
- Columnas y tipos: `n_dias_analizados: int64; total_headways_largos: int64; pct_largos_pico_manana: float64; pct_largos_pico_tarde: float64; pct_largos_cierre: float64; pct_largos_otros: float64; disp_promedio_pico_manana: float64; disp_promedio_pico_tarde: float64; disp_promedio_cierre: float64; pct_vacio_pico_manana: float64; pct_vacio_pico_tarde: float64; pct_vacio_cierre: float64`
- Muestra (`head(3)`):

```csv
n_dias_analizados,total_headways_largos,pct_largos_pico_manana,pct_largos_pico_tarde,pct_largos_cierre,pct_largos_otros,disp_promedio_pico_manana,disp_promedio_pico_tarde,disp_promedio_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre
30,447,19.5,15.7,14.3,50.6,2.67,7.11,3.15,34.1,0.0,5.6
```

### `reports/tables/baseline/headway_by_franja.csv`

- Descripción: Indicadores de headway por ruta, franja horaria y tipo de día.
- Fuente: src/proyecto_grado/analytics/headway.py:134-136
- Forma: `24 x 11`
- Fecha de última modificación: `2026-06-08 17:28:37`
- Columnas y tipos: `FK_RUTA: int64; franja: str; tipo_dia: str; n_intervalos: float64; headway_mean: float64; headway_std: float64; cv_headway: float64; headway_p50: float64; headway_p95: float64; bunching_pct: float64; excess_wait_pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,franja,tipo_dia,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,MEDIODIA,DOMINGO,620.0,30.3,16.29,0.537,26.78,62.63,1.94,40.48
1,MEDIODIA,LABORAL,9340.0,10.21,5.63,0.551,9.15,20.13,3.1,0.92
1,MEDIODIA,SABADO,1397.0,13.66,6.5,0.476,12.5,26.31,2.36,2.15
```

### `reports/tables/baseline/headway_by_hour.csv`

- Descripción: Indicadores de headway por ruta, hora de inicio y tipo de día.
- Fuente: src/proyecto_grado/analytics/headway.py:134-136
- Forma: `88 x 11`
- Fecha de última modificación: `2026-06-08 17:28:37`
- Columnas y tipos: `FK_RUTA: int64; HORA_INICIO_H: float64; tipo_dia: str; n_intervalos: float64; headway_mean: float64; headway_std: float64; cv_headway: float64; headway_p50: float64; headway_p95: float64; bunching_pct: float64; excess_wait_pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,HORA_INICIO_H,tipo_dia,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,4.0,LABORAL,1210.0,7.84,4.01,0.511,7.19,15.14,7.93,0.08
1,4.0,SABADO,191.0,8.8,4.25,0.484,8.3,16.29,5.76,0.0
1,5.0,DOMINGO,29.0,24.77,9.33,0.377,22.38,36.59,0.0,24.14
```

### `reports/tables/baseline/headway_summary.csv`

- Descripción: Resumen por ruta de regularidad de headway: media, desviación, CV, p50/p95, bunching y espera excesiva.
- Fuente: src/proyecto_grado/analytics/headway.py:134-136
- Forma: `2 x 9`
- Fecha de última modificación: `2026-06-08 17:28:37`
- Columnas y tipos: `FK_RUTA: int64; n_intervalos: float64; headway_mean: float64; headway_std: float64; cv_headway: float64; headway_p50: float64; headway_p95: float64; bunching_pct: float64; excess_wait_pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,50658.0,10.97,7.92,0.722,9.15,24.17,3.82,2.79
3,53223.0,10.56,8.17,0.774,8.58,24.7,4.71,3.09
```

### `reports/tables/baseline/load_factor_distribution.csv`

- Descripción: Tabla basada en load_factor estimado; NO utilizable como ocupación simultánea ni KPI válido de ajuste oferta-demanda.
- Fuente: src/proyecto_grado/analytics/demand_supply.py:114-116
- Forma: `6 x 4`
- Fecha de última modificación: `2026-06-08 16:01:01`
- Columnas y tipos: `FK_RUTA: int64; estado_bin: str; n_bins: int64; pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,estado_bin,n_bins,pct
1,OPTIMO,341,3.41
1,SOBRECARGA,9642,96.34
1,SUBCARGA,25,0.25
```

### `reports/tables/baseline/productivity_summary.csv`

- Descripción: Resumen por ruta de productividad por despacho semanal y tendencia OLS.
- Fuente: src/proyecto_grado/analytics/vehicle_productivity.py:158-162; scripts/build_productivity.py
- Forma: `2 x 10`
- Fecha de última modificación: `2026-06-23 10:40:24`
- Columnas y tipos: `FK_RUTA: int64; n_semanas_validas: int64; productividad_promedio_bruta: float64; productividad_p50: float64; productividad_std: float64; tendencia_slope_semanal: float64; tendencia_slope_mensual_est: float64; primera_semana_estimada: float64; ultima_semana_estimada: float64; caida_total_periodo: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,n_semanas_validas,productividad_promedio_bruta,productividad_p50,productividad_std,tendencia_slope_semanal,tendencia_slope_mensual_est,primera_semana_estimada,ultima_semana_estimada,caida_total_periodo
1,111,44.4,44.51,2.53,0.005,0.02,44.15,44.66,-0.51
3,111,48.5,48.65,2.47,0.006,0.025,48.18,48.83,-0.65
```

### `reports/tables/baseline/productivity_weekly_series.csv`

- Descripción: Serie semanal por ruta de pasajeros, despachos, productividad bruta, tendencia OLS y productividad ajustada.
- Fuente: src/proyecto_grado/analytics/vehicle_productivity.py:158-162; scripts/build_productivity.py
- Forma: `222 x 7`
- Fecha de última modificación: `2026-06-23 10:40:24`
- Columnas y tipos: `semana: str; FK_RUTA: int64; pasajeros_total: int64; despachos_total: int64; productividad_bruta: float64; tendencia_ols: float64; productividad_ajustada: float64`
- Muestra (`head(3)`):

```csv
semana,FK_RUTA,pasajeros_total,despachos_total,productividad_bruta,tendencia_ols,productividad_ajustada
2024-04-22,1,27811,580,47.95,44.15,48.2
2024-04-22,3,30180,566,53.32,48.18,53.64
2024-04-29,1,25278,559,45.22,44.15,45.47
```

### `reports/tables/eda/dataset_overview.csv`

- Descripción: Tabla diagnóstica post-ETL sobre disponibilidad, retención, nulos, flags QC o KPIs operacionales.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `4 x 4`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `stage: str; available: bool; rows: int64; columns: int64`
- Muestra (`head(3)`):

```csv
stage,available,rows,columns
raw,True,104803,17
quality_checked,True,104803,40
trip_end_resolved,True,104803,44
```

### `reports/tables/eda/demand_by_hour_weekday.csv`

- Descripción: Demanda y despachos agregados por día de semana y hora.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `107 x 4`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `dia_semana: int64; hora: int64; despachos: int64; pasajeros_total: int64`
- Muestra (`head(3)`):

```csv
dia_semana,hora,despachos,pasajeros_total
0,4,704,30071
0,5,1497,73723
0,6,1325,75663
```

### `reports/tables/eda/demand_by_route.csv`

- Descripción: Demanda y despachos agregados por ruta.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `2 x 4`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `FK_RUTA: int64; despachos: int64; pasajeros_total: int64; pasajeros_promedio: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,despachos,pasajeros_total,pasajeros_promedio
1,51041,2270402,44.48192629454752
3,53609,2604692,48.5868417616445
```

### `reports/tables/eda/duration_by_route.csv`

- Descripción: Duración de recorridos por ruta: conteo, media, mediana y p95.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `2 x 5`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `FK_RUTA: int64; count: int64; mean: float64; median: float64; p95: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,count,mean,median,p95
1,51041,160.56265126728186,157.3,199.06666666666663
3,53609,161.33999359560272,161.03333333333333,213.38333333333333
```

### `reports/tables/eda/finalization_summary.csv`

- Descripción: Distribución de tipos de finalización de recorrido después de resolver fin de viaje.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `5 x 3`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `FIN_TIPO: str; count: int64; pct: float64`
- Muestra (`head(3)`):

```csv
FIN_TIPO,count,pct
COMPLETO,90450,86.30478135167886
TRUNCADO_RETORNO,11327,10.807896720513725
TRUNCADO_INDETERMINADO,1886,1.7995668062937131
```

### `reports/tables/eda/missing_before_after.csv`

- Descripción: Tabla diagnóstica post-ETL sobre disponibilidad, retención, nulos, flags QC o KPIs operacionales.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `7 x 5`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `column: str; raw_missing: int64; raw_missing_pct: float64; final_missing: float64; final_missing_pct: float64`
- Muestra (`head(3)`):

```csv
column,raw_missing,raw_missing_pct,final_missing,final_missing_pct
PK_INTERVALO_DESPACHO,0,0.0,0.0,0.0
PLACA,0,0.0,0.0,0.0
FK_RUTA,0,0.0,0.0,0.0
```

### `reports/tables/eda/operational_kpis.csv`

- Descripción: Tabla diagnóstica post-ETL sobre disponibilidad, retención, nulos, flags QC o KPIs operacionales.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `17 x 3`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `kpi: str; value: float64; unit: str`
- Muestra (`head(3)`):

```csv
kpi,value,unit
despachos_raw,104803.0,rows
despachos_qc,104803.0,rows
despachos_end,104803.0,rows
```

### `reports/tables/eda/qc_flag_summary.csv`

- Descripción: Tabla diagnóstica post-ETL sobre disponibilidad, retención, nulos, flags QC o KPIs operacionales.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `16 x 3`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `flag: str; count: int64; pct: float64`
- Muestra (`head(3)`):

```csv
flag,count,pct
qc_any_flag,15615,14.899382651259982
qc_soft_fail,15602,14.88697842619009
flag_hf_nula,14353,13.695218648321136
```

### `reports/tables/eda/retention_summary.csv`

- Descripción: Tabla diagnóstica post-ETL sobre disponibilidad, retención, nulos, flags QC o KPIs operacionales.
- Fuente: src/proyecto_grado/analytics/report.py y src/proyecto_grado/analytics/kpis.py/plots.py
- Forma: `1 x 4`
- Fecha de última modificación: `2026-04-25 11:18:41`
- Columnas y tipos: `raw_rows: int64; model_ready_rows: int64; rows_difference: int64; retention_pct: float64`
- Muestra (`head(3)`):

```csv
raw_rows,model_ready_rows,rows_difference,retention_pct
104803,104650,153,99.85401181263896
```

### `reports/tables/etl/model_ready_qc_20260503_114750.csv`

- Descripción: QC final del dataset model-ready: duplicados y reglas críticas.
- Fuente: src/proyecto_grado/etl/model_ready.py:255-264
- Forma: `3 x 3`
- Fecha de última modificación: `2026-05-03 11:47:50`
- Columnas y tipos: `regla: str; conteo: int64; pct: float64`
- Muestra (`head(3)`):

```csv
regla,conteo,pct
pk_duplicada,0,0.0
placa_vacia,0,0.0
duracion_no_positiva,0,0.0
```

### `reports/tables/etl/model_ready_qc_20260610_191955.csv`

- Descripción: QC final del dataset model-ready: duplicados y reglas críticas.
- Fuente: src/proyecto_grado/etl/model_ready.py:255-264
- Forma: `3 x 3`
- Fecha de última modificación: `2026-06-10 19:19:55`
- Columnas y tipos: `regla: str; conteo: int64; pct: float64`
- Muestra (`head(3)`):

```csv
regla,conteo,pct
pk_duplicada,0,0.0
placa_vacia,0,0.0
duracion_no_positiva,0,0.0
```

### `reports/tables/etl/model_ready_qc_20260610_192142.csv`

- Descripción: QC final del dataset model-ready: duplicados y reglas críticas.
- Fuente: src/proyecto_grado/etl/model_ready.py:255-264
- Forma: `3 x 3`
- Fecha de última modificación: `2026-06-10 19:21:42`
- Columnas y tipos: `regla: str; conteo: int64; pct: float64`
- Muestra (`head(3)`):

```csv
regla,conteo,pct
pk_duplicada,0,0.0
placa_vacia,0,0.0
duracion_no_positiva,0,0.0
```

### `reports/tables/gaps_horario_operativo.csv`

- Descripción: Resumen de gaps dentro del horario operativo vs 24 horas por ruta, granularidad y tipo de día.
- Fuente: src/proyecto_grado/eda/temporal_analysis.py:737
- Forma: `30 x 9`
- Fecha de última modificación: `2026-05-13 16:12:03`
- Columnas y tipos: `granularidad_min: int64; ruta: int64; tipo_dia: str; n_franjas_op: int64; n_gaps_op: int64; pct_gaps_op: float64; n_franjas_24h: int64; n_gaps_24h: int64; pct_gaps_24h: float64`
- Muestra (`head(3)`):

```csv
granularidad_min,ruta,tipo_dia,n_franjas_op,n_gaps_op,pct_gaps_op,n_franjas_24h,n_gaps_24h,pct_gaps_24h
15,1,DOMINGO,5004,2943,58.81,10017,7945,79.32
15,1,FESTIVO,768,463,60.29,1536,1228,79.95
15,1,FESTIVO_PUENTE,980,546,55.71,1920,1486,77.4
```

### `reports/tables/operational_hours_summary.csv`

- Descripción: Horario operativo estimado por ruta, tipo de día y granularidad.
- Fuente: src/proyecto_grado/features/operational_hours.py:289-290
- Forma: `30 x 14`
- Fecha de última modificación: `2026-05-03 18:02:13`
- Columnas y tipos: `tipo_dia: str; ruta: int64; granularidad_min: int64; hora_inicio_op: str; hora_fin_op: str; hora_inicio_op_min: int64; hora_fin_op_min: int64; duracion_operativa_h: float64; n_dias_muestra: int64; n_dias_usado: int64; umbral_usado: float64; fallback_laboral: bool; franjas_anomalas_count: int64; pct_cobertura_dentro_horario: float64`
- Muestra (`head(3)`):

```csv
tipo_dia,ruta,granularidad_min,hora_inicio_op,hora_fin_op,hora_inicio_op_min,hora_fin_op_min,duracion_operativa_h,n_dias_muestra,n_dias_usado,umbral_usado,fallback_laboral,franjas_anomalas_count,pct_cobertura_dentro_horario
LABORAL,1,15,04:30,18:00,270,1080,13.75,501,501,0.1,False,1,1.0
SABADO,1,15,04:30,17:45,270,1065,13.5,106,106,0.1,False,2,1.0
DOMINGO,1,15,05:15,17:00,315,1020,12.0,105,105,0.1,False,10,1.0
```

### `reports/tables/qc/qc_resumen.csv`

- Descripción: Resumen de control de calidad ETL por regla/flag.
- Fuente: src/proyecto_grado/etl/qc.py:385-389
- Forma: `16 x 3`
- Fecha de última modificación: `2026-06-10 19:21:35`
- Columnas y tipos: `regla_flag: str; conteo: int64; porcentaje: float64`
- Muestra (`head(3)`):

```csv
regla_flag,conteo,porcentaje
qc_any_flag,16497,15.035545023696685
qc_soft_fail,16483,15.022785271600435
flag_hf_nula,15159,13.816077287641267
```

### `reports/tables/qc/qc_top_rutas.csv`

- Descripción: Conteos de flags QC para las rutas con más alertas; el identificador de ruta no está persistido en columnas (inferido - confirmar).
- Fuente: src/proyecto_grado/etl/qc.py:385-389
- Forma: `2 x 3`
- Fecha de última modificación: `2026-06-10 19:21:35`
- Columnas y tipos: `qc_any_flag: int64; qc_hard_fail: int64; qc_soft_fail: int64`
- Muestra (`head(3)`):

```csv
qc_any_flag,qc_hard_fail,qc_soft_fail
8321,8,8313
8176,6,8170
```

### `reports/tables/qc/qc_top_vehiculos.csv`

- Descripción: Conteos de flags QC para vehículos con más alertas; la placa no está persistida en columnas (inferido - confirmar).
- Fuente: src/proyecto_grado/etl/qc.py:385-389
- Forma: `15 x 3`
- Fecha de última modificación: `2026-06-10 19:21:35`
- Columnas y tipos: `qc_any_flag: int64; qc_hard_fail: int64; qc_soft_fail: int64`
- Muestra (`head(3)`):

```csv
qc_any_flag,qc_hard_fail,qc_soft_fail
155,3,152
570,1,569
380,1,379
```

### `reports/tables/time_series_summary.csv`

- Descripción: Resumen de series temporales por ruta y granularidad: franjas, gaps, pasajeros y validación.
- Fuente: scripts/build_time_series.py:116,141
- Forma: `6 x 9`
- Fecha de última modificación: `2026-05-03 14:10:20`
- Columnas y tipos: `granularidad_min: int64; ruta: int64; n_franjas: int64; n_gaps: int64; pct_gaps: float64; pasajeros_total: float64; valida: bool; errores: float64; advertencias: float64`
- Muestra (`head(3)`):

```csv
granularidad_min,ruta,n_franjas,n_gaps,pct_gaps,pasajeros_total,valida,errores,advertencias
15,1,71727,38888,54.2,2287320.0,True,,
15,3,71732,38775,54.1,2624512.0,True,,
30,1,35864,17377,48.5,2287320.0,True,,
```

## Artefactos textuales y JSON relacionados

| Ruta | Qué contiene | Bytes | Modificado |
| --- | --- | --- | --- |
| reports/tables/baseline/BASELINE_REPORT.txt | Reporte textual consolidado del baseline; advierte load_factor y formula demanda recuperable. | 7197 | 2026-06-29 11:51:32 |
| reports/tables/baseline/fleet_availability_report.txt | Reporte textual de disponibilidad de flota; desalineado con CSV actual de 30 días. | 1809 | 2026-06-22 21:05:47 |
| reports/tables/baseline/productivity_report.txt | Reporte textual de productividad por despacho y tendencia OLS. | 3223 | 2026-06-23 10:40:24 |
| reports/tables/eda/temporal_executive_summary.txt | Resumen ejecutivo textual del EDA temporal. | 5436 | 2026-05-07 18:35:44 |
| reports/tables/etl/model_ready_metadata_20260503_114750.json | Metadata JSON del freeze/corrida model-ready (inferido - confirmar). | 1118 | 2026-05-03 11:47:52 |
| reports/tables/etl/model_ready_metadata_20260610_191955.json | Metadata JSON del freeze/corrida model-ready (inferido - confirmar). | 1119 | 2026-06-10 19:19:57 |
| reports/tables/etl/model_ready_metadata_20260610_192142.json | Metadata JSON del freeze/corrida model-ready (inferido - confirmar). | 1119 | 2026-06-10 19:21:47 |
