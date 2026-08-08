"""
scripts/build_baseline.py
Genera el reporte de baseline operativo para la tesis.

Uso:
    python scripts/build_baseline.py

Salida: reports/tables/baseline/
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_baseline")

ROOT = Path(__file__).resolve().parent.parent
MR_PATH = ROOT / "data/processed/model_ready/despachos_model_ready.parquet"
OUTPUT_DIR = ROOT / "reports/tables/baseline"


def load_model_ready() -> pd.DataFrame:
    if not MR_PATH.exists():
        logger.error("No encontrado: %s", MR_PATH)
        sys.exit(1)
    df = pd.read_parquet(MR_PATH)
    logger.info("model_ready: %d filas cargadas", len(df))
    return df


def write_report(
    hw_summary: pd.DataFrame,
    df_mr: pd.DataFrame,
    output_dir: Path,
) -> None:
    sep = "─" * 65

    pas_promedio = df_mr["PASAJEROS"].mean()
    capacidad_nominal = 28
    tasa_rotacion = round(pas_promedio / capacidad_nominal, 2)
    total_pasajeros = int(df_mr["PASAJEROS"].sum())
    duracion_promedio = round(df_mr["DURACION_MIN_FINAL"].mean(), 2)
    recorridos_completos = round(100 * df_mr["RECORRIDO_COMPLETO"].sum() / len(df_mr), 2)
    total_despachos = len(df_mr)
    registros_brutos = 105644
    retencion = round(100 * total_despachos / registros_brutos, 2)

    def _val(df, ruta, col):
        row = df[df["FK_RUTA"] == ruta]
        if row.empty or col not in df.columns:
            return "N/D"
        v = row.iloc[0][col]
        return f"{v:.2f}" if isinstance(v, float) else str(v)

    lines = [
        "=" * 65,
        "BASELINE OPERATIVO — EMPRESA MONTEBELLO",
        "Período: Abril 2024 – Mayo 2026 | Rutas 1 y 3",
        "=" * 65,
        "",
        "Indicadores del sistema actual de despacho empírico de",
        "Transportes Montebello. La mejora al cierre del proyecto",
        "se medirá como la reducción del CV headway mediante",
        "simulación retrospectiva con el modelo predictivo.",
        "",
        "NOTA METODOLÓGICA",
        "-" * 17,
        "Montebello opera como sistema semiformalizado sin paradas",
        "fijas. PASAJEROS registra el total acumulado de abordajes",
        "por recorrido (~161 min), no pasajeros simultáneos a bordo.",
        "El load factor clásico es conceptualmente incorrecto para",
        "este sistema y ha sido excluido del baseline.",
        "",
        sep,
        "REGULARIDAD DEL SERVICIO — CV HEADWAY",
        sep,
        f"  {'Indicador':<36}{'Ruta 1':>10}{'Ruta 3':>10}",
        "  " + "─" * 56,
    ]

    for label, col in [
        ("Headway promedio (min)", "headway_mean"),
        ("Headway mediano p50 (min)", "headway_p50"),
        ("Desviación estándar (min)", "headway_std"),
        ("CV headway  ← KPI principal", "cv_headway"),
        ("Headway p95 (min)", "headway_p95"),
        ("Bunching < 3 min (%)", "bunching_pct"),
        ("Espera excesiva > 30min (%)", "excess_wait_pct"),
    ]:
        lines.append(f"  {label:<36}{_val(hw_summary, 1, col):>10}{_val(hw_summary, 3, col):>10}")

    lines.append("")
    for ruta in [1, 3]:
        row = hw_summary[hw_summary["FK_RUTA"] == ruta]
        if row.empty:
            continue
        cv = row.iloc[0]["cv_headway"]
        if cv > 0.68:
            zona = "IRREGULAR (Cases 1–10, R ≈ 0.50–0.61)"
        elif cv > 0.37:
            zona = "MODERADO  (Cases 11–15, R ≈ 0.61–0.81)"
        else:
            zona = "REGULAR   (Cases 16–20, R ≈ 0.81–0.96)"
        lines.append(f"  Ruta {ruta}: CV = {cv:.3f}  →  {zona}")

    lines += [
        "",
        sep,
        "INDICADOR COMPLEMENTARIO — PRODUCTIVIDAD DEL VEHÍCULO",
        sep,
        "  Sistema sin paradas fijas → tasa de rotación del vehículo:",
        "",
        "  tasa_rotacion = pasajeros_promedio / capacidad_nominal",
        f"                = {pas_promedio:.2f} / {capacidad_nominal}",
        f"                = {tasa_rotacion} rotaciones por recorrido",
        "",
        "  Interpretación: cada asiento fue ocupado en promedio por",
        f"  {tasa_rotacion} pasajeros distintos en un recorrido de",
        f"  ~{duracion_promedio} min. Valor razonable para ascenso/",
        "  descenso libre en recorridos de larga duración.",
        "",
        f"  Total pasajeros (Abr 2024–May 2026) : {total_pasajeros:,}",
        f"  Pasajeros promedio por despacho      : {pas_promedio:.2f}",
        f"  Duración promedio recorrido (min)    : {duracion_promedio}",
        f"  Recorridos COMPLETO (%)              : {recorridos_completos}",
        "",
        sep,
        "CALIDAD DEL PIPELINE ETL",
        sep,
        f"  Despachos model-ready                : {total_despachos:,}",
        f"  Registros brutos de entrada          : {registros_brutos:,}",
        f"  Tasa de retención                    : {retencion}%",
        "  flag_hf_nula (hora final ausente)    : 14.497 (13.72%)",
        "  qc_soft_fail / qc_any_flag           : 15.767 registros",
        "  flag_duracion_excesiva               :    912 registros",
        "  flag_pasajeros_absurdos              :    483 registros",
        "",
        "=" * 65,
        "REFERENCIA BIBLIOGRÁFICA",
        "=" * 65,
        "  Henderson, G., Kwong, P., & Adkins, H. (1991).",
        "  Regularity Indices for Evaluating Transit Performance.",
        "  Transportation Research Record, 1297, pp. 3-9.",
        "",
        "  Definición CV headway (p. 5):",
        "    Cv = std(headways) / mean(headways)",
        "",
        "  Escala empírica (Tabla 1, p. 5):",
        "    Cv < 0.37    → Regular      (Cases 16-20, R ≈ 0.81-0.96)",
        "    Cv 0.37-0.68 → Moderado     (Cases 11-15, R ≈ 0.61-0.81)",
        "    Cv > 0.68    → Irregular    (Cases  1-10, R ≈ 0.34-0.61)",
        "",
        "  Montebello R1 (Cv=0.722) y R3 (Cv=0.774): IRREGULAR.",
        "",
        "=" * 65,
        "Generado por: python scripts/build_baseline.py",
        "=" * 65,
    ]

    path = output_dir / "BASELINE_REPORT.txt"
    text = "\n".join(lines)
    path.write_text(text, encoding="utf-8")
    logger.info("Reporte → %s", path)
    try:
        print("\n" + text)
    except UnicodeEncodeError:
        safe = text.encode(sys.stdout.encoding or "ascii", errors="replace").decode(
            sys.stdout.encoding or "ascii", errors="replace"
        )
        print("\n" + safe)


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera el reporte de baseline operativo.")
    ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "src"))

    from proyecto_grado.analytics.headway import HeadwayAnalyzer

    logger.info("── Calculando headway baseline ──")
    df_mr = load_model_ready()
    hw_analyzer = HeadwayAnalyzer(df_mr)
    hw_analyzer.save(OUTPUT_DIR)
    hw_summary = hw_analyzer.summary()

    write_report(hw_summary, df_mr, OUTPUT_DIR)
    logger.info("✅ Baseline completado → %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
