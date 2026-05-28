# Proyecto de Grado — Predicción inteligente de la demanda de pasajeros

**Título:** Predicción inteligente de la demanda de pasajeros mediante técnicas de aprendizaje automático para apoyar la optimización del despacho vehicular en la empresa Montebello.

**Autor:** Carlos Alex Macías Perdomo — Código 22500208
**Directora:** Maritza Correa Valencia
**Programa:** Maestría en IA y Ciencia de Datos — Universidad Autónoma de Occidente (UAO)

## Descripción

Implementación de modelos de aprendizaje automático para predecir la demanda de pasajeros y apoyar el despacho vehicular de la empresa Montebello (Cali, Colombia), utilizando datos históricos de APC, GPS y despachos provenientes de la base de datos operativa Registel.

El pipeline cubre desde la extracción incremental de MySQL, pasando por control de calidad, enriquecimiento GPS, construcción de series temporales e informes EDA, hasta la etapa de modelado (en curso).

## Estado actual del proyecto

| Fase | Módulo | Estado |
|------|--------|--------|
| ETL | `etl/` — Extracción MySQL, normalización, QC, GPS, model-ready | ✅ Implementado |
| ETL Analytics | `analytics/` — Diagnósticos, KPIs y figuras post-ETL | ✅ Implementado |
| Features | `features/` — Series temporales (3 granularidades × 2 rutas), horario operativo | ✅ Implementado |
| EDA temporal | `eda/` — Perfiles intraday/semanal/mensual, ACF/PACF, atípicos | ✅ Implementado |
| Dashboard | `dashboard/` — Streamlit: ETL, series temporales y EDA temporal | ✅ Implementado |
| Modelado | `models/baselines/`, `models/ml/`, `models/dl/` | 🔲 Pendiente |
| Evaluación | `evaluation/` | 🔲 Pendiente |
| Despacho | `dispatch/` | 🔲 Pendiente |

## Contexto de datos

**Fuente:** Base de datos MySQL de Registel — tabla `tbl_intervalo_despacho`.

| Artefacto | Tamaño | Descripción |
|-----------|--------|-------------|
| Raw CSV | 15.4 MB | Despachos históricos crudos |
| Dataset model-ready | 3.3 MB (Parquet) / 14.5 MB (CSV) | ~150 000 despachos tras filtros QC |
| 6 series temporales | ~2.9 MB total | 15/30/60 min × rutas 1 y 3 |
| Artefactos EDA | ~18 Parquet | Perfiles, ACF/PACF, atípicos |
| Figuras PNG | ~50 archivos | Heatmaps, curvas intraday, ACF/PACF |

**Rutas operativas:** 1 y 3 (Cali, Colombia).

**Tipos de día:** `LABORAL`, `SABADO`, `DOMINGO`, `FESTIVO`, `FESTIVO_PUENTE`.

**Franjas horarias:** `MADRUGADA` (0–5 h), `MAÑANA` (6–11 h), `MEDIODÍA` (12–13 h), `TARDE` (14–18 h), `NOCHE` (19–23 h).

**Variables objetivo** generadas por las series temporales:
- `pasajeros_total` — suma de pasajeros en el bin de tiempo
- `despachos_count` — número de despachos en el bin
- `pasajeros_promedio` — promedio de pasajeros por despacho
- `ocupacion_p95` — percentil 95 de ocupación en el bin

## Estructura del repositorio

```
proyecto_grado/
├── configs/
│   ├── etl.yaml                    # Parámetros del pipeline ETL (GPS, QC, trip_end, rutas)
│   └── features.yaml               # Parámetros de features/series temporales
├── data/
│   ├── raw/                        # Datos crudos (despachos_raw_historico.csv — 15.4 MB)
│   ├── interim/
│   │   ├── gps/                    # Artefactos GPS (despachos_end.parquet)
│   │   └── qc/                     # Resultados QC del ETL
│   └── processed/
│       ├── eda/                    # Artefactos EDA temporal (Parquet por ruta/granularidad)
│       ├── model_ready/            # Dataset final model-ready (CSV + Parquet)
│       ├── time_series/            # ts_ruta{1,3}_g{15,30,60}min.parquet
│       └── operational_hours.parquet
├── docs/                           # Documentación técnica (pendiente)
├── notebooks/                      # Notebooks por fase (pendiente)
│   ├── 01_eda/
│   ├── 02_preprocessing/
│   ├── 03_modeling/
│   └── 04_evaluation/
├── reports/
│   ├── figures/eda/                # ~50 figuras PNG (ACF/PACF, heatmaps, intraday, etc.)
│   └── tables/                     # Métricas CSV/JSON del ETL y EDA
├── scripts/
│   ├── build_time_series.py        # Construye 6 series temporales (3 gran. × 2 rutas)
│   ├── estimate_operational_hours.py  # Estima horario operativo real
│   └── run_eda_temporal.py         # Genera artefactos EDA y figuras
├── src/proyecto_grado/
│   ├── analytics/                  # Diagnósticos ETL, KPIs y gráficos post-ETL
│   ├── dashboard/                  # Dashboard Streamlit (app.py)
│   ├── eda/                        # Análisis temporal: TemporalEDA
│   ├── etl/                        # Pipeline ETL completo (Bloques 1–9)
│   │   ├── config.py               # Rutas, constantes y configuración global
│   │   ├── db.py                   # Acceso a MySQL y CSVs
│   │   ├── extract.py              # Extracción incremental desde Registel
│   │   ├── gps.py                  # Geocerca e imputación de HORA_INICIAL_REAL
│   │   ├── model_ready.py          # Construcción del dataset final
│   │   ├── pipeline.py             # Orquestador principal (Bloques 3–9)
│   │   ├── qc.py                   # Control de calidad (hard/soft fails)
│   │   ├── transforms.py           # Transformaciones y normalización
│   │   ├── trip_end.py             # Clasificación del fin de recorrido via GPS
│   │   └── utils.py                # Utilidades del pipeline
│   ├── features/                   # Series temporales y horario operativo
│   │   ├── operational_hours.py    # Estimación empírica del horario operativo real
│   │   ├── time_series_builder.py  # Agregación en bins con enriquecimiento temporal
│   │   └── validators.py           # Validadores de datos
│   ├── models/
│   │   ├── baselines/              # SARIMA, Prophet (pendiente)
│   │   ├── ml/                     # Random Forest, XGBoost (pendiente)
│   │   └── dl/                     # LSTM, GRU (pendiente)
│   ├── evaluation/                 # Métricas y comparación de modelos (pendiente)
│   ├── dispatch/                   # Módulo de apoyo al despacho (pendiente)
│   └── utils/
└── tests/
    ├── unit/                       # 14 módulos de pruebas unitarias
    └── integration/                # Prueba de integración del pipeline ETL
```

## Inicio rápido

```powershell
# 1) Crear entorno virtual
make venv
. .venv/Scripts/activate

# 2) Instalar dependencias de desarrollo
make dev

# 3) Ver todos los targets disponibles
make help
```

## Flujo de trabajo

```powershell
# Ejecutar pipeline ETL completo (requiere .env con credenciales REGISTEL_DB_*)
make etl

# Generar diagnósticos, KPIs y figuras post-ETL
make post-etl-report

# Construir series temporales (3 granularidades × 2 rutas)
make build-ts

# Estimar horario operativo y regenerar series con gap_tipo
make estimate-op-hours

# Análisis EDA temporal (genera Parquet + figuras en reports/)
make eda-temporal

# Iniciar dashboard Streamlit
make dashboard

# --- Calidad de código ---
make lint          # Linting con ruff
make format        # Formateo con ruff
make typecheck     # Verificación de tipos con mypy

# --- Pruebas ---
make test          # Suite completa
make test-eda      # Solo tests del módulo EDA temporal
make test-cov      # Con reporte de cobertura HTML
```

## Pipeline ETL — Bloques 1–9

El pipeline corre como proceso monolítico orquestado por `pipeline.py`:

| Bloque | Módulo | Descripción |
|--------|--------|-------------|
| 3 | `extract.py` | Extracción incremental desde MySQL (Registel) |
| 4 | `transforms.py` | Normalización temporal, cálculo de duraciones, filtrado de rutas |
| 5 | `gps.py` | Geocerca (radio 700 m) e imputación de `HORA_INICIAL_REAL` |
| 6 | `qc.py` | Control de calidad: hard fails (duraciones/pasajeros absurdos) y soft fails (percentiles) |
| 7 | `trip_end.py` | Clasificación del fin de recorrido via telemetría GPS |
| 8 | `model_ready.py` | Construcción del dataset final con flag `MODEL_READY_OK` |
| 9 | `pipeline.py` | Exportación Parquet/CSV y generación de metadatos JSON |

**Configuración:** `configs/etl.yaml` — rutas operativas, coordenadas GPS, umbrales QC, parámetros de trip_end.

## Tecnologías

- **Lenguaje:** Python 3.11+
- **Datos & ETL:** pandas, pyarrow, SQLAlchemy, PyMySQL, mysql-connector-python
- **EDA / Stats:** statsmodels, scipy, holidays (festivos Colombia)
- **Dashboard:** Streamlit, Plotly, Altair
- **ML/DL (pendiente):** scikit-learn, XGBoost, Prophet, statsmodels (SARIMA), torch (LSTM/GRU)
- **Calidad de código:** ruff (lint + format), mypy, pytest, pre-commit
- **Infraestructura:** Make, Docker, docker-compose

## Variables de entorno

Copiar `.env.example` a `.env` y completar con las credenciales de la base de datos Registel:

```
REGISTEL_DB_HOST=...
REGISTEL_DB_PORT=3306
REGISTEL_DB_NAME=...
REGISTEL_DB_USER=...
REGISTEL_DB_PASSWORD=...
```

El archivo `.env` está en `.gitignore` y nunca debe subirse al repositorio.

## Docker

```powershell
make docker-build   # Construye la imagen (multi-stage, Python 3.11-slim)
make docker-up      # Levanta los servicios
make docker-etl     # Ejecuta el pipeline ETL dentro del contenedor
make docker-shell   # Abre una shell interactiva en el contenedor
make docker-down    # Detiene los servicios
```

## Licencia

Uso académico — Universidad Autónoma de Occidente, 2026.
