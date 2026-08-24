"""Cuadros de respaldo para la seccion de analisis de mecanismos.

Genera las tablas que sustentan las afirmaciones de esa seccion y que hasta
ahora no contaban con respaldo tabulado en el documento:

  1. Variabilidad de la serie: desviacion tipica intradiaria y por franja
     horaria entre dias equivalentes. Sustenta el argumento sobre el limite
     del error alcanzable.
  2. Amplitud reproducida por cada metodo frente a la observada.
  3. Errores de SARIMA por dia de la semana, que evidencian el arrastre de
     nivel en las transiciones entre tipos de dia.
  4. Detalle de las jornadas festivas, con el numero de franjas sin precedente
     en la ventana de entrenamiento.

Uso:
    python analisis/14_cuadros_mecanismos.py
"""

from pathlib import Path

import pandas as pd

pd.set_option("display.width", 240)

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")
TARGET = "pasajeros_total"
TIPOS_RAROS = ["FESTIVO", "FESTIVO_PUENTE"]

SALIDA.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------
# 1. Variabilidad de la serie
# ---------------------------------------------------------------
# Dos medidas distintas: la dispersion dentro de una misma jornada, que refleja
# la amplitud del ciclo intradiario, y la dispersion de cada franja horaria
# entre dias equivalentes, que refleja la variabilidad no explicada por el
# calendario. Esta segunda es la que acota el error alcanzable.

df = pd.read_parquet(PARQUET)
filas_intra, perfiles = [], []

for ruta in (1, 3):
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    por_dia = d.groupby("dia_op")[TARGET].agg(["mean", "std"])
    filas_intra.append({
        "route": ruta,
        "jornadas": len(por_dia),
        "demanda_media": por_dia["mean"].mean(),
        "desv_intradiaria_mediana": por_dia["std"].median(),
    })

    lab = d[d["tipo_dia"] == "LABORAL"]
    perfil = (
        lab.groupby("hora")[TARGET]
        .agg(media="mean", desv="std", n="count")
        .reset_index()
    )
    perfil["route"] = ruta
    perfiles.append(perfil)

intra = pd.DataFrame(filas_intra).round(1)
perfil = pd.concat(perfiles, ignore_index=True).round(1)

print("=" * 70)
print("CUADRO 1a. Variabilidad intradiaria")
print(intra.to_string(index=False))

print("\nCUADRO 1b. Perfil horario en dias laborales (extremos del ciclo)")
resumen_perfil = (
    perfil[perfil["n"] >= 100]
    .groupby("route")
    .agg(
        franjas=("hora", "count"),
        media_min=("media", "min"),
        media_max=("media", "max"),
        desv_min=("desv", "min"),
        desv_max=("desv", "max"),
    )
    .round(1)
)
print(resumen_perfil.to_string())

intra.to_csv(SALIDA / "cuadro_variabilidad_intradiaria.csv", index=False)
perfil.to_csv(SALIDA / "cuadro_perfil_horario_laboral.csv", index=False)

# ---------------------------------------------------------------
# 2. Amplitud reproducida por cada metodo
# ---------------------------------------------------------------
# La diferencia entre el valor maximo y el minimo predichos en cada jornada,
# comparada con la observada, indica si el metodo reproduce el perfil
# intradiario o converge hacia un valor proximo a la media.

archivos = {
    "SARIMA": ("sarima_multiples_dias.csv", "rango_pred_sarima"),
    "Prophet": ("prophet_multiples_dias.csv", "rango_pred_prophet"),
    "XGBoost": ("xgboost_multiples_dias.csv", "rango_pred_xgboost"),
}

filas_amp = []
for metodo, (archivo, columna) in archivos.items():
    ruta_archivo = SALIDA / archivo
    if not ruta_archivo.exists():
        print(f"\nAviso: no se encontro {archivo}; se omite {metodo}.")
        continue
    r = pd.read_csv(ruta_archivo)
    for ruta, g in r.groupby("route"):
        filas_amp.append({
            "metodo": metodo,
            "route": ruta,
            "amplitud_predicha": g[columna].mean(),
            "amplitud_observada": g["rango_real"].mean(),
            "proporcion": g[columna].mean() / g["rango_real"].mean(),
        })

amp = pd.DataFrame(filas_amp).round(3)
print("\n" + "=" * 70)
print("CUADRO 2. Amplitud reproducida frente a la observada")
print(amp.to_string(index=False))
amp.to_csv(SALIDA / "cuadro_amplitud_metodos.csv", index=False)

# ---------------------------------------------------------------
# 3. Error de SARIMA por dia de la semana
# ---------------------------------------------------------------
# El arrastre del nivel del dia anterior deberia manifestarse como un error
# elevado en los lunes, que suceden a un domingo de demanda reducida.

ruta_sarima = SALIDA / "sarima_multiples_dias.csv"
if ruta_sarima.exists():
    s = pd.read_csv(ruta_sarima)
    s["dia_semana"] = pd.to_datetime(s["dia_op"]).dt.dayofweek
    nombres = {0: "Lunes", 1: "Martes", 2: "Miercoles", 3: "Jueves",
               4: "Viernes", 5: "Sabado", 6: "Domingo"}
    s["nombre_dia"] = s["dia_semana"].map(nombres)

    # Solo dias laborales, para aislar el efecto del dia de la semana del
    # efecto del tipo de dia.
    lab = s[s["tipo_dia"] == "LABORAL"]
    tabla_dow = (
        lab.pivot_table(index="nombre_dia", columns="route",
                        values="mae_sarima", aggfunc="mean")
        .reindex(["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"])
        .round(2)
    )
    print("\n" + "=" * 70)
    print("CUADRO 3. Error de SARIMA por dia de la semana (solo dias laborales)")
    print(tabla_dow.to_string())
    tabla_dow.to_csv(SALIDA / "cuadro_sarima_por_dia_semana.csv")

    print("\nDiez errores mas elevados de SARIMA, Ruta 1")
    print(
        s[s["route"] == 1]
        .nlargest(10, "mae_sarima")[["dia_op", "nombre_dia", "tipo_dia", "mae_sarima"]]
        .round(2)
        .to_string(index=False)
    )

# ---------------------------------------------------------------
# 4. Jornadas festivas en detalle
# ---------------------------------------------------------------
# La columna de celdas sin precedente identifica cuando el predictor de
# referencia carece de observaciones del tipo de dia en su ventana y recurre
# al promedio general.

ruta_xgb = SALIDA / "xgboost_multiples_dias.csv"
if ruta_xgb.exists():
    x = pd.read_csv(ruta_xgb)
    fest = x[x["tipo_dia"].isin(TIPOS_RAROS)][
        ["route", "dia_op", "tipo_dia", "n", "celdas_sin_media",
         "mae_xgboost", "mae_media"]
    ].round(2)
    print("\n" + "=" * 70)
    print("CUADRO 4. Jornadas festivas en detalle")
    print(fest.to_string(index=False))
    fest.to_csv(SALIDA / "cuadro_jornadas_festivas.csv", index=False)

print(f"\nCuadros guardados en {SALIDA}")
