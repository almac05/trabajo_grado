"""Build the leakage-safe modeling dataset from the official snapshot.

Usage:
    python scripts/build_modeling_dataset.py
    python scripts/build_modeling_dataset.py --sample-days 120 --output-path .pytest_tmp/modeling_sample/modeling_dataset.parquet
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from proyecto_grado.modeling.config import (  # noqa: E402
    ModelingPaths,
    ensure_modeling_dirs,
    load_scenario_definitions,
    load_target_config,
    load_yaml,
    make_run_id,
)
from proyecto_grado.modeling.dataset import (  # noqa: E402
    build_modeling_dataset,
    build_multitarget_datasets,
    save_modeling_dataset,
    save_multitarget_datasets,
)

LOGGER = logging.getLogger("build_modeling_dataset")


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
    parser = argparse.ArgumentParser(description="Construye dataset de modelado g30min")
    parser.add_argument("--targets-config", default="configs/modeling/targets.yaml")
    parser.add_argument("--source-path", default=None)
    parser.add_argument(
        "--output-path",
        default="data/processed/modeling/modeling_dataset_g30min.parquet",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed/modeling",
        help="Directorio para datasets multitarget por escenario.",
    )
    parser.add_argument("--models-config", default="configs/modeling/models.yaml")
    parser.add_argument(
        "--series-dir",
        default="data/processed/modeling/time_series",
    )
    parser.add_argument("--metadata-dir", default="models/metadata")
    parser.add_argument("--sample-days", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--no-save-series", action="store_true")
    parser.add_argument("--multitarget", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run dataset construction and persistence."""
    _setup_logging()
    args = parse_args()
    target_cfg = load_target_config(args.targets_config)
    raw_cfg = load_yaml(args.targets_config)
    source_path = _resolve_project_path(
        args.source_path or raw_cfg.get("source_path", ModelingPaths().source_path)
    )
    output_path = _resolve_project_path(args.output_path)
    run_id = args.run_id or make_run_id("dataset")
    np.random.seed(42)

    paths = ModelingPaths(
        source_path=source_path,
        dataset_path=output_path,
        time_series_dir=_resolve_project_path(args.series_dir),
        metadata_dir=_resolve_project_path(args.metadata_dir),
    )
    ensure_modeling_dirs(paths)

    LOGGER.info("Fuente oficial: %s", source_path)
    LOGGER.info("Version dataset: %s", target_cfg.dataset_version)
    if args.multitarget:
        scenarios = load_scenario_definitions(args.models_config)
        datasets, metadata, route_series = build_multitarget_datasets(
            source_path=source_path,
            cfg=target_cfg,
            scenarios=scenarios,
            sample_days=args.sample_days,
        )
        backups = save_multitarget_datasets(
            datasets=datasets,
            metadata=metadata,
            route_series=route_series,
            scenarios=scenarios,
            output_dir=_resolve_project_path(args.output_dir),
            run_id=run_id,
            paths=paths,
            save_series=not args.no_save_series,
        )
        dataset = next(iter(datasets.values()))
    else:
        dataset, metadata, route_series = build_modeling_dataset(
            source_path=source_path,
            cfg=target_cfg,
            sample_days=args.sample_days,
        )
        backups = save_modeling_dataset(
            dataset=dataset,
            metadata=metadata,
            route_series=route_series,
            output_path=output_path,
            run_id=run_id,
            paths=paths,
            save_series=not args.no_save_series,
        )

    print("\nBUILD MODELING DATASET")
    print(f"run_id: {run_id}")
    print(
        f"dataset: {output_path if not args.multitarget else _resolve_project_path(args.output_dir)}"
    )
    print(f"filas: {len(dataset):,}")
    print(f"observadas: {int(dataset['target_observed'].sum()):,}")
    print(f"gaps dentro del dataset: {int(dataset['is_gap'].sum()):,}")
    print(f"rango: {dataset['timestamp'].min()} -> {dataset['timestamp'].max()}")
    print(f"hash fuente: {metadata['source_hash_sha256']}")
    if "dataset_hash_sha256" in metadata:
        print(f"hash dataset: {metadata['dataset_hash_sha256']}")
    if args.multitarget:
        print("datasets por escenario:")
        for scenario_name, payload in metadata["scenarios"].items():
            print(
                "  "
                f"{scenario_name}: {payload['dataset_path']} | "
                f"filas={payload['rows']:,} observadas={payload['observed_rows']:,}"
            )
    if any(backups.values()):
        print("respaldos creados:")
        for key, value in backups.items():
            if value is not None:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
