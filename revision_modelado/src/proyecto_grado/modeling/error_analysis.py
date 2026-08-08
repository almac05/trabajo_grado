"""Error analysis tables and figures for baseline forecasts."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

from proyecto_grado.modeling.config import backup_if_exists
from proyecto_grado.modeling.evaluate import metrics_by_group

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def build_error_tables(predictions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build route, hour and day-type error summaries."""
    return {
        "by_route": metrics_by_group(predictions, ["split", "model", "route"]),
        "by_hour": metrics_by_group(predictions, ["split", "model", "hora_del_dia"]),
        "by_day_type": metrics_by_group(predictions, ["split", "model", "tipo_dia"]),
    }


def _final_test_observed(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return evaluable final-test rows for plotting."""
    data = predictions[predictions["split"].eq("test_final")].copy()
    data = data.dropna(subset=["y_real", "y_pred"])
    return data


def plot_observed_vs_predicted(
    predictions: pd.DataFrame, output_path: str | Path, run_id: str
) -> None:
    """Plot observed vs predicted passenger totals for the final holdout."""
    data = _final_test_observed(predictions)
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for ax, route in zip(axes, sorted(data["route"].unique()), strict=False):
        route_data = data[data["route"].eq(route)].copy()
        if route_data.empty:
            continue
        max_ts = route_data["timestamp"].min() + pd.Timedelta(days=14)
        route_data = route_data[route_data["timestamp"] <= max_ts]
        observed = route_data.drop_duplicates("timestamp").sort_values("timestamp")
        ax.plot(observed["timestamp"], observed["y_real"], color="black", lw=1.5, label="observado")
        for model, model_data in route_data.groupby("model"):
            model_data = model_data.sort_values("timestamp")
            ax.plot(model_data["timestamp"], model_data["y_pred"], lw=1.0, alpha=0.8, label=model)
        ax.set_title(f"Ruta {route}")
        ax.set_ylabel("pasajeros")
        ax.grid(True, alpha=0.25)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    axes[-1].set_xlabel("timestamp")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_metrics_comparison(metrics: pd.DataFrame, output_path: str | Path, run_id: str) -> None:
    """Plot final-test MAE by route and baseline."""
    data = metrics[metrics["split"].eq("test_final")].copy()
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    data["label"] = data["model"] + " | R" + data["route"].astype(str)
    ax.bar(data["label"], data["mae"], color="#3C6E71")
    ax.set_ylabel("MAE")
    ax.set_xlabel("baseline y ruta")
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_error_by_hour(error_by_hour: pd.DataFrame, output_path: str | Path, run_id: str) -> None:
    """Plot final-test MAE by hour and baseline."""
    data = error_by_hour[error_by_hour["split"].eq("test_final")].copy()
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    for model, model_data in data.groupby("model"):
        hourly = model_data.groupby("hora_del_dia", as_index=False)["mae"].mean()
        ax.plot(hourly["hora_del_dia"], hourly["mae"], marker="o", lw=1.5, label=model)
    ax.set_xlabel("hora del dia")
    ax.set_ylabel("MAE")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_residuals(predictions: pd.DataFrame, output_path: str | Path, run_id: str) -> None:
    """Plot final-test residual distributions."""
    data = _final_test_observed(predictions)
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for model, model_data in data.groupby("model"):
        ax.hist(model_data["error"], bins=40, alpha=0.35, label=model)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("error = y_pred - y_real")
    ax.set_ylabel("frecuencia")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_backtesting_folds(folds: pd.DataFrame, output_path: str | Path, run_id: str) -> None:
    """Plot train, validation and final-test windows."""
    output_path = Path(output_path)
    backup_if_exists(output_path, run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = folds.copy()
    data["train_start"] = pd.to_datetime(data["train_start"])
    data["train_end"] = pd.to_datetime(data["train_end"])
    data["eval_start"] = pd.to_datetime(data["eval_start"])
    data["eval_end"] = pd.to_datetime(data["eval_end"])

    fig, ax = plt.subplots(figsize=(13, 6))
    y_positions = range(len(data))
    for y, (_, row) in zip(y_positions, data.iterrows(), strict=False):
        ax.hlines(
            y,
            row["train_start"],
            row["train_end"],
            color="#284B63",
            lw=5,
            label="train" if y == 0 else None,
        )
        color = "#D1495B" if row["split"] == "test_final" else "#F4A261"
        label = "test final" if row["split"] == "test_final" else ("validacion" if y == 0 else None)
        ax.hlines(y, row["eval_start"], row["eval_end"], color=color, lw=5, label=label)
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(data["fold"].astype(str))
    ax.set_xlabel("fecha")
    ax.set_ylabel("fold")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
