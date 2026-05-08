# syntax=docker/dockerfile:1.7
# =============================================================================
# Dockerfile multi-stage para el pipeline ETL de Montebello
# Stage 1: builder  -> instala dependencias y wheels
# Stage 2: runtime  -> imagen minima con el codigo y sus dependencias
# =============================================================================

ARG PYTHON_VERSION=3.11

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias de sistema para compilar wheels (prophet, pyarrow, mysql-connector, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        curl \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalamos dependencias Python primero (layer cache)
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip && \
    pip install --prefix=/install .

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/usr/local/bin:$PATH

# Dependencias de runtime minimas (libs para mysql/pyarrow)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder /install /usr/local

# Copiar el codigo fuente
COPY --chown=app:app src/ ./src/
COPY --chown=app:app pyproject.toml README.md ./

# Directorios de datos (se montan como volumenes en docker-compose)
RUN mkdir -p /app/data/raw /app/data/interim /app/data/processed \
             /app/reports/tables /app/configs \
    && chown -R app:app /app

USER app

# Comando por defecto: ejecutar el pipeline ETL completo
CMD ["python", "-m", "proyecto_grado.etl.pipeline"]
