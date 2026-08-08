"""Regime, importance and objective-comparison analysis for XGBoost runs."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

from proyecto_grado.modeling.config import backup_if_exists
from proyecto_grado.modeling.evaluate import metrics_by_group

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDINARIO_TIPOS = {"LABORAL", "SABADO", "DOMINGO"}
RARO_TIPOS = {"FESTIVO", "FESTIVO_PUENTE"}


def _add_regimen(predictions: pd.DataFrame) -> pd.DataFrame:
    """Label each row as ``ordinario`` or ``raro`` from ``tipo_dia``."""
    data = predictions.copy()
    data["regimen"] = data["tipo_dia"].map(
        lambda t: "ordinario" if t in ORDINARIO_TIPOS else ("raro" if t in RARO_TIPOS else "otro")
    )
    return data


def build_regime_metrics_by_fold(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute MAE/bias per fold, model, route and regimen (LABORAL/SABADO/DOMINGO vs festivos)."""
    data = _add_regimen(predictions)
    group_cols = ["target", "scenario", "split", "fold", "model", "route", "regimen"]
    return metrics_by_group(data, group_cols)


def summarize_regime_metrics(regime_metrics_by_fold: pd.DataFrame) -> pd.DataFrame:
    """Average MAE/bias across folds per model, route and regimen (validation split)."""
    data = regime_metrics_by_fold[regime_metrics_by_fold["split"].eq("validation")].copy()
    if data.empty:
        return pd.DataFrame()
    summary = (
        data.groupby(["target", "scenario", "model", "route", "regimen"], dropna=False)
        .agg(
            n_folds=("fold", "nunique"),
            n_obs_total=("n", "sum"),
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            bias_mean_mean=("bias_mean", "mean"),
            bias_mean_std=("bias_mean", "std"),
        )
        .reset_index()
        .sort_values(["target", "scenario", "regimen", "route", "model"])
    )
    return summary


def build_importance_table(diagnostics: pd.DataFrame) -> pd.DataFrame:
    """Explode per-fold gain-importance dicts into a long feature-ranked table."""
    if diagnostics.empty:
        return pd.DataFrame(
            columns=["target", "scenario", "model", "route", "feature", "gain_mean", "rank"]
        )
    rows: list[dict[str, object]] = []
    for _, row in diagnostics.iterrows():
        for feature, gain in row["importance_gain"].items():
            rows.append(
                {
                    "target": row["target"],
                    "scenario": row["scenario"],
                    "model": row["model"],
                    "route": row["route"],
                    "split": row["split"],
                    "fold": row["fold"],
                    "feature": feature,
                    "gain": gain,
                }
            )
    long_table = pd.DataFrame(rows)
    if long_table.empty:
        return pd.DataFrame(
            columns=["target", "scenario", "model", "route", "feature", "gain_mean", "rank"]
        )

    summary = (
        long_table[long_table["split"].eq("validation")]
        .groupby(["target", "scenario", "model", "route", "feature"], dropna=False)["gain"]
        .mean()
        .reset_index()
        .rename(columns={"gain": "gain_mean"})
    )
    summary["rank"] = summary.groupby(["target", "scenario", "model", "route"])["gain_mean"].rank(
        ascending=False, method="first"
    )
    return summary.sort_values(["target", "scenario", "model", "route", "rank"]).reset_index(
        drop=True
    )


def build_n_estimators_summary(diagnostics: pd.DataFrame) -> pd.DataFrame:
    """Summarize trees selected by early stopping per model and route."""
    if diagnostics.empty:
        return pd.DataFrame()
    data = diagnostics[diagnostics["split"].eq("validation")].copy()
    summary = (
        data.groupby(["target", "scenario", "model", "route"], dropna=False)["n_estimators_used"]
        .agg(n_folds="count", mean="mean", std="std", min="min", max="max")
        .reset_index()
    )
    return summary


def build_objective_comparison(
    metrics_by_fold: pd.DataFrame,
    model_l2: str = "xgboost_l2",
    model_l1: str = "xgboost_l1",
) -> pd.DataFrame:
    """Pair xgboost_l2 vs xgboost_l1 metrics by fold and route (validation split)."""
    data = metrics_by_fold[
        metrics_by_fold["split"].eq("validation")
        & metrics_by_fold["model"].isin([model_l2, model_l1])
    ].copy()
    if data.empty:
        return pd.DataFrame()

    key_cols = ["target", "scenario", "fold", "route"]
    l2 = data[data["model"].eq(model_l2)][[*key_cols, "mae", "bias_mean"]].rename(
        columns={"mae": "mae_l2", "bias_mean": "bias_l2"}
    )
    l1 = data[data["model"].eq(model_l1)][[*key_cols, "mae", "bias_mean"]].rename(
        columns={"mae": "mae_l1", "bias_mean": "bias_l1"}
    )
    paired = l2.merge(l1, on=key_cols, how="inner")
    paired["mae_diff_l1_menos_l2"] = paired["mae_l1"] - paired["mae_l2"]
    paired["bias_abs_diff_l1_menos_l2"] = paired["bias_l1"].abs() - paired["bias_l2"].abs()
    paired["gana_mae"] = paired["mae_diff_l1_menos_l2"].map(
        lambda d: model_l2 if d > 0 else (model_l1 if d < 0 else "empate")
    )
    return paired.sort_values(["target", "scenario", "route", "fold"]).reset_index(drop=True)


def plot_importance_by_route(
    importance_table: pd.DataFrame,
    output_path: str | Path,
    run_id: str,
    top_n: int = 15,
) -> None:
    """Plot top-N gain importance per route for one model."""
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    routes = sorted(importance_table["route"].unique())
    fig, axes = plt.subplots(1, len(routes), figsize=(6.5 * len(routes), 6), squeeze=False)
    for ax, route in zip(axes[0], routes, strict=False):
        route_data = importance_table[importance_table["route"].eq(route)].nsmallest(top_n, "rank")
        route_data = route_data.sort_values("gain_mean")
        ax.barh(route_data["feature"], route_data["gain_mean"], color="#3C6E71")
        ax.set_xlabel("importancia (gain)")
        ax.set_ylabel("variable")
        ax.set_title(f"Ruta {route}", fontsize=10)
        ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_regime_comparison(
    regime_summary: pd.DataFrame,
    output_path: str | Path,
    run_id: str,
) -> None:
    """Plot MAE by model, route and regimen (ordinario vs raro)."""
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = regime_summary.copy()
    data["label"] = data["model"] + " | R" + data["route"].astype(str)

    regimes = sorted(data["regimen"].unique())
    fig, axes = plt.subplots(1, len(regimes), figsize=(7 * len(regimes), 5.5), squeeze=False)
    for ax, regimen in zip(axes[0], regimes, strict=False):
        subset = data[data["regimen"].eq(regimen)].sort_values("mae_mean")
        ax.bar(subset["label"], subset["mae_mean"], yerr=subset["mae_std"], color="#D1495B")
        ax.set_ylabel("MAE promedio entre folds")
        ax.set_xlabel("modelo y ruta")
        ax.set_title(f"regimen: {regimen}", fontsize=10)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_error_evolution_by_fold(
    metrics_by_fold: pd.DataFrame,
    output_path: str | Path,
    run_id: str,
    models: list[str] | None = None,
) -> None:
    """Plot MAE across validation folds for the requested models, per route."""
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = metrics_by_fold[metrics_by_fold["split"].eq("validation")].copy()
    if models is not None:
        data = data[data["model"].isin(models)]
    data["fold_num"] = pd.to_numeric(data["fold"], errors="coerce")
    data = data.dropna(subset=["fold_num"]).sort_values("fold_num")

    routes = sorted(data["route"].unique())
    fig, axes = plt.subplots(len(routes), 1, figsize=(11, 4.5 * len(routes)), squeeze=False)
    for ax_row, route in zip(axes, routes, strict=False):
        ax = ax_row[0]
        route_data = data[data["route"].eq(route)]
        for model, model_data in route_data.groupby("model"):
            ax.plot(model_data["fold_num"], model_data["mae"], marker="o", lw=1.2, label=model)
        ax.set_title(f"Ruta {route}", fontsize=10)
        ax.set_ylabel("MAE")
        ax.set_xlabel("fold de validacion")
        ax.grid(True, alpha=0.25)
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
