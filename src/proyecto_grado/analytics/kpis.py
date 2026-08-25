"""Operational KPIs for the Montebello demand-prediction project."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def _pct(part: int | float, total: int | float) -> float | None:
    return float(part / total * 100.0) if total else None


def _as_datetime(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    return pd.to_datetime(df[col], errors="coerce")


def _resolve_pasajeros_col(df: pd.DataFrame, columna_pasajeros: str) -> str | None:
    """Resuelve la columna de pasajeros a usar, con fallback al conteo crudo.

    ``PASAJEROS`` es el conteo crudo del dispositivo APC, inflado por eventos
    de puerta (ver etl/transforms.py::run_block4); ``PASAJEROS_REALES`` es la
    version corregida y la que se prefiere. El fallback a ``PASAJEROS``
    sostiene compatibilidad con snapshots anteriores a la correccion.
    """
    if columna_pasajeros in df.columns:
        return columna_pasajeros
    if "PASAJEROS" in df.columns:
        return "PASAJEROS"
    return None


def operational_kpis(
    datasets: Mapping[str, pd.DataFrame | None],
    columna_pasajeros: str = "PASAJEROS_REALES",
) -> pd.DataFrame:
    """Return thesis-friendly KPIs for ETL quality and operating behavior."""
    raw = datasets.get("raw")
    qc = datasets.get("qc")
    end = datasets.get("end")
    model = datasets.get("model_ready")

    raw_rows = 0 if raw is None else len(raw)
    qc_rows = 0 if qc is None else len(qc)
    end_rows = 0 if end is None else len(end)
    model_rows = 0 if model is None else len(model)

    rows = [
        {"kpi": "despachos_raw", "value": raw_rows, "unit": "rows"},
        {"kpi": "despachos_qc", "value": qc_rows, "unit": "rows"},
        {"kpi": "despachos_end", "value": end_rows, "unit": "rows"},
        {"kpi": "despachos_model_ready", "value": model_rows, "unit": "rows"},
        {"kpi": "retencion_model_ready_pct", "value": _pct(model_rows, raw_rows), "unit": "pct"},
    ]

    if qc is not None and not qc.empty:
        for col in ["qc_hard_fail", "qc_soft_fail", "qc_any_flag"]:
            if col in qc.columns:
                count = int(qc[col].fillna(False).astype(bool).sum())
                rows.append({"kpi": col, "value": count, "unit": "rows"})
                rows.append({"kpi": f"{col}_pct", "value": _pct(count, len(qc)), "unit": "pct"})

    final_df = model if model is not None else end
    if final_df is not None and not final_df.empty:
        pax_col = _resolve_pasajeros_col(final_df, columna_pasajeros)
        if pax_col is not None:
            pasajeros = pd.to_numeric(final_df[pax_col], errors="coerce")
            rows.extend(
                [
                    {
                        "kpi": "pasajeros_total",
                        "value": float(pasajeros.sum()),
                        "unit": "passengers",
                    },
                    {
                        "kpi": "pasajeros_promedio",
                        "value": float(pasajeros.mean()),
                        "unit": "passengers",
                    },
                ]
            )
        if "DURACION_MIN_FINAL" in final_df.columns:
            dur = pd.to_numeric(final_df["DURACION_MIN_FINAL"], errors="coerce")
            rows.extend(
                [
                    {"kpi": "duracion_promedio_min", "value": float(dur.mean()), "unit": "minutes"},
                    {
                        "kpi": "duracion_p95_min",
                        "value": float(dur.quantile(0.95)),
                        "unit": "minutes",
                    },
                ]
            )

    if end is not None and not end.empty and "RECORRIDO_COMPLETO" in end.columns:
        completos = int(pd.to_numeric(end["RECORRIDO_COMPLETO"], errors="coerce").fillna(0).sum())
        rows.append({"kpi": "recorridos_completos", "value": completos, "unit": "rows"})
        rows.append(
            {"kpi": "recorridos_completos_pct", "value": _pct(completos, len(end)), "unit": "pct"}
        )

    return pd.DataFrame(rows)


def demand_by_route(
    df: pd.DataFrame | None, columna_pasajeros: str = "PASAJEROS_REALES"
) -> pd.DataFrame:
    """Aggregate passenger demand by route."""
    if df is None or df.empty or "FK_RUTA" not in df.columns:
        return pd.DataFrame(
            columns=["FK_RUTA", "despachos", "pasajeros_total", "pasajeros_promedio"]
        )
    out = df.copy()
    pax_col = _resolve_pasajeros_col(out, columna_pasajeros)
    out["PASAJEROS"] = pd.to_numeric(out.get(pax_col), errors="coerce")
    return (
        out.groupby("FK_RUTA", dropna=False)
        .agg(
            despachos=("FK_RUTA", "size"),
            pasajeros_total=("PASAJEROS", "sum"),
            pasajeros_promedio=("PASAJEROS", "mean"),
        )
        .reset_index()
        .sort_values("FK_RUTA")
    )


def demand_by_hour_weekday(
    df: pd.DataFrame | None, columna_pasajeros: str = "PASAJEROS_REALES"
) -> pd.DataFrame:
    """Aggregate passenger demand by weekday and hour."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["dia_semana", "hora", "despachos", "pasajeros_total"])
    out = df.copy()
    if "HORA_INICIAL_REAL" in out.columns:
        ts = _as_datetime(out, "HORA_INICIAL_REAL")
        out["dia_semana"] = ts.dt.dayofweek
        out["hora"] = ts.dt.hour
    elif {"DIA_SEMANA", "HORA_INICIO_H"}.issubset(out.columns):
        out["dia_semana"] = out["DIA_SEMANA"]
        out["hora"] = out["HORA_INICIO_H"]
    else:
        return pd.DataFrame(columns=["dia_semana", "hora", "despachos", "pasajeros_total"])

    pax_col = _resolve_pasajeros_col(out, columna_pasajeros)
    out["PASAJEROS"] = pd.to_numeric(out.get(pax_col), errors="coerce")
    return (
        out.dropna(subset=["dia_semana", "hora"])
        .groupby(["dia_semana", "hora"], dropna=False)
        .agg(despachos=("hora", "size"), pasajeros_total=("PASAJEROS", "sum"))
        .reset_index()
        .sort_values(["dia_semana", "hora"])
    )


def duration_by_route(df: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize final trip duration by route."""
    if (
        df is None
        or df.empty
        or "FK_RUTA" not in df.columns
        or "DURACION_MIN_FINAL" not in df.columns
    ):
        return pd.DataFrame(columns=["FK_RUTA", "count", "mean", "median", "p95"])
    out = df.copy()
    out["DURACION_MIN_FINAL"] = pd.to_numeric(out["DURACION_MIN_FINAL"], errors="coerce")
    grouped = out.groupby("FK_RUTA", dropna=False)["DURACION_MIN_FINAL"]
    return grouped.agg(
        count="count", mean="mean", median="median", p95=lambda s: s.quantile(0.95)
    ).reset_index()


def build_kpi_tables(datasets: Mapping[str, pd.DataFrame | None]) -> dict[str, pd.DataFrame]:
    """Build all KPI tables from loaded ETL datasets."""
    final_df = datasets.get("model_ready")
    if final_df is None:
        final_df = datasets.get("end")
    return {
        "operational_kpis": operational_kpis(datasets),
        "demand_by_route": demand_by_route(final_df),
        "demand_by_hour_weekday": demand_by_hour_weekday(final_df),
        "duration_by_route": duration_by_route(final_df),
    }
