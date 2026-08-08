"""Temporal splits and expanding-window backtesting utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TemporalFold:
    """A half-open temporal validation window."""

    fold: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    split: str = "validation"


@dataclass(frozen=True)
class FinalTestWindow:
    """Final holdout period after all backtesting folds."""

    fold: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    split: str = "test_final"


def dataset_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return min and max timestamps for the dataset."""
    if df.empty:
        raise ValueError("No se pueden calcular splits sobre dataset vacio")
    ts = pd.to_datetime(df["timestamp"])
    return pd.Timestamp(ts.min()), pd.Timestamp(ts.max())


def make_final_test_window(
    df: pd.DataFrame,
    test_weeks: int = 10,
    granularity_min: int = 30,
) -> FinalTestWindow:
    """Reserve the last ``test_weeks`` as final temporal holdout."""
    start, end = dataset_bounds(df)
    test_start = end - pd.Timedelta(weeks=int(test_weeks))
    test_end = end + pd.Timedelta(minutes=int(granularity_min))
    if test_start <= start:
        raise ValueError("El periodo de test consume todo el dataset")
    return FinalTestWindow(
        fold="test_final",
        train_start=start,
        train_end=test_start,
        test_start=test_start,
        test_end=test_end,
    )


def make_expanding_folds(
    df: pd.DataFrame,
    validation_weeks: int = 2,
    step_weeks: int = 2,
    min_train_weeks: int = 26,
    test_weeks: int = 10,
) -> list[TemporalFold]:
    """Create expanding-window folds before the final test period."""
    start, end = dataset_bounds(df)
    test_start = end - pd.Timedelta(weeks=int(test_weeks))
    val_delta = pd.Timedelta(weeks=int(validation_weeks))
    step_delta = pd.Timedelta(weeks=int(step_weeks))
    first_val_start = start + pd.Timedelta(weeks=int(min_train_weeks))

    folds: list[TemporalFold] = []
    val_start = first_val_start
    fold_idx = 1
    while val_start + val_delta <= test_start:
        folds.append(
            TemporalFold(
                fold=str(fold_idx),
                train_start=start,
                train_end=val_start,
                validation_start=val_start,
                validation_end=val_start + val_delta,
            )
        )
        val_start = val_start + step_delta
        fold_idx += 1

    if not folds:
        raise ValueError("No se generaron folds; reduzca min_train_weeks o validation_weeks")
    validate_temporal_folds(folds, test_start)
    return folds


def validate_temporal_folds(folds: list[TemporalFold], test_start: pd.Timestamp) -> None:
    """Validate temporal ordering and absence of train/validation leakage."""
    previous_val_end: pd.Timestamp | None = None
    for fold in folds:
        if not (fold.train_start < fold.train_end <= fold.validation_start < fold.validation_end):
            raise ValueError(f"Fold {fold.fold} tiene orden temporal invalido")
        if fold.validation_end > test_start:
            raise ValueError(f"Fold {fold.fold} invade el test final")
        if previous_val_end is not None and fold.validation_start < previous_val_end:
            raise ValueError("Los folds de validacion se solapan")
        previous_val_end = fold.validation_end


def window_masks(
    df: pd.DataFrame,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    eval_start: pd.Timestamp,
    eval_end: pd.Timestamp,
) -> tuple[pd.Series, pd.Series]:
    """Return train and evaluation masks for half-open temporal windows."""
    ts = pd.to_datetime(df["timestamp"])
    train_mask = (ts >= train_start) & (ts < train_end)
    eval_mask = (ts >= eval_start) & (ts < eval_end)
    if train_mask.any() and eval_mask.any() and ts[train_mask].max() >= ts[eval_mask].min():
        raise ValueError("Fuga temporal: train alcanza o supera inicio de evaluacion")
    return train_mask, eval_mask


def folds_to_frame(folds: list[TemporalFold], final_test: FinalTestWindow) -> pd.DataFrame:
    """Convert fold objects to a tabular audit trail."""
    rows: list[dict[str, object]] = []
    for fold in folds:
        rows.append(
            {
                "split": fold.split,
                "fold": fold.fold,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "eval_start": fold.validation_start,
                "eval_end": fold.validation_end,
            }
        )
    rows.append(
        {
            "split": final_test.split,
            "fold": final_test.fold,
            "train_start": final_test.train_start,
            "train_end": final_test.train_end,
            "eval_start": final_test.test_start,
            "eval_end": final_test.test_end,
        }
    )
    return pd.DataFrame(rows)
