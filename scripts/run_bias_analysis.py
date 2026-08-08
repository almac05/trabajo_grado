"""Genera el analisis de sesgo (Parte B) sobre predicciones ya persistidas.

No recalcula predicciones; consume el parquet producido por
`run_backtesting.py --multitarget` y la tabla mensual de flota ya calculada
por `diagnostico_reduccion_flota.py`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from proyecto_grado.modeling.bias_analysis import (  # noqa: E402
    bias_by_slot,
    bias_decomposition,
    bias_monthly,
    bias_temporal_by_fold,
    bias_vs_fleet,
    temporal_bias_correlation,
)
from proyecto_grado.modeling.config import backup_if_exists, make_run_id  # noqa: E402

LOGGER = logging.getLogger("run_bias_analysis")

FIGURE_STYLE = {
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#6b7280",
    "axes.labelcolor": "#1f2933",
    "xtick.color": "#1f2933",
    "ytick.color": "#1f2933",
}
GRAYSCALE_SAFE_PALETTE = {
    "naive": "#6b7280",
    "seasonal_naive_daily": "#8a5a44",
    "seasonal_naive_weekly": "#4b78a8",
    "historical_average_route_day_type_slot": "#c0392b",
    "rolling_average_4w": "#2f6f73",
    "rolling_average_8w": "#5a8f3f",
    "rolling_average_12w": "#8e7cc3",
    "rolling_average_26w": "#1f2933",
}


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Analisis de sesgo de baselines")
    parser.add_argument("--predictions-path", required=True)
    parser.add_argument("--folds-path", required=True)
    parser.add_argument(
        "--fleet-monthly-path",
        default="reports/tables/baseline/diagnostico_flota_mensual.csv",
    )
    parser.add_argument("--tables-dir", default="reports/tables/modeling")
    parser.add_argument("--figures-dir", default="reports/figures/modeling")
    parser.add_argument("--metadata-dir", default="models/metadata")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--fleet-correlation-split",
        default="validation",
        help="Split usado para la correlacion sesgo-flota (necesita varios meses).",
    )
    return parser.parse_args()


def _style_axis(ax) -> None:
    ax.grid(True, which="major", axis="both", color="#d9dee3", linewidth=0.7, alpha=0.85)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#6b7280")
    ax.spines["bottom"].set_color("#6b7280")
    ax.tick_params(colors="#1f2933", labelsize=9)
    ax.axhline(0, color="#6b7280", linewidth=0.9, alpha=0.6)


def _color_for(model: str) -> str:
    return GRAYSCALE_SAFE_PALETTE.get(model, "#111827")


def _plot_bias_por_fold(bias_by_fold: pd.DataFrame, output_path: Path) -> None:
    data = bias_by_fold[bias_by_fold["split"].eq("validation")].dropna(
        subset=["distance_days", "bias_mean"]
    )
    if data.empty:
        return
    routes = sorted(data["route"].unique())
    fig, axes = plt.subplots(1, len(routes), figsize=(6.5 * len(routes), 4.8), sharey=True)
    axes = [axes] if len(routes) == 1 else list(axes)
    for ax, route in zip(axes, routes, strict=False):
        route_data = data[data["route"] == route]
        for model, group in route_data.groupby("model"):
            group = group.sort_values("distance_days")
            ax.plot(
                group["distance_days"],
                group["bias_mean"],
                marker="o",
                markersize=3.5,
                linewidth=1.4,
                label=model,
                color=_color_for(model),
                alpha=0.9,
            )
        ax.set_xlabel("Distancia train-center -> periodo predicho (dias)", fontsize=9)
        ax.set_ylabel("Sesgo medio (pasajeros)", fontsize=9)
        ax.set_title(f"Ruta {route}", loc="left", fontsize=10, fontweight="semibold")
        _style_axis(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.05))
    fig.tight_layout(pad=1.6)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_bias_mensual(monthly: pd.DataFrame, output_path: Path) -> None:
    if monthly.empty:
        return
    routes = sorted(monthly["route"].unique())
    fig, axes = plt.subplots(1, len(routes), figsize=(6.5 * len(routes), 4.8), sharey=True)
    axes = [axes] if len(routes) == 1 else list(axes)
    for ax, route in zip(axes, routes, strict=False):
        route_data = monthly[monthly["route"] == route]
        for model, group in route_data.groupby("model"):
            group = group.sort_values("mes")
            ax.plot(
                group["mes"],
                group["bias_mean"],
                marker="o",
                markersize=3.5,
                linewidth=1.4,
                label=model,
                color=_color_for(model),
                alpha=0.9,
            )
        ax.set_xlabel("Mes", fontsize=9)
        ax.set_ylabel("Sesgo medio (pasajeros)", fontsize=9)
        ax.set_title(f"Ruta {route}", loc="left", fontsize=10, fontweight="semibold")
        ax.tick_params(axis="x", rotation=35)
        _style_axis(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout(pad=1.6)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_bias_por_hora(by_slot: pd.DataFrame, output_path: Path) -> None:
    if by_slot.empty:
        return
    agg = (
        by_slot.groupby(["model", "route", "hora_del_dia"], as_index=False)
        .apply(lambda g: pd.Series({"bias_mean": (g["bias_mean"] * g["n"]).sum() / g["n"].sum()}))
        .reset_index(drop=True)
    )
    routes = sorted(agg["route"].unique())
    fig, axes = plt.subplots(1, len(routes), figsize=(6.5 * len(routes), 4.8), sharey=True)
    axes = [axes] if len(routes) == 1 else list(axes)
    for ax, route in zip(axes, routes, strict=False):
        route_data = agg[agg["route"] == route]
        for model, group in route_data.groupby("model"):
            group = group.sort_values("hora_del_dia")
            ax.plot(
                group["hora_del_dia"],
                group["bias_mean"],
                marker="o",
                markersize=3.5,
                linewidth=1.4,
                label=model,
                color=_color_for(model),
                alpha=0.9,
            )
        ax.set_xlabel("Hora del dia", fontsize=9)
        ax.set_ylabel("Sesgo medio (pasajeros)", fontsize=9)
        ax.set_title(f"Ruta {route}", loc="left", fontsize=10, fontweight="semibold")
        _style_axis(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout(pad=1.6)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_mae_vs_ventana(decomposition: pd.DataFrame, output_path: Path) -> None:
    data = decomposition[
        decomposition["split"].eq("test_final") & decomposition["scenario"].eq("sin_oferta")
    ].copy()
    if data.empty:
        return
    window_order = {
        "rolling_average_4w": 4,
        "rolling_average_8w": 8,
        "rolling_average_12w": 12,
        "rolling_average_26w": 26,
        "historical_average_route_day_type_slot": 999,
    }
    data = data[data["model"].isin(window_order)]
    data["ventana_semanas"] = data["model"].map(window_order)
    data = data.sort_values("ventana_semanas")

    routes = sorted(data["route"].unique())
    fig, axes = plt.subplots(1, len(routes), figsize=(6.5 * len(routes), 4.8))
    axes = [axes] if len(routes) == 1 else list(axes)
    for ax, route in zip(axes, routes, strict=False):
        route_data = data[data["route"] == route]
        ax2 = ax.twinx()
        ax.plot(
            route_data["ventana_semanas"],
            route_data["mae"],
            marker="o",
            color="#2f6f73",
            label="MAE",
        )
        ax2.plot(
            route_data["ventana_semanas"],
            route_data["bias_mean"].abs(),
            marker="s",
            color="#c0392b",
            label="|Sesgo medio|",
        )
        ax.set_xlabel("Ventana W (semanas; 999 = historico completo)", fontsize=9)
        ax.set_ylabel("MAE (pasajeros)", fontsize=9, color="#2f6f73")
        ax2.set_ylabel("|Sesgo medio| (pasajeros)", fontsize=9, color="#c0392b")
        ax.set_title(f"Ruta {route}", loc="left", fontsize=10, fontweight="semibold")
        _style_axis(ax)
    fig.tight_layout(pad=1.6)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Run the bias analysis and persist tables, figures and metadata."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = parse_args()
    run_id = args.run_id or make_run_id("bias_analysis")

    predictions_path = _resolve_project_path(args.predictions_path)
    folds_path = _resolve_project_path(args.folds_path)
    fleet_path = _resolve_project_path(args.fleet_monthly_path)
    tables_dir = _resolve_project_path(args.tables_dir)
    figures_dir = _resolve_project_path(args.figures_dir)
    metadata_dir = _resolve_project_path(args.metadata_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update(FIGURE_STYLE)

    predictions = pd.read_parquet(predictions_path)
    folds = pd.read_csv(folds_path)

    LOGGER.info("Predicciones cargadas: %s filas", f"{len(predictions):,}")

    decomposition = bias_decomposition(predictions)
    bias_by_fold = bias_temporal_by_fold(predictions, folds)
    correlation = temporal_bias_correlation(bias_by_fold)

    monthly_test = bias_monthly(predictions[predictions["split"].eq("test_final")].copy())
    monthly_validation = bias_monthly(
        predictions[predictions["split"].eq(args.fleet_correlation_split)].copy()
    )
    monthly_test["split"] = "test_final"
    monthly_validation["split"] = args.fleet_correlation_split
    bias_temporal_table = pd.concat(
        [bias_by_fold.assign(nivel="fold"), monthly_test.assign(nivel="mes_test")],
        ignore_index=True,
        sort=False,
    )

    fleet_monthly = pd.read_csv(fleet_path)
    fleet_correlation = (
        bias_vs_fleet(monthly_validation, fleet_monthly)
        if not monthly_validation.empty
        else pd.DataFrame()
    )

    by_slot = bias_by_slot(predictions[predictions["split"].eq("test_final")].copy())

    fallback_levels = pd.DataFrame()
    rolling_predictions = predictions[predictions["model"].str.startswith("rolling_average")]
    if not rolling_predictions.empty:
        fallback_levels = (
            rolling_predictions.groupby(["model", "target", "scenario", "route"])["fallback_level"]
            .value_counts(normalize=True)
            .rename("proportion")
            .reset_index()
        )
        fallback_levels["proportion_pct"] = (fallback_levels["proportion"] * 100).round(3)

    outputs = {
        "bias_decomposition": tables_dir / f"bias_decomposition_{run_id}.csv",
        "bias_temporal": tables_dir / f"bias_temporal_{run_id}.csv",
        "bias_temporal_correlation": tables_dir / f"bias_temporal_correlation_{run_id}.csv",
        "bias_by_slot": tables_dir / f"bias_by_slot_{run_id}.csv",
        "rolling_fallback_levels": tables_dir / f"rolling_fallback_levels_{run_id}.csv",
        "bias_vs_fleet": tables_dir / f"bias_vs_fleet_{run_id}.csv",
    }
    backups = {name: backup_if_exists(path, run_id) for name, path in outputs.items()}
    decomposition.to_csv(outputs["bias_decomposition"], index=False)
    bias_temporal_table.to_csv(outputs["bias_temporal"], index=False)
    correlation.to_csv(outputs["bias_temporal_correlation"], index=False)
    by_slot.to_csv(outputs["bias_by_slot"], index=False)
    fallback_levels.to_csv(outputs["rolling_fallback_levels"], index=False)
    fleet_correlation.to_csv(outputs["bias_vs_fleet"], index=False)

    figure_paths = {
        "bias_por_fold": figures_dir / f"bias_por_fold_{run_id}.png",
        "bias_mensual": figures_dir / f"bias_mensual_{run_id}.png",
        "bias_por_hora": figures_dir / f"bias_por_hora_{run_id}.png",
        "mae_vs_ventana": figures_dir / f"mae_vs_ventana_{run_id}.png",
    }
    _plot_bias_por_fold(bias_by_fold, figure_paths["bias_por_fold"])
    _plot_bias_mensual(monthly_test, figure_paths["bias_mensual"])
    _plot_bias_por_hora(by_slot, figure_paths["bias_por_hora"])
    _plot_mae_vs_ventana(decomposition, figure_paths["mae_vs_ventana"])

    metadata = {
        "run_id": run_id,
        "predictions_path": str(predictions_path),
        "folds_path": str(folds_path),
        "fleet_monthly_path": str(fleet_path),
        "fleet_correlation_split": args.fleet_correlation_split,
        "outputs": {k: str(v) for k, v in outputs.items()},
        "figures": {k: str(v) for k, v in figure_paths.items()},
        "n_predictions": len(predictions),
        "models": sorted(predictions["model"].dropna().unique().tolist()),
    }
    metadata_path = metadata_dir / f"bias_analysis_{run_id}.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    print("\nRUN BIAS ANALYSIS")
    print(f"run_id: {run_id}")
    print(f"predicciones: {predictions_path} ({len(predictions):,} filas)")
    print("\nDescomposicion de sesgo (test_final, sin_oferta):")
    display = decomposition[
        decomposition["split"].eq("test_final") & decomposition["scenario"].eq("sin_oferta")
    ][["model", "route", "n", "mae", "bias_mean", "bias_to_mae_ratio", "dispersion_fraction"]]
    print(display.round(3).to_string(index=False))
    print("\nCorrelacion sesgo vs distancia temporal (validation folds):")
    print(
        correlation[correlation["scenario"].eq("sin_oferta")][
            ["model", "route", "n_folds", "pearson_r", "pearson_p", "spearman_r", "spearman_p"]
        ]
        .round(4)
        .to_string(index=False)
    )
    if not fleet_correlation.empty:
        print("\nCorrelacion sesgo mensual vs vehiculos activos:")
        print(
            fleet_correlation[fleet_correlation["scenario"].eq("sin_oferta")][
                [
                    "model",
                    "route",
                    "n_meses",
                    "pearson_r_vehiculos_activos",
                    "pearson_ci95_low_vehiculos_activos",
                    "pearson_ci95_high_vehiculos_activos",
                ]
            ]
            .round(4)
            .to_string(index=False)
        )
    print("\ntablas:")
    for name, path in outputs.items():
        print(f"  {name}: {path}")
    print("\nfiguras:")
    for name, path in figure_paths.items():
        print(f"  {name}: {path}")
    if any(backups.values()):
        print("\nrespaldos creados:")
        for key, value in backups.items():
            if value is not None:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
