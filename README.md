# Proyecto de Grado — Predicción inteligente de la demanda de pasajeros

**Título:** Predicción inteligente de la demanda de pasajeros mediante técnicas de aprendizaje automático para apoyar la optimización del despacho vehicular en la empresa Montebello.

**Autor:** Carlos Alex Macías Perdomo — Código 22500208
**Directora:** Maritza Correa Valencia
**Programa:** Maestría en IA y Ciencia de Datos — Universidad Autónoma de Occidente (UAO)

## Descripción

Implementación de modelos de aprendizaje automático para predecir la demanda de pasajeros y apoyar el despacho vehicular de la empresa Montebello (Cali, Colombia), utilizando datos históricos de APC, GPS y despachos provenientes de Registel.

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

## Estructura del repositorio

```
proyecto_grado/
├── configs/
│   ├── etl.yaml                    # Configuración del pipeline ETL
│   └── features.yaml               # Configuración de features/series temporales
├── data/
│   ├── raw/                        # Datos crudos (despachos_raw_historico.csv)
│   ├── interim/
│   │   ├── gps/                    # Artefactos GPS (despachos_end.parquet)
│   │   └── qc/                     # Resultados QC del ETL
│   └── processed/
│       ├── eda/                    # Artefactos EDA temporal (Parquet por ruta/granularidad)
│       ├── model_ready/            # Dataset final model-ready (CSV + Parquet)
│       ├── time_series/            # Series temporales: ts_ruta{1,3}_g{15,30,60}min.parquet
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
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── extract.py
│   │   ├── gps.py
│   │   ├── model_ready.py
│   │   ├── pipeline.py
│   │   ├── qc.py
│   │   ├── transforms.py
│   │   ├── trip_end.py
│   │   └── utils.py
│   ├── features/                   # Series temporales y horario operativo
│   │   ├── operational_hours.py
│   │   ├── time_series_builder.py
│   │   └── validators.py
│   ├── models/
│   │   ├── baselines/              # SARIMA, Prophet (pendiente)
│   │   ├── ml/                     # Random Forest, XGBoost (pendiente)
│   │   └── dl/                     # LSTM, GRU (pendiente)
│   ├── evaluation/                 # Métricas y comparación (pendiente)
│   ├── dispatch/                   # Módulo de apoyo al despacho (pendiente)
│   └── utils/
└── tests/
    ├── unit/                       # 13 módulos de pruebas unitarias
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

## Flujo de trabajo actual

```powershell
# Ejecutar pipeline ETL (requiere .env con credenciales REGISTEL_DB_*)
make etl

# Construir series temporales (3 granularidades × 2 rutas)
make build-ts

# Estimar horario operativo y regenerar series con gap_tipo
make estimate-op-hours

# Análisis EDA temporal (genera Parquet + figuras en reports/)
make eda-temporal

# Iniciar dashboard Streamlit
make dashboard

# Ejecutar pruebas
make test
make test-eda       # Solo tests EDA temporal
make test-cov       # Con reporte de cobertura
```

## Tecnologías

- **Lenguaje:** Python 3.11+
- **Datos:** pandas, pyarrow, SQLAlchemy, PyMySQL
- **EDA / Stats:** statsmodels, scipy
- **Dashboard:** Streamlit, Plotly
- **ML/DL:** scikit-learn, XGBoost, statsmodels, Prophet *(pendiente)*
- **Calidad:** ruff, mypy, pytest, pre-commit
- **Infraestructura:** Make, Docker, docker-compose

## Licencia

Uso académico — Universidad Autónoma de Occidente, 2025.
