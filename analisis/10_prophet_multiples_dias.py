"""Evaluacion de Prophet sobre multiples dias del conjunto de prueba.

Prophet se evalua por una razon especifica: a diferencia de SARIMA, admite
festivos como componente explicito y varias estacionalidades simultaneas. El
fallo de SARIMA se atribuyo a que no dispone de mecanismo para distinguir el
tipo de dia; Prophet si lo tiene, de modo que permite verificar si esa
carencia era la causa o si el limite reside en la variabilidad irreducible de
la serie.

Se emplea exactamente el mismo diseno que en la evaluacion de SARIMA --misma
muestra de jornadas, misma ventana de entrenamiento, mismo horizonte de una
jornada completa-- de modo que los resultados de ambos metodos y del predictor
de referencia son directamente comparables.

Uso:
    python analisis/10_prophet_multiples_dias.py
"""

import logging
import time
import warnings
from pathlib import Path

import pandas as pd
from prophet import Prophet

# Prophet y su motor de inferencia emiten mensajes por cada ajuste; con varias
# decenas de modelos la consola quedaria ilegible.
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")

RUTAS = (1, 3)
TARGET = "pasajeros_total"

# Mismos parametros que la evaluacion de SARIMA, para que la muestra de
# jornadas resultante sea identica.
INICIO_TEST = pd.Timestamp("2026-04-02")
FIN_TEST = pd.Timestamp("2026-06-10")
SEMANAS_ENTRENAMIENTO = 26
PASO_MUESTREO = 1   # todas las jornadas del test, no una de cada tres
MIN_FRANJAS = 8     # domingos y festivos operan jornadas mas cortas

TIPOS_FESTIVOS = ("FESTIVO", "FESTIVO_PUENTE")

# ---------------------------------------------------------------
# 2. Evaluacion
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)

resumen = []
predicciones = []

for ruta in RUTAS:
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    # Calendario de festivos. Se toma de todo el dataset, no solo del periodo
    # de entrenamiento: el calendario es informacion conocida de antemano, de
    # modo que incluir fechas futuras no constituye fuga temporal.
    fest = d[d["tipo_dia"].isin(TIPOS_FESTIVOS)].copy()
    fest["fecha"] = (fest["timestamp"] - pd.Timedelta(hours=4)).dt.normalize()
    festivos = (
        fest[["tipo_dia", "fecha"]]
        .drop_duplicates()
        .rename(columns={"tipo_dia": "holiday", "fecha": "ds"})
        .reset_index(drop=True)
    )

    conteo = d.groupby("dia_op").size()
    candidatos = [
        dia for dia, n in conteo.items()
        if INICIO_TEST.date() <= dia <= FIN_TEST.date() and n >= MIN_FRANJAS
    ]
    dias = sorted(candidatos)[::PASO_MUESTREO]

    print(f"\n{'=' * 60}")
    print(f"Ruta {ruta}: {len(dias)} jornadas | {len(festivos)} festivos en calendario")

    for i, dia in enumerate(dias, start=1):
        inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
        fin_dia = inicio_dia + pd.Timedelta(days=1)
        inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)

        train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
        test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]

        if len(test) < MIN_FRANJAS or len(train) < 500:
            print(f"  [{i:2d}/{len(dias)}] {dia}  datos insuficientes, se omite")
            continue

        tipo = test["tipo_dia"].iloc[0]

        # --- Prophet ---
        # yearly_seasonality se desactiva: con 26 semanas de entrenamiento no
        # hay ciclo anual observable.
        t0 = time.perf_counter()
        try:
            modelo = Prophet(
                holidays=festivos,
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
            )
            modelo.fit(
                train[["timestamp", TARGET]].rename(
                    columns={"timestamp": "ds", TARGET: "y"}
                )
            )
            pronostico = modelo.predict(
                test[["timestamp"]].rename(columns={"timestamp": "ds"})
            )
            pred_prophet = pronostico["yhat"].to_numpy()
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i:2d}/{len(dias)}] {dia}  fallo el ajuste: {exc}")
            continue
        segundos = time.perf_counter() - t0

        # --- Referencia: media historica por tipo de dia y franja ---
        medias = train.groupby(["tipo_dia", "hora"])[TARGET].mean()
        idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
        pred_media = medias.reindex(idx).to_numpy()
        n_sin_media = pd.isna(pred_media).sum()
        pred_media = pd.Series(pred_media).fillna(train[TARGET].mean()).to_numpy()

        real = test[TARGET].to_numpy()
        err_prophet = pred_prophet - real
        err_media = pred_media - real

        resumen.append({
            "route": ruta,
            "dia_op": dia,
            "tipo_dia": tipo,
            "n": len(test),
            "demanda_media": real.mean(),
            "mae_prophet": abs(err_prophet).mean(),
            "sesgo_prophet": err_prophet.mean(),
            "rango_pred_prophet": pred_prophet.max() - pred_prophet.min(),
            "rango_real": real.max() - real.min(),
            "mae_media": abs(err_media).mean(),
            "sesgo_media": err_media.mean(),
            "celdas_sin_media": int(n_sin_media),
            "segundos": segundos,
        })

        predicciones.append(pd.DataFrame({
            "route": ruta,
            "dia_op": dia,
            "tipo_dia": tipo,
            "hora": test["hora"].to_numpy(),
            "real": real,
            "pred_prophet": pred_prophet,
            "pred_media": pred_media,
        }))

        print(f"  [{i:2d}/{len(dias)}] {dia} {tipo:14s} "
              f"MAE Prophet {abs(err_prophet).mean():6.2f} | "
              f"media {abs(err_media).mean():6.2f} | {segundos:4.1f}s")

# ---------------------------------------------------------------
# 3. Resultados
# ---------------------------------------------------------------

r = pd.DataFrame(resumen)
p = pd.concat(predicciones, ignore_index=True)

SALIDA.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA / "prophet_multiples_dias.csv", index=False)
p.to_csv(SALIDA / "prophet_predicciones.csv", index=False)

print("\n" + "=" * 60)
print("RESUMEN POR RUTA")
print(
    r.groupby("route")
    .agg(
        dias=("dia_op", "count"),
        demanda_media=("demanda_media", "mean"),
        mae_prophet=("mae_prophet", "mean"),
        sesgo_prophet=("sesgo_prophet", "mean"),
        mae_media=("mae_media", "mean"),
        sesgo_media=("sesgo_media", "mean"),
        segundos=("segundos", "mean"),
    )
    .round(2)
    .to_string()
)

print("\nPOR TIPO DE DIA")
print(
    r.groupby(["route", "tipo_dia"])
    .agg(
        dias=("dia_op", "count"),
        demanda_media=("demanda_media", "mean"),
        mae_prophet=("mae_prophet", "mean"),
        mae_media=("mae_media", "mean"),
    )
    .round(2)
    .to_string()
)

print("\nAMPLITUD DE LA PREDICCION FRENTE A LA OBSERVADA")
amp = r.groupby("route")[["rango_pred_prophet", "rango_real"]].mean().round(1)
amp["proporcion"] = (amp["rango_pred_prophet"] / amp["rango_real"]).round(3)
print(amp.to_string())

print(f"\nProphet supera a la referencia en "
      f"{(r['mae_prophet'] < r['mae_media']).sum()} de {len(r)} jornadas")


print(f"\nDetalle guardado en {SALIDA}")
