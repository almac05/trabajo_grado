"""Baseline forecasters for the first reproducible modeling phase."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

BASELINE_MODELS = [
    "naive",
    "seasonal_naive_daily",
    "seasonal_naive_weekly",
    "historical_average_route_day_type_slot",
]


@dataclass(frozen=True)
class BaselineDescription:
    """Human-readable model metadata."""

    name: str
    description: str


BASELINE_DESCRIPTIONS = {
    "naive": BaselineDescription("naive", "Predice la franja anterior de la misma ruta."),
    "seasonal_naive_daily": BaselineDescription(
        "seasonal_naive_daily",
        "Predice la misma franja del dia anterior (lag_48 para 30 min).",
    ),
    "seasonal_naive_weekly": BaselineDescription(
        "seasonal_naive_weekly",
        "Predice la misma franja de la semana anterior (lag_336 para 30 min).",
    ),
    "historical_average_route_day_type_slot": BaselineDescription(
        "historical_average_route_day_type_slot",
        "Promedio historico por ruta, tipo de dia y franja de 30 minutos.",
    ),
}


class HistoricalAverageBaseline:
    """Historical mean baseline fitted only on past training data."""

    def __init__(self, target_col: str = "pasajeros_total", verbose: bool = False) -> None:
        self.target_col = target_col
        self.verbose = verbose
        self.primary_: pd.DataFrame | None = None
        self.route_slot_: pd.DataFrame | None = None
        self.route_: pd.DataFrame | None = None
        self.global_mean_: float | None = None

    def fit(self, train_df: pd.DataFrame) -> HistoricalAverageBaseline:
        """Fit averages using observed target rows from the training window."""
        observed = train_df[train_df[self.target_col].notna()].copy()
        if "target_observed" in observed.columns:
            observed = observed[observed["target_observed"].astype(bool)]
        if observed.empty:
            raise ValueError("No hay observaciones de entrenamiento para promedio historico")

        if self.verbose:
            print("      [fit] historical_average_route_day_type_slot")
            print(f"            filas train observadas: {len(observed):,}")
            print(
                "            rango train: "
                f"{observed['timestamp'].min()} -> {observed['timestamp'].max()}"
                if "timestamp" in observed.columns
                else "            rango train: No disponible"
            )

        self.primary_ = (
            observed.groupby(["FK_RUTA", "tipo_dia", "franja_30min"], as_index=False)[
                self.target_col
            ]
            .mean()
            .rename(columns={self.target_col: "pred_primary"})
        )
        self.route_slot_ = (
            observed.groupby(["FK_RUTA", "franja_30min"], as_index=False)[self.target_col]
            .mean()
            .rename(columns={self.target_col: "pred_route_slot"})
        )
        self.route_ = (
            observed.groupby(["FK_RUTA"], as_index=False)[self.target_col]
            .mean()
            .rename(columns={self.target_col: "pred_route"})
        )
        self.global_mean_ = float(observed[self.target_col].mean())

        if self.verbose:
            print(
                f"            promedios exactos (ruta + tipo_dia + franja): {len(self.primary_):,}"
            )
            print(
                "            fallback ruta + franja: "
                f"{len(self.route_slot_):,}; fallback ruta: {len(self.route_):,}"
            )
            print(f"            promedio global train: {self.global_mean_:.3f}")
        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """Predict using primary keys and conservative fallbacks."""
        if self.primary_ is None or self.route_slot_ is None or self.route_ is None:
            raise RuntimeError("HistoricalAverageBaseline debe ajustarse antes de predecir")

        pred = df[["FK_RUTA", "tipo_dia", "franja_30min"]].copy()
        pred["_row_order"] = range(len(pred))
        pred = pred.merge(self.primary_, on=["FK_RUTA", "tipo_dia", "franja_30min"], how="left")
        pred = pred.merge(self.route_slot_, on=["FK_RUTA", "franja_30min"], how="left")
        pred = pred.merge(self.route_, on=["FK_RUTA"], how="left")
        values = pred["pred_primary"].fillna(pred["pred_route_slot"])
        values = values.fillna(pred["pred_route"])
        values = values.fillna(self.global_mean_)
        if self.verbose:
            exact_mask = pred["pred_primary"].notna()
            route_slot_mask = pred["pred_primary"].isna() & pred["pred_route_slot"].notna()
            route_fallback_mask = (
                pred["pred_primary"].isna()
                & pred["pred_route_slot"].isna()
                & pred["pred_route"].notna()
            )
            global_fallback_mask = (
                pred["pred_primary"].isna()
                & pred["pred_route_slot"].isna()
                & pred["pred_route"].isna()
            )
            print("      [predict] historical_average_route_day_type_slot")
            print(f"                filas a predecir: {len(pred):,}")
            print(f"                match exacto: {int(exact_mask.sum()):,}")
            print(f"                fallback ruta+franja: {int(route_slot_mask.sum()):,}")
            print(f"                fallback ruta: {int(route_fallback_mask.sum()):,}")
            print(f"                fallback global: {int(global_fallback_mask.sum()):,}")
        return values.sort_index().astype(float)


def validate_model_names(model_names: list[str]) -> None:
    """Validate requested baseline names."""
    invalid = sorted(set(model_names).difference(BASELINE_MODELS))
    if invalid:
        raise ValueError(f"Baselines no soportados en esta fase: {invalid}")


def predict_baseline(
    model_name: str,
    train_df: pd.DataFrame,
    predict_df: pd.DataFrame,
    target_col: str = "pasajeros_total",
    verbose: bool = False,
) -> pd.Series:
    """Generate predictions for one baseline model."""
    validate_model_names([model_name])
    if model_name == "naive":
        if verbose:
            print("      [predict] naive usa lag_1: franja anterior de la misma ruta")
        return predict_df["lag_1"].astype(float)
    if model_name == "seasonal_naive_daily":
        if verbose:
            print("      [predict] seasonal_naive_daily usa lag_48: misma franja del dia anterior")
        return predict_df["lag_48"].astype(float)
    if model_name == "seasonal_naive_weekly":
        if verbose:
            print(
                "      [predict] seasonal_naive_weekly usa lag_336: misma franja de la semana anterior"
            )
        return predict_df["lag_336"].astype(float)
    model = HistoricalAverageBaseline(target_col=target_col, verbose=verbose).fit(train_df)
    return model.predict(predict_df)
