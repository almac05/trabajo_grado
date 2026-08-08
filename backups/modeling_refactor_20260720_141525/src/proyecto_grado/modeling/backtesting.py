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
) -> pd.DataFrame:
    """Create the persisted prediction schema required by the project."""
    out = pd.DataFrame(
        {
            "dataset_version": predict_df["dataset_version"].to_numpy(),
            "run_id": run_id,
            "model": model_name,
            "route": predict_df["FK_RUTA"].astype(int).to_numpy(),
            "granularity_min": granularity_min,
            "fold": str(fold),
            "split": split,
            "origin_timestamp": pd.to_datetime(predict_df["timestamp"])
            - pd.Timedelta(minutes=granularity_min * horizon),
            "timestamp": pd.to_datetime(predict_df["timestamp"]),
            "horizon": horizon,
            "y_real": predict_df["pasajeros_total"].astype(float).to_numpy(),
            "y_pred": y_pred.to_numpy(dtype=float),
            "tipo_dia": predict_df["tipo_dia"].astype(str).to_numpy(),
            "hora_del_dia": predict_df["hora_del_dia"].astype(int).to_numpy(),
            "is_gap": predict_df["is_gap"].astype(bool).to_numpy(),
            "gap_tipo": predict_df["gap_tipo"].astype(str).to_numpy(),
            "target_observed": predict_df["target_observed"].astype(bool).to_numpy(),
        }
    )
    return add_error_columns(out)


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
    verbose: bool = False,
) -> pd.DataFrame:
    """Predict one temporal evaluation window for all requested baselines."""
    model_names = list(model_names)
    validate_model_names(model_names)
    train_mask, eval_mask = window_masks(dataset, train_start, train_end, eval_start, eval_end)
    train_df = dataset.loc[train_mask & dataset["target_observed"].astype(bool)].copy()
    predict_df = dataset.loc[eval_mask].copy()
    if train_df.empty:
        raise ValueError(f"Fold {fold}: entrenamiento vacio")
    if predict_df.empty:
        raise ValueError(f"Fold {fold}: evaluacion vacia")

    if verbose:
        print("\n" + "-" * 72)
        print(f"[fold {fold} | {split}]")
        print(f"  train: {train_start} -> {train_end} | filas observadas: {len(train_df):,}")
        print(f"  eval : {eval_start} -> {eval_end} | filas a predecir: {len(predict_df):,}")
        print(f"  eval por ruta: {predict_df['FK_RUTA'].value_counts().sort_index().to_dict()}")
        print(f"  gaps en eval: {int(predict_df['is_gap'].sum()):,} de {len(predict_df):,} filas")

    predictions: list[pd.DataFrame] = []
    for model_name in model_names:
        if verbose:
            print(f"  modelo: {model_name}")
        y_pred = predict_baseline(model_name, train_df, predict_df, verbose=verbose)
        pred_frame = _prediction_frame(
            predict_df=predict_df,
            y_pred=y_pred,
            model_name=model_name,
            run_id=run_id,
            fold=fold,
            split=split,
            horizon=horizon,
            granularity_min=granularity_min,
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
    max_folds: int | None = None,
    verbose: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run expanding-window validation and the final 10-week holdout."""
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
            verbose=verbose,
        )
    )
    predictions = pd.concat(pred_parts, ignore_index=True)

    metrics_by_fold = metrics_by_group(predictions, ["split", "fold", "model", "route"])
    metrics_comparison = metrics_by_group(predictions, ["split", "model", "route"])
    folds_frame = folds_to_frame(folds, final_test)
    folds_frame["run_id"] = run_id
    folds_frame["config"] = str(
        {
            "test_weeks": test_weeks,
            "validation_weeks": validation_weeks,
            "step_weeks": step_weeks,
            "min_train_weeks": min_train_weeks,
        }
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
