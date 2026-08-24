"""Metricas completas de los metodos evaluados.

Recalcula el conjunto de indicadores sobre las predicciones ya almacenadas,
sin reentrenar ningun modelo. El anteproyecto compromete MAE, RMSE y MAPE
como criterios de seleccion; se incorporan dos ajustes que se justifican en la
metodologia:

  - Se anade el sesgo, definido como la media del error con signo. En un
    sistema de recomendacion de despacho la demanda estimada se convierte en
    numero de vehiculos, de modo que una desviacion sistematica se traduce
    directamente en recomendaciones de oferta excesiva o deficitaria.

  - Se sustituye el MAPE por el WAPE. El MAPE se indefine ante valores
    observados nulos y sobrepesa las franjas de baja demanda: predecir diez
    pasajeros donde hubo dos produce un error del cuatrocientos por ciento.
    Con una demanda media de treinta pasajeros en dias festivos y minimos de
    ocho, el indicador resultaria inestable. El WAPE --suma de errores
    absolutos sobre suma de observados-- conserva la interpretacion porcentual
    sin esas propiedades. Se reporta ademas el MAPE restringido a las franjas
    por encima de un umbral, a efectos de dejar constancia del indicador
    comprometido.

Conjunto comun de jornadas. Las arquitecturas recurrentes omiten las jornadas
cuya jornada previa carece de operacion suficiente, de modo que evaluan menos
dias que los metodos restantes. La comparacion se restringe a la interseccion,
para que las diferencias sean atribuibles al metodo y no al conjunto evaluado.

Las metricas se calculan sobre el conjunto de observaciones, no promediando
por jornada: este ultimo criterio asignaria igual peso a una jornada de ocho
franjas y a una de veintiocho.

Uso:
    python analisis/15_metricas_completas.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.width", 250)

SALIDA = Path("analisis/salidas")

# Umbral por debajo del cual el MAPE deja de ser informativo.
UMBRAL_MAPE = 10

TIPOS_RAROS = ["FESTIVO", "FESTIVO_PUENTE"]

# Cada fuente aporta una columna de prediccion distinta; el valor observado
# esta siempre en 'real'. El predictor de referencia se recalcula dentro de
# cada script de evaluacion, de modo que puede tomarse de cualquiera de ellos.
FUENTES = {
    "SARIMA": ("sarima_predicciones.csv", "pred_sarima"),
    "Prophet": ("prophet_predicciones.csv", "pred_prophet"),
    "XGBoost": ("xgboost_predicciones.csv", "pred_xgboost"),
    "LSTM": ("lstm_predicciones_52s.csv", "pred_lstm"),
    "GRU": ("gru_predicciones.csv", "pred_gru"),
    "CNN-LSTM": ("cnn_lstm_predicciones.csv", "pred_cnn_lstm"),
    "Referencia": ("xgboost_predicciones.csv", "pred_media"),
}


def metricas(real: np.ndarray, pred: np.ndarray) -> dict:
    """Calcula el conjunto de indicadores sobre un vector de observaciones."""
    error = pred - real
    absoluto = np.abs(error)

    mask = real >= UMBRAL_MAPE
    mape = 100 * np.mean(absoluto[mask] / real[mask]) if mask.any() else np.nan

    return {
        "n": len(real),
        "demanda_media": real.mean(),
        "mae": absoluto.mean(),
        "rmse": np.sqrt(np.mean(error ** 2)),
        "wape": 100 * absoluto.sum() / real.sum(),
        "sesgo": error.mean(),
        "mape_parcial": mape,
        "n_mape": int(mask.sum()),
    }


# ---------------------------------------------------------------
# 1. Carga y determinacion del conjunto comun
# ---------------------------------------------------------------

datos = {}
for metodo, (archivo, columna) in FUENTES.items():
    ruta = SALIDA / archivo
    if not ruta.exists():
        print(f"Aviso: no se encontro {archivo}; se omite {metodo}.")
        continue

    d = pd.read_csv(ruta)
    if columna not in d.columns:
        print(f"Aviso: {archivo} no contiene {columna}; se omite {metodo}.")
        continue

    d = d[d["real"].notna() & d[columna].notna()].copy()
    d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.date
    datos[metodo] = (d, columna)

if not datos:
    raise FileNotFoundError("No se encontro ningun archivo de predicciones.")

jornadas = [
    set(zip(d["route"], d["dia_op"], strict=False)) for d, _ in datos.values()
]
comun = set.intersection(*jornadas)

print(f"Metodos evaluados: {', '.join(datos)}")
print(f"Jornadas por metodo: {[len(j) for j in jornadas]}")
print(f"Jornadas comunes a todos: {len(comun)}")

# ---------------------------------------------------------------
# 2. Calculo sobre el conjunto comun
# ---------------------------------------------------------------

filas_global, filas_regimen, filas_tipo = [], [], []

for metodo, (d, columna) in datos.items():
    d = d[[(r, dia) in comun for r, dia in zip(d["route"], d["dia_op"], strict=False)]]
    d = d.copy()
    d["regimen"] = (
        d["tipo_dia"].isin(TIPOS_RAROS).map({True: "raro", False: "ordinario"})
    )

    for ruta, g in d.groupby("route"):
        filas_global.append({
            "metodo": metodo, "route": ruta,
            **metricas(g["real"].to_numpy(), g[columna].to_numpy()),
        })

    for (ruta, regimen), g in d.groupby(["route", "regimen"]):
        filas_regimen.append({
            "metodo": metodo, "route": ruta, "regimen": regimen,
            **metricas(g["real"].to_numpy(), g[columna].to_numpy()),
        })

    for (ruta, tipo_dia), g in d.groupby(["route", "tipo_dia"]):
        filas_tipo.append({
            "metodo": metodo, "route": ruta, "tipo_dia": tipo_dia,
            **metricas(g["real"].to_numpy(), g[columna].to_numpy()),
        })

glob = pd.DataFrame(filas_global).round(2)
reg = pd.DataFrame(filas_regimen).round(2)
tip = pd.DataFrame(filas_tipo).round(2)

# ---------------------------------------------------------------
# 3. Resultados
# ---------------------------------------------------------------

cols = ["metodo", "route", "n", "demanda_media", "mae", "rmse", "wape",
        "sesgo", "mape_parcial"]

print("\n" + "=" * 110)
print("METRICAS GLOBALES")
print(glob[cols].sort_values(["route", "mae"]).to_string(index=False))

print("\n" + "=" * 110)
print("POR REGIMEN DE DIA")
print(
    reg[["metodo", "route", "regimen", "n", "demanda_media", "mae", "rmse",
         "wape", "sesgo"]]
    .sort_values(["regimen", "route", "mae"])
    .to_string(index=False)
)

print("\n" + "=" * 110)
print("MAE POR TIPO DE DIA")
print(
    tip.pivot_table(index="metodo", columns=["route", "tipo_dia"], values="mae")
    .round(2)
    .to_string()
)

print("\nSESGO POR TIPO DE DIA")
print(
    tip.pivot_table(index="metodo", columns=["route", "tipo_dia"], values="sesgo")
    .round(2)
    .to_string()
)

# La cobertura del MAPE documenta por que el indicador se sustituye: incluso
# restringido a franjas con demanda apreciable, su valor resulta inestable.
print("\nCOBERTURA DEL MAPE "
      f"(franjas con demanda superior a {UMBRAL_MAPE} pasajeros)")
cob = glob.drop_duplicates(subset=["route"])[["route", "n", "n_mape"]].copy()
cob["pct_cubierto"] = (100 * cob["n_mape"] / cob["n"]).round(1)
print(cob.to_string(index=False))

glob.to_csv(SALIDA / "metricas_completas_global.csv", index=False)
reg.to_csv(SALIDA / "metricas_completas_regimen.csv", index=False)
tip.to_csv(SALIDA / "metricas_completas_tipo_dia.csv", index=False)
print(f"\nResultados guardados en {SALIDA}")
