"""Entrenamiento de XGBoost sobre un unico fold, escrito paso a paso.

Objetivo: entender que hace el pipeline, reproduciendo a mano un caso simple.
No modifica nada del proyecto.
"""

from collections import defaultdict

import pandas as pd
import xgboost as xgb

# ---------------------------------------------------------------
# 1. Cargar los datos
# ---------------------------------------------------------------
P = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
df = pd.read_parquet(P)
# ver el contenido del DataFrame
print(df.head())

# ver las columnas del DataFrame
print(df.columns)

# imprime una linea divisoria
print("-" * 80)


# Veriifcar si el dataframe tiene dos o mas columnas com los mismos valores
def columnas_duplicadas(df):
    """Agrupa las columnas que tienen exactamente los mismos valores."""
    grupos = defaultdict(list)

    for c in df.columns:
        s = df[c]
        # Huella del contenido: tipo, patron de nulos y valores.
        # Convertir a tupla permite usarla como clave de diccionario.
        huella = (
            str(s.dtype),
            tuple(s.isna().to_numpy()[:200]),  # muestra del patron de nulos
            tuple(s.dropna().astype(str).to_numpy()[:200]),  # muestra de valores
        )
        grupos[huella].append(c)

    # Solo los grupos con mas de una columna
    return [g for g in grupos.values() if len(g) > 1]


candidatos = columnas_duplicadas(df)

print(f"Grupos candidatos: {len(candidatos)}\n")
for g in candidatos:
    # Verificacion exacta sobre todas las filas, no solo la muestra
    base = df[g[0]]
    confirmados = [c for c in g[1:] if ((df[c] == base) | (df[c].isna() & base.isna())).all()]
    if confirmados:
        print(f"{g[0]}  ==  {confirmados}")


# Una sola ruta. Los baselines son por ruta, asi que el modelo tambien.
d = df[df["FK_RUTA"] == 1].copy().sort_values("timestamp")
print("Ruta 1:", d.shape)
print("Rango:", d["timestamp"].min(), "->", d["timestamp"].max())

# ---------------------------------------------------------------
# 2. Definir el corte temporal
# ---------------------------------------------------------------
# En series temporales NO se puede partir al azar: el modelo veria el futuro.
# Entrenamos con todo lo anterior al corte, evaluamos las 2 semanas siguientes.
CORTE = pd.Timestamp("2026-03-19 04:00:00")  # inicio de la validacion
FIN = pd.Timestamp("2026-04-02 04:00:00")  # fin de la validacion

train = d[d["timestamp"] < CORTE]
val = d[(d["timestamp"] >= CORTE) & (d["timestamp"] < FIN)]

print(f"\nEntrenamiento: {len(train)} filas hasta {CORTE.date()}")
print(f"Validacion:    {len(val)} filas de {CORTE.date()} a {FIN.date()}")

# ---------------------------------------------------------------
# 3. Elegir las features
# ---------------------------------------------------------------
TARGET = "pasajeros_total"

# se defienen las columnas a excluir del entrenamiento, por ser duplicadas o irrelevantes
EXCLUIR = {
    # constantes
    "dataset_version",
    "source_hash",
    "granularidad_min",
    "target",
    "target_col",
    "scenario",
    "feature_set",
    "observed_flag",
    "FK_RUTA",
    # marcas temporales (no extrapolables)
    "timestamp",
    "target_interval_start",
    "target_interval_end",
    "feature_cutoff_timestamp",
    # target y derivados
    "pasajeros_total",
    "pasajeros_por_despacho_real",
    "despachos_count_real",
    # banderas del resultado
    "target_observed",
    "target_pasajeros_total_observed",
    "target_pasajeros_por_despacho_observed",
    "is_gap",
    "gap_tipo",
    # texto sin codificar
    "tipo_dia",
    "franja_horaria",
    # alias duplicados confirmados
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_48",
    "lag_96",
    "lag_336",
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_mean_12",
    "rolling_std_6",
    "rolling_std_12",
}

# El escenario es "sin_oferta": el modelo no debe ver informacion de despachos.
# Ademas, el conteo de despachos tampoco se consolida hasta que el vehiculo
# retorna, asi que no estaria disponible en el momento de la decision.
EXCLUIR |= {c for c in df.columns if c.startswith("despachos_count_real")}

features = [c for c in d.columns if c not in EXCLUIR]
# Solo columnas numericas: XGBoost no acepta texto sin codificar.
features = [c for c in features if pd.api.types.is_numeric_dtype(d[c])]

print(f"\nFeatures usadas: {len(features)}")
print(features)

# Solo filas donde el target existe (excluye huecos operativos).
train = train[train[TARGET].notna()]
val = val[val[TARGET].notna()]

X_train, y_train = train[features], train[TARGET]
X_val, y_val = val[features], val[TARGET]

# ---------------------------------------------------------------
# 4. Entrenar
# ---------------------------------------------------------------
modelo = xgb.XGBRegressor(
    objective="reg:absoluteerror",  # aprende la mediana condicional
    eval_metric="mae",
    max_depth=5,
    min_child_weight=5,
    learning_rate=0.05,
    n_estimators=2000,  # techo alto; la parada temprana decide
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    early_stopping_rounds=50,
    random_state=42,
)

# Las ultimas 2 semanas del entrenamiento se reservan para la parada temprana.
# Asi la validacion no influye en ninguna decision y su metrica es honesta.
CORTE_ES = CORTE - pd.Timedelta(weeks=2)

fit = train[train["timestamp"] < CORTE_ES]
stop = train[train["timestamp"] >= CORTE_ES]

print(f"Ajuste: {len(fit)} filas | Parada temprana: {len(stop)} filas")

X_fit, y_fit = fit[features], fit[TARGET]
X_stop, y_stop = stop[features], stop[TARGET]

modelo.fit(X_fit, y_fit, eval_set=[(X_stop, y_stop)], verbose=False)

print(f"\nArboles construidos: {modelo.best_iteration + 1}")

# ---------------------------------------------------------------
# 5. Predecir y medir
# ---------------------------------------------------------------
val = val.copy()
val["y_pred"] = modelo.predict(X_val)
val["error"] = val["y_pred"] - val[TARGET]  # positivo = sobreprediccion

mae = val["error"].abs().mean()
sesgo = val["error"].mean()

print(f"\nMAE:   {mae:.2f}")
print(f"Sesgo: {sesgo:+.2f}")
print(f"Demanda media observada: {val[TARGET].mean():.2f}")

# ---------------------------------------------------------------
# 6. Que variables pesaron
# ---------------------------------------------------------------
imp = (
    pd.Series(modelo.get_booster().get_score(importance_type="gain"))
    .sort_values(ascending=False)
    .head(15)
)
print("\n--- Top 15 features por ganancia ---")
print(imp.round(1).to_string())

print("Ajuste hasta:", fit["timestamp"].max())
print("Parada:", stop["timestamp"].min(), "->", stop["timestamp"].max())
print("Validacion:", val["timestamp"].min(), "->", val["timestamp"].max())

val["dia_op"] = (val["timestamp"] - pd.Timedelta(hours=4)).dt.date

print("--- Sesgo por hora ---")
print(val.groupby("hora_del_dia")["error"].agg(["size", "mean"]).round(2).to_string())

print("\n--- Sesgo por tipo de dia ---")
print(val.groupby("tipo_dia")["error"].agg(["size", "mean"]).round(2).to_string())

print("\n--- Peores dias ---")
por_dia = val.groupby("dia_op").agg(
    n=("error", "size"), sesgo=("error", "mean"), real=(TARGET, "mean")
)
print(por_dia.sort_values("sesgo", ascending=False).head(8).round(2).to_string())

arboles = modelo.get_booster().get_dump()
print(f"Arboles construidos: {len(arboles)}")
print(arboles[0])
