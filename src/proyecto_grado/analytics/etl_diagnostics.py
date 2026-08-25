"""Diagnostics for comparing ETL inputs, intermediate outputs and model-ready data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from proyecto_grado.etl.config import DESPACHOS_CSV, END_PATH, MODEL_READY_DIR, QC_PATH


@dataclass(frozen=True)
class DatasetPaths:
    raw: str = DESPACHOS_CSV
    qc: str = QC_PATH
    end: str = END_PATH
    model_ready: str = str(Path(MODEL_READY_DIR) / "despachos_model_ready.parquet")


def read_dataset(path: str | Path) -> pd.DataFrame | None:
    """Read a CSV/Parquet dataset if it exists; otherwise return None."""
    p = Path(path)
    if not p.exists():
        return None
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p, encoding="utf-8")
    if p.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    raise ValueError(f"Formato no soportado: {p}")


def load_etl_datasets(paths: DatasetPaths | None = None) -> dict[str, pd.DataFrame | None]:
    """Load the standard ETL datasets without failing when one stage is missing."""
    paths = paths or DatasetPaths()
    return {
        "raw": read_dataset(paths.raw),
        "qc": read_dataset(paths.qc),
        "end": read_dataset(paths.end),
        "model_ready": read_dataset(paths.model_ready),
    }


def dataset_overview(datasets: Mapping[str, pd.DataFrame | None]) -> pd.DataFrame:
    """Return row/column counts and availability by ETL stage."""
    rows = []
    labels = {
        "raw": "raw",
        "qc": "quality_checked",
        "end": "trip_end_resolved",
        "model_ready": "model_ready",
    }
    for name in ["raw", "qc", "end", "model_ready"]:
        df = datasets.get(name)
        rows.append(
            {
                "stage": labels[name],
                "available": df is not None,
                "rows": 0 if df is None else len(df),
                "columns": 0 if df is None else int(df.shape[1]),
            }
        )
    return pd.DataFrame(rows)


def retention_summary(datasets: Mapping[str, pd.DataFrame | None]) -> pd.DataFrame:
    """Summarize row retention from raw data to model-ready data."""
    raw = datasets.get("raw")
    model_ready = datasets.get("model_ready")
    raw_rows = 0 if raw is None else len(raw)
    model_rows = 0 if model_ready is None else len(model_ready)
    dropped = raw_rows - model_rows if raw_rows else None
    pct = float(model_rows / raw_rows * 100.0) if raw_rows else None
    return pd.DataFrame(
        [
            {
                "raw_rows": raw_rows,
                "model_ready_rows": model_rows,
                "rows_difference": dropped,
                "retention_pct": pct,
            }
        ]
    )


def missing_before_after(
    raw_df: pd.DataFrame | None,
    final_df: pd.DataFrame | None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Compare missingness for key operational columns before and after ETL."""
    columns = columns or [
        "PK_INTERVALO_DESPACHO",
        "PLACA",
        "FK_RUTA",
        "HORA_INICIAL_REAL",
        "HORA_FINAL_REAL",
        "PASAJEROS",
        "PASAJEROS_REALES",
        "DISTANCIA",
    ]
    rows = []
    for col in columns:
        row = {"column": col}
        for label, df in [("raw", raw_df), ("final", final_df)]:
            if df is None or col not in df.columns:
                row[f"{label}_missing"] = None
                row[f"{label}_missing_pct"] = None
            else:
                missing = int(df[col].isna().sum())
                row[f"{label}_missing"] = missing
                row[f"{label}_missing_pct"] = float(missing / len(df) * 100.0) if len(df) else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def qc_flag_summary(qc_df: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize quality-control flags produced by the ETL QC stage."""
    if qc_df is None or qc_df.empty:
        return pd.DataFrame(columns=["flag", "count", "pct"])

    flag_cols = [
        c
        for c in qc_df.columns
        if c.startswith("flag_") or c in {"qc_any_flag", "qc_hard_fail", "qc_soft_fail"}
    ]
    rows = []
    for col in flag_cols:
        values = qc_df[col].fillna(False).astype(bool)
        count = int(values.sum())
        rows.append({"flag": col, "count": count, "pct": float(count / len(qc_df) * 100.0)})
    return pd.DataFrame(rows).sort_values(["count", "flag"], ascending=[False, True])


def finalization_summary(df: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize trip-finalization labels after GPS/end-time processing."""
    if df is None or "FIN_TIPO" not in df.columns:
        return pd.DataFrame(columns=["FIN_TIPO", "count", "pct"])
    counts = df["FIN_TIPO"].fillna("SIN_VALOR").astype(str).value_counts(dropna=False)
    out = counts.rename_axis("FIN_TIPO").reset_index(name="count")
    out["pct"] = out["count"].apply(lambda x: float(x / len(df) * 100.0) if len(df) else 0.0)
    return out


def build_etl_diagnostics(
    datasets: Mapping[str, pd.DataFrame | None],
) -> dict[str, pd.DataFrame]:
    """Build the standard post-ETL diagnostic tables."""
    final_df = datasets.get("model_ready")
    if final_df is None:
        final_df = datasets.get("end")
    return {
        "dataset_overview": dataset_overview(datasets),
        "retention_summary": retention_summary(datasets),
        "missing_before_after": missing_before_after(datasets.get("raw"), final_df),
        "qc_flag_summary": qc_flag_summary(datasets.get("qc")),
        "finalization_summary": finalization_summary(datasets.get("end")),
    }
