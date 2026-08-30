"""Pruebas de las validaciones del agregador comparativo."""

import numpy as np
import pandas as pd
import pytest

from proyecto_grado.modeling.evaluation_aggregation import (
    ErrorValidacionProcedencia,
    calcular_metricas,
    construir_fuentes,
    validar_claves_unicas,
    validar_version_dataset,
)
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion


@pytest.mark.unit
def test_construye_seis_metodos_y_dos_referencias() -> None:
    config = cargar_configuracion_evaluacion()
    fuentes = construir_fuentes(config)

    assert [fuente.nombre for fuente in fuentes] == [
        "SARIMA",
        "Prophet",
        "XGBoost",
        "LSTM",
        "GRU",
        "CNN-LSTM",
        "Referencia (26s)",
        "Referencia (52s)",
    ]
    assert sum(fuente.es_referencia for fuente in fuentes) == 2


@pytest.mark.unit
def test_rechaza_claves_duplicadas_por_franja() -> None:
    datos = pd.DataFrame(
        {
            "route": [1, 1],
            "dia_op": ["2026-04-02", "2026-04-02"],
            "hora": ["05:00", "05:00"],
        }
    )

    with pytest.raises(ErrorValidacionProcedencia, match="claves duplicadas"):
        validar_claves_unicas(datos, "duplicado.csv")


@pytest.mark.unit
def test_metricas_conservan_definiciones_vigentes() -> None:
    real = np.array([10.0, 20.0])
    pred = np.array([12.0, 16.0])

    resultado = calcular_metricas(real, pred, umbral_mape=10)

    assert resultado["n"] == 2
    assert resultado["mae"] == pytest.approx(3.0)
    assert resultado["rmse"] == pytest.approx(np.sqrt(10.0))
    assert resultado["wape"] == pytest.approx(20.0)
    assert resultado["sesgo"] == pytest.approx(-1.0)
    assert resultado["mape_parcial"] == pytest.approx(20.0)


@pytest.mark.unit
def test_version_interna_del_dataset_coincide() -> None:
    config = cargar_configuracion_evaluacion()

    hash_dataset, fecha_ns = validar_version_dataset(config)

    assert len(hash_dataset) == 64
    assert fecha_ns > 0
