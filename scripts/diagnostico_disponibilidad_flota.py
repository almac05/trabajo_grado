"""
scripts/diagnostico_disponibilidad_flota.py
=============================================
Script exploratorio para verificar el mecanismo operativo descrito:

  1. Los vehículos salen escalonados en la mañana.
  2. Regresan al patio en ventanas de tiempo similares (porque
     los recorridos duran ~161 min en promedio).
  3. Se forma una cola de vehículos disponibles en el patio.
  4. El despachador los saca por orden de llegada (FIFO).
  5. En momentos de alta frecuencia de despacho, la cola se agota.
  6. Cuando no hay vehículos disponibles, se origina una espera
     larga hasta que el próximo vehículo regrese del recorrido.

Este script reconstruye, para cada vehículo y cada instante,
si está EN_RUTA o EN_PATIO, y cuenta cuántos vehículos hay
disponibles en patio en cada franja de tiempo. Luego cruza esto
con las franjas de mayor espera (headway) para verificar si
coinciden con los momentos de "patio vacío".

Este script NO modifica ningún dato. Solo imprime resultados
y genera un CSV de diagnóstico para inspección manual.

Uso:
    python scripts/diagnostico_disponibilidad_flota.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)

ROOT = Path(__file__).resolve().parent.parent
MR_PATH = ROOT / "data/processed/model_ready/despachos_model_ready.parquet"
OUT_DIR = ROOT / "reports/tables/baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("DIAGNÓSTICO — Disponibilidad de flota en patio")
print("=" * 70)

df = pd.read_parquet(MR_PATH)
df = df[df["MODEL_READY_OK"].eq(True) & df["HORA_FIN_FINAL"].notna()].copy()
df["HORA_INICIAL_REAL"] = pd.to_datetime(df["HORA_INICIAL_REAL"])
df["HORA_FIN_FINAL"] = pd.to_datetime(df["HORA_FIN_FINAL"])
df["FECHA_INICIAL"] = pd.to_datetime(df["FECHA_INICIAL"])
df["fecha_dia"] = df["FECHA_INICIAL"].dt.date

print(f"\nTotal despachos elegibles: {len(df):,}")

# ── PASO 1 — Elegir un día representativo con buen volumen ─────────────────
conteo_dia = df.groupby("fecha_dia").size().sort_values(ascending=False)
# Tomar un día laboral típico (no el de mayor outlier, sino uno robusto)
dia_ejemplo = conteo_dia.index[5]  # quinto día con más actividad, evita extremos
print(f"\nDía de análisis elegido: {dia_ejemplo} ({conteo_dia.loc[dia_ejemplo]} despachos ese día)")

dia_df = df[df["fecha_dia"] == dia_ejemplo].copy()
dia_df = dia_df.sort_values(["PLACA", "HORA_INICIAL_REAL"]).reset_index(drop=True)

print(f"Vehículos activos ese día: {dia_df['PLACA'].nunique()}")

# ── PASO 2 — Reconstruir línea de tiempo EN_RUTA / EN_PATIO por vehículo ────
# Para cada vehículo, generamos intervalos:
#   [HORA_INICIAL_REAL, HORA_FIN_FINAL]      -> EN_RUTA
#   [HORA_FIN_FINAL, siguiente_HORA_INICIAL] -> EN_PATIO

dia_df["siguiente_inicio"] = dia_df.groupby("PLACA")["HORA_INICIAL_REAL"].shift(-1)

intervalos = []
for _, row in dia_df.iterrows():
    # Intervalo EN_RUTA
    intervalos.append(
        {
            "PLACA": row["PLACA"],
            "estado": "EN_RUTA",
            "inicio": row["HORA_INICIAL_REAL"],
            "fin": row["HORA_FIN_FINAL"],
            "ruta": row["FK_RUTA"],
        }
    )
    # Intervalo EN_PATIO (si hay siguiente despacho ese día)
    if pd.notna(row["siguiente_inicio"]):
        intervalos.append(
            {
                "PLACA": row["PLACA"],
                "estado": "EN_PATIO",
                "inicio": row["HORA_FIN_FINAL"],
                "fin": row["siguiente_inicio"],
                "ruta": np.nan,
            }
        )

timeline = pd.DataFrame(intervalos)
timeline = timeline[timeline["inicio"] < timeline["fin"]].copy()

print(
    f"\nIntervalos reconstruidos: {len(timeline)} "
    f"({(timeline['estado'] == 'EN_RUTA').sum()} en ruta, "
    f"{(timeline['estado'] == 'EN_PATIO').sum()} en patio)"
)

# ── PASO 3 — Contar vehículos EN_PATIO por minuto a lo largo del día ───────
inicio_dia = pd.Timestamp(dia_ejemplo) + pd.Timedelta(hours=4)
fin_dia = pd.Timestamp(dia_ejemplo) + pd.Timedelta(hours=20)
minutos = pd.date_range(inicio_dia, fin_dia, freq="5min")

disponibilidad = []
patio = timeline[timeline["estado"] == "EN_PATIO"]

for t in minutos:
    en_patio = patio[(patio["inicio"] <= t) & (patio["fin"] > t)]
    disponibilidad.append(
        {
            "timestamp": t,
            "vehiculos_en_patio": len(en_patio),
        }
    )

disp_df = pd.DataFrame(disponibilidad)

print("\n" + "─" * 70)
print("3. DISPONIBILIDAD DE FLOTA EN PATIO A LO LARGO DEL DÍA")
print("   (muestra cada 30 min)")
print("─" * 70)
print(disp_df.iloc[::6][["timestamp", "vehiculos_en_patio"]].to_string(index=False))

# ── PASO 4 — Detectar franjas con patio vacío (0 vehículos disponibles) ────
franjas_vacias = disp_df[disp_df["vehiculos_en_patio"] == 0]
print(
    f"\n⚠️  Franjas de 5 min con PATIO VACÍO (0 vehículos disponibles): "
    f"{len(franjas_vacias)} de {len(disp_df)} "
    f"({100 * len(franjas_vacias) / len(disp_df):.1f}% del día operativo)"
)

if len(franjas_vacias) > 0:
    print("\nPrimeras 10 franjas con patio vacío:")
    print(franjas_vacias.head(10)["timestamp"].to_string(index=False))

# ── PASO 5 — Cruzar con headway real: ¿coincide patio vacío con esperas largas?
print("\n" + "─" * 70)
print("5. CRUCE: ¿LAS FRANJAS DE PATIO VACÍO COINCIDEN CON HEADWAYS LARGOS?")
print("─" * 70)

# Calcular headway real para ese mismo día (cualquier vehículo, misma ruta)
for ruta in [1, 3]:
    ruta_df = dia_df[dia_df["FK_RUTA"] == ruta].sort_values("HORA_INICIAL_REAL").copy()
    ruta_df["headway_min"] = ruta_df["HORA_INICIAL_REAL"].diff().dt.total_seconds() / 60
    ruta_df = ruta_df.dropna(subset=["headway_min"])

    print(f"\n--- Ruta {ruta} ---")
    print(ruta_df[["HORA_INICIAL_REAL", "headway_min"]].to_string(index=False))

    # Para cada despacho con headway largo, verificar disponibilidad de
    # patio en los minutos previos a su salida
    headways_largos = ruta_df[ruta_df["headway_min"] > 20]
    if len(headways_largos) > 0:
        print(f"\n  Despachos con headway > 20 min en Ruta {ruta}: {len(headways_largos)}")
        for _, hrow in headways_largos.iterrows():
            t_salida = hrow["HORA_INICIAL_REAL"]
            t_check = t_salida - pd.Timedelta(minutes=10)
            disp_en_ese_momento = disp_df[
                (disp_df["timestamp"] >= t_check - pd.Timedelta(minutes=5))
                & (disp_df["timestamp"] <= t_check + pd.Timedelta(minutes=5))
            ]
            promedio_disp = disp_en_ese_momento["vehiculos_en_patio"].mean()
            print(
                f"    Salida {t_salida.strftime('%H:%M')} "
                f"(headway={hrow['headway_min']:.1f} min) → "
                f"vehículos en patio ~10 min antes: {promedio_disp:.1f}"
            )

# ── PASO 6 — Guardar resultados para inspección ─────────────────────────────
disp_df.to_csv(OUT_DIR / "diagnostico_disponibilidad_flota.csv", index=False)
timeline.to_csv(OUT_DIR / "diagnostico_timeline_vehiculos.csv", index=False)

print("\n" + "=" * 70)
print("Archivos guardados:")
print(f"  - {OUT_DIR / 'diagnostico_disponibilidad_flota.csv'}")
print(f"  - {OUT_DIR / 'diagnostico_timeline_vehiculos.csv'}")
print("=" * 70)
print("FIN DEL DIAGNÓSTICO")
print("=" * 70)
