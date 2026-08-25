"""Configuration helpers for the reproducible modeling pipeline."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
# freeze_20260823_203700 corrige el sesgo de conteo APC (PASAJEROS_REALES
# en vez de PASAJEROS crudo); ver configs/modeling/targets.yaml.
DEFAULT_DATASET_VERSION = "freeze_20260823_203700"
DEFAULT_SOURCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "model_ready"
    / "despachos_model_ready_freeze_20260823_203700.parquet"
)


@dataclass(frozen=True)
class ModelingPaths:
    """Canonical paths used by the modeling scripts."""

    source_path: Path = DEFAULT_SOURCE_PATH
    dataset_path: Path = (
        PROJECT_ROOT / "data" / "processed" / "modeling" / "modeling_dataset_g30min.parquet"
    )
    time_series_dir: Path = PROJECT_ROOT / "data" / "processed" / "modeling" / "time_series"
    tables_dir: Path = PROJECT_ROOT / "reports" / "tables" / "modeling"
    figures_dir: Path = PROJECT_ROOT / "reports" / "figures" / "modeling"
    metadata_dir: Path = PROJECT_ROOT / "models" / "metadata"


@dataclass(frozen=True)
class TargetDefinition:
    """Definition for one supervised target."""

    name: str
    column: str
    observed_flag: str
    unit: str = ""
    description: str = ""


@dataclass(frozen=True)
class ScenarioDefinition:
    """Definition for one modeling scenario."""

    name: str
    target: str
    feature_set: str
    description: str = ""


@dataclass(frozen=True)
class TargetConfig:
    """Target and dataset construction settings."""

    dataset_version: str = DEFAULT_DATASET_VERSION
    target: str = "pasajeros_total"
    granularity_min: int = 30
    horizon: int = 1
    routes: tuple[int, ...] = (1, 3)
    operational_only: bool = True
    gap_imputation: str = "mark"
    targets: dict[str, TargetDefinition] | None = None
    timing: dict[str, str] | None = None


@dataclass(frozen=True)
class BacktestingConfig:
    """Temporal validation settings."""

    test_weeks: int = 10
    validation_weeks: int = 2
    step_weeks: int = 2
    min_train_weeks: int = 26
    seed: int = 42
    operational_day_start: str = "04:00:00"
    require_full_operational_days: bool = True
    drop_partial_boundary_days: bool = True


DEFAULT_TARGET_DEFINITIONS = {
    "pasajeros_total": TargetDefinition(
        name="pasajeros_total",
        column="pasajeros_total",
        observed_flag="target_pasajeros_total_observed",
        unit="pasajeros por franja",
        description="Pasajeros acumulados en la ruta y franja temporal.",
    ),
    "pasajeros_por_despacho": TargetDefinition(
        name="pasajeros_por_despacho",
        column="pasajeros_por_despacho_real",
        observed_flag="target_pasajeros_por_despacho_observed",
        unit="pasajeros por despacho",
        description="Productividad observada por despacho real dentro de la franja.",
    ),
}

DEFAULT_SCENARIOS = {
    "sin_oferta": ScenarioDefinition(
        name="sin_oferta",
        target="pasajeros_total",
        feature_set="calendario_ruta_lags_demanda",
        description="Predice pasajeros por franja sin usar variables de oferta.",
    ),
    "oferta_historica_rezagada": ScenarioDefinition(
        name="oferta_historica_rezagada",
        target="pasajeros_total",
        feature_set="calendario_ruta_lags_demanda_lags_despachos",
        description="Predice pasajeros por franja usando solo oferta historica rezagada.",
    ),
    "productividad_por_despacho": ScenarioDefinition(
        name="productividad_por_despacho",
        target="pasajeros_por_despacho",
        feature_set="calendario_ruta_lags_productividad_lags_demanda_lags_despachos",
        description="Predice productividad por despacho sin multiplicar por oferta futura.",
    ),
}


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return an empty dict when it does not exist."""
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_target_definitions(raw: dict[str, Any]) -> dict[str, TargetDefinition]:
    """Parse target definitions with safe defaults for legacy configs."""
    definitions: dict[str, TargetDefinition] = {}
    targets_raw = raw.get("targets") or {}
    for name, payload in targets_raw.items():
        payload = payload or {}
        definitions[str(name)] = TargetDefinition(
            name=str(name),
            column=str(payload.get("column", name)),
            observed_flag=str(payload.get("observed_flag", f"target_{name}_observed")),
            unit=str(payload.get("unit", "")),
            description=str(payload.get("description", "")),
        )
    if not definitions:
        definitions = dict(DEFAULT_TARGET_DEFINITIONS)
    else:
        for name, default in DEFAULT_TARGET_DEFINITIONS.items():
            definitions.setdefault(name, default)
    return definitions


def load_target_config(path: str | Path | None = None) -> TargetConfig:
    """Load target configuration from YAML, falling back to defaults."""
    cfg_path = Path(path) if path else PROJECT_ROOT / "configs" / "modeling" / "targets.yaml"
    raw = load_yaml(cfg_path)
    routes = tuple(int(r) for r in raw.get("routes", TargetConfig.routes))
    source_snapshot = str(raw.get("dataset_version", DEFAULT_DATASET_VERSION))
    target_definitions = _load_target_definitions(raw)
    return TargetConfig(
        dataset_version=source_snapshot,
        target=str(raw.get("target", "pasajeros_total")),
        granularity_min=int(raw.get("granularity_min", 30)),
        horizon=int(raw.get("horizon", 1)),
        routes=routes,
        operational_only=bool(raw.get("operational_only", True)),
        gap_imputation=str(raw.get("gap_imputation", "mark")),
        targets=target_definitions,
        timing=dict(raw.get("timing", {})),
    )


def load_backtesting_config(path: str | Path | None = None) -> BacktestingConfig:
    """Load backtesting configuration from YAML, falling back to defaults."""
    cfg_path = Path(path) if path else PROJECT_ROOT / "configs" / "modeling" / "backtesting.yaml"
    raw = load_yaml(cfg_path)
    return BacktestingConfig(
        test_weeks=int(raw.get("test_weeks", 10)),
        validation_weeks=int(raw.get("validation_weeks", 2)),
        step_weeks=int(raw.get("step_weeks", 2)),
        min_train_weeks=int(raw.get("min_train_weeks", 26)),
        seed=int(raw.get("seed", 42)),
        operational_day_start=str(raw.get("operational_day_start", "04:00:00")),
        require_full_operational_days=bool(raw.get("require_full_operational_days", True)),
        drop_partial_boundary_days=bool(raw.get("drop_partial_boundary_days", True)),
    )


def load_model_names(path: str | Path | None = None) -> list[str]:
    """Load enabled baseline model names from YAML."""
    cfg_path = Path(path) if path else PROJECT_ROOT / "configs" / "modeling" / "models.yaml"
    raw = load_yaml(cfg_path)
    models = raw.get("baselines", [])
    if not models:
        return [
            "naive",
            "seasonal_naive_daily",
            "seasonal_naive_weekly",
            "historical_average_route_day_type_slot",
        ]
    return [str(item["name"] if isinstance(item, dict) else item) for item in models]


def load_xgboost_model_names(path: str | Path | None = None) -> list[str]:
    """Load enabled XGBoost configuration names from YAML."""
    cfg_path = Path(path) if path else PROJECT_ROOT / "configs" / "modeling" / "models.yaml"
    raw = load_yaml(cfg_path)
    models = raw.get("xgboost_models", [])
    return [str(item["name"] if isinstance(item, dict) else item) for item in models]


def load_scenario_definitions(path: str | Path | None = None) -> dict[str, ScenarioDefinition]:
    """Load enabled scenario definitions from YAML."""
    cfg_path = Path(path) if path else PROJECT_ROOT / "configs" / "modeling" / "models.yaml"
    raw = load_yaml(cfg_path)
    scenarios = raw.get("scenarios", [])
    if not scenarios:
        return dict(DEFAULT_SCENARIOS)

    parsed: dict[str, ScenarioDefinition] = {}
    for item in scenarios:
        if isinstance(item, str):
            if item not in DEFAULT_SCENARIOS:
                raise ValueError(f"Escenario no soportado: {item}")
            parsed[item] = DEFAULT_SCENARIOS[item]
            continue
        name = str(item["name"])
        parsed[name] = ScenarioDefinition(
            name=name,
            target=str(
                item.get(
                    "target", DEFAULT_SCENARIOS.get(name, ScenarioDefinition(name, "", "")).target
                )
            ),
            feature_set=str(
                item.get(
                    "feature_set",
                    DEFAULT_SCENARIOS.get(name, ScenarioDefinition(name, "", "")).feature_set,
                )
            ),
            description=str(item.get("description", "")),
        )
    return parsed


def target_definition(cfg: TargetConfig, target_name: str) -> TargetDefinition:
    """Return a target definition from a loaded config."""
    definitions = cfg.targets or DEFAULT_TARGET_DEFINITIONS
    if target_name not in definitions:
        raise ValueError(f"Target no configurado: {target_name}")
    return definitions[target_name]


def scenario_dataset_path(
    scenario: ScenarioDefinition,
    granularity_min: int,
    output_dir: str | Path | None = None,
) -> Path:
    """Build the canonical dataset path for a target/scenario pair."""
    root = Path(output_dir) if output_dir else PROJECT_ROOT / "data" / "processed" / "modeling"
    return (
        root / f"modeling_dataset_{scenario.target}_{scenario.name}_g{granularity_min}min.parquet"
    )


def ensure_modeling_dirs(paths: ModelingPaths | None = None) -> ModelingPaths:
    """Create output directories used by the modeling pipeline."""
    paths = paths or ModelingPaths()
    for path in [
        paths.dataset_path.parent,
        paths.time_series_dir,
        paths.tables_dir,
        paths.figures_dir,
        paths.metadata_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    return paths


def make_run_id(prefix: str = "baselines") -> str:
    """Build a stable-enough run identifier for persisted outputs."""
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}"


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def backup_if_exists(
    path: str | Path,
    run_id: str,
    backup_root: str | Path | None = None,
) -> Path | None:
    """Copy an existing artifact before it is overwritten.

    The backup path mirrors the project-relative output path under
    ``models/metadata/backups/<run_id>/``.
    """
    path = Path(path)
    if not path.exists():
        return None

    backup_root = Path(backup_root) if backup_root else ModelingPaths().metadata_dir / "backups"
    try:
        rel = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        rel = Path(path.name)
    backup_path = backup_root / run_id / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_path)
    return backup_path


def write_json_with_backup(payload: dict[str, Any], path: str | Path, run_id: str) -> Path | None:
    """Write JSON and back up any previous artifact."""
    path = Path(path)
    backup_path = backup_if_exists(path, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    return backup_path


def dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert dataclasses with Path values into JSON-friendly dictionaries."""
    raw = asdict(obj)
    return {key: str(value) if isinstance(value, Path) else value for key, value in raw.items()}
