import pandas as pd
import pytest

from proyecto_grado.etl import gps


def test_haversine_misma_coordenada_da_cero():
    distancia = gps.haversine_m(3.4516, -76.5320, 3.4516, -76.5320)

    assert distancia == pytest.approx(0.0)


def test_normalizar_latlon_limpia_comas_invalidos_y_fuera_de_rango():
    df = pd.DataFrame(
        {
            "latitud": ["3,4516", "91", "abc", "4.0"],
            "longitud": ["-76,5320", "-76.5", "-76.5", "181"],
        }
    )

    result = gps.normalizar_latlon(df)

    assert len(result) == 1
    assert result.iloc[0]["latitud"] == pytest.approx(3.4516)
    assert result.iloc[0]["longitud"] == pytest.approx(-76.5320)
