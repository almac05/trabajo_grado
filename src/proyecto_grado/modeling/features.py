"""Feature engineering for leakage-safe time-series modeling."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

FORBIDDEN_PREDICTORS = {
    "pasajeros_promedio",
    "ocupacion_p95",
    "HORA_FIN_FINAL",
    "DURACION_MIN_FINAL",
    "FIN_TIPO",
    "HORA_FIN_FUENTE",
    "RECORRIDO_COMPLETO",
}

CALENDAR_FEATURES = [
    "hora_del_dia",
    "dia_semana",
    "mes",
    "semana_anio",
    "es_fin_semana",
    "es_festivo",
    "tipo_dia",
    "franja_horaria",
    "FK_RUTA",
]
LAG_STEPS = [1, 2, 3, 48, 96, 336]
DISPATCH_LAG_STEPS = [1, 2, 3, 48, 336]
ROLLING_WINDOWS_MEAN = [3, 6, 12]
ROLLING_WINDOWS_STD = [6, 12]
CYCLIC_FEATURES = ["hora_sin", "hora_cos", "dia_semana_sin", "dia_semana_cos"]
TARGET_PREFIX_BY_COLUMN = {
    "pasajeros_total": "pasajeros_total",
    "pasajeros_por_despacho_real": "pasajeros_por_despacho",
    "despachos_count_real": "despachos_count_real",
}


def _target_prefix(target_col: str) -> str:
    """Return the feature prefix used for a source column."""
    return TARGET_PREFIX_BY_COLUMN.get(target_col, target_col)


def ensure_modeling_target_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dispatch and target-observed columns used by modeling."""
    data = df.copy()
    if "despachos_count_real" not in data.columns:
        if "despachos_count" not in data.columns:
            raise ValueError("Falta despachos_count o despachos_count_real")
        data["despachos_count_real"] = data["despachos_count"]

    data["despachos_count_real"] = pd.to_numeric(
        data["despachos_count_real"],
        errors="coerce",
    )
    data["pasajeros_total"] = pd.to_numeric(data["pasajeros_total"], errors="coerce")
    data["pasajeros_por_despacho_real"] = np.where(
        data["despachos_count_real"] > 0,
        data["pasajeros_total"] / data["despachos_count_real"],
        np.nan,
    )

    gap_mask = (
        data["is_gap"].astype(bool)
        if "is_gap" in data.columns
        else pd.Series(False, index=data.index)
    )
    data["target_pasajeros_total_observed"] = data["pasajeros_total"].notna() & ~gap_mask
    data["target_pasajeros_por_despacho_observed"] = (
        data["pasajeros_por_despacho_real"].notna() & data["despachos_count_real"].gt(0) & ~gap_mask
    )
    if "target_observed" not in data.columns:
        data["target_observed"] = data["target_pasajeros_total_observed"]
    return data


def add_lagged_features(
    df: pd.DataFrame,
    source_col: str,
    route_col: str = "FK_RUTA",
    lag_steps: list[int] | None = None,
    rolling_mean_windows: list[int] | None = None,
    rolling_std_windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add leakage-safe lag and rolling features for one source column."""
    lag_steps = LAG_STEPS if lag_steps is None else lag_steps
    rolling_mean_windows = (
        ROLLING_WINDOWS_MEAN if rolling_mean_windows is None else rolling_mean_windows
    )
    rolling_std_windows = (
        ROLLING_WINDOWS_STD if rolling_std_windows is None else rolling_std_windows
    )
    prefix = _target_prefix(source_col)
    data = df.copy()
    grouped = data.groupby(route_col, sort=False)[source_col]

    for lag in lag_steps:
        data[f"{prefix}_lag_{lag}"] = grouped.shift(lag)

    for window in rolling_mean_windows:
        data[f"{prefix}_rolling_mean_{window}"] = grouped.transform(
            lambda s, w=window: s.shift(1).rolling(w, min_periods=1).mean()
        )

    for window in rolling_std_windows:
        data[f"{prefix}_rolling_std_{window}"] = grouped.transform(
            lambda s, w=window: s.shift(1).rolling(w, min_periods=2).std()
        )
    return data


def add_modeling_features(
    df: pd.DataFrame,
    target_col: str = "pasajeros_total",
    route_col: str = "FK_RUTA",
) -> pd.DataFrame:
    """Add lag, rolling and cyclic features without using the current target.

    Lags and rolling windows are computed on the complete 30-minute grid before
    any operational-hour filtering. Rolling features are based on ``shift(1)`` so
    the current observation is never included.
    """
    required = {"timestamp", route_col, "pasajeros_total"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas para features: {sorted(missing)}")

    data = ensure_modeling_target_columns(df)
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data = data.sort_values([route_col, "timestamp"]).reset_index(drop=True)

    data = add_lagged_features(data, "pasajeros_total", route_col=route_col)
    data = add_lagged_features(data, "pasajeros_por_despacho_real", route_col=route_col)
    data = add_lagged_features(
        data,
        "despachos_count_real",
        route_col=route_col,
        lag_steps=DISPATCH_LAG_STEPS,
        rolling_std_windows=[],
    )

    minute_of_day = data["timestamp"].dt.hour * 60 + data["timestamp"].dt.minute
    data["franja_30min"] = data["timestamp"].dt.strftime("%H:%M")
    data["hora_sin"] = np.sin(2 * math.pi * minute_of_day / 1440.0)
    data["hora_cos"] = np.cos(2 * math.pi * minute_of_day / 1440.0)
    data["dia_semana_sin"] = np.sin(2 * math.pi * data["dia_semana"] / 7.0)
    data["dia_semana_cos"] = np.cos(2 * math.pi * data["dia_semana"] / 7.0)

    for lag in LAG_STEPS:
        data[f"lag_{lag}"] = data[f"pasajeros_total_lag_{lag}"]
    for window in ROLLING_WINDOWS_MEAN:
        data[f"rolling_mean_{window}"] = data[f"pasajeros_total_rolling_mean_{window}"]
    for window in ROLLING_WINDOWS_STD:
        data[f"rolling_std_{window}"] = data[f"pasajeros_total_rolling_std_{window}"]

    if target_col == "pasajeros_por_despacho_real":
        data["target_observed"] = data["target_pasajeros_por_despacho_observed"]
    else:
        data["target_observed"] = data["target_pasajeros_total_observed"]
    return data


def _lag_columns(prefix: str, lags: list[int] | None = None) -> list[str]:
    """Return lag column names for one prefix."""
    return [f"{prefix}_lag_{lag}" for lag in (lags or LAG_STEPS)]


def _rolling_columns(prefix: str, include_std: bool = True) -> list[str]:
    """Return rolling column names for one prefix."""
    cols = [f"{prefix}_rolling_mean_{window}" for window in ROLLING_WINDOWS_MEAN]
    if include_std:
        cols.extend(f"{prefix}_rolling_std_{window}" for window in ROLLING_WINDOWS_STD)
    return cols


def feature_columns(feature_set: str | None = None) -> list[str]:
    """Return approved predictor columns for the requested scenario feature set."""
    common = CALENDAR_FEATURES + CYCLIC_FEATURES
    demand = _lag_columns("pasajeros_total") + _rolling_columns("pasajeros_total")
    productivity = _lag_columns("pasajeros_por_despacho") + _rolling_columns(
        "pasajeros_por_despacho"
    )
    dispatch = _lag_columns("despachos_count_real", DISPATCH_LAG_STEPS) + _rolling_columns(
        "despachos_count_real",
        include_std=False,
    )

    if feature_set in (None, "calendario_ruta_lags_demanda"):
        cols = common + demand
    elif feature_set == "calendario_ruta_lags_demanda_lags_despachos":
        cols = common + demand + dispatch
    elif feature_set == "calendario_ruta_lags_productividad_lags_demanda_lags_despachos":
        cols = common + productivity + demand + dispatch
    else:
        raise ValueError(f"Feature set no soportado: {feature_set}")
    validate_no_forbidden_predictors(cols)
    return cols


def validate_no_forbidden_predictors(columns: Iterable[str]) -> None:
    """Raise if a prohibited leakage-prone column is included as predictor."""
    normalized = {col.lower() for col in columns}
    forbidden = {col.lower() for col in FORBIDDEN_PREDICTORS}
    overlap = sorted(normalized.intersection(forbidden))
    if overlap:
        raise ValueError(f"Columnas con fuga temporal prohibidas como predictors: {overlap}")


def validate_lag_features(
    df: pd.DataFrame,
    target_col: str = "pasajeros_total",
    route_col: str = "FK_RUTA",
) -> None:
    """Validate that lag features equal shifted target values by route."""
    data = df.sort_values([route_col, "timestamp"]).reset_index(drop=True)
    grouped = data.groupby(route_col, sort=False)[target_col]
    prefix = _target_prefix(target_col)

    for lag in LAG_STEPS:
        expected = grouped.shift(lag)
        column = f"{prefix}_lag_{lag}"
        if column not in data.columns:
            if target_col == "pasajeros_total" and f"lag_{lag}" in data.columns:
                column = f"lag_{lag}"
            else:
                continue
        actual = data[column]
        both_na = expected.isna() & actual.isna()
        both_values = expected.notna() & actual.notna() & np.isclose(expected, actual)
        mismatch = ~(both_na | both_values)
        if bool(mismatch.any()):
            raise ValueError(f"Validacion anti-fuga fallo en {column}")

    for window in ROLLING_WINDOWS_MEAN:
        expected = grouped.transform(
            lambda s, w=window: s.shift(1).rolling(w, min_periods=1).mean()
        )
        column = f"{prefix}_rolling_mean_{window}"
        if column not in data.columns:
            if target_col == "pasajeros_total" and f"rolling_mean_{window}" in data.columns:
                column = f"rolling_mean_{window}"
            else:
                continue
        actual = data[column]
        both_na = expected.isna() & actual.isna()
        both_values = expected.notna() & actual.notna() & np.isclose(expected, actual)
        mismatch = ~(both_na | both_values)
        if bool(mismatch.any()):
            raise ValueError(f"Validacion anti-fuga fallo en {column}")

    for window in ROLLING_WINDOWS_STD:
        expected = grouped.transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=2).std())
        column = f"{prefix}_rolling_std_{window}"
        if column not in data.columns:
            if target_col == "pasajeros_total" and f"rolling_std_{window}" in data.columns:
                column = f"rolling_std_{window}"
            else:
                continue
        actual = data[column]
        both_na = expected.isna() & actual.isna()
        both_values = expected.notna() & actual.notna() & np.isclose(expected, actual)
        mismatch = ~(both_na | both_values)
        if bool(mismatch.any()):
            raise ValueError(f"Validacion anti-fuga fallo en {column}")
