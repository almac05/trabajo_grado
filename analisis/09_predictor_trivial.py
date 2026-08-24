"""Compara XGBoost contra un predictor trivial de media por franja.

El predictor trivial estima cada franja con la media historica de su
combinacion (tipo de dia, hora). Usa la misma ventana de 26 semanas previas al
corte y se evalua sobre exactamente el mismo conjunto de prueba, de modo que
la comparacion aisla el aporte del modelo de aprendizaje.
"""

import pandas as pd

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
PREDICCIONES = "analisis/salidas/test_final_predicciones.csv"

TARGET = "pasajeros_total"
CORTE = pd.Timestamp("2026-04-02 04:00:00")
SEMANAS = 26

df = pd.read_parquet(PARQUET)
xgb = pd.read_csv(PREDICCIONES, parse_dates=["timestamp"])

resultados = []

for ruta in (1, 3):
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    # Misma ventana que uso XGBoost: 26 semanas anteriores al corte.
    train = d[(d["timestamp"] >= CORTE - pd.Timedelta(weeks=SEMANAS))
              & (d["timestamp"] < CORTE)]

    # Media por tipo de dia y hora. Se incluye tipo_dia porque un laboral y un
    # domingo tienen niveles muy distintos a la misma hora.
    medias = train.groupby(["tipo_dia", "hora"])[TARGET].mean()
    media_global = train[TARGET].mean()

    # Evaluar sobre las mismas filas que XGBoost
    t = xgb[xgb["route"] == ruta].copy()
    t["hora"] = t["timestamp"].dt.strftime("%H:%M")

    idx = pd.MultiIndex.from_arrays([t["tipo_dia"], t["hora"]])
    t["pred_trivial"] = medias.reindex(idx).to_numpy()
    n_fallback = t["pred_trivial"].isna().sum()
    t["pred_trivial"] = t["pred_trivial"].fillna(media_global)

    t["error_trivial"] = t["pred_trivial"] - t[TARGET]

    print(f"\nRuta {ruta}: {len(t)} observaciones | "
          f"celdas sin media historica: {n_fallback}")

    for regimen, g in t.groupby("regimen"):
        resultados.append({
            "route": ruta,
            "regimen": regimen,
            "n": len(g),
            "demanda_media": g[TARGET].mean(),
            "mae_xgboost": g["error"].abs().mean(),
            "sesgo_xgboost": g["error"].mean(),
            "mae_trivial": g["error_trivial"].abs().mean(),
            "sesgo_trivial": g["error_trivial"].mean(),
        })

r = pd.DataFrame(resultados)
r["dif_mae"] = r["mae_xgboost"] - r["mae_trivial"]   # negativo = gana XGBoost

print("\n" + "=" * 70)
print(r.round(2).to_string(index=False))
