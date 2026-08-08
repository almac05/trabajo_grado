"""Run expanding-window backtesting for XGBoost, integrated with the baselines.

Registers ``xgboost_l2`` and ``xgboost_l1`` (configs/modeling/models.yaml)
alongside the 8 existing baselines and evaluates all of them on the same
38 validation folds + final test window, across the 3 multitarget scenarios.
"""

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
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_backtesting import _load_multitarget_datasets  # noqa: E402

from proyecto_grado.modeling.backtesting import run_multitarget_backtesting  # noqa: E402
from proyecto_grado.modeling.config import (  # noqa: E402
    backup_if_exists,
    file_sha256,
    load_backtesting_config,
    load_model_names,
    load_scenario_definitions,
    load_target_config,
    load_xgboost_model_names,
    make_run_id,
)
from proyecto_grado.modeling.features import feature_columns  # noqa: E402
from proyecto_grado.modeling.xgboost_models import (  # noqa: E402
    DEFAULT_EARLY_STOPPING_ROUNDS,
    DEFAULT_EARLY_STOPPING_WEEKS,
    DEFAULT_XGBOOST_PARAMS,
    XGBOOST_OBJECTIVES,
)
from proyecto_grado.modeling.xgboost_report import (  # noqa: E402
    build_importance_table,
    build_n_estimators_summary,
    build_objective_comparison,
    build_regime_metrics_by_fold,
    plot_error_evolution_by_fold,
    plot_importance_by_route,
    plot_regime_comparison,
    summarize_regime_metrics,
)

LOGGER = logging.getLogger("run_xgboost_backtesting")


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
    parser = argparse.ArgumentParser(
        description="Backtesting de XGBoost integrado con los baselines existentes"
    )
    parser.add_argument("--dataset-dir", default="data/processed/modeling")
    parser.add_argument("--targets-config", default="configs/modeling/targets.yaml")
    parser.add_argument("--backtesting-config", default="configs/modeling/backtesting.yaml")
    parser.add_argument("--models-config", default="configs/modeling/models.yaml")
    parser.add_argument("--tables-dir", default="reports/tables/modeling")
    parser.add_argument("--figures-dir", default="reports/figures/modeling")
    parser.add_argument("--metadata-dir", default="models/metadata")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-folds", type=int, default=None)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def _write_csv(df: pd.DataFrame, path: Path, run_id: str) -> Path | None:
    backup = backup_if_exists(path, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return backup


def main() -> None:
    """Run baselines + XGBoost backtesting and persist all Phase-3 artifacts."""
    _setup_logging()
    args = parse_args()
    run_id = args.run_id or make_run_id("xgboost")

    target_cfg = load_target_config(args.targets_config)
    bt_cfg = load_backtesting_config(args.backtesting_config)
    baseline_names = load_model_names(args.models_config)
    xgboost_names = load_xgboost_model_names(args.models_config)
    if not xgboost_names:
        raise ValueError("configs/modeling/models.yaml no registra modelos xgboost_models")
    model_names = baseline_names + xgboost_names
    scenarios = load_scenario_definitions(args.models_config)

    dataset_dir = _resolve_project_path(args.dataset_dir)
    tables_dir = _resolve_project_path(args.tables_dir)
    figures_dir = _resolve_project_path(args.figures_dir)
    metadata_dir = _resolve_project_path(args.metadata_dir)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    datasets, scenario_specs, dataset_paths = _load_multitarget_datasets(
        dataset_dir=dataset_dir,
        target_cfg=target_cfg,
        scenarios=scenarios,
    )
    dataset = next(iter(datasets.values()))

    if not args.quiet:
        print("\nRUN_XGBOOST_BACKTESTING.PY - INICIO")
        print(f"  run_id: {run_id}")
        print(f"  escenarios: {', '.join(datasets)}")
        print(f"  baselines: {', '.join(baseline_names)}")
        print(f"  xgboost: {', '.join(xgboost_names)}")
        print(f"  dataset base shape: {dataset.shape}")

    predictions, metrics_by_fold, metrics_comparison, folds, diagnostics = (
        run_multitarget_backtesting(
            datasets=datasets,
            scenario_specs=scenario_specs,
            model_names=model_names,
            run_id=run_id,
            test_weeks=bt_cfg.test_weeks,
            validation_weeks=bt_cfg.validation_weeks,
            step_weeks=bt_cfg.step_weeks,
            min_train_weeks=bt_cfg.min_train_weeks,
            horizon=target_cfg.horizon,
            granularity_min=target_cfg.granularity_min,
            operational_day_start=bt_cfg.operational_day_start,
            require_full_operational_days=bt_cfg.require_full_operational_days,
            max_folds=args.max_folds,
            verbose=not args.quiet,
        )
    )

    # --- Analisis Fase 3: regimen, importancia, comparacion de objetivos ---
    regime_by_fold = build_regime_metrics_by_fold(predictions)
    regime_summary = summarize_regime_metrics(regime_by_fold)
    importance_table = build_importance_table(diagnostics)
    n_estimators_summary = build_n_estimators_summary(diagnostics)
    objective_comparison = build_objective_comparison(metrics_by_fold)

    outputs = {
        "predictions": tables_dir / f"predictions_multitarget_{run_id}.parquet",
        "metrics_comparison": tables_dir / f"metrics_comparison_{run_id}.csv",
        "metrics_by_fold": tables_dir / f"metrics_by_fold_{run_id}.csv",
        "folds": tables_dir / f"backtesting_folds_{run_id}.csv",
        "xgb_por_regimen": tables_dir / f"xgb_por_regimen_{run_id}.csv",
        "xgb_importancia": tables_dir / f"xgb_importancia_{run_id}.csv",
        "xgb_objetivos": tables_dir / f"xgb_objetivos_{run_id}.csv",
        "xgb_n_estimators": tables_dir / f"xgb_n_estimators_{run_id}.csv",
    }
    backups = {
        "predictions": backup_if_exists(outputs["predictions"], run_id),
        "metrics_comparison": _write_csv(metrics_comparison, outputs["metrics_comparison"], run_id),
        "metrics_by_fold": _write_csv(metrics_by_fold, outputs["metrics_by_fold"], run_id),
        "folds": _write_csv(folds, outputs["folds"], run_id),
        "xgb_por_regimen": _write_csv(regime_summary, outputs["xgb_por_regimen"], run_id),
        "xgb_importancia": _write_csv(importance_table, outputs["xgb_importancia"], run_id),
        "xgb_objetivos": _write_csv(objective_comparison, outputs["xgb_objetivos"], run_id),
        "xgb_n_estimators": _write_csv(n_estimators_summary, outputs["xgb_n_estimators"], run_id),
    }
    outputs["predictions"].parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(outputs["predictions"], index=False)

    # --- Figuras ---
    figures_dir.mkdir(parents=True, exist_ok=True)
    for model_name in xgboost_names:
        model_importance = importance_table[importance_table["model"].eq(model_name)]
        if not model_importance.empty:
            plot_importance_by_route(
                model_importance,
                figures_dir / f"xgb_importancia_{model_name}_{run_id}.png",
                run_id,
            )
    if not regime_summary.empty:
        plot_regime_comparison(
            regime_summary,
            figures_dir / f"xgb_regimen_{run_id}.png",
            run_id,
        )
    plot_error_evolution_by_fold(
        metrics_by_fold,
        figures_dir / f"xgb_evolucion_error_{run_id}.png",
        run_id,
        models=[*xgboost_names, "rolling_average_8w"],
    )

    # --- Metadatos ---
    feature_columns_by_scenario = {
        name: feature_columns(spec["feature_set"]) for name, spec in scenario_specs.items()
    }
    run_metadata = {
        "run_id": run_id,
        "models": model_names,
        "baseline_models": baseline_names,
        "xgboost_models": xgboost_names,
        "xgboost_objectives": XGBOOST_OBJECTIVES,
        "xgboost_hyperparameters": DEFAULT_XGBOOST_PARAMS,
        "xgboost_early_stopping_rounds": DEFAULT_EARLY_STOPPING_ROUNDS,
        "xgboost_early_stopping_weeks": DEFAULT_EARLY_STOPPING_WEEKS,
        "one_model_per_route": True,
        "route_indicator_excluded_from_features": "FK_RUTA se excluye por ruta (constante).",
        "scenarios": list(datasets),
        "feature_columns_by_scenario": feature_columns_by_scenario,
        "dataset_paths": dataset_paths,
        "dataset_hashes_sha256": {
            key: file_sha256(path) for key, path in dataset_paths.items() if Path(path).exists()
        },
        "backtesting_config": {
            "test_weeks": bt_cfg.test_weeks,
            "validation_weeks": bt_cfg.validation_weeks,
            "step_weeks": bt_cfg.step_weeks,
            "min_train_weeks": bt_cfg.min_train_weeks,
            "seed": bt_cfg.seed,
            "operational_day_start": bt_cfg.operational_day_start,
        },
        "n_folds_validation": int(
            folds.loc[folds["split"].eq("validation"), "fold"].astype(str).nunique()
        ),
        "mlflow_tracking": "no configurado en este repositorio; se omite por decision explicita "
        "(ver metadatos JSON como registro de la corrida).",
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    metadata_path = metadata_dir / f"xgboost_{run_id}.json"
    backup_if_exists(metadata_path, run_id)
    metadata_path.write_text(
        json.dumps(run_metadata, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("\nRUN XGBOOST BACKTESTING")
    print(f"run_id: {run_id}")
    print(f"predicciones: {outputs['predictions']}")
    print(f"folds validacion: {run_metadata['n_folds_validation']}")
    print("\nmetricas comparacion (test_final):")
    display_cols = [
        c
        for c in ["target", "scenario", "split", "model", "route", "n", "mae", "wape", "bias_mean"]
        if c in metrics_comparison.columns
    ]
    test_final = metrics_comparison[metrics_comparison["split"].eq("test_final")]
    print(test_final[display_cols].round(3).to_string(index=False))
    if any(backups.values()):
        print("\nrespaldos creados:")
        for key, value in backups.items():
            if value is not None:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
