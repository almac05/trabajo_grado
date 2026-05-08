"""Plot helpers for post-ETL diagnostics."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter, MaxNLocator

PALETTE = {
    "primary": "#2f6f73",
    "secondary": "#4b78a8",
    "accent": "#8a5a44",
    "muted": "#6b7280",
    "grid": "#d9dee3",
}


def _set_theme() -> None:
    sns.set_theme(
        context="paper",
        style="whitegrid",
        font="DejaVu Sans",
        rc={
            "figure.dpi": 120,
            "savefig.dpi": 220,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.titleweight": "semibold",
            "axes.edgecolor": "#2f3437",
            "grid.color": PALETTE["grid"],
            "grid.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
        },
    )


def _format_number(value, _pos=None) -> str:
    if pd.isna(value):
        return ""
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return f"{value:.0f}"


def _format_bar_label(value: float) -> str:
    if pd.isna(value):
        return ""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:.0f}"


def _annotate_vertical_bars(ax, values) -> None:
    max_value = max(values) if len(values) else 0
    offset = max_value * 0.012 if max_value else 1
    for patch, value in zip(ax.patches, values, strict=False):
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            patch.get_height() + offset,
            _format_bar_label(float(value)),
            ha="center",
            va="bottom",
            fontsize=8.5,
            color="#1f2933",
        )


def _annotate_horizontal_bars(ax, values) -> None:
    max_value = max(values) if len(values) else 0
    offset = max_value * 0.01 if max_value else 1
    for patch, value in zip(ax.patches, values, strict=False):
        ax.text(
            patch.get_width() + offset,
            patch.get_y() + patch.get_height() / 2,
            _format_bar_label(float(value)),
            ha="left",
            va="center",
            fontsize=8.5,
            color="#1f2933",
        )


def _save_current(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=1.2)
    plt.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close()


def plot_row_counts(dataset_overview: pd.DataFrame, path: str | Path) -> None:
    """Save a bar chart with row counts by ETL stage."""
    _set_theme()
    data = dataset_overview.copy()
    data["stage_label"] = data["stage"].replace(
        {
            "raw": "Crudo",
            "quality_checked": "QC",
            "trip_end_resolved": "Fin resuelto",
            "model_ready": "Model-ready",
        }
    )
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    sns.barplot(data=data, x="stage_label", y="rows", color=PALETTE["primary"], ax=ax)
    ax.set_ylabel("Filas")
    ax.set_xlabel("Etapa")
    ax.set_title("Registros conservados por etapa del ETL")
    ax.yaxis.set_major_formatter(FuncFormatter(_format_number))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.tick_params(axis="x", rotation=0)
    _annotate_vertical_bars(ax, data["rows"].tolist())
    ax.margins(y=0.14)
    _save_current(path)


def plot_qc_flags(qc_flag_summary: pd.DataFrame, path: str | Path, top_n: int = 12) -> None:
    """Save a horizontal bar chart with the most frequent QC flags."""
    _set_theme()
    data = qc_flag_summary.head(top_n).copy()
    if data.empty:
        return
    data = data.sort_values("count", ascending=True)
    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    sns.barplot(data=data, x="count", y="flag", color=PALETTE["accent"], ax=ax)
    ax.set_xlabel("Registros")
    ax.set_ylabel("")
    ax.set_title("Principales alertas de calidad del ETL")
    ax.xaxis.set_major_formatter(FuncFormatter(_format_number))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    _annotate_horizontal_bars(ax, data["count"].tolist())
    ax.margins(x=0.13)
    _save_current(path)


def plot_demand_by_route(demand_by_route: pd.DataFrame, path: str | Path) -> None:
    """Save a bar chart with total passengers by route."""
    _set_theme()
    data = demand_by_route.copy()
    if data.empty:
        return
    data["ruta"] = data["FK_RUTA"].astype(str)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    sns.barplot(data=data, x="ruta", y="pasajeros_total", color=PALETTE["secondary"], ax=ax)
    ax.set_xlabel("Ruta")
    ax.set_ylabel("Pasajeros")
    ax.set_title("Demanda acumulada por ruta")
    ax.yaxis.set_major_formatter(FuncFormatter(_format_number))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    _annotate_vertical_bars(ax, data["pasajeros_total"].tolist())
    ax.margins(y=0.14)
    _save_current(path)


def plot_hour_weekday_heatmap(demand_by_hour_weekday: pd.DataFrame, path: str | Path) -> None:
    """Save a heatmap-like image for passenger demand by weekday and hour."""
    _set_theme()
    data = demand_by_hour_weekday.copy()
    if data.empty:
        return
    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora",
        values="pasajeros_total",
        aggfunc="sum",
        fill_value=0,
    )
    weekday_labels = {
        0: "Lun",
        1: "Mar",
        2: "Mie",
        3: "Jue",
        4: "Vie",
        5: "Sab",
        6: "Dom",
    }
    pivot = pivot.reindex(range(7), fill_value=0)
    pivot.index = [weekday_labels.get(int(i), str(i)) for i in pivot.index]

    fig, ax = plt.subplots(figsize=(10.8, 5.3))
    sns.heatmap(
        pivot,
        cmap="YlGnBu",
        ax=ax,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"label": "Pasajeros", "format": FuncFormatter(_format_number)},
    )
    ax.set_xlabel("Hora de inicio")
    ax.set_ylabel("Dia de semana")
    ax.set_title("Distribucion horaria de la demanda por dia")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    _save_current(path)


def save_standard_plots(
    tables: dict[str, pd.DataFrame],
    figures_dir: str | Path,
) -> list[Path]:
    """Generate the standard post-ETL figures and return saved paths."""
    figures_dir = Path(figures_dir)
    saved: list[Path] = []

    mapping = [
        ("dataset_overview", "etl_rows_by_stage.png", plot_row_counts),
        ("qc_flag_summary", "qc_flags_top.png", plot_qc_flags),
        ("demand_by_route", "demand_by_route.png", plot_demand_by_route),
        ("demand_by_hour_weekday", "demand_by_hour_weekday.png", plot_hour_weekday_heatmap),
    ]
    for table_name, file_name, fn in mapping:
        df = tables.get(table_name)
        if df is None or df.empty:
            continue
        path = figures_dir / file_name
        fn(df, path)
        saved.append(path)
    return saved
