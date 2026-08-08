"""Temporal splits and expanding-window backtesting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd

DEFAULT_OPERATIONAL_DAY_START = "04:00:00"


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


@dataclass(frozen=True)
class AlignmentResult:
    """Temporal bounds aligned to complete operational days."""

    original_start: pd.Timestamp
    original_end: pd.Timestamp
    aligned_start: pd.Timestamp
    aligned_end: pd.Timestamp
    operational_day_start: str
    granularity_min: int
    start_rows_excluded: int = 0
    end_rows_excluded: int = 0
    start_operational_days_excluded: int = 0
    end_operational_days_excluded: int = 0


def dataset_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return min and max timestamps for the dataset."""
    if df.empty:
        raise ValueError("No se pueden calcular splits sobre dataset vacio")
    ts = pd.to_datetime(df["timestamp"])
    return pd.Timestamp(ts.min()), pd.Timestamp(ts.max())


def parse_operational_day_start(value: str | time = DEFAULT_OPERATIONAL_DAY_START) -> time:
    """Parse the configured operational-day start time."""
    if isinstance(value, time):
        return value
    return pd.Timestamp(str(value)).time()


def _boundary_for_date(ts: pd.Timestamp, operational_day_start: str | time) -> pd.Timestamp:
    """Return the operational-day boundary on the calendar date of ``ts``."""
    start_time = parse_operational_day_start(operational_day_start)
    return pd.Timestamp.combine(ts.date(), start_time)


def align_start_to_operational_day(
    start: pd.Timestamp,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
) -> pd.Timestamp:
    """Align a start timestamp upward to the next complete operational day."""
    start = pd.Timestamp(start)
    boundary = _boundary_for_date(start, operational_day_start)
    if start == boundary:
        return boundary
    if start < boundary:
        return boundary
    return boundary + pd.Timedelta(days=1)


def align_end_to_operational_day(
    end_exclusive: pd.Timestamp,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
) -> pd.Timestamp:
    """Align an exclusive end timestamp downward to a complete operational-day boundary."""
    end_exclusive = pd.Timestamp(end_exclusive)
    boundary = _boundary_for_date(end_exclusive, operational_day_start)
    if end_exclusive >= boundary:
        return boundary
    return boundary - pd.Timedelta(days=1)


def operational_day_label(
    ts: pd.Series | pd.Timestamp,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
) -> pd.Series | pd.Timestamp:
    """Return the date label of the operational day containing each timestamp."""
    start_time = parse_operational_day_start(operational_day_start)
    if isinstance(ts, pd.Series):
        values = pd.to_datetime(ts)
        labels = values.dt.normalize()
        before_start = values.dt.time < start_time
        labels.loc[before_start] = labels.loc[before_start] - pd.Timedelta(days=1)
        return labels

    value = pd.Timestamp(ts)
    label = value.normalize()
    if value.time() < start_time:
        label -= pd.Timedelta(days=1)
    return label


def _rows_between(
    df: pd.DataFrame | None,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Return rows in a half-open interval, or an empty frame when no df is provided."""
    if df is None or end <= start:
        return pd.DataFrame()
    ts = pd.to_datetime(df["timestamp"])
    return df.loc[(ts >= start) & (ts < end)].copy()


def align_to_full_operational_days(
    df: pd.DataFrame | None = None,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
    granularity_min: int = 30,
    end_is_inclusive: bool = False,
) -> AlignmentResult:
    """Align a half-open range to complete operational days.

    When ``df`` is passed without explicit bounds, the available range is
    interpreted as ``[min(timestamp), max(timestamp) + granularity)`` because
    time bins are labelled by their left edge.
    """
    if df is None and (start is None or end is None):
        raise ValueError("Debe pasar df o limites start/end")

    if start is None:
        if df is None or df.empty:
            raise ValueError("No se puede alinear un dataframe vacio")
        start_ts = pd.Timestamp(pd.to_datetime(df["timestamp"]).min())
    else:
        start_ts = pd.Timestamp(start)

    if end is None:
        if df is None or df.empty:
            raise ValueError("No se puede alinear un dataframe vacio")
        end_ts = pd.Timestamp(pd.to_datetime(df["timestamp"]).max()) + pd.Timedelta(
            minutes=int(granularity_min)
        )
    else:
        end_ts = pd.Timestamp(end)
        if end_is_inclusive:
            end_ts += pd.Timedelta(minutes=int(granularity_min))

    aligned_start = align_start_to_operational_day(start_ts, operational_day_start)
    aligned_end = align_end_to_operational_day(end_ts, operational_day_start)
    if aligned_end <= aligned_start:
        raise ValueError("La ventana queda vacia despues de alinear a dias operativos completos")

    start_excluded = _rows_between(df, start_ts, aligned_start)
    end_excluded = _rows_between(df, aligned_end, end_ts)

    return AlignmentResult(
        original_start=start_ts,
        original_end=end_ts,
        aligned_start=aligned_start,
        aligned_end=aligned_end,
        operational_day_start=str(operational_day_start),
        granularity_min=int(granularity_min),
        start_rows_excluded=len(start_excluded),
        end_rows_excluded=len(end_excluded),
        start_operational_days_excluded=int(
            operational_day_label(start_excluded["timestamp"], operational_day_start).nunique()
        )
        if not start_excluded.empty
        else 0,
        end_operational_days_excluded=int(
            operational_day_label(end_excluded["timestamp"], operational_day_start).nunique()
        )
        if not end_excluded.empty
        else 0,
    )


def alignment_exclusion_summary(
    df: pd.DataFrame,
    result: AlignmentResult,
) -> pd.DataFrame:
    """Build a row-level summary of partial boundary days removed."""
    rows = [
        {
            "boundary": "start",
            "original_timestamp": result.original_start,
            "aligned_timestamp": result.aligned_start,
            "rows_excluded": result.start_rows_excluded,
            "operational_days_excluded": result.start_operational_days_excluded,
            "reason": "inicio parcial antes del primer dia operativo completo",
        },
        {
            "boundary": "end",
            "original_timestamp": result.original_end,
            "aligned_timestamp": result.aligned_end,
            "rows_excluded": result.end_rows_excluded,
            "operational_days_excluded": result.end_operational_days_excluded,
            "reason": "ultimo dia operativo parcial excluido",
        },
    ]
    return pd.DataFrame(rows)


def split_alignment_summary(
    df: pd.DataFrame,
    test_weeks: int = 10,
    granularity_min: int = 30,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
) -> pd.DataFrame:
    """Summarize dataset and final-test boundary exclusions."""
    start, end = dataset_bounds(df)
    raw_end_exclusive = end + pd.Timedelta(minutes=int(granularity_min))
    raw_test_start = end - pd.Timedelta(weeks=int(test_weeks))
    dataset_alignment = align_to_full_operational_days(
        df=df,
        start=start,
        end=raw_end_exclusive,
        operational_day_start=operational_day_start,
        granularity_min=granularity_min,
    )
    test_alignment = align_to_full_operational_days(
        df=df,
        start=raw_test_start,
        end=raw_end_exclusive,
        operational_day_start=operational_day_start,
        granularity_min=granularity_min,
    )

    dataset_summary = alignment_exclusion_summary(df, dataset_alignment)
    dataset_summary["scope"] = "dataset_available_range"
    test_summary = alignment_exclusion_summary(df, test_alignment)
    test_summary["scope"] = "final_test_window"
    return pd.concat([dataset_summary, test_summary], ignore_index=True)


def _assert_operational_boundary(
    ts: pd.Timestamp,
    name: str,
    operational_day_start: str | time,
) -> None:
    """Raise when a timestamp is not on the configured operational-day boundary."""
    if pd.Timestamp(ts).time() != parse_operational_day_start(operational_day_start):
        raise ValueError(f"{name} no esta alineado a {operational_day_start}: {ts}")


def validate_full_operational_window(
    start: pd.Timestamp,
    end: pd.Timestamp,
    label: str,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
) -> None:
    """Validate that a half-open window contains complete operational days only."""
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    _assert_operational_boundary(start, f"{label}_start", operational_day_start)
    _assert_operational_boundary(end, f"{label}_end", operational_day_start)
    if end <= start:
        raise ValueError(f"{label} queda vacia despues de alinear")
    if ((end - start) / pd.Timedelta(days=1)) % 1 != 0:
        raise ValueError(f"{label} no contiene un numero entero de dias operativos")


def make_final_test_window(
    df: pd.DataFrame,
    test_weeks: int = 10,
    granularity_min: int = 30,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
    require_full_operational_days: bool = True,
) -> FinalTestWindow:
    """Reserve the last ``test_weeks`` as final temporal holdout."""
    start, end = dataset_bounds(df)
    test_start = end - pd.Timedelta(weeks=int(test_weeks))
    test_end = end + pd.Timedelta(minutes=int(granularity_min))
    if require_full_operational_days:
        dataset_alignment = align_to_full_operational_days(
            df=df,
            start=start,
            end=test_end,
            operational_day_start=operational_day_start,
            granularity_min=granularity_min,
        )
        test_alignment = align_to_full_operational_days(
            df=df,
            start=test_start,
            end=test_end,
            operational_day_start=operational_day_start,
            granularity_min=granularity_min,
        )
        start = dataset_alignment.aligned_start
        test_start = test_alignment.aligned_start
        test_end = test_alignment.aligned_end
        validate_full_operational_window(test_start, test_end, "test", operational_day_start)
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
    granularity_min: int = 30,
    operational_day_start: str | time = DEFAULT_OPERATIONAL_DAY_START,
    require_full_operational_days: bool = True,
) -> list[TemporalFold]:
    """Create expanding-window folds before the final test period."""
    start, end = dataset_bounds(df)
    test_start = end - pd.Timedelta(weeks=int(test_weeks))
    if require_full_operational_days:
        raw_end_exclusive = end + pd.Timedelta(minutes=int(granularity_min))
        dataset_alignment = align_to_full_operational_days(
            df=df,
            start=start,
            end=raw_end_exclusive,
            operational_day_start=operational_day_start,
            granularity_min=granularity_min,
        )
        test_alignment = align_to_full_operational_days(
            df=df,
            start=test_start,
            end=raw_end_exclusive,
            operational_day_start=operational_day_start,
            granularity_min=granularity_min,
        )
        start = dataset_alignment.aligned_start
        test_start = test_alignment.aligned_start
    val_delta = pd.Timedelta(weeks=int(validation_weeks))
    step_delta = pd.Timedelta(weeks=int(step_weeks))
    first_val_start = start + pd.Timedelta(weeks=int(min_train_weeks))
    if require_full_operational_days:
        first_val_start = align_start_to_operational_day(
            first_val_start,
            operational_day_start,
        )

    folds: list[TemporalFold] = []
    val_start = first_val_start
    fold_idx = 1
    while val_start + val_delta <= test_start:
        val_end = val_start + val_delta
        if require_full_operational_days:
            val_start = align_start_to_operational_day(val_start, operational_day_start)
            val_end = align_end_to_operational_day(val_end, operational_day_start)
            validate_full_operational_window(
                val_start,
                val_end,
                f"validation_{fold_idx}",
                operational_day_start,
            )
        folds.append(
            TemporalFold(
                fold=str(fold_idx),
                train_start=start,
                train_end=val_start,
                validation_start=val_start,
                validation_end=val_end,
            )
        )
        val_start = val_start + step_delta
        fold_idx += 1

    if not folds:
        raise ValueError("No se generaron folds; reduzca min_train_weeks o validation_weeks")
    validate_temporal_folds(
        folds, test_start, operational_day_start if require_full_operational_days else None
    )
    return folds


def validate_temporal_folds(
    folds: list[TemporalFold],
    test_start: pd.Timestamp,
    operational_day_start: str | time | None = None,
) -> None:
    """Validate temporal ordering and absence of train/validation leakage."""
    previous_val_end: pd.Timestamp | None = None
    for fold in folds:
        if not (fold.train_start < fold.train_end <= fold.validation_start < fold.validation_end):
            raise ValueError(f"Fold {fold.fold} tiene orden temporal invalido")
        if operational_day_start is not None:
            validate_full_operational_window(
                fold.validation_start,
                fold.validation_end,
                f"validation_{fold.fold}",
                operational_day_start,
            )
            _assert_operational_boundary(fold.train_start, "train_start", operational_day_start)
            _assert_operational_boundary(fold.train_end, "train_end", operational_day_start)
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
