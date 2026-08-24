"""Comparacion de SARIMA, Prophet y el predictor de referencia.

Cruza los resultados de las evaluaciones previas sobre las jornadas comunes.
Los tres metodos se evaluaron con identica ventana de entrenamiento (26
semanas), identico horizonte (una jornada completa) y sobre las mismas
observaciones, de modo que la comparacion aisla el metodo y no el acceso a la
informacion.

Requiere haber ejecutado antes:
    analisis/08_sarima_multiples_dias.py
    analisis/10_prophet_multiples_dias.py

Uso:
    python analisis/11_comparacion_metodos_clasicos.py
"""

from pathlib import Path

import pandas as pd

pd.set_option("display.width", 220)

SALIDA = Path("analisis/salidas")

# ---------------------------------------------------------------
# 1. Carga y cruce
# ---------------------------------------------------------------

s = pd.read_csv(SALIDA / "sarima_multiples_dias.csv")
p = pd.read_csv(SALIDA / "prophet_multiples_dias.csv")

# Los objetos date no sobreviven al CSV, que los almacena como texto. Se
# normalizan ambos antes de cruzar para evitar comparaciones entre tipos
# distintos, que producirian un cruce vacio sin lanzar ningun error.
for df in (s, p):
    df["dia_op"] = pd.to_datetime(df["dia_op"]).dt.date

c = p.merge(
    s[["route", "dia_op", "mae_sarima", "sesgo_sarima", "rango_pred_sarima"]],
    on=["route", "dia_op"],
    how="inner",
)

if c.empty:
    raise ValueError(
        "El cruce no produjo jornadas comunes. Verifique que ambas evaluaciones "
        "usen los mismos parametros de muestreo."
    )

print(f"Jornadas comunes: {len(c)} de {len(s)} en SARIMA y {len(p)} en Prophet")

# ---------------------------------------------------------------
# 2. Comparacion agregada
# ---------------------------------------------------------------

print("\n" + "=" * 70)
print("COMPARACION POR RUTA")
print(
    c.groupby("route")
    .agg(
        jornadas=("dia_op", "count"),
        demanda_media=("demanda_media", "mean"),
        mae_sarima=("mae_sarima", "mean"),
        mae_prophet=("mae_prophet", "mean"),
        mae_referencia=("mae_media", "mean"),
        sesgo_sarima=("sesgo_sarima", "mean"),
        sesgo_prophet=("sesgo_prophet", "mean"),
        sesgo_referencia=("sesgo_media", "mean"),
    )
    .round(2)
    .to_string()
)

print("\nPOR TIPO DE DIA")
print(
    c.groupby(["route", "tipo_dia"])
    .agg(
        jornadas=("dia_op", "count"),
        demanda_media=("demanda_media", "mean"),
        mae_sarima=("mae_sarima", "mean"),
        mae_prophet=("mae_prophet", "mean"),
        mae_referencia=("mae_media", "mean"),
    )
    .round(2)
    .to_string()
)

# ---------------------------------------------------------------
# 3. Amplitud reproducida
# ---------------------------------------------------------------

# La amplitud predicha frente a la observada indica si el metodo reproduce el
# perfil intradiario o converge a un valor proximo a la media.
print("\nAMPLITUD DE LA PREDICCION FRENTE A LA OBSERVADA")
amp = (
    c.groupby("route")[["rango_pred_sarima", "rango_pred_prophet", "rango_real"]]
    .mean()
    .round(1)
)
amp["prop_sarima"] = (amp["rango_pred_sarima"] / amp["rango_real"]).round(3)
amp["prop_prophet"] = (amp["rango_pred_prophet"] / amp["rango_real"]).round(3)
print(amp.to_string())

# ---------------------------------------------------------------
# 4. Comparacion pareada
# ---------------------------------------------------------------

# La proporcion de jornadas ganadas es mas informativa que la diferencia media,
# porque no la dominan unas pocas jornadas atipicas.
print("\nCOMPARACION PAREADA (jornadas ganadas sobre el total)")
pares = [
    ("Prophet", "SARIMA", "mae_prophet", "mae_sarima"),
    ("Prophet", "referencia", "mae_prophet", "mae_media"),
    ("SARIMA", "referencia", "mae_sarima", "mae_media"),
]
for nombre_a, nombre_b, col_a, col_b in pares:
    for ruta, g in c.groupby("route"):
        gana = (g[col_a] < g[col_b]).sum()
        print(f"  Ruta {ruta}: {nombre_a} supera a {nombre_b} en "
              f"{gana:2d} de {len(g)} jornadas ({100 * gana / len(g):.0f} %)")

# ---------------------------------------------------------------
# 5. Salida
# ---------------------------------------------------------------

cols = [
    "route", "dia_op", "tipo_dia", "n", "demanda_media",
    "mae_sarima", "mae_prophet", "mae_media",
    "sesgo_sarima", "sesgo_prophet", "sesgo_media",
    "rango_pred_sarima", "rango_pred_prophet", "rango_real",
]
c[cols].to_csv(SALIDA / "comparacion_metodos_clasicos.csv", index=False)
print(f"\nDetalle guardado en {SALIDA / 'comparacion_metodos_clasicos.csv'}")
