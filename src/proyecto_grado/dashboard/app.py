"""Streamlit dashboard for the Montebello demand prediction thesis project."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import altair as alt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib.ticker import FuncFormatter, MaxNLocator

from proyecto_grado.analytics.etl_diagnostics import (
    DatasetPaths,
    build_etl_diagnostics,
    load_etl_datasets,
)
from proyecto_grado.analytics.kpis import build_kpi_tables
from proyecto_grado.analytics.plots import PALETTE
from proyecto_grado.etl.config import PROJECT_ROOT

APP_TITLE = "Dashboard Montebello"
EDA_DIR = PROJECT_ROOT / "data" / "processed" / "eda"
EDA_FIGURES_DIR = PROJECT_ROOT / "reports" / "figures" / "eda"
EDA_SUMMARY_PATH = PROJECT_ROOT / "reports" / "tables" / "eda" / "temporal_executive_summary.txt"
WEEKDAY_LABELS = {
    0: "Lun",
    1: "Mar",
    2: "Mie",
    3: "Jue",
    4: "Vie",
    5: "Sab",
    6: "Dom",
}
DATASET_LABELS = {
    "raw": "Despachos raw",
    "qc": "Control de calidad",
    "end": "Fin de recorrido",
    "model_ready": "Model-ready",
}
TIME_SERIES_DIR = PROJECT_ROOT / "data" / "processed" / "time_series"
TIME_SERIES_SUMMARY_PATH = PROJECT_ROOT / "reports" / "tables" / "time_series_summary.csv"
OPERATIONAL_HOURS_PATH = PROJECT_ROOT / "data" / "processed" / "operational_hours.parquet"
OPERATIONAL_HOURS_SUMMARY_PATH = (
    PROJECT_ROOT / "reports" / "tables" / "operational_hours_summary.csv"
)
TIME_SERIES_METRIC_LABELS = {
    "pasajeros_total": "Pasajeros totales",
    "despachos_count": "Despachos",
    "pasajeros_promedio": "Pasajeros promedio",
    "ocupacion_p95": "Ocupacion p95",
}
GAP_TYPE_LABELS = {
    "operativo": "Operativo",
    "gap_anomalo": "Gap anomalo",
    "fuera_operacion": "Fuera de operacion",
}
DAY_TYPE_ORDER = ["LABORAL", "SABADO", "DOMINGO", "FESTIVO", "FESTIVO_PUENTE"]
_TS_FILE_PATTERN = re.compile(r"ts_ruta(\d+)_g(\d+)min")
_EDA_COMBO_PATTERN = re.compile(
    r"(?:perfil_intraday|perfil_semanal|autocorr|atipicos)_(\d+)_g(\d+)min"
)
_ROLLING_DEFAULTS: dict[int, tuple[int, int]] = {
    15: (96, 288),
    30: (48, 144),
    60: (24, 72),
}


def _format_number(value: object, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    number = float(value)
    if decimals:
        return f"{number:,.{decimals}f}"
    return f"{number:,.0f}"


def _format_percent(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):,.2f}%"


def _format_file_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _sample_for_chart(df: pd.DataFrame, max_rows: int = 8000) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    step = max(1, len(df) // max_rows)
    return df.iloc[::step].copy()


def _metric_value(kpis: pd.DataFrame, name: str) -> object:
    if kpis.empty or "kpi" not in kpis.columns:
        return None
    values = kpis.loc[kpis["kpi"] == name, "value"]
    return values.iloc[0] if not values.empty else None


def _show_missing_dataset_warnings(datasets: dict[str, pd.DataFrame | None]) -> None:
    for key, label in DATASET_LABELS.items():
        if datasets.get(key) is None:
            st.warning(f"Etapa {label} aun no ejecutada")


def _style_available(df: pd.DataFrame):
    return df.style.map(
        lambda value: (
            "background-color: #d8f3dc; color: #1b4332"
            if bool(value)
            else "background-color: #ffe5e5; color: #7f1d1d"
        ),
        subset=["available"],
    )


def _style_missing(df: pd.DataFrame):
    pct_cols = [col for col in df.columns if col.endswith("_pct")]
    if not pct_cols:
        return df
    return df.style.background_gradient(subset=pct_cols, cmap="Oranges", vmin=0, vmax=100)


def _style_minutes(df: pd.DataFrame):
    minute_cols = [col for col in ["mean", "median", "p95"] if col in df.columns]
    if not minute_cols:
        return df
    return df.style.format(dict.fromkeys(minute_cols, "{:,.2f}")).background_gradient(
        subset=minute_cols,
        cmap="Blues",
    )


def _style_outliers(df: pd.DataFrame):
    if df.empty or "tipo_atipico" not in df.columns:
        return df
    return df.style.map(
        lambda value: (
            "background-color: #ffe2e2; color: #7f1d1d"
            if value == "alto"
            else "background-color: #dbeafe; color: #1e3a8a"
            if value == "bajo"
            else ""
        ),
        subset=["tipo_atipico"],
    )


def _style_ts_summary(df: pd.DataFrame):
    styler = df.style
    if "pct_gaps" in df.columns:
        styler = styler.background_gradient(subset=["pct_gaps"], cmap="Oranges", vmin=0, vmax=100)
    if "valida" in df.columns:
        styler = styler.map(
            lambda value: (
                "background-color: #d8f3dc; color: #1b4332"
                if bool(value)
                else "background-color: #ffe5e5; color: #7f1d1d"
            ),
            subset=["valida"],
        )
    return styler


def _style_operational_hours(df: pd.DataFrame):
    styler = df.style
    if "pct_cobertura_dentro_horario" in df.columns:
        styler = styler.background_gradient(
            subset=["pct_cobertura_dentro_horario"],
            cmap="Greens",
            vmin=0,
            vmax=1,
        )
    if "franjas_anomalas_count" in df.columns:
        styler = styler.background_gradient(subset=["franjas_anomalas_count"], cmap="Oranges")
    if "fallback_laboral" in df.columns:
        styler = styler.map(
            lambda value: ("background-color: #fff4cc; color: #78350f" if bool(value) else ""),
            subset=["fallback_laboral"],
        )
    return styler


def _apply_chart_theme() -> None:
    sns.set_theme(
        context="paper",
        style="whitegrid",
        font="DejaVu Sans",
        rc={
            "figure.dpi": 120,
            "axes.edgecolor": "#2f3437",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#d9dee3",
            "grid.linewidth": 0.7,
        },
    )


def _compact_axis_number(value, _position=None) -> str:
    if pd.isna(value):
        return ""
    number = float(value)
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.0f}k"
    return f"{number:.0f}"


def _render_figure(fig) -> None:
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


@st.cache_data(ttl=300, show_spinner="Cargando datasets ETL...")
def load_dashboard_data() -> tuple[
    dict[str, pd.DataFrame | None],
    dict[str, pd.DataFrame],
    dict[str, pd.DataFrame],
]:
    datasets = load_etl_datasets()
    diagnostics = build_etl_diagnostics(datasets)
    kpi_tables = build_kpi_tables(datasets)
    return datasets, diagnostics, kpi_tables


@st.cache_data(ttl=300)
def get_model_ready_mtime(path: str) -> str:
    dataset_path = Path(path)
    if not dataset_path.exists():
        return "Dataset model-ready no disponible"
    modified = datetime.fromtimestamp(dataset_path.stat().st_mtime)
    return modified.strftime("%Y-%m-%d %H:%M:%S")


@st.cache_data(ttl=300)
def get_generated_files() -> pd.DataFrame:
    roots = [PROJECT_ROOT / "data" / "processed", PROJECT_ROOT / "reports"]
    rows = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in {".csv", ".json", ".parquet", ".png", ".txt"}:
                continue
            stat = path.stat()
            rows.append(
                {
                    "archivo": str(path.relative_to(PROJECT_ROOT)),
                    "tipo": path.suffix.lower().lstrip("."),
                    "tamano": _format_file_size(stat.st_size),
                    "modificado": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner="Cargando series temporales...")
def load_time_series_outputs() -> tuple[dict[tuple[int, int], pd.DataFrame], pd.DataFrame]:
    summary = (
        pd.read_csv(TIME_SERIES_SUMMARY_PATH, encoding="utf-8")
        if TIME_SERIES_SUMMARY_PATH.exists()
        else pd.DataFrame()
    )
    outputs: dict[tuple[int, int], pd.DataFrame] = {}
    if not TIME_SERIES_DIR.exists():
        return outputs, summary

    for path in sorted(TIME_SERIES_DIR.glob("ts_ruta*_g*min.parquet")):
        m = _TS_FILE_PATTERN.match(path.stem)
        if not m:
            continue
        route, gran = int(m.group(1)), int(m.group(2))
        df = pd.read_parquet(path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if "FK_RUTA" not in df.columns:
            df["FK_RUTA"] = route
        outputs[(route, gran)] = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    return outputs, summary


@st.cache_data(ttl=300, show_spinner="Cargando horarios operativos...")
def load_operational_hours_outputs() -> pd.DataFrame:
    if OPERATIONAL_HOURS_PATH.exists():
        return pd.read_parquet(OPERATIONAL_HOURS_PATH)
    if OPERATIONAL_HOURS_SUMMARY_PATH.exists():
        return pd.read_csv(OPERATIONAL_HOURS_SUMMARY_PATH, encoding="utf-8")
    return pd.DataFrame()


@st.cache_data(ttl=300)
def get_recent_log_text() -> str:
    candidates = []
    for root in [PROJECT_ROOT / "reports", PROJECT_ROOT / "logs", PROJECT_ROOT]:
        if root.exists():
            candidates.extend(root.glob("**/*.log"))
    if not candidates:
        return ""
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return latest.read_text(encoding="utf-8", errors="replace")[-200:]


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --montebello-primary: {PALETTE["primary"]};
            --montebello-secondary: {PALETTE["secondary"]};
            --montebello-accent: {PALETTE["accent"]};
        }}
        .block-container {{
            padding-top: 1.4rem;
        }}
        h1, h2, h3 {{
            color: #1f2933;
        }}
        [data-testid="stMetric"] {{
            border-left: 4px solid var(--montebello-primary);
            background: #f8fafc;
            padding: 0.7rem 0.85rem;
            border-radius: 8px;
        }}
        [data-testid="stSidebar"] hr {{
            margin: 1rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    st.session_state.setdefault("pipeline_process", None)
    st.session_state.setdefault("pipeline_logs", [])
    st.session_state.setdefault("pipeline_running", False)
    st.session_state.setdefault("pipeline_returncode", None)


def render_sidebar() -> str:
    st.sidebar.markdown("### 🚌 Montebello ETL")
    st.sidebar.caption("Prediccion de demanda de pasajeros - UAO")
    st.sidebar.divider()
    if st.sidebar.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.divider()
    return st.sidebar.radio(
        "Navegacion",
        [
            "Resumen General",
            "Diagnostico ETL",
            "KPIs Operacionales",
            "Series Temporales",
            "EDA Temporal",
            "Pipeline & Logs",
        ],
    )


def plot_row_counts_inline(dataset_overview: pd.DataFrame) -> None:
    if dataset_overview.empty:
        st.warning("Etapa dataset_overview aun no ejecutada")
        return
    _apply_chart_theme()
    data = dataset_overview.copy()
    data["stage_label"] = data["stage"].replace(
        {
            "raw": "Crudo",
            "quality_checked": "QC",
            "trip_end_resolved": "Fin resuelto",
            "model_ready": "Model-ready",
        }
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    sns.barplot(data=data, x="stage_label", y="rows", color=PALETTE["primary"], ax=ax)
    ax.set_title("Registros conservados por etapa del ETL")
    ax.set_xlabel("Etapa")
    ax.set_ylabel("Filas")
    ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.margins(y=0.15)
    _render_figure(fig)


def plot_qc_flags_inline(qc_flag_summary: pd.DataFrame) -> None:
    if qc_flag_summary.empty:
        st.warning("Etapa Control de calidad aun no ejecutada")
        return
    _apply_chart_theme()
    data = qc_flag_summary.head(12).sort_values("count", ascending=True)
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    sns.barplot(data=data, x="count", y="flag", color=PALETTE["accent"], ax=ax)
    ax.set_title("Principales alertas de calidad del ETL")
    ax.set_xlabel("Registros")
    ax.set_ylabel("")
    ax.xaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.margins(x=0.12)
    _render_figure(fig)


def plot_finalization_pie(finalization_summary: pd.DataFrame) -> None:
    if finalization_summary.empty:
        st.warning("Etapa Fin de recorrido aun no ejecutada")
        return
    _apply_chart_theme()
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    colors = [PALETTE["primary"], PALETTE["secondary"], PALETTE["accent"], "#6b7280", "#9ca3af"]
    ax.pie(
        finalization_summary["count"],
        labels=finalization_summary["FIN_TIPO"],
        autopct="%1.1f%%",
        startangle=90,
        colors=colors[: len(finalization_summary)],
        textprops={"fontsize": 9},
    )
    ax.set_title("Clasificacion de fin de recorrido")
    ax.axis("equal")
    _render_figure(fig)


def plot_demand_by_route_inline(demand_by_route: pd.DataFrame, metric: str) -> None:
    if demand_by_route.empty:
        st.warning("Etapa Model-ready aun no ejecutada")
        return
    _apply_chart_theme()
    data = demand_by_route.copy()
    data["ruta"] = data["FK_RUTA"].astype(str)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    color = PALETTE["secondary"] if metric == "pasajeros_total" else PALETTE["primary"]
    sns.barplot(data=data, x="ruta", y=metric, color=color, ax=ax)
    ax.set_title("Demanda por ruta")
    ax.set_xlabel("Ruta")
    ax.set_ylabel("Pasajeros" if metric == "pasajeros_total" else "Pasajeros/despacho")
    ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.margins(y=0.15)
    _render_figure(fig)


def plot_hour_weekday_heatmap_inline(demand_by_hour_weekday: pd.DataFrame) -> None:
    if demand_by_hour_weekday.empty:
        st.warning("Etapa Model-ready aun no ejecutada")
        return
    _apply_chart_theme()
    pivot = demand_by_hour_weekday.pivot_table(
        index="dia_semana",
        columns="hora",
        values="pasajeros_total",
        aggfunc="sum",
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0)
    pivot.index = [WEEKDAY_LABELS.get(int(index), str(index)) for index in pivot.index]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    sns.heatmap(
        pivot,
        cmap="YlGnBu",
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": "Pasajeros", "format": FuncFormatter(_compact_axis_number)},
    )
    ax.set_title("Distribucion horaria de la demanda por dia")
    ax.set_xlabel("Hora de inicio")
    ax.set_ylabel("Dia de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _render_figure(fig)


def _ensure_time_context(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    ts = pd.to_datetime(data["timestamp"], errors="coerce")
    data["timestamp"] = ts
    if "hora_del_dia" not in data.columns:
        data["hora_del_dia"] = ts.dt.hour
    if "dia_semana" not in data.columns:
        data["dia_semana"] = ts.dt.dayofweek
    if "fecha" not in data.columns:
        data["fecha"] = ts.dt.date
    return data


def detect_contextual_outliers(
    df: pd.DataFrame,
    metric: str,
    iqr_multiplier: float,
) -> pd.DataFrame:
    data = _ensure_time_context(df)
    data[metric] = pd.to_numeric(data[metric], errors="coerce")
    context_cols = ["dia_semana", "hora_del_dia"]
    grouped = data.groupby(context_cols, dropna=False)[metric]

    data["contexto_n"] = grouped.transform("count")
    data["mediana_contexto"] = grouped.transform("median")
    data["q1_contexto"] = grouped.transform(lambda series: series.quantile(0.25))
    data["q3_contexto"] = grouped.transform(lambda series: series.quantile(0.75))
    data["iqr_contexto"] = data["q3_contexto"] - data["q1_contexto"]
    data["limite_inferior"] = (data["q1_contexto"] - iqr_multiplier * data["iqr_contexto"]).clip(
        lower=0
    )
    data["limite_superior"] = data["q3_contexto"] + iqr_multiplier * data["iqr_contexto"]

    eligible = data["contexto_n"].ge(8) & data["iqr_contexto"].gt(0) & data[metric].notna()
    data["atipico_alto"] = eligible & data[metric].gt(data["limite_superior"])
    data["atipico_bajo"] = eligible & data[metric].lt(data["limite_inferior"])
    data["tipo_atipico"] = ""
    data.loc[data["atipico_alto"], "tipo_atipico"] = "alto"
    data.loc[data["atipico_bajo"], "tipo_atipico"] = "bajo"
    data["desviacion_vs_mediana"] = data[metric] - data["mediana_contexto"]
    data["ratio_vs_mediana"] = data[metric] / data["mediana_contexto"].where(
        data["mediana_contexto"].ne(0)
    )
    return data


def build_time_series_insights(
    df: pd.DataFrame, metric: str, outliers: pd.DataFrame
) -> pd.DataFrame:
    data = _ensure_time_context(df)
    data[metric] = pd.to_numeric(data[metric], errors="coerce")
    rows = []

    if not data.empty:
        metric_values = data[metric].dropna()
        if not metric_values.empty:
            peak_row = data.loc[metric_values.idxmax()]
            rows.append(
                {
                    "hallazgo": "Mayor valor por franja",
                    "detalle": str(peak_row["timestamp"]),
                    "valor": float(peak_row[metric]),
                }
            )

        daily = data.groupby("fecha", dropna=False)[metric].sum().sort_values(ascending=False)
        if not daily.empty:
            rows.append(
                {
                    "hallazgo": "Dia con mayor demanda acumulada",
                    "detalle": str(daily.index[0]),
                    "valor": float(daily.iloc[0]),
                }
            )

        hourly = (
            data.groupby(["dia_semana", "hora_del_dia"], dropna=False)[metric]
            .mean()
            .sort_values(ascending=False)
        )
        if not hourly.empty:
            day, hour = hourly.index[0]
            rows.append(
                {
                    "hallazgo": "Contexto horario mas fuerte",
                    "detalle": f"{WEEKDAY_LABELS.get(int(day), day)} {int(hour):02d}:00",
                    "valor": float(hourly.iloc[0]),
                }
            )

        if "is_gap" in data.columns:
            gap_pct = float(data["is_gap"].fillna(False).astype(bool).mean() * 100)
            rows.append(
                {
                    "hallazgo": "Franjas imputadas como gap",
                    "detalle": "Porcentaje sobre la serie filtrada",
                    "valor": gap_pct,
                }
            )

    if not outliers.empty:
        rows.append(
            {
                "hallazgo": "Atipicos detectados",
                "detalle": "Altos y bajos segun IQR por dia/hora",
                "valor": len(outliers),
            }
        )

    return pd.DataFrame(rows)


def plot_time_series_trend_inline(
    df: pd.DataFrame,
    outlier_df: pd.DataFrame,
    metric: str,
    rolling_window: int,
) -> None:
    if df.empty:
        st.warning("No hay datos para el rango seleccionado.")
        return
    data = df.sort_values("timestamp").copy()
    data[metric] = pd.to_numeric(data[metric], errors="coerce")
    data["media_movil"] = data[metric].rolling(rolling_window, min_periods=1).mean()
    metric_label = TIME_SERIES_METRIC_LABELS.get(metric, metric)
    moving_label = f"Media movil ({rolling_window} franjas)"

    context_cols = [
        col
        for col in [
            "FK_RUTA",
            "is_gap",
            "gap_tipo",
            "dentro_horario_operativo",
            "franja_horaria",
            "tipo_dia",
        ]
        if col in data.columns
    ]
    chart_data = _sample_for_chart(data[["timestamp", metric, "media_movil", *context_cols]].copy())
    line_data = chart_data.melt(
        id_vars=["timestamp", *context_cols],
        value_vars=[metric, "media_movil"],
        var_name="serie",
        value_name="valor",
    )
    line_data["serie"] = line_data["serie"].replace(
        {
            metric: metric_label,
            "media_movil": moving_label,
        }
    )

    zoom = alt.selection_interval(bind="scales", encodings=["x"])
    legend_selection = alt.selection_point(fields=["serie"], bind="legend")

    base = alt.Chart(line_data).encode(
        x=alt.X("timestamp:T", title="Fecha"),
        y=alt.Y("valor:Q", title=metric_label),
        color=alt.Color(
            "serie:N",
            scale=alt.Scale(
                domain=[metric_label, moving_label],
                range=[PALETTE["secondary"], PALETTE["primary"]],
            ),
            title="Serie",
        ),
        opacity=alt.condition(legend_selection, alt.value(0.95), alt.value(0.18)),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Fecha"),
            alt.Tooltip("serie:N", title="Serie"),
            alt.Tooltip("valor:Q", title="Valor", format=",.2f"),
            *[
                alt.Tooltip(f"{col}:N", title=title)
                for col, title in [
                    ("FK_RUTA", "Ruta"),
                    ("franja_horaria", "Franja"),
                    ("tipo_dia", "Tipo dia"),
                    ("gap_tipo", "Tipo gap"),
                    ("dentro_horario_operativo", "Dentro horario"),
                    ("is_gap", "Gap"),
                ]
                if col in line_data.columns
            ],
        ],
    )
    lines = base.mark_line(point=False).add_params(legend_selection)

    chart = lines
    if not outlier_df.empty:
        outlier_cols = [
            "timestamp",
            "FK_RUTA",
            metric,
            "tipo_atipico",
            "mediana_contexto",
            "limite_inferior",
            "limite_superior",
            "desviacion_vs_mediana",
            "ratio_vs_mediana",
            "franja_horaria",
            "tipo_dia",
            "gap_tipo",
            "dentro_horario_operativo",
            "is_gap",
        ]
        outlier_chart_data = outlier_df[
            [col for col in outlier_cols if col in outlier_df.columns]
        ].copy()
        outlier_chart_data[metric] = pd.to_numeric(outlier_chart_data[metric], errors="coerce")
        points = (
            alt.Chart(outlier_chart_data)
            .mark_circle(size=58, opacity=0.9, stroke="white", strokeWidth=0.5)
            .encode(
                x=alt.X("timestamp:T", title="Fecha"),
                y=alt.Y(f"{metric}:Q", title=metric_label),
                color=alt.Color(
                    "tipo_atipico:N",
                    scale=alt.Scale(
                        domain=["alto", "bajo"],
                        range=["#b91c1c", "#2563eb"],
                    ),
                    title="Atipico",
                ),
                tooltip=[
                    alt.Tooltip("timestamp:T", title="Fecha"),
                    alt.Tooltip(f"{metric}:Q", title=metric_label, format=",.2f"),
                    alt.Tooltip("tipo_atipico:N", title="Tipo"),
                    alt.Tooltip("mediana_contexto:Q", title="Mediana contexto", format=",.2f"),
                    alt.Tooltip("limite_inferior:Q", title="Limite inferior", format=",.2f"),
                    alt.Tooltip("limite_superior:Q", title="Limite superior", format=",.2f"),
                    alt.Tooltip("desviacion_vs_mediana:Q", title="Desviacion", format=",.2f"),
                    alt.Tooltip("ratio_vs_mediana:Q", title="Ratio", format=",.2f"),
                    *[
                        alt.Tooltip(f"{col}:N", title=title)
                        for col, title in [
                            ("FK_RUTA", "Ruta"),
                            ("franja_horaria", "Franja"),
                            ("tipo_dia", "Tipo dia"),
                            ("gap_tipo", "Tipo gap"),
                            ("dentro_horario_operativo", "Dentro horario"),
                            ("is_gap", "Gap"),
                        ]
                        if col in outlier_chart_data.columns
                    ],
                ],
            )
        )
        chart = chart + points

    chart = (
        chart.add_params(zoom)
        .properties(
            height=520,
            title="Evolucion temporal con atipicos contextuales",
        )
        .configure_axis(
            grid=True,
            gridColor=PALETTE["grid"],
            labelColor="#1f2933",
            titleColor="#1f2933",
        )
        .configure_legend(
            orient="top-left",
            titleColor="#1f2933",
            labelColor="#1f2933",
        )
        .configure_title(
            color="#1f2933",
            fontSize=16,
            anchor="middle",
        )
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)


def plot_time_series_heatmap_inline(df: pd.DataFrame, metric: str, aggfunc: str = "mean") -> None:
    if df.empty:
        st.warning("No hay datos para construir el mapa horario.")
        return
    _apply_chart_theme()
    data = _ensure_time_context(df)
    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora_del_dia",
        values=metric,
        aggfunc=aggfunc,
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0)
    pivot.index = [WEEKDAY_LABELS.get(int(index), str(index)) for index in pivot.index]

    fig, ax = plt.subplots(figsize=(11, 5.2))
    sns.heatmap(
        pivot,
        cmap="YlGnBu",
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={
            "label": TIME_SERIES_METRIC_LABELS.get(metric, metric),
            "format": FuncFormatter(_compact_axis_number),
        },
    )
    ax.set_title("Patron promedio por dia y hora")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Dia de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _render_figure(fig)


def plot_time_series_distribution_inline(df: pd.DataFrame, metric: str) -> None:
    if df.empty:
        st.warning("No hay datos para comparar distribuciones.")
        return
    _apply_chart_theme()
    data = df.copy()
    data[metric] = pd.to_numeric(data[metric], errors="coerce")
    group_col = "franja_horaria" if "franja_horaria" in data.columns else "hora_del_dia"
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    sns.boxplot(
        data=data,
        x=group_col,
        y=metric,
        color=PALETTE["secondary"],
        fliersize=2,
        ax=ax,
    )
    ax.set_title("Distribucion de la demanda por franja")
    ax.set_xlabel("Franja horaria" if group_col == "franja_horaria" else "Hora")
    ax.set_ylabel(TIME_SERIES_METRIC_LABELS.get(metric, metric))
    ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.tick_params(axis="x", rotation=0)
    _render_figure(fig)


def plot_outlier_heatmap_inline(outlier_df: pd.DataFrame) -> None:
    if outlier_df.empty:
        st.info("No se detectaron atipicos con los filtros actuales.")
        return
    _apply_chart_theme()
    data = _ensure_time_context(outlier_df)
    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora_del_dia",
        values="timestamp",
        aggfunc="count",
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0)
    pivot.index = [WEEKDAY_LABELS.get(int(index), str(index)) for index in pivot.index]

    fig, ax = plt.subplots(figsize=(11, 4.8))
    sns.heatmap(
        pivot,
        cmap="Reds",
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": "Atipicos"},
    )
    ax.set_title("Concentracion de atipicos por dia y hora")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Dia de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _render_figure(fig)


def plot_gap_heatmap_inline(df: pd.DataFrame) -> None:
    if df.empty or "is_gap" not in df.columns:
        st.info("La serie no contiene columna is_gap.")
        return
    _apply_chart_theme()
    data = _ensure_time_context(df)
    data["gap"] = data["is_gap"].fillna(False).astype(bool)
    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora_del_dia",
        values="gap",
        aggfunc="mean",
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0) * 100
    pivot.index = [WEEKDAY_LABELS.get(int(index), str(index)) for index in pivot.index]

    fig, ax = plt.subplots(figsize=(11, 4.8))
    sns.heatmap(
        pivot,
        cmap="Oranges",
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": "% gaps"},
        vmin=0,
        vmax=max(1.0, float(pivot.max().max())),
    )
    ax.set_title("Franjas imputadas como gap por dia y hora")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Dia de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _render_figure(fig)


def build_gap_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["gap_tipo", "descripcion", "franjas", "pct"])

    total = len(df)
    if "gap_tipo" in df.columns:
        counts = df["gap_tipo"].fillna("sin_clasificar").astype(str).value_counts()
    elif "is_gap" in df.columns:
        fallback = (
            df["is_gap"]
            .fillna(False)
            .astype(bool)
            .map({True: "gap_sin_horario", False: "operativo"})
        )
        counts = fallback.value_counts()
    else:
        return pd.DataFrame(columns=["gap_tipo", "descripcion", "franjas", "pct"])

    rows = []
    for gap_tipo, count in counts.items():
        rows.append(
            {
                "gap_tipo": gap_tipo,
                "descripcion": GAP_TYPE_LABELS.get(gap_tipo, gap_tipo),
                "franjas": int(count),
                "pct": float(count / total * 100.0) if total else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("franjas", ascending=False)


def plot_gap_type_heatmap_inline(df: pd.DataFrame, gap_type: str) -> None:
    if df.empty or "gap_tipo" not in df.columns:
        plot_gap_heatmap_inline(df)
        return

    _apply_chart_theme()
    data = _ensure_time_context(df)
    data["target_gap"] = data["gap_tipo"].fillna("").astype(str).eq(gap_type)
    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora_del_dia",
        values="target_gap",
        aggfunc="mean",
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0) * 100
    pivot.index = [WEEKDAY_LABELS.get(int(index), str(index)) for index in pivot.index]

    label = GAP_TYPE_LABELS.get(gap_type, gap_type)
    cmap = "Reds" if gap_type == "gap_anomalo" else "Greys"
    fig, ax = plt.subplots(figsize=(11, 4.8))
    sns.heatmap(
        pivot,
        cmap=cmap,
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": f"% {label}"},
        vmin=0,
        vmax=max(1.0, float(pivot.max().max())),
    )
    ax.set_title(f"{label} por dia y hora")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Dia de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _render_figure(fig)


def render_operational_hours_section(
    operational_hours: pd.DataFrame,
    filtered: pd.DataFrame,
    route: int,
    gran: int,
) -> None:
    if operational_hours.empty:
        st.warning("No se encontro la estimacion de horarios operativos.")
        st.code("make estimate-op-hours", language="powershell")
        return

    required = {"ruta", "granularidad_min", "tipo_dia", "hora_inicio_op_min", "hora_fin_op_min"}
    missing = required - set(operational_hours.columns)
    if missing:
        st.warning(f"El resumen de horarios operativos no tiene columnas esperadas: {missing}")
        return

    op = operational_hours[
        (operational_hours["ruta"] == route) & (operational_hours["granularidad_min"] == gran)
    ].copy()
    if op.empty:
        st.info(
            "No hay horario operativo calculado para esta ruta y granularidad. "
            "Ejecuta `make estimate-op-hours` despues de construir las series."
        )
        return

    valid = op[op["hora_inicio_op_min"].ge(0) & op["hora_fin_op_min"].ge(0)].copy()
    if valid.empty:
        st.warning("La estimacion existe, pero no produjo rangos operativos validos.")
        st.dataframe(op, use_container_width=True, hide_index=True)
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("Tipos de dia", _format_number(valid["tipo_dia"].nunique()))
    metric_cols[1].metric(
        "Duracion promedio",
        f"{valid['duracion_operativa_h'].mean():.1f} h"
        if "duracion_operativa_h" in valid.columns
        else "N/D",
    )
    metric_cols[2].metric(
        "Franjas anomalas",
        _format_number(valid.get("franjas_anomalas_count", pd.Series(dtype=float)).sum()),
    )
    metric_cols[3].metric(
        "Fallback laboral",
        _format_number(
            valid.get("fallback_laboral", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()
        ),
    )

    chart_df = valid.copy()
    base_time = pd.Timestamp("2000-01-01")
    chart_df["inicio_dt"] = base_time + pd.to_timedelta(chart_df["hora_inicio_op_min"], unit="m")
    chart_df["fin_dt"] = base_time + pd.to_timedelta(
        chart_df["hora_fin_op_min"] + chart_df["granularidad_min"],
        unit="m",
    )
    chart_df["medio_dt"] = chart_df["inicio_dt"] + (chart_df["fin_dt"] - chart_df["inicio_dt"]) / 2
    chart_df["rango"] = chart_df["hora_inicio_op"] + " - " + chart_df["hora_fin_op"]
    chart_df["tipo_dia"] = pd.Categorical(
        chart_df["tipo_dia"],
        categories=DAY_TYPE_ORDER,
        ordered=True,
    )
    chart_df = chart_df.sort_values("tipo_dia")

    bars = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadius=4, height=22)
        .encode(
            x=alt.X("inicio_dt:T", title="Hora del dia", axis=alt.Axis(format="%H:%M")),
            x2="fin_dt:T",
            y=alt.Y("tipo_dia:N", title="Tipo de dia", sort=DAY_TYPE_ORDER),
            color=alt.Color("tipo_dia:N", title="Tipo de dia", legend=None),
            tooltip=[
                alt.Tooltip("tipo_dia:N", title="Tipo de dia"),
                alt.Tooltip("rango:N", title="Horario operativo"),
                alt.Tooltip("duracion_operativa_h:Q", title="Duracion h", format=",.2f"),
                alt.Tooltip("n_dias_muestra:Q", title="Dias muestra"),
                alt.Tooltip("n_dias_usado:Q", title="Dias usados"),
                alt.Tooltip("franjas_anomalas_count:Q", title="Franjas anomalas"),
                alt.Tooltip(
                    "pct_cobertura_dentro_horario:Q",
                    title="Cobertura interna",
                    format=".1%",
                ),
                alt.Tooltip("fallback_laboral:N", title="Fallback laboral"),
            ],
        )
        .properties(height=max(210, len(chart_df) * 42), title="Horario operativo estimado")
        .interactive()
    )
    labels = (
        alt.Chart(chart_df)
        .mark_text(align="center", baseline="middle", color="white", fontSize=12)
        .encode(
            x=alt.X("medio_dt:T", axis=alt.Axis(format="%H:%M")),
            y=alt.Y("tipo_dia:N", sort=DAY_TYPE_ORDER),
            text="rango:N",
        )
    )
    st.altair_chart((bars + labels).configure_title(anchor="middle"), use_container_width=True)

    st.dataframe(_style_operational_hours(op), use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar horarios operativos CSV",
        data=_df_to_csv(op),
        file_name=f"operational_hours_ruta{route}_g{gran}min.csv",
        mime="text/csv",
    )

    gap_summary = build_gap_type_summary(filtered)
    if not gap_summary.empty:
        st.subheader("Clasificacion de franjas segun horario operativo")
        st.dataframe(gap_summary, use_container_width=True, hide_index=True)


def plot_granularity_comparison_inline(
    series_by_combo: dict[tuple[int, int], pd.DataFrame],
    route: int,
    grans: list[int],
    metric: str,
    start_date: date,
    end_date: date,
) -> None:
    """Muestra tabla y barras comparativas de las granularidades disponibles para la ruta."""
    if not grans:
        st.info("No hay granularidades disponibles para comparar.")
        return

    metric_label = TIME_SERIES_METRIC_LABELS.get(metric, metric)
    rows = []
    for gran in grans:
        key = (route, gran)
        if key not in series_by_combo:
            continue
        sliced = series_by_combo[key].copy()
        mask = sliced["timestamp"].dt.date.between(start_date, end_date)
        sliced = sliced.loc[mask]
        n_franjas = len(sliced)
        n_gaps = (
            int(sliced["is_gap"].fillna(False).astype(bool).sum())
            if "is_gap" in sliced.columns
            else 0
        )
        pct_gaps = round(100.0 * n_gaps / n_franjas, 1) if n_franjas > 0 else 0.0
        metric_values = pd.to_numeric(sliced[metric], errors="coerce")
        metric_agg = (
            float(metric_values.sum())
            if metric in {"pasajeros_total", "despachos_count"}
            else float(metric_values.mean())
        )
        rows.append(
            {
                "granularidad": f"{gran} min",
                "n_franjas": n_franjas,
                "n_gaps": n_gaps,
                "pct_gaps (%)": pct_gaps,
                metric_label: round(metric_agg, 2),
            }
        )

    comp = pd.DataFrame(rows)
    if comp.empty:
        st.info("Sin datos para el rango seleccionado.")
        return

    st.subheader(f"Comparacion entre granularidades — Ruta {route}")
    st.caption(
        "Misma ruta y rango de fechas; solo cambia la resolucion temporal. "
        "La metrica de pasajeros es identica porque el total no depende del bin."
    )
    st.dataframe(comp, use_container_width=True, hide_index=True)

    _apply_chart_theme()
    bar_cols = ["n_franjas", "pct_gaps (%)", metric_label]
    bar_colors = [PALETTE["primary"], PALETTE["accent"], PALETTE["secondary"]]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, col, color in zip(axes, bar_cols, bar_colors, strict=True):
        sns.barplot(data=comp, x="granularidad", y=col, color=color, ax=ax)
        ax.set_title(col)
        ax.set_xlabel("Granularidad")
        ax.set_ylabel("")
        ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.margins(y=0.18)
    fig.suptitle(f"Ruta {route} — impacto de la granularidad", fontsize=11, y=1.01)
    fig.tight_layout()
    _render_figure(fig)


def render_summary_page(
    datasets: dict[str, pd.DataFrame | None],
    diagnostics: dict[str, pd.DataFrame],
    kpi_tables: dict[str, pd.DataFrame],
) -> None:
    model_ready_mtime = get_model_ready_mtime(DatasetPaths().model_ready)
    kpis = kpi_tables.get("operational_kpis", pd.DataFrame())

    st.title("Prediccion de demanda de pasajeros - Empresa Montebello")
    st.caption(f"Ultima actualizacion dataset model-ready: {model_ready_mtime}")
    _show_missing_dataset_warnings(datasets)

    row_1 = st.columns(4)
    row_1[0].metric("Despachos raw", _format_number(_metric_value(kpis, "despachos_raw")))
    row_1[1].metric("Despachos QC", _format_number(_metric_value(kpis, "despachos_qc")))
    row_1[2].metric(
        "Despachos model-ready",
        _format_number(_metric_value(kpis, "despachos_model_ready")),
    )
    row_1[3].metric("Retencion", _format_percent(_metric_value(kpis, "retencion_model_ready_pct")))

    row_2 = st.columns(4)
    row_2[0].metric("Pasajeros totales", _format_number(_metric_value(kpis, "pasajeros_total")))
    row_2[1].metric(
        "Pasajeros promedio/despacho",
        _format_number(_metric_value(kpis, "pasajeros_promedio"), decimals=2),
    )
    row_2[2].metric(
        "Duracion promedio (min)",
        _format_number(_metric_value(kpis, "duracion_promedio_min"), decimals=2),
    )
    row_2[3].metric(
        "Recorridos completos",
        _format_percent(_metric_value(kpis, "recorridos_completos_pct")),
    )

    with st.expander("Estado del pipeline", expanded=True):
        overview = diagnostics.get("dataset_overview", pd.DataFrame())
        st.dataframe(_style_available(overview), use_container_width=True, hide_index=True)


def render_diagnostics_page(diagnostics: dict[str, pd.DataFrame]) -> None:
    st.title("Diagnostico ETL")

    chart_cols = st.columns(2)
    with chart_cols[0]:
        plot_row_counts_inline(diagnostics.get("dataset_overview", pd.DataFrame()))
    with chart_cols[1]:
        plot_qc_flags_inline(diagnostics.get("qc_flag_summary", pd.DataFrame()))

    st.subheader("Nulos antes y despues")
    missing = diagnostics.get("missing_before_after", pd.DataFrame())
    st.dataframe(_style_missing(missing), use_container_width=True, hide_index=True)

    final_cols = st.columns([1.2, 0.8])
    finalization = diagnostics.get("finalization_summary", pd.DataFrame())
    with final_cols[0]:
        st.subheader("Resumen de finalizacion")
        st.dataframe(finalization, use_container_width=True, hide_index=True)
    with final_cols[1]:
        plot_finalization_pie(finalization)

    st.subheader("Retencion")
    st.dataframe(
        diagnostics.get("retention_summary", pd.DataFrame()),
        use_container_width=True,
        hide_index=True,
    )


def render_kpis_page(kpi_tables: dict[str, pd.DataFrame]) -> None:
    st.title("KPIs Operacionales")

    demand_route = kpi_tables.get("demand_by_route", pd.DataFrame())
    metric = st.radio(
        "Metrica de demanda por ruta",
        ["pasajeros_total", "pasajeros_promedio"],
        horizontal=True,
    )
    plot_demand_by_route_inline(demand_route, metric)
    st.download_button(
        "Descargar demanda por ruta CSV",
        data=_df_to_csv(demand_route),
        file_name="demand_by_route.csv",
        mime="text/csv",
    )

    st.subheader("Demanda por dia y hora")
    demand_hour = kpi_tables.get("demand_by_hour_weekday", pd.DataFrame())
    plot_hour_weekday_heatmap_inline(demand_hour)
    st.download_button(
        "Descargar demanda por dia y hora CSV",
        data=_df_to_csv(demand_hour),
        file_name="demand_by_hour_weekday.csv",
        mime="text/csv",
    )

    st.subheader("Duracion por ruta")
    duration = kpi_tables.get("duration_by_route", pd.DataFrame())
    st.dataframe(_style_minutes(duration), use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar duracion por ruta CSV",
        data=_df_to_csv(duration),
        file_name="duration_by_route.csv",
        mime="text/csv",
    )

    st.subheader("KPIs base")
    operational = kpi_tables.get("operational_kpis", pd.DataFrame())
    st.dataframe(operational, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar KPIs CSV",
        data=_df_to_csv(operational),
        file_name="operational_kpis.csv",
        mime="text/csv",
    )


def render_time_series_page() -> None:
    st.title("Series temporales")
    series_by_combo, summary = load_time_series_outputs()
    operational_hours = load_operational_hours_outputs()

    if not series_by_combo:
        st.warning("No se encontraron series temporales generadas.")
        st.code("make build-ts", language="powershell")
        return

    if not summary.empty:
        with st.expander("Resumen comparativo (granularidades x rutas)", expanded=True):
            st.dataframe(_style_ts_summary(summary), use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar resumen CSV",
                data=_df_to_csv(summary),
                file_name="time_series_summary.csv",
                mime="text/csv",
            )

    available_routes = sorted({ruta for ruta, _ in series_by_combo})
    available_grans = sorted({gran for _, gran in series_by_combo})

    controls = st.columns([0.65, 0.75, 1.1, 1.1, 1.0])
    route = controls[0].selectbox("Ruta", available_routes, format_func=lambda v: f"Ruta {v}")
    grans_for_route = [g for g in available_grans if (route, g) in series_by_combo]
    gran = controls[1].selectbox(
        "Granularidad",
        grans_for_route,
        format_func=lambda v: f"{v} min",
    )
    metric = controls[2].selectbox(
        "Metrica",
        list(TIME_SERIES_METRIC_LABELS),
        format_func=lambda v: TIME_SERIES_METRIC_LABELS[v],
    )
    iqr_multiplier = controls[3].slider(
        "Sensibilidad atipicos IQR",
        min_value=1.0,
        max_value=3.5,
        value=1.5,
        step=0.1,
    )
    default_roll, max_roll = _ROLLING_DEFAULTS.get(gran, (24, 72))
    rolling_window = controls[4].slider(
        "Media movil",
        min_value=1,
        max_value=max_roll,
        value=default_roll,
        step=1,
        help="Numero de franjas usadas para suavizar la tendencia.",
    )

    data = series_by_combo[(route, gran)].copy()
    min_date = data["timestamp"].min().date()
    max_date = data["timestamp"].max().date()
    selected_range = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = end_date = selected_range

    mask = data["timestamp"].dt.date.between(start_date, end_date)
    filtered = data.loc[mask].copy()
    scored = detect_contextual_outliers(filtered, metric, iqr_multiplier)
    outliers = scored[scored["tipo_atipico"].ne("")].copy()

    metric_cols = st.columns(5)
    metric_values = pd.to_numeric(filtered[metric], errors="coerce")
    if metric in {"pasajeros_total", "despachos_count"}:
        selected_metric_value = _format_number(metric_values.sum(), decimals=1)
    else:
        selected_metric_value = _format_number(metric_values.mean(), decimals=2)
    metric_cols[0].metric("Filas", _format_number(len(filtered)))
    metric_cols[1].metric(TIME_SERIES_METRIC_LABELS[metric], selected_metric_value)
    if "is_gap" in filtered.columns:
        gap_count = int(filtered["is_gap"].fillna(False).astype(bool).sum())
        gap_pct = float(gap_count / len(filtered) * 100) if len(filtered) else 0
        metric_cols[2].metric("Gaps", f"{_format_number(gap_count)} ({gap_pct:.1f}%)")
    else:
        metric_cols[2].metric("Gaps", "N/D")
    if "gap_tipo" in filtered.columns:
        gap_anomalo_count = int(filtered["gap_tipo"].fillna("").astype(str).eq("gap_anomalo").sum())
        metric_cols[3].metric("Gaps anomalos", _format_number(gap_anomalo_count))
    else:
        metric_cols[3].metric("Gaps anomalos", "N/D")
    metric_cols[4].metric("Atipicos", _format_number(len(outliers)))

    tabs = st.tabs(
        [
            "Tendencia",
            "Atipicos",
            "Patrones",
            "Horario operativo",
            "Gaps y calidad",
            "Comparacion",
            "Datos",
        ]
    )

    with tabs[0]:
        plot_time_series_trend_inline(filtered, outliers, metric, rolling_window)
        insights = build_time_series_insights(filtered, metric, outliers)
        if not insights.empty:
            st.subheader("Hallazgos rapidos")
            st.dataframe(insights, use_container_width=True, hide_index=True)

    with tabs[1]:
        plot_outlier_heatmap_inline(outliers)
        outlier_cols = [
            "timestamp",
            "FK_RUTA",
            metric,
            "tipo_atipico",
            "mediana_contexto",
            "limite_inferior",
            "limite_superior",
            "desviacion_vs_mediana",
            "ratio_vs_mediana",
            "is_gap",
            "dia_semana",
            "hora_del_dia",
        ]
        available_cols = [col for col in outlier_cols if col in outliers.columns]
        table = outliers.reindex(columns=available_cols).sort_values(
            "desviacion_vs_mediana",
            key=lambda values: values.abs(),
            ascending=False,
        )
        st.dataframe(_style_outliers(table.head(100)), use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar atipicos CSV",
            data=_df_to_csv(table),
            file_name=f"ts_ruta{route}_g{gran}min_outliers.csv",
            mime="text/csv",
        )

    with tabs[2]:
        chart_cols = st.columns(2)
        with chart_cols[0]:
            plot_time_series_heatmap_inline(filtered, metric)
        with chart_cols[1]:
            plot_time_series_distribution_inline(filtered, metric)

    with tabs[3]:
        render_operational_hours_section(operational_hours, filtered, route, gran)

    with tabs[4]:
        plot_gap_heatmap_inline(filtered)
        if "gap_tipo" in filtered.columns:
            gap_type_cols = st.columns(2)
            with gap_type_cols[0]:
                plot_gap_type_heatmap_inline(filtered, "gap_anomalo")
            with gap_type_cols[1]:
                plot_gap_type_heatmap_inline(filtered, "fuera_operacion")

            gap_type_summary = build_gap_type_summary(filtered)
            st.subheader("Resumen por tipo de franja")
            st.dataframe(gap_type_summary, use_container_width=True, hide_index=True)

        if "is_gap" in filtered.columns:
            gap_summary = (
                _ensure_time_context(filtered)
                .assign(is_gap=lambda frame: frame["is_gap"].fillna(False).astype(bool))
                .groupby(["dia_semana", "hora_del_dia"], dropna=False)
                .agg(franjas=("timestamp", "count"), gaps=("is_gap", "sum"))
                .reset_index()
            )
            gap_summary["gap_pct"] = gap_summary["gaps"] / gap_summary["franjas"] * 100
            st.dataframe(
                gap_summary.sort_values("gap_pct", ascending=False).head(40),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[5]:
        plot_granularity_comparison_inline(
            series_by_combo, route, grans_for_route, metric, start_date, end_date
        )

    with tabs[6]:
        st.dataframe(filtered.head(500), use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar serie filtrada CSV",
            data=_df_to_csv(filtered),
            file_name=f"ts_ruta{route}_g{gran}min_filtrada.csv",
            mime="text/csv",
        )


def run_pipeline_subprocess() -> None:
    command = [
        sys.executable,
        "-c",
        "from proyecto_grado.etl.pipeline import main as run_pipeline; run_pipeline()",
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )
    st.session_state.pipeline_process = process
    st.session_state.pipeline_running = True
    st.session_state.pipeline_logs = []
    log_box = st.empty()

    if process.stdout is not None:
        for line in iter(process.stdout.readline, ""):
            if not line:
                break
            st.session_state.pipeline_logs.append(line.rstrip())
            log_box.code("\n".join(st.session_state.pipeline_logs[-160:]), language="text")

    returncode = process.wait()
    st.session_state.pipeline_returncode = returncode
    st.session_state.pipeline_process = None
    st.session_state.pipeline_running = False

    if returncode == 0:
        st.success("Pipeline completado correctamente. Recargando datasets...")
        st.cache_data.clear()
        st.rerun()

    logs = "\n".join(st.session_state.pipeline_logs).lower()
    if "mysql" in logs or "conex" in logs or "database" in logs:
        st.error(
            "No fue posible ejecutar el pipeline. Verifica que MySQL/Registel este disponible."
        )
    else:
        st.error(f"El pipeline finalizo con codigo de salida {returncode}.")


def render_pipeline_page() -> None:
    st.title("Pipeline & Logs")

    if st.button("▶ Ejecutar Pipeline Completo", type="primary", use_container_width=True):
        run_pipeline_subprocess()

    if st.session_state.pipeline_logs:
        st.subheader("Logs capturados en la sesion")
        st.code("\n".join(st.session_state.pipeline_logs[-160:]), language="text")

    st.subheader("Logs recientes")
    recent_logs = get_recent_log_text()
    if recent_logs:
        st.code(recent_logs, language="text")
    else:
        st.info("No se encontraron archivos .log recientes en reports/ ni logs/.")

    st.subheader("Archivos generados")
    files = get_generated_files()
    if files.empty:
        st.warning("No se encontraron artefactos generados en data/processed ni reports.")
        return

    for root_label, prefix in [
        ("Datos procesados", "data\\processed"),
        ("Reportes", "reports"),
    ]:
        normalized = files["archivo"].str.replace("/", "\\", regex=False)
        subset = files[normalized.str.startswith(prefix)]
        with st.expander(root_label, expanded=root_label == "Datos procesados"):
            st.dataframe(subset, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# EDA Temporal — data loaders
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300, show_spinner="Cargando artefactos EDA...")
def load_eda_artifacts(route: int, gran: int) -> dict[str, pd.DataFrame]:
    """Carga todos los artefactos EDA para ruta y granularidad dadas."""
    arts: dict[str, pd.DataFrame] = {}

    def _load(path: Path) -> pd.DataFrame:
        return pd.read_parquet(path) if path.exists() else pd.DataFrame()

    arts["perfil_intraday"] = _load(EDA_DIR / f"perfil_intraday_{route}_g{gran}min.parquet")
    arts["perfil_semanal"] = _load(EDA_DIR / f"perfil_semanal_{route}_g{gran}min.parquet")
    arts["perfil_mensual"] = _load(EDA_DIR / f"perfil_mensual_{route}.parquet")
    arts["autocorrelacion"] = _load(EDA_DIR / f"autocorr_{route}_g{gran}min.parquet")
    arts["atipicos"] = _load(EDA_DIR / f"atipicos_{route}_g{gran}min.parquet")
    arts["correlacion_features"] = _load(EDA_DIR / "correlacion_features.parquet")
    return arts


def _eda_artifacts_exist() -> bool:
    """Retorna True si existen al menos algunos artefactos EDA."""
    if EDA_DIR.exists() and any(EDA_DIR.glob("*.parquet")):
        return True
    if EDA_FIGURES_DIR.exists() and any(EDA_FIGURES_DIR.glob("*.png")):
        return True
    return EDA_SUMMARY_PATH.exists()


@st.cache_data(ttl=300)
def load_eda_summary_text() -> str:
    if not EDA_SUMMARY_PATH.exists():
        return ""
    return EDA_SUMMARY_PATH.read_text(encoding="utf-8", errors="replace").strip()


@st.cache_data(ttl=300)
def get_eda_generated_files() -> pd.DataFrame:
    roots = [EDA_DIR, EDA_FIGURES_DIR, EDA_SUMMARY_PATH.parent]
    rows = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {
                ".csv",
                ".parquet",
                ".png",
                ".txt",
            }:
                continue
            path_key = str(path.resolve())
            if path_key in seen:
                continue
            seen.add(path_key)
            stat = path.stat()
            rows.append(
                {
                    "archivo": str(path.relative_to(PROJECT_ROOT)),
                    "tipo": path.suffix.lower().lstrip("."),
                    "tamano": _format_file_size(stat.st_size),
                    "modificado": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "modified_at": stat.st_mtime,
                }
            )
    return pd.DataFrame(rows).sort_values("archivo") if rows else pd.DataFrame()


def _discover_eda_combos() -> set[tuple[int, int]]:
    if not EDA_DIR.exists():
        return set()
    combos: set[tuple[int, int]] = set()
    for path in EDA_DIR.glob("*.parquet"):
        match = _EDA_COMBO_PATTERN.match(path.stem)
        if match:
            combos.add((int(match.group(1)), int(match.group(2))))
    return combos


def _run_eda_subprocess() -> None:
    """Ejecuta run_eda_temporal.py como subproceso mostrando progreso."""
    script = PROJECT_ROOT / "scripts" / "run_eda_temporal.py"
    if not script.exists():
        st.error(f"Script no encontrado: {script}")
        return

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )
    log_box = st.empty()
    log_lines: list[str] = []
    if process.stdout:
        for line in iter(process.stdout.readline, ""):
            if not line:
                break
            log_lines.append(line.rstrip())
            log_box.code("\n".join(log_lines[-60:]), language="text")
    returncode = process.wait()
    if returncode == 0:
        st.success("EDA completado. Recargando...")
        st.cache_data.clear()
        st.rerun()
    else:
        st.error(f"EDA finalizó con código {returncode}.")


# ---------------------------------------------------------------------------
# EDA Temporal — block renderers
# ---------------------------------------------------------------------------


def _eda_metric_card(label: str, value: str, help_text: str = "", delta: str = "") -> None:
    st.metric(label=label, value=value, delta=delta or None, help=help_text or None)


def _ordered_day_types(values: pd.Series | list[object]) -> list[str]:
    raw_values = pd.Series(values).dropna().astype(str).unique().tolist()
    ordered = [value for value in DAY_TYPE_ORDER if value in raw_values]
    ordered.extend(sorted(value for value in raw_values if value not in DAY_TYPE_ORDER))
    return ordered


def _bool_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    return df[col].fillna(False).astype(bool)


def _outlier_pct_text(atdf: pd.DataFrame) -> str:
    if "pct_atipicos" not in atdf.columns:
        return "N/D"
    if atdf.empty:
        return "0.00%"
    return f"{float(atdf['pct_atipicos'].iloc[0]):.2f}%"


def plot_eda_intraday_inline(
    intraday_df: pd.DataFrame,
    route: int,
    gran: int,
    selected_type: str,
) -> None:
    if intraday_df.empty:
        st.info("Artefacto perfil_intraday no encontrado. Ejecuta el EDA primero.")
        return

    _apply_chart_theme()
    data = intraday_df.copy()
    for col in ["hora_del_dia", "media", "p25", "p75"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    fig, ax = plt.subplots(figsize=(11, 5.2))
    if selected_type == "Todos superpuestos" and "tipo_dia" in data.columns:
        palette = {
            "LABORAL": PALETTE["primary"],
            "SABADO": PALETTE["secondary"],
            "DOMINGO": PALETTE["accent"],
            "FESTIVO": "#b45309",
            "FESTIVO_PUENTE": "#6d28d9",
        }
        for tipo_dia in _ordered_day_types(data["tipo_dia"]):
            sub = data[data["tipo_dia"].astype(str) == tipo_dia].sort_values("hora_del_dia")
            ax.plot(
                sub["hora_del_dia"],
                sub["media"],
                marker="o",
                linewidth=2,
                markersize=4,
                label=tipo_dia,
                color=palette.get(tipo_dia, "#6b7280"),
            )
    else:
        if "tipo_dia" in data.columns and selected_type != "Serie agregada":
            data = data[data["tipo_dia"].astype(str) == selected_type]
        sub = data.sort_values("hora_del_dia")
        if sub.empty:
            st.warning("Sin datos para el tipo de dia seleccionado.")
            plt.close(fig)
            return

        if {"p25", "p75"}.issubset(sub.columns):
            ax.fill_between(
                sub["hora_del_dia"],
                sub["p25"],
                sub["p75"],
                alpha=0.25,
                color=PALETTE["secondary"],
                label="Banda p25-p75",
            )
        ax.plot(
            sub["hora_del_dia"],
            sub["media"],
            color=PALETTE["primary"],
            linewidth=2.4,
            label="Media",
        )
        picos = sub[_bool_col(sub, "es_pico")]
        valles = sub[_bool_col(sub, "es_valle")]
        if not picos.empty:
            ax.scatter(
                picos["hora_del_dia"],
                picos["media"],
                color="#16a34a",
                s=70,
                zorder=5,
                label="Hora pico",
            )
        if not valles.empty:
            ax.scatter(
                valles["hora_del_dia"],
                valles["media"],
                color="#6b7280",
                s=55,
                zorder=5,
                label="Hora valle",
            )

    ax.set_title(f"Perfil intradia - Ruta {route} | {gran} min | {selected_type}")
    ax.set_xlabel("Hora del dia")
    ax.set_ylabel("Pasajeros promedio")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.legend(loc="upper left", fontsize=8, ncols=2)
    _render_figure(fig)


def plot_eda_weekly_heatmap_inline(ts_df: pd.DataFrame, route: int, gran: int) -> None:
    if ts_df.empty:
        st.info("Serie temporal no disponible para la combinacion seleccionada.")
        return

    data = ts_df.copy()
    if "gap_tipo" in data.columns:
        data = data[data["gap_tipo"] == "operativo"]
    if data.empty:
        st.info("Sin franjas operativas para este filtro.")
        return

    _apply_chart_theme()
    data = _ensure_time_context(data)
    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora_del_dia",
        values="pasajeros_total",
        aggfunc="mean",
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0)
    pivot.index = [WEEKDAY_LABELS.get(int(index), str(index)) for index in pivot.index]

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.heatmap(
        pivot,
        cmap="YlGnBu",
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={
            "label": "Pasajeros promedio",
            "format": FuncFormatter(_compact_axis_number),
        },
    )
    ax.set_title(f"Demanda promedio por dia y hora - Ruta {route} | {gran} min")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Dia de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _render_figure(fig)


def plot_eda_monthly_trend_inline(monthly_df: pd.DataFrame, route: int) -> None:
    if monthly_df.empty:
        st.info("Perfil mensual no disponible.")
        return

    mes_data = (
        monthly_df[monthly_df["tipo_periodo"] == "mes"].copy()
        if "tipo_periodo" in monthly_df.columns
        else monthly_df.copy()
    )
    if mes_data.empty:
        st.info("Perfil mensual no disponible.")
        return

    _apply_chart_theme()
    mes_data = mes_data.sort_values("periodo").reset_index(drop=True)
    x = np.arange(len(mes_data), dtype=float)
    y = pd.to_numeric(mes_data["demanda_total"], errors="coerce").astype(float)
    if len(mes_data) >= 2 and y.notna().sum() >= 2:
        slope_month, intercept_month = np.polyfit(x[y.notna()], y[y.notna()], 1)
        trend = intercept_month + slope_month * x
    else:
        trend = y

    colors = [
        PALETTE["accent"] if bool(value) else PALETTE["secondary"]
        for value in mes_data.get("es_atipico", pd.Series(False, index=mes_data.index))
    ]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.bar(mes_data["periodo"], y, color=colors, alpha=0.88, label="Demanda mensual")
    ax.plot(
        mes_data["periodo"],
        trend,
        color=PALETTE["primary"],
        linewidth=2.4,
        linestyle="--",
        label="Tendencia visual",
    )
    ax.set_title(f"Tendencia mensual - Ruta {route}")
    ax.set_xlabel("")
    ax.set_ylabel("Pasajeros")
    ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=8)
    _render_figure(fig)

    if "tendencia_slope" in mes_data.columns:
        slope = float(mes_data["tendencia_slope"].iloc[0])
        monthly_change = slope * 30
        if abs(slope) < 0.5:
            direction = "estable"
        elif slope > 0:
            direction = f"creciente (+{monthly_change:,.0f} pasajeros/mes)"
        else:
            direction = f"decreciente ({monthly_change:,.0f} pasajeros/mes)"
        st.caption(
            f"Tendencia estimada desde demanda diaria agregada: **{direction}**. "
            "Barras en color acento = meses atipicos (> 2 sigma)."
        )


def plot_eda_autocorrelation_inline(adf: pd.DataFrame, route: int, gran: int) -> None:
    if adf.empty or "acf_value" not in adf.columns:
        st.info("Artefacto de autocorrelacion no disponible.")
        return

    _apply_chart_theme()
    data = adf.copy()
    lags = pd.to_numeric(data["lag"], errors="coerce")
    signif = 1.96 / np.sqrt(max(100, len(data) * 4))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=False)

    for ax, title, value_col, sig_col in [
        (axes[0], "ACF", "acf_value", "es_significativo_acf"),
        (axes[1], "PACF", "pacf_value", "es_significativo_pacf"),
    ]:
        values = pd.to_numeric(data[value_col], errors="coerce")
        is_significant = _bool_col(data, sig_col)
        colors = np.where(is_significant, PALETTE["primary"], "#a0c4c6")
        ax.bar(lags, values, color=colors, width=0.65)
        ax.axhline(signif, color=PALETTE["accent"], linestyle="--", linewidth=1)
        ax.axhline(-signif, color=PALETTE["accent"], linestyle="--", linewidth=1)
        ax.axhline(0, color="#1f2933", linewidth=0.8)
        ax.set_title(f"{title} - Ruta {route} | {gran} min")
        ax.set_xlabel("Lag (franjas)")
        ax.set_ylabel("Correlacion")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))

    relevant = data[_bool_col(data, "lags_relevantes_acf") & lags.gt(0)]
    for _, row in relevant.head(12).iterrows():
        lag = int(row["lag"])
        val = float(row["acf_value"])
        axes[0].annotate(
            str(lag),
            (lag, val),
            textcoords="offset points",
            xytext=(0, 6 if val >= 0 else -12),
            fontsize=7,
            color="#dc2626",
            ha="center",
        )

    _render_figure(fig)

    adf_pval = float(data["adf_pvalue"].iloc[0]) if "adf_pvalue" in data.columns else np.nan
    if not np.isnan(adf_pval):
        state = "estacionaria" if adf_pval < 0.05 else "no estacionaria"
        st.caption(f"Test ADF: p = {adf_pval:.4f}. La serie es **{state}**.")
    if not relevant.empty:
        lags_rel = relevant["lag"].astype(int).tolist()
        max_lag = max(lags_rel)
        st.info(
            f"Lags ACF > 0.3: {lags_rel[:10]}. "
            f"Lookback recomendado: {max_lag} franjas (~{max_lag * gran // 60} h)."
        )


def plot_eda_outliers_inline(
    ts_df: pd.DataFrame,
    atdf: pd.DataFrame,
    route: int,
    gran: int,
    metodo: str,
) -> None:
    if ts_df.empty:
        st.info("Serie temporal no disponible para graficar atipicos.")
        return

    _apply_chart_theme()
    data = ts_df.copy()
    if "gap_tipo" in data.columns:
        data = data[data["gap_tipo"] == "operativo"]
    data = _sample_for_chart(data, max_rows=10000)
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data["pasajeros_total"] = pd.to_numeric(data["pasajeros_total"], errors="coerce")

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.scatter(
        data["timestamp"],
        data["pasajeros_total"],
        s=8,
        alpha=0.35,
        color="#9ca3af",
        label="Serie operativa",
    )

    if not atdf.empty and "timestamp" in atdf.columns:
        out = atdf.copy()
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
        out["pasajeros_total"] = pd.to_numeric(out["pasajeros_total"], errors="coerce")
        ax.scatter(
            out["timestamp"],
            out["pasajeros_total"],
            s=30,
            alpha=0.85,
            color="#dc2626",
            label=f"Atipicos ({metodo})",
        )

    ax.set_title(f"Atipicos sobre serie operativa - Ruta {route} | {gran} min")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Pasajeros")
    ax.yaxis.set_major_formatter(FuncFormatter(_compact_axis_number))
    ax.legend(fontsize=8)
    _render_figure(fig)


def render_eda_block_a(arts: dict[str, pd.DataFrame], route: int, gran: int) -> None:
    """Bloque A - resumen ejecutivo del EDA."""
    st.subheader("Resumen ejecutivo")

    idf = arts.get("perfil_intraday", pd.DataFrame())
    sdf = arts.get("perfil_semanal", pd.DataFrame())
    mdf = arts.get("perfil_mensual", pd.DataFrame())
    adf = arts.get("autocorrelacion", pd.DataFrame())
    atdf = arts.get("atipicos", pd.DataFrame())

    pico_hora = ratio_pv = "N/D"
    if not idf.empty and "hora_del_dia" in idf.columns:
        laboral = idf[idf["tipo_dia"] == "LABORAL"] if "tipo_dia" in idf.columns else idf
        if not laboral.empty and "es_pico" in laboral.columns:
            horas_pico = sorted(
                pd.to_numeric(laboral.loc[_bool_col(laboral, "es_pico"), "hora_del_dia"])
                .dropna()
                .astype(int)
                .tolist()
            )
            pico_hora = ", ".join(f"{hour:02d}:00" for hour in horas_pico) if horas_pico else "N/D"
        if "ratio_pico_valle" in laboral.columns and not laboral.empty:
            ratio = laboral["ratio_pico_valle"].dropna()
            ratio_pv = f"{float(ratio.iloc[0]):.2f}x" if not ratio.empty else "N/D"

    dia_mayor = "N/D"
    if not sdf.empty and "es_max" in sdf.columns:
        row_max = sdf.loc[_bool_col(sdf, "es_max")]
        if not row_max.empty and "nombre_dia" in row_max.columns:
            dia_mayor = str(row_max["nombre_dia"].iloc[0])

    tendencia = "N/D"
    if not mdf.empty:
        mes_data = mdf[mdf["tipo_periodo"] == "mes"] if "tipo_periodo" in mdf.columns else mdf
        if not mes_data.empty and "tendencia_slope" in mes_data.columns:
            slope = float(mes_data["tendencia_slope"].iloc[0])
            if abs(slope) < 0.5:
                tendencia = "Estable"
            elif slope > 0:
                tendencia = f"Creciente (+{slope * 30:,.0f} pas/mes)"
            else:
                tendencia = f"Decreciente ({slope * 30:,.0f} pas/mes)"

    adf_state = "N/D"
    adf_delta = ""
    lookback = "N/D"
    if not adf.empty and "adf_pvalue" in adf.columns:
        pval = float(adf["adf_pvalue"].iloc[0])
        adf_state = "Estacionaria" if pval < 0.05 else "No estacionaria"
        adf_delta = f"p={pval:.4f}"
        lags_rel = adf.loc[_bool_col(adf, "lags_relevantes_acf") & adf["lag"].gt(0), "lag"]
        if not lags_rel.empty:
            max_lag = int(lags_rel.max())
            lookback = f"{max_lag} franjas (~{max_lag * gran // 60} h)"

    c1, c2, c3 = st.columns(3)
    c1.metric("Hora pico (LABORAL)", pico_hora)
    c2.metric("Ratio pico/valle", ratio_pv)
    c3.metric("Dia mayor demanda", dia_mayor)

    c4, c5, c6 = st.columns(3)
    c4.metric("Tendencia", tendencia)
    c5.metric("Lookback recomendado", lookback)
    c6.metric("ADF estacionariedad", adf_state, adf_delta or None)

    c7, c8 = st.columns(2)
    c7.metric("Atipicos operativos", _outlier_pct_text(atdf))

    corr_df = arts.get("correlacion_features", pd.DataFrame())
    if not corr_df.empty:
        c8.metric(
            "Feature mas correlacionada",
            str(corr_df.iloc[0]["feature"])[:28],
            f"{float(corr_df.iloc[0]['correlacion_spearman']):+.3f}",
        )
        show_cols = [
            col
            for col in ["rank", "feature", "correlacion_spearman", "abs_correlacion"]
            if col in corr_df.columns
        ]
        with st.expander("Top features correlacionadas", expanded=False):
            st.dataframe(corr_df[show_cols].head(10), use_container_width=True, hide_index=True)

    summary_text = load_eda_summary_text()
    if summary_text:
        with st.expander("Resumen ejecutivo generado por scripts/run_eda_temporal.py"):
            st.code(summary_text, language="text")


def render_eda_block_b(
    arts: dict[str, pd.DataFrame],
    route: int,
    gran: int,
) -> None:
    """Bloque B - perfil intradia."""
    idf = arts.get("perfil_intraday", pd.DataFrame())
    if idf.empty:
        st.info("Artefacto perfil_intraday no encontrado. Ejecuta el EDA primero.")
        return

    if "tipo_dia" in idf.columns:
        tipos_disponibles = _ordered_day_types(idf["tipo_dia"])
        opciones = ["Todos superpuestos", *tipos_disponibles]
    else:
        opciones = ["Serie agregada"]

    selected_type = st.selectbox("Tipo de dia", opciones, key="eda_b_tipo_dia")
    plot_eda_intraday_inline(idf, route, gran, selected_type)

    with st.expander("Datos de perfil intradia", expanded=False):
        st.dataframe(
            idf.sort_values(idf.columns.tolist()), use_container_width=True, hide_index=True
        )


def render_eda_block_c(
    series_by_combo: dict[tuple[int, int], pd.DataFrame],
    arts: dict[str, pd.DataFrame],
    route: int,
    gran: int,
) -> None:
    """Bloque C - heatmap semanal."""
    ts_df = series_by_combo.get((route, gran), pd.DataFrame())
    plot_eda_weekly_heatmap_inline(ts_df, route, gran)

    sdf = arts.get("perfil_semanal", pd.DataFrame())
    if not sdf.empty:
        st.caption("Estadisticas por dia de semana")
        show_cols = [
            c
            for c in [
                "nombre_dia",
                "demanda_total",
                "demanda_promedio",
                "variabilidad",
                "es_max",
                "es_min",
            ]
            if c in sdf.columns
        ]
        st.dataframe(sdf[show_cols], use_container_width=True, hide_index=True)


def render_eda_block_d(arts: dict[str, pd.DataFrame], route: int, gran: int) -> None:
    """Bloque D - tendencia mensual y ACF/PACF."""
    plot_eda_monthly_trend_inline(arts.get("perfil_mensual", pd.DataFrame()), route)
    plot_eda_autocorrelation_inline(arts.get("autocorrelacion", pd.DataFrame()), route, gran)


def render_eda_block_e(
    arts: dict[str, pd.DataFrame],
    series_by_combo: dict[tuple[int, int], pd.DataFrame],
    route: int,
    gran: int,
) -> None:
    """Bloque E - valores atipicos."""
    atdf = arts.get("atipicos", pd.DataFrame())
    ts_df = series_by_combo.get((route, gran), pd.DataFrame())

    metodo = st.selectbox(
        "Metodo de deteccion",
        ["IQR", "zscore", "Ambos"],
        key="eda_e_metodo",
    )
    pct_val = _outlier_pct_text(atdf)
    st.metric("% franjas operativas atipicas", pct_val)

    if not atdf.empty and "metodo_deteccion" in atdf.columns:
        if metodo == "IQR":
            atdf_filtered = atdf[_bool_col(atdf, "es_atipico_iqr")]
        elif metodo == "zscore":
            atdf_filtered = atdf[_bool_col(atdf, "es_atipico_zscore")]
        else:
            atdf_filtered = atdf
    else:
        atdf_filtered = atdf

    plot_eda_outliers_inline(ts_df, atdf_filtered, route, gran, metodo)

    if not atdf_filtered.empty:
        sort_col = (
            "zscore_tipo_dia" if "zscore_tipo_dia" in atdf_filtered.columns else "pasajeros_total"
        )
        show_cols = [
            c
            for c in [
                "fecha",
                "hora_del_dia",
                "tipo_dia",
                "pasajeros_total",
                "es_atipico_iqr",
                "es_atipico_zscore",
                "metodo_deteccion",
                "zscore_tipo_dia",
            ]
            if c in atdf_filtered.columns
        ]
        if not show_cols:
            st.dataframe(atdf_filtered.head(20), use_container_width=True, hide_index=True)
            return
        if sort_col not in show_cols and show_cols:
            sort_col = show_cols[0]
        top20 = (
            atdf_filtered[show_cols]
            .sort_values(
                sort_col,
                key=lambda series: pd.to_numeric(series, errors="coerce").abs(),
                ascending=False,
            )
            .head(20)
        )
        st.caption("Top 20 valores mas extremos")
        st.dataframe(top20, use_container_width=True, hide_index=True)
        st.caption(
            f"{pct_val} de franjas operativas son atipicas dentro del rango "
            "esperado para sistemas con operacion descentralizada."
        )
    elif "pct_atipicos" in atdf.columns:
        st.success("No se detectaron atipicos con el metodo seleccionado.")


def _render_eda_image(path: Path, caption: str) -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"Figura no encontrada: {path.name}")


def render_eda_cli_outputs(arts: dict[str, pd.DataFrame], route: int, gran: int) -> None:
    st.subheader("Figuras generadas por el CLI")

    idf = arts.get("perfil_intraday", pd.DataFrame())
    if not idf.empty and "tipo_dia" in idf.columns:
        tipos = _ordered_day_types(idf["tipo_dia"])
    else:
        tipos = ["todos"]
    selected_type = st.selectbox("Curva intradia estatica", tipos, key="eda_fig_tipo_dia")
    slug = str(selected_type).lower()

    figure_specs = [
        (
            EDA_FIGURES_DIR / f"curva_intraday_{route}_{slug}_g{gran}min.png",
            f"Curva intradia - {selected_type}",
        ),
        (
            EDA_FIGURES_DIR / f"heatmap_demanda_hora_dia_{route}_g{gran}min.png",
            "Heatmap hora-dia",
        ),
        (
            EDA_FIGURES_DIR / f"boxplot_tipo_dia_{route}_g{gran}min.png",
            "Distribucion por tipo de dia",
        ),
        (
            EDA_FIGURES_DIR / f"acf_pacf_{route}_g{gran}min.png",
            "ACF / PACF",
        ),
        (EDA_FIGURES_DIR / f"tendencia_mensual_{route}.png", "Tendencia mensual"),
    ]

    for index in range(0, len(figure_specs), 2):
        cols = st.columns(2)
        for col, (path, caption) in zip(cols, figure_specs[index : index + 2], strict=False):
            with col:
                _render_eda_image(path, caption)

    files = get_eda_generated_files()
    if not files.empty:
        st.subheader("Artefactos EDA en disco")
        display_files = files.drop(columns=["modified_at"], errors="ignore")
        st.dataframe(display_files, use_container_width=True, hide_index=True)
    else:
        st.info("No se encontraron artefactos EDA en disco.")


def render_eda_temporal_page() -> None:
    """Pagina EDA Temporal: resultados del analisis exploratorio temporal."""
    st.title("EDA Temporal")
    st.caption(
        "Resultados generados por `src/proyecto_grado/eda/temporal_analysis.py` "
        "y `scripts/run_eda_temporal.py`."
    )

    if not _eda_artifacts_exist():
        st.warning("No se encontraron artefactos EDA. Ejecuta el analisis para generarlos.")
        if st.button("Ejecutar EDA Temporal", type="primary", use_container_width=True):
            with st.spinner("Ejecutando analisis EDA temporal..."):
                _run_eda_subprocess()
        return

    eda_files = get_eda_generated_files()
    if not eda_files.empty:
        parquet_count = int((eda_files["tipo"] == "parquet").sum())
        figure_count = int((eda_files["tipo"] == "png").sum())
        latest = eda_files.sort_values("modified_at", ascending=False)["modificado"].iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Artefactos Parquet", _format_number(parquet_count))
        c2.metric("Figuras PNG", _format_number(figure_count))
        c3.metric("Ultima actualizacion", latest)

    series_by_combo, _ = load_time_series_outputs()
    available_combos = set(series_by_combo) | _discover_eda_combos()

    if not available_combos:
        st.warning("No se encontraron combinaciones ruta/granularidad. Ejecuta `make build-ts`.")
        return

    ctrl = st.columns([0.5, 0.5])
    available_routes = sorted({route for route, _ in available_combos})
    route = ctrl[0].selectbox(
        "Ruta",
        available_routes,
        format_func=lambda v: f"Ruta {v}",
        key="eda_route",
    )
    grans_for_route = sorted({gran for route_id, gran in available_combos if route_id == route})
    gran = ctrl[1].selectbox(
        "Granularidad",
        grans_for_route,
        format_func=lambda v: f"{v} min",
        key="eda_gran",
    )

    arts = load_eda_artifacts(route, gran)

    tabs = st.tabs(
        [
            "A. Resumen ejecutivo",
            "B. Perfil intradia",
            "C. Heatmap semanal",
            "D. Tendencia y ACF",
            "E. Atipicos",
            "F. Figuras CLI",
        ]
    )

    with tabs[0]:
        render_eda_block_a(arts, route, gran)

    with tabs[1]:
        render_eda_block_b(arts, route, gran)

    with tabs[2]:
        render_eda_block_c(series_by_combo, arts, route, gran)

    with tabs[3]:
        render_eda_block_d(arts, route, gran)

    with tabs[4]:
        render_eda_block_e(arts, series_by_combo, route, gran)

    with tabs[5]:
        render_eda_cli_outputs(arts, route, gran)

    st.divider()
    if st.button("Regenerar artefactos EDA", use_container_width=False):
        with st.spinner("Ejecutando EDA temporal..."):
            _run_eda_subprocess()


def render_app() -> None:
    st.set_page_config(layout="wide", page_title=APP_TITLE)
    init_session_state()
    inject_styles()
    page = render_sidebar()
    datasets, diagnostics, kpi_tables = load_dashboard_data()

    if page == "Resumen General":
        render_summary_page(datasets, diagnostics, kpi_tables)
    elif page == "Diagnostico ETL":
        render_diagnostics_page(diagnostics)
    elif page == "KPIs Operacionales":
        render_kpis_page(kpi_tables)
    elif page == "Series Temporales":
        render_time_series_page()
    elif page == "EDA Temporal":
        render_eda_temporal_page()
    else:
        render_pipeline_page()


def main() -> None:
    """Console entry point for `dashboard`."""
    from streamlit.web import cli as stcli

    app_path = Path(__file__).resolve()
    sys.argv = ["streamlit", "run", *sys.argv[1:], str(app_path)]
    stcli.main()


if __name__ == "__main__":
    render_app()
