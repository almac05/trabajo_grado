"""Pruebas de integración del pipeline ETL sin conexión a base de datos.

Cubre la cadena B4 → B6 → B7 → B8 → B9 usando DataFrames sintéticos y
directorios temporales, sin requerir MySQL ni datos reales.
"""

from pathlib import Path

import pandas as pd
import pytest

import proyecto_grado.etl.model_ready as _model_ready
import proyecto_grado.etl.qc as _qc
import proyecto_grado.etl.trip_end as _trip_end
from proyecto_grado.etl.model_ready import run_block8, run_block9
from proyecto_grado.etl.qc import run_block6, validar_coherencia_operacional_avanzada
from proyecto_grado.etl.transforms import run_block4
from proyecto_grado.etl.trip_end import classify_trip_end_block7, run_block7

# ---------------------------------------------------------------------------
# Fixture compartida
# ---------------------------------------------------------------------------


@pytest.fixture
def despachos_raw():
    """20 despachos sintéticos completos (HORA_FINAL_REAL poblada) más 2 con
    rutas no operativas, imitando la salida del Bloque 3 (extracción MySQL).
    """
    base = pd.Timestamp("2024-04-16 05:30:00")
    rows = []

    # 20 despachos válidos: rutas 1 y 3, duración 90 min, 1 alarma cada uno
    for i in range(20):
        t_ini = base + pd.Timedelta(minutes=30 * i)
        t_fin = t_ini + pd.Timedelta(minutes=90)
        rows.append(
            {
                "PK_INTERVALO_DESPACHO": i + 1,
                "FECHA_INICIAL": t_ini.date().isoformat(),
                "HORA_INICIAL_PLAN": t_ini.strftime("%H:%M:%S"),
                "HORA_INICIAL_REAL": t_ini.strftime("%H:%M:%S"),
                "HORA_INICIAL_AUX": None,
                "FECHA_FINAL": t_fin.date().isoformat(),
                "HORA_FINAL_PLAN": t_fin.strftime("%H:%M:%S"),
                "HORA_FINAL_REAL": t_fin.strftime("%H:%M:%S"),
                "HORA_FINAL_AUX": None,
                "FK_RUTA": 1 if i % 2 == 0 else 3,
                "PASAJEROS": 15 + i,
                "DISTANCIA": 8.5 + i * 0.1,
                "FK_VEHICULO": 100 + i % 5,
                "CONDUCTOR": 200 + i % 3,
                "ESTADO_DESPACHO": 1,
                "PK_INFORMACION_REGISTRADORA": 1000 + i,
                "PLACA": f"ABC{100 + i % 5}",
                "ALARMAS": 1,
            }
        )

    # 2 despachos con rutas no operativas (deben filtrarse en B4)
    for extra_i, ruta in enumerate([2, 4]):
        t = base + pd.Timedelta(hours=12 + extra_i)
        rows.append(
            {
                "PK_INTERVALO_DESPACHO": 100 + extra_i,
                "FECHA_INICIAL": t.date().isoformat(),
                "HORA_INICIAL_PLAN": t.strftime("%H:%M:%S"),
                "HORA_INICIAL_REAL": t.strftime("%H:%M:%S"),
                "HORA_INICIAL_AUX": None,
                "FECHA_FINAL": (t + pd.Timedelta(hours=1)).date().isoformat(),
                "HORA_FINAL_PLAN": (t + pd.Timedelta(hours=1)).strftime("%H:%M:%S"),
                "HORA_FINAL_REAL": (t + pd.Timedelta(hours=1)).strftime("%H:%M:%S"),
                "HORA_FINAL_AUX": None,
                "FK_RUTA": ruta,
                "PASAJEROS": 10,
                "DISTANCIA": 5.0,
                "FK_VEHICULO": 110,
                "CONDUCTOR": 210,
                "ESTADO_DESPACHO": 1,
                "PK_INFORMACION_REGISTRADORA": 2000 + extra_i,
                "PLACA": "XYZ999",
                "ALARMAS": 0,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests de transformación (sin I/O a disco)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_b4_filtra_rutas_y_calcula_pasajeros_reales(despachos_raw):
    """B4 debe eliminar rutas no operativas y calcular PASAJEROS_REALES."""
    df = run_block4(despachos_raw)

    assert set(df["FK_RUTA"].unique()).issubset({1, 3})
    assert len(df) == 20, "Las 2 filas de rutas extra deben eliminarse"
    assert pd.api.types.is_datetime64_any_dtype(df["HORA_INICIAL_REAL"])
    assert pd.api.types.is_datetime64_any_dtype(df["HORA_FINAL_REAL"])
    # PASAJEROS_REALES = PASAJEROS - ALARMAS (todos tienen 1 alarma)
    assert (df["PASAJEROS_REALES"] == df["PASAJEROS"] - df["ALARMAS"]).all()
    assert (df["PASAJEROS_REALES"] >= 0).all()


@pytest.mark.integration
def test_b6_datos_validos_no_generan_hard_fails(despachos_raw):
    """Datos sintéticos bien formados no deben activar ningún hard fail."""
    df4 = run_block4(despachos_raw)

    out, resumen, _, _ = validar_coherencia_operacional_avanzada(
        df4,
        col_pk="PK_INTERVALO_DESPACHO",
        col_placa="PLACA",
        col_ruta="FK_RUTA",
        col_estado="ESTADO_DESPACHO",
        col_hi="HORA_INICIAL_REAL",
        col_hf="HORA_FINAL_REAL",
        col_pasaj="PASAJEROS_REALES",
        col_dist="DISTANCIA",
    )

    assert not out["qc_hard_fail"].any()
    assert (out["duracion_min"] > 0).all()
    n_hard = resumen.loc[resumen["regla_flag"] == "qc_hard_fail", "conteo"].iloc[0]
    assert n_hard == 0


@pytest.mark.integration
def test_b6_detecta_hard_fail_en_fila_invalida(despachos_raw):
    """Una fila con PLACA nula y pasajeros negativos debe activar hard fail."""
    df4 = run_block4(despachos_raw).copy()
    # Corromper la primera fila
    df4.loc[df4.index[0], "PLACA"] = None
    df4.loc[df4.index[0], "PASAJEROS_REALES"] = -5

    out, _, _, _ = validar_coherencia_operacional_avanzada(
        df4,
        col_pk="PK_INTERVALO_DESPACHO",
        col_placa="PLACA",
        col_ruta="FK_RUTA",
        col_estado="ESTADO_DESPACHO",
        col_hi="HORA_INICIAL_REAL",
        col_hf="HORA_FINAL_REAL",
        col_pasaj="PASAJEROS_REALES",
        col_dist="DISTANCIA",
    )

    bad_row = out.loc[out.index[0]]
    assert bool(bad_row["flag_placa_nula"])
    assert bool(bad_row["flag_pasajeros_negativos"])
    assert bool(bad_row["qc_hard_fail"])


@pytest.mark.integration
def test_b7_completos_sin_gps_no_requiere_bd(despachos_raw):
    """Con todos los despachos completos (HF real), B7 no necesita GPS."""
    df4 = run_block4(despachos_raw)

    result = classify_trip_end_block7(df4, con_gps=None, debug=False)

    assert "RECORRIDO_COMPLETO" in result.columns
    assert "FIN_TIPO" in result.columns
    assert "HORA_FIN_FUENTE" in result.columns
    assert (result["RECORRIDO_COMPLETO"] == 1).all()
    assert (result["FIN_TIPO"] == "COMPLETO").all()
    assert (result["HORA_FIN_FUENTE"] == "REAL").all()
    assert not result["PK_INTERVALO_DESPACHO"].duplicated().any()


@pytest.mark.integration
def test_cadena_b4_b6_b7_preserva_filas_y_pks(despachos_raw):
    """La cadena B4→B6(qc)→B7 no debe perder ni duplicar despachos."""
    df4 = run_block4(despachos_raw)

    out_qc, _, _, _ = validar_coherencia_operacional_avanzada(
        df4,
        col_pk="PK_INTERVALO_DESPACHO",
        col_placa="PLACA",
        col_ruta="FK_RUTA",
        col_estado="ESTADO_DESPACHO",
        col_hi="HORA_INICIAL_REAL",
        col_hf="HORA_FINAL_REAL",
        col_pasaj="PASAJEROS_REALES",
        col_dist="DISTANCIA",
    )

    df7 = classify_trip_end_block7(out_qc, con_gps=None, debug=False)

    assert len(df7) == len(df4)
    assert not df7["PK_INTERVALO_DESPACHO"].duplicated().any()
    pks_entrada = set(df4["PK_INTERVALO_DESPACHO"])
    pks_salida = set(df7["PK_INTERVALO_DESPACHO"])
    assert pks_entrada == pks_salida


# ---------------------------------------------------------------------------
# Tests con I/O a disco (monkeypatch de rutas)
# ---------------------------------------------------------------------------


@pytest.fixture
def patched_paths(tmp_path, monkeypatch):
    """Redirige todas las rutas de artefactos ETL a directorios temporales."""
    qc_dir = tmp_path / "qc"
    qc_dir.mkdir()
    qc_reports = tmp_path / "qc_reports"
    qc_reports.mkdir()
    model_dir = tmp_path / "model_ready"
    etl_reports = tmp_path / "etl_reports"

    qc_path = str(qc_dir / "despachos_qc.parquet")
    end_path = str(tmp_path / "despachos_end.parquet")

    monkeypatch.setattr(_qc, "QC_PATH", qc_path)
    monkeypatch.setattr(_qc, "QC_DIR", str(qc_dir))
    monkeypatch.setattr(_qc, "QC_REPORTS_DIR", str(qc_reports))

    monkeypatch.setattr(_trip_end, "QC_PATH", qc_path)
    monkeypatch.setattr(_trip_end, "END_PATH", end_path)

    monkeypatch.setattr(_model_ready, "END_PATH", end_path)
    monkeypatch.setattr(_model_ready, "MODEL_READY_DIR", str(model_dir))
    monkeypatch.setattr(_model_ready, "ETL_REPORTS_DIR", str(etl_reports))

    return {
        "qc_path": qc_path,
        "end_path": end_path,
        "model_dir": model_dir,
        "etl_reports": etl_reports,
        "tmp_path": tmp_path,
    }


@pytest.mark.integration
def test_b8_schema_y_restricciones_sobre_end_path(despachos_raw, patched_paths):
    """B8 debe producir el schema correcto a partir de un END_PATH válido."""
    df4 = run_block4(despachos_raw)
    out_qc, _, _, _ = validar_coherencia_operacional_avanzada(
        df4,
        col_pk="PK_INTERVALO_DESPACHO",
        col_placa="PLACA",
        col_ruta="FK_RUTA",
        col_estado="ESTADO_DESPACHO",
        col_hi="HORA_INICIAL_REAL",
        col_hf="HORA_FINAL_REAL",
        col_pasaj="PASAJEROS_REALES",
        col_dist="DISTANCIA",
    )
    df7 = classify_trip_end_block7(out_qc, con_gps=None, debug=False)
    df7.to_parquet(patched_paths["end_path"], index=False)

    df8 = run_block8()

    required_cols = {
        "PK_INTERVALO_DESPACHO",
        "PLACA",
        "FK_RUTA",
        "HORA_INICIAL_REAL",
        "DURACION_MIN_FINAL",
        "HORA_INICIO_H",
        "DIA_SEMANA",
        "MES",
    }
    assert required_cols.issubset(set(df8.columns))
    assert len(df8) > 0
    assert (df8["DURACION_MIN_FINAL"] > 0).all()
    assert df8["DIA_SEMANA"].between(0, 6).all()
    assert df8["HORA_INICIO_H"].between(0, 23).all()
    assert not df8["PK_INTERVALO_DESPACHO"].duplicated().any()
    assert (patched_paths["model_dir"] / "despachos_model_ready.parquet").exists()


@pytest.mark.integration
def test_pipeline_completo_b4_a_b9_sin_bd(despachos_raw, patched_paths):
    """Cadena completa B4→B6→B7→B8→B9 usando paths temporales y sin MySQL."""
    # B4: transformaciones deterministas
    df4 = run_block4(despachos_raw)
    assert len(df4) == 20

    # B6: QC (escribe QC_PATH en tmp)
    run_block6(df4)
    assert Path(patched_paths["qc_path"]).exists()

    # B7: trip_end (lee QC_PATH, escribe END_PATH; todos son completos → sin GPS)
    run_block7()
    assert Path(patched_paths["end_path"]).exists()

    # B8: model_ready
    df8 = run_block8()
    assert len(df8) > 0
    assert (df8["DURACION_MIN_FINAL"] > 0).all()

    # B9: export freeze + metadata
    run_block9()

    model_dir = patched_paths["model_dir"]
    assert (model_dir / "despachos_model_ready.parquet").exists()

    freeze_files = list(model_dir.glob("*freeze*.parquet"))
    assert len(freeze_files) >= 1

    meta_files = list(patched_paths["etl_reports"].glob("model_ready_metadata_*.json"))
    assert len(meta_files) >= 1

    # Verificaciones de integridad del dataset final
    assert not df8["PK_INTERVALO_DESPACHO"].duplicated().any()
    assert set(df8["FK_RUTA"].unique()).issubset({1, 3})
