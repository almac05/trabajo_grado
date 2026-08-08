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
    parser.add_argument("--multitarget", action="store_true")
    return parser.parse_args()


def _write_csv(df: pd.DataFrame, path: Path, run_id: str) -> Path | None:
    backup = backup_if_exists(path, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return backup


def build_metrics_common_support(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute model metrics only on rows evaluable by every model.

    A row belongs to the common support when all detected models have a
    non-null real value and a non-null prediction for the same split, fold,
    route, timestamp and horizon. This avoids comparing models on different
    sets of time slots when lag-based baselines have missing predictions.
    """
    model_names = sorted(predictions["model"].dropna().unique().tolist())
    if not model_names:
        return pd.DataFrame()

    key_cols = [
        "dataset_version",
        "run_id",
        "target",
        "scenario",
        "feature_set",
        "split",
        "fold",
        "route",
        "granularity_min",
        "horizon",
        "timestamp",
    ]
    key_cols = [col for col in key_cols if col in predictions.columns]

    data = predictions.copy()
    data["_is_evaluable"] = data["y_real"].notna() & data["y_pred"].notna()
    support = (
        data.groupby(key_cols, dropna=False)
        .agg(
            n_models=("model", "nunique"),
            n_evaluable=("_is_evaluable", "sum"),
        )
        .reset_index()
    )
    support = support[
        support["n_models"].eq(len(model_names)) & support["n_evaluable"].eq(len(model_names))
    ]
    common = predictions.merge(support[key_cols], on=key_cols, how="inner")
    group_cols = [
        col
        for col in ["target", "scenario", "feature_set", "split", "model", "route"]
        if col in common.columns
    ]
    metrics = metrics_by_group(common, group_cols)
    metrics["support_type"] = "common_all_models"
    metrics["models_required"] = ", ".join(model_names)
    return metrics


def _bias_direction(value: float) -> str:
    if value > 0:
        return "sobreestima"
    if value < 0:
        return "subestima"
    return "sin_sesgo"


def _bias_level(row: pd.Series) -> str:
    mae = float(row["mae"]) if pd.notna(row["mae"]) else 0.0
    if mae == 0:
        return "No disponible"
    ratio = abs(float(row["bias_mean"])) / mae
    if ratio >= 0.5:
        return "alto"
    if ratio >= 0.2:
        return "moderado"
    return "bajo"


def build_bias_summary_test_final(metrics_comparison: pd.DataFrame) -> pd.DataFrame:
    """Summarize final-test bias direction and relative magnitude."""
    required = {"split", "model", "route", "n", "mae", "wape", "bias_mean"}
    missing = required.difference(metrics_comparison.columns)
    if missing:
        raise ValueError(f"Faltan columnas para resumen de sesgo: {sorted(missing)}")

    data = metrics_comparison[metrics_comparison["split"].eq("test_final")].copy()
    if data.empty:
        return pd.DataFrame()

    data["bias_abs"] = data["bias_mean"].abs()
    data["bias_direction"] = data["bias_mean"].map(_bias_direction)
    data["bias_to_mae_ratio"] = data["bias_abs"] / data["mae"]
    data["bias_level"] = data.apply(_bias_level, axis=1)
    data["interpretacion"] = (
        data["bias_direction"] + " con sesgo " + data["bias_level"] + " frente al MAE en test final"
    )
    prefix_cols = [col for col in ["target", "scenario", "feature_set"] if col in data.columns]
    cols = [
        *prefix_cols,
        "model",
        "route",
        "n",
        "mae",
        "wape",
        "bias_mean",
        "bias_abs",
        "bias_to_mae_ratio",
        "bias_direction",
        "bias_level",
        "interpretacion",
    ]
    sort_cols = [*prefix_cols, "route", "model"]
    return data[cols].sort_values(sort_cols).reset_index(drop=True)


def build_target_coverage_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarize target and prediction coverage by target/scenario/split."""
    group_cols = [
        col for col in ["target", "scenario", "split", "route"] if col in predictions.columns
    ]
    if not group_cols:
        group_cols = ["split", "route"]
    data = predictions.copy()
    data["_y_real_present"] = data["y_real"].notna()
    data["_y_pred_present"] = data["y_pred"].notna()
    data["_evaluable"] = data["_y_real_present"] & data["_y_pred_present"]
    data["_gap"] = data["is_gap"].astype(bool) if "is_gap" in data.columns else False
    summary = (
        data.groupby(group_cols, dropna=False)
        .agg(
            rows=("y_real", "size"),
            y_real_present=("_y_real_present", "sum"),
            y_pred_present=("_y_pred_present", "sum"),
            evaluable_rows=("_evaluable", "sum"),
            gap_rows=("_gap", "sum"),
        )
        .reset_index()
    )
    summary["pct_evaluable"] = summary["evaluable_rows"] / summary["rows"] * 100.0
    summary["pct_gap"] = summary["gap_rows"] / summary["rows"] * 100.0
    return summary


def main() -> None:
    """Evaluate predictions and persist metrics/error summaries."""
    _setup_logging()
    args = parse_args()
    run_id = args.run_id or make_run_id("evaluate")
    predictions_path = _resolve_project_path(args.predictions_path)
    tables_dir = _resolve_project_path(args.tables_dir)
    predictions = pd.read_parquet(predictions_path)

    group_prefix = [
        col for col in ["target", "scenario", "feature_set"] if col in predictions.columns
    ]
    metrics_by_fold = metrics_by_group(
        predictions,
        [*group_prefix, "split", "fold", "model", "route"],
    )
    metrics_comparison = metrics_by_group(
        predictions,
        [*group_prefix, "split", "model", "route"],
    )
    metrics_common_support = build_metrics_common_support(predictions)
    bias_summary_test_final = build_bias_summary_test_final(metrics_comparison)
    target_coverage_summary = build_target_coverage_summary(predictions)
    error_tables = build_error_tables(predictions)

    suffix = "_multitarget" if args.multitarget else ""

    outputs = {
        "metrics_by_fold": tables_dir / f"metrics_by_fold{suffix}.csv",
        "metrics_comparison": tables_dir / f"metrics_comparison{suffix}.csv",
        "metrics_common_support": tables_dir / f"metrics_common_support{suffix}.csv",
        "bias_summary_test_final": tables_dir / f"bias_summary_test_final{suffix}.csv",
        "target_coverage_summary": tables_dir / "target_coverage_summary.csv",
        "error_analysis_by_route": tables_dir / f"error_analysis_by_route{suffix}.csv",
        "error_analysis_by_hour": tables_dir / f"error_analysis_by_hour{suffix}.csv",
        "error_analysis_by_day_type": tables_dir / f"error_analysis_by_day_type{suffix}.csv",
        "error_analysis_by_target": tables_dir / "error_analysis_by_target.csv",
        "error_analysis_by_scenario": tables_dir / "error_analysis_by_scenario.csv",
        "error_analysis_by_dispatch_history_level": tables_dir
        / "error_analysis_by_dispatch_history_level.csv",
    }
    backups = {
        "metrics_by_fold": _write_csv(metrics_by_fold, outputs["metrics_by_fold"], run_id),
        "metrics_comparison": _write_csv(metrics_comparison, outputs["metrics_comparison"], run_id),
        "metrics_common_support": _write_csv(
            metrics_common_support,
            outputs["metrics_common_support"],
            run_id,
        ),
        "bias_summary_test_final": _write_csv(
            bias_summary_test_final,
            outputs["bias_summary_test_final"],
            run_id,
        ),
        "target_coverage_summary": _write_csv(
            target_coverage_summary,
            outputs["target_coverage_summary"],
            run_id,
        ),
        "error_analysis_by_route": _write_csv(
            error_tables["by_route"],
            outputs["error_analysis_by_route"],
            run_id,
        ),
        "error_analysis_by_hour": _write_csv(
            error_tables["by_hour"],
            outputs["error_analysis_by_hour"],
            run_id,
        ),
        "error_analysis_by_day_type": _write_csv(
            error_tables["by_day_type"],
            outputs["error_analysis_by_day_type"],
            run_id,
        ),
        "error_analysis_by_target": _write_csv(
            error_tables["by_target"],
            outputs["error_analysis_by_target"],
            run_id,
        )
        if not error_tables["by_target"].empty
        else None,
        "error_analysis_by_scenario": _write_csv(
            error_tables["by_scenario"],
            outputs["error_analysis_by_scenario"],
            run_id,
        )
        if not error_tables["by_scenario"].empty
        else None,
        "error_analysis_by_dispatch_history_level": _write_csv(
            error_tables["by_dispatch_history_level"],
            outputs["error_analysis_by_dispatch_history_level"],
            run_id,
        )
        if not error_tables["by_dispatch_history_level"].empty
        else None,
    }

    print("\nEVALUATE MODELS")
    print(f"predicciones: {predictions_path}")
    print(f"filas prediccion: {len(predictions):,}")
    print("\nmetricas comparacion:")
    display_cols = [
        col
        for col in [
            "target",
            "scenario",
            "split",
            "model",
            "route",
            "n",
            "mae",
            "rmse",
            "smape",
            "wape",
            "bias_mean",
        ]
        if col in metrics_comparison.columns
    ]
    print(metrics_comparison[display_cols].round(3).to_string(index=False))
    print("\nmetricas soporte comun:")
    print(metrics_common_support[display_cols].round(3).to_string(index=False))
    print("\nresumen sesgo test final:")
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
        if col in bias_summary_test_final.columns
    ]
    print(bias_summary_test_final[bias_cols].round(3).to_string(index=False))
    print("\ncobertura targets:")
    print(target_coverage_summary.round(3).to_string(index=False))
    if any(backups.values()):
        print("\nrespaldos creados:")
        for key, value in backups.items():
            if value is not None:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
