import pandas as pd

from proyecto_grado.etl import transforms


def test_combinar_fecha_hora_crea_datetime_y_marca_invalidos():
    df = pd.DataFrame(
        {
            "FECHA": ["2024-04-16", "2024-04-16", "bad-date"],
            "HORA": ["08:30:00", "sin hora", "09:15:00"],
        }
    )

    result = transforms.combinar_fecha_hora(df, "FECHA", "HORA", "FECHA_HORA")

    assert result.loc[0, "FECHA_HORA"] == pd.Timestamp("2024-04-16 08:30:00")
    assert pd.isna(result.loc[1, "FECHA_HORA"])
    assert pd.isna(result.loc[2, "FECHA_HORA"])


def test_run_block4_normaliza_pasajeros_y_filtra_rutas(capsys):
    df = pd.DataFrame(
        {
            "FECHA_INICIAL": ["2024-04-16", "2024-04-16", "2024-04-16"],
            "HORA_INICIAL_PLAN": ["08:00:00", "09:00:00", "10:00:00"],
            "HORA_INICIAL_REAL": ["08:05:00", "09:05:00", "10:05:00"],
            "FECHA_FINAL": ["2024-04-16", "2024-04-16", "2024-04-16"],
            "HORA_FINAL_PLAN": ["09:00:00", "10:00:00", "11:00:00"],
            "HORA_FINAL_REAL": ["09:10:00", "10:10:00", "11:10:00"],
            "HORA_INICIAL_AUX": ["x", "y", "z"],
            "HORA_FINAL_AUX": ["x", "y", "z"],
            "ALARMAS": ["2", "5", "0"],
            "PASAJEROS": ["10", "3", "7"],
            "FK_RUTA": [1, 3, 99],
        }
    )

    result = transforms.run_block4(df)
    capsys.readouterr()

    assert result["FK_RUTA"].tolist() == [1, 3]
    assert result["PASAJEROS_REALES"].tolist() == [8, 0]
    assert "HORA_INICIAL_AUX" not in result.columns
    assert pd.api.types.is_datetime64_any_dtype(result["HORA_INICIAL_REAL"])
