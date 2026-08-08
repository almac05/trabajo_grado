# Inventario de figuras y tablas para diagnostico/EDA

Generado: 2026-06-29 14:29:57 (America/Bogota).

Alcance aplicado: inspeccion de `reports/`, `data/processed/`, `tables/` si existe, y busqueda en `scripts/`, `src/` y `notebooks/` de llamadas a matplotlib/seaborn/Altair/Streamlit. No se regeneraron artefactos existentes; solo se escribio este inventario.

Carpetas solicitadas que no existen en la raiz del repo: `figures, img, outputs, results, assets, tables`.
No se encontraron notebooks `.ipynb`; `notebooks/` contiene solo `.gitkeep`. No se encontraron `.xlsx` en el alcance.

**Conteo rapido**

| Tipo | Cantidad |
| --- | --- |
| Figuras PNG guardadas | 60 |
| Figuras solo en codigo / dashboard | 20 |
| Tablas CSV/Parquet/XLSX inspeccionadas | 78 |
| Reportes textuales adicionales en reports/tables | 4 |
| JSON adicionales en reports/tables | 3 |

Notas: las descripciones marcadas como `(contenido inferido - confirmar)` no pudieron verificarse directamente desde codigo o estructura de datos. Para figuras guardadas, dimensiones/dpi provienen del encabezado PNG; para figuras solo en codigo se reporta el tamano `figsize` o altura interactiva cuando aparece en el codigo.

## A) EDA temporal de la demanda

### Figuras

| Ruta / ubicacion | Fuente | Titulo y ejes | Que muestra | Ruta/granularidad | Formato/dim | Modificado |
| --- | --- | --- | --- | --- | --- | --- |
| reports/figures/eda/acf_pacf_1_g15min.png | scripts/run_eda_temporal.py:plot_acf_pacf | Autocorrelacion - Ruta 1 \| 15 min; x: Lag (franjas); y: Correlacion; subplots: ACF y PACF | ACF/PACF para evaluar estacionalidad y lookback de la serie de pasajeros. | Ruta 1; 15 min; lags hasta 48 franjas | PNG; 2373x984px; dpi 200x200 | 2026-05-07 18:35:41 |
| reports/figures/eda/acf_pacf_1_g30min.png | scripts/run_eda_temporal.py:plot_acf_pacf | Autocorrelacion - Ruta 1 \| 30 min; x: Lag (franjas); y: Correlacion; subplots: ACF y PACF | ACF/PACF para evaluar estacionalidad y lookback de la serie de pasajeros. | Ruta 1; 30 min; lags hasta 48 franjas | PNG; 2373x984px; dpi 200x200 | 2026-05-07 18:35:41 |
| reports/figures/eda/acf_pacf_1_g60min.png | scripts/run_eda_temporal.py:plot_acf_pacf | Autocorrelacion - Ruta 1 \| 60 min; x: Lag (franjas); y: Correlacion; subplots: ACF y PACF | ACF/PACF para evaluar estacionalidad y lookback de la serie de pasajeros. | Ruta 1; 60 min; lags hasta 48 franjas | PNG; 2373x984px; dpi 200x200 | 2026-05-07 18:35:42 |
| reports/figures/eda/acf_pacf_3_g15min.png | scripts/run_eda_temporal.py:plot_acf_pacf | Autocorrelacion - Ruta 3 \| 15 min; x: Lag (franjas); y: Correlacion; subplots: ACF y PACF | ACF/PACF para evaluar estacionalidad y lookback de la serie de pasajeros. | Ruta 3; 15 min; lags hasta 48 franjas | PNG; 2373x984px; dpi 200x200 | 2026-05-07 18:35:43 |
| reports/figures/eda/acf_pacf_3_g30min.png | scripts/run_eda_temporal.py:plot_acf_pacf | Autocorrelacion - Ruta 3 \| 30 min; x: Lag (franjas); y: Correlacion; subplots: ACF y PACF | ACF/PACF para evaluar estacionalidad y lookback de la serie de pasajeros. | Ruta 3; 30 min; lags hasta 48 franjas | PNG; 2373x984px; dpi 200x200 | 2026-05-07 18:35:43 |
| reports/figures/eda/acf_pacf_3_g60min.png | scripts/run_eda_temporal.py:plot_acf_pacf | Autocorrelacion - Ruta 3 \| 60 min; x: Lag (franjas); y: Correlacion; subplots: ACF y PACF | ACF/PACF para evaluar estacionalidad y lookback de la serie de pasajeros. | Ruta 3; 60 min; lags hasta 48 franjas | PNG; 2373x984px; dpi 200x200 | 2026-05-07 18:35:44 |
| reports/figures/eda/boxplot_tipo_dia_1_g15min.png | scripts/run_eda_temporal.py:plot_boxplot_tipo_dia | Distribucion de demanda por tipo de dia - Ruta 1 \| 15 min; x: Tipo de dia; y: Pasajeros por franja | Distribucion de pasajeros por franja para LABORAL/SABADO/DOMINGO/FESTIVO/FESTIVO_PUENTE. | Ruta 1; 15 min; tipo_dia | PNG; 1773x974px; dpi 200x200 | 2026-05-07 18:35:36 |
| reports/figures/eda/boxplot_tipo_dia_1_g30min.png | scripts/run_eda_temporal.py:plot_boxplot_tipo_dia | Distribucion de demanda por tipo de dia - Ruta 1 \| 30 min; x: Tipo de dia; y: Pasajeros por franja | Distribucion de pasajeros por franja para LABORAL/SABADO/DOMINGO/FESTIVO/FESTIVO_PUENTE. | Ruta 1; 30 min; tipo_dia | PNG; 1773x974px; dpi 200x200 | 2026-05-07 18:35:37 |
| reports/figures/eda/boxplot_tipo_dia_1_g60min.png | scripts/run_eda_temporal.py:plot_boxplot_tipo_dia | Distribucion de demanda por tipo de dia - Ruta 1 \| 60 min; x: Tipo de dia; y: Pasajeros por franja | Distribucion de pasajeros por franja para LABORAL/SABADO/DOMINGO/FESTIVO/FESTIVO_PUENTE. | Ruta 1; 60 min; tipo_dia | PNG; 1774x974px; dpi 200x200 | 2026-05-07 18:35:37 |
| reports/figures/eda/boxplot_tipo_dia_3_g15min.png | scripts/run_eda_temporal.py:plot_boxplot_tipo_dia | Distribucion de demanda por tipo de dia - Ruta 3 \| 15 min; x: Tipo de dia; y: Pasajeros por franja | Distribucion de pasajeros por franja para LABORAL/SABADO/DOMINGO/FESTIVO/FESTIVO_PUENTE. | Ruta 3; 15 min; tipo_dia | PNG; 1774x974px; dpi 200x200 | 2026-05-07 18:35:38 |
| reports/figures/eda/boxplot_tipo_dia_3_g30min.png | scripts/run_eda_temporal.py:plot_boxplot_tipo_dia | Distribucion de demanda por tipo de dia - Ruta 3 \| 30 min; x: Tipo de dia; y: Pasajeros por franja | Distribucion de pasajeros por franja para LABORAL/SABADO/DOMINGO/FESTIVO/FESTIVO_PUENTE. | Ruta 3; 30 min; tipo_dia | PNG; 1774x974px; dpi 200x200 | 2026-05-07 18:35:39 |
| reports/figures/eda/boxplot_tipo_dia_3_g60min.png | scripts/run_eda_temporal.py:plot_boxplot_tipo_dia | Distribucion de demanda por tipo de dia - Ruta 3 \| 60 min; x: Tipo de dia; y: Pasajeros por franja | Distribucion de pasajeros por franja para LABORAL/SABADO/DOMINGO/FESTIVO/FESTIVO_PUENTE. | Ruta 3; 60 min; tipo_dia | PNG; 1773x974px; dpi 200x200 | 2026-05-07 18:35:39 |
| reports/figures/eda/curva_intraday_1_domingo_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| DOMINGO \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 15 min; tipo_dia=DOMINGO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:26 |
| reports/figures/eda/curva_intraday_1_domingo_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| DOMINGO \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 30 min; tipo_dia=DOMINGO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_domingo_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| DOMINGO \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 60 min; tipo_dia=DOMINGO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:29 |
| reports/figures/eda/curva_intraday_1_festivo_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| FESTIVO \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 15 min; tipo_dia=FESTIVO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:26 |
| reports/figures/eda/curva_intraday_1_festivo_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| FESTIVO \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 30 min; tipo_dia=FESTIVO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:28 |
| reports/figures/eda/curva_intraday_1_festivo_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| FESTIVO \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 60 min; tipo_dia=FESTIVO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:29 |
| reports/figures/eda/curva_intraday_1_festivo_puente_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| FESTIVO_PUENTE \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 15 min; tipo_dia=FESTIVO_PUENTE | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_festivo_puente_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| FESTIVO_PUENTE \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 30 min; tipo_dia=FESTIVO_PUENTE | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:28 |
| reports/figures/eda/curva_intraday_1_festivo_puente_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| FESTIVO_PUENTE \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 60 min; tipo_dia=FESTIVO_PUENTE | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_1_laboral_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| LABORAL \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 15 min; tipo_dia=LABORAL | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_laboral_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| LABORAL \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 30 min; tipo_dia=LABORAL | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:28 |
| reports/figures/eda/curva_intraday_1_laboral_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| LABORAL \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 60 min; tipo_dia=LABORAL | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_1_sabado_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| SABADO \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 15 min; tipo_dia=SABADO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:27 |
| reports/figures/eda/curva_intraday_1_sabado_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| SABADO \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 30 min; tipo_dia=SABADO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:29 |
| reports/figures/eda/curva_intraday_1_sabado_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 1 \| SABADO \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 1; 60 min; tipo_dia=SABADO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_3_domingo_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| DOMINGO \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 15 min; tipo_dia=DOMINGO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:30 |
| reports/figures/eda/curva_intraday_3_domingo_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| DOMINGO \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 30 min; tipo_dia=DOMINGO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:32 |
| reports/figures/eda/curva_intraday_3_domingo_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| DOMINGO \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 60 min; tipo_dia=DOMINGO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:34 |
| reports/figures/eda/curva_intraday_3_festivo_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| FESTIVO \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 15 min; tipo_dia=FESTIVO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:31 |
| reports/figures/eda/curva_intraday_3_festivo_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| FESTIVO \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 30 min; tipo_dia=FESTIVO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:32 |
| reports/figures/eda/curva_intraday_3_festivo_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| FESTIVO \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 60 min; tipo_dia=FESTIVO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:34 |
| reports/figures/eda/curva_intraday_3_festivo_puente_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| FESTIVO_PUENTE \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 15 min; tipo_dia=FESTIVO_PUENTE | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:31 |
| reports/figures/eda/curva_intraday_3_festivo_puente_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| FESTIVO_PUENTE \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 30 min; tipo_dia=FESTIVO_PUENTE | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:33 |
| reports/figures/eda/curva_intraday_3_festivo_puente_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| FESTIVO_PUENTE \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 60 min; tipo_dia=FESTIVO_PUENTE | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:34 |
| reports/figures/eda/curva_intraday_3_laboral_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| LABORAL \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 15 min; tipo_dia=LABORAL | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:31 |
| reports/figures/eda/curva_intraday_3_laboral_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| LABORAL \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 30 min; tipo_dia=LABORAL | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:33 |
| reports/figures/eda/curva_intraday_3_laboral_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| LABORAL \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 60 min; tipo_dia=LABORAL | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:35 |
| reports/figures/eda/curva_intraday_3_sabado_g15min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| SABADO \| 15 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 15 min; tipo_dia=SABADO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:32 |
| reports/figures/eda/curva_intraday_3_sabado_g30min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| SABADO \| 30 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 30 min; tipo_dia=SABADO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:33 |
| reports/figures/eda/curva_intraday_3_sabado_g60min.png | scripts/run_eda_temporal.py:plot_curva_intraday | Ruta 3 \| SABADO \| 60 min; x: Hora del dia; y: Pasajeros promedio; banda: p25-p75 | Perfil intradia de demanda promedio, con banda intercuartil y marcadores de horas pico/valle. | Ruta 3; 60 min; tipo_dia=SABADO | PNG; 1973x973px; dpi 200x200 | 2026-05-07 18:35:35 |
| reports/figures/eda/demand_by_hour_weekday.png | src/proyecto_grado/analytics/plots.py:plot_hour_weekday_heatmap | Distribucion horaria de la demanda por dia; x: Hora de inicio; y: Dia de semana; color: Pasajeros | Demanda acumulada por dia de semana y hora, a partir del model-ready. | Ambas rutas; hora x dia_semana | PNG; 2185x1137px; dpi 220x220 | 2026-04-25 11:18:42 |
| reports/figures/eda/demand_by_route.png | src/proyecto_grado/analytics/plots.py:plot_demand_by_route | Demanda acumulada por ruta; x: Ruta; y: Pasajeros | Comparacion de pasajeros totales acumulados entre Ruta 1 y Ruta 3. | Rutas 1 y 3; acumulado historico | PNG; 1553x939px; dpi 220x220 | 2026-04-25 11:18:42 |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g15min.png | scripts/run_eda_temporal.py:plot_heatmap_hora_dia | Demanda promedio por dia y hora - Ruta 1 \| 15 min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor de demanda promedio por hora y dia de semana en franjas operativas. | Ruta 1; 15 min; semana x hora | PNG; 2185x973px; dpi 200x200 | 2026-05-07 18:35:35 |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g30min.png | scripts/run_eda_temporal.py:plot_heatmap_hora_dia | Demanda promedio por dia y hora - Ruta 1 \| 30 min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor de demanda promedio por hora y dia de semana en franjas operativas. | Ruta 1; 30 min; semana x hora | PNG; 2185x973px; dpi 200x200 | 2026-05-07 18:35:36 |
| reports/figures/eda/heatmap_demanda_hora_dia_1_g60min.png | scripts/run_eda_temporal.py:plot_heatmap_hora_dia | Demanda promedio por dia y hora - Ruta 1 \| 60 min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor de demanda promedio por hora y dia de semana en franjas operativas. | Ruta 1; 60 min; semana x hora | PNG; 2185x973px; dpi 200x200 | 2026-05-07 18:35:37 |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g15min.png | scripts/run_eda_temporal.py:plot_heatmap_hora_dia | Demanda promedio por dia y hora - Ruta 3 \| 15 min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor de demanda promedio por hora y dia de semana en franjas operativas. | Ruta 3; 15 min; semana x hora | PNG; 2185x973px; dpi 200x200 | 2026-05-07 18:35:38 |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g30min.png | scripts/run_eda_temporal.py:plot_heatmap_hora_dia | Demanda promedio por dia y hora - Ruta 3 \| 30 min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor de demanda promedio por hora y dia de semana en franjas operativas. | Ruta 3; 30 min; semana x hora | PNG; 2185x973px; dpi 200x200 | 2026-05-07 18:35:38 |
| reports/figures/eda/heatmap_demanda_hora_dia_3_g60min.png | scripts/run_eda_temporal.py:plot_heatmap_hora_dia | Demanda promedio por dia y hora - Ruta 3 \| 60 min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor de demanda promedio por hora y dia de semana en franjas operativas. | Ruta 3; 60 min; semana x hora | PNG; 2186x973px; dpi 200x200 | 2026-05-07 18:35:39 |
| reports/figures/eda/tendencia_mensual_1.png | scripts/run_eda_temporal.py:plot_tendencia_mensual | Tendencia mensual - Ruta 1; x: Periodo mensual; y: Pasajeros totales; linea: Tendencia OLS | Serie mensual de demanda total con tendencia lineal y meses atipicos resaltados. | Ruta 1; mes | PNG; 2173x973px; dpi 200x200 | 2026-05-07 18:35:40 |
| reports/figures/eda/tendencia_mensual_3.png | scripts/run_eda_temporal.py:plot_tendencia_mensual | Tendencia mensual - Ruta 3; x: Periodo mensual; y: Pasajeros totales; linea: Tendencia OLS | Serie mensual de demanda total con tendencia lineal y meses atipicos resaltados. | Ruta 3; mes | PNG; 2173x973px; dpi 200x200 | 2026-05-07 18:35:40 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_demand_by_route_inline | Streamlit + seaborn/matplotlib | Demanda por ruta; x: Ruta; y: Pasajeros o Pasajeros/despacho | Comparacion interactiva por ruta entre pasajeros totales y pasajeros promedio por despacho. | Rutas 1 y 3; acumulado historico | Streamlit st.pyplot; figsize 8x4.5 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_hour_weekday_heatmap_inline | Streamlit + seaborn/matplotlib | Distribucion horaria de la demanda por dia; x: Hora de inicio; y: Dia de semana; color: Pasajeros | Mapa de calor interactivo del dashboard para demanda acumulada por hora y dia. | Ambas rutas; hora x dia_semana | Streamlit st.pyplot; figsize 11x5.2 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_time_series_trend_inline | Streamlit + Altair | Evolucion temporal con atipicos contextuales; x: Fecha; y: metrica seleccionada | Serie temporal filtrable con media movil y puntos de atipicos contextuales. | Ruta/granularidad/rango seleccionados | Altair interactivo; height 520 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_time_series_heatmap_inline | Streamlit + seaborn/matplotlib | Patron promedio por dia y hora; x: Hora; y: Dia de semana; color: metrica seleccionada | Mapa de calor para la metrica de serie temporal seleccionada. | Ruta/granularidad/rango seleccionados | Streamlit st.pyplot; figsize 11x5.2 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_time_series_distribution_inline | Streamlit + seaborn/matplotlib | Distribucion de la demanda por franja; x: Franja horaria u hora; y: metrica seleccionada | Boxplot de la metrica seleccionada por franja horaria/hora. | Ruta/granularidad/rango seleccionados | Streamlit st.pyplot; figsize 10.5x4.8 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_outlier_heatmap_inline | Streamlit + seaborn/matplotlib | Concentracion de atipicos por dia y hora; x: Hora; y: Dia de semana; color: Atipicos | Conteo de atipicos contextuales por dia de semana y hora. | Ruta/granularidad/filtros seleccionados | Streamlit st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_eda_intraday_inline | Streamlit + matplotlib | Perfil intradia - Ruta {route} \| {gran} min \| {selected_type}; x: Hora del dia; y: Pasajeros promedio | Perfil intradia del artefacto EDA, con opcion de superponer tipos de dia o mostrar banda p25-p75. | Ruta/granularidad/tipo_dia seleccionados | Streamlit st.pyplot; figsize 11x5.2 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_eda_weekly_heatmap_inline | Streamlit + seaborn/matplotlib | Demanda promedio por dia y hora - Ruta {route} \| {gran} min; x: Hora; y: Dia de semana; color: Pasajeros promedio | Mapa de calor EDA filtrado a franjas operativas para una ruta/granularidad. | Ruta/granularidad seleccionadas; semana x hora | Streamlit st.pyplot; figsize 11x5 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_eda_monthly_trend_inline | Streamlit + matplotlib | Tendencia mensual - Ruta {route}; x: periodo; y: Pasajeros | Barras mensuales de demanda con tendencia visual y meses atipicos en color acento. | Ruta seleccionada; mes | Streamlit st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_eda_autocorrelation_inline | Streamlit + matplotlib | ACF/PACF - Ruta {route} \| {gran} min; x: Lag (franjas); y: Correlacion | ACF y PACF del artefacto EDA, resaltando lags significativos y relevantes. | Ruta/granularidad seleccionadas; lags | Streamlit st.pyplot; figsize 12x4.8 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_eda_outliers_inline | Streamlit + matplotlib | Atipicos sobre serie operativa - Ruta {route} \| {gran} min; x: Fecha; y: Pasajeros | Nube temporal de pasajeros en franjas operativas con atipicos resaltados. | Ruta/granularidad seleccionadas; fecha | Streamlit st.pyplot; figsize 12x4.8 | 2026-05-13 16:39:54 |

### Tablas

#### `data/processed/eda/atipicos_1_g15min.parquet`

- Descripcion: Franjas operativas atipicas de pasajeros detectadas por IQR y/o z-score por tipo de dia.
- Forma: `447 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 05:15:00,2024-04-16,5,LABORAL,193.0,True,True,3.3730902868662835,ambos,-30.5,165.5,1.3611863942263773
2024-04-16 06:00:00,2024-04-16,6,LABORAL,229.0,True,True,4.412851945512669,ambos,-30.5,165.5,1.3611863942263773
2024-04-16 15:45:00,2024-04-16,15,LABORAL,166.0,True,False,2.5932690428814946,IQR,-30.5,165.5,1.3611863942263773
```

#### `data/processed/eda/atipicos_1_g30min.parquet`

- Descripcion: Franjas operativas atipicas de pasajeros detectadas por IQR y/o z-score por tipo de dia.
- Forma: `121 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 06:00:00,2024-04-16,6,LABORAL,315.0,True,True,3.109452696887395,ambos,-51.0,293.0,0.6545139827987234
2024-04-18 05:30:00,2024-04-18,5,LABORAL,352.0,True,True,3.780123371921941,ambos,-51.0,293.0,0.6545139827987234
2024-04-21 16:30:00,2024-04-21,16,DOMINGO,96.0,False,True,3.5337838880850665,zscore,-51.0,293.0,0.6545139827987234
```

#### `data/processed/eda/atipicos_1_g60min.parquet`

- Descripcion: Franjas operativas atipicas de pasajeros detectadas por IQR y/o z-score por tipo de dia.
- Forma: `27 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-18 05:00:00,2024-04-18,5,LABORAL,621.0,True,True,3.515931492375089,ambos,-129.0,575.0,0.2696225284601558
2024-04-23 05:00:00,2024-04-23,5,LABORAL,583.0,True,True,3.133436443919811,ambos,-129.0,575.0,0.2696225284601558
2024-05-12 08:00:00,2024-05-12,8,DOMINGO,149.0,False,True,3.1651734197074894,zscore,-129.0,575.0,0.2696225284601558
```

#### `data/processed/eda/atipicos_3_g15min.parquet`

- Descripcion: Franjas operativas atipicas de pasajeros detectadas por IQR y/o z-score por tipo de dia.
- Forma: `771 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 05:45:00,2024-04-16,5,LABORAL,195.0,True,False,2.403213563430973,IQR,-42.5,193.5,2.339411961040143
2024-04-16 06:00:00,2024-04-16,6,LABORAL,219.0,True,False,2.943209219353117,IQR,-42.5,193.5,2.339411961040143
2024-04-16 06:15:00,2024-04-16,6,LABORAL,197.0,True,False,2.448213201424485,IQR,-42.5,193.5,2.339411961040143
```

#### `data/processed/eda/atipicos_3_g30min.parquet`

- Descripcion: Franjas operativas atipicas de pasajeros detectadas por IQR y/o z-score por tipo de dia.
- Forma: `341 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 05:30:00,2024-04-16,5,LABORAL,362.0,True,False,2.5418418751459644,IQR,-98.0,358.0,1.8143123171056132
2024-04-16 06:00:00,2024-04-16,6,LABORAL,416.0,True,True,3.233583665955704,ambos,-98.0,358.0,1.8143123171056132
2024-04-17 05:30:00,2024-04-17,5,LABORAL,407.0,True,True,3.118293367487414,ambos,-98.0,358.0,1.8143123171056132
```

#### `data/processed/eda/atipicos_3_g60min.parquet`

- Descripcion: Franjas operativas atipicas de pasajeros detectadas por IQR y/o z-score por tipo de dia.
- Forma: `124 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `timestamp: datetime64[us]; fecha: str; hora_del_dia: int64; tipo_dia: str; pasajeros_total: float64; es_atipico_iqr: bool; es_atipico_zscore: bool; zscore_tipo_dia: float64; metodo_deteccion: str; limite_inf_iqr: float64; limite_sup_iqr: float64; pct_atipicos: float64`
- Muestra (`head(3)`):

```csv
timestamp,fecha,hora_del_dia,tipo_dia,pasajeros_total,es_atipico_iqr,es_atipico_zscore,zscore_tipo_dia,metodo_deteccion,limite_inf_iqr,limite_sup_iqr,pct_atipicos
2024-04-16 06:00:00,2024-04-16,6,LABORAL,757.0,True,True,3.102023615176226,ambos,-182.0,674.0,1.244355243351731
2024-04-17 05:00:00,2024-04-17,5,LABORAL,709.0,True,False,2.7629220810346795,IQR,-182.0,674.0,1.244355243351731
2024-04-17 06:00:00,2024-04-17,6,LABORAL,740.0,True,False,2.9819251551677617,IQR,-182.0,674.0,1.244355243351731
```

#### `data/processed/eda/autocorr_1_g15min.parquet`

- Descripcion: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Forma: `49 x 13`
- Fecha de ultima modificacion: `2026-05-07 18:35:16`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-14.17501571665056,1.973028235955265e-26,True,1,15
1,0.20534829989383094,0.2053482998938309,-0.010815662560168499,0.010815662560168499,True,True,False,-14.17501571665056,1.973028235955265e-26,True,1,15
2,0.2962102386664353,0.26522635943606726,-0.011262506046542664,0.011262506046542664,True,True,False,-14.17501571665056,1.973028235955265e-26,True,1,15
```

#### `data/processed/eda/autocorr_1_g30min.parquet`

- Descripcion: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Forma: `49 x 13`
- Fecha de ultima modificacion: `2026-05-07 18:35:18`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-18.875286567668546,0.0,True,1,30
1,0.5023068295883818,0.5023068295883816,-0.014415007424512238,0.014415007424512294,True,True,True,-18.875286567668546,0.0,True,1,30
2,0.4777079302953831,0.3014570579970273,-0.017681899037881754,0.017681899037881754,True,True,True,-18.875286567668546,0.0,True,1,30
```

#### `data/processed/eda/autocorr_1_g60min.parquet`

- Descripcion: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Forma: `49 x 13`
- Fecha de ultima modificacion: `2026-05-07 18:35:19`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-15.94627957524435,7.443246455064352e-29,True,1,60
1,0.6485654045609283,0.6485654045609283,-0.019585934486457957,0.019585934486457957,True,True,True,-15.94627957524435,7.443246455064352e-29,True,1,60
2,0.3858760096143572,-0.05999879077265652,-0.026576851370178678,0.026576851370178678,True,True,True,-15.94627957524435,7.443246455064352e-29,True,1,60
```

#### `data/processed/eda/autocorr_3_g15min.parquet`

- Descripcion: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Forma: `49 x 13`
- Fecha de ultima modificacion: `2026-05-07 18:35:23`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-14.126387294892552,2.3754431556336704e-26,True,3,15
1,0.3794979168029455,0.37949791680294553,-0.010796282874383056,0.010796282874383056,True,True,True,-14.126387294892552,2.3754431556336704e-26,True,3,15
2,0.4138003143638548,0.3151723474460383,-0.012252888494627578,0.012252888494627578,True,True,True,-14.126387294892552,2.3754431556336704e-26,True,3,15
```

#### `data/processed/eda/autocorr_3_g30min.parquet`

- Descripcion: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Forma: `49 x 13`
- Fecha de ultima modificacion: `2026-05-07 18:35:24`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-21.771769223092672,0.0,True,3,30
1,0.6261132018639527,0.6261132018639528,-0.014296407741527406,0.014296407741527406,True,True,True,-21.771769223092672,0.0,True,3,30
2,0.4875072641952538,0.15705971896302243,-0.019095396033233403,0.019095396033233403,True,True,True,-21.771769223092672,0.0,True,3,30
```

#### `data/processed/eda/autocorr_3_g60min.parquet`

- Descripcion: ACF/PACF por ruta y granularidad, significancia de lags y prueba ADF de estacionariedad.
- Forma: `49 x 13`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `lag: int64; acf_value: float64; pacf_value: float64; acf_ci_lower: float64; acf_ci_upper: float64; es_significativo_acf: bool; es_significativo_pacf: bool; lags_relevantes_acf: bool; adf_statistic: float64; adf_pvalue: float64; adf_is_stationary: bool; ruta: int64; granularidad_min: int64`
- Muestra (`head(3)`):

```csv
lag,acf_value,pacf_value,acf_ci_lower,acf_ci_upper,es_significativo_acf,es_significativo_pacf,lags_relevantes_acf,adf_statistic,adf_pvalue,adf_is_stationary,ruta,granularidad_min
0,1.0,1.0,0.0,0.0,True,True,True,-16.15433919123102,4.5347226513403795e-29,True,3,60
1,0.61981324202494,0.6198132420249399,-0.019634029514386864,0.019634029514386864,True,True,True,-16.15433919123102,4.5347226513403795e-29,True,3,60
2,0.2547623688933479,-0.21013227910224286,-0.02610910263531152,0.02610910263531152,True,True,False,-16.15433919123102,4.5347226513403795e-29,True,3,60
```

#### `data/processed/eda/correlacion_features.parquet`

- Descripcion: Ranking de correlaciones Spearman entre PASAJEROS y features numericas/codificadas del model-ready.
- Forma: `13 x 4`
- Fecha de ultima modificacion: `2026-05-07 18:35:25`
- Columnas y tipos: `feature: str; correlacion_spearman: float64; abs_correlacion: float64; rank: int64`
- Muestra (`head(3)`):

```csv
feature,correlacion_spearman,abs_correlacion,rank
DURACION_MIN_FINAL,0.3351661329697794,0.3351661329697794,1
PLACA,0.2679366847239228,0.2679366847239228,2
DISTANCIA,0.24304526041464544,0.24304526041464544,3
```

#### `data/processed/eda/perfil_intraday_1_g15min.parquet`

- Descripcion: Perfil intradia por ruta/granularidad/tipo_dia: media, mediana y cuantiles de pasajeros por hora, con horas pico/valle.
- Forma: `72 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,12.5,12.5,12.25,12.75,12.95,False,True,1.3982180248568763,"8,9,12,16","4,5,7,17"
DOMINGO,5,29.48611111111111,29.0,23.0,35.0,41.45,False,True,1.3982180248568763,"8,9,12,16","4,5,7,17"
DOMINGO,6,30.236220472440944,29.0,26.0,35.0,45.0,False,False,1.3982180248568763,"8,9,12,16","4,5,7,17"
```

#### `data/processed/eda/perfil_intraday_1_g30min.parquet`

- Descripcion: Perfil intradia por ruta/granularidad/tipo_dia: media, mediana y cuantiles de pasajeros por hora, con horas pico/valle.
- Forma: `72 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,12.5,12.5,12.25,12.75,12.95,False,True,1.5040803420533355,"8,9,11,12","4,5,13,17"
DOMINGO,5,33.698412698412696,30.0,24.0,38.0,67.8,False,True,1.5040803420533355,"8,9,11,12","4,5,13,17"
DOMINGO,6,39.183673469387756,35.0,27.25,50.0,67.29999999999998,False,False,1.5040803420533355,"8,9,11,12","4,5,13,17"
```

#### `data/processed/eda/perfil_intraday_1_g60min.parquet`

- Descripcion: Perfil intradia por ruta/granularidad/tipo_dia: media, mediana y cuantiles de pasajeros por hora, con horas pico/valle.
- Forma: `72 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,12.5,12.5,12.25,12.75,12.95,False,True,2.039453222651428,"7,8,9,10","4,5,16,17"
DOMINGO,5,46.15217391304348,41.5,32.25,61.5,76.75,False,True,2.039453222651428,"7,8,9,10","4,5,16,17"
DOMINGO,6,64.0,62.0,34.5,90.25,117.05,False,False,2.039453222651428,"7,8,9,10","4,5,16,17"
```

#### `data/processed/eda/perfil_intraday_3_g15min.parquet`

- Descripcion: Perfil intradia por ruta/granularidad/tipo_dia: media, mediana y cuantiles de pasajeros por hora, con horas pico/valle.
- Forma: `72 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:11`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,26.166666666666668,26.5,20.0,31.25,38.05,False,True,1.1775643255524622,"8,9,10,16","4,5,7,13"
DOMINGO,5,29.77391304347826,27.0,23.0,33.0,57.0,False,True,1.1775643255524622,"8,9,10,16","4,5,7,13"
DOMINGO,6,30.352459016393443,29.0,25.0,34.0,50.94999999999999,False,False,1.1775643255524622,"8,9,10,16","4,5,7,13"
```

#### `data/processed/eda/perfil_intraday_3_g30min.parquet`

- Descripcion: Perfil intradia por ruta/granularidad/tipo_dia: media, mediana y cuantiles de pasajeros por hora, con horas pico/valle.
- Forma: `72 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,32.04081632653061,30.0,22.0,38.0,57.599999999999994,False,True,1.2554425167815582,"8,9,10,11","4,13,14,17"
DOMINGO,5,38.47191011235955,33.0,25.0,50.0,65.0,False,False,1.2554425167815582,"8,9,10,11","4,13,14,17"
DOMINGO,6,38.175257731958766,34.0,27.0,49.0,63.599999999999966,False,False,1.2554425167815582,"8,9,10,11","4,13,14,17"
```

#### `data/processed/eda/perfil_intraday_3_g60min.parquet`

- Descripcion: Perfil intradia por ruta/granularidad/tipo_dia: media, mediana y cuantiles de pasajeros por hora, con horas pico/valle.
- Forma: `72 x 12`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `tipo_dia: str; hora_del_dia: int64; media: float64; mediana: float64; p25: float64; p75: float64; p95: float64; es_pico: bool; es_valle: bool; ratio_pico_valle: float64; horas_pico: str; horas_valle: str`
- Muestra (`head(3)`):

```csv
tipo_dia,hora_del_dia,media,mediana,p25,p75,p95,es_pico,es_valle,ratio_pico_valle,horas_pico,horas_valle
DOMINGO,4,36.51162790697674,34.0,28.0,51.0,58.9,False,True,1.7223785356471522,"5,6,8,10","4,13,16,17"
DOMINGO,5,68.48,66.5,55.25,85.25,111.24999999999996,True,False,1.7223785356471522,"5,6,8,10","4,13,16,17"
DOMINGO,6,66.125,67.5,49.25,86.0,109.25,True,False,1.7223785356471522,"5,6,8,10","4,13,16,17"
```

#### `data/processed/eda/perfil_mensual_1.parquet`

- Descripcion: Demanda mensual y semanal por ruta, con pendiente/intercepto OLS y meses atipicos.
- Forma: `133 x 6`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `periodo: str; demanda_total: float64; tipo_periodo: str; es_atipico: bool; tendencia_slope: float64; tendencia_intercept: float64`
- Muestra (`head(3)`):

```csv
periodo,demanda_total,tipo_periodo,es_atipico,tendencia_slope,tendencia_intercept
2024-04,60975.0,mes,False,-1.9902526077837601,3801.2737875099074
2024-05,118783.0,mes,False,-1.9902526077837601,3801.2737875099074
2024-06,103512.0,mes,False,-1.9902526077837601,3801.2737875099074
```

#### `data/processed/eda/perfil_mensual_3.parquet`

- Descripcion: Demanda mensual y semanal por ruta, con pendiente/intercepto OLS y meses atipicos.
- Forma: `133 x 6`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `periodo: str; demanda_total: float64; tipo_periodo: str; es_atipico: bool; tendencia_slope: float64; tendencia_intercept: float64`
- Muestra (`head(3)`):

```csv
periodo,demanda_total,tipo_periodo,es_atipico,tendencia_slope,tendencia_intercept
2024-04,67580.0,mes,False,-1.73687526212746,4157.428792757541
2024-05,128905.0,mes,False,-1.73687526212746,4157.428792757541
2024-06,111829.0,mes,False,-1.73687526212746,4157.428792757541
```

#### `data/processed/eda/perfil_semanal_1_g15min.parquet`

- Descripcion: Perfil semanal de demanda por dia de semana, con demanda total/promedio, variabilidad y marcas de maximo/minimo.
- Forma: `7 x 7`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,345166.0,72.08980785296575,0.5108319281331668,Lunes,False,False
1,428368.0,78.87460872767446,0.4420362152469957,Martes,True,False
2,389507.0,74.10711567732116,0.4609696365610281,Miercoles,False,False
```

#### `data/processed/eda/perfil_semanal_1_g30min.parquet`

- Descripcion: Perfil semanal de demanda por dia de semana, con demanda total/promedio, variabilidad y marcas de maximo/minimo.
- Forma: `7 x 7`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,345166.0,129.13056490834268,0.4896075386658852,Lunes,False,False
1,428368.0,148.7905522750955,0.3733647652750276,Martes,True,False
2,389507.0,138.5652792600498,0.4049842296939777,Miercoles,False,False
```

#### `data/processed/eda/perfil_semanal_1_g60min.parquet`

- Descripcion: Perfil semanal de demanda por dia de semana, con demanda total/promedio, variabilidad y marcas de maximo/minimo.
- Forma: `7 x 7`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,345166.0,240.19902574808629,0.49398977664300275,Lunes,False,False
1,428368.0,281.26592252133946,0.3664258260470872,Martes,True,False
2,389507.0,261.2387659289068,0.38868653649705415,Miercoles,False,False
```

#### `data/processed/eda/perfil_semanal_3_g15min.parquet`

- Descripcion: Perfil semanal de demanda por dia de semana, con demanda total/promedio, variabilidad y marcas de maximo/minimo.
- Forma: `7 x 7`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,403349.0,83.33657024793388,0.5498174469187028,Lunes,False,False
1,494851.0,90.73175650898423,0.5004783029389859,Martes,True,False
2,449067.0,85.2928774928775,0.5196555980570245,Miercoles,False,False
```

#### `data/processed/eda/perfil_semanal_3_g30min.parquet`

- Descripcion: Perfil semanal de demanda por dia de semana, con demanda total/promedio, variabilidad y marcas de maximo/minimo.
- Forma: `7 x 7`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,403349.0,147.96368305209097,0.5713464260290211,Lunes,False,False
1,494851.0,169.00648907103826,0.47694548394131697,Martes,True,False
2,449067.0,156.90670859538784,0.49951468980180175,Miercoles,False,False
```

#### `data/processed/eda/perfil_semanal_3_g60min.parquet`

- Descripcion: Perfil semanal de demanda por dia de semana, con demanda total/promedio, variabilidad y marcas de maximo/minimo.
- Forma: `7 x 7`
- Fecha de ultima modificacion: `2026-05-07 18:35:12`
- Columnas y tipos: `dia_semana: int64; demanda_total: float64; demanda_promedio: float64; variabilidad: float64; nombre_dia: str; es_max: bool; es_min: bool`
- Muestra (`head(3)`):

```csv
dia_semana,demanda_total,demanda_promedio,variabilidad,nombre_dia,es_max,es_min
0,403349.0,282.6552207428171,0.5673528462150763,Lunes,False,False
1,494851.0,328.5863213811421,0.44306640858941193,Martes,True,False
2,449067.0,302.4020202020202,0.4792637853814676,Miercoles,False,False
```

#### `data/processed/time_series/ts_ruta1_g15min.parquet`

- Descripcion: Serie temporal agregada por ruta y granularidad con pasajeros, despachos, gaps y contexto calendario/operativo.
- Forma: `71727 x 19`
- Fecha de ultima modificacion: `2026-05-03 18:02:18`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:30:00,120.0,2,60.0,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,1,True,operativo
2024-04-16 04:45:00,109.0,2,54.5,59.45,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,1,True,operativo
2024-04-16 05:00:00,87.0,2,43.5,43.95,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,15,1,True,operativo
```

#### `data/processed/time_series/ts_ruta1_g30min.parquet`

- Descripcion: Serie temporal agregada por ruta y granularidad con pasajeros, despachos, gaps y contexto calendario/operativo.
- Forma: `35864 x 19`
- Fecha de ultima modificacion: `2026-05-03 18:02:21`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:30:00,229.0,4,57.25,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,30,1,True,operativo
2024-04-16 05:00:00,280.0,5,56.0,71.8,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,30,1,True,operativo
2024-04-16 05:30:00,261.0,5,52.2,58.0,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,30,1,True,operativo
```

#### `data/processed/time_series/ts_ruta1_g60min.parquet`

- Descripcion: Serie temporal agregada por ruta y granularidad con pasajeros, despachos, gaps y contexto calendario/operativo.
- Forma: `17933 x 19`
- Fecha de ultima modificacion: `2026-05-03 18:02:23`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:00:00,229.0,4,57.25,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,60,1,True,operativo
2024-04-16 05:00:00,541.0,10,54.1,69.04999999999998,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,60,1,True,operativo
2024-04-16 06:00:00,554.0,11,50.36363636363637,68.0,False,6,1,False,4,16,2,MANANA,False,LABORAL,60,1,True,operativo
```

#### `data/processed/time_series/ts_ruta3_g15min.parquet`

- Descripcion: Serie temporal agregada por ruta y granularidad con pasajeros, despachos, gaps y contexto calendario/operativo.
- Forma: `71732 x 19`
- Fecha de ultima modificacion: `2026-05-03 18:02:20`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:15:00,49.0,1,49.0,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,3,True,operativo
2024-04-16 04:30:00,90.0,2,45.0,48.6,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,3,True,operativo
2024-04-16 04:45:00,42.0,1,42.0,42.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,15,3,True,operativo
```

#### `data/processed/time_series/ts_ruta3_g30min.parquet`

- Descripcion: Serie temporal agregada por ruta y granularidad con pasajeros, despachos, gaps y contexto calendario/operativo.
- Forma: `35867 x 19`
- Fecha de ultima modificacion: `2026-05-03 18:02:23`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:00:00,49.0,1,49.0,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,30,3,True,operativo
2024-04-16 04:30:00,132.0,3,44.0,48.3,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,30,3,True,operativo
2024-04-16 05:00:00,294.0,5,58.8,75.8,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,30,3,True,operativo
```

#### `data/processed/time_series/ts_ruta3_g60min.parquet`

- Descripcion: Serie temporal agregada por ruta y granularidad con pasajeros, despachos, gaps y contexto calendario/operativo.
- Forma: `17934 x 19`
- Fecha de ultima modificacion: `2026-05-03 18:02:24`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; granularidad_min: int64; FK_RUTA: int64; dentro_horario_operativo: bool; gap_tipo: str`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,granularidad_min,FK_RUTA,dentro_horario_operativo,gap_tipo
2024-04-16 04:00:00,181.0,4,45.25,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,60,3,True,operativo
2024-04-16 05:00:00,656.0,10,65.6,86.55,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,60,3,True,operativo
2024-04-16 06:00:00,757.0,11,68.81818181818181,91.5,False,6,1,False,4,16,2,MANANA,False,LABORAL,60,3,True,operativo
```

#### `data/processed/time_series/ts_ruta_1.parquet`

- Descripcion: (contenido inferido - confirmar) Serie temporal legacy por ruta; no sigue el patron actual con granularidad en el nombre.
- Forma: `17933 x 16`
- Fecha de ultima modificacion: `2026-05-03 12:22:57`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; FK_RUTA: int64`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,FK_RUTA
2024-04-16 04:00:00,229.0,4,57.25,60.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,1
2024-04-16 05:00:00,541.0,10,54.1,69.04999999999998,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,1
2024-04-16 06:00:00,554.0,11,50.36363636363637,68.0,False,6,1,False,4,16,2,MANANA,False,LABORAL,1
```

#### `data/processed/time_series/ts_ruta_3.parquet`

- Descripcion: (contenido inferido - confirmar) Serie temporal legacy por ruta; no sigue el patron actual con granularidad en el nombre.
- Forma: `17934 x 16`
- Fecha de ultima modificacion: `2026-05-03 12:22:57`
- Columnas y tipos: `timestamp: datetime64[us]; pasajeros_total: float64; despachos_count: int64; pasajeros_promedio: float64; ocupacion_p95: float64; is_gap: bool; hora_del_dia: int64; dia_semana: int64; es_fin_semana: bool; mes: int64; semana_anio: int64; trimestre: int64; franja_horaria: str; es_festivo: bool; tipo_dia: str; FK_RUTA: int64`
- Muestra (`head(3)`):

```csv
timestamp,pasajeros_total,despachos_count,pasajeros_promedio,ocupacion_p95,is_gap,hora_del_dia,dia_semana,es_fin_semana,mes,semana_anio,trimestre,franja_horaria,es_festivo,tipo_dia,FK_RUTA
2024-04-16 04:00:00,181.0,4,45.25,49.0,False,4,1,False,4,16,2,MADRUGADA,False,LABORAL,3
2024-04-16 05:00:00,656.0,10,65.6,86.55,False,5,1,False,4,16,2,MADRUGADA,False,LABORAL,3
2024-04-16 06:00:00,757.0,11,68.81818181818181,91.5,False,6,1,False,4,16,2,MANANA,False,LABORAL,3
```

#### `reports/tables/eda/demand_by_hour_weekday.csv`

- Descripcion: Tabla agregada de demanda para figuras post-ETL: por hora/dia de semana o por ruta.
- Forma: `107 x 4`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `dia_semana: int64; hora: int64; despachos: int64; pasajeros_total: int64`
- Muestra (`head(3)`):

```csv
dia_semana,hora,despachos,pasajeros_total
0,4,704,30071
0,5,1497,73723
0,6,1325,75663
```

#### `reports/tables/eda/demand_by_route.csv`

- Descripcion: Tabla agregada de demanda para figuras post-ETL: por hora/dia de semana o por ruta.
- Forma: `2 x 4`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `FK_RUTA: int64; despachos: int64; pasajeros_total: int64; pasajeros_promedio: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,despachos,pasajeros_total,pasajeros_promedio
1,51041,2270402,44.48192629454752
3,53609,2604692,48.5868417616445
```

## B) Diagnostico de la oferta / contraccion de flota

### Figuras

No encontre figuras guardadas ni figuras solo en codigo para este tema.

### Tablas

#### `reports/tables/baseline/diagnostico_flota_comparacion.csv`

- Descripcion: Comparacion inicio vs fin del periodo para vehiculos activos, despachos, pasajeros, productividad e intensidad.
- Forma: `5 x 5`
- Fecha de ultima modificacion: `2026-06-23 10:49:46`
- Columnas y tipos: `indicador: str; primer_mes: float64; ultimo_mes: float64; variacion_absoluta: float64; variacion_pct: float64`
- Muestra (`head(3)`):

```csv
indicador,primer_mes,ultimo_mes,variacion_absoluta,variacion_pct
Vehículos activos,63.0,42.0,-21.0,-33.3
Despachos totales,5266.0,3179.0,-2087.0,-39.6
Pasajeros totales,247688.0,145868.0,-101820.0,-41.1
```

#### `reports/tables/baseline/diagnostico_flota_mensual.csv`

- Descripcion: Serie mensual de vehiculos activos, despachos, pasajeros, productividad por despacho e intensidad de uso.
- Forma: `27 x 6`
- Fecha de ultima modificacion: `2026-06-23 10:49:46`
- Columnas y tipos: `mes: str; vehiculos_activos: int64; despachos_total: int64; pasajeros_total: int64; productividad_por_despacho: float64; despachos_por_vehiculo: float64`
- Muestra (`head(3)`):

```csv
mes,vehiculos_activos,despachos_total,pasajeros_total,productividad_por_despacho,despachos_por_vehiculo
2024-04-01,63,2514,128555,51.14,39.9
2024-05-01,63,5266,247688,47.04,83.59
2024-06-01,63,4783,215341,45.02,75.92
```

#### `reports/tables/baseline/diagnostico_vehiculos_estado.csv`

- Descripcion: Ultimo mes activo por PLACA y meses desde la ultima operacion, para identificar vehiculos retirados/inactivos.
- Forma: `67 x 3`
- Fecha de ultima modificacion: `2026-06-23 10:49:46`
- Columnas y tipos: `PLACA: str; ultimo_mes_activo: str; meses_desde_ultimo: float64`
- Muestra (`head(3)`):

```csv
PLACA,ultimo_mes_activo,meses_desde_ultimo
SRE698,2026-06-01,0.0
VBV580,2026-05-01,1.0
VBW125,2026-06-01,0.0
```

## C) Indicadores / KPIs de linea base

### Figuras

| Ruta / ubicacion | Fuente | Titulo y ejes | Que muestra | Ruta/granularidad | Formato/dim | Modificado |
| --- | --- | --- | --- | --- | --- | --- |
| reports/figures/operational_heatmap_1_15min.png | src/proyecto_grado/features/operational_hours.py:OperationalHoursEstimator.plot_heatmap | Cobertura operativa - ruta 1 \| 15 min; x: Tipo de dia; y: Franja horaria (HH:MM); color: pct_activa | Mapa de calor de la frecuencia historica de franjas con despacho para estimar horario operativo. | Ruta 1; 15 min; tipo_dia x franja | PNG; 1394x2267px; dpi 120x120 | 2026-05-03 18:02:13 |
| reports/figures/operational_heatmap_1_30min.png | src/proyecto_grado/features/operational_hours.py:OperationalHoursEstimator.plot_heatmap | Cobertura operativa - ruta 1 \| 30 min; x: Tipo de dia; y: Franja horaria (HH:MM); color: pct_activa | Mapa de calor de la frecuencia historica de franjas con despacho para estimar horario operativo. | Ruta 1; 30 min; tipo_dia x franja | PNG; 1334x1067px; dpi 120x120 | 2026-05-03 18:02:14 |
| reports/figures/operational_heatmap_1_60min.png | src/proyecto_grado/features/operational_hours.py:OperationalHoursEstimator.plot_heatmap | Cobertura operativa - ruta 1 \| 60 min; x: Tipo de dia; y: Franja horaria (HH:MM); color: pct_activa | Mapa de calor de la frecuencia historica de franjas con despacho para estimar horario operativo. | Ruta 1; 60 min; tipo_dia x franja | PNG; 1328x947px; dpi 120x120 | 2026-05-03 18:02:14 |
| reports/figures/operational_heatmap_3_15min.png | src/proyecto_grado/features/operational_hours.py:OperationalHoursEstimator.plot_heatmap | Cobertura operativa - ruta 3 \| 15 min; x: Tipo de dia; y: Franja horaria (HH:MM); color: pct_activa | Mapa de calor de la frecuencia historica de franjas con despacho para estimar horario operativo. | Ruta 3; 15 min; tipo_dia x franja | PNG; 1394x2267px; dpi 120x120 | 2026-05-03 18:02:15 |
| reports/figures/operational_heatmap_3_30min.png | src/proyecto_grado/features/operational_hours.py:OperationalHoursEstimator.plot_heatmap | Cobertura operativa - ruta 3 \| 30 min; x: Tipo de dia; y: Franja horaria (HH:MM); color: pct_activa | Mapa de calor de la frecuencia historica de franjas con despacho para estimar horario operativo. | Ruta 3; 30 min; tipo_dia x franja | PNG; 1334x1067px; dpi 120x120 | 2026-05-03 18:02:15 |
| reports/figures/operational_heatmap_3_60min.png | src/proyecto_grado/features/operational_hours.py:OperationalHoursEstimator.plot_heatmap | Cobertura operativa - ruta 3 \| 60 min; x: Tipo de dia; y: Franja horaria (HH:MM); color: pct_activa | Mapa de calor de la frecuencia historica de franjas con despacho para estimar horario operativo. | Ruta 3; 60 min; tipo_dia x franja | PNG; 1328x947px; dpi 120x120 | 2026-05-03 18:02:15 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_gap_heatmap_inline | Streamlit + seaborn/matplotlib | Franjas imputadas como gap por dia y hora; x: Hora; y: Dia de semana; color: % gaps | Porcentaje de franjas marcadas como gap por dia y hora para la serie filtrada. | Ruta/granularidad/filtros seleccionados | Streamlit st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_gaps_comparison_bars | Streamlit + matplotlib | Gaps: horario operativo vs 24h - Ruta {route} \| {gran} min; x: Tipo de dia; y: % de franjas como gap | Barras comparando porcentaje de gaps sobre 24h contra gaps dentro del horario operativo estimado. | Ruta y granularidad seleccionadas; tipo_dia | Streamlit st.pyplot; figsize 10x5 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_gap_type_heatmap_inline | Streamlit + seaborn/matplotlib | {gap_tipo} por dia y hora; x: Hora; y: Dia de semana; color: % del tipo de gap | Mapa de calor para gap_anomalo o fuera_operacion, segun selector del dashboard. | Ruta/granularidad/filtros seleccionados | Streamlit st.pyplot; figsize 11x4.8 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:render_operational_hours_section | Streamlit + Altair | Horario operativo estimado; x: Hora del dia; y: Tipo de dia | Bandas de inicio-fin operativo estimado por tipo de dia, con etiquetas de rango horario. | Ruta y granularidad seleccionadas; tipo_dia | Altair interactivo; height max(210, n_tipos*42) | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_granularity_comparison_inline | Streamlit + seaborn/matplotlib | Ruta {route} - impacto de la granularidad; subplots: n_franjas, pct_gaps (%), metrica seleccionada | Comparacion entre granularidades 15/30/60 min para una misma ruta y rango de fechas. | Ruta seleccionada; compara granularidades | Streamlit st.pyplot; figsize 13x4.2 | 2026-05-13 16:39:54 |

### Tablas

#### `data/processed/operational_hours.parquet`

- Descripcion: Horario operativo estimado por tipo_dia, ruta y granularidad, con duracion, cobertura y franjas anomalas.
- Forma: `30 x 14`
- Fecha de ultima modificacion: `2026-05-03 18:02:13`
- Columnas y tipos: `tipo_dia: str; ruta: int64; granularidad_min: int64; hora_inicio_op: str; hora_fin_op: str; hora_inicio_op_min: int64; hora_fin_op_min: int64; duracion_operativa_h: float64; n_dias_muestra: int64; n_dias_usado: int64; umbral_usado: float64; fallback_laboral: bool; franjas_anomalas_count: int64; pct_cobertura_dentro_horario: float64`
- Muestra (`head(3)`):

```csv
tipo_dia,ruta,granularidad_min,hora_inicio_op,hora_fin_op,hora_inicio_op_min,hora_fin_op_min,duracion_operativa_h,n_dias_muestra,n_dias_usado,umbral_usado,fallback_laboral,franjas_anomalas_count,pct_cobertura_dentro_horario
LABORAL,1,15,04:30,18:00,270,1080,13.75,501,501,0.1,False,1,1.0
SABADO,1,15,04:30,17:45,270,1065,13.5,106,106,0.1,False,2,1.0
DOMINGO,1,15,05:15,17:00,315,1020,12.0,105,105,0.1,False,10,1.0
```

#### `reports/tables/baseline/demand_supply_by_franja.csv`

- Descripcion: Desajuste demanda-oferta por bins operativos usando load_factor estimado; interpretacion limitada porque PASAJEROS son abordajes acumulados, no ocupacion simultanea.
- Forma: `40 x 11`
- Fecha de ultima modificacion: `2026-06-08 16:01:01`
- Columnas y tipos: `FK_RUTA: int64; franja_horaria: str; tipo_dia: str; n_bins: float64; load_factor_mean: float64; load_factor_p50: float64; load_factor_p95: float64; sobrecarga_pct: float64; subcarga_pct: float64; optimo_pct: float64; desajuste_abs_mean: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,franja_horaria,tipo_dia,n_bins,load_factor_mean,load_factor_p50,load_factor_p95,sobrecarga_pct,subcarga_pct,optimo_pct,desajuste_abs_mean
1,MADRUGADA,DOMINGO,46.0,1.071,1.089,1.491,78.26,0.0,21.74,9.5
1,MADRUGADA,FESTIVO,5.0,1.204,1.143,1.423,100.0,0.0,0.0,14.8
1,MADRUGADA,FESTIVO_PUENTE,10.0,0.974,0.946,1.21,70.0,0.0,30.0,7.7
```

#### `reports/tables/baseline/demand_supply_summary.csv`

- Descripcion: Desajuste demanda-oferta por bins operativos usando load_factor estimado; interpretacion limitada porque PASAJEROS son abordajes acumulados, no ocupacion simultanea.
- Forma: `2 x 9`
- Fecha de ultima modificacion: `2026-06-08 16:01:01`
- Columnas y tipos: `FK_RUTA: int64; n_bins: float64; load_factor_mean: float64; load_factor_p50: float64; load_factor_p95: float64; sobrecarga_pct: float64; subcarga_pct: float64; optimo_pct: float64; desajuste_abs_mean: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,n_bins,load_factor_mean,load_factor_p50,load_factor_p95,sobrecarga_pct,subcarga_pct,optimo_pct,desajuste_abs_mean
1,10008.0,1.544,1.545,2.179,96.34,0.25,3.41,86.3
3,9958.0,1.642,1.661,2.321,96.24,0.22,3.53,113.2
```

#### `reports/tables/baseline/diagnostico_disponibilidad_flota.csv`

- Descripcion: Reconstruccion de disponibilidad/timeline EN_RUTA-EN_PATIO para diagnosticar patio vacio y espera larga.
- Forma: `193 x 2`
- Fecha de ultima modificacion: `2026-06-22 20:52:17`
- Columnas y tipos: `timestamp: str; vehiculos_en_patio: int64`
- Muestra (`head(3)`):

```csv
timestamp,vehiculos_en_patio
2024-05-31 04:00:00,0
2024-05-31 04:05:00,0
2024-05-31 04:10:00,0
```

#### `reports/tables/baseline/diagnostico_disponibilidad_multidia.csv`

- Descripcion: Disponibilidad de vehiculos en patio por franjas criticas y conteo de headways largos por franja.
- Forma: `12 x 13`
- Fecha de ultima modificacion: `2026-06-22 20:58:42`
- Columnas y tipos: `fecha: str; disp_pico_manana: float64; disp_pico_tarde: float64; disp_cierre: float64; pct_vacio_pico_manana: float64; pct_vacio_pico_tarde: float64; pct_vacio_cierre: float64; headways_largos_pico_manana: int64; headways_largos_pico_tarde: int64; headways_largos_cierre: int64; headways_largos_otros: int64; n_despachos: int64; n_vehiculos: int64`
- Muestra (`head(3)`):

```csv
fecha,disp_pico_manana,disp_pico_tarde,disp_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre,headways_largos_pico_manana,headways_largos_pico_tarde,headways_largos_cierre,headways_largos_otros,n_despachos,n_vehiculos
2024-04-16,3.17,6.67,3.83,33.3,0.0,0.0,1,0,0,4,204,57
2024-06-05,3.31,10.0,4.17,35.4,0.0,0.0,3,0,2,3,222,57
2024-07-24,1.73,9.67,3.83,60.4,0.0,0.0,3,1,1,4,188,56
```

#### `reports/tables/baseline/diagnostico_timeline_vehiculos.csv`

- Descripcion: Reconstruccion de disponibilidad/timeline EN_RUTA-EN_PATIO para diagnosticar patio vacio y espera larga.
- Forma: `384 x 5`
- Fecha de ultima modificacion: `2026-06-22 20:52:17`
- Columnas y tipos: `PLACA: str; estado: str; inicio: str; fin: str; ruta: float64`
- Muestra (`head(3)`):

```csv
PLACA,estado,inicio,fin,ruta
SRE698,EN_RUTA,2024-05-31 05:37:25,2024-05-31 07:21:54,3.0
SRE698,EN_PATIO,2024-05-31 07:21:54,2024-05-31 07:24:56,
SRE698,EN_RUTA,2024-05-31 07:24:56,2024-05-31 09:55:57,1.0
```

#### `reports/tables/baseline/fleet_availability_by_day.csv`

- Descripcion: Disponibilidad de vehiculos en patio por franjas criticas y conteo de headways largos por franja.
- Forma: `15 x 13`
- Fecha de ultima modificacion: `2026-06-22 21:05:47`
- Columnas y tipos: `fecha: str; disp_pico_manana: float64; disp_pico_tarde: float64; disp_cierre: float64; pct_vacio_pico_manana: float64; pct_vacio_pico_tarde: float64; pct_vacio_cierre: float64; headways_largos_pico_manana: int64; headways_largos_pico_tarde: int64; headways_largos_cierre: int64; headways_largos_otros: int64; n_despachos: int64; n_vehiculos: int64`
- Muestra (`head(3)`):

```csv
fecha,disp_pico_manana,disp_pico_tarde,disp_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre,headways_largos_pico_manana,headways_largos_pico_tarde,headways_largos_cierre,headways_largos_otros,n_despachos,n_vehiculos
2024-04-16,3.17,6.67,3.83,33.3,0.0,0.0,1,0,0,4,204,57
2024-05-24,2.08,10.12,1.58,50.0,0.0,16.7,1,2,2,7,198,55
2024-07-04,2.56,6.38,1.75,39.6,0.0,16.7,2,2,1,9,207,53
```

#### `reports/tables/baseline/fleet_availability_summary.csv`

- Descripcion: Disponibilidad de vehiculos en patio por franjas criticas y conteo de headways largos por franja.
- Forma: `1 x 12`
- Fecha de ultima modificacion: `2026-06-22 21:05:47`
- Columnas y tipos: `n_dias_analizados: int64; total_headways_largos: int64; pct_largos_pico_manana: float64; pct_largos_pico_tarde: float64; pct_largos_cierre: float64; pct_largos_otros: float64; disp_promedio_pico_manana: float64; disp_promedio_pico_tarde: float64; disp_promedio_cierre: float64; pct_vacio_pico_manana: float64; pct_vacio_pico_tarde: float64; pct_vacio_cierre: float64`
- Muestra (`head(3)`):

```csv
n_dias_analizados,total_headways_largos,pct_largos_pico_manana,pct_largos_pico_tarde,pct_largos_cierre,pct_largos_otros,disp_promedio_pico_manana,disp_promedio_pico_tarde,disp_promedio_cierre,pct_vacio_pico_manana,pct_vacio_pico_tarde,pct_vacio_cierre
15,212,17.5,15.6,11.3,55.7,2.65,7.95,3.26,36.8,0.0,3.9
```

#### `reports/tables/baseline/headway_by_franja.csv`

- Descripcion: Indicadores de regularidad de headway: media, desviacion, CV, p50/p95, bunching y espera excesiva.
- Forma: `24 x 11`
- Fecha de ultima modificacion: `2026-06-08 17:28:37`
- Columnas y tipos: `FK_RUTA: int64; franja: str; tipo_dia: str; n_intervalos: float64; headway_mean: float64; headway_std: float64; cv_headway: float64; headway_p50: float64; headway_p95: float64; bunching_pct: float64; excess_wait_pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,franja,tipo_dia,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,MEDIODIA,DOMINGO,620.0,30.3,16.29,0.537,26.78,62.63,1.94,40.48
1,MEDIODIA,LABORAL,9340.0,10.21,5.63,0.551,9.15,20.13,3.1,0.92
1,MEDIODIA,SABADO,1397.0,13.66,6.5,0.476,12.5,26.31,2.36,2.15
```

#### `reports/tables/baseline/headway_by_hour.csv`

- Descripcion: Indicadores de regularidad de headway: media, desviacion, CV, p50/p95, bunching y espera excesiva.
- Forma: `88 x 11`
- Fecha de ultima modificacion: `2026-06-08 17:28:37`
- Columnas y tipos: `FK_RUTA: int64; HORA_INICIO_H: float64; tipo_dia: str; n_intervalos: float64; headway_mean: float64; headway_std: float64; cv_headway: float64; headway_p50: float64; headway_p95: float64; bunching_pct: float64; excess_wait_pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,HORA_INICIO_H,tipo_dia,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,4.0,LABORAL,1210.0,7.84,4.01,0.511,7.19,15.14,7.93,0.08
1,4.0,SABADO,191.0,8.8,4.25,0.484,8.3,16.29,5.76,0.0
1,5.0,DOMINGO,29.0,24.77,9.33,0.377,22.38,36.59,0.0,24.14
```

#### `reports/tables/baseline/headway_summary.csv`

- Descripcion: Indicadores de regularidad de headway: media, desviacion, CV, p50/p95, bunching y espera excesiva.
- Forma: `2 x 9`
- Fecha de ultima modificacion: `2026-06-08 17:28:37`
- Columnas y tipos: `FK_RUTA: int64; n_intervalos: float64; headway_mean: float64; headway_std: float64; cv_headway: float64; headway_p50: float64; headway_p95: float64; bunching_pct: float64; excess_wait_pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,n_intervalos,headway_mean,headway_std,cv_headway,headway_p50,headway_p95,bunching_pct,excess_wait_pct
1,50658.0,10.97,7.92,0.722,9.15,24.17,3.82,2.79
3,53223.0,10.56,8.17,0.774,8.58,24.7,4.71,3.09
```

#### `reports/tables/baseline/load_factor_distribution.csv`

- Descripcion: Desajuste demanda-oferta por bins operativos usando load_factor estimado; interpretacion limitada porque PASAJEROS son abordajes acumulados, no ocupacion simultanea.
- Forma: `6 x 4`
- Fecha de ultima modificacion: `2026-06-08 16:01:01`
- Columnas y tipos: `FK_RUTA: int64; estado_bin: str; n_bins: int64; pct: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,estado_bin,n_bins,pct
1,OPTIMO,341,3.41
1,SOBRECARGA,9642,96.34
1,SUBCARGA,25,0.25
```

#### `reports/tables/baseline/productivity_summary.csv`

- Descripcion: Productividad por despacho por ruta/semana: pasajeros, despachos, productividad bruta, tendencia OLS y ajustada.
- Forma: `2 x 10`
- Fecha de ultima modificacion: `2026-06-23 10:40:24`
- Columnas y tipos: `FK_RUTA: int64; n_semanas_validas: int64; productividad_promedio_bruta: float64; productividad_p50: float64; productividad_std: float64; tendencia_slope_semanal: float64; tendencia_slope_mensual_est: float64; primera_semana_estimada: float64; ultima_semana_estimada: float64; caida_total_periodo: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,n_semanas_validas,productividad_promedio_bruta,productividad_p50,productividad_std,tendencia_slope_semanal,tendencia_slope_mensual_est,primera_semana_estimada,ultima_semana_estimada,caida_total_periodo
1,111,44.4,44.51,2.53,0.005,0.02,44.15,44.66,-0.51
3,111,48.5,48.65,2.47,0.006,0.025,48.18,48.83,-0.65
```

#### `reports/tables/baseline/productivity_weekly_series.csv`

- Descripcion: Productividad por despacho por ruta/semana: pasajeros, despachos, productividad bruta, tendencia OLS y ajustada.
- Forma: `222 x 7`
- Fecha de ultima modificacion: `2026-06-23 10:40:24`
- Columnas y tipos: `semana: str; FK_RUTA: int64; pasajeros_total: int64; despachos_total: int64; productividad_bruta: float64; tendencia_ols: float64; productividad_ajustada: float64`
- Muestra (`head(3)`):

```csv
semana,FK_RUTA,pasajeros_total,despachos_total,productividad_bruta,tendencia_ols,productividad_ajustada
2024-04-22,1,27811,580,47.95,44.15,48.2
2024-04-22,3,30180,566,53.32,48.18,53.64
2024-04-29,1,25278,559,45.22,44.15,45.47
```

#### `reports/tables/eda/duration_by_route.csv`

- Descripcion: KPIs operacionales generales: duracion por ruta o conteos/retencion/pasajeros/duracion del pipeline.
- Forma: `2 x 5`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `FK_RUTA: int64; count: int64; mean: float64; median: float64; p95: float64`
- Muestra (`head(3)`):

```csv
FK_RUTA,count,mean,median,p95
1,51041,160.56265126728186,157.3,199.06666666666663
3,53609,161.33999359560272,161.03333333333333,213.38333333333333
```

#### `reports/tables/eda/operational_kpis.csv`

- Descripcion: KPIs operacionales generales: duracion por ruta o conteos/retencion/pasajeros/duracion del pipeline.
- Forma: `17 x 3`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `kpi: str; value: float64; unit: str`
- Muestra (`head(3)`):

```csv
kpi,value,unit
despachos_raw,104803.0,rows
despachos_qc,104803.0,rows
despachos_end,104803.0,rows
```

#### `reports/tables/gaps_horario_operativo.csv`

- Descripcion: Resumen de horarios operativos, gaps y cobertura de series por ruta/granularidad.
- Forma: `30 x 9`
- Fecha de ultima modificacion: `2026-05-13 16:12:03`
- Columnas y tipos: `granularidad_min: int64; ruta: int64; tipo_dia: str; n_franjas_op: int64; n_gaps_op: int64; pct_gaps_op: float64; n_franjas_24h: int64; n_gaps_24h: int64; pct_gaps_24h: float64`
- Muestra (`head(3)`):

```csv
granularidad_min,ruta,tipo_dia,n_franjas_op,n_gaps_op,pct_gaps_op,n_franjas_24h,n_gaps_24h,pct_gaps_24h
15,1,DOMINGO,5004,2943,58.81,10017,7945,79.32
15,1,FESTIVO,768,463,60.29,1536,1228,79.95
15,1,FESTIVO_PUENTE,980,546,55.71,1920,1486,77.4
```

#### `reports/tables/operational_hours_summary.csv`

- Descripcion: Resumen de horarios operativos, gaps y cobertura de series por ruta/granularidad.
- Forma: `30 x 14`
- Fecha de ultima modificacion: `2026-05-03 18:02:13`
- Columnas y tipos: `tipo_dia: str; ruta: int64; granularidad_min: int64; hora_inicio_op: str; hora_fin_op: str; hora_inicio_op_min: int64; hora_fin_op_min: int64; duracion_operativa_h: float64; n_dias_muestra: int64; n_dias_usado: int64; umbral_usado: float64; fallback_laboral: bool; franjas_anomalas_count: int64; pct_cobertura_dentro_horario: float64`
- Muestra (`head(3)`):

```csv
tipo_dia,ruta,granularidad_min,hora_inicio_op,hora_fin_op,hora_inicio_op_min,hora_fin_op_min,duracion_operativa_h,n_dias_muestra,n_dias_usado,umbral_usado,fallback_laboral,franjas_anomalas_count,pct_cobertura_dentro_horario
LABORAL,1,15,04:30,18:00,270,1080,13.75,501,501,0.1,False,1,1.0
SABADO,1,15,04:30,17:45,270,1065,13.5,106,106,0.1,False,2,1.0
DOMINGO,1,15,05:15,17:00,315,1020,12.0,105,105,0.1,False,10,1.0
```

#### `reports/tables/time_series_summary.csv`

- Descripcion: Resumen de horarios operativos, gaps y cobertura de series por ruta/granularidad.
- Forma: `6 x 9`
- Fecha de ultima modificacion: `2026-05-03 14:10:20`
- Columnas y tipos: `granularidad_min: int64; ruta: int64; n_franjas: int64; n_gaps: int64; pct_gaps: float64; pasajeros_total: float64; valida: bool; errores: float64; advertencias: float64`
- Muestra (`head(3)`):

```csv
granularidad_min,ruta,n_franjas,n_gaps,pct_gaps,pasajeros_total,valida,errores,advertencias
15,1,71727,38888,54.2,2287320.0,True,,
15,3,71732,38775,54.1,2624512.0,True,,
30,1,35864,17377,48.5,2287320.0,True,,
```

## D) Modelado y evaluacion

No encontre artefactos guardados de entrenamiento, prediccion o evaluacion de modelos. `src/proyecto_grado/models/`, `src/proyecto_grado/evaluation/` y `notebooks/03_modeling`, `notebooks/04_evaluation` no contienen salidas tabulares o graficas, mas alla de `.gitkeep`. Los ACF/PACF y correlaciones del EDA son insumos pre-modelado y quedaron listados en A.

## E) Otros

### Figuras

| Ruta / ubicacion | Fuente | Titulo y ejes | Que muestra | Ruta/granularidad | Formato/dim | Modificado |
| --- | --- | --- | --- | --- | --- | --- |
| reports/figures/eda/etl_rows_by_stage.png | src/proyecto_grado/analytics/plots.py:plot_row_counts | Registros conservados por etapa del ETL; x: Etapa; y: Filas | Conteo de filas disponibles/conservadas en raw, QC, fin resuelto y model-ready. | Ambas rutas; etapa ETL | PNG; 1773x939px; dpi 220x220 | 2026-04-25 11:18:41 |
| reports/figures/eda/qc_flags_top.png | src/proyecto_grado/analytics/plots.py:plot_qc_flags | Principales alertas de calidad del ETL; x: Registros; y: Flag QC | Frecuencia de las alertas/banderas de calidad mas comunes en la etapa QC. | Ambas rutas; etapa QC | PNG; 2039x1203px; dpi 220x220 | 2026-04-25 11:18:42 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_row_counts_inline | Streamlit + seaborn/matplotlib | Registros conservados por etapa del ETL; x: Etapa; y: Filas | Version inline del conteo de filas por etapa ETL mostrado en el dashboard. | Ambas rutas; etapa ETL | Streamlit st.pyplot; figsize 8.5x4.4 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_qc_flags_inline | Streamlit + seaborn/matplotlib | Principales alertas de calidad del ETL; x: Registros; y: flag | Top 12 flags de calidad ordenados por frecuencia en el dashboard. | Ambas rutas; QC | Streamlit st.pyplot; figsize 9.2x5.4 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/dashboard/app.py:plot_finalization_pie | Streamlit + matplotlib | Clasificacion de fin de recorrido; grafico circular sin ejes | Distribucion porcentual de FIN_TIPO tras resolver fin de recorrido. | Ambas rutas; fin de recorrido | Streamlit st.pyplot; figsize 6.4x4.6 | 2026-05-13 16:39:54 |
| solo en codigo, no guardada - src/proyecto_grado/etl/gps.py:validar_radio_con_nulos | matplotlib plt.show | Distancia minima al patio (Hora Planificada) en registros Nulos; x: Distancia (metros); y: Frecuencia | Histograma de distancias GPS minimas al patio para validar radio de geocerca en registros sin hora real. | Rutas operativas; muestra de nulos GPS | matplotlib show; figsize 10x4; no archivo | 2026-05-02 13:05:44 |

### Tablas

#### `data/processed/model_ready/despachos_model_ready.csv`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `109559 x 18`
- Fecha de ultima modificacion: `2026-06-10 19:21:42`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready.parquet`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `109559 x 18`
- Fecha de ultima modificacion: `2026-06-10 19:21:43`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16 00:00:00,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16 00:00:00,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16 00:00:00,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready_freeze_20260503_114750.csv`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `105490 x 18`
- Fecha de ultima modificacion: `2026-05-03 11:47:52`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready_freeze_20260503_114750.parquet`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `105490 x 18`
- Fecha de ultima modificacion: `2026-05-03 11:47:51`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16 00:00:00,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16 00:00:00,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16 00:00:00,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready_freeze_20260610_191955.csv`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `109559 x 18`
- Fecha de ultima modificacion: `2026-06-10 19:19:57`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready_freeze_20260610_191955.parquet`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `109559 x 18`
- Fecha de ultima modificacion: `2026-06-10 19:19:55`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16 00:00:00,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16 00:00:00,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16 00:00:00,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.csv`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `109559 x 18`
- Fecha de ultima modificacion: `2026-06-10 19:21:47`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: str; HORA_INICIAL_REAL: str; HORA_FIN_FINAL: str; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int64; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.parquet`

- Descripcion: Dataset model-ready/freeze de despachos individuales, base de modelado y EDA; contiene variables limpias y flags finales.
- Forma: `109559 x 18`
- Fecha de ultima modificacion: `2026-06-10 19:21:43`
- Columnas y tipos: `PK_INTERVALO_DESPACHO: int64; PLACA: str; FK_RUTA: int64; FECHA_INICIAL: datetime64[us]; HORA_INICIAL_REAL: datetime64[us]; HORA_FIN_FINAL: datetime64[ns]; DURACION_MIN_FINAL: float64; PASAJEROS: int64; DISTANCIA: int64; RECORRIDO_COMPLETO: float64; FIN_TIPO: str; HORA_FIN_FUENTE: str; HORA_INICIO_H: float64; HORA_FIN_H: int32; DIA_SEMANA: float64; MES: float64; DIA: float64; MODEL_READY_OK: bool`
- Muestra (`head(3)`):

```csv
PK_INTERVALO_DESPACHO,PLACA,FK_RUTA,FECHA_INICIAL,HORA_INICIAL_REAL,HORA_FIN_FINAL,DURACION_MIN_FINAL,PASAJEROS,DISTANCIA,RECORRIDO_COMPLETO,FIN_TIPO,HORA_FIN_FUENTE,HORA_INICIO_H,HORA_FIN_H,DIA_SEMANA,MES,DIA,MODEL_READY_OK
244812,VCL424,3,2024-04-16 00:00:00,2024-04-16 04:42:58,2024-04-16 06:17:02,94.06666666666666,49,33200,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244810,VCC469,3,2024-04-16 00:00:00,2024-04-16 04:32:38,2024-04-16 06:16:04,103.43333333333334,41,42800,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
244811,VCC406,3,2024-04-16 00:00:00,2024-04-16 04:25:06,2024-04-16 06:44:43,139.61666666666667,49,41100,1.0,COMPLETO,REAL,4.0,6,1.0,4.0,16.0,True
```

#### `reports/tables/eda/dataset_overview.csv`

- Descripcion: Tabla diagnostica post-ETL sobre disponibilidad, retencion, nulos, flags QC o finalizacion de recorridos.
- Forma: `4 x 4`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `stage: str; available: bool; rows: int64; columns: int64`
- Muestra (`head(3)`):

```csv
stage,available,rows,columns
raw,True,104803,17
quality_checked,True,104803,40
trip_end_resolved,True,104803,44
```

#### `reports/tables/eda/finalization_summary.csv`

- Descripcion: Tabla diagnostica post-ETL sobre disponibilidad, retencion, nulos, flags QC o finalizacion de recorridos.
- Forma: `5 x 3`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `FIN_TIPO: str; count: int64; pct: float64`
- Muestra (`head(3)`):

```csv
FIN_TIPO,count,pct
COMPLETO,90450,86.30478135167886
TRUNCADO_RETORNO,11327,10.807896720513725
TRUNCADO_INDETERMINADO,1886,1.7995668062937131
```

#### `reports/tables/eda/missing_before_after.csv`

- Descripcion: Tabla diagnostica post-ETL sobre disponibilidad, retencion, nulos, flags QC o finalizacion de recorridos.
- Forma: `7 x 5`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `column: str; raw_missing: int64; raw_missing_pct: float64; final_missing: float64; final_missing_pct: float64`
- Muestra (`head(3)`):

```csv
column,raw_missing,raw_missing_pct,final_missing,final_missing_pct
PK_INTERVALO_DESPACHO,0,0.0,0.0,0.0
PLACA,0,0.0,0.0,0.0
FK_RUTA,0,0.0,0.0,0.0
```

#### `reports/tables/eda/qc_flag_summary.csv`

- Descripcion: Tabla diagnostica post-ETL sobre disponibilidad, retencion, nulos, flags QC o finalizacion de recorridos.
- Forma: `16 x 3`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `flag: str; count: int64; pct: float64`
- Muestra (`head(3)`):

```csv
flag,count,pct
qc_any_flag,15615,14.899382651259982
qc_soft_fail,15602,14.88697842619009
flag_hf_nula,14353,13.695218648321136
```

#### `reports/tables/eda/retention_summary.csv`

- Descripcion: Tabla diagnostica post-ETL sobre disponibilidad, retencion, nulos, flags QC o finalizacion de recorridos.
- Forma: `1 x 4`
- Fecha de ultima modificacion: `2026-04-25 11:18:41`
- Columnas y tipos: `raw_rows: int64; model_ready_rows: int64; rows_difference: int64; retention_pct: float64`
- Muestra (`head(3)`):

```csv
raw_rows,model_ready_rows,rows_difference,retention_pct
104803,104650,153,99.85401181263896
```

#### `reports/tables/etl/model_ready_qc_20260503_114750.csv`

- Descripcion: QC final del dataset model-ready: totales de filas, duplicados y missingness de columnas criticas.
- Forma: `3 x 3`
- Fecha de ultima modificacion: `2026-05-03 11:47:50`
- Columnas y tipos: `regla: str; conteo: int64; pct: float64`
- Muestra (`head(3)`):

```csv
regla,conteo,pct
pk_duplicada,0,0.0
placa_vacia,0,0.0
duracion_no_positiva,0,0.0
```

#### `reports/tables/etl/model_ready_qc_20260610_191955.csv`

- Descripcion: QC final del dataset model-ready: totales de filas, duplicados y missingness de columnas criticas.
- Forma: `3 x 3`
- Fecha de ultima modificacion: `2026-06-10 19:19:55`
- Columnas y tipos: `regla: str; conteo: int64; pct: float64`
- Muestra (`head(3)`):

```csv
regla,conteo,pct
pk_duplicada,0,0.0
placa_vacia,0,0.0
duracion_no_positiva,0,0.0
```

#### `reports/tables/etl/model_ready_qc_20260610_192142.csv`

- Descripcion: QC final del dataset model-ready: totales de filas, duplicados y missingness de columnas criticas.
- Forma: `3 x 3`
- Fecha de ultima modificacion: `2026-06-10 19:21:42`
- Columnas y tipos: `regla: str; conteo: int64; pct: float64`
- Muestra (`head(3)`):

```csv
regla,conteo,pct
pk_duplicada,0,0.0
placa_vacia,0,0.0
duracion_no_positiva,0,0.0
```

#### `reports/tables/qc/qc_resumen.csv`

- Descripcion: Resumen de control de calidad ETL por regla, ruta o vehiculo.
- Forma: `16 x 3`
- Fecha de ultima modificacion: `2026-06-10 19:21:35`
- Columnas y tipos: `regla_flag: str; conteo: int64; porcentaje: float64`
- Muestra (`head(3)`):

```csv
regla_flag,conteo,porcentaje
qc_any_flag,16497,15.035545023696685
qc_soft_fail,16483,15.022785271600435
flag_hf_nula,15159,13.816077287641267
```

#### `reports/tables/qc/qc_top_rutas.csv`

- Descripcion: Resumen de control de calidad ETL por regla, ruta o vehiculo.
- Forma: `2 x 3`
- Fecha de ultima modificacion: `2026-06-10 19:21:35`
- Columnas y tipos: `qc_any_flag: int64; qc_hard_fail: int64; qc_soft_fail: int64`
- Muestra (`head(3)`):

```csv
qc_any_flag,qc_hard_fail,qc_soft_fail
8321,8,8313
8176,6,8170
```

#### `reports/tables/qc/qc_top_vehiculos.csv`

- Descripcion: Resumen de control de calidad ETL por regla, ruta o vehiculo.
- Forma: `15 x 3`
- Fecha de ultima modificacion: `2026-06-10 19:21:35`
- Columnas y tipos: `qc_any_flag: int64; qc_hard_fail: int64; qc_soft_fail: int64`
- Muestra (`head(3)`):

```csv
qc_any_flag,qc_hard_fail,qc_soft_fail
155,3,152
570,1,569
380,1,379
```

## Artefactos textuales y JSON relacionados

| Ruta | Que contiene | Bytes | Modificado |
| --- | --- | --- | --- |
| reports/tables/baseline/BASELINE_REPORT.txt | Reporte textual consolidado del baseline operativo: headway, reduccion de flota, productividad y disponibilidad. | 7197 | 2026-06-29 11:51:32 |
| reports/tables/baseline/fleet_availability_report.txt | Reporte textual de disponibilidad de flota en patio y headways largos. | 1809 | 2026-06-22 21:05:47 |
| reports/tables/baseline/productivity_report.txt | Reporte textual de productividad por despacho y tendencia OLS por ruta. | 3223 | 2026-06-23 10:40:24 |
| reports/tables/eda/temporal_executive_summary.txt | Resumen ejecutivo textual del EDA temporal. | 5436 | 2026-05-07 18:35:44 |

| Ruta | Que contiene | Bytes | Modificado |
| --- | --- | --- | --- |
| reports/tables/etl/model_ready_metadata_20260503_114750.json | (contenido inferido - confirmar) Metadata del freeze model-ready o corrida ETL. | 1118 | 2026-05-03 11:47:52 |
| reports/tables/etl/model_ready_metadata_20260610_191955.json | (contenido inferido - confirmar) Metadata del freeze model-ready o corrida ETL. | 1119 | 2026-06-10 19:19:57 |
| reports/tables/etl/model_ready_metadata_20260610_192142.json | (contenido inferido - confirmar) Metadata del freeze model-ready o corrida ETL. | 1119 | 2026-06-10 19:21:47 |

## Resumen por KPI

| KPI | Estado | Evidencia encontrada | Comentario |
| --- | --- | --- | --- |
| CV headway / irregularidad | Tabla guardada | `reports/tables/baseline/headway_summary.csv`, `headway_by_franja.csv`, `headway_by_hour.csv`; no figura guardada especifica de CV/headway. | Figura de distribucion/serie de headway aun no existe. |
| Headway promedio/std/p50/p95 | Tabla guardada | `reports/tables/baseline/headway_*.csv` | Sin figura guardada. |
| Bunching < 3 min | Tabla guardada | `reports/tables/baseline/headway_*.csv` | Sin figura guardada. |
| Espera excesiva > 30 min | Tabla guardada | `reports/tables/baseline/headway_*.csv` | Sin figura guardada. |
| Disponibilidad de flota en patio | Tabla y figura guardadas | `fleet_availability_summary.csv`, `fleet_availability_by_day.csv`, `diagnostico_disponibilidad_*.csv`; `reports/figures/operational_heatmap_*.png` | Heatmaps muestran cobertura operativa, no directamente vehiculos_en_patio por hora. |
| Patio vacio por franja critica | Tabla guardada | `fleet_availability_summary.csv`, `fleet_availability_by_day.csv`, `diagnostico_disponibilidad_multidia.csv` | Sin figura guardada directa; solo dashboard/gaps y heatmap operativo. |
| Vehiculos activos / contraccion de flota | Tabla guardada | `diagnostico_flota_mensual.csv`, `diagnostico_flota_comparacion.csv`, `diagnostico_vehiculos_estado.csv` | No hay figura guardada de serie mensual de flota. |
| Despachos totales mensuales | Tabla guardada | `diagnostico_flota_mensual.csv`, `diagnostico_flota_comparacion.csv` | No hay figura guardada. |
| Pasajeros totales mensuales | Tabla y figura parcial | `diagnostico_flota_mensual.csv`; `tendencia_mensual_1.png`, `tendencia_mensual_3.png` muestran demanda mensual por ruta | La figura de tendencia no incorpora vehiculos activos/despachos en el mismo panel. |
| Productividad por despacho | Tabla guardada | `productivity_summary.csv`, `productivity_weekly_series.csv`, `diagnostico_flota_mensual.csv` | No hay figura guardada de productividad semanal/mensual. |
| Rotacion / gaps entre despachos por vehiculo | Solo en codigo/consola | `scripts/diagnostico_rotacion.py` imprime diagnostico y no genera archivos. | No existe tabla ni figura guardada. |
| Costo operativo | No encontrado | No encontre tabla/figura/codigo que calcule costos. | Hueco claro para diagnostico si el capitulo requiere costos. |
| Demanda recuperable | Solo formulado en texto | `reports/tables/baseline/BASELINE_REPORT.txt` define la formula para Fase 4. | No existe tabla/figura calculada todavia. |
| Load factor / demanda-oferta | Tabla guardada con advertencia metodologica | `demand_supply_summary.csv`, `demand_supply_by_franja.csv`, `load_factor_distribution.csv` | El reporte baseline advierte que load factor clasico no aplica como ocupacion simultanea. |
| Retencion ETL | Tabla y figura guardadas | `retention_summary.csv`, `dataset_overview.csv`; `etl_rows_by_stage.png` | OK para diagnostico ETL. |
| Atipicos de demanda | Tabla y figura/codigo | `data/processed/eda/atipicos_*.parquet`; dashboard inline `plot_eda_outliers_inline` no guardado. | No hay PNG estatico de atipicos como serie; el dashboard los dibuja. |
| Estacionalidad / autocorrelacion | Tabla y figura guardadas | `autocorr_*.parquet`; `acf_pacf_*.png` | OK como insumo pre-modelado. |

## Huecos detectados

- Figura guardada de serie mensual multi-KPI de contraccion de flota: vehiculos activos, despachos, pasajeros y productividad en paneles comparables.
- Figura guardada de `CV headway` por ruta/franja/hora y distribucion de headways; actualmente solo existen tablas.
- Figura guardada de productividad semanal/mensual por ruta con tendencia OLS; actualmente solo existen tablas y reporte textual.
- Figura guardada de disponibilidad real de vehiculos en patio por hora/dia; los PNG actuales son heatmaps de cobertura operativa (`pct_activa`), no vehiculos_en_patio.
- Tabla/figura persistida de rotacion operacional por vehiculo: gaps entre fin e inicio, cambios de ruta, ciclos por dia; `diagnostico_rotacion.py` solo imprime consola.
- Tabla/figura de costo operativo; no encontre calculos de costos.
- Tabla/figura de demanda recuperable; solo aparece la formula conceptual para Fase 4.
- Artefactos de modelado/evaluacion: no hay metricas de modelos, predicciones, backtesting ni simulacion retrospectiva guardadas.
- Figura de festivos/puentes comparando contra laborales en un unico panel; existen curvas por tipo de dia separadas, pero no una comparacion sintetica guardada.
- Mapa de calor o calendario mensual de demanda diaria; existen heatmaps dia_semana x hora y tendencia mensual, pero no calendario diario.
