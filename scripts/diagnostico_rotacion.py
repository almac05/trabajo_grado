"""
scripts/diagnostico_rotacion.py
================================
Script exploratorio para verificar el patrón real de operación de
los vehículos de Montebello, antes de implementar los indicadores
de tiempo de rotación e inactividad.

Este script NO modifica ningún dato ni genera archivos.
Solo imprime resultados en consola para análisis.

Uso:
    python scripts/diagnostico_rotacion.py
"""

from pathlib import Path

import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 150)

ROOT = Path(__file__).resolve().parent.parent
MR_PATH = ROOT / "data/processed/model_ready/despachos_model_ready.parquet"

print("=" * 70)
print("DIAGNÓSTICO — Patrón de operación de vehículos (PLACA)")
print("=" * 70)

df = pd.read_parquet(MR_PATH)
df = df[df["MODEL_READY_OK"]].copy()
df["HORA_INICIAL_REAL"] = pd.to_datetime(df["HORA_INICIAL_REAL"])
df["HORA_FIN_FINAL"] = pd.to_datetime(df["HORA_FIN_FINAL"])
df["FECHA_INICIAL"] = pd.to_datetime(df["FECHA_INICIAL"])
df["fecha_dia"] = df["FECHA_INICIAL"].dt.date

print(f"\nTotal despachos elegibles: {len(df):,}")
print(f"Total vehículos (PLACA) únicos: {df['PLACA'].nunique():,}")

# ── 1. Vehículos con más despachos ──────────────────────────────────────────
top_placas = df["PLACA"].value_counts().head(5)
print("\n" + "─" * 70)
print("1. VEHÍCULOS CON MÁS DESPACHOS (total histórico)")
print("─" * 70)
print(top_placas)

# ── 2. Inspección de un día completo para el vehículo más activo ───────────
placa_ejemplo = top_placas.index[0]
sub = df[df["PLACA"] == placa_ejemplo].sort_values("HORA_INICIAL_REAL").copy()

# Buscar un día con varios despachos para ese vehículo
conteo_por_dia = sub.groupby("fecha_dia").size().sort_values(ascending=False)
dia_ejemplo = conteo_por_dia.index[0]

print("\n" + "─" * 70)
print(f"2. DESPACHOS DE {placa_ejemplo} EL DÍA {dia_ejemplo}")
print(f"   (día con más despachos para este vehículo: {conteo_por_dia.iloc[0]})")
print("─" * 70)

dia_data = (
    sub[sub["fecha_dia"] == dia_ejemplo][
        [
            "PLACA",
            "FK_RUTA",
            "HORA_INICIAL_REAL",
            "HORA_FIN_FINAL",
            "DURACION_MIN_FINAL",
            "PASAJEROS",
            "FIN_TIPO",
        ]
    ]
    .sort_values("HORA_INICIAL_REAL")
    .reset_index(drop=True)
)

print(dia_data.to_string())

# Calcular gap entre fin de un despacho e inicio del siguiente
dia_data["gap_min"] = (
    dia_data["HORA_INICIAL_REAL"].shift(-1) - dia_data["HORA_FIN_FINAL"]
).dt.total_seconds() / 60

print("\n" + "─" * 70)
print("3. GAPS ENTRE DESPACHOS CONSECUTIVOS (mismo vehículo)")
print("   gap_min = HORA_INICIAL_REAL(siguiente) - HORA_FIN_FINAL(actual)")
print("─" * 70)
print(
    dia_data[
        ["FK_RUTA", "HORA_INICIAL_REAL", "HORA_FIN_FINAL", "DURACION_MIN_FINAL", "gap_min"]
    ].to_string()
)

n_negativos = (dia_data["gap_min"] < 0).sum()
print(f"\n⚠️  Gaps negativos en este día: {n_negativos}")
if n_negativos > 0:
    print("   (Esto indicaría solapamiento - el vehículo 'inicia' otro")
    print("    despacho antes de terminar el anterior según los datos)")

# ── 4. Estadística general: despachos por vehículo por día ─────────────────
despachos_por_dia = df.groupby(["PLACA", "fecha_dia"]).size().reset_index(name="n_despachos")

print("\n" + "─" * 70)
print("4. DISTRIBUCIÓN DE DESPACHOS POR VEHÍCULO POR DÍA (todo el dataset)")
print("─" * 70)
print(despachos_por_dia["n_despachos"].describe())
print(f"\nModa (valor más común): {despachos_por_dia['n_despachos'].mode().tolist()}")
print("\nDistribución de frecuencias (top 10):")
print(despachos_por_dia["n_despachos"].value_counts().sort_index().head(10))

# ── 5. Gaps generales (muestra ampliada, todos los vehículos) ──────────────
print("\n" + "─" * 70)
print("5. GAPS ENTRE DESPACHOS CONSECUTIVOS — MUESTRA AMPLIADA")
print("   (calculado sobre TODOS los vehículos con 2+ despachos/día)")
print("─" * 70)

df_sorted = df.sort_values(["PLACA", "fecha_dia", "HORA_INICIAL_REAL"]).copy()
df_sorted["gap_min"] = (
    df_sorted.groupby(["PLACA", "fecha_dia"])["HORA_INICIAL_REAL"].shift(-1)
    - df_sorted["HORA_FIN_FINAL"]
).dt.total_seconds() / 60

# Solo gaps válidos (no NaN = hay un siguiente despacho ese mismo día)
gaps_validos = df_sorted["gap_min"].dropna()

print(f"\nTotal de gaps calculados (mismo vehículo, mismo día): {len(gaps_validos):,}")
print(
    f"Gaps negativos (solapamiento aparente): {(gaps_validos < 0).sum():,} "
    f"({100 * (gaps_validos < 0).mean():.2f}%)"
)
print(f"Gaps == 0 a 1 min: {((gaps_validos >= 0) & (gaps_validos <= 1)).sum():,}")
print("\nEstadística descriptiva de gaps (excluyendo negativos):")
print(gaps_validos[gaps_validos >= 0].describe())

print("\n" + "─" * 70)
print("6. ¿CAMBIA DE RUTA EL VEHÍCULO ENTRE DESPACHOS CONSECUTIVOS?")
print("─" * 70)
df_sorted["ruta_siguiente"] = df_sorted.groupby(["PLACA", "fecha_dia"])["FK_RUTA"].shift(-1)
cambio_ruta = df_sorted.dropna(subset=["ruta_siguiente"]).assign(
    cambia=lambda x: x["FK_RUTA"] != x["ruta_siguiente"]
)
print(f"Total comparaciones: {len(cambio_ruta):,}")
print(
    f"Vehículo cambia de ruta entre despachos consecutivos: "
    f"{cambio_ruta['cambia'].sum():,} ({100 * cambio_ruta['cambia'].mean():.2f}%)"
)
print(
    f"Vehículo mantiene la misma ruta: "
    f"{(~cambio_ruta['cambia']).sum():,} ({100 * (~cambio_ruta['cambia']).mean():.2f}%)"
)

print("\n" + "=" * 70)
print("FIN DEL DIAGNÓSTICO")
print("=" * 70)
