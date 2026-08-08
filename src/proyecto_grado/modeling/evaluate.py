"""Evaluation metrics for time-series demand forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_error_columns(predictions: pd.DataFrame) -> pd.DataFrame:
    """Add signed, absolute and squared error columns."""
    data = predictions.copy()
    data["error"] = data["y_pred"] - data["y_real"]
    data["error_abs"] = data["error"].abs()
    data["error_squared"] = data["error"] ** 2
    return data


def metric_dict(df: pd.DataFrame) -> dict[str, float | int]:
    """Compute MAE, RMSE, sMAPE, WAPE and mean bias."""
    evaluable = df.dropna(subset=["y_real", "y_pred"]).copy()
    n_total = len(df)
    n = len(evaluable)
    if n == 0:
        return {
            "n": 0,
            "n_total": n_total,
            "missing_y": int(df["y_real"].isna().sum()),
            "missing_pred": int(df["y_pred"].isna().sum()),
            "mae": np.nan,
            "rmse": np.nan,
            "smape": np.nan,
            "wape": np.nan,
            "bias_mean": np.nan,
            "bias_abs": np.nan,
            "bias_to_mae_ratio": np.nan,
        }

    error = evaluable["y_pred"] - evaluable["y_real"]
    abs_error = error.abs()
    denominator = evaluable["y_real"].abs() + evaluable["y_pred"].abs()
    smape_terms = np.where(denominator > 0, 2.0 * abs_error / denominator, 0.0)
    y_abs_sum = float(evaluable["y_real"].abs().sum())
    mae = float(abs_error.mean())
    bias_mean = float(error.mean())
    return {
        "n": n,
        "n_total": n_total,
        "missing_y": int(df["y_real"].isna().sum()),
        "missing_pred": int(df["y_pred"].isna().sum()),
        "mae": mae,
        "rmse": float(np.sqrt((error**2).mean())),
        "smape": float(np.mean(smape_terms) * 100.0),
        "wape": float(abs_error.sum() / y_abs_sum * 100.0) if y_abs_sum > 0 else np.nan,
        "bias_mean": bias_mean,
        "bias_abs": abs(bias_mean),
        "bias_to_mae_ratio": abs(bias_mean) / mae if mae > 0 else np.nan,
    }


def metrics_by_group(predictions: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Compute metrics for each group in a prediction table."""
    if predictions.empty:
        return pd.DataFrame(columns=group_cols + list(metric_dict(predictions).keys()))

    rows: list[dict[str, object]] = []
    for keys, group in predictions.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys, strict=False))
        if "dataset_version" in group.columns and "dataset_version" not in record:
            record["dataset_version"] = group["dataset_version"].iloc[0]
        if "run_id" in group.columns and "run_id" not in record:
            record["run_id"] = group["run_id"].iloc[0]
        record.update(metric_dict(group))
        rows.append(record)
    return pd.DataFrame(rows)
