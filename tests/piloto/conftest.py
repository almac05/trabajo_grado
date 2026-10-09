"""Utilidades comunes de las pruebas de la piloto."""

import pytest

from proyecto_grado.modeling.config import PROJECT_ROOT

SEMILLA = PROJECT_ROOT / "data" / "actualizacion_20261004"
SEMILLA_CRUDO = SEMILLA / "raw" / "despachos_raw_historico.csv"
SEMILLA_APTO = (
    SEMILLA / "processed" / "model_ready" / "despachos_model_ready_freeze_20261005_011520.parquet"
)
SEMILLA_FIN = SEMILLA / "interim" / "gps" / "despachos_end.parquet"
SEMILLA_DATASET = (
    SEMILLA
    / "processed"
    / "modeling"
    / "modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
)
SEMILLA_OBJETIVOS = SEMILLA / "targets.yaml"
HORARIO_OPERATIVO = PROJECT_ROOT / "data" / "processed" / "operational_hours.parquet"

requiere_semilla = pytest.mark.skipif(
    not (SEMILLA_CRUDO.exists() and SEMILLA_APTO.exists() and HORARIO_OPERATIVO.exists()),
    reason="Requiere los datos locales de data/actualizacion_20261004/ (no versionados).",
)
requiere_horario = pytest.mark.skipif(
    not HORARIO_OPERATIVO.exists(), reason="Requiere data/processed/operational_hours.parquet."
)
