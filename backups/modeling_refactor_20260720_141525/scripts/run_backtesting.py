"""Run expanding-window backtesting for baseline models."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from proyecto_grado.modeling.backtesting import run_baseline_backtesting  # noqa: E402
from proyecto_grado.modeling.config import (  # noqa: E402
    backup_if_exists,
    file_sha256,
    load_backtesting_config,
    load_model_names,
    load_target_config,
    make_run_id,
)

LOGGER = logging.getLogger("run_backtesting")


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
    parser = argparse.ArgumentParser(description="Ejecuta backtesting de baselines")
    parser.add_argument(
        "--dataset-path",
        default="data/processed/modeling/modeling_dataset_g30min.parquet",
    )
    parser.add_argument("--targets-config", default="configs/modeling/targets.yaml")
    parser.add_argument("--backtesting-config", default="configs/modeling/backtesting.yaml")
    parser.add_argument("--models-config", default="configs/modeling/models.yaml")
    parser.add_argument("--tables-dir", default="reports/tables/modeling")
    parser.add_argument("--metadata-dir", default="models/metadata")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-folds", type=int, default=None)
    parser.add_argument("--test-weeks", type=int, default=None)
    parser.add_argument("--validation-weeks", type=int, default=None)
    parser.add_argument("--step-weeks", type=int, default=None)
    parser.add_argument("--min-train-weeks", type=int, default=None)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce los prints explicativos fold por fold.",
    )
    return parser.parse_args()


def _write_frame(df: pd.DataFrame, path: Path, run_id: str, parquet: bool = False) -> Path | None:
    backup = backup_if_exists(path, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if parquet:
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    return backup


def main() -> None:
    """Run baselines and persist predictions plus metrics."""
    _setup_logging()
    args = parse_args()
    target_cfg = load_target_config(args.targets_config)
    bt_cfg = load_backtesting_config(args.backtesting_config)
    model_names = load_model_names(args.models_config)
    run_id = args.run_id or make_run_id("baselines")
    np.random.seed(bt_cfg.seed)

    dataset_path = _resolve_project_path(args.dataset_path)
    tables_dir = _resolve_project_path(args.tables_dir)
    metadata_dir = _resolve_project_path(args.metadata_dir)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    dataset = pd.read_parquet(dataset_path)
    if not args.quiet:
        print("\nRUN_BACKTESTING.PY - INICIO")
        print(f"  dataset_path: {dataset_path}")
        print(f"  targets_config: {_resolve_project_path(args.targets_config)}")
        print(f"  backtesting_config: {_resolve_project_path(args.backtesting_config)}")
        print(f"  models_config: {_resolve_project_path(args.models_config)}")
        print(f"  tables_dir: {tables_dir}")
        print(f"  metadata_dir: {metadata_dir}")
        print(f"  run_id: {run_id}")
        print(f"  seed: {bt_cfg.seed}")
        print(f"  dataset shape: {dataset.shape}")
        print(f"  dataset timestamp: {dataset['timestamp'].min()} -> {dataset['timestamp'].max()}")
        print(f"  modelos cargados: {', '.join(model_names)}")
        print("  Nota: train y valid/test se separan por tiempo; no se usa shuffle.")

    predictions, metrics_by_fold, metrics_comparison, folds = run_baseline_backtesting(
        dataset=dataset,
        model_names=model_names,
        run_id=run_id,
        test_weeks=args.test_weeks or bt_cfg.test_weeks,
        validation_weeks=args.validation_weeks or bt_cfg.validation_weeks,
        step_weeks=args.step_weeks or bt_cfg.step_weeks,
        min_train_weeks=args.min_train_weeks or bt_cfg.min_train_weeks,
        horizon=target_cfg.horizon,
        granularity_min=target_cfg.granularity_min,
        max_folds=args.max_folds,
        verbose=not args.quiet,
    )

    outputs = {
        "predictions": tables_dir / "predictions_baselines.parquet",
        "metrics_by_fold": tables_dir / "metrics_by_fold.csv",
        "metrics_comparison": tables_dir / "metrics_comparison.csv",
        "folds": tables_dir / "backtesting_folds.csv",
    }
    backups = {
        "predictions": _write_frame(predictions, outputs["predictions"], run_id, parquet=True),
        "metrics_by_fold": _write_frame(metrics_by_fold, outputs["metrics_by_fold"], run_id),
        "metrics_comparison": _write_frame(
            metrics_comparison, outputs["metrics_comparison"], run_id
        ),
        "folds": _write_frame(folds, outputs["folds"], run_id),
    }

    run_metadata = {
        "run_id": run_id,
        "dataset_path": str(dataset_path),
        "dataset_hash_sha256": file_sha256(dataset_path),
        "models": model_names,
        "n_folds_validation": int(folds["split"].eq("validation").sum()),
        "includes_final_test": bool(folds["split"].eq("test_final").any()),
        "target_config": target_cfg.__dict__,
        "backtesting_config": {
            "test_weeks": args.test_weeks or bt_cfg.test_weeks,
            "validation_weeks": args.validation_weeks or bt_cfg.validation_weeks,
            "step_weeks": args.step_weeks or bt_cfg.step_weeks,
            "min_train_weeks": args.min_train_weeks or bt_cfg.min_train_weeks,
            "seed": bt_cfg.seed,
        },
    }
    metadata_path = metadata_dir / f"run_{run_id}.json"
    backup_if_exists(metadata_path, run_id)
    metadata_path.write_text(
        json.dumps(run_metadata, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("\nRUN BASELINE BACKTESTING")
    print(f"run_id: {run_id}")
    print(f"dataset: {dataset_path}")
    print(f"folds validacion: {run_metadata['n_folds_validation']}")
    print(f"predicciones: {len(predictions):,}")
    print(f"periodo total: {dataset['timestamp'].min()} -> {dataset['timestamp'].max()}")
    print("\nventanas:")
    print(folds.to_string(index=False))
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
