"""Analisis cuantitativo del sesgo de los baselines de pronostico.

Este modulo consume las predicciones ya persistidas por el backtesting
(``predictions_multitarget_<run_id>.parquet``) y no recalcula ninguna
prediccion; solo agrega errores ya calculados (`error = y_pred - y_real`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_GROUP_COLS = ["target", "scenario", "model", "route"]


def _evaluable(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return rows with both real and predicted values available."""
    return predictions.dropna(subset=["y_real", "y_pred"]).copy()


def bias_decomposition(
    predictions: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Descompone el error en componente de sesgo y de dispersion (B.1).

    `bias_to_mae_ratio` es la fraccion de MAE que se eliminaria con un simple
    ajuste de nivel (restar `bias_mean` a toda prediccion); el resto
    (`dispersion_fraction`) es el error que persistiria incluso corrigiendo el
    nivel. Es una aproximacion estandar (no una identidad exacta), valida
    porque `mean(|error|) >= |mean(error)|` garantiza que la razon cae en
    [0, 1].
    """
    group_cols = group_cols or [*DEFAULT_GROUP_COLS, "split"]
    data = _evaluable(predictions)
    if data.empty:
        return pd.DataFrame(columns=[*group_cols, "n", "bias_mean", "bias_median", "error_std"])

    rows: list[dict[str, object]] = []
    for keys, group in data.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        error = group["error"]
        mae = float(error.abs().mean())
        bias_mean = float(error.mean())
        bias_to_mae_ratio = abs(bias_mean) / mae if mae > 0 else np.nan
        record = dict(zip(group_cols, keys, strict=False))
        record.update(
            {
                "n": len(group),
                "bias_mean": bias_mean,
                "bias_median": float(error.median()),
                "error_std": float(error.std(ddof=1)) if len(group) > 1 else np.nan,
                "pct_sobreprediccion": float((error > 0).mean() * 100.0),
                "mae": mae,
                "bias_to_mae_ratio": bias_to_mae_ratio,
                "dispersion_fraction": (
                    max(0.0, 1.0 - bias_to_mae_ratio) if pd.notna(bias_to_mae_ratio) else np.nan
                ),
            }
        )
        rows.append(record)
    return pd.DataFrame(rows)


def _fold_windows(folds: pd.DataFrame) -> pd.DataFrame:
    """Compute train-window center and eval-window midpoint per fold."""
    data = folds.copy()
    for col in ("train_start", "train_end", "eval_start", "eval_end"):
        data[col] = pd.to_datetime(data[col])
    data["train_center"] = data["train_start"] + (data["train_end"] - data["train_start"]) / 2
    data["eval_mid"] = data["eval_start"] + (data["eval_end"] - data["eval_start"]) / 2
    data["distance_days"] = (data["eval_mid"] - data["train_center"]).dt.total_seconds() / 86400.0
    return data[
        ["split", "fold", "target", "scenario", "distance_days", "train_center", "eval_mid"]
    ]


def bias_temporal_by_fold(
    predictions: pd.DataFrame,
    folds: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Sesgo por fold de validacion vs. distancia train-center -> periodo predicho (B.2).

    La distancia crece con el numero de fold porque la ventana de
    entrenamiento se expande (train_start fijo) mientras el periodo evaluado
    avanza en el tiempo; es la variable que opera como proxy de "que tan
    lejos, hacia el futuro, se proyecta el promedio historico calculado".
    """
    group_cols = group_cols or DEFAULT_GROUP_COLS
    data = _evaluable(predictions)
    fold_windows = _fold_windows(folds)

    rows: list[dict[str, object]] = []
    agg_cols = [*group_cols, "split", "fold"]
    for keys, group in data.groupby(agg_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(agg_cols, keys, strict=False))
        record["bias_mean"] = float(group["error"].mean())
        record["n"] = len(group)
        rows.append(record)
    bias_by_fold = pd.DataFrame(rows)
    if bias_by_fold.empty:
        return bias_by_fold

    merged = bias_by_fold.merge(
        fold_windows,
        on=["split", "fold", "target", "scenario"],
        how="left",
    )
    return merged


def temporal_bias_correlation(
    bias_by_fold: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Correlacion (Pearson y Spearman) entre distancia temporal y sesgo, por modelo."""
    group_cols = group_cols or DEFAULT_GROUP_COLS
    rows: list[dict[str, object]] = []
    for keys, group in bias_by_fold.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys, strict=False))
        valid = group.dropna(subset=["distance_days", "bias_mean"])
        record["n_folds"] = len(valid)
        if len(valid) >= 3 and valid["distance_days"].nunique() > 1:
            pearson_r, pearson_p = stats.pearsonr(valid["distance_days"], valid["bias_mean"])
            spearman_r, spearman_p = stats.spearmanr(valid["distance_days"], valid["bias_mean"])
            record["pearson_r"] = float(pearson_r)
            record["pearson_p"] = float(pearson_p)
            record["spearman_r"] = float(spearman_r)
            record["spearman_p"] = float(spearman_p)
        else:
            record["pearson_r"] = np.nan
            record["pearson_p"] = np.nan
            record["spearman_r"] = np.nan
            record["spearman_p"] = np.nan
        rows.append(record)
    return pd.DataFrame(rows)


def bias_monthly(
    predictions: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Serie mensual de bias_mean por modelo y ruta."""
    group_cols = group_cols or DEFAULT_GROUP_COLS
    data = _evaluable(predictions)
    if data.empty:
        return pd.DataFrame(columns=[*group_cols, "mes", "bias_mean", "n"])
    data["mes"] = pd.to_datetime(data["timestamp"]).dt.to_period("M").dt.to_timestamp()

    rows: list[dict[str, object]] = []
    agg_cols = [*group_cols, "mes"]
    for keys, group in data.groupby(agg_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(agg_cols, keys, strict=False))
        record["bias_mean"] = float(group["error"].mean())
        record["n"] = len(group)
        rows.append(record)
    return pd.DataFrame(rows)


def _pearson_ci(r: float, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Confidence interval for a Pearson r via the Fisher z transform."""
    if n < 4 or abs(r) >= 1.0:
        return (np.nan, np.nan)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    z_crit = stats.norm.ppf(1 - (1 - confidence) / 2)
    lo, hi = z - z_crit * se, z + z_crit * se
    return (float(np.tanh(lo)), float(np.tanh(hi)))


def bias_vs_fleet(
    bias_monthly_df: pd.DataFrame,
    fleet_monthly: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Correlaciona el sesgo mensual con vehiculos activos y despachos del mes (B.3).

    Reporta el coeficiente y su intervalo de confianza al 95%; la correlacion
    es evidencia consistente con la hipotesis de contraccion de flota, no
    prueba de causalidad.
    """
    group_cols = group_cols or DEFAULT_GROUP_COLS
    fleet = fleet_monthly.copy()
    fleet["mes"] = pd.to_datetime(fleet["mes"])

    merged = bias_monthly_df.merge(fleet, on="mes", how="inner")
    rows: list[dict[str, object]] = []
    for keys, group in merged.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys, strict=False))
        record["n_meses"] = len(group)
        for fleet_col in ("vehiculos_activos", "despachos_total"):
            if (
                len(group) >= 4
                and group[fleet_col].nunique() > 1
                and group["bias_mean"].nunique() > 1
            ):
                pearson_r, pearson_p = stats.pearsonr(group[fleet_col], group["bias_mean"])
                spearman_r, spearman_p = stats.spearmanr(group[fleet_col], group["bias_mean"])
                ci_low, ci_high = _pearson_ci(pearson_r, len(group))
            else:
                pearson_r = pearson_p = spearman_r = spearman_p = ci_low = ci_high = np.nan
            record[f"pearson_r_{fleet_col}"] = pearson_r
            record[f"pearson_p_{fleet_col}"] = pearson_p
            record[f"pearson_ci95_low_{fleet_col}"] = ci_low
            record[f"pearson_ci95_high_{fleet_col}"] = ci_high
            record[f"spearman_r_{fleet_col}"] = spearman_r
            record[f"spearman_p_{fleet_col}"] = spearman_p
        rows.append(record)
    return pd.DataFrame(rows)


def bias_by_slot(
    predictions: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Sesgo promedio por hora del dia y tipo de dia, por modelo (B.4)."""
    group_cols = group_cols or [*DEFAULT_GROUP_COLS, "tipo_dia", "hora_del_dia"]
    data = _evaluable(predictions)
    if data.empty:
        return pd.DataFrame(columns=[*group_cols, "bias_mean", "n"])

    rows: list[dict[str, object]] = []
    for keys, group in data.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = dict(zip(group_cols, keys, strict=False))
        record["bias_mean"] = float(group["error"].mean())
        record["n"] = len(group)
        rows.append(record)
    return pd.DataFrame(rows)
