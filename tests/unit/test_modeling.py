"""Minimal tests for the first modeling phase."""

from __future__ import annotations

import pandas as pd
import pytest

from proyecto_grado.modeling.backtesting import predict_window
from proyecto_grado.modeling.baselines import RollingAverageBaseline, predict_baseline
from proyecto_grado.modeling.config import load_xgboost_model_names
from proyecto_grado.modeling.evaluate import add_error_columns, metric_dict
from proyecto_grado.modeling.features import (
    add_modeling_features,
    feature_columns,
    validate_lag_features,
)
from proyecto_grado.modeling.splits import (
    align_end_to_operational_day,
    align_start_to_operational_day,
    align_to_full_operational_days,
    make_expanding_folds,
    make_final_test_window,
    split_alignment_summary,
    validate_full_operational_window,
)
from proyecto_grado.modeling.xgboost_models import (
    _early_stopping_split,
    fit_predict_xgboost_route,
    predict_xgboost,
)
from scripts.evaluate_models import build_metrics_common_support
from scripts.run_backtesting import _csv_name

_FAST_XGB_PARAMS = {"n_estimators": 30, "max_depth": 2, "min_child_weight": 1}


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


def _full_day_series(days: int = 120, with_gaps: bool = False) -> pd.DataFrame:
    """Create a full 30-minute panel labelled by left bin edge."""
    df = _base_series(n=days * 48)
    if with_gaps:
        df.loc[df.index[10:20], "is_gap"] = True
        df.loc[df.index[10:20], "pasajeros_total"] = pd.NA
    return df


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


def test_align_start_after_operational_boundary_moves_to_next_day():
    """A 16:00 start should advance to the next 04:00 boundary."""
    aligned = align_start_to_operational_day(pd.Timestamp("2026-04-01 16:00"))
    assert aligned == pd.Timestamp("2026-04-02 04:00")


def test_align_start_exact_boundary_is_preserved():
    """A 04:00 start is already a complete operational-day boundary."""
    aligned = align_start_to_operational_day(pd.Timestamp("2026-04-01 04:00"))
    assert aligned == pd.Timestamp("2026-04-01 04:00")


def test_align_start_before_operational_boundary_moves_to_same_day():
    """A 02:00 start should advance to 04:00 of the same calendar day."""
    aligned = align_start_to_operational_day(pd.Timestamp("2026-04-01 02:00"))
    assert aligned == pd.Timestamp("2026-04-01 04:00")


def test_align_end_excludes_partial_last_day_ending_at_1600():
    """A range ending at 16:30 excludes the operational day that started at 04:00."""
    aligned = align_end_to_operational_day(pd.Timestamp("2026-06-10 16:30"))
    assert aligned == pd.Timestamp("2026-06-10 04:00")


def test_align_end_exact_boundary_is_preserved():
    """An exclusive end exactly at 04:00 remains unchanged."""
    aligned = align_end_to_operational_day(pd.Timestamp("2026-06-10 04:00"))
    assert aligned == pd.Timestamp("2026-06-10 04:00")


def test_align_to_full_days_has_no_30_minute_off_by_one():
    """The last 30-minute bin of a complete day ends at the exclusive 04:00 boundary."""
    df = _full_day_series(days=3)
    result = align_to_full_operational_days(df=df, granularity_min=30)

    assert result.aligned_start == pd.Timestamp("2024-01-01 04:00")
    assert result.aligned_end == pd.Timestamp("2024-01-04 04:00")
    window = df[(df["timestamp"] >= result.aligned_start) & (df["timestamp"] < result.aligned_end)]
    assert window["timestamp"].max() == pd.Timestamp("2024-01-04 03:30")


def test_folds_start_and_end_at_operational_boundary():
    """All validation and final-test windows should start/end at 04:00."""
    df = _full_day_series(days=300)
    folds = make_expanding_folds(
        df,
        validation_weeks=2,
        step_weeks=2,
        min_train_weeks=26,
        test_weeks=10,
        granularity_min=30,
    )
    final_test = make_final_test_window(df, test_weeks=10, granularity_min=30)

    assert len(folds) > 0
    for fold in folds:
        assert fold.validation_start.time().strftime("%H:%M:%S") == "04:00:00"
        assert fold.validation_end.time().strftime("%H:%M:%S") == "04:00:00"
        validate_full_operational_window(
            fold.validation_start,
            fold.validation_end,
            f"validation_{fold.fold}",
        )
    assert final_test.test_start.time().strftime("%H:%M:%S") == "04:00:00"
    assert final_test.test_end.time().strftime("%H:%M:%S") == "04:00:00"


def test_folds_are_chronological_and_do_not_overlap_test():
    """Train, validation and test windows must remain chronological and disjoint."""
    df = _full_day_series(days=300)
    final_test = make_final_test_window(df, test_weeks=10, granularity_min=30)
    folds = make_expanding_folds(
        df,
        validation_weeks=2,
        step_weeks=2,
        min_train_weeks=26,
        test_weeks=10,
        granularity_min=30,
    )

    previous_end = None
    for fold in folds:
        assert fold.train_start < fold.train_end <= fold.validation_start < fold.validation_end
        assert fold.validation_end <= final_test.test_start
        if previous_end is not None:
            assert fold.validation_start >= previous_end
        previous_end = fold.validation_end


def test_alignment_works_with_gaps_inside_complete_days():
    """Internal gaps should not cause a complete boundary day to be treated as partial."""
    df = _full_day_series(days=5, with_gaps=True)
    result = align_to_full_operational_days(df=df, granularity_min=30)
    summary = split_alignment_summary(df, test_weeks=1, granularity_min=30)

    assert result.aligned_start == pd.Timestamp("2024-01-01 04:00")
    assert result.aligned_end == pd.Timestamp("2024-01-06 04:00")
    assert summary.loc[summary["scope"].eq("dataset_available_range"), "rows_excluded"].sum() == 0


def test_versioned_csv_name_preserves_historical_outputs():
    """Versioned output names should include run_id instead of reusing stable names."""
    assert _csv_name("metrics_by_fold_multitarget", "run_abc", True) == (
        "metrics_by_fold_multitarget_run_abc.csv"
    )
    assert _csv_name("metrics_by_fold_multitarget", "run_abc", False) == (
        "metrics_by_fold_multitarget.csv"
    )


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


def _daily_slot_series(n_days: int, value: float, franja: str = "08:00") -> pd.DataFrame:
    """One observation per day at a fixed 30-minute slot, for rolling-average tests."""
    ts = pd.date_range("2024-01-01 08:00", periods=n_days, freq="1D")
    return pd.DataFrame(
        {
            "timestamp": ts,
            "FK_RUTA": [1] * n_days,
            "tipo_dia": ["LABORAL"] * n_days,
            "franja_30min": [franja] * n_days,
            "pasajeros_total": [value] * n_days,
            "target_observed": [True] * n_days,
        }
    )


def test_rolling_average_does_not_use_predict_df_target_values():
    """The predict_df target column must never influence a rolling-average prediction."""
    train = _daily_slot_series(n_days=60, value=10.0)
    train_end = train["timestamp"].max() + pd.Timedelta(days=1)
    pred = pd.DataFrame(
        {
            "FK_RUTA": [1],
            "tipo_dia": ["LABORAL"],
            "franja_30min": ["08:00"],
            "pasajeros_total": [99999.0],
        }
    )

    y_pred, meta = predict_baseline(
        "rolling_average_4w",
        train,
        pred,
        train_end=train_end,
        return_meta=True,
    )
    assert y_pred.iloc[0] == pytest.approx(10.0)
    assert meta["fallback_level"].iloc[0] == "1"


def test_rolling_average_window_cutoff_ignores_observations_before_w():
    """Observations older than the W-week window must not affect the prediction."""
    train = _daily_slot_series(n_days=200, value=10.0)
    train_end = train["timestamp"].max() + pd.Timedelta(days=1)
    pred = pd.DataFrame({"FK_RUTA": [1], "tipo_dia": ["LABORAL"], "franja_30min": ["08:00"]})

    baseline_pred, _ = RollingAverageBaseline(window_weeks=4).fit(train, train_end).predict(pred)

    old_cutoff = train_end - pd.Timedelta(weeks=10)
    mutated = train.copy()
    mutated.loc[mutated["timestamp"] < old_cutoff, "pasajeros_total"] = 9999.0
    mutated_pred, _ = RollingAverageBaseline(window_weeks=4).fit(mutated, train_end).predict(pred)

    assert baseline_pred.iloc[0] == pytest.approx(10.0)
    assert mutated_pred.iloc[0] == pytest.approx(baseline_pred.iloc[0])


def test_rolling_average_fallback_hierarchy_and_level_recorded():
    """A forced-empty cell should fall back to the adjacent-slot level and record it."""
    n_days = 30
    ts = pd.date_range("2024-01-01 08:00", periods=n_days, freq="1D")
    rows = []
    for t in ts:
        rows.append(
            {
                "timestamp": t,
                "FK_RUTA": 1,
                "tipo_dia": "LABORAL",
                "franja_30min": "08:00",
                "pasajeros_total": 10.0,
                "target_observed": True,
            }
        )
        rows.append(
            {
                "timestamp": t,
                "FK_RUTA": 1,
                "tipo_dia": "LABORAL",
                "franja_30min": "07:30",
                "pasajeros_total": 20.0,
                "target_observed": True,
            }
        )
        rows.append(
            {
                "timestamp": t,
                "FK_RUTA": 1,
                "tipo_dia": "LABORAL",
                "franja_30min": "08:30",
                "pasajeros_total": 30.0,
                "target_observed": True,
            }
        )
    train = pd.DataFrame(rows)
    train_end = ts[-1] + pd.Timedelta(days=1)

    # The target cell (ruta=1, LABORAL, 08:00) never appears with an observed
    # value anywhere in the training history: levels 1, 2 and 4 must all miss,
    # and the estimate must come from the adjacent 07:30/08:30 slots (level 3).
    mask = (train["franja_30min"] == "08:00") & (train["FK_RUTA"] == 1)
    train.loc[mask, "pasajeros_total"] = pd.NA
    train.loc[mask, "target_observed"] = False

    pred = pd.DataFrame({"FK_RUTA": [1], "tipo_dia": ["LABORAL"], "franja_30min": ["08:00"]})
    model = RollingAverageBaseline(window_weeks=2, min_obs_celda=3).fit(train, train_end)
    y_pred, fallback_level = model.predict(pred)

    assert fallback_level.iloc[0] == "3"
    assert y_pred.iloc[0] == pytest.approx(25.0)


def test_rolling_average_requires_train_end():
    """rolling_average_* baselines must fail explicitly without train_end."""
    train = _daily_slot_series(n_days=40, value=10.0)
    pred = pd.DataFrame({"FK_RUTA": [1], "tipo_dia": ["LABORAL"], "franja_30min": ["08:00"]})

    with pytest.raises(ValueError):
        predict_baseline("rolling_average_4w", train, pred)


def test_rolling_average_wired_through_predict_window():
    """predict_window must thread train_end and expose fallback_level per model."""
    df = add_modeling_features(_full_day_series(days=90))
    predictions = predict_window(
        dataset=df,
        train_start=df["timestamp"].min(),
        train_end=pd.Timestamp("2024-03-01 04:00"),
        eval_start=pd.Timestamp("2024-03-01 04:00"),
        eval_end=pd.Timestamp("2024-03-01 08:00"),
        model_names=["naive", "rolling_average_4w"],
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

    assert "fallback_level" in predictions.columns
    naive_rows = predictions[predictions["model"] == "naive"]
    rolling_rows = predictions[predictions["model"] == "rolling_average_4w"]
    assert naive_rows["fallback_level"].isna().all()
    assert rolling_rows["fallback_level"].isin(["1", "2", "3", "4", "5"]).all()


def test_frozen_regression_existing_baselines_metrics():
    """The 4 pre-existing baselines must keep exact metrics on a fixed dataset.

    Reference values captured from the current implementation before adding
    rolling_average_*; any future change to naive/seasonal_naive_*/historical
    average that alters these numbers is a behavioral regression.
    """
    df = add_modeling_features(_base_series(n=400))
    train = df.iloc[:300]
    pred = df.iloc[350:360]

    expected = {
        "naive": {"mae": 5.8, "bias_mean": 4.0},
        "seasonal_naive_daily": {"mae": 2.0, "bias_mean": 2.0},
        "seasonal_naive_weekly": {"mae": 14.0, "bias_mean": 14.0},
        "historical_average_route_day_type_slot": {"mae": 9.0, "bias_mean": 9.0},
    }

    for model, expected_metrics in expected.items():
        y_pred = predict_baseline(model, train, pred)
        frame = add_error_columns(
            pd.DataFrame(
                {"y_real": pred["pasajeros_total"].to_numpy(), "y_pred": y_pred.to_numpy()}
            )
        )
        metrics = metric_dict(frame)
        assert metrics["mae"] == pytest.approx(expected_metrics["mae"]), model
        assert metrics["bias_mean"] == pytest.approx(expected_metrics["bias_mean"]), model


def test_xgboost_models_registered_in_config():
    """xgboost_l2 and xgboost_l1 must be registered the same way as baselines."""
    names = load_xgboost_model_names()
    assert names == ["xgboost_l2", "xgboost_l1"]


def test_xgboost_does_not_recover_synthetic_validation_target():
    """A model trained only on history must not reproduce an injected validation constant."""
    df = add_modeling_features(_full_day_series(days=90))
    train_end = pd.Timestamp("2024-03-01 04:00")
    train_df = df[(df["timestamp"] < train_end) & df["target_observed"]].copy()
    predict_df = df[
        (df["timestamp"] >= train_end) & (df["timestamp"] < train_end + pd.Timedelta(days=2))
    ].copy()
    predict_df["pasajeros_total"] = 99999.0

    y_pred = predict_xgboost(
        "xgboost_l2",
        train_df,
        predict_df,
        target_col="pasajeros_total",
        feature_set="calendario_ruta_lags_demanda",
        train_end=train_end,
        params=_FAST_XGB_PARAMS,
        early_stopping_rounds=5,
        early_stopping_weeks=1,
    )

    assert (99999.0 - y_pred).abs().min() > 100.0


def test_xgboost_early_stopping_split_never_reaches_train_end():
    """The early-stopping carve-out must stay strictly inside the training window."""
    df = add_modeling_features(_full_day_series(days=60))
    train_end = pd.Timestamp("2024-02-01 04:00")
    train_df = df[(df["timestamp"] < train_end) & df["target_observed"]].copy()

    fit_df, stop_df = _early_stopping_split(train_df, train_end, weeks=2)

    assert not fit_df.empty
    assert not stop_df.empty
    assert stop_df["timestamp"].max() < train_end
    assert stop_df["timestamp"].min() >= train_end - pd.Timedelta(weeks=2)
    assert fit_df["timestamp"].max() < stop_df["timestamp"].min()


def test_xgboost_trains_and_predicts_without_imputing_nulls():
    """XGBoost must fit and predict directly on frames containing null lag features."""
    df = add_modeling_features(_full_day_series(days=60))
    train_end = pd.Timestamp("2024-02-01 04:00")
    train_df = df[(df["timestamp"] < train_end) & df["target_observed"]].copy()
    predict_df = df[
        (df["timestamp"] >= train_end) & (df["timestamp"] < train_end + pd.Timedelta(days=1))
    ].copy()
    assert train_df["pasajeros_total_lag_336"].isna().any()

    y_pred, meta = fit_predict_xgboost_route(
        train_df,
        predict_df,
        target_col="pasajeros_total",
        feature_set="calendario_ruta_lags_demanda",
        objective="reg:absoluteerror",
        train_end=train_end,
        params=_FAST_XGB_PARAMS,
        early_stopping_rounds=5,
        early_stopping_weeks=1,
    )

    assert y_pred.notna().all()
    assert meta.n_train_rows > 0
    assert meta.n_early_stop_rows > 0
    assert meta.n_estimators_used <= _FAST_XGB_PARAMS["n_estimators"]


def test_xgboost_wired_through_predict_window():
    """predict_window must dispatch XGBoost configurations and collect diagnostics."""
    df = add_modeling_features(_full_day_series(days=90))
    diagnostics: list[dict[str, object]] = []

    predictions = predict_window(
        dataset=df,
        train_start=df["timestamp"].min(),
        train_end=pd.Timestamp("2024-03-01 04:00"),
        eval_start=pd.Timestamp("2024-03-01 04:00"),
        eval_end=pd.Timestamp("2024-03-02 04:00"),
        model_names=["naive", "xgboost_l2"],
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
        diagnostics=diagnostics,
    )

    xgb_rows = predictions[predictions["model"] == "xgboost_l2"]
    assert not xgb_rows.empty
    assert xgb_rows["fallback_level"].isna().all()
    assert xgb_rows["y_pred"].notna().all()
    assert diagnostics
    assert diagnostics[0]["model"] == "xgboost_l2"
    assert diagnostics[0]["importance_gain"]
