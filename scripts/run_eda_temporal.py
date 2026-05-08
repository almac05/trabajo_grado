"""Script CLI para ejecutar el EDA temporal y generar figuras estáticas."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter, MaxNLocator

# Allow running as a script from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from proyecto_grado.eda.temporal_analysis import TemporalEDA
from proyecto_grado.etl.config import PROJECT_ROOT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FIGURES_DIR = PROJECT_ROOT / "reports" / "figures" / "eda"
SUMMARY_PATH = PROJECT_ROOT / "reports" / "tables" / "eda" / "temporal_executive_summary.txt"
PALETTE = {
    "primary": "#2f6f73",
    "secondary": "#4b78a8",
    "accent": "#8a5a44",
    "pico": "#16a34a",
    "valle": "#6b7280",
    "atipico": "#dc2626",
    "grid": "#d9dee3",
}
WEEKDAY_LABELS = {
    0: "Lun",
    1: "Mar",
    2: "Mie",
    3: "Jue",
    4: "Vie",
    5: "Sab",
    6: "Dom",
}


def _set_theme() -> None:
    sns.set_theme(
        context="paper",
        style="whitegrid",
        font="DejaVu Sans",
        rc={
            "figure.dpi": 120,
            "savefig.dpi": 200,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.titleweight": "semibold",
            "axes.edgecolor": "#2f3437",
            "grid.color": PALETTE["grid"],
            "grid.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
        },
    )


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=1.2)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Figura guardada: %s", path.name)


def _save_summary(summary: str) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")
    logger.info("Resumen ejecutivo guardado: %s", SUMMARY_PATH)


# ---------------------------------------------------------------------------
# Figure generators
# ---------------------------------------------------------------------------


def plot_curva_intraday(
    intraday_df: pd.DataFrame,
    ruta: int,
    gran: int,
) -> None:
    """Curva intradía con banda p25-p75 por tipo_dia."""
    if intraday_df.empty or "hora_del_dia" not in intraday_df.columns:
        return

    tipos_dia = intraday_df["tipo_dia"].unique() if "tipo_dia" in intraday_df.columns else [None]
    for tipo_dia in tipos_dia:
        sub = (
            intraday_df[intraday_df["tipo_dia"] == tipo_dia] if tipo_dia else intraday_df
        ).sort_values("hora_del_dia")
        if sub.empty:
            continue

        fig, ax = plt.subplots(figsize=(10, 5))
        horas = sub["hora_del_dia"].values

        ax.fill_between(
            horas,
            sub["p25"].values,
            sub["p75"].values,
            alpha=0.25,
            color=PALETTE["secondary"],
            label="Banda p25-p75",
        )
        ax.plot(horas, sub["media"].values, color=PALETTE["primary"], lw=2, label="Media")

        picos = sub[sub["es_pico"]]
        valles = sub[sub["es_valle"]]
        if not picos.empty:
            ax.scatter(
                picos["hora_del_dia"],
                picos["media"],
                color=PALETTE["pico"],
                zorder=5,
                s=70,
                label="Hora pico",
            )
        if not valles.empty:
            ax.scatter(
                valles["hora_del_dia"],
                valles["media"],
                color=PALETTE["valle"],
                zorder=5,
                s=70,
                label="Hora valle",
            )

        td_label = tipo_dia if tipo_dia else "Todos"
        ax.set_title(f"Ruta {ruta} | {td_label} | {gran} min")
        ax.set_xlabel("Hora del día")
        ax.set_ylabel("Pasajeros promedio")
        ax.set_xticks(range(0, 24, 2))
        ax.legend(loc="upper left", fontsize=8)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))

        td_slug = (tipo_dia or "todos").lower()
        out = FIGURES_DIR / f"curva_intraday_{ruta}_{td_slug}_g{gran}min.png"
        _save(fig, out)


def plot_heatmap_hora_dia(
    ts_df: pd.DataFrame,
    ruta: int,
    gran: int,
) -> None:
    """Heatmap dia de semana x hora con pasajeros_total promedio."""
    if ts_df.empty:
        return
    data = ts_df.copy()
    if "gap_tipo" in data.columns:
        data = data[data["gap_tipo"] == "operativo"]
    if data.empty:
        return

    pivot = data.pivot_table(
        index="dia_semana",
        columns="hora_del_dia",
        values="pasajeros_total",
        aggfunc="mean",
        fill_value=0,
    )
    pivot = pivot.reindex(range(7), fill_value=0)
    pivot.index = [WEEKDAY_LABELS.get(int(i), str(i)) for i in pivot.index]

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(
        pivot,
        cmap="YlGnBu",
        ax=ax,
        linewidths=0.3,
        linecolor="white",
        cbar_kws={"label": "Pasajeros promedio"},
    )
    ax.set_title(f"Demanda promedio por día y hora — Ruta {ruta} | {gran} min")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Día de semana")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)

    out = FIGURES_DIR / f"heatmap_demanda_hora_dia_{ruta}_g{gran}min.png"
    _save(fig, out)


def plot_tendencia_mensual(
    mensual_df: pd.DataFrame,
    ruta: int,
) -> None:
    """Serie mensual con línea de tendencia y meses atípicos marcados."""
    if mensual_df.empty:
        return
    data = mensual_df[mensual_df["tipo_periodo"] == "mes"].copy()
    if data.empty:
        return

    data = data.sort_values("periodo").reset_index(drop=True)
    x = np.arange(len(data))
    y = data["demanda_total"].values

    slope = float(data["tendencia_slope"].iloc[0]) if "tendencia_slope" in data.columns else 0.0
    if len(data) >= 2 and np.isfinite(y).sum() >= 2:
        slope_month, intercept_month = np.polyfit(x[np.isfinite(y)], y[np.isfinite(y)], 1)
        y_trend = intercept_month + slope_month * x
    else:
        y_trend = y

    fig, ax = plt.subplots(figsize=(11, 5))
    colors = [
        PALETTE["accent"] if anom else PALETTE["secondary"]
        for anom in data.get("es_atipico", [False] * len(data))
    ]
    ax.bar(x, y, color=colors, alpha=0.85, label="Demanda mensual")
    ax.plot(x, y_trend, color=PALETTE["primary"], lw=2, ls="--", label="Tendencia OLS")

    ax.set_xticks(x)
    ax.set_xticklabels(data["periodo"].tolist(), rotation=45, ha="right", fontsize=7)
    ax.set_title(f"Tendencia mensual — Ruta {ruta}")
    ax.set_ylabel("Pasajeros totales")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))

    direction = "crece" if slope > 0.5 else ("decrece" if slope < -0.5 else "es estable")
    ax.set_xlabel(f"La demanda {direction} a razón de {abs(slope * 30):,.0f} pasajeros/mes")
    ax.legend(fontsize=8)

    out = FIGURES_DIR / f"tendencia_mensual_{ruta}.png"
    _save(fig, out)


def plot_acf_pacf(
    autocorr_df: pd.DataFrame,
    ruta: int,
    gran: int,
) -> None:
    """Gráfico ACF y PACF lado a lado."""
    if autocorr_df.empty or "acf_value" not in autocorr_df.columns:
        return

    df = autocorr_df.copy()
    lags = df["lag"].values
    acf_vals = df["acf_value"].values
    pacf_vals = df["pacf_value"].values
    n = int((df["adf_pvalue"].notna().sum() > 0) and df.shape[0])
    signif = 1.96 / np.sqrt(max(n, 100))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)
    for ax, vals, title in zip(axes, [acf_vals, pacf_vals], ["ACF", "PACF"], strict=False):
        ax.bar(
            lags,
            vals,
            color=PALETTE["primary"],
            alpha=0.7,
            width=0.6,
        )
        ax.axhline(signif, color=PALETTE["accent"], ls="--", lw=1, label="±95% conf")
        ax.axhline(-signif, color=PALETTE["accent"], ls="--", lw=1)
        ax.axhline(0, color="#1f2933", lw=0.8)

        # Annotate lags with |ACF| > 0.3
        if title == "ACF":
            for lag, val in zip(lags, vals, strict=False):
                if lag > 0 and abs(val) > 0.3:
                    ax.annotate(
                        str(int(lag)),
                        (lag, val),
                        textcoords="offset points",
                        xytext=(0, 5 if val > 0 else -12),
                        fontsize=7,
                        color=PALETTE["atipico"],
                        ha="center",
                    )

        ax.set_title(f"{title} — Ruta {ruta} | {gran} min")
        ax.set_xlabel("Lag (franjas)")
        ax.set_ylabel("Correlación")
        ax.legend(fontsize=7)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))

    adf_pval = float(df["adf_pvalue"].iloc[0]) if "adf_pvalue" in df.columns else np.nan
    adf_str = f"ADF p={adf_pval:.4f}" if not np.isnan(adf_pval) else "ADF no disponible"
    fig.suptitle(
        f"Autocorrelación — {adf_str} | {'Estacionaria' if adf_pval < 0.05 else 'No estacionaria'}",
        fontsize=11,
    )
    out = FIGURES_DIR / f"acf_pacf_{ruta}_g{gran}min.png"
    _save(fig, out)


def plot_boxplot_tipo_dia(
    ts_df: pd.DataFrame,
    ruta: int,
    gran: int,
) -> None:
    """Boxplot de demanda por tipo de día con outliers marcados."""
    if ts_df.empty or "tipo_dia" not in ts_df.columns:
        return
    data = ts_df.copy()
    if "gap_tipo" in data.columns:
        data = data[data["gap_tipo"] == "operativo"]
    if data.empty:
        return

    order = [
        t
        for t in ["LABORAL", "SABADO", "DOMINGO", "FESTIVO", "FESTIVO_PUENTE"]
        if t in data["tipo_dia"].unique()
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(
        data=data,
        x="tipo_dia",
        y="pasajeros_total",
        hue="tipo_dia",
        order=order,
        hue_order=order,
        palette=dict.fromkeys(order, PALETTE["primary"]),
        legend=False,
        fliersize=3,
        flierprops={"color": PALETTE["atipico"], "alpha": 0.5},
        ax=ax,
    )
    ax.set_title(f"Distribución de demanda por tipo de día — Ruta {ruta} | {gran} min")
    ax.set_xlabel("Tipo de día")
    ax.set_ylabel("Pasajeros por franja")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.tick_params(axis="x", rotation=0)

    out = FIGURES_DIR / f"boxplot_tipo_dia_{ruta}_g{gran}min.png"
    _save(fig, out)


# ---------------------------------------------------------------------------
# Executive summary builder
# ---------------------------------------------------------------------------


def build_executive_summary(eda: TemporalEDA, results: dict) -> str:
    """Construye el resumen ejecutivo como texto formateado."""
    lines: list[str] = []

    def h(title: str) -> None:
        lines.append(f"\n{'=' * 60}")
        lines.append(f"  {title}")
        lines.append("=" * 60)

    def row(label: str, value: str) -> None:
        lines.append(f"  {label:<35} {value}")

    h("RESUMEN EJECUTIVO — EDA TEMPORAL MONTEBELLO")

    # --- Perfil intradía ---
    h("1. HORAS PICO POR RUTA Y TIPO DE DÍA (operativas)")
    intraday_all: dict[tuple[int, int], pd.DataFrame] = results.get("perfil_intraday", {})
    pv_ratios: list[tuple[int, int, str, float]] = []
    for (ruta, gran), idf in intraday_all.items():
        if gran != 60 or idf.empty:
            continue
        for tipo_dia, sub in idf.groupby("tipo_dia"):
            picos = sub.loc[sub["es_pico"], "hora_del_dia"].tolist()
            valles = sub.loc[sub["es_valle"], "hora_del_dia"].tolist()
            ratio = (
                float(sub["ratio_pico_valle"].iloc[0])
                if "ratio_pico_valle" in sub.columns
                else np.nan
            )
            if picos:
                horas_str = ", ".join(f"{int(h):02d}:00" for h in picos)
                row(f"Ruta {ruta} | {tipo_dia} | horas pico", horas_str)
            if valles:
                valles_str = ", ".join(f"{int(v):02d}:00" for v in valles)
                row(f"Ruta {ruta} | {tipo_dia} | horas valle", valles_str)
            if not np.isnan(ratio):
                row(f"Ruta {ruta} | {tipo_dia} | ratio pico/valle", f"{ratio:.2f}x")
                pv_ratios.append((ruta, gran, str(tipo_dia), ratio))

    # --- Perfil semanal ---
    h("2. DÍA DE MAYOR Y MENOR DEMANDA PROMEDIO")
    semanal_all: dict[tuple[int, int], pd.DataFrame] = results.get("perfil_semanal", {})
    for (ruta, gran), sdf in semanal_all.items():
        if gran != 60 or sdf.empty:
            continue
        max_row = sdf.loc[sdf["es_max"]]
        min_row = sdf.loc[sdf["es_min"]]
        if not max_row.empty:
            row(f"Ruta {ruta} | día mayor demanda", str(max_row["nombre_dia"].iloc[0]))
        if not min_row.empty:
            row(f"Ruta {ruta} | día menor demanda", str(min_row["nombre_dia"].iloc[0]))

    # --- Tendencia mensual ---
    h("3. TENDENCIA DE DEMANDA POR RUTA")
    mensual_all: dict[int, pd.DataFrame] = results.get("perfil_mensual", {})
    for ruta, mdf in mensual_all.items():
        mes_data = mdf[mdf["tipo_periodo"] == "mes"]
        if mes_data.empty:
            continue
        slope = float(mes_data["tendencia_slope"].iloc[0])
        monthly_change = slope * 30  # aprox pasajeros/mes
        if abs(slope) < 0.5:
            direction = "ESTABLE"
        elif slope > 0:
            direction = f"CRECIENTE (+{monthly_change:,.0f} pasajeros/mes)"
        else:
            direction = f"DECRECIENTE ({monthly_change:,.0f} pasajeros/mes)"
        row(f"Ruta {ruta} | tendencia", direction)
        n_atipicos_mes = int(mes_data["es_atipico"].sum())
        if n_atipicos_mes:
            atipicos_str = ", ".join(mes_data.loc[mes_data["es_atipico"], "periodo"].tolist())
            row(f"Ruta {ruta} | meses atípicos", atipicos_str)

    # --- Autocorrelación ---
    h("4. ESTACIONARIEDAD Y LOOKBACK RECOMENDADO")
    autocorr_all: dict[tuple[int, int], pd.DataFrame] = results.get("autocorrelacion", {})
    for (ruta, gran), adf in autocorr_all.items():
        if adf.empty:
            continue
        adf_pval = float(adf["adf_pvalue"].iloc[0])
        adf_stat_val = float(adf["adf_statistic"].iloc[0])
        estacionaria = bool(adf["adf_is_stationary"].iloc[0])
        row(
            f"Ruta {ruta} | {gran}min | ADF statistic",
            f"{adf_stat_val:.4f}  p={adf_pval:.4f}",
        )
        row(
            f"Ruta {ruta} | {gran}min | ¿Estacionaria?",
            "SÍ (p < 0.05)" if estacionaria else "NO (p >= 0.05)",
        )
        lags_relevantes = adf.loc[adf["lags_relevantes_acf"] & (adf["lag"] > 0), "lag"].tolist()
        if lags_relevantes:
            max_lag = max(lags_relevantes)
            row(
                f"Ruta {ruta} | {gran}min | lags ACF > 0.3",
                f"{lags_relevantes[:8]!s}",
            )
            row(
                f"Ruta {ruta} | {gran}min | lookback recomendado",
                f"{max_lag} franjas ({max_lag * gran // 60:.0f} h aprox.)",
            )

    # --- Atípicos ---
    h("5. VALORES ATÍPICOS")
    atipicos_all: dict[tuple[int, int], pd.DataFrame] = results.get("atipicos", {})
    for (ruta, gran), atdf in atipicos_all.items():
        if atdf.empty:
            pct = 0.0
        else:
            pct = float(atdf["pct_atipicos"].iloc[0]) if "pct_atipicos" in atdf.columns else 0.0
        row(f"Ruta {ruta} | {gran}min | % atípicos operativos", f"{pct:.2f}%")

    # --- Correlación de features ---
    h("6. TOP-10 FEATURES MÁS CORRELACIONADAS CON PASAJEROS")
    corr_df: pd.DataFrame = results.get("correlacion_features", pd.DataFrame())
    if not corr_df.empty:
        for _, r in corr_df.head(10).iterrows():
            row(
                f"  #{int(r['rank'])} {str(r['feature'])[:32]}",
                f"{r['correlacion_spearman']:+.3f}",
            )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _set_theme()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Iniciando EDA temporal completo...")
    eda = TemporalEDA()
    results = eda.run_all()

    # ---- Generate static figures ----
    ts_dir = PROJECT_ROOT / "data" / "processed" / "time_series"
    import re as _re

    ts_pattern = _re.compile(r"ts_ruta(\d+)_g(\d+)min")

    ts_loaded: dict[tuple[int, int], pd.DataFrame] = {}
    for path in sorted(ts_dir.glob("ts_ruta*_g*min.parquet")):
        m = ts_pattern.match(path.stem)
        if not m:
            continue
        ruta_id, gran_id = int(m.group(1)), int(m.group(2))
        df_ts = pd.read_parquet(path)
        df_ts["timestamp"] = pd.to_datetime(df_ts["timestamp"], errors="coerce")
        ts_loaded[(ruta_id, gran_id)] = df_ts

    intraday_results: dict = results.get("perfil_intraday", {})
    mensual_results: dict = results.get("perfil_mensual", {})
    autocorr_results: dict = results.get("autocorrelacion", {})

    for (ruta, gran), idf in intraday_results.items():
        plot_curva_intraday(idf, ruta, gran)

    for (ruta, gran), ts_df in ts_loaded.items():
        plot_heatmap_hora_dia(ts_df, ruta, gran)
        plot_boxplot_tipo_dia(ts_df, ruta, gran)

    for ruta, mdf in mensual_results.items():
        plot_tendencia_mensual(mdf, ruta)

    for (ruta, gran), adf in autocorr_results.items():
        plot_acf_pacf(adf, ruta, gran)

    # ---- Print executive summary ----
    summary = build_executive_summary(eda, results)
    _save_summary(summary)
    print(summary)


if __name__ == "__main__":
    main()
