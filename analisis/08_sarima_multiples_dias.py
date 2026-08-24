"""Evaluacion de SARIMA sobre multiples dias del conjunto de prueba.

El analisis exploratorio sobre un unico dia mostro que SARIMA converge a
predecir la media de la serie, sin reproducir el perfil intradiario. Este
script verifica si ese comportamiento se sostiene sobre una muestra amplia de
dias y en ambas rutas, y lo contrasta con un predictor de referencia
construido como la media historica por tipo de dia y franja horaria.

Diferencia conceptual con XGBoost: SARIMA no recibe una tabla de variables
predictoras sino una serie, y predice la jornada completa de una vez hacia
adelante. Esto es coherente con la restriccion de consolidacion: al cierre del
dia anterior todos sus registros estan disponibles, mientras que los de las
franjas recientes no.

Uso:
    python analisis/08_sarima_multiples_dias.py
"""

import time
import warnings
from pathlib import Path

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

# statsmodels avisa de no convergencia con ordenes estacionales largos; el
# aviso es esperado y no invalida la prediccion.
warnings.filterwarnings("ignore", message=".*Maximum Likelihood optimization.*")
warnings.filterwarnings("ignore", message=".*convergence.*")

# ---------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")

RUTAS = (1, 3)
TARGET = "pasajeros_total"

# Conjunto de prueba: ultimas 10 semanas del dataset.
INICIO_TEST = pd.Timestamp("2026-04-02")
FIN_TEST = pd.Timestamp("2026-06-10")

SEMANAS_ENTRENAMIENTO = 26


PASO_MUESTREO = 1   # todas las jornadas del test, no una de cada tres
MIN_FRANJAS = 8     # domingos y festivos operan jornadas mas cortas

# Ordenes no estacionales (p, d, q):
#   p=2  la PACF cae abruptamente tras el rezago 2
#   d=0  las series son estacionarias segun las pruebas ADF
#   q=1  componente de medias moviles minimo
ORDEN = (2, 0, 1)

# Ordenes estacionales (P, D, Q, s):
#   s=27 ciclo diario en la serie filtrada al horario operativo. La mediana de
#        franjas por dia operativo es 26 en Ruta 1 y 27 en Ruta 3, y el pico de
#        la ACF se concentra entre los rezagos 26 y 29.
#   P=1, Q=1  ordenes minimos: con s largo el ajuste se vuelve costoso.
ORDEN_ESTACIONAL = (1, 0, 1, 27)

# ---------------------------------------------------------------
# 2. Carga
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)

resumen = []
predicciones = []

for ruta in RUTAS:
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    # Dias candidatos: dentro del periodo de prueba y con jornada completa.
    conteo = d.groupby("dia_op").size()
    candidatos = [
        dia for dia, n in conteo.items()
        if INICIO_TEST.date() <= dia <= FIN_TEST.date() and n >= MIN_FRANJAS
    ]
    dias = sorted(candidatos)[::PASO_MUESTREO]

    print(f"\n{'=' * 60}")
    print(f"Ruta {ruta}: {len(d)} observaciones operativas | "
          f"{len(candidatos)} dias candidatos | {len(dias)} evaluados")

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

        # --- SARIMA ---
        # La serie se pasa sin indice temporal: al filtrar el horario operativo
        # deja de ser regular (salto de ~10 h entre cierre y apertura) y
        # statsmodels intentaria inferir una frecuencia inexistente.
        t0 = time.perf_counter()
        try:
            ajuste = SARIMAX(
                train[TARGET].reset_index(drop=True),
                order=ORDEN,
                seasonal_order=ORDEN_ESTACIONAL,
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit(disp=False)
            pred_sarima = ajuste.forecast(steps=len(test)).to_numpy()
            aic = ajuste.aic
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i:2d}/{len(dias)}] {dia}  fallo el ajuste: {exc}")
            continue
        segundos = time.perf_counter() - t0

        # --- Referencia: media historica por tipo de dia y franja ---
        # Usa exactamente la misma ventana de entrenamiento, de modo que la
        # comparacion aisla el metodo y no la informacion disponible.
        medias = train.groupby(["tipo_dia", "hora"])[TARGET].mean()
        idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
        pred_media = medias.reindex(idx).to_numpy()
        n_sin_media = pd.isna(pred_media).sum()
        pred_media = pd.Series(pred_media).fillna(train[TARGET].mean()).to_numpy()

        real = test[TARGET].to_numpy()
        err_sarima = pred_sarima - real
        err_media = pred_media - real

        resumen.append({
            "route": ruta,
            "dia_op": dia,
            "tipo_dia": tipo,
            "n": len(test),
            "demanda_media": real.mean(),
            "mae_sarima": abs(err_sarima).mean(),
            "sesgo_sarima": err_sarima.mean(),
            "rango_pred_sarima": pred_sarima.max() - pred_sarima.min(),
            "rango_real": real.max() - real.min(),
            "mae_media": abs(err_media).mean(),
            "sesgo_media": err_media.mean(),
            "celdas_sin_media": int(n_sin_media),
            "aic": aic,
            "segundos": segundos,
        })

        predicciones.append(pd.DataFrame({
            "route": ruta,
            "dia_op": dia,
            "tipo_dia": tipo,
            "hora": test["hora"].to_numpy(),
            "real": real,
            "pred_sarima": pred_sarima,
            "pred_media": pred_media,
        }))

        print(f"  [{i:2d}/{len(dias)}] {dia} {tipo:14s} "
              f"MAE SARIMA {abs(err_sarima).mean():6.2f} | "
              f"media {abs(err_media).mean():6.2f} | {segundos:4.1f}s")

# ---------------------------------------------------------------
# 3. Resultados
# ---------------------------------------------------------------

r = pd.DataFrame(resumen)
p = pd.concat(predicciones, ignore_index=True)

SALIDA.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA / "sarima_multiples_dias.csv", index=False)
p.to_csv(SALIDA / "sarima_predicciones.csv", index=False)

print("\n" + "=" * 60)
print("RESUMEN POR RUTA")
print(
    r.groupby("route")
    .agg(
        dias=("dia_op", "count"),
        demanda_media=("demanda_media", "mean"),
        mae_sarima=("mae_sarima", "mean"),
        sesgo_sarima=("sesgo_sarima", "mean"),
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
        mae_sarima=("mae_sarima", "mean"),
        mae_media=("mae_media", "mean"),
    )
    .round(2)
    .to_string()
)

# El rango de la prediccion frente al rango observado indica si el modelo
# reproduce el perfil intradiario o converge a un valor constante.
print("\nAMPLITUD DE LA PREDICCION FRENTE A LA OBSERVADA")
amp = r.groupby("route")[["rango_pred_sarima", "rango_real"]].mean().round(1)
amp["proporcion"] = (amp["rango_pred_sarima"] / amp["rango_real"]).round(3)
print(amp.to_string())

print(f"\nDetalle guardado en {SALIDA}")
