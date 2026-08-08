"""
scripts/diagnostico_reduccion_flota.py
========================================
Verifica empíricamente la hipótesis de reducción progresiva de
la flota: vehículos que cumplen su tiempo de vida útil sin ser
reemplazados.

Genera tres análisis:
  1. Flota activa por mes (PLACAs únicas que operaron)
  2. Despachos totales por mes
  3. Productividad mensual (pasajeros/despacho)
  4. Vehículos "retirados" — su último mes de operación

Este script NO modifica datos. Imprime resultados y guarda CSVs
para inspección.

Uso:
    python scripts/diagnostico_reduccion_flota.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)

ROOT = Path(__file__).resolve().parent.parent
MR_PATH = ROOT / "data/processed/model_ready/despachos_model_ready.parquet"
OUT_DIR = ROOT / "reports/tables/baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("DIAGNÓSTICO — Reducción progresiva de flota operativa")
print("=" * 70)

df = pd.read_parquet(MR_PATH)
df = df[df["MODEL_READY_OK"].eq(True)].copy()
df["FECHA_INICIAL"] = pd.to_datetime(df["FECHA_INICIAL"])
df["mes"] = df["FECHA_INICIAL"].dt.to_period("M").dt.start_time

print(f"\nTotal despachos elegibles: {len(df):,}")
print(f"Total vehículos únicos en el período: {df['PLACA'].nunique()}")
print(f"Período: {df['FECHA_INICIAL'].min().date()} a {df['FECHA_INICIAL'].max().date()}")

# ── 1. Flota activa por mes ────────────────────────────────────────────────
print("\n" + "─" * 70)
print("1. FLOTA ACTIVA POR MES (PLACAs únicas que operaron)")
print("─" * 70)

flota_mensual = (
    df.groupby("mes")
    .agg(
        vehiculos_activos=("PLACA", "nunique"),
        despachos_total=("PASAJEROS", "count"),
        pasajeros_total=("PASAJEROS", "sum"),
    )
    .reset_index()
)
flota_mensual["productividad_por_despacho"] = (
    flota_mensual["pasajeros_total"] / flota_mensual["despachos_total"]
).round(2)
flota_mensual["despachos_por_vehiculo"] = (
    flota_mensual["despachos_total"] / flota_mensual["vehiculos_activos"]
).round(2)

print(flota_mensual.to_string(index=False))

# ── 2. Variación inicio vs fin del período ─────────────────────────────────
print("\n" + "─" * 70)
print("2. COMPARACIÓN INICIO vs FIN DEL PERÍODO")
print("─" * 70)

# Excluir primer y último mes (suelen ser parciales)
flota_completos = flota_mensual.iloc[1:-1].copy()

primer_mes = flota_completos.iloc[0]
ultimo_mes = flota_completos.iloc[-1]

comparacion = pd.DataFrame(
    [
        {
            "indicador": "Vehículos activos",
            "primer_mes": int(primer_mes["vehiculos_activos"]),
            "ultimo_mes": int(ultimo_mes["vehiculos_activos"]),
            "variacion_absoluta": int(
                ultimo_mes["vehiculos_activos"] - primer_mes["vehiculos_activos"]
            ),
            "variacion_pct": round(
                100
                * (ultimo_mes["vehiculos_activos"] - primer_mes["vehiculos_activos"])
                / primer_mes["vehiculos_activos"],
                1,
            ),
        },
        {
            "indicador": "Despachos totales",
            "primer_mes": int(primer_mes["despachos_total"]),
            "ultimo_mes": int(ultimo_mes["despachos_total"]),
            "variacion_absoluta": int(
                ultimo_mes["despachos_total"] - primer_mes["despachos_total"]
            ),
            "variacion_pct": round(
                100
                * (ultimo_mes["despachos_total"] - primer_mes["despachos_total"])
                / primer_mes["despachos_total"],
                1,
            ),
        },
        {
            "indicador": "Pasajeros totales",
            "primer_mes": int(primer_mes["pasajeros_total"]),
            "ultimo_mes": int(ultimo_mes["pasajeros_total"]),
            "variacion_absoluta": int(
                ultimo_mes["pasajeros_total"] - primer_mes["pasajeros_total"]
            ),
            "variacion_pct": round(
                100
                * (ultimo_mes["pasajeros_total"] - primer_mes["pasajeros_total"])
                / primer_mes["pasajeros_total"],
                1,
            ),
        },
        {
            "indicador": "Productividad pas/despacho",
            "primer_mes": primer_mes["productividad_por_despacho"],
            "ultimo_mes": ultimo_mes["productividad_por_despacho"],
            "variacion_absoluta": round(
                ultimo_mes["productividad_por_despacho"] - primer_mes["productividad_por_despacho"],
                2,
            ),
            "variacion_pct": round(
                100
                * (
                    ultimo_mes["productividad_por_despacho"]
                    - primer_mes["productividad_por_despacho"]
                )
                / primer_mes["productividad_por_despacho"],
                1,
            ),
        },
        {
            "indicador": "Despachos por vehículo (intensidad de uso)",
            "primer_mes": primer_mes["despachos_por_vehiculo"],
            "ultimo_mes": ultimo_mes["despachos_por_vehiculo"],
            "variacion_absoluta": round(
                ultimo_mes["despachos_por_vehiculo"] - primer_mes["despachos_por_vehiculo"], 2
            ),
            "variacion_pct": round(
                100
                * (ultimo_mes["despachos_por_vehiculo"] - primer_mes["despachos_por_vehiculo"])
                / primer_mes["despachos_por_vehiculo"],
                1,
            ),
        },
    ]
)

print(f"\nPrimer mes completo: {primer_mes['mes'].date()}")
print(f"Último mes completo: {ultimo_mes['mes'].date()}")
print()
print(comparacion.to_string(index=False))

# ── 3. Vehículos retirados (último mes que operaron) ───────────────────────
print("\n" + "─" * 70)
print("3. VEHÍCULOS POTENCIALMENTE RETIRADOS")
print("   (PLACAs cuyo último despacho fue antes del último mes del dataset)")
print("─" * 70)

ultimo_mes_global = df["mes"].max()
ultimo_despacho_por_vehiculo = (
    df.groupby("PLACA")["mes"].max().reset_index(name="ultimo_mes_activo")
)
ultimo_despacho_por_vehiculo["meses_desde_ultimo"] = (
    (ultimo_mes_global - ultimo_despacho_por_vehiculo["ultimo_mes_activo"]).dt.days / 30.44
).round(1)

# Vehículos retirados: no operaron en los últimos 2 meses
retirados = ultimo_despacho_por_vehiculo[
    ultimo_despacho_por_vehiculo["meses_desde_ultimo"] >= 2
].sort_values("ultimo_mes_activo")

print(f"\nVehículos totales: {len(ultimo_despacho_por_vehiculo)}")
print(f"Vehículos retirados (sin actividad ≥2 meses): {len(retirados)}")
print(f"Vehículos aún activos: {len(ultimo_despacho_por_vehiculo) - len(retirados)}")

if len(retirados) > 0:
    print("\nLista de vehículos retirados (ordenados por mes de salida):")
    print(retirados.to_string(index=False))

# ── 4. Patrón de retiros por mes ───────────────────────────────────────────
print("\n" + "─" * 70)
print("4. RETIROS POR MES (cuándo los vehículos salieron del servicio)")
print("─" * 70)

retiros_por_mes = (
    retirados.groupby("ultimo_mes_activo").size().reset_index(name="vehiculos_retirados")
)
print(retiros_por_mes.to_string(index=False))

# ── 5. Guardar resultados ──────────────────────────────────────────────────
flota_mensual.to_csv(OUT_DIR / "diagnostico_flota_mensual.csv", index=False)
comparacion.to_csv(OUT_DIR / "diagnostico_flota_comparacion.csv", index=False)
ultimo_despacho_por_vehiculo.to_csv(OUT_DIR / "diagnostico_vehiculos_estado.csv", index=False)

print("\n" + "=" * 70)
print("Archivos guardados:")
print(f"  - {OUT_DIR / 'diagnostico_flota_mensual.csv'}")
print(f"  - {OUT_DIR / 'diagnostico_flota_comparacion.csv'}")
print(f"  - {OUT_DIR / 'diagnostico_vehiculos_estado.csv'}")
print("=" * 70)
print("FIN DEL DIAGNÓSTICO")
print("=" * 70)
