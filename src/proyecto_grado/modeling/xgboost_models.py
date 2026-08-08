"""XGBoost forecasters trained per route within each backtesting fold.

Each fold trains one model per route (Ruta 1, Ruta 3) so results stay
comparable with the per-route baselines. Early stopping uses the last
``EARLY_STOPPING_WEEKS`` of the fold's *training* window only; the
validation fold used for metrics is never touched during fitting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import xgboost as xgb

from proyecto_grado.modeling.features import feature_columns

XGBOOST_OBJECTIVES: dict[str, str] = {
    "xgboost_l2": "reg:squarederror",
    "xgboost_l1": "reg:absoluteerror",
}
XGBOOST_MODELS: list[str] = list(XGBOOST_OBJECTIVES)

DEFAULT_XGBOOST_PARAMS: dict[str, object] = {
    "max_depth": 5,
    "min_child_weight": 5,
    "learning_rate": 0.05,
    "n_estimators": 2000,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": 42,
}
DEFAULT_EARLY_STOPPING_ROUNDS = 50
DEFAULT_EARLY_STOPPING_WEEKS = 2

# Columns from feature_columns() that arrive as strings and must be handed to
# XGBoost as pandas categoricals (native categorical splits, nulls preserved).
CATEGORICAL_FEATURE_CANDIDATES = ["tipo_dia", "franja_horaria"]


@dataclass
class RouteFitDiagnostics:
    """Per-route, per-fold fit outcome used for reporting."""

    route: int
    n_estimators_used: int
    best_iteration: int
    n_train_rows: int
    n_early_stop_rows: int
    importance_gain: dict[str, float] = field(default_factory=dict)


def validate_xgboost_model_names(model_names: list[str]) -> None:
    """Validate requested XGBoost configuration names."""
    invalid = sorted(set(model_names).difference(XGBOOST_MODELS))
    if invalid:
        raise ValueError(f"Modelos XGBoost no soportados: {invalid}")


def _route_feature_columns(feature_set: str, route_col: str = "FK_RUTA") -> list[str]:
    """Return predictor columns for a single-route model.

    ``route_col`` is dropped because it is constant within a per-route model
    and would only waste split evaluations.
    """
    return [col for col in feature_columns(feature_set) if col != route_col]


def _early_stopping_split(
    train_df: pd.DataFrame,
    train_end: pd.Timestamp,
    weeks: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carve the last ``weeks`` of the training window out for early stopping.

    Both halves come strictly from ``[train_start, train_end)``, so this
    split can never intersect the fold's validation window.
    """
    cutoff = pd.Timestamp(train_end) - pd.Timedelta(weeks=weeks)
    ts = pd.to_datetime(train_df["timestamp"])
    fit_df = train_df.loc[ts < cutoff]
    stop_df = train_df.loc[ts >= cutoff]
    return fit_df, stop_df


def _prepare_matrix(
    df: pd.DataFrame,
    features: list[str],
    categories: dict[str, list[str]],
) -> pd.DataFrame:
    """Select predictor columns and cast categoricals with fixed train categories."""
    matrix = df[features].copy()
    for col, cats in categories.items():
        matrix[col] = pd.Categorical(matrix[col], categories=cats)
    return matrix


def fit_predict_xgboost_route(
    train_df: pd.DataFrame,
    predict_df: pd.DataFrame,
    target_col: str,
    feature_set: str,
    objective: str,
    train_end: pd.Timestamp,
    route_col: str = "FK_RUTA",
    params: dict[str, object] | None = None,
    early_stopping_rounds: int = DEFAULT_EARLY_STOPPING_ROUNDS,
    early_stopping_weeks: int = DEFAULT_EARLY_STOPPING_WEEKS,
) -> tuple[pd.Series, RouteFitDiagnostics]:
    """Fit one XGBoost model for a single route and predict its fold rows."""
    if train_df.empty:
        raise ValueError("No hay datos de entrenamiento para el modelo XGBoost")
    route = int(train_df[route_col].iloc[0])
    features = _route_feature_columns(feature_set, route_col)
    fit_df, stop_df = _early_stopping_split(train_df, train_end, early_stopping_weeks)
    if fit_df.empty or stop_df.empty:
        raise ValueError(
            f"Ruta {route}: datos insuficientes para separar ajuste y parada temprana "
            f"({len(fit_df)} filas de ajuste, {len(stop_df)} de parada temprana)"
        )

    categorical_cols = [c for c in CATEGORICAL_FEATURE_CANDIDATES if c in features]
    categories = {col: sorted(train_df[col].dropna().unique().tolist()) for col in categorical_cols}

    x_fit = _prepare_matrix(fit_df, features, categories)
    x_stop = _prepare_matrix(stop_df, features, categories)
    x_predict = _prepare_matrix(predict_df, features, categories)
    y_fit = fit_df[target_col].astype(float)
    y_stop = stop_df[target_col].astype(float)

    model_params = {**DEFAULT_XGBOOST_PARAMS, **(params or {})}
    model = xgb.XGBRegressor(
        objective=objective,
        eval_metric="mae",
        enable_categorical=True,
        tree_method="hist",
        early_stopping_rounds=early_stopping_rounds,
        **model_params,
    )
    model.fit(x_fit, y_fit, eval_set=[(x_stop, y_stop)], verbose=False)

    y_pred = pd.Series(model.predict(x_predict), index=predict_df.index, dtype=float)
    best_iteration = int(getattr(model, "best_iteration", model.n_estimators - 1))
    importance = model.get_booster().get_score(importance_type="gain")
    diagnostics = RouteFitDiagnostics(
        route=route,
        n_estimators_used=best_iteration + 1,
        best_iteration=best_iteration,
        n_train_rows=len(fit_df),
        n_early_stop_rows=len(stop_df),
        importance_gain=dict(importance),
    )
    return y_pred, diagnostics


def predict_xgboost(
    model_name: str,
    train_df: pd.DataFrame,
    predict_df: pd.DataFrame,
    target_col: str,
    feature_set: str,
    train_end: pd.Timestamp,
    route_col: str = "FK_RUTA",
    params: dict[str, object] | None = None,
    early_stopping_rounds: int = DEFAULT_EARLY_STOPPING_ROUNDS,
    early_stopping_weeks: int = DEFAULT_EARLY_STOPPING_WEEKS,
    return_meta: bool = False,
) -> pd.Series | tuple[pd.Series, dict[str, dict[int, RouteFitDiagnostics]]]:
    """Generate XGBoost predictions for one fold, fitting one model per route."""
    validate_xgboost_model_names([model_name])
    objective = XGBOOST_OBJECTIVES[model_name]

    y_pred = pd.Series(index=predict_df.index, dtype=float)
    route_diagnostics: dict[int, RouteFitDiagnostics] = {}
    for route in sorted(predict_df[route_col].dropna().unique().tolist()):
        route_train = train_df.loc[train_df[route_col] == route]
        route_predict_idx = predict_df.index[predict_df[route_col] == route]
        route_predict = predict_df.loc[route_predict_idx]
        if route_train.empty or route_predict.empty:
            continue
        route_pred, diag = fit_predict_xgboost_route(
            route_train,
            route_predict,
            target_col=target_col,
            feature_set=feature_set,
            objective=objective,
            train_end=train_end,
            route_col=route_col,
            params=params,
            early_stopping_rounds=early_stopping_rounds,
            early_stopping_weeks=early_stopping_weeks,
        )
        y_pred.loc[route_predict_idx] = route_pred.to_numpy()
        route_diagnostics[int(route)] = diag

    if return_meta:
        return y_pred, {"route_diagnostics": route_diagnostics}
    return y_pred
