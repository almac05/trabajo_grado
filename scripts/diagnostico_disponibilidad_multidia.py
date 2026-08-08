"""
scripts/diagnostico_disponibilidad_multidia.py
=================================================
Repite el diagnóstico de disponibilidad de flota en patio para
varios días (laborales, distintas semanas) y verifica si el
patrón observado se mantiene consistente:

  - Disponibilidad de flota positiva durante horas pico (05h-09h, 14h-16h)
  - Caída progresiva de disponibilidad hacia el cierre (16h30-17h30)
  - Coincidencia entre patio vacío y headways largos, concentrada
    en el cierre de jornada

Este script NO modifica ningún dato. Solo imprime resultados
y genera un CSV consolidado para inspección.

Uso:
    python scripts/diagnostico_disponibilidad_multidia.py
    python scripts/diagnostico_disponibilidad_multidia.py --n-dias 5
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)

ROOT = Path(__file__).resolve().parent.parent
MR_PATH = ROOT / "data/processed/model_ready/despachos_model_ready.parquet"
OUT_DIR = ROOT / "reports/tables/baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Franjas horarias de interés (según hallazgo del diagnóstico anterior)
PICO_MANANA = (5, 9)
PICO_TARDE = (14, 16)
CIERRE = (16.5, 17.5)


def reconstruir_timeline(dia_df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruye intervalos EN_RUTA / EN_PATIO por vehículo para un día."""
    dia_df = dia_df.sort_values(["PLACA", "HORA_INICIAL_REAL"]).reset_index(drop=True)
    dia_df["siguiente_inicio"] = dia_df.groupby("PLACA")["HORA_INICIAL_REAL"].shift(-1)

    intervalos = []
    for _, row in dia_df.iterrows():
        intervalos.append(
            {
                "PLACA": row["PLACA"],
                "estado": "EN_RUTA",
                "inicio": row["HORA_INICIAL_REAL"],
                "fin": row["HORA_FIN_FINAL"],
            }
        )
        if pd.notna(row["siguiente_inicio"]):
            intervalos.append(
                {
                    "PLACA": row["PLACA"],
                    "estado": "EN_PATIO",
                    "inicio": row["HORA_FIN_FINAL"],
                    "fin": row["siguiente_inicio"],
                }
            )

    timeline = pd.DataFrame(intervalos)
    return timeline[timeline["inicio"] < timeline["fin"]].copy()


def calcular_disponibilidad(timeline: pd.DataFrame, fecha_dia, freq="5min") -> pd.DataFrame:
    """Cuenta vehículos en patio por franja de tiempo a lo largo del día."""
    inicio_dia = pd.Timestamp(fecha_dia) + pd.Timedelta(hours=4)
    fin_dia = pd.Timestamp(fecha_dia) + pd.Timedelta(hours=20)
    minutos = pd.date_range(inicio_dia, fin_dia, freq=freq)

    patio = timeline[timeline["estado"] == "EN_PATIO"]
    disponibilidad = []
    for t in minutos:
        en_patio = patio[(patio["inicio"] <= t) & (patio["fin"] > t)]
        disponibilidad.append({"timestamp": t, "vehiculos_en_patio": len(en_patio)})

    return pd.DataFrame(disponibilidad)


def resumen_por_franja(disp_df: pd.DataFrame, fecha_dia) -> dict:
    """Calcula disponibilidad promedio en cada franja de interés."""
    disp_df = disp_df.copy()
    disp_df["hora"] = disp_df["timestamp"].dt.hour + disp_df["timestamp"].dt.minute / 60

    def _avg_en_rango(lo, hi):
        sub = disp_df[(disp_df["hora"] >= lo) & (disp_df["hora"] < hi)]
        return round(sub["vehiculos_en_patio"].mean(), 2) if len(sub) else np.nan

    def _pct_vacio_en_rango(lo, hi):
        sub = disp_df[(disp_df["hora"] >= lo) & (disp_df["hora"] < hi)]
        return round(100 * (sub["vehiculos_en_patio"] == 0).mean(), 1) if len(sub) else np.nan

    return {
        "fecha": fecha_dia,
        "disp_pico_manana": _avg_en_rango(*PICO_MANANA),
        "disp_pico_tarde": _avg_en_rango(*PICO_TARDE),
        "disp_cierre": _avg_en_rango(*CIERRE),
        "pct_vacio_pico_manana": _pct_vacio_en_rango(*PICO_MANANA),
        "pct_vacio_pico_tarde": _pct_vacio_en_rango(*PICO_TARDE),
        "pct_vacio_cierre": _pct_vacio_en_rango(*CIERRE),
    }


def headways_largos_por_franja(dia_df: pd.DataFrame, umbral_min: float = 15.0) -> dict:
    """Cuenta headways largos (>umbral) por franja horaria, ambas rutas."""
    resultado = {
        "headways_largos_pico_manana": 0,
        "headways_largos_pico_tarde": 0,
        "headways_largos_cierre": 0,
        "headways_largos_otros": 0,
    }
    for ruta in [1, 3]:
        ruta_df = dia_df[dia_df["FK_RUTA"] == ruta].sort_values("HORA_INICIAL_REAL").copy()
        ruta_df["headway_min"] = ruta_df["HORA_INICIAL_REAL"].diff().dt.total_seconds() / 60
        ruta_df["hora"] = (
            ruta_df["HORA_INICIAL_REAL"].dt.hour + ruta_df["HORA_INICIAL_REAL"].dt.minute / 60
        )
        largos = ruta_df[ruta_df["headway_min"] > umbral_min]
        for _, row in largos.iterrows():
            h = row["hora"]
            if PICO_MANANA[0] <= h < PICO_MANANA[1]:
                resultado["headways_largos_pico_manana"] += 1
            elif PICO_TARDE[0] <= h < PICO_TARDE[1]:
                resultado["headways_largos_pico_tarde"] += 1
            elif CIERRE[0] <= h < CIERRE[1]:
                resultado["headways_largos_cierre"] += 1
            else:
                resultado["headways_largos_otros"] += 1
    return resultado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-dias", type=int, default=8, help="Número de días laborales a analizar")
    args = parser.parse_args()

    print("=" * 70)
    print("DIAGNÓSTICO MULTI-DÍA — Consistencia de disponibilidad de flota")
    print("=" * 70)

    df = pd.read_parquet(MR_PATH)
    df = df[df["MODEL_READY_OK"].eq(True) & df["HORA_FIN_FINAL"].notna()].copy()
    df["HORA_INICIAL_REAL"] = pd.to_datetime(df["HORA_INICIAL_REAL"])
    df["HORA_FIN_FINAL"] = pd.to_datetime(df["HORA_FIN_FINAL"])
    df["FECHA_INICIAL"] = pd.to_datetime(df["FECHA_INICIAL"])
    df["fecha_dia"] = df["FECHA_INICIAL"].dt.date
    df["dia_semana"] = df["FECHA_INICIAL"].dt.dayofweek  # 0=lunes

    # Seleccionar días laborales (lunes-viernes) con volumen robusto,
    # espaciados en el tiempo para evitar sesgo de una sola semana
    conteo_dia = df.groupby("fecha_dia").size()
    dias_laborales = df[df["dia_semana"] < 5]["fecha_dia"].unique()
    dias_validos = [
        d
        for d in sorted(dias_laborales)
        if conteo_dia.get(d, 0) >= 150  # mínimo de despachos para ser representativo
    ]

    # Tomar muestra espaciada uniformemente a lo largo del período
    paso = max(len(dias_validos) // args.n_dias, 1)
    dias_muestra = dias_validos[::paso][: args.n_dias]

    print(f"\nDías laborales válidos disponibles: {len(dias_validos)}")
    print(f"Días seleccionados para el análisis ({len(dias_muestra)}):")
    for d in dias_muestra:
        print(f"  - {d} ({conteo_dia[d]} despachos)")

    resultados = []
    for dia_ejemplo in dias_muestra:
        dia_df = df[df["fecha_dia"] == dia_ejemplo].copy()
        timeline = reconstruir_timeline(dia_df)
        disp_df = calcular_disponibilidad(timeline, dia_ejemplo)

        fila = resumen_por_franja(disp_df, dia_ejemplo)
        fila.update(headways_largos_por_franja(dia_df))
        fila["n_despachos"] = len(dia_df)
        fila["n_vehiculos"] = dia_df["PLACA"].nunique()
        resultados.append(fila)

    resultado_df = pd.DataFrame(resultados)

    print("\n" + "─" * 70)
    print("RESUMEN CONSOLIDADO — DISPONIBILIDAD PROMEDIO POR FRANJA")
    print("─" * 70)
    print(
        resultado_df[
            [
                "fecha",
                "n_despachos",
                "n_vehiculos",
                "disp_pico_manana",
                "disp_pico_tarde",
                "disp_cierre",
                "pct_vacio_pico_manana",
                "pct_vacio_pico_tarde",
                "pct_vacio_cierre",
            ]
        ].to_string(index=False)
    )

    print("\n" + "─" * 70)
    print("RESUMEN CONSOLIDADO — HEADWAYS LARGOS (>15 min) POR FRANJA")
    print("─" * 70)
    print(
        resultado_df[
            [
                "fecha",
                "headways_largos_pico_manana",
                "headways_largos_pico_tarde",
                "headways_largos_cierre",
                "headways_largos_otros",
            ]
        ].to_string(index=False)
    )

    # ── Estadística agregada final ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CONCLUSIÓN ESTADÍSTICA AGREGADA (todos los días analizados)")
    print("=" * 70)

    total_largos_cierre = resultado_df["headways_largos_cierre"].sum()
    total_largos_pico_m = resultado_df["headways_largos_pico_manana"].sum()
    total_largos_pico_t = resultado_df["headways_largos_pico_tarde"].sum()
    total_largos_otros = resultado_df["headways_largos_otros"].sum()
    total_largos = (
        total_largos_cierre + total_largos_pico_m + total_largos_pico_t + total_largos_otros
    )

    print(f"\nTotal headways largos (>15 min) detectados: {total_largos}")
    if total_largos > 0:
        print(
            f"  En pico mañana (05h-09h)  : {total_largos_pico_m} "
            f"({100 * total_largos_pico_m / total_largos:.1f}%)"
        )
        print(
            f"  En pico tarde (14h-16h)   : {total_largos_pico_t} "
            f"({100 * total_largos_pico_t / total_largos:.1f}%)"
        )
        print(
            f"  En cierre (16h30-17h30)  : {total_largos_cierre} "
            f"({100 * total_largos_cierre / total_largos:.1f}%)"
        )
        print(
            f"  En otras franjas          : {total_largos_otros} "
            f"({100 * total_largos_otros / total_largos:.1f}%)"
        )

    print("\nDisponibilidad promedio de flota (todos los días):")
    print(f"  Pico mañana : {resultado_df['disp_pico_manana'].mean():.2f} vehículos")
    print(f"  Pico tarde  : {resultado_df['disp_pico_tarde'].mean():.2f} vehículos")
    print(f"  Cierre      : {resultado_df['disp_cierre'].mean():.2f} vehículos")

    print("\n% de tiempo con patio vacío (promedio todos los días):")
    print(f"  Pico mañana : {resultado_df['pct_vacio_pico_manana'].mean():.1f}%")
    print(f"  Pico tarde  : {resultado_df['pct_vacio_pico_tarde'].mean():.1f}%")
    print(f"  Cierre      : {resultado_df['pct_vacio_cierre'].mean():.1f}%")

    # ── Guardar resultado consolidado ───────────────────────────────────────
    out_path = OUT_DIR / "diagnostico_disponibilidad_multidia.csv"
    resultado_df.to_csv(out_path, index=False)
    print(f"\nResultado consolidado guardado en: {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
