"""Build the leakage-safe modeling dataset from the official snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from proyecto_grado.features.time_series_builder import TimeSeriesBuilder
from proyecto_grado.modeling.config import (
    ModelingPaths,
    ScenarioDefinition,
    TargetConfig,
    backup_if_exists,
    file_sha256,
    scenario_dataset_path,
    target_definition,
)
from proyecto_grado.modeling.features import (
    DISPATCH_LAG_STEPS,
    LAG_STEPS,
    ROLLING_WINDOWS_MEAN,
    ROLLING_WINDOWS_STD,
    add_modeling_features,
    feature_columns,
    validate_lag_features,
)

REQUIRED_SOURCE_COLUMNS = {
    "PK_INTERVALO_DESPACHO",
    "FK_RUTA",
    "HORA_INICIAL_REAL",
    "PASAJEROS",
    "MODEL_READY_OK",
}

MODELING_COLUMNS = [
    "dataset_version",
    "source_hash",
    "timestamp",
    "target_interval_start",
    "target_interval_end",
    "feature_cutoff_timestamp",
    "FK_RUTA",
    "granularidad_min",
    "pasajeros_total",
    "despachos_count_real",
    "pasajeros_por_despacho_real",
    "target_pasajeros_total_observed",
    "target_pasajeros_por_despacho_observed",
    "target_observed",
    "is_gap",
    "gap_tipo",
    "dentro_horario_operativo",
    "hora_del_dia",
    "dia_semana",
    "mes",
    "semana_anio",
    "es_fin_semana",
    "es_festivo",
    "tipo_dia",
    "franja_horaria",
    "franja_30min",
    "pasajeros_total_lag_1",
    "pasajeros_total_lag_2",
    "pasajeros_total_lag_3",
    "pasajeros_total_lag_48",
    "pasajeros_total_lag_96",
    "pasajeros_total_lag_336",
    "pasajeros_total_rolling_mean_3",
    "pasajeros_total_rolling_mean_6",
    "pasajeros_total_rolling_mean_12",
    "pasajeros_total_rolling_std_6",
    "pasajeros_total_rolling_std_12",
    "pasajeros_por_despacho_lag_1",
    "pasajeros_por_despacho_lag_2",
    "pasajeros_por_despacho_lag_3",
    "pasajeros_por_despacho_lag_48",
    "pasajeros_por_despacho_lag_96",
    "pasajeros_por_despacho_lag_336",
    "pasajeros_por_despacho_rolling_mean_3",
    "pasajeros_por_despacho_rolling_mean_6",
    "pasajeros_por_despacho_rolling_mean_12",
    "pasajeros_por_despacho_rolling_std_6",
    "pasajeros_por_despacho_rolling_std_12",
    "despachos_count_real_lag_1",
    "despachos_count_real_lag_2",
    "despachos_count_real_lag_3",
    "despachos_count_real_lag_48",
    "despachos_count_real_lag_336",
    "despachos_count_real_rolling_mean_3",
    "despachos_count_real_rolling_mean_6",
    "despachos_count_real_rolling_mean_12",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_48",
    "lag_96",
    "lag_336",
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_mean_12",
    "rolling_std_6",
    "rolling_std_12",
    "hora_sin",
    "hora_cos",
    "dia_semana_sin",
    "dia_semana_cos",
]


def load_model_ready_snapshot(path: str | Path, routes: tuple[int, ...]) -> pd.DataFrame:
    """Load and validate the official model-ready snapshot."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el snapshot model-ready: {path}")

    df = pd.read_parquet(path)
    missing = REQUIRED_SOURCE_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas en model-ready: {sorted(missing)}")

    df = df.copy()
    df = df[df["MODEL_READY_OK"].eq(True)]
    df = df[df["FK_RUTA"].isin(routes)]
    if df.empty:
        raise ValueError("El snapshot no contiene filas validas para las rutas solicitadas")
    return df


def build_time_series(
    source_df: pd.DataFrame,
    cfg: TargetConfig,
) -> dict[int, pd.DataFrame]:
    """Regenerate route-level time series from the source snapshot."""
    builder_cfg: dict[str, Any] = {
        "granularidades_min": [cfg.granularity_min],
        "rutas": list(cfg.routes),
        "imputacion_gaps": cfg.gap_imputation,
    }
    builder = TimeSeriesBuilder(builder_cfg)
    series: dict[int, pd.DataFrame] = {}
    for route in cfg.routes:
        route_series = builder.build(
            source_df,
            ruta=route,
            granularidad_min=cfg.granularity_min,
        )
        if route_series.empty:
            raise ValueError(f"No se pudo construir serie para ruta {route}")
        series[route] = route_series
    return series


def build_modeling_dataset(
    source_path: str | Path,
    cfg: TargetConfig,
    sample_days: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], dict[int, pd.DataFrame]]:
    """Build the modeling dataset with leakage-safe features.

    Gaps are preserved as rows with ``is_gap=True`` and missing target values.
    Supervised metrics later exclude rows where ``target_observed`` is false.
    """
    source_path = Path(source_path)
    source_hash = file_sha256(source_path)
    source_df = load_model_ready_snapshot(source_path, cfg.routes)
    route_series = build_time_series(source_df, cfg)

    full = pd.concat(route_series.values(), ignore_index=True)
    full["dataset_version"] = cfg.dataset_version
    full["source_hash"] = source_hash

    featured = add_modeling_features(full, target_col=cfg.target)
    validate_lag_features(featured, target_col=cfg.target)
    validate_lag_features(featured, target_col="pasajeros_por_despacho_real")
    validate_lag_features(featured, target_col="despachos_count_real")

    if int(cfg.horizon) != 1:
        raise NotImplementedError("Esta fase solo implementa horizon=1")
    featured["target_interval_start"] = pd.to_datetime(featured["timestamp"])
    featured["target_interval_end"] = featured["target_interval_start"] + pd.Timedelta(
        minutes=int(cfg.granularity_min)
    )
    featured["feature_cutoff_timestamp"] = featured["target_interval_start"]

    if cfg.operational_only:
        if "dentro_horario_operativo" not in featured.columns:
            raise ValueError("La serie no tiene dentro_horario_operativo para filtrar")
        featured = featured[featured["dentro_horario_operativo"].eq(True)].copy()

    if sample_days is not None:
        min_ts = featured["timestamp"].min()
        cutoff = min_ts + pd.Timedelta(days=int(sample_days))
        featured = featured[featured["timestamp"] < cutoff].copy()

    if cfg.target == "pasajeros_por_despacho_real":
        featured["target_observed"] = featured["target_pasajeros_por_despacho_observed"]
    else:
        featured["target_observed"] = featured["target_pasajeros_total_observed"]
    feature_columns()

    missing_output_cols = [col for col in MODELING_COLUMNS if col not in featured.columns]
    if missing_output_cols:
        raise ValueError(f"Faltan columnas de salida: {missing_output_cols}")

    dataset = (
        featured[MODELING_COLUMNS].sort_values(["FK_RUTA", "timestamp"]).reset_index(drop=True)
    )
    metadata = dataset_metadata(dataset, source_path, cfg, source_hash)
    return dataset, metadata, route_series


def prepare_scenario_dataset(
    base_dataset: pd.DataFrame,
    cfg: TargetConfig,
    scenario: ScenarioDefinition,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a scenario-specific dataset with the correct target flag."""
    target_def = target_definition(cfg, scenario.target)
    required = {
        target_def.column,
        target_def.observed_flag,
        "dataset_version",
        "source_hash",
        "timestamp",
        "FK_RUTA",
    }
    missing = required.difference(base_dataset.columns)
    if missing:
        raise ValueError(f"Faltan columnas para escenario {scenario.name}: {sorted(missing)}")

    features = feature_columns(scenario.feature_set)
    missing_features = [col for col in features if col not in base_dataset.columns]
    if missing_features:
        raise ValueError(f"Faltan features para escenario {scenario.name}: {missing_features}")

    dataset = base_dataset.copy()
    dataset["target"] = scenario.target
    dataset["scenario"] = scenario.name
    dataset["feature_set"] = scenario.feature_set
    dataset["target_col"] = target_def.column
    dataset["observed_flag"] = target_def.observed_flag
    dataset["target_observed"] = dataset[target_def.observed_flag].astype(bool)

    metadata = {
        "target": scenario.target,
        "target_col": target_def.column,
        "observed_flag": target_def.observed_flag,
        "scenario": scenario.name,
        "feature_set": scenario.feature_set,
        "feature_columns": features,
        "rows": len(dataset),
        "observed_rows": int(dataset["target_observed"].sum()),
        "gap_rows": int(dataset["is_gap"].astype(bool).sum()),
        "start_timestamp": str(dataset["timestamp"].min()),
        "end_timestamp": str(dataset["timestamp"].max()),
    }
    return dataset, metadata


def build_multitarget_datasets(
    source_path: str | Path,
    cfg: TargetConfig,
    scenarios: dict[str, ScenarioDefinition],
    sample_days: int | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any], dict[int, pd.DataFrame]]:
    """Build all configured target/scenario datasets from one source read."""
    base_dataset, base_metadata, route_series = build_modeling_dataset(
        source_path=source_path,
        cfg=cfg,
        sample_days=sample_days,
    )
    datasets: dict[str, pd.DataFrame] = {}
    scenario_metadata: dict[str, Any] = {}
    for scenario in scenarios.values():
        dataset, metadata = prepare_scenario_dataset(base_dataset, cfg, scenario)
        datasets[scenario.name] = dataset
        scenario_metadata[scenario.name] = metadata

    metadata = {
        **base_metadata,
        "mode": "multitarget",
        "scenarios": scenario_metadata,
    }
    return datasets, metadata, route_series


def dataset_metadata(
    dataset: pd.DataFrame,
    source_path: Path,
    cfg: TargetConfig,
    source_hash: str,
) -> dict[str, Any]:
    """Build a JSON-serializable metadata record for a modeling dataset."""
    observed = dataset[dataset["target_observed"]]
    gaps = dataset[dataset["is_gap"]]
    return {
        "dataset_version": cfg.dataset_version,
        "source_path": str(source_path),
        "source_hash_sha256": source_hash,
        "target": cfg.target,
        "granularity_min": cfg.granularity_min,
        "horizon": cfg.horizon,
        "routes": list(cfg.routes),
        "operational_only": cfg.operational_only,
        "gap_imputation": cfg.gap_imputation,
        "rows": len(dataset),
        "observed_rows": len(observed),
        "gap_rows": len(gaps),
        "start_timestamp": str(dataset["timestamp"].min()),
        "end_timestamp": str(dataset["timestamp"].max()),
        "rows_by_route": {
            str(route): int(count)
            for route, count in dataset["FK_RUTA"].value_counts().sort_index().items()
        },
        "observed_rows_by_route": {
            str(route): int(count)
            for route, count in observed["FK_RUTA"].value_counts().sort_index().items()
        },
        "gap_rows_by_type": {
            str(kind): int(count) for kind, count in dataset["gap_tipo"].value_counts().items()
        },
        "feature_columns": feature_columns(),
        "lag_steps": list(LAG_STEPS),
        "dispatch_lag_steps": list(DISPATCH_LAG_STEPS),
        "rolling_windows_mean": list(ROLLING_WINDOWS_MEAN),
        "rolling_windows_std": list(ROLLING_WINDOWS_STD),
    }


def save_modeling_dataset(
    dataset: pd.DataFrame,
    metadata: dict[str, Any],
    route_series: dict[int, pd.DataFrame],
    output_path: str | Path,
    run_id: str,
    paths: ModelingPaths | None = None,
    save_series: bool = True,
) -> dict[str, Path | None]:
    """Persist the modeling dataset, metadata and optional regenerated series."""
    paths = paths or ModelingPaths()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    backups: dict[str, Path | None] = {}
    backups["dataset"] = backup_if_exists(output_path, run_id)
    dataset.to_parquet(output_path, index=False)
    metadata["dataset_path"] = str(output_path)
    metadata["dataset_hash_sha256"] = file_sha256(output_path)

    metadata_path = paths.metadata_dir / "modeling_dataset_metadata.json"
    backups["metadata"] = backup_if_exists(metadata_path, run_id)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    if save_series:
        paths.time_series_dir.mkdir(parents=True, exist_ok=True)
        for route, series in route_series.items():
            series_path = (
                paths.time_series_dir / f"ts_ruta{route}_g{metadata['granularity_min']}min.parquet"
            )
            backups[f"time_series_ruta{route}"] = backup_if_exists(series_path, run_id)
            series.to_parquet(series_path, index=False)

    return backups


def save_multitarget_datasets(
    datasets: dict[str, pd.DataFrame],
    metadata: dict[str, Any],
    route_series: dict[int, pd.DataFrame],
    scenarios: dict[str, ScenarioDefinition],
    output_dir: str | Path,
    run_id: str,
    paths: ModelingPaths | None = None,
    save_series: bool = False,
) -> dict[str, Path | None]:
    """Persist scenario datasets and one multitarget metadata artifact."""
    paths = paths or ModelingPaths()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    backups: dict[str, Path | None] = {}
    dataset_paths: dict[str, str] = {}
    for scenario_name, dataset in datasets.items():
        scenario = scenarios[scenario_name]
        output_path = scenario_dataset_path(
            scenario,
            granularity_min=int(metadata["granularity_min"]),
            output_dir=output_dir,
        )
        backups[f"dataset_{scenario_name}"] = backup_if_exists(output_path, run_id)
        dataset.to_parquet(output_path, index=False)
        dataset_paths[scenario_name] = str(output_path)
        metadata["scenarios"][scenario_name]["dataset_path"] = str(output_path)
        metadata["scenarios"][scenario_name]["dataset_hash_sha256"] = file_sha256(output_path)

    metadata["scenario_dataset_paths"] = dataset_paths
    metadata_path = paths.metadata_dir / f"modeling_multitarget_dataset_{run_id}.json"
    backups["metadata"] = backup_if_exists(metadata_path, run_id)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    if save_series:
        paths.time_series_dir.mkdir(parents=True, exist_ok=True)
        for route, series in route_series.items():
            series_path = (
                paths.time_series_dir / f"ts_ruta{route}_g{metadata['granularity_min']}min.parquet"
            )
            backups[f"time_series_ruta{route}"] = backup_if_exists(series_path, run_id)
            series.to_parquet(series_path, index=False)

    return backups
