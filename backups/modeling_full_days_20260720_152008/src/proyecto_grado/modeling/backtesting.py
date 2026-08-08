"""Backtesting orchestration for baseline models."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict

import pandas as pd

from proyecto_grado.modeling.baselines import predict_baseline, validate_model_names
from proyecto_grado.modeling.evaluate import add_error_columns, metrics_by_group
from proyecto_grado.modeling.splits import (
    FinalTestWindow,
    TemporalFold,
    folds_to_frame,
    make_expanding_folds,
    make_final_test_window,
    window_masks,
)


def _prediction_frame(
    predict_df: pd.DataFrame,
    y_pred: pd.Series,
    model_name: str,
    run_id: str,
    fold: str,
    split: str,
    horizon: int,
    granularity_min: int,
    target: str = "pasajeros_total",
    scenario: str = "sin_oferta",
    feature_set: str = "calendario_ruta_lags_demanda",
    target_col: str = "pasajeros_total",
    observed_flag: str = "target_observed",
) -> pd.DataFrame:
    """Create the persisted prediction schema required by the project."""
    if int(horizon) != 1:
        raise NotImplementedError("Esta fase solo persiste predicciones horizon=1")
    timestamp = pd.to_datetime(predict_df["timestamp"])
    interval_start = pd.to_datetime(
        predict_df.get("target_interval_start", predict_df["timestamp"])
    )
    interval_end = pd.to_datetime(
        predict_df.get(
            "target_interval_end",
            timestamp + pd.Timedelta(minutes=int(granularity_min)),
        )
    )
    feature_cutoff = pd.to_datetime(predict_df.get("feature_cutoff_timestamp", interval_start))
    source_hash = (
        predict_df["source_hash"].to_numpy()
        if "source_hash" in predict_df.columns
        else pd.Series([pd.NA] * len(predict_df)).to_numpy()
    )
    despachos = (
        predict_df["despachos_count_real"].astype(float).to_numpy()
        if "despachos_count_real" in predict_df.columns
        else pd.Series([pd.NA] * len(predict_df)).to_numpy()
    )
    productividad = (
        predict_df["pasajeros_por_despacho_real"].astype(float).to_numpy()
        if "pasajeros_por_despacho_real" in predict_df.columns
        else pd.Series([pd.NA] * len(predict_df)).to_numpy()
    )
    dispatch_level = (
        predict_df["dispatch_history_level"].astype(str).to_numpy()
        if "dispatch_history_level" in predict_df.columns
        else pd.Series([pd.NA] * len(predict_df)).to_numpy()
    )
    out = pd.DataFrame(
        {
            "dataset_version": predict_df["dataset_version"].to_numpy(),
            "source_hash": source_hash,
            "run_id": run_id,
            "target": target,
            "scenario": scenario,
            "feature_set": feature_set,
            "model": model_name,
            "route": predict_df["FK_RUTA"].astype(int).to_numpy(),
            "granularity_min": granularity_min,
            "fold": str(fold),
            "split": split,
            "origin_timestamp": timestamp,
            "target_interval_start": interval_start,
            "target_interval_end": interval_end,
            "feature_cutoff_timestamp": feature_cutoff,
            "timestamp": timestamp,
            "horizon": horizon,
            "y_real": predict_df[target_col].astype(float).to_numpy(),
            "y_pred": y_pred.to_numpy(dtype=float),
            "tipo_dia": predict_df["tipo_dia"].astype(str).to_numpy(),
            "hora_del_dia": predict_df["hora_del_dia"].astype(int).to_numpy(),
            "is_gap": predict_df["is_gap"].astype(bool).to_numpy(),
            "gap_tipo": predict_df["gap_tipo"].astype(str).to_numpy(),
            "target_observed": predict_df[observed_flag].astype(bool).to_numpy(),
            "despachos_count_real": despachos,
            "pasajeros_por_despacho_real": productividad,
            "dispatch_history_level": dispatch_level,
        }
    )
    return add_error_columns(out)


def _assign_dispatch_history_level(
    train_df: pd.DataFrame,
    predict_df: pd.DataFrame,
    history_col: str = "despachos_count_real_lag_48",
) -> pd.DataFrame:
    """Classify evaluation rows by lagged dispatch history using train quantiles."""
    data = predict_df.copy()
    if history_col not in data.columns or history_col not in train_df.columns:
        data["dispatch_history_level"] = pd.NA
        return data

    train_values = pd.to_numeric(train_df[history_col], errors="coerce").dropna()
    if train_values.empty:
        data["dispatch_history_level"] = pd.NA
        return data

    q_low, q_high = train_values.quantile([1 / 3, 2 / 3]).to_list()
    values = pd.to_numeric(data[history_col], errors="coerce")
    data["dispatch_history_level"] = pd.NA
    data.loc[values <= q_low, "dispatch_history_level"] = "bajo"
    data.loc[(values > q_low) & (values <= q_high), "dispatch_history_level"] = "medio"
    data.loc[values > q_high, "dispatch_history_level"] = "alto"
    return data


def predict_window(
    dataset: pd.DataFrame,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    eval_start: pd.Timestamp,
    eval_end: pd.Timestamp,
    model_names: Iterable[str],
    run_id: str,
    fold: str,
    split: str,
    horizon: int = 1,
    granularity_min: int = 30,
    target: str = "pasajeros_total",
    scenario: str = "sin_oferta",
    feature_set: str = "calendario_ruta_lags_demanda",
    target_col: str = "pasajeros_total",
    observed_flag: str = "target_observed",
    verbose: bool = False,
) -> pd.DataFrame:
    """Predict one temporal evaluation window for all requested baselines."""
    if int(horizon) != 1:
        raise NotImplementedError("Esta fase solo soporta horizon=1")
    model_names = list(model_names)
    validate_model_names(model_names)
    train_mask, eval_mask = window_masks(dataset, train_start, train_end, eval_start, eval_end)
    train_df = dataset.loc[train_mask & dataset[observed_flag].astype(bool)].copy()
    predict_df = dataset.loc[eval_mask].copy()
    predict_df = _assign_dispatch_history_level(train_df, predict_df)
    if train_df.empty:
        raise ValueError(f"Fold {fold}: entrenamiento vacio")
    if predict_df.empty:
        raise ValueError(f"Fold {fold}: evaluacion vacia")

    if verbose:
        print("\n" + "-" * 72)
        print(f"[fold {fold} | {split} | target={target} | scenario={scenario}]")
        print(f"  train: {train_start} -> {train_end} | filas observadas: {len(train_df):,}")
        print(f"  eval : {eval_start} -> {eval_end} | filas a predecir: {len(predict_df):,}")
        print(f"  eval por ruta: {predict_df['FK_RUTA'].value_counts().sort_index().to_dict()}")
        print(f"  gaps en eval: {int(predict_df['is_gap'].sum()):,} de {len(predict_df):,} filas")

    predictions: list[pd.DataFrame] = []
    for model_name in model_names:
        if verbose:
            print(f"  modelo: {model_name}")
        y_pred = predict_baseline(
            model_name,
            train_df,
            predict_df,
            target_col=target_col,
            scenario=scenario,
            horizon=horizon,
            verbose=verbose,
        )
        pred_frame = _prediction_frame(
            predict_df=predict_df,
            y_pred=y_pred,
            model_name=model_name,
            run_id=run_id,
            fold=fold,
            split=split,
            horizon=horizon,
            granularity_min=granularity_min,
            target=target,
            scenario=scenario,
            feature_set=feature_set,
            target_col=target_col,
            observed_flag=observed_flag,
        )
        if verbose:
            evaluable = pred_frame.dropna(subset=["y_real", "y_pred"])
            print(f"      predicciones generadas: {len(pred_frame):,}")
            print(f"      y_real faltante por gaps: {int(pred_frame['y_real'].isna().sum()):,}")
            print(f"      y_pred faltante: {int(pred_frame['y_pred'].isna().sum()):,}")
            print(f"      filas evaluables para metricas: {len(evaluable):,}")
        predictions.append(pred_frame)
    return pd.concat(predictions, ignore_index=True)


def run_baseline_backtesting(
    dataset: pd.DataFrame,
    model_names: list[str],
    run_id: str,
    test_weeks: int = 10,
    validation_weeks: int = 2,
    step_weeks: int = 2,
    min_train_weeks: int = 26,
    horizon: int = 1,
    granularity_min: int = 30,
    target: str = "pasajeros_total",
    scenario: str = "sin_oferta",
    feature_set: str = "calendario_ruta_lags_demanda",
    target_col: str = "pasajeros_total",
    observed_flag: str = "target_observed",
    max_folds: int | None = None,
    verbose: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run expanding-window validation and the final 10-week holdout."""
    if int(horizon) != 1:
        raise NotImplementedError("Esta fase solo soporta horizon=1")
    data = dataset.sort_values(["FK_RUTA", "timestamp"]).reset_index(drop=True).copy()
    folds = make_expanding_folds(
        data,
        validation_weeks=validation_weeks,
        step_weeks=step_weeks,
        min_train_weeks=min_train_weeks,
        test_weeks=test_weeks,
    )
    if max_folds is not None:
        folds = folds[: int(max_folds)]
    final_test = make_final_test_window(
        data, test_weeks=test_weeks, granularity_min=granularity_min
    )

    if verbose:
        print("\nBACKTESTING - RESUMEN DE CONFIGURACION")
        print(f"  filas dataset: {len(data):,}")
        print(f"  rango dataset: {data['timestamp'].min()} -> {data['timestamp'].max()}")
        print(f"  rutas: {sorted(data['FK_RUTA'].dropna().unique().tolist())}")
        print(f"  target: {target} ({target_col}) | scenario: {scenario}")
        print(f"  modelos: {', '.join(model_names)}")
        print(f"  granularidad: {granularity_min} min | horizonte: {horizon} franja(s)")
        print(
            "  ventanas: "
            f"train minimo {min_train_weeks} semanas, "
            f"validacion {validation_weeks} semanas, "
            f"paso {step_weeks} semanas, "
            f"test final {test_weeks} semanas"
        )
        print(f"  folds de validacion: {len(folds)}")
        print(
            "  test final: "
            f"{final_test.test_start} -> {final_test.test_end} "
            f"(train hasta {final_test.train_end})"
        )

    pred_parts: list[pd.DataFrame] = []
    for fold in folds:
        pred_parts.append(
            predict_window(
                dataset=data,
                train_start=fold.train_start,
                train_end=fold.train_end,
                eval_start=fold.validation_start,
                eval_end=fold.validation_end,
                model_names=model_names,
                run_id=run_id,
                fold=fold.fold,
                split=fold.split,
                horizon=horizon,
                granularity_min=granularity_min,
                target=target,
                scenario=scenario,
                feature_set=feature_set,
                target_col=target_col,
                observed_flag=observed_flag,
                verbose=verbose,
            )
        )

    pred_parts.append(
        predict_window(
            dataset=data,
            train_start=final_test.train_start,
            train_end=final_test.train_end,
            eval_start=final_test.test_start,
            eval_end=final_test.test_end,
            model_names=model_names,
            run_id=run_id,
            fold=final_test.fold,
            split=final_test.split,
            horizon=horizon,
            granularity_min=granularity_min,
            target=target,
            scenario=scenario,
            feature_set=feature_set,
            target_col=target_col,
            observed_flag=observed_flag,
            verbose=verbose,
        )
    )
    predictions = pd.concat(pred_parts, ignore_index=True)

    metrics_by_fold = metrics_by_group(
        predictions,
        ["target", "scenario", "feature_set", "split", "fold", "model", "route"],
    )
    metrics_comparison = metrics_by_group(
        predictions,
        ["target", "scenario", "feature_set", "split", "model", "route"],
    )
    folds_frame = folds_to_frame(folds, final_test)
    folds_frame["run_id"] = run_id
    folds_frame["target"] = target
    folds_frame["scenario"] = scenario
    folds_frame["config"] = str(
        {
            "test_weeks": test_weeks,
            "validation_weeks": validation_weeks,
            "step_weeks": step_weeks,
            "min_train_weeks": min_train_weeks,
        }
    )
    return predictions, metrics_by_fold, metrics_comparison, folds_frame


def run_multitarget_backtesting(
    datasets: dict[str, pd.DataFrame],
    scenario_specs: dict[str, dict[str, str]],
    model_names: list[str],
    run_id: str,
    test_weeks: int = 10,
    validation_weeks: int = 2,
    step_weeks: int = 2,
    min_train_weeks: int = 26,
    horizon: int = 1,
    granularity_min: int = 30,
    max_folds: int | None = None,
    verbose: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the same baselines for every configured target/scenario dataset."""
    pred_parts: list[pd.DataFrame] = []
    fold_parts: list[pd.DataFrame] = []
    for scenario_name, dataset in datasets.items():
        spec = scenario_specs[scenario_name]
        predictions, _, _, folds = run_baseline_backtesting(
            dataset=dataset,
            model_names=model_names,
            run_id=run_id,
            test_weeks=test_weeks,
            validation_weeks=validation_weeks,
            step_weeks=step_weeks,
            min_train_weeks=min_train_weeks,
            horizon=horizon,
            granularity_min=granularity_min,
            target=spec["target"],
            scenario=scenario_name,
            feature_set=spec["feature_set"],
            target_col=spec["target_col"],
            observed_flag=spec["observed_flag"],
            max_folds=max_folds,
            verbose=verbose,
        )
        pred_parts.append(predictions)
        fold_parts.append(folds)

    predictions = pd.concat(pred_parts, ignore_index=True)
    metrics_by_fold = metrics_by_group(
        predictions,
        ["target", "scenario", "feature_set", "split", "fold", "model", "route"],
    )
    metrics_comparison = metrics_by_group(
        predictions,
        ["target", "scenario", "feature_set", "split", "model", "route"],
    )
    folds_frame = pd.concat(fold_parts, ignore_index=True).drop_duplicates(
        [
            "split",
            "fold",
            "train_start",
            "train_end",
            "eval_start",
            "eval_end",
            "target",
            "scenario",
        ]
    )
    return predictions, metrics_by_fold, metrics_comparison, folds_frame


def windows_to_metadata(
    folds: list[TemporalFold], final_test: FinalTestWindow
) -> dict[str, object]:
    """Serialize windows for run metadata."""
    return {
        "folds": [asdict(fold) for fold in folds],
        "final_test": asdict(final_test),
    }
