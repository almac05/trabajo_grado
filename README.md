# Proyecto de Grado — Predicción inteligente de la demanda de pasajeros

**Título:** Predicción inteligente de la demanda de pasajeros mediante técnicas de aprendizaje automático para apoyar la optimización del despacho vehicular en la empresa Montebello.

**Autor:** Carlos Alex Macías Perdomo — Código 22500208
**Directora:** Maritza Correa Valencia
**Programa:** Maestría en IA y Ciencia de Datos — Universidad Autónoma de Occidente (UAO)

## Descripción
Implementación de modelos de aprendizaje automático (SARIMA, Prophet, Random Forest, XGBoost, LSTM, GRU) para predecir la demanda de pasajeros y apoyar el despacho vehicular de la empresa Montebello (Cali, Colombia), utilizando datos históricos de APC, GPS y despachos provenientes de Registel.

## Estructura del repositorio
```
proyecto_grado/
├── configs/                    # Configuraciones (YAML) para modelos y pipelines
├── data/
│   ├── raw/                    # Datos crudos extraídos de Registel (MySQL)
│   ├── interim/                # Datos en transformación
│   ├── processed/              # Datasets listos para modelado
│   └── external/               # Fuentes externas (clima, calendario)
├── docs/                       # Documentación técnica y metodológica
├── notebooks/
│   ├── 01_eda/                 # Fase 1 — Análisis exploratorio
│   ├── 02_preprocessing/       # Limpieza y features
│   ├── 03_modeling/            # Experimentos de modelado
│   └── 04_evaluation/          # Comparación y validación
├── reports/
│   ├── figures/                # Gráficos generados
│   └── tables/                 # Tablas y métricas
├── scripts/                    # Scripts utilitarios (CLI)
├── src/proyecto_grado/
│   ├── data/                   # Acceso y carga de datos
│   ├── etl/                    # Pipeline ETL (extract/transform/load)
│   ├── features/               # Ingeniería de características
│   ├── models/
│   │   ├── baselines/          # SARIMA, Prophet
│   │   ├── ml/                 # Random Forest, XGBoost
│   │   └── dl/                 # LSTM, GRU, híbridos
│   ├── evaluation/             # Métricas (MAE, RMSE, MAPE) y comparación
│   ├── dispatch/               # Módulo heurístico de apoyo al despacho
│   └── utils/                  # Utilidades compartidas
└── tests/
    ├── unit/
    └── integration/
```

## Fases metodológicas
1. **Caracterización de variables** — extracción, limpieza y EDA sobre datos operativos.
2. **Arquitectura y ETL** — pipeline reproducible Registel (MySQL) → AWS S3/Parquet.
3. **Modelado** — entrenamiento comparativo de modelos predictivos.
4. **Evaluación** — validación con MAE, RMSE, MAPE y análisis de sensibilidad.

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

## Tecnologías
- **Lenguaje:** Python 3.11+
- **Datos:** pandas, pyarrow, SQLAlchemy, PyMySQL
- **ML:** scikit-learn, XGBoost, statsmodels, Prophet
- **DL:** PyTorch / TensorFlow (según modelo)
- **Cloud:** AWS (S3, Glue, SageMaker)
- **Calidad:** ruff, mypy, pytest, pre-commit
- **Orquestación:** Make, Docker, docker-compose

## Licencia
Uso académico — Universidad Autónoma de Occidente, 2025.
