import pandas as pd
import pytest

from proyecto_grado.analytics.etl_diagnostics import (
    build_etl_diagnostics,
    dataset_overview,
    finalization_summary,
    missing_before_after,
    qc_flag_summary,
    retention_summary,
)
from proyecto_grado.analytics.kpis import (
    build_kpi_tables,
    demand_by_hour_weekday,
    demand_by_route,
    duration_by_route,
    operational_kpis,
)


@pytest.fixture
def analytics_datasets():
    raw = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2, 3],
            "PLACA": ["ABC123", None, "XYZ789"],
            "FK_RUTA": [1, 3, 1],
            "HORA_INICIAL_REAL": ["2024-04-16 08:00:00", None, "2024-04-16 10:00:00"],
            "HORA_FINAL_REAL": ["2024-04-16 09:00:00", None, "2024-04-16 11:00:00"],
            "PASAJEROS": [10, 20, 30],
            "DISTANCIA": [12.0, 14.0, 13.0],
        }
    )
    qc = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2, 3],
            "qc_hard_fail": [False, True, False],
            "qc_soft_fail": [False, False, True],
            "qc_any_flag": [False, True, True],
            "flag_hi_nula": [False, True, False],
        }
    )
    end = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2, 3],
            "FIN_TIPO": ["COMPLETO", "TRUNCADO_RETORNO", "COMPLETO"],
            "RECORRIDO_COMPLETO": [1, 0, 1],
        }
    )
    model_ready = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 3],
            "PLACA": ["ABC123", "XYZ789"],
            "FK_RUTA": [1, 1],
            "HORA_INICIAL_REAL": ["2024-04-16 08:00:00", "2024-04-16 10:00:00"],
            "HORA_FIN_FINAL": ["2024-04-16 09:00:00", "2024-04-16 11:00:00"],
            "PASAJEROS": [10, 30],
            "DISTANCIA": [12.0, 13.0],
            "DURACION_MIN_FINAL": [60.0, 60.0],
        }
    )
    return {"raw": raw, "qc": qc, "end": end, "model_ready": model_ready}


def test_build_etl_diagnostics_genera_tablas_esperadas(analytics_datasets):
    tables = build_etl_diagnostics(analytics_datasets)

    assert set(tables) == {
        "dataset_overview",
        "retention_summary",
        "missing_before_after",
        "qc_flag_summary",
        "finalization_summary",
    }
    assert tables["retention_summary"].loc[0, "retention_pct"] == pytest.approx(66.6666667)


def test_dataset_overview_y_retencion(analytics_datasets):
    overview = dataset_overview(analytics_datasets)
    retention = retention_summary(analytics_datasets)

    assert overview.loc[overview["stage"] == "raw", "rows"].iloc[0] == 3
    assert overview.loc[overview["stage"] == "model_ready", "columns"].iloc[0] == 8
    assert retention.loc[0, "raw_rows"] == 3
    assert retention.loc[0, "model_ready_rows"] == 2


def test_missing_qc_y_finalizacion(analytics_datasets):
    missing = missing_before_after(analytics_datasets["raw"], analytics_datasets["model_ready"])
    qc_summary = qc_flag_summary(analytics_datasets["qc"])
    fin = finalization_summary(analytics_datasets["end"])

    hi_row = missing.loc[missing["column"] == "HORA_INICIAL_REAL"].iloc[0]
    assert hi_row["raw_missing"] == 1
    assert hi_row["final_missing"] == 0
    assert qc_summary.loc[qc_summary["flag"] == "qc_any_flag", "count"].iloc[0] == 2
    assert fin.loc[fin["FIN_TIPO"] == "COMPLETO", "count"].iloc[0] == 2


def test_operational_kpis_y_agregados(analytics_datasets):
    kpis = operational_kpis(analytics_datasets)
    route = demand_by_route(analytics_datasets["model_ready"])
    hour = demand_by_hour_weekday(analytics_datasets["model_ready"])
    duration = duration_by_route(analytics_datasets["model_ready"])

    assert kpis.loc[kpis["kpi"] == "despachos_raw", "value"].iloc[0] == 3
    assert kpis.loc[kpis["kpi"] == "qc_hard_fail", "value"].iloc[0] == 1
    assert route.loc[route["FK_RUTA"] == 1, "pasajeros_total"].iloc[0] == 40
    assert hour["pasajeros_total"].sum() == 40
    assert duration.loc[duration["FK_RUTA"] == 1, "mean"].iloc[0] == 60.0


def test_build_kpi_tables_genera_tablas_esperadas(analytics_datasets):
    tables = build_kpi_tables(analytics_datasets)

    assert set(tables) == {
        "operational_kpis",
        "demand_by_route",
        "demand_by_hour_weekday",
        "duration_by_route",
    }
