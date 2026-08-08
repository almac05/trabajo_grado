"""Evaluate persisted baseline predictions and build error-analysis tables."""

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
from proyecto_grado.modeling.error_analysis import build_error_tables  # noqa: E402
from proyecto_grado.modeling.evaluate import metrics_by_group  # noqa: E402

LOGGER = logging.getLogger("evaluate_models")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Evalua predicciones de modelos")
    parser.add_argument(
        "--predictions-path",
        default="reports/tables/modeling/predictions_baselines.parquet",
    )
    parser.add_argument("--tables-dir", default="reports/tables/modeling")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def _write_csv(df: pd.DataFrame, path: Path, run_id: str) -> Path | None:
    backup = backup_if_exists(path, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return backup


def main() -> None:
    """Evaluate predictions and persist metrics/error summaries."""
    _setup_logging()
    args = parse_args()
    run_id = args.run_id or make_run_id("evaluate")
    predictions_path = _resolve_project_path(args.predictions_path)
    tables_dir = _resolve_project_path(args.tables_dir)
    predictions = pd.read_parquet(predictions_path)

    metrics_by_fold = metrics_by_group(predictions, ["split", "fold", "model", "route"])
    metrics_comparison = metrics_by_group(predictions, ["split", "model", "route"])
    error_tables = build_error_tables(predictions)

    outputs = {
        "metrics_by_fold": tables_dir / "metrics_by_fold.csv",
        "metrics_comparison": tables_dir / "metrics_comparison.csv",
        "error_analysis_by_route": tables_dir / "error_analysis_by_route.csv",
        "error_analysis_by_hour": tables_dir / "error_analysis_by_hour.csv",
        "error_analysis_by_day_type": tables_dir / "error_analysis_by_day_type.csv",
    }
    backups = {
        "metrics_by_fold": _write_csv(metrics_by_fold, outputs["metrics_by_fold"], run_id),
        "metrics_comparison": _write_csv(metrics_comparison, outputs["metrics_comparison"], run_id),
        "error_analysis_by_route": _write_csv(
            error_tables["by_route"], outputs["error_analysis_by_route"], run_id
        ),
        "error_analysis_by_hour": _write_csv(
            error_tables["by_hour"], outputs["error_analysis_by_hour"], run_id
        ),
        "error_analysis_by_day_type": _write_csv(
            error_tables["by_day_type"], outputs["error_analysis_by_day_type"], run_id
        ),
    }

    print("\nEVALUATE MODELS")
    print(f"predicciones: {predictions_path}")
    print(f"filas prediccion: {len(predictions):,}")
    print("\nmetricas comparacion:")
    display_cols = ["split", "model", "route", "n", "mae", "rmse", "smape", "wape", "bias_mean"]
    print(metrics_comparison[display_cols].round(3).to_string(index=False))
    if any(backups.values()):
        print("\nrespaldos creados:")
        for key, value in backups.items():
            if value is not None:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
