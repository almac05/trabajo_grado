"""Minimal tests for the first modeling phase."""

from __future__ import annotations

import pandas as pd
import pytest

from proyecto_grado.modeling.backtesting import predict_window
from proyecto_grado.modeling.baselines import predict_baseline
from proyecto_grado.modeling.evaluate import add_error_columns, metric_dict
from proyecto_grado.modeling.features import (
    add_modeling_features,
    feature_columns,
    validate_lag_features,
)
from proyecto_grado.modeling.splits import make_expanding_folds, make_final_test_window
from scripts.evaluate_models import build_metrics_common_support


def _base_series(n: int = 500) -> pd.DataFrame:
    """Create a small 30-minute operational series for tests."""
    ts = pd.date_range("2024-01-01 04:00", periods=n, freq="30min")
    return pd.DataFrame(
        {
            "timestamp": ts,
            "FK_RUTA": [1] * n,
            "granularidad_min": [30] * n,
            "pasajeros_total": [float(i % 50) for i in range(n)],
            "despachos_count": [2 if i % 9 else 0 for i in range(n)],
            "is_gap": [False] * n,
            "target_observed": [True] * n,
            "dataset_version": ["test"] * n,
            "source_hash": ["hash"] * n,
            "gap_tipo": ["operativo"] * n,
            "dentro_horario_operativo": [True] * n,
            "tipo_dia": ["LABORAL"] * n,
            "franja_horaria": ["MANANA"] * n,
            "franja_30min": [t.strftime("%H:%M") for t in ts],
            "hora_del_dia": ts.hour,
            "dia_semana": ts.dayofweek,
            "mes": ts.month,
            "semana_anio": ts.isocalendar().week.astype(int),
            "es_fin_semana": ts.dayofweek >= 5,
            "es_festivo": [False] * n,
        }
    )


def test_metrics_basic_values():
    """MAE, RMSE, WAPE and bias should match manual calculations."""
    preds = pd.DataFrame({"y_real": [10.0, 20.0], "y_pred": [12.0, 18.0]})
    preds = add_error_columns(preds)
    metrics = metric_dict(preds)

    assert metrics["mae"] == pytest.approx(2.0)
    assert metrics["rmse"] == pytest.approx(2.0)
    assert metrics["wape"] == pytest.approx(13.3333333)
    assert metrics["bias_mean"] == pytest.approx(0.0)


def test_features_use_shifted_values_only():
    """Rolling means must use shifted targets and exclude the current row."""
    df = _base_series(n=20)
    featured = add_modeling_features(df)
    validate_lag_features(featured)

    row = featured.iloc[4]
    assert row["lag_1"] == pytest.approx(featured.iloc[3]["pasajeros_total"])
    assert row["rolling_mean_3"] == pytest.approx(featured.iloc[1:4]["pasajeros_total"].mean())


def test_multitarget_columns_and_observed_flags():
    """Feature engineering should create both supervised targets and flags."""
    df = _base_series(n=20)
    featured = add_modeling_features(df)

    assert "despachos_count_real" in featured.columns
    assert "pasajeros_por_despacho_real" in featured.columns
    assert "target_pasajeros_total_observed" in featured.columns
    assert "target_pasajeros_por_despacho_observed" in featured.columns
    assert featured.loc[0, "target_pasajeros_total_observed"]
    assert not featured.loc[0, "target_pasajeros_por_despacho_observed"]


def test_explicit_lag_aliases_match_passenger_target():
    """Legacy lag aliases must remain equivalent to passenger-total lags."""
    featured = add_modeling_features(_base_series(n=60))

    assert featured["lag_1"].equals(featured["pasajeros_total_lag_1"])
    assert featured["lag_48"].equals(featured["pasajeros_total_lag_48"])
    assert featured["rolling_mean_3"].equals(featured["pasajeros_total_rolling_mean_3"])


def test_productivity_lags_use_shifted_productivity_values():
    """Productivity lags must use previous productivity, not current rows."""
    featured = add_modeling_features(_base_series(n=20))
    validate_lag_features(featured, target_col="pasajeros_por_despacho_real")

    row = featured.iloc[5]
    assert row["pasajeros_por_despacho_lag_1"] == pytest.approx(
        featured.iloc[4]["pasajeros_por_despacho_real"]
    )


def test_scenario_feature_sets_exclude_current_dispatch_count():
    """Scenarios may use lagged dispatch history but not current dispatch count."""
    sin_oferta = feature_columns("calendario_ruta_lags_demanda")
    oferta = feature_columns("calendario_ruta_lags_demanda_lags_despachos")
    productividad = feature_columns(
        "calendario_ruta_lags_productividad_lags_demanda_lags_despachos"
    )

    assert "despachos_count_real" not in sin_oferta
    assert "despachos_count_real" not in oferta
    assert "despachos_count_real" not in productividad
    assert "despachos_count_real_lag_48" in oferta
    assert "pasajeros_por_despacho_lag_48" in productividad


def test_expanding_folds_do_not_overlap_final_test():
    """Validation folds must end before the reserved final test window."""
    df = _base_series(n=24 * 2 * 60)
    final_test = make_final_test_window(df, test_weeks=2, granularity_min=30)
    folds = make_expanding_folds(
        df,
        validation_weeks=1,
        step_weeks=1,
        min_train_weeks=2,
        test_weeks=2,
    )

    assert folds
    assert all(fold.train_end <= fold.validation_start for fold in folds)
    assert all(fold.validation_end <= final_test.test_start for fold in folds)


def test_naive_baselines_read_expected_lag_columns():
    """Simple baselines should map directly to their lag columns."""
    df = add_modeling_features(_base_series(n=400))
    train = df.iloc[:300]
    pred = df.iloc[350:360]

    assert predict_baseline("naive", train, pred).iloc[0] == pytest.approx(pred["lag_1"].iloc[0])
    assert predict_baseline("seasonal_naive_daily", train, pred).iloc[0] == pytest.approx(
        pred["lag_48"].iloc[0]
    )
    assert predict_baseline("seasonal_naive_weekly", train, pred).iloc[0] == pytest.approx(
        pred["lag_336"].iloc[0]
    )


def test_productivity_baselines_read_target_specific_lags():
    """Baselines for productivity should read productivity lag columns."""
    df = add_modeling_features(_base_series(n=400))
    train = df.iloc[:300].copy()
    pred = df.iloc[350:360].copy()
    train["target_observed"] = train["target_pasajeros_por_despacho_observed"]

    assert predict_baseline(
        "naive",
        train,
        pred,
        target_col="pasajeros_por_despacho_real",
    ).iloc[0] == pytest.approx(pred["pasajeros_por_despacho_lag_1"].iloc[0])
    assert predict_baseline(
        "seasonal_naive_daily",
        train,
        pred,
        target_col="pasajeros_por_despacho_real",
    ).iloc[0] == pytest.approx(pred["pasajeros_por_despacho_lag_48"].iloc[0])


def test_baselines_reject_non_one_horizon():
    """This phase should fail explicitly for horizons other than one."""
    df = add_modeling_features(_base_series(n=50))

    with pytest.raises(NotImplementedError):
        predict_baseline("naive", df.iloc[:20], df.iloc[20:25], horizon=2)


def test_historical_average_uses_train_only():
    """Historical average should be fitted from train rows only."""
    train = pd.DataFrame(
        {
            "FK_RUTA": [1, 1, 1],
            "tipo_dia": ["LABORAL", "LABORAL", "SABADO"],
            "franja_30min": ["08:00", "08:00", "08:00"],
            "pasajeros_total": [10.0, 30.0, 999.0],
            "target_observed": [True, True, True],
        }
    )
    pred = pd.DataFrame(
        {
            "FK_RUTA": [1],
            "tipo_dia": ["LABORAL"],
            "franja_30min": ["08:00"],
        }
    )

    y_pred = predict_baseline("historical_average_route_day_type_slot", train, pred)
    assert y_pred.iloc[0] == pytest.approx(20.0)


def test_prediction_frame_uses_interval_start_as_origin():
    """Persisted predictions should use the target interval start as origin."""
    df = add_modeling_features(_base_series(n=140))
    predictions = predict_window(
        dataset=df,
        train_start=pd.Timestamp("2024-01-01 04:00"),
        train_end=pd.Timestamp("2024-01-02 04:00"),
        eval_start=pd.Timestamp("2024-01-02 04:00"),
        eval_end=pd.Timestamp("2024-01-02 08:00"),
        model_names=["naive"],
        run_id="test_run",
        fold="1",
        split="validation",
        horizon=1,
        granularity_min=30,
        target="pasajeros_total",
        scenario="sin_oferta",
        feature_set="calendario_ruta_lags_demanda",
        target_col="pasajeros_total",
        observed_flag="target_pasajeros_total_observed",
    )

    first = predictions.iloc[0]
    assert first["origin_timestamp"] == first["timestamp"]
    assert first["target_interval_start"] == first["timestamp"]
    assert first["target_interval_end"] == first["timestamp"] + pd.Timedelta(minutes=30)
    assert first["feature_cutoff_timestamp"] == first["timestamp"]
    assert "source_hash" in predictions.columns
    assert "dispatch_history_level" in predictions.columns


def test_common_support_groups_by_target_and_scenario():
    """Common-support metrics must not mix different targets or scenarios."""
    rows = []
    for target, scenario in [
        ("pasajeros_total", "sin_oferta"),
        ("pasajeros_total", "oferta_historica_rezagada"),
    ]:
        for model in ["naive", "seasonal_naive_daily"]:
            rows.append(
                {
                    "dataset_version": "test",
                    "run_id": "run",
                    "target": target,
                    "scenario": scenario,
                    "feature_set": "features",
                    "split": "test_final",
                    "fold": "test_final",
                    "route": 1,
                    "granularity_min": 30,
                    "horizon": 1,
                    "timestamp": pd.Timestamp("2024-01-01"),
                    "model": model,
                    "y_real": 10.0,
                    "y_pred": 11.0,
                }
            )
    metrics = build_metrics_common_support(pd.DataFrame(rows))

    assert set(metrics["scenario"]) == {"sin_oferta", "oferta_historica_rezagada"}
    assert set(metrics["target"]) == {"pasajeros_total"}
