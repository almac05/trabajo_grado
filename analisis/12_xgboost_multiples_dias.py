"""Evaluacion de XGBoost con reentrenamiento diario.

Replica el diseno empleado con SARIMA y Prophet --una jornada completa como
horizonte, reentrenamiento en cada jornada, ventana de 26 semanas-- de modo
que los tres metodos resulten comparables. La evaluacion previa de XGBoost
sobre el conjunto de prueba empleo un unico entrenamiento para las diez
semanas, lo que no permitia contrastarlo con los metodos que reentrenan a
diario.

Uso:
    python analisis/12_xgboost_multiples_dias.py
"""

import time
from pathlib import Path

import pandas as pd

from proyecto_grado.modeling.experimentos import (
    PARAMS_XGB,
    seleccionar_features,
)
import xgboost as xgb

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")

RUTAS = (1, 3)
TARGET = "pasajeros_total"

INICIO_TEST = pd.Timestamp("2026-04-02")
FIN_TEST = pd.Timestamp("2026-06-10")
SEMANAS_ENTRENAMIENTO = 26
PARADA_SEMANAS = 2
PASO_MUESTREO = 1
MIN_FRANJAS = 8

df = pd.read_parquet(PARQUET)
resumen, predicciones = [], []

for ruta in RUTAS:
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    # Las features son las mismas en todas las jornadas: se calculan una vez.
    features = seleccionar_features(d)

    conteo = d.groupby("dia_op").size()
    dias = sorted(
        dia for dia, n in conteo.items()
        if INICIO_TEST.date() <= dia <= FIN_TEST.date() and n >= MIN_FRANJAS
    )[::PASO_MUESTREO]

    print(f"\n{'=' * 60}")
    print(f"Ruta {ruta}: {len(dias)} jornadas | {len(features)} features")

    for i, dia in enumerate(dias, start=1):
        inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
        fin_dia = inicio_dia + pd.Timedelta(days=1)
        inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)
        corte_parada = inicio_dia - pd.Timedelta(weeks=PARADA_SEMANAS)

        train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
        fit = train[train["timestamp"] < corte_parada]
        stop = train[train["timestamp"] >= corte_parada]
        test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]

        if len(test) < MIN_FRANJAS or len(fit) < 500 or len(stop) == 0:
            print(f"  [{i:2d}/{len(dias)}] {dia}  datos insuficientes, se omite")
            continue

        tipo = test["tipo_dia"].iloc[0]

        t0 = time.perf_counter()
        modelo = xgb.XGBRegressor(**PARAMS_XGB)
        modelo.fit(
            fit[features], fit[TARGET],
            eval_set=[(stop[features], stop[TARGET])], verbose=False,
        )
        pred_xgb = modelo.predict(test[features])
        segundos = time.perf_counter() - t0

        # Referencia: media historica por tipo de dia y franja, misma ventana.
        medias = train.groupby(["tipo_dia", "hora"])[TARGET].mean()
        idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
        pred_media = medias.reindex(idx).to_numpy()
        n_sin_media = pd.isna(pred_media).sum()
        pred_media = pd.Series(pred_media).fillna(train[TARGET].mean()).to_numpy()

        real = test[TARGET].to_numpy()
        err_xgb = pred_xgb - real
        err_media = pred_media - real

        resumen.append({
            "route": ruta, "dia_op": dia, "tipo_dia": tipo, "n": len(test),
            "demanda_media": real.mean(),
            "mae_xgboost": abs(err_xgb).mean(),
            "sesgo_xgboost": err_xgb.mean(),
            "rango_pred_xgboost": pred_xgb.max() - pred_xgb.min(),
            "rango_real": real.max() - real.min(),
            "mae_media": abs(err_media).mean(),
            "sesgo_media": err_media.mean(),
            "celdas_sin_media": int(n_sin_media),
            "arboles": modelo.best_iteration + 1,
            "segundos": segundos,
        })

        predicciones.append(pd.DataFrame({
            "route": ruta, "dia_op": dia, "tipo_dia": tipo,
            "hora": test["hora"].to_numpy(), "real": real,
            "pred_xgboost": pred_xgb, "pred_media": pred_media,
        }))

        print(f"  [{i:2d}/{len(dias)}] {dia} {tipo:14s} "
              f"MAE XGB {abs(err_xgb).mean():6.2f} | "
              f"media {abs(err_media).mean():6.2f} | {segundos:4.1f}s")

r = pd.DataFrame(resumen)
p = pd.concat(predicciones, ignore_index=True)

SALIDA.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA / "xgboost_multiples_dias.csv", index=False)
p.to_csv(SALIDA / "xgboost_predicciones.csv", index=False)

print("\n" + "=" * 60)
print("RESUMEN POR RUTA")
print(r.groupby("route").agg(
    dias=("dia_op", "count"), demanda_media=("demanda_media", "mean"),
    mae_xgboost=("mae_xgboost", "mean"), sesgo_xgboost=("sesgo_xgboost", "mean"),
    mae_media=("mae_media", "mean"), sesgo_media=("sesgo_media", "mean"),
    arboles=("arboles", "mean"), segundos=("segundos", "mean"),
).round(2).to_string())

print("\nPOR TIPO DE DIA")
print(r.groupby(["route", "tipo_dia"]).agg(
    dias=("dia_op", "count"), demanda_media=("demanda_media", "mean"),
    mae_xgboost=("mae_xgboost", "mean"), mae_media=("mae_media", "mean"),
).round(2).to_string())

print("\nAMPLITUD DE LA PREDICCION FRENTE A LA OBSERVADA")
amp = r.groupby("route")[["rango_pred_xgboost", "rango_real"]].mean().round(1)
amp["proporcion"] = (amp["rango_pred_xgboost"] / amp["rango_real"]).round(3)
print(amp.to_string())

print(f"\nXGBoost supera a la referencia en "
      f"{(r['mae_xgboost'] < r['mae_media']).sum()} de {len(r)} jornadas")
