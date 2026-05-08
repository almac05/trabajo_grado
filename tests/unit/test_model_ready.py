import shutil
from pathlib import Path

import pandas as pd
import pytest

from proyecto_grado.etl import model_ready


@pytest.fixture
def workspace_tmp_dir():
    path = Path("build") / "pytest_tmp" / "test_model_ready"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_run_block8_genera_model_ready_en_directorio_temporal(workspace_tmp_dir, monkeypatch):
    end_path = workspace_tmp_dir / "despachos_end.parquet"
    model_ready_dir = workspace_tmp_dir / "model_ready"
    model_ready_dir.mkdir()

    df = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2, 3],
            "PLACA": ["ABC123", "DEF456", "GHI789"],
            "FK_RUTA": [1, 3, 1],
            "FECHA_INICIAL": ["2024-04-16", "2024-04-16", "2024-04-16"],
            "HORA_INICIAL_REAL": [
                "2024-04-16 08:00:00",
                "2024-04-16 09:00:00",
                "2024-04-16 10:00:00",
            ],
            "HORA_FINAL_REAL": [pd.NaT, pd.NaT, pd.NaT],
            "HORA_FIN_ESTIMADA": [
                "2024-04-16 09:00:00",
                "2024-04-16 10:00:00",
                "2024-04-16 10:03:00",
            ],
            "PASAJEROS": [20, 30, 10],
            "DISTANCIA": [12.0, 13.0, 4.0],
            "RECORRIDO_COMPLETO": [0, 0, 0],
            "FIN_TIPO": ["TRUNCADO_RETORNO", "TRUNCADO_RETORNO", "TRUNCADO_RETORNO"],
            "HORA_FIN_FUENTE": ["GPS_ESTIMADA", "GPS_ESTIMADA", "GPS_ESTIMADA"],
            "qc_hard_fail": [False, True, False],
        }
    )
    df.to_parquet(end_path, index=False)

    monkeypatch.setattr(model_ready, "END_PATH", str(end_path))
    monkeypatch.setattr(model_ready, "MODEL_READY_DIR", str(model_ready_dir))
    monkeypatch.setattr(model_ready, "inicializar_entorno", lambda **kwargs: None)
    monkeypatch.setattr(model_ready, "display", lambda obj: None)

    result = model_ready.run_block8()

    assert result["PK_INTERVALO_DESPACHO"].tolist() == [1]
    assert result.loc[result.index[0], "DURACION_MIN_FINAL"] == pytest.approx(60.0)
    assert (model_ready_dir / "despachos_model_ready.parquet").exists()
    assert (model_ready_dir / "despachos_model_ready.csv").exists()
