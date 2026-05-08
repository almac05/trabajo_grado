import pandas as pd

from proyecto_grado.etl import trip_end


def test_classify_trip_end_from_gps_signals_sin_datos():
    hora_fin, fin_tipo = trip_end.classify_trip_end_from_gps_signals(pd.DataFrame())

    assert hora_fin is None
    assert fin_tipo == "SIN_GPS_POST_INICIO"


def test_classify_trip_end_from_gps_signals_detecta_abandono():
    gps = pd.DataFrame(
        {
            "fecha_gps": pd.date_range("2024-04-16 08:00:00", periods=4, freq="5min"),
            "velocidad": [2.0, 1.0, 0.0, 1.5],
        }
    )

    hora_fin, fin_tipo = trip_end.classify_trip_end_from_gps_signals(gps)

    assert hora_fin == pd.Timestamp("2024-04-16 08:15:00")
    assert fin_tipo == "TRUNCADO_ABANDONO"


def test_classify_trip_end_from_gps_signals_detecta_retorno():
    gps = pd.DataFrame(
        {
            "fecha_gps": pd.date_range("2024-04-16 08:00:00", periods=3, freq="5min"),
            "velocidad": [15.0, 16.0, 18.0],
        }
    )

    hora_fin, fin_tipo = trip_end.classify_trip_end_from_gps_signals(gps)

    assert hora_fin == pd.Timestamp("2024-04-16 08:10:00")
    assert fin_tipo == "TRUNCADO_RETORNO"


def test_classify_trip_end_from_gps_signals_usa_mensaje_apagado():
    gps = pd.DataFrame(
        {
            "fecha_gps": pd.date_range("2024-04-16 08:00:00", periods=4, freq="5min"),
            "velocidad": [8.0, 8.0, 8.0, 8.0],
            "msg": ["", "", "", "M\u00f3vil Apagado"],
        }
    )

    _, fin_tipo = trip_end.classify_trip_end_from_gps_signals(
        gps,
        pct_baja=0.3,
        w_msg=0.35,
    )

    assert fin_tipo == "TRUNCADO_ABANDONO"


def test_apply_final_postprocessing_adjustments_completo_real_tiene_prioridad():
    df = pd.DataFrame(
        {
            "HORA_FINAL_REAL": [pd.Timestamp("2024-04-16 09:00:00"), pd.NaT],
            "RECORRIDO_COMPLETO": [0, 0],
            "HORA_FIN_ESTIMADA": [pd.Timestamp("2024-04-16 08:45:00"), pd.NaT],
            "FIN_TIPO": ["TRUNCADO_RETORNO", None],
            "HORA_FIN_FUENTE": ["GPS_ESTIMADA", None],
        }
    )

    result = trip_end.apply_final_postprocessing_adjustments(df)

    assert result.loc[0, "RECORRIDO_COMPLETO"] == 1
    assert result.loc[0, "HORA_FIN_ESTIMADA"] == pd.Timestamp("2024-04-16 09:00:00")
    assert result.loc[0, "FIN_TIPO"] == "COMPLETO"
    assert result.loc[0, "HORA_FIN_FUENTE"] == "REAL"
    assert pd.isna(result.loc[1, "HORA_FIN_ESTIMADA"])


def test_merge_block7_results_fusiona_truncados_y_respeta_final_real():
    base = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2],
            "HORA_FINAL_REAL": [pd.Timestamp("2024-04-16 09:00:00"), pd.NaT],
            "RECORRIDO_COMPLETO": [0, None],
            "HORA_FIN_ESTIMADA": [pd.Timestamp("2024-04-16 08:30:00"), pd.NaT],
            "FIN_TIPO": ["TRUNCADO_RETORNO", None],
            "HORA_FIN_FUENTE": ["GPS_ESTIMADA", None],
        }
    )
    updates = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2],
            "RECORRIDO_COMPLETO": [0, 0],
            "HORA_FIN_ESTIMADA": [
                pd.Timestamp("2024-04-16 09:30:00"),
                pd.Timestamp("2024-04-16 11:00:00"),
            ],
            "FIN_TIPO": ["TRUNCADO_ABANDONO", "TRUNCADO_RETORNO"],
            "HORA_FIN_FUENTE": ["GPS_ESTIMADA", "GPS_ESTIMADA"],
        }
    )

    result = trip_end.merge_block7_results(base, updates)

    assert result.loc[0, "RECORRIDO_COMPLETO"] == 1
    assert result.loc[0, "HORA_FIN_ESTIMADA"] == pd.Timestamp("2024-04-16 09:00:00")
    assert result.loc[0, "FIN_TIPO"] == "COMPLETO"
    assert result.loc[1, "RECORRIDO_COMPLETO"] == 0
    assert result.loc[1, "HORA_FIN_ESTIMADA"] == pd.Timestamp("2024-04-16 11:00:00")
    assert result.loc[1, "FIN_TIPO"] == "TRUNCADO_RETORNO"
