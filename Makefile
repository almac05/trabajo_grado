# =============================================================================
# Makefile - Proyecto de Grado
# Predicción inteligente de demanda de pasajeros - Empresa Montebello
# =============================================================================

# --- Configuracion general ---
BASE_PYTHON   ?= python
BASE_PIP      ?= pip
PACKAGE       := proyecto_grado
SRC_DIR       := src/$(PACKAGE)
TESTS_DIR     := tests
NOTEBOOKS_DIR := notebooks
VENV          := .venv

# Detectar activador de venv segun SO
ifeq ($(OS),Windows_NT)
	VENV_BIN       := .\.venv\Scripts
	ACTIVATE       := $(VENV_BIN)/activate
	RM_RF          := powershell -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	VENV_PYTHON    := $(VENV_BIN)\python.exe
	VENV_PIP       := $(VENV_BIN)\pip.exe
	VENV_PRECOMMIT := $(VENV_BIN)\pre-commit.exe
	PY_UTF8_RUN    := set PYTHONIOENCODING=utf-8&&
else
	VENV_BIN       := $(VENV)/bin
	ACTIVATE       := $(VENV_BIN)/activate
	RM_RF          := rm -rf
	VENV_PYTHON    := $(VENV_BIN)/python
	VENV_PIP       := $(VENV_BIN)/pip
	VENV_PRECOMMIT := $(VENV_BIN)/pre-commit
	PY_UTF8_RUN    := PYTHONIOENCODING=utf-8
endif

ifeq ($(wildcard $(VENV_PYTHON)),)
	PYTHON := $(BASE_PYTHON)
	PIP    := $(BASE_PIP)
else
	PYTHON := $(VENV_PYTHON)
	PIP    := $(VENV_PIP)
endif

.DEFAULT_GOAL := help
.PHONY: help venv install dev lint format typecheck test test-eda test-cov \
        clean clean-pyc clean-build clean-cache \
        etl etl-dry-run etl-clean \
        build-ts build-ts-ruta1 build-ts-ruta3 estimate-op-hours \
        eda-temporal eda-clean \
        docker-build docker-up docker-down docker-logs docker-ps docker-config docker-shell docker-etl \
        post-etl-report dashboard \
        precommit-install precommit-run \
        freeze

# =============================================================================
# Ayuda
# =============================================================================
help:  ## Muestra esta ayuda
	@echo "Proyecto de Grado - Prediccion de demanda de pasajeros (Montebello)"
	@echo ""
	@echo "Uso: make <target>"
	@echo ""
	@echo "Targets disponibles:"
	@$(PYTHON) -c "import re,sys; [print(f'  {m.group(1):<22}{m.group(2)}') for l in open('Makefile',encoding='utf-8') for m in [re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', l)] if m]"

# =============================================================================
# Entorno y dependencias
# =============================================================================
venv:  ## Crea el entorno virtual en .venv
	$(PYTHON) -m venv $(VENV)
	@echo "Entorno creado. Activa con: . $(ACTIVATE)"

install:  ## Instala dependencias de produccion
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .

dev:  ## Instala dependencias de desarrollo + pre-commit
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"
	$(VENV_PRECOMMIT) install

freeze:  ## Congela dependencias actuales en requirements.lock
	$(PIP) freeze > requirements.lock

# =============================================================================
# Calidad de codigo
# =============================================================================
lint:  ## Ejecuta linters (ruff)
	ruff check $(SRC_DIR) $(TESTS_DIR)

format:  ## Formatea el codigo con ruff
	ruff check --fix $(SRC_DIR) $(TESTS_DIR)
	ruff format $(SRC_DIR) $(TESTS_DIR)

typecheck:  ## Verificacion estatica de tipos con mypy
	mypy $(SRC_DIR)

precommit-install:  ## Instala los git hooks de pre-commit
	$(VENV_PRECOMMIT) install

precommit-run:  ## Ejecuta todos los hooks de pre-commit sobre el repo
	$(VENV_PRECOMMIT) run --all-files

# =============================================================================
# Tests
# =============================================================================
test:  ## Ejecuta la suite de pruebas completa
	$(PYTHON) -m pytest $(TESTS_DIR) -p no:cacheprovider

test-eda:  ## Ejecuta solo los tests del modulo EDA temporal
	$(PYTHON) -m pytest $(TESTS_DIR)/unit/test_temporal_eda.py -v -p no:cacheprovider

test-cov:  ## Ejecuta pruebas con reporte de cobertura
	$(PYTHON) -m pytest $(TESTS_DIR) -p no:cacheprovider --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

# =============================================================================
# Fase 1-2: Pipeline ETL (Registel MySQL -> data/ + reports/tables/)
# =============================================================================
# El pipeline es un script monolitico que cubre Bloques 1-9:
#   1) Extraccion incremental desde MySQL (Registel)
#   2) Normalizacion temporal y filtrado de rutas
#   3) Enriquecimiento con GPS (imputacion de HORA_INICIAL_REAL)
#   4) QC (hard/soft fails) y exports a data/interim/qc
#   5) Inferencia de fin de recorrido via telemetria GPS
#   6) Construccion del dataset model-ready + metadatos
# Requiere un .env con las credenciales REGISTEL_DB_* (ver .env.example).

etl:  ## Ejecuta el pipeline ETL completo (pipeline.py, Bloques 1-9)
	$(PY_UTF8_RUN) $(PYTHON) -m $(PACKAGE).etl.pipeline

etl-dry-run:  ## Verifica sintaxis e imports del pipeline sin ejecutarlo
	$(PYTHON) -c "import ast, pathlib; ast.parse(pathlib.Path('$(SRC_DIR)/etl/pipeline.py').read_text(encoding='utf-8')); print('OK: pipeline.py sintaxis valida')"

etl-clean:  ## Borra artefactos intermedios del ETL (data/interim y reports/tables)
	$(RM_RF) data/interim/batches_parquet
	$(RM_RF) data/interim/qc
	$(RM_RF) data/interim/gps
	$(RM_RF) reports/tables/qc
	$(RM_RF) reports/tables/etl

# =============================================================================
# Fase 2: Serie temporal agregada (features)
# =============================================================================
estimate-op-hours:  ## Estima el horario operativo real y regenera las 6 series con gap_tipo
	$(PY_UTF8_RUN) $(PYTHON) scripts/estimate_operational_hours.py

build-ts:  ## Construye 6 series temporales: 3 granularidades x 2 rutas
	$(PY_UTF8_RUN) $(PYTHON) scripts/build_time_series.py

build-ts-ruta1:  ## Construye 3 series temporales para ruta 1 (15/30/60 min)
	$(PY_UTF8_RUN) $(PYTHON) scripts/build_time_series.py --ruta 1

build-ts-ruta3:  ## Construye 3 series temporales para ruta 3 (15/30/60 min)
	$(PY_UTF8_RUN) $(PYTHON) scripts/build_time_series.py --ruta 3

# =============================================================================
# Fase 1: Analisis exploratorio de datos (EDA)
# =============================================================================
eda-temporal:  ## EDA temporal: perfil intraday, ACF/PACF, atipicos y tendencia sobre series
	$(PY_UTF8_RUN) $(PYTHON) scripts/run_eda_temporal.py

eda-clean:  ## Borra artefactos del EDA temporal (data/processed/eda/ y reports/figures/eda/)
	$(RM_RF) data/processed/eda
	$(RM_RF) reports/figures/eda

# =============================================================================
# Fase 3-4: Entrenamiento y evaluacion (pendiente de implementacion)
# =============================================================================
# train-baseline, train-ml, train-dl, evaluate, report
# Los modulos models/ y evaluation/ son stubs. Targets disponibles
# cuando se implementen los modulos correspondientes.

# =============================================================================
# Docker
# =============================================================================
docker-config:  ## Valida la configuracion de docker-compose (sin ejecutar)
	docker compose config --quiet && echo "OK: docker-compose.yml valido"

docker-build:  ## Construye la imagen Docker
	docker build -t $(PACKAGE):latest .

docker-up:  ## Levanta los servicios con docker compose
	docker compose up -d --build

docker-down:  ## Detiene los servicios y elimina volumenes anonimos
	docker compose down

docker-ps:  ## Lista los contenedores del proyecto
	docker compose ps

docker-logs:  ## Muestra logs de los contenedores en seguimiento
	docker compose logs -f

docker-shell:  ## Abre una shell interactiva en el contenedor app
	docker compose run --rm app bash

docker-etl:  ## Ejecuta el pipeline ETL dentro del contenedor
	docker compose run --rm app python -m $(PACKAGE).etl.pipeline

post-etl-report:  ## Genera diagnosticos, KPIs y figuras post-ETL
	$(PYTHON) -m $(PACKAGE).analytics.report

dashboard: ## Inicia el dashboard de Streamlit para visualización de resultados
	$(PY_UTF8_RUN) $(PYTHON) -c "from $(PACKAGE).dashboard.app import main; main()"

# =============================================================================
# Limpieza
# =============================================================================
clean: clean-pyc clean-build clean-cache  ## Limpia todos los artefactos

clean-pyc:  ## Elimina archivos .pyc y __pycache__
	$(RM_RF) **/__pycache__
	$(RM_RF) **/*.pyc

clean-build:  ## Elimina artefactos de build
	$(RM_RF) build
	$(RM_RF) dist
	$(RM_RF) *.egg-info
	$(RM_RF) src/*.egg-info

clean-cache:  ## Elimina caches de herramientas
	$(RM_RF) .pytest_cache
	$(RM_RF) .ruff_cache
	$(RM_RF) .mypy_cache
	$(RM_RF) htmlcov
	$(RM_RF) .coverage
