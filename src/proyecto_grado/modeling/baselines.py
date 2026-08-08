"""Baseline forecasters for the first reproducible modeling phase."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

ROLLING_AVERAGE_VARIANTS: dict[str, int] = {
    "rolling_average_4w": 4,
    "rolling_average_8w": 8,
    "rolling_average_12w": 12,
    "rolling_average_26w": 26,
}

BASELINE_MODELS = [
    "naive",
    "seasonal_naive_daily",
    "seasonal_naive_weekly",
    "historical_average_route_day_type_slot",
    *ROLLING_AVERAGE_VARIANTS,
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
    **{
        name: BaselineDescription(
            name,
            f"Promedio movil de las ultimas {weeks} semanas por ruta, "
            "tipo de dia y franja de 30 minutos, con jerarquia de fallback.",
        )
        for name, weeks in ROLLING_AVERAGE_VARIANTS.items()
    },
}


def _target_prefix(target_col: str) -> str:
    """Map a target column to its lag feature prefix."""
    if target_col == "pasajeros_por_despacho_real":
        return "pasajeros_por_despacho"
    if target_col == "despachos_count_real":
        return "despachos_count_real"
    return "pasajeros_total"


def _lag_column_for_target(target_col: str, lag: int, predict_df: pd.DataFrame) -> str:
    """Return the lag column to use for a target, preserving legacy aliases."""
    explicit = f"{_target_prefix(target_col)}_lag_{lag}"
    if explicit in predict_df.columns:
        return explicit
    legacy = f"lag_{lag}"
    if target_col == "pasajeros_total" and legacy in predict_df.columns:
        return legacy
    raise ValueError(f"Falta columna de lag requerida: {explicit}")


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


def _shift_franja(franja: str, steps: int) -> str:
    """Return the 30-minute slot label `steps` positions away from `franja`."""
    base = pd.Timestamp("2000-01-01 " + franja)
    shifted = base + pd.Timedelta(minutes=30 * steps)
    return shifted.strftime("%H:%M")


class RollingAverageBaseline:
    """Rolling-window average baseline with a documented fallback hierarchy.

    Niveles de fallback quando la celda (ruta, tipo_dia, franja) no tiene al
    menos ``min_obs_celda`` observaciones dentro de la ventana ``W``:
    1. (ruta, tipo_dia, franja) en ventana W.
    2. (ruta, tipo_dia, franja) en ventana ampliada 2W.
    3. Franjas adyacentes (franja-30min, franja+30min) para (ruta, tipo_dia), en W.
    4. (ruta, franja) sin distinguir tipo_dia, en W.
    5. Media global de la ruta en W (o 2W si la ruta no tiene datos en W).
    """

    def __init__(
        self,
        window_weeks: int,
        target_col: str = "pasajeros_total",
        min_obs_celda: int = 3,
        expanded_multiplier: int = 2,
        verbose: bool = False,
    ) -> None:
        self.window_weeks = int(window_weeks)
        self.target_col = target_col
        self.min_obs_celda = int(min_obs_celda)
        self.expanded_multiplier = int(expanded_multiplier)
        self.verbose = verbose
        self.level1_: pd.DataFrame | None = None
        self.level2_: pd.DataFrame | None = None
        self.level3_: pd.DataFrame | None = None
        self.level4_: pd.DataFrame | None = None
        self.level5_: pd.DataFrame | None = None
        self.global_fallback_: float | None = None

    def _window(
        self,
        observed: pd.DataFrame,
        train_end: pd.Timestamp,
        weeks: int,
    ) -> pd.DataFrame:
        start = train_end - pd.Timedelta(weeks=weeks)
        ts = observed["timestamp"]
        return observed.loc[(ts >= start) & (ts < train_end)]

    @staticmethod
    def _grouped_mean(df: pd.DataFrame, keys: list[str], min_count: int) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=[*keys, "pred_value"])
        agg = df.groupby(keys, as_index=False).agg(
            pred_value=("_target_value", "mean"),
            _count=("_target_value", "count"),
        )
        return agg.loc[agg["_count"] >= min_count, [*keys, "pred_value"]]

    def fit(self, train_df: pd.DataFrame, train_end: pd.Timestamp) -> RollingAverageBaseline:
        """Fit hierarchical rolling averages strictly before `train_end`."""
        observed = train_df[train_df[self.target_col].notna()].copy()
        if "target_observed" in observed.columns:
            observed = observed[observed["target_observed"].astype(bool)]
        if observed.empty:
            raise ValueError("No hay observaciones de entrenamiento para promedio movil")
        observed["timestamp"] = pd.to_datetime(observed["timestamp"])
        observed["_target_value"] = observed[self.target_col].astype(float)
        train_end = pd.Timestamp(train_end)

        win_w = self._window(observed, train_end, self.window_weeks)
        win_2w = self._window(observed, train_end, self.window_weeks * self.expanded_multiplier)

        self.level1_ = self._grouped_mean(
            win_w, ["FK_RUTA", "tipo_dia", "franja_30min"], self.min_obs_celda
        )
        self.level2_ = self._grouped_mean(
            win_2w, ["FK_RUTA", "tipo_dia", "franja_30min"], self.min_obs_celda
        )
        self.level4_ = self._grouped_mean(win_w, ["FK_RUTA", "franja_30min"], self.min_obs_celda)

        self.level3_ = self._fit_adjacent_slots(win_w)

        route_w = win_w.groupby("FK_RUTA")["_target_value"].mean()
        route_2w = win_2w.groupby("FK_RUTA")["_target_value"].mean()
        self.level5_ = route_w.combine_first(route_2w).rename("pred_value").reset_index()
        self.global_fallback_ = float(
            win_w["_target_value"].mean() if not win_w.empty else win_2w["_target_value"].mean()
        )

        if self.verbose:
            print(f"      [fit] rolling_average_{self.window_weeks}w")
            print(f"            filas en ventana W: {len(win_w):,}; en 2W: {len(win_2w):,}")
            print(
                "            celdas nivel1: "
                f"{len(self.level1_):,}; nivel2: {len(self.level2_):,}; "
                f"nivel3: {len(self.level3_):,}; nivel4: {len(self.level4_):,}"
            )
        return self

    def _fit_adjacent_slots(self, win_w: pd.DataFrame) -> pd.DataFrame:
        """Pool observations of the neighboring 30-minute slots per (ruta, tipo_dia).

        A row observed at franja `F` is a "previous neighbor" contribution for
        the target cell `F+1` and a "next neighbor" contribution for `F-1`.
        Relabeling and pooling this way lets a target cell receive a level-3
        estimate even when it has zero observations anywhere in `win_w`
        (e.g. a slot the route never actually served), as long as at least
        one of its neighbors was observed within the window.
        """
        if win_w.empty:
            return pd.DataFrame(columns=["FK_RUTA", "tipo_dia", "franja_30min", "pred_value"])

        as_prev_neighbor = win_w.copy()
        as_prev_neighbor["franja_30min"] = as_prev_neighbor["franja_30min"].map(
            lambda f: _shift_franja(f, 1)
        )
        as_next_neighbor = win_w.copy()
        as_next_neighbor["franja_30min"] = as_next_neighbor["franja_30min"].map(
            lambda f: _shift_franja(f, -1)
        )
        pooled = pd.concat([as_prev_neighbor, as_next_neighbor], ignore_index=True)
        return self._grouped_mean(
            pooled, ["FK_RUTA", "tipo_dia", "franja_30min"], self.min_obs_celda
        )

    def predict(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """Predict using the fallback hierarchy; also return the level used per row."""
        if self.level1_ is None:
            raise RuntimeError("RollingAverageBaseline debe ajustarse antes de predecir")

        pred = df[["FK_RUTA", "tipo_dia", "franja_30min"]].copy()
        pred = pred.merge(
            self.level1_.rename(columns={"pred_value": "v1"}),
            on=["FK_RUTA", "tipo_dia", "franja_30min"],
            how="left",
        )
        pred = pred.merge(
            self.level2_.rename(columns={"pred_value": "v2"}),
            on=["FK_RUTA", "tipo_dia", "franja_30min"],
            how="left",
        )
        pred = pred.merge(
            self.level3_.rename(columns={"pred_value": "v3"}),
            on=["FK_RUTA", "tipo_dia", "franja_30min"],
            how="left",
        )
        pred = pred.merge(
            self.level4_.rename(columns={"pred_value": "v4"}),
            on=["FK_RUTA", "franja_30min"],
            how="left",
        )
        pred = pred.merge(
            self.level5_.rename(columns={"pred_value": "v5"}),
            on=["FK_RUTA"],
            how="left",
        )
        pred["v5"] = pred["v5"].fillna(self.global_fallback_)

        values = pred["v1"].copy()
        level = pd.Series(pd.NA, index=pred.index, dtype="object")
        level.loc[values.notna()] = "1"
        for col, lvl in (("v2", "2"), ("v3", "3"), ("v4", "4"), ("v5", "5")):
            fills = values.isna() & pred[col].notna()
            values = values.fillna(pred[col])
            level.loc[fills] = lvl

        if self.verbose:
            print(f"      [predict] rolling_average_{self.window_weeks}w")
            print(
                f"                distribucion de niveles de fallback: {level.value_counts().to_dict()}"
            )
        return values.astype(float), level


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
    scenario: str = "sin_oferta",
    horizon: int = 1,
    train_end: pd.Timestamp | None = None,
    return_meta: bool = False,
    verbose: bool = False,
) -> pd.Series | tuple[pd.Series, dict[str, pd.Series] | None]:
    """Generate predictions for one baseline model.

    When `return_meta` is True, returns `(y_pred, meta)`, where `meta` is
    `None` for baselines without auxiliary output and a dict with
    `fallback_level` for `rolling_average_*` baselines.
    """
    if int(horizon) != 1:
        raise NotImplementedError("Los baselines actuales solo implementan horizon=1")
    validate_model_names([model_name])
    meta: dict[str, pd.Series] | None = None
    if model_name == "naive":
        lag_col = _lag_column_for_target(target_col, 1, predict_df)
        if verbose:
            print(
                "      [predict] naive usa "
                f"{lag_col}: franja anterior de la misma ruta | escenario={scenario}"
            )
        y_pred = predict_df[lag_col].astype(float)
    elif model_name == "seasonal_naive_daily":
        lag_col = _lag_column_for_target(target_col, 48, predict_df)
        if verbose:
            print(
                f"      [predict] seasonal_naive_daily usa {lag_col}: misma franja del dia anterior"
            )
        y_pred = predict_df[lag_col].astype(float)
    elif model_name == "seasonal_naive_weekly":
        lag_col = _lag_column_for_target(target_col, 336, predict_df)
        if verbose:
            print(
                "      [predict] seasonal_naive_weekly usa "
                f"{lag_col}: misma franja de la semana anterior"
            )
        y_pred = predict_df[lag_col].astype(float)
    elif model_name in ROLLING_AVERAGE_VARIANTS:
        if train_end is None:
            raise ValueError(f"{model_name} requiere train_end para acotar la ventana movil")
        window_weeks = ROLLING_AVERAGE_VARIANTS[model_name]
        model = RollingAverageBaseline(
            window_weeks=window_weeks,
            target_col=target_col,
            verbose=verbose,
        ).fit(train_df, pd.Timestamp(train_end))
        y_pred, fallback_level = model.predict(predict_df)
        meta = {"fallback_level": fallback_level}
    else:
        model = HistoricalAverageBaseline(target_col=target_col, verbose=verbose).fit(train_df)
        y_pred = model.predict(predict_df)

    if return_meta:
        return y_pred, meta
    return y_pred
