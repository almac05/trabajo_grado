# Project Summary — Proyecto Grado Montebello
*Generado automáticamente — 2026-06-08*

---

## 1. ESTRUCTURA DEL PROYECTO

```
proyecto_grado/
├── configs/
│   ├── etl.yaml
│   └── features.yaml
├── docs/
├── notebooks/
│   ├── 01_eda/          (vacío)
│   ├── 02_preprocessing/ (vacío)
│   ├── 03_modeling/     (vacío)
│   └── 04_evaluation/   (vacío)
├── reports/
│   ├── figures/
│   │   ├── eda/         (curvas intradía, heatmaps, ACF/PACF, boxplots, tendencia)
│   │   └── operational_heatmap_*.png
│   └── tables/
│       ├── eda/         (CSVs + temporal_executive_summary.txt)
│       ├── etl/         (model_ready_qc + metadata con timestamp)
│       ├── qc/
│       ├── gaps_horario_operativo.csv
│       ├── operational_hours_summary.csv
│       └── time_series_summary.csv
├── src/proyecto_grado/
│   ├── analytics/
│   ├── dashboard/
│   ├── data/
│   ├── dispatch/        (vacío)
│   ├── eda/
│   ├── etl/
│   ├── evaluation/      (vacío)
│   ├── features/
│   └── models/
│       ├── baselines/   (vacío — solo __init__.py)
│       ├── dl/          (vacío — solo __init__.py)
│       └── ml/          (vacío — solo __init__.py)
├── tests/
└── pyproject.toml
```

### Stack tecnológico

| Categoría | Librerías |
|---|---|
| Datos | pandas ≥2.1, numpy ≥1.26, pyarrow ≥15.0 |
| BD fuente | sqlalchemy ≥2.0, pymysql ≥1.1, mysql-connector-python 9.6 |
| Visualización | matplotlib ≥3.8, seaborn ≥0.13, streamlit ≥1.36, altair ≥5.0 |
| ML clásico | scikit-learn ≥1.4, statsmodels ≥0.14, xgboost ≥2.0 |
| Series temporales | prophet ≥1.1, holidays ≥0.46 (festivos Colombia) |
| DL (opcional) | torch ≥2.2 |
| Cloud (opcional) | boto3, s3fs, sagemaker |
| Dev | pytest, ruff, mypy, pre-commit, jupyter |

---

## 2. MÓDULOS PRINCIPALES

### `src/proyecto_grado/etl/`

| Archivo | Descripción |
|---|---|
| `config.py` | Rutas canónicas del proyecto, inicialización de entorno y directorios |
| `db.py` | Conexión a MySQL Registel; lectura de tablas y extracción incremental |
| `extract.py` | **Bloque 3** — Extracción de despachos desde MySQL o CSV crudo |
| `transforms.py` | **Bloque 4** — Normalización de tipos, limpieza básica, estandarización de columnas |
| `gps.py` | **Bloque 5** — Geocerca, validación de radio GPS, imputación de coordenadas |
| `qc.py` | **Bloque 6** — Flags de calidad (qc_hard_fail / qc_soft_fail / qc_any_flag) |
| `trip_end.py` | **Bloque 7** — Resolución del fin de recorrido: COMPLETO / TRUNCADO / SIN_GPS |
| `model_ready.py` | **Bloques 8-9** — Dataset final con filtros de integridad, versionado y metadatos JSON |
| `utils.py` | Helper `display()` para notebooks/consola |
| `pipeline.py` | **Punto de entrada ETL** — Orquesta Bloques 3→9 secuencialmente |

### `src/proyecto_grado/analytics/`

| Archivo | Descripción |
|---|---|
| `etl_diagnostics.py` | Tablas de diagnóstico post-ETL: retención, missingness antes/después, flags QC, finalization |
| `kpis.py` | KPIs operativos: pasajeros total/promedio, duración, despachos por etapa ETL |
| `plots.py` | Gráficos estándar post-ETL (demanda por ruta, heatmap hora×día) |
| `report.py` | CLI `build_post_etl_report()` — genera CSVs + figuras en `reports/` |

### `src/proyecto_grado/features/`

| Archivo | Descripción |
|---|---|
| `time_series_builder.py` | `TimeSeriesBuilder` — agrega despachos en bins (15/30/60 min), imputa gaps, enriquece con tipo_dia, festivos Colombia, franja_horaria |
| `operational_hours.py` | `OperationalHoursEstimator` — estima horario operativo real por (tipo_dia × ruta × granularidad), genera heatmaps de cobertura |
| `validators.py` | `TimeSeriesValidator` — valida continuidad temporal, valores negativos y cobertura mínima de días |

### `src/proyecto_grado/eda/`

| Archivo | Descripción |
|---|---|
| `temporal_analysis.py` | `TemporalEDA` — 6 análisis: perfil intradía, semanal, mensual+tendencia OLS, ACF/PACF+ADF, atípicos IQR+Z-score, correlación Spearman features |

### `src/proyecto_grado/dashboard/`

| Archivo | Descripción |
|---|---|
| `app.py` | App Streamlit (`dashboard` CLI entry point) |

### `src/proyecto_grado/models/`

Todos los subpaquetes (`baselines/`, `dl/`, `ml/`) contienen **únicamente `__init__.py` vacíos**. Sin implementación.

### Punto de entrada principal

```
src/proyecto_grado/etl/pipeline.py → pipeline.main()
```

Secundarios: `analytics/report.py → main()`, `dashboard/app.py → main()`.

---

## 3. ESQUEMA DE DATOS

### Dataset `model_ready` (105 490 filas, 18 columnas)

*Fuente: `data/processed/model_ready/despachos_model_ready.parquet`*
*Metadatos: `reports/tables/etl/model_ready_metadata_20260503_114750.json`*

| Columna | Tipo | Descripción |
|---|---|---|
| `PK_INTERVALO_DESPACHO` | int | Clave primaria del despacho |
| `PLACA` | str | Identificador del vehículo |
| `FK_RUTA` | int | Ruta (valores: 1, 3) |
| `FECHA_INICIAL` | datetime | Fecha del despacho |
| `HORA_INICIAL_REAL` | datetime | Timestamp de inicio real |
| `HORA_FIN_FINAL` | datetime | Timestamp de fin (real o estimado) |
| `DURACION_MIN_FINAL` | float | Duración del recorrido en minutos |
| `PASAJEROS` | float | Pasajeros transportados (variable objetivo) |
| `DISTANCIA` | float | Distancia recorrida |
| `RECORRIDO_COMPLETO` | bool | Indica recorrido completo vs. truncado |
| `FIN_TIPO` | str | COMPLETO / TRUNCADO_RETORNO / TRUNCADO_INDETERMINADO / TRUNCADO_ABANDONO / SIN_GPS |
| `HORA_FIN_FUENTE` | str | Origen del timestamp de fin |
| `HORA_INICIO_H` | int | Hora de inicio (0–23) |
| `HORA_FIN_H` | int | Hora de fin (0–23) |
| `DIA_SEMANA` | int | Día de semana (0=lunes, 6=domingo) |
| `MES` | int | Mes (1–12) |
| `DIA` | int | Día del mes |
| `MODEL_READY_OK` | bool | Flag de elegibilidad para modelado |

**Distribución DURACION_MIN_FINAL:** media=161 min, p50=159 min, p95=205 min, p99=273 min, max=479 min

**Distribución FIN_TIPO:**
- COMPLETO: 90 993 (86.2 %)
- TRUNCADO_RETORNO: 11 446 (10.8 %)
- TRUNCADO_INDETERMINADO: 1 906 (1.8 %)
- TRUNCADO_ABANDONO: 1 120 (1.1 %)
- SIN_GPS: 25 (0.02 %)

### Serie temporal agregada (`TimeSeriesBuilder` output)

Generada por combinación (ruta × granularidad_min); rutas: [1, 3], granularidades: [15, 30, 60 min].

| Columna | Tipo | Descripción |
|---|---|---|
| `timestamp` | datetime | Inicio del bin temporal |
| `pasajeros_total` | float | **Variable objetivo principal** — suma de pasajeros en el bin |
| `despachos_count` | int | Número de despachos en el bin |
| `pasajeros_promedio` | float | Promedio de pasajeros por despacho en el bin |
| `ocupacion_p95` | float | Percentil 95 de pasajeros en el bin |
| `hora_del_dia` | int | Hora del día (0–23) |
| `dia_semana` | int | Día de semana (0=lunes) |
| `es_fin_semana` | bool | True si sábado o domingo |
| `mes` | int | Mes |
| `semana_anio` | int | Semana ISO del año |
| `trimestre` | int | Trimestre (1–4) |
| `franja_horaria` | str | MADRUGADA / MANANA / MEDIODIA / TARDE / NOCHE |
| `es_festivo` | bool | Festivo Colombia (librería `holidays`) |
| `tipo_dia` | str | LABORAL / SABADO / DOMINGO / FESTIVO / FESTIVO_PUENTE |
| `is_gap` | bool | True si no hubo despachos reales en ese bin |
| `granularidad_min` | int | Granularidad del bin (15/30/60) |
| `FK_RUTA` | int | Ruta |
| `dentro_horario_operativo` | bool | Bin dentro del horario estimado |
| `gap_tipo` | str | operativo / gap_anomalo / fuera_operacion |

### Config `features.yaml`

```yaml
granularidades_min: [15, 30, 60]
franjas_horarias:
  MADRUGADA: [0, 5]
  MANANA:    [6, 11]
  MEDIODIA:  [12, 13]
  TARDE:     [14, 18]
  NOCHE:     [19, 23]
imputacion_gaps: zero
cobertura_minima_dias: 30
rutas: [1, 3]
horario_operativo:
  umbral_actividad: 0.10
  umbral_anomalia: 0.30
  min_dias_muestra: 10
  incluir_festivo_puente: true
```

---

## 4. MÉTRICAS Y KPIs ACTUALES

### KPIs de calidad ETL (`analytics/kpis.py → operational_kpis()`)

Calculados para todas las etapas del pipeline:
- `despachos_raw / qc / end / model_ready` — conteos por etapa
- `retencion_model_ready_pct` — porcentaje de registros que llegan al modelo
- `qc_hard_fail_pct / qc_soft_fail_pct / qc_any_flag_pct`
- `pasajeros_total / pasajeros_promedio`
- `duracion_promedio_min / duracion_p95_min`
- `recorridos_completos / recorridos_completos_pct`

### KPIs de demanda (`analytics/kpis.py`)

- **`demand_by_route()`** → despachos, pasajeros_total, pasajeros_promedio por FK_RUTA
- **`demand_by_hour_weekday()`** → despachos y pasajeros_total por (dia_semana × hora)
- **`duration_by_route()`** → count, mean, median, p95 de DURACION_MIN_FINAL por ruta

### Horario operativo estimado (`features/operational_hours.py`)

`OperationalHoursEstimator` calcula por (tipo_dia × ruta × granularidad_min):

| Métrica | Descripción |
|---|---|
| `hora_inicio_op / hora_fin_op` | Rango horario operativo |
| `duracion_operativa_h` | Horas de servicio |
| `franjas_anomalas_count` | Bins dentro del horario con actividad < 30% |
| `pct_cobertura_dentro_horario` | Fracción de bins activos dentro del horario |

**Resultados clave (ruta 1, granularidad 60 min):**
- LABORAL: 04:00–18:00 (15 h), 1 franja anómala, cobertura 100%
- SABADO: 04:00–18:00 (15 h)
- DOMINGO: 05:00–17:00 (13 h)

### Análisis de gaps (`eda/temporal_analysis.py → calcular_gaps_horario_operativo()`)

Compara gaps dentro del horario operativo vs. vista 24h:

| Granularidad | Ruta | Tipo día | % gaps operativo | % gaps 24h |
|---|---|---|---|---|
| 60 min | 1 | LABORAL | 5.4% | 40.8% |
| 60 min | 1 | SABADO | 7.7% | 42.3% |
| 60 min | 1 | DOMINGO | 20.4% | 56.9% |
| 60 min | 3 | LABORAL | 6.5% | 41.5% |
| 60 min | 3 | DOMINGO | 23.1% | 55.1% |

> Los gaps nocturnos estructurales inflan el % reportado si se usa vista 24h. La columna `pct_gaps_op` es la métrica correcta para análisis de eficiencia.

---

## 5. ESTADO DEL EDA

### Módulos implementados

`eda/temporal_analysis.py` — clase `TemporalEDA` con 6 análisis completos:

1. **`perfil_intraday()`** — media/mediana/p25/p75/p95 por (hora × tipo_dia); identifica horas pico/valle y ratio pico/valle
2. **`perfil_semanal()`** — demanda total/promedio por día; índice de variabilidad (CV)
3. **`perfil_mensual()`** — tendencia OLS diaria; detección de meses atípicos (|d - μ| > 2σ)
4. **`autocorrelacion()`** — ACF, PACF (método ywm), test ADF; lags con |ACF| > 0.3 como candidatos a lookback
5. **`atipicos()`** — IQR global + Z-score por tipo_dia; columna `metodo_deteccion`
6. **`correlacion_features()`** — Spearman entre PASAJEROS y todas las features numéricas

### Reportes ya generados en `reports/`

**Tablas CSV (`reports/tables/eda/`):**
- `dataset_overview.csv`, `retention_summary.csv`, `missing_before_after.csv`
- `qc_flag_summary.csv`, `finalization_summary.csv`
- `operational_kpis.csv`, `demand_by_route.csv`, `demand_by_hour_weekday.csv`, `duration_by_route.csv`
- `temporal_executive_summary.txt` ← resumen ejecutivo textual completo

**Figuras (`reports/figures/eda/`):**
- Curvas intradía por tipo_dia × ruta × granularidad (15 combinaciones × 2 rutas = 30 PNGs)
- Heatmaps demanda hora×día (6 PNGs)
- Boxplots por tipo_dia (6 PNGs)
- Tendencia mensual (2 PNGs)
- ACF/PACF (6 PNGs)

### Hallazgos clave del EDA (temporal_executive_summary.txt)

- **Horas pico LABORAL** — Ruta 1: 05-06h y 14-15h (ratio 4.09×); Ruta 3: 05-06-07h y 15h (ratio 3.40×)
- **Mayor demanda:** Martes en ambas rutas
- **Menor demanda:** Domingo en ambas rutas
- **Tendencia:** DECRECIENTE — Ruta 1: −60 pas/mes; Ruta 3: −52 pas/mes
- **Estacionariedad:** Todas las series son estacionarias (ADF p < 0.0001)
- **Lookback recomendado:** 14 franjas a 60 min (~14 h) para Rutas 1 y 3
- **Atípicos operativos:** Ruta 1 ≤ 1.4%; Ruta 3 ≤ 2.3%
- **Top feature correlacionada con PASAJEROS:** DURACION_MIN_FINAL (ρ = +0.335)

---

## 6. LO QUE FALTA PARA EL BASELINE

### ¿Existe cálculo de CV headway?

**NO.** No hay ninguna función ni script que calcule headway (intervalo entre vehículos consecutivos en una misma ruta) ni su coeficiente de variación (CV). Tampoco existe cálculo de:
- Headway observado vs. programado
- Irregularidad de despacho (bunching)
- Desviación estándar del intervalo entre salidas

El `gaps_horario_operativo.csv` mide ausencia de despachos en bins temporales, pero **no es headway**.

### ¿Existe análisis de desajuste demanda-oferta?

**NO.** No hay módulo que compare:
- Capacidad ofertada (vehículos × aforo) vs. demanda observada (pasajeros)
- Índice de ocupación (load factor) por franja
- Franjas de sobrecarga o subcarga operativa

`ocupacion_p95` en la serie temporal es el p95 de pasajeros por despacho dentro del bin, pero no se compara contra ninguna capacidad nominal.

### ¿Hay scripts de evaluación de modelos iniciados?

**NO.** Los tres subpaquetes de modelos están completamente vacíos:
- `src/proyecto_grado/models/baselines/__init__.py` — vacío
- `src/proyecto_grado/models/ml/__init__.py` — vacío
- `src/proyecto_grado/models/dl/__init__.py` — vacío
- `src/proyecto_grado/evaluation/` — vacío

No existe ningún script de:
- Naive baselines (última observación, promedio histórico, día de la semana)
- Entrenamiento de modelos
- Evaluación con métricas (MAE, RMSE, MAPE)
- Walk-forward validation o backtesting

### Resumen de brechas para llegar al baseline

| Componente | Estado | Ubicación sugerida |
|---|---|---|
| Cálculo de headway observado | ❌ No existe | `analytics/headway.py` |
| CV headway por ruta × franja | ❌ No existe | `analytics/headway.py` |
| Desajuste demanda-oferta (load factor) | ❌ No existe | `analytics/demand_supply.py` |
| Naive baseline (última obs, media histórica) | ❌ No existe | `models/baselines/` |
| Baseline estacional (día de semana + hora) | ❌ No existe | `models/baselines/` |
| Walk-forward cross-validation | ❌ No existe | `evaluation/` |
| Métricas MAE/RMSE/MAPE/SMAPE | ❌ No existe | `evaluation/metrics.py` |
| Pipeline de entrenamiento | ❌ No existe | `models/ml/` o `models/baselines/` |

**Lo que SÍ está listo como input para el baseline:**
- ✅ Dataset model_ready (105 490 registros limpios)
- ✅ Series temporales agregadas en 3 granularidades × 2 rutas (6 Parquets)
- ✅ Features temporales completas (tipo_dia, franja, festivos, is_gap, gap_tipo)
- ✅ Horario operativo estimado (para filtrar a franjas válidas)
- ✅ Lookback recomendado por la autocorrelación (14 lags a 60 min)
- ✅ EDA completo con caracterización de patrones
