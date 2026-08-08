"""
scripts/build_baseline_consolidado.py
======================================
Construye el reporte de baseline operativo consolidado leyendo los
CSVs generados por los módulos de análisis ya ejecutados:

  - headway_summary.csv                    (HeadwayAnalyzer)
  - fleet_availability_summary.csv         (FleetAvailabilityAnalyzer)
  - productivity_summary.csv               (ProductivityAnalyzer)
  - diagnostico_flota_comparacion.csv      (diagnostico_reduccion_flota)
  - diagnostico_flota_mensual.csv          (diagnostico_reduccion_flota)

Integra los cuatro hallazgos en una narrativa coherente y genera
reports/tables/baseline/BASELINE_REPORT.txt

Si algún CSV falta, el script lo reporta y omite esa sección sin fallar.

Uso:
    python scripts/build_baseline_consolidado.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "reports/tables/baseline"


def _load(nombre: str) -> pd.DataFrame | None:
    path = BASE / nombre
    if not path.exists():
        logger.warning("CSV no encontrado (sección omitida): %s", nombre)
        return None
    return pd.read_csv(path)


def _val(df: pd.DataFrame, ruta: int, col: str, fmt: str = "{:.2f}") -> str:
    if df is None or "FK_RUTA" not in df.columns:
        return "N/D"
    row = df[df["FK_RUTA"] == ruta]
    if row.empty or col not in df.columns:
        return "N/D"
    v = row.iloc[0][col]
    try:
        return fmt.format(float(v))
    except (ValueError, TypeError):
        return str(v)


def build_report() -> str:
    hw = _load("headway_summary.csv")
    fleet = _load("fleet_availability_summary.csv")
    prod = _load("productivity_summary.csv")
    comp = _load("diagnostico_flota_comparacion.csv")

    sep = "─" * 65
    lineas = [
        "=" * 65,
        "BASELINE OPERATIVO CONSOLIDADO — EMPRESA MONTEBELLO",
        "Período: Abril 2024 – Mayo 2026 | Rutas 1 y 3",
        "Dataset: 105.490 despachos model-ready | Retención ETL: 99.85%",
        "=" * 65,
        "",
        "RESUMEN EJECUTIVO",
        "-----------------",
        "El sistema de despacho empírico de Montebello presenta",
        "irregularidad de servicio (CV headway IRREGULAR) en un",
        "contexto de reducción progresiva de flota por vehículos",
        "que cumplen su vida útil sin reposición. La productividad",
        "por despacho se mantiene estable, lo que confirma que la",
        "demanda está intacta: el problema es de OFERTA, no de",
        "demanda. El modelo predictivo busca optimizar la",
        "distribución temporal de una flota menor para maximizar",
        "la cobertura de la demanda existente.",
        "",
    ]

    # ── SECCIÓN 1 — CV HEADWAY ──────────────────────────────────────────────
    if hw is not None:
        lineas += [
            sep,
            "1. REGULARIDAD DEL SERVICIO — CV HEADWAY (KPI PRINCIPAL)",
            sep,
            f"  {'Indicador':<34}{'Ruta 1':>10}{'Ruta 3':>10}",
            "  " + "─" * 54,
            f"  {'Headway promedio (min)':<34}"
            f"{_val(hw, 1, 'headway_mean'):>10}{_val(hw, 3, 'headway_mean'):>10}",
            f"  {'Desviación estándar (min)':<34}"
            f"{_val(hw, 1, 'headway_std'):>10}{_val(hw, 3, 'headway_std'):>10}",
            f"  {'CV headway':<34}"
            f"{_val(hw, 1, 'cv_headway', '{:.3f}'):>10}{_val(hw, 3, 'cv_headway', '{:.3f}'):>10}",
            f"  {'Headway p95 (min)':<34}"
            f"{_val(hw, 1, 'headway_p95'):>10}{_val(hw, 3, 'headway_p95'):>10}",
            f"  {'Bunching < 3 min (%)':<34}"
            f"{_val(hw, 1, 'bunching_pct'):>10}{_val(hw, 3, 'bunching_pct'):>10}",
            f"  {'Espera excesiva > 30 min (%)':<34}"
            f"{_val(hw, 1, 'excess_wait_pct'):>10}{_val(hw, 3, 'excess_wait_pct'):>10}",
            "",
            "  Clasificación según Henderson, Kwong & Adkins (1991,",
            "  TRR 1297, Tabla 1, p.5): ambas rutas IRREGULARES",
            "  (Cv 0.72-0.77 → Cases 11-13, Regularity Index R ≈ 0.61).",
            "",
            "  NOTA: El load factor clásico no aplica a Montebello.",
            "  Como sistema sin paradas fijas, PASAJEROS registra el",
            "  total acumulado de abordajes por recorrido, no pasajeros",
            "  simultáneos a bordo (Wang et al., 2021).",
            "",
        ]

    # ── SECCIÓN 2 — REDUCCIÓN DE FLOTA ──────────────────────────────────────
    if comp is not None:
        lineas += [
            sep,
            "2. REDUCCIÓN PROGRESIVA DE FLOTA (HALLAZGO ESTRUCTURAL)",
            sep,
            "  Causa: vehículos que cumplen vida útil sin reposición.",
            "",
            f"  {'Indicador':<32}{'Inicio':>10}{'Fin':>10}{'Δ%':>8}",
            "  " + "─" * 58,
        ]
        for _, r in comp.iterrows():
            ind = str(r["indicador"])[:32]
            lineas.append(
                f"  {ind:<32}{r['primer_mes']!s:>10}"
                f"{r['ultimo_mes']!s:>10}{r['variacion_pct']!s:>8}"
            )
        lineas += [
            "",
            "  HALLAZGO CLAVE: La productividad por despacho cae solo",
            "  ~2.5% mientras los pasajeros totales caen ~41%. Esto",
            "  confirma que la demanda está intacta — la caída se debe",
            "  a MENOS DESPACHOS por reducción de flota, no a menos",
            "  demanda por despacho.",
            "",
        ]

    # ── SECCIÓN 3 — PRODUCTIVIDAD ESTABLE ───────────────────────────────────
    if prod is not None:
        lineas += [
            sep,
            "3. PRODUCTIVIDAD POR DESPACHO (DEMANDA INTACTA)",
            sep,
            f"  {'Indicador':<34}{'Ruta 1':>10}{'Ruta 3':>10}",
            "  " + "─" * 54,
            f"  {'Productividad media (pas/desp)':<34}"
            f"{_val(prod, 1, 'productividad_promedio_bruta'):>10}"
            f"{_val(prod, 3, 'productividad_promedio_bruta'):>10}",
            f"  {'Desviación estándar':<34}"
            f"{_val(prod, 1, 'productividad_std'):>10}"
            f"{_val(prod, 3, 'productividad_std'):>10}",
            f"  {'Tendencia (pas/mes)':<34}"
            f"{_val(prod, 1, 'tendencia_slope_mensual_est', '{:.3f}'):>10}"
            f"{_val(prod, 3, 'tendencia_slope_mensual_est', '{:.3f}'):>10}",
            "",
            "  La productividad por despacho es ESTABLE en ~44-48",
            "  pasajeros, validando que cada despacho que sale captura",
            "  la demanda esperada. Esto desliga la productividad del",
            "  modelo predictivo y permite usarla como multiplicador",
            "  honesto para estimar demanda recuperable en Fase 4.",
            "",
        ]

    # ── SECCIÓN 4 — DISPONIBILIDAD DE FLOTA ─────────────────────────────────
    if fleet is not None:
        f = fleet.iloc[0]
        lineas += [
            sep,
            "4. DISPONIBILIDAD DE FLOTA EN PATIO",
            sep,
            f"  Análisis sobre {int(f.get('n_dias_analizados', 0))} días laborales representativos.",
            "",
            f"  % tiempo patio vacío - pico mañana (05-09h) : {f.get('pct_vacio_pico_manana', 'N/D')}%",
            f"  % tiempo patio vacío - pico tarde (14-16h)  : {f.get('pct_vacio_pico_tarde', 'N/D')}%",
            f"  % tiempo patio vacío - cierre (16h30-17h30) : {f.get('pct_vacio_cierre', 'N/D')}%",
            "",
            f"  Headways largos explicados por flota (pico mañana): "
            f"{f.get('pct_largos_pico_manana', 'N/D')}%",
            f"  Headways largos por otras causas no de flota     : "
            f"{f.get('pct_largos_otros', 'N/D')}%",
            "",
            "  La limitación de flota en pico matutino es estructural",
            "  (primer recorrido ~161 min impide retornos tempranos),",
            "  pero explica solo una fracción de la irregularidad. El",
            "  mayor potencial del modelo está en el RITMO de despacho.",
            "",
        ]

    # ── CIERRE — META Y METODOLOGÍA ─────────────────────────────────────────
    lineas += [
        "=" * 65,
        "MEDICIÓN DE LA MEJORA (FASE 4)",
        "=" * 65,
        "La mejora se demostrará por SIMULACIÓN RETROSPECTIVA:",
        "comparar el CV headway del despacho empírico real contra",
        "el CV headway que se habría obtenido si el despachador",
        "hubiera seguido las recomendaciones del modelo predictivo,",
        "sobre el período de prueba.",
        "",
        "Indicador de demanda recuperable (Fase 4):",
        "  demanda_recuperable = (despachos_recomendados −",
        "  despachos_reales) × productividad_estable (~46 pas/desp)",
        "",
        "La simulación asume adopción total de las recomendaciones",
        "como límite superior de mejora alcanzable. El modelo no",
        "revierte la tendencia estructural de reducción de flota",
        "(exógena), sino que mitiga su impacto operativo.",
        "",
        "=" * 65,
        "REFERENCIA BIBLIOGRÁFICA",
        "=" * 65,
        "  Henderson, G., Kwong, P., & Adkins, H. (1991). Regularity",
        "  Indices for Evaluating Transit Performance. Transportation",
        "  Research Record, 1297, pp. 3-9.",
        "",
        "  Wang et al. (2021) — sobre conteo de abordajes en sistemas",
        "  de transporte sin paradas fijas.",
        "",
        "=" * 65,
        "Generado por: python scripts/build_baseline_consolidado.py",
        "=" * 65,
    ]

    return "\n".join(lineas)


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    texto = build_report()
    out = BASE / "BASELINE_REPORT.txt"
    out.write_text(texto, encoding="utf-8")
    logger.info("✅ Reporte consolidado generado → %s", out)
    print("\n" + texto)


if __name__ == "__main__":
    main()
