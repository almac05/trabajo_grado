"""SARIMA sobre un unico dia operativo, escrito paso a paso.

Objetivo: entender el mecanismo antes de escalarlo al conjunto de prueba.

Diferencia conceptual con XGBoost: SARIMA no recibe una tabla de variables
predictoras sino una serie. Predice la jornada completa de una vez, hacia
adelante desde el ultimo dato observado, en lugar de estimar cada franja de
forma independiente. Esto es coherente con la restriccion de consolidacion:
al cierre del dia anterior todos sus registros estan disponibles, mientras
que los de las franjas recientes no.
"""

import time

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

# ---------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
RUTA = 1
TARGET = "pasajeros_total"

# Dia a predecir. Debe caer dentro del conjunto de prueba (2 abril - 10 junio).
DIA = pd.Timestamp("2026-04-15")

SEMANAS_ENTRENAMIENTO = 26

# Ordenes no estacionales (p, d, q):
#   p=2  la PACF cae abruptamente tras el rezago 2
#   d=0  las series son estacionarias segun las pruebas ADF
#   q=1  componente de medias moviles minimo
ORDEN = (2, 0, 1)

# Ordenes estacionales (P, D, Q, s):
#   s=27 ciclo diario en la serie filtrada al horario operativo; la mediana de
#        franjas por dia operativo es 26 en Ruta 1 y 27 en Ruta 3, y el pico de
#        la ACF se concentra entre los rezagos 26 y 29
#   P=1, Q=1  ordenes minimos: con s largo el ajuste se vuelve costoso
ORDEN_ESTACIONAL = (1, 0, 1, 48)

# ---------------------------------------------------------------
# 2. Preparar la serie
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)

d = df[(df["FK_RUTA"] == RUTA) & df[TARGET].notna()].copy()
d = d.sort_values("timestamp").reset_index(drop=True)

print(f"Ruta {RUTA}: {len(d)} observaciones operativas")
print(f"Rango: {d['timestamp'].min()} -> {d['timestamp'].max()}")

d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
por_dia = d.groupby("dia_op")[TARGET].agg(["mean", "std", "min", "max"])
print(por_dia.tail(20).round(1).to_string())
print("\nDesviacion tipica intradiaria mediana:", por_dia["std"].median().round(1))

d["hora"] = d["timestamp"].dt.strftime("%H:%M")
lab = d[d["tipo_dia"] == "LABORAL"]
print(lab.groupby("hora")[TARGET].agg(["mean", "std", "count"]).round(1).to_string())

# El dia operativo va de las 04:00 a las 04:00 del dia siguiente.
inicio_dia = DIA + pd.Timedelta(hours=4)
fin_dia = inicio_dia + pd.Timedelta(days=1)
inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)

train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]

print(f"\nEntrenamiento: {len(train)} franjas "
      f"({train['timestamp'].min().date()} -> {train['timestamp'].max().date()})")
print(f"Dia a predecir: {len(test)} franjas ({DIA.date()}, "
      f"{test['tipo_dia'].iloc[0]})")

if len(test) == 0:
    raise ValueError(f"No hay observaciones operativas el {DIA.date()}.")

# IMPORTANTE: se pasa la serie sin indice temporal. Al filtrar el horario
# operativo la serie deja de ser regular (hay un salto de ~10 h entre el
# cierre de un dia y la apertura del siguiente), y statsmodels intentaria
# inferir una frecuencia inexistente.
y_train = train[TARGET].reset_index(drop=True)
y_test = test[TARGET].reset_index(drop=True)

# ---------------------------------------------------------------
# 3. Entrenar
# ---------------------------------------------------------------

print(f"\nAjustando SARIMA{ORDEN}x{ORDEN_ESTACIONAL} ...")
t0 = time.perf_counter()

modelo = SARIMAX(
    y_train,
    order=ORDEN,
    seasonal_order=ORDEN_ESTACIONAL,
    # Con s largo la optimizacion puede no converger si se imponen estas
    # restricciones sobre los parametros.
    enforce_stationarity=False,
    enforce_invertibility=False,
)
ajuste = modelo.fit(disp=False)

segundos = time.perf_counter() - t0
print(f"Ajuste completado en {segundos:.1f} s")
print(f"AIC: {ajuste.aic:.1f}")

# ---------------------------------------------------------------
# 4. Predecir la jornada completa
# ---------------------------------------------------------------

y_pred = ajuste.forecast(steps=len(y_test))

r = pd.DataFrame({
    "hora": test["timestamp"].dt.strftime("%H:%M").to_numpy(),
    "real": y_test.to_numpy(),
    "pred": y_pred.to_numpy().round(1),
})
r["error"] = (r["pred"] - r["real"]).round(1)

# ---------------------------------------------------------------
# 5. Evaluar
# ---------------------------------------------------------------

mae = r["error"].abs().mean()
sesgo = r["error"].mean()

print(f"\nMAE:   {mae:.2f}")
print(f"Sesgo: {sesgo:+.2f}")
print(f"Demanda media observada: {r['real'].mean():.2f}")

print("\n--- Prediccion franja a franja ---")
print(r.to_string(index=False))

media_franja = train.groupby(train["timestamp"].dt.strftime("%H:%M"))[TARGET].mean()
pred_trivial = test["timestamp"].dt.strftime("%H:%M").map(media_franja)
print("MAE media por franja:", (pred_trivial - test[TARGET]).abs().mean().round(2))
