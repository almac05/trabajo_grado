import datetime as dt

import pandas as pd

from proyecto_grado.etl import qc


def test_join_reasons_y_fix_object_dates_for_parquet():
    row = pd.Series({"flag_a": True, "flag_b": False, "flag_c": True})
    df = pd.DataFrame(
        {
            "fecha": [dt.date(2024, 4, 16), None],
            "texto": ["2024-04-16", "sin convertir"],
        }
    )

    fixed = qc._fix_object_dates_for_parquet(df)

    assert qc._join_reasons(row, ["flag_a", "flag_b", "flag_c"]) == "flag_a,flag_c"
    assert pd.api.types.is_datetime64_any_dtype(fixed["fecha"])
    assert not pd.api.types.is_datetime64_any_dtype(fixed["texto"])


def test_validar_coherencia_operacional_detecta_hard_fails():
    df = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2, 3, 3],
            "PLACA": ["ABC123", "", "XYZ789", "QWE456"],
            "FK_RUTA": [1, 1, 3, 3],
            "ESTADO_DESPACHO": ["OK", "OK", "OK", "OK"],
            "HORA_INICIAL_REAL": [
                "2024-04-16 08:00:00",
                None,
                "2024-04-16 10:00:00",
                "2024-04-16 11:00:00",
            ],
            "HORA_FINAL_REAL": [
                "2024-04-16 09:00:00",
                "2024-04-16 09:30:00",
                "2024-04-16 09:30:00",
                None,
            ],
            "PASAJEROS": [10, -1, 20, 15],
            "DISTANCIA": [12.5, -5, 8, 9],
        }
    )
    cfg = {
        **qc.CFG,
        "duracion_pctl_soft": 100.0,
        "pasajeros_pctl_soft": 100.0,
    }

    out, resumen, top_vehiculos, top_rutas = qc.validar_coherencia_operacional_avanzada(
        df,
        col_pk="PK_INTERVALO_DESPACHO",
        col_placa="PLACA",
        col_ruta="FK_RUTA",
        col_estado="ESTADO_DESPACHO",
        col_hi="HORA_INICIAL_REAL",
        col_hf="HORA_FINAL_REAL",
        col_pasaj="PASAJEROS",
        col_dist="DISTANCIA",
        cfg=cfg,
    )

    assert bool(out.loc[0, "qc_hard_fail"]) is False
    assert bool(out.loc[1, "flag_placa_nula"]) is True
    assert bool(out.loc[1, "flag_hi_nula"]) is True
    assert bool(out.loc[1, "flag_pasajeros_negativos"]) is True
    assert bool(out.loc[1, "flag_distancia_negativa"]) is True
    assert bool(out.loc[2, "flag_horas_invertidas"]) is True
    assert bool(out.loc[2, "flag_duracion_negativa"]) is True
    assert bool(out.loc[3, "flag_pk_duplicada"]) is True
    assert bool(out.loc[3, "flag_hf_nula"]) is True
    assert int(out["qc_hard_fail"].sum()) == 3
    assert resumen.loc[resumen["regla_flag"] == "qc_hard_fail", "conteo"].iloc[0] == 3
    assert top_vehiculos is not None
    assert top_rutas is not None
