"""Build modeling figures and a compact Markdown report for baseline runs."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from proyecto_grado.modeling.config import backup_if_exists, make_run_id  # noqa: E402
from proyecto_grado.modeling.error_analysis import (  # noqa: E402
    build_error_tables,
    plot_backtesting_folds,
    plot_error_by_hour,
    plot_metrics_comparison,
    plot_observed_vs_predicted,
    plot_residuals,
)

LOGGER = logging.getLogger("build_modeling_report")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _markdown_table(df: pd.DataFrame) -> str:
    """Render a small DataFrame as Markdown without optional dependencies."""
    if df.empty:
        return "_Sin datos._"
    data = df.astype(object).where(pd.notna(df), "")
    headers = [str(col) for col in data.columns]
    rows = ["| " + " | ".join(headers) + " |"]
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in data.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in data.columns) + " |")
    return "\n".join(rows)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Construye reporte y figuras de modelado")
    parser.add_argument(
        "--predictions-path",
        default="reports/tables/modeling/predictions_baselines.parquet",
    )
    parser.add_argument(
        "--metrics-path",
        default="reports/tables/modeling/metrics_comparison.csv",
    )
    parser.add_argument(
        "--folds-path",
        default="reports/tables/modeling/backtesting_folds.csv",
    )
    parser.add_argument("--tables-dir", default="reports/tables/modeling")
    parser.add_argument("--figures-dir", default="reports/figures/modeling")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> None:
    """Create figures and a short reproducibility report."""
    _setup_logging()
    args = parse_args()
    run_id = args.run_id or make_run_id("report")
    predictions_path = _resolve_project_path(args.predictions_path)
    metrics_path = _resolve_project_path(args.metrics_path)
    folds_path = _resolve_project_path(args.folds_path)
    tables_dir = _resolve_project_path(args.tables_dir)
    figures_dir = _resolve_project_path(args.figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    predictions = pd.read_parquet(predictions_path)
    metrics = pd.read_csv(metrics_path)
    folds = pd.read_csv(folds_path)
    error_tables = build_error_tables(predictions)

    output_figures = {
        "observed_vs_predicted": figures_dir / "observed_vs_predicted_baselines.png",
        "metrics_comparison": figures_dir / "metrics_comparison_baselines.png",
        "error_by_hour": figures_dir / "error_by_hour_baselines.png",
        "residuals": figures_dir / "residuals_baselines.png",
        "backtesting_folds": figures_dir / "backtesting_folds.png",
    }
    plot_observed_vs_predicted(predictions, output_figures["observed_vs_predicted"], run_id)
    plot_metrics_comparison(metrics, output_figures["metrics_comparison"], run_id)
    plot_error_by_hour(error_tables["by_hour"], output_figures["error_by_hour"], run_id)
    plot_residuals(predictions, output_figures["residuals"], run_id)
    plot_backtesting_folds(folds, output_figures["backtesting_folds"], run_id)

    report_path = tables_dir / "modeling_report_baselines.md"
    backup_if_exists(report_path, run_id)
    final_metrics = metrics[metrics["split"].eq("test_final")].copy()
    lines = [
        "# Reporte inicial de modelado - baselines",
        "",
        f"run_id: `{run_id}`",
        f"predicciones: `{predictions_path}`",
        "",
        "## Metricas test final",
        "",
        _markdown_table(
            final_metrics[
                ["model", "route", "n", "mae", "rmse", "smape", "wape", "bias_mean"]
            ].round(3)
        ),
        "",
        "## Figuras",
        "",
    ]
    for path in output_figures.values():
        lines.append(f"- `{path}`")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nBUILD MODELING REPORT")
    print(f"reporte: {report_path}")
    print("figuras:")
    for path in output_figures.values():
        print(f"  {path}")


if __name__ == "__main__":
    main()
