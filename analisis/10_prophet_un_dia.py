"""Prophet sobre un unico dia operativo, escrito paso a paso.

Prophet se evalua por una razon especifica: a diferencia de SARIMA, admite
festivos como componente explicito del modelo y varias estacionalidades
simultaneas. El fallo de SARIMA se atribuyo a que no dispone de mecanismo
para distinguir el tipo de dia; Prophet si lo tiene, de modo que permite
verificar si esa carencia era la causa o si el limite esta en la variabilidad
irreducible de la serie.

El horizonte es la jornada completa, igual que en SARIMA, para que ambos
resultados sean comparables.
"""

import time

import pandas as pd
from prophet import Prophet

# ---------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
RUTA = 1
TARGET = "pasajeros_total"

# Mismo dia que se uso con SARIMA, para comparar directamente.
DIA = pd.Timestamp("2026-04-15")

SEMANAS_ENTRENAMIENTO = 26

TIPOS_FESTIVOS = ("FESTIVO", "FESTIVO_PUENTE")

# ---------------------------------------------------------------
# 2. Preparar los datos
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)

d = df[(df["FK_RUTA"] == RUTA) & df[TARGET].notna()].copy()
d = d.sort_values("timestamp").reset_index(drop=True)
d["hora"] = d["timestamp"].dt.strftime("%H:%M")

inicio_dia = DIA + pd.Timedelta(hours=4)
fin_dia = inicio_dia + pd.Timedelta(days=1)
inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)

train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]

print(f"Ruta {RUTA} | entrenamiento: {len(train)} franjas | "
      f"dia a predecir: {len(test)} franjas ({DIA.date()}, {test['tipo_dia'].iloc[0]})")

# Prophet exige exactamente dos columnas: ds (marca temporal) y y (valor).
# A diferencia de SARIMA, aqui si se pasan los timestamps reales: Prophet los
# necesita para calcular las estacionalidades en unidades de tiempo.
serie_train = train[["timestamp", TARGET]].rename(
    columns={"timestamp": "ds", TARGET: "y"}
)

# ---------------------------------------------------------------
# 3. Calendario de festivos
# ---------------------------------------------------------------

# Se toman de todo el dataset, no solo del periodo de entrenamiento: el
# calendario es informacion conocida de antemano, de modo que incluir las
# fechas futuras no constituye fuga.
fest = d[d["tipo_dia"].isin(TIPOS_FESTIVOS)].copy()
fest["fecha"] = (fest["timestamp"] - pd.Timedelta(hours=4)).dt.normalize()

# Se mantienen FESTIVO y FESTIVO_PUENTE como grupos separados: el analisis de
# la linea base mostro que se comportan de forma distinta.
festivos = (
    fest[["tipo_dia", "fecha"]]
    .drop_duplicates()
    .rename(columns={"tipo_dia": "holiday", "fecha": "ds"})
    .reset_index(drop=True)
)

print(f"\nFestivos en el calendario: {len(festivos)}")
print(festivos["holiday"].value_counts().to_string())

# ---------------------------------------------------------------
# 4. Entrenar
# ---------------------------------------------------------------

# yearly_seasonality se desactiva: con 26 semanas de entrenamiento no hay
# ciclo anual observable. Las dos estacionalidades relevantes son la diaria
# (perfil intradiario) y la semanal (laborales frente a fin de semana).
modelo = Prophet(
    holidays=festivos,
    daily_seasonality=True,
    weekly_seasonality=True,
    yearly_seasonality=False,
)

print("\nAjustando Prophet ...")
t0 = time.perf_counter()
modelo.fit(serie_train)
segundos = time.perf_counter() - t0
print(f"Ajuste completado en {segundos:.1f} s")

# ---------------------------------------------------------------
# 5. Predecir la jornada completa
# ---------------------------------------------------------------

# Prophet predice sobre las marcas temporales que se le indiquen, de modo que
# basta con pasarle las franjas del dia objetivo.
futuro = test[["timestamp"]].rename(columns={"timestamp": "ds"})
pronostico = modelo.predict(futuro)

r = pd.DataFrame({
    "hora": test["hora"].to_numpy(),
    "real": test[TARGET].to_numpy(),
    "pred": pronostico["yhat"].to_numpy().round(1),
})
r["error"] = (r["pred"] - r["real"]).round(1)

# ---------------------------------------------------------------
# 6. Evaluar
# ---------------------------------------------------------------

# Referencia: media historica por tipo de dia y franja sobre la misma ventana.
medias = train.groupby(["tipo_dia", "hora"])[TARGET].mean()
idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
pred_media = medias.reindex(idx).to_numpy()
err_media = pred_media - test[TARGET].to_numpy()

print(f"\n{'':<12}{'MAE':>8}{'Sesgo':>9}{'Amplitud':>10}")
print(f"{'Prophet':<12}{r['error'].abs().mean():8.2f}"
      f"{r['error'].mean():+9.2f}{r['pred'].max() - r['pred'].min():10.1f}")
print(f"{'Referencia':<12}{abs(err_media).mean():8.2f}"
      f"{err_media.mean():+9.2f}{pred_media.max() - pred_media.min():10.1f}")
print(f"{'Observado':<12}{'':>8}{'':>9}{r['real'].max() - r['real'].min():10.1f}")
print(f"\nDemanda media observada: {r['real'].mean():.2f}")

print("\n--- Prediccion franja a franja ---")
print(r.to_string(index=False))
