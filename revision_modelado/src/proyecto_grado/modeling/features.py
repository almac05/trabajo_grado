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
ROLLING_WINDOWS_MEAN = [3, 6, 12]
ROLLING_WINDOWS_STD = [6, 12]
CYCLIC_FEATURES = ["hora_sin", "hora_cos", "dia_semana_sin", "dia_semana_cos"]


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
    required = {"timestamp", route_col, target_col}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas para features: {sorted(missing)}")

    data = df.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data = data.sort_values([route_col, "timestamp"]).reset_index(drop=True)

    grouped = data.groupby(route_col, sort=False)[target_col]
    for lag in LAG_STEPS:
        data[f"lag_{lag}"] = grouped.shift(lag)

    for window in ROLLING_WINDOWS_MEAN:
        data[f"rolling_mean_{window}"] = grouped.transform(
            lambda s, w=window: s.shift(1).rolling(w, min_periods=1).mean()
        )

    for window in ROLLING_WINDOWS_STD:
        data[f"rolling_std_{window}"] = grouped.transform(
            lambda s, w=window: s.shift(1).rolling(w, min_periods=2).std()
        )

    minute_of_day = data["timestamp"].dt.hour * 60 + data["timestamp"].dt.minute
    data["franja_30min"] = data["timestamp"].dt.strftime("%H:%M")
    data["hora_sin"] = np.sin(2 * math.pi * minute_of_day / 1440.0)
    data["hora_cos"] = np.cos(2 * math.pi * minute_of_day / 1440.0)
    data["dia_semana_sin"] = np.sin(2 * math.pi * data["dia_semana"] / 7.0)
    data["dia_semana_cos"] = np.cos(2 * math.pi * data["dia_semana"] / 7.0)
    return data


def feature_columns() -> list[str]:
    """Return the approved predictor columns for this modeling phase."""
    lag_cols = [f"lag_{lag}" for lag in LAG_STEPS]
    rolling_cols = [
        "rolling_mean_3",
        "rolling_mean_6",
        "rolling_mean_12",
        "rolling_std_6",
        "rolling_std_12",
    ]
    cols = CALENDAR_FEATURES + lag_cols + rolling_cols + CYCLIC_FEATURES
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

    for lag in LAG_STEPS:
        expected = grouped.shift(lag)
        actual = data[f"lag_{lag}"]
        both_na = expected.isna() & actual.isna()
        both_values = expected.notna() & actual.notna() & np.isclose(expected, actual)
        mismatch = ~(both_na | both_values)
        if bool(mismatch.any()):
            raise ValueError(f"Validacion anti-fuga fallo en lag_{lag}")

    for window in ROLLING_WINDOWS_MEAN:
        expected = grouped.transform(
            lambda s, w=window: s.shift(1).rolling(w, min_periods=1).mean()
        )
        actual = data[f"rolling_mean_{window}"]
        both_na = expected.isna() & actual.isna()
        both_values = expected.notna() & actual.notna() & np.isclose(expected, actual)
        mismatch = ~(both_na | both_values)
        if bool(mismatch.any()):
            raise ValueError(f"Validacion anti-fuga fallo en rolling_mean_{window}")

    for window in ROLLING_WINDOWS_STD:
        expected = grouped.transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=2).std())
        actual = data[f"rolling_std_{window}"]
        both_na = expected.isna() & actual.isna()
        both_values = expected.notna() & actual.notna() & np.isclose(expected, actual)
        mismatch = ~(both_na | both_values)
        if bool(mismatch.any()):
            raise ValueError(f"Validacion anti-fuga fallo en rolling_std_{window}")
