"""Genera la figura mensual de contraccion de oferta operativa.

Lee la tabla ya calculada `diagnostico_flota_mensual.csv` y produce una
figura 2x2 para el capitulo de diagnostico. No recalcula indicadores ni
modifica los datos fuente.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "reports" / "tables" / "baseline" / "diagnostico_flota_mensual.csv"
OUTPUT_PNG = ROOT / "reports" / "figures" / "baseline" / "contraccion_flota_mensual.png"

SPAN_START = pd.Timestamp("2025-10-01")
SPAN_END = pd.Timestamp("2025-12-01")

MONTH_ABBR = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def _format_month(x: float, _pos=None) -> str:
    date = mdates.num2date(x)
    return f"{MONTH_ABBR[date.month]} {date.year}"


def _format_thousands(value: float, _pos=None) -> str:
    return f"{value / 1000:.0f}k"


def _format_integer(value: float, _pos=None) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _read_monthly_data(path: Path) -> pd.DataFrame:
    required = {
        "mes",
        "vehiculos_activos",
        "despachos_total",
        "pasajeros_total",
        "productividad_por_despacho",
        "despachos_por_vehiculo",
    }
    df = pd.read_csv(path, encoding="utf-8")
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en {path}: {sorted(missing)}")

    df = df.copy()
    df["mes"] = pd.to_datetime(df["mes"], errors="raise")
    df = df.sort_values("mes").reset_index(drop=True)

    if len(df) < 3:
        raise ValueError("La tabla mensual debe tener al menos tres meses.")

    # El primer y ultimo mes del CSV son parciales; el diagnostico comparativo
    # usa el periodo completo mayo 2024 - mayo 2026.
    return df.iloc[1:-1].copy().reset_index(drop=True)


def _style_axis(ax) -> None:
    ax.grid(True, which="major", axis="both", color="#d9dee3", linewidth=0.7, alpha=0.85)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#6b7280")
    ax.spines["bottom"].set_color("#6b7280")
    ax.tick_params(colors="#1f2933", labelsize=9)
    ax.axvspan(SPAN_START, SPAN_END, color="#8a5a44", alpha=0.12, linewidth=0)


def _plot_series(ax, df: pd.DataFrame, column: str, title: str, ylabel: str, color: str) -> None:
    ax.plot(
        df["mes"],
        df[column],
        color=color,
        linewidth=2.1,
        marker="o",
        markersize=4.8,
        markerfacecolor="white",
        markeredgewidth=1.4,
    )
    ax.set_title(title, loc="left", fontsize=12, fontweight="semibold", color="#111827")
    ax.set_ylabel(ylabel, fontsize=10, color="#1f2933")
    _style_axis(ax)


def build_figure(df: pd.DataFrame, output_path: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#6b7280",
            "axes.labelcolor": "#1f2933",
            "xtick.color": "#1f2933",
            "ytick.color": "#1f2933",
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    ax_veh, ax_desp = axes[0]
    ax_pas, ax_prod = axes[1]

    _plot_series(
        ax_veh,
        df,
        "vehiculos_activos",
        "Vehículos activos",
        "Vehículos",
        "#2f6f73",
    )
    _plot_series(
        ax_desp,
        df,
        "despachos_total",
        "Despachos totales",
        "Despachos",
        "#4b78a8",
    )
    _plot_series(
        ax_pas,
        df,
        "pasajeros_total",
        "Pasajeros totales",
        "Pasajeros",
        "#8a5a44",
    )
    _plot_series(
        ax_prod,
        df,
        "productividad_por_despacho",
        "Productividad (pasajeros/despacho)",
        "Pasajeros/despacho",
        "#6b7280",
    )

    ax_desp.yaxis.set_major_formatter(FuncFormatter(_format_integer))
    ax_pas.yaxis.set_major_formatter(FuncFormatter(_format_thousands))
    ax_prod.set_ylim(bottom=0)
    ax_prod.yaxis.set_major_locator(MaxNLocator(nbins=6))

    locator = mdates.MonthLocator(bymonth=[1, 4, 7, 10])
    formatter = FuncFormatter(_format_month)
    for ax in axes.flat:
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

    for ax in axes[1]:
        ax.set_xlabel("Mes", fontsize=10, color="#1f2933")
        ax.tick_params(axis="x", rotation=0)

    trans = mtransforms.blended_transform_factory(ax_veh.transData, ax_veh.transAxes)
    ax_veh.text(
        pd.Timestamp("2025-10-08"),
        0.92,
        "retiros de vehículos",
        transform=trans,
        fontsize=9,
        color="#7c2d12",
        ha="left",
        va="center",
    )

    first = df.iloc[0]
    last = df.iloc[-1]
    ax_veh.annotate(
        f"{int(first['vehiculos_activos'])} → {int(last['vehiculos_activos'])}",
        xy=(last["mes"], last["vehiculos_activos"]),
        xytext=(-58, 18),
        textcoords="offset points",
        fontsize=9,
        color="#1f2933",
        arrowprops={"arrowstyle": "-", "color": "#6b7280", "lw": 0.8},
    )

    prod_min = round(df["productividad_por_despacho"].min())
    prod_max = round(df["productividad_por_despacho"].max())
    ax_prod.text(
        0.03,
        0.9,
        f"{prod_min}-{prod_max}, estable",
        transform=ax_prod.transAxes,
        fontsize=9,
        color="#1f2933",
        ha="left",
        va="center",
    )

    fig.tight_layout(pad=1.8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _fmt_month(ts: pd.Timestamp) -> str:
    return f"{MONTH_ABBR[ts.month]} {ts.year}"


def print_verification(df: pd.DataFrame, output_path: Path) -> None:
    first = df.iloc[0]
    last = df.iloc[-1]
    series = [
        ("Vehículos activos", "vehiculos_activos", "{:.0f}"),
        ("Despachos totales", "despachos_total", "{:.0f}"),
        ("Pasajeros totales", "pasajeros_total", "{:.0f}"),
        ("Productividad (pas/desp)", "productividad_por_despacho", "{:.2f}"),
    ]

    print("Verificación de figura - contracción de flota")
    print(f"Meses graficados: {len(df)}")
    print(f"Primer mes: {_fmt_month(first['mes'])}")
    print(f"Último mes: {_fmt_month(last['mes'])}")
    for label, column, fmt in series:
        print(f"{label}: {fmt.format(first[column])} -> {fmt.format(last[column])}")
    print(f"PNG generado: {output_path}")


def main() -> None:
    df = _read_monthly_data(INPUT_CSV)
    build_figure(df, OUTPUT_PNG)
    print_verification(df, OUTPUT_PNG)


if __name__ == "__main__":
    main()
