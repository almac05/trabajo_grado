"""Build modeling figures and a compact Markdown report for baseline runs."""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--metrics-common-path", default=None)
    parser.add_argument("--bias-path", default=None)
    parser.add_argument("--coverage-path", default=None)
    parser.add_argument("--metadata-path", default=None)
    parser.add_argument("--tables-dir", default="reports/tables/modeling")
    parser.add_argument("--figures-dir", default="reports/figures/modeling")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--multitarget", action="store_true")
    parser.add_argument(
        "--versioned-outputs",
        action="store_true",
        help="Incluye run_id en el reporte multitarget generado.",
    )
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
    if args.multitarget:
        metrics_common = (
            pd.read_csv(_resolve_project_path(args.metrics_common_path))
            if args.metrics_common_path
            else pd.DataFrame()
        )
        bias = (
            pd.read_csv(_resolve_project_path(args.bias_path)) if args.bias_path else pd.DataFrame()
        )
        coverage = (
            pd.read_csv(_resolve_project_path(args.coverage_path))
            if args.coverage_path
            else pd.DataFrame()
        )
        metadata = {}
        if args.metadata_path:
            metadata = json.loads(
                _resolve_project_path(args.metadata_path).read_text(encoding="utf-8")
            )

        report_name = (
            f"reporte_refactor_multitarget_{run_id}.md"
            if args.versioned_outputs
            else "reporte_refactor_multitarget.md"
        )
        report_path = tables_dir / report_name
        backup_if_exists(report_path, run_id)
        final_metrics = metrics[metrics["split"].eq("test_final")].copy()
        selected_metric_cols = [
            col
            for col in [
                "target",
                "scenario",
                "model",
                "route",
                "n",
                "mae",
                "rmse",
                "smape",
                "wape",
                "bias_mean",
                "bias_to_mae_ratio",
            ]
            if col in final_metrics.columns
        ]
        coverage_cols = [
            col
            for col in [
                "target",
                "scenario",
                "split",
                "route",
                "rows",
                "evaluable_rows",
                "gap_rows",
                "pct_evaluable",
                "pct_gap",
            ]
            if col in coverage.columns
        ]
        bias_cols = [
            col
            for col in [
                "target",
                "scenario",
                "model",
                "route",
                "n",
                "mae",
                "wape",
                "bias_mean",
                "bias_level",
            ]
            if col in bias.columns
        ]
        lines = [
            "# Reporte refactor multitarget",
            "",
            "## A. Alcance",
            "",
            "Se ejecutan baselines simples para dos objetivos y tres escenarios, sin modelos avanzados.",
            "",
            "## B. Fuente y version",
            "",
            f"run_id: `{run_id}`",
            f"predicciones: `{predictions_path}`",
            f"filas de prediccion: `{len(predictions):,}`",
            f"dataset_version: `{predictions['dataset_version'].iloc[0] if not predictions.empty else ''}`",
            "",
            "## C. Objetivos",
            "",
            "- `pasajeros_total`: demanda agregada por ruta y franja.",
            "- `pasajeros_por_despacho`: productividad observada por despacho real.",
            "",
            "## D. Escenarios",
            "",
            "- `sin_oferta`: calendario, ruta, lags y rolling de demanda.",
            "- `oferta_historica_rezagada`: agrega solo despachos reales rezagados.",
            "- `productividad_por_despacho`: predice productividad sin multiplicar por oferta futura.",
            "",
            "## E. Control de fuga temporal",
            "",
            "Todas las lags usan observaciones anteriores por ruta; las rolling features se calculan con `shift(1)`.",
            "`origin_timestamp`, `target_interval_start` y `feature_cutoff_timestamp` coinciden al inicio de la franja para `horizon=1`.",
            "",
            "## F. Backtesting",
            "",
            _markdown_table(
                folds[
                    [
                        col
                        for col in [
                            "target",
                            "scenario",
                            "split",
                            "fold",
                            "train_start",
                            "train_end",
                            "eval_start",
                            "eval_end",
                        ]
                        if col in folds.columns
                    ]
                ].head(20)
            ),
            "",
            "## G. Baselines",
            "",
            "- `naive`: usa lag 1.",
            "- `seasonal_naive_daily`: usa lag 48 en granularidad de 30 minutos.",
            "- `seasonal_naive_weekly`: usa lag 336 en granularidad de 30 minutos.",
            "- `historical_average_route_day_type_slot`: promedio historico de train por ruta, tipo de dia y franja.",
            "",
            "## H. Metricas test final",
            "",
            _markdown_table(final_metrics[selected_metric_cols].round(3)),
            "",
            "## I. Metricas sobre soporte comun",
            "",
            _markdown_table(
                metrics_common.round(3) if not metrics_common.empty else metrics_common
            ),
            "",
            "## J. Sesgo test final",
            "",
            _markdown_table(bias[bias_cols].round(3) if bias_cols else bias),
            "",
            "## K. Cobertura y gaps",
            "",
            _markdown_table(coverage[coverage_cols].round(3) if coverage_cols else coverage),
            "",
            "## L. Artefactos",
            "",
            f"- `{predictions_path}`",
            f"- `{metrics_path}`",
            f"- `{folds_path}`",
            f"- `{args.metrics_common_path or ''}`",
            f"- `{args.bias_path or ''}`",
            f"- `{args.coverage_path or ''}`",
            "",
            "## M. Comandos de reproduccion",
            "",
            "```powershell",
            "python scripts/build_modeling_dataset.py --multitarget",
            "python scripts/run_backtesting.py --multitarget",
            "python scripts/evaluate_models.py --multitarget --predictions-path reports/tables/modeling/predictions_multitarget_<run_id>.parquet",
            "python scripts/build_modeling_report.py --multitarget --predictions-path reports/tables/modeling/predictions_multitarget_<run_id>.parquet --metrics-path reports/tables/modeling/metrics_comparison_multitarget.csv --folds-path reports/tables/modeling/backtesting_folds_multitarget.csv --metrics-common-path reports/tables/modeling/metrics_common_support_multitarget.csv --bias-path reports/tables/modeling/bias_summary_test_final_multitarget.csv --coverage-path reports/tables/modeling/target_coverage_summary.csv",
            "```",
        ]
        if metadata:
            lines.insert(6, f"metadata: `{args.metadata_path}`")
        report_path.write_text("\n".join(lines), encoding="utf-8")

        print("\nBUILD MODELING REPORT MULTITARGET")
        print(f"reporte: {report_path}")
        return

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
