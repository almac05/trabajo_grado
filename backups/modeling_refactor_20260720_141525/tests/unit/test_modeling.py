"""Minimal tests for the first modeling phase."""

from __future__ import annotations

import pandas as pd
import pytest

from proyecto_grado.modeling.baselines import predict_baseline
from proyecto_grado.modeling.evaluate import add_error_columns, metric_dict
from proyecto_grado.modeling.features import add_modeling_features, validate_lag_features
from proyecto_grado.modeling.splits import make_expanding_folds, make_final_test_window


def _base_series(n: int = 500) -> pd.DataFrame:
    """Create a small 30-minute operational series for tests."""
    ts = pd.date_range("2024-01-01 04:00", periods=n, freq="30min")
    return pd.DataFrame(
        {
            "timestamp": ts,
            "FK_RUTA": [1] * n,
            "granularidad_min": [30] * n,
            "pasajeros_total": [float(i % 50) for i in range(n)],
            "is_gap": [False] * n,
            "target_observed": [True] * n,
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
