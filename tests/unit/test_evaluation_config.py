"""Pruebas del contrato de evaluacion comparativa."""

from pathlib import Path

import pytest
import yaml

from proyecto_grado.modeling.evaluation_config import (
    ErrorConfiguracionEvaluacion,
    cargar_configuracion_evaluacion,
)


@pytest.mark.unit
def test_carga_configuracion_comparativa_canonica() -> None:
    config = cargar_configuracion_evaluacion()

    assert config.dataset_version == "freeze_20260823_203700"
    assert config.inicio.isoformat() == "2026-04-02"
    assert config.fin.isoformat() == "2026-06-10"
    assert config.extremos_inclusivos is True
    assert config.rutas == (1, 3)
    assert config.metodo("SARIMA").semanas_entrenamiento == 26
    assert config.metodo("GRU").semanas_entrenamiento == 52
    assert config.metodo("XGBoost").semanas_parada_temprana == 2
    assert config.metodo("Prophet").semanas_parada_temprana is None
    assert config.referencias["Referencia (26s)"].metodo_fuente == "xgboost"
    assert config.referencias["Referencia (52s)"].metodo_fuente == "gru"


@pytest.mark.unit
def test_rechaza_metodo_obligatorio_faltante(tmp_path: Path) -> None:
    ruta_origen = Path("configs/modeling/evaluacion_comparativa.yaml")
    raw = yaml.safe_load(ruta_origen.read_text(encoding="utf-8"))
    raw["metodos_obligatorios"].pop("GRU")
    ruta = tmp_path / "evaluacion_incompleta.yaml"
    ruta.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ErrorConfiguracionEvaluacion, match="metodos_obligatorios"):
        cargar_configuracion_evaluacion(ruta)


@pytest.mark.unit
def test_rechaza_version_en_nombre_distinta(tmp_path: Path) -> None:
    ruta_origen = Path("configs/modeling/evaluacion_comparativa.yaml")
    raw = yaml.safe_load(ruta_origen.read_text(encoding="utf-8"))
    raw["metodos_obligatorios"]["GRU"]["artefacto_predicciones"] = (
        "analisis/salidas/predicciones__gru__freeze_20260822_000000.csv"
    )
    ruta = tmp_path / "evaluacion_version_invalida.yaml"
    ruta.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ErrorConfiguracionEvaluacion, match="version del nombre"):
        cargar_configuracion_evaluacion(ruta)
