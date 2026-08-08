"""Barrido de la ventana de entrenamiento de XGBoost.

Pregunta: cuanta historia conviene usar para entrenar el modelo?

Hipotesis de partida: entrenar con el historico completo arrastra el nivel de
demanda del periodo previo a la contraccion de flota (63 -> 42 vehiculos), lo
que produce sobrepredicion sistematica. Acortar la ventana deberia reducir ese
sesgo, igual que ocurre con el baseline de promedio movil.

Diseno: 6 cortes temporales separados 8 semanas (para que las ventanas de
validacion no se solapen), cada uno evaluando 7 ventanas de entrenamiento.
Todos los modelos de un mismo corte se evaluan sobre exactamente las mismas
observaciones, de modo que la diferencia entre ellos aisla el efecto de la
ventana.

IMPORTANTE: "ventana de entrenamiento" es hacia atras (cuanta historia se usa),
no el horizonte de prediccion, que es fijo en una franja de 30 minutos.

Uso:
    python analisis/03_barrido_ventana_entrenamiento.py
"""

from pathlib import Path

import pandas as pd
import xgboost as xgb

# ---------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"

RUTA = 3
TARGET = "pasajeros_total"

SALIDA = Path(f"analisis/salidas/barrido_disponibilidad_real_r{RUTA}.csv")

# El corte base se situa antes del test final (2 abril - 10 junio 2026), de modo
# que este analisis no toca los datos reservados para reportar resultados.
CORTE_BASE = pd.Timestamp("2026-03-19 04:00:00")
N_CORTES = 6
SEPARACION_CORTES = 8  # semanas; > 2 evita solapamiento entre validaciones

VALIDACION_SEMANAS = 2
PARADA_SEMANAS = 2  # ultimas semanas del entrenamiento, para parada temprana

VENTANAS_ENTRENAMIENTO = [8, 10, 13, 26, 52, 78, None]  # None = todo el historico

MIN_FILAS_AJUSTE = 500

TIPOS_RAROS = ["FESTIVO", "FESTIVO_PUENTE"]

PARAMS = {
    "objective": "reg:absoluteerror",  # aprende la mediana condicional
    "eval_metric": "mae",
    "max_depth": 5,
    "min_child_weight": 5,
    "learning_rate": 0.05,
    "n_estimators": 2000,  # techo alto; la parada temprana decide
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "early_stopping_rounds": 50,
    "random_state": 42,
}

# ---------------------------------------------------------------
# 1. Cargar y filtrar
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)

# Un modelo por ruta: los baselines tambien son por ruta, asi la comparacion
# es directa y cada ruta puede aprender su propia estructura.
d = df[df["FK_RUTA"] == RUTA].copy().sort_values("timestamp")

print(f"Ruta {RUTA}: {d.shape[0]} filas")
print(f"Rango: {d['timestamp'].min()} -> {d['timestamp'].max()}")

# ---------------------------------------------------------------
# 2. Seleccionar features
# ---------------------------------------------------------------

EXCLUIR = {
    # constantes dentro del archivo: no aportan informacion
    "dataset_version",
    "source_hash",
    "granularidad_min",
    "target",
    "target_col",
    "scenario",
    "feature_set",
    "observed_flag",
    "FK_RUTA",
    # marcas temporales: los arboles no extrapolan, y una fecha siempre crece
    "timestamp",
    "target_interval_start",
    "target_interval_end",
    "feature_cutoff_timestamp",
    # el target y variables que lo contienen
    "pasajeros_total",
    "pasajeros_por_despacho_real",
    # banderas que describen el resultado de la franja
    "target_observed",
    "target_pasajeros_total_observed",
    "target_pasajeros_por_despacho_observed",
    "is_gap",
    "gap_tipo",
    # texto sin codificar
    "tipo_dia",
    "franja_horaria",
    # alias duplicados del target (verificados identicos)
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

# El escenario es "sin_oferta": no debe usar informacion de despachos. Ademas,
# el conteo de despachos no se consolida hasta que el vehiculo retorna, asi que
# tampoco estaria disponible en el momento de la decision.
EXCLUIR |= {c for c in d.columns if c.startswith("despachos_count_real")}

features = [c for c in d.columns if c not in EXCLUIR and pd.api.types.is_numeric_dtype(d[c])]

# Hipotesis: con una ventana de exactamente 52 semanas, cada valor de
# semana_anio identifica un unico bloque de datos, de modo que el modelo puede
# usarlo para memorizar en lugar de generalizar. Con ventanas mas largas cada
# valor aparece dos o mas veces y el efecto se diluye.
CALENDARIO_ANUAL = {"semana_anio", "mes"}
features = [c for c in features if c not in CALENDARIO_ANUAL]

# Restriccion de disponibilidad: los pasajeros de una franja solo se consolidan
# cuando el vehiculo termina el recorrido (mediana 159 min). En el momento de
# decidir el despacho, las franjas recientes aun no estan cargadas.
# Se excluyen los rezagos cortos y las medias moviles que dependen de ellas.
NO_DISPONIBLES = {
    c
    for c in features
    if c.endswith(("_lag_1", "_lag_2", "_lag_3"))
    or c.endswith(
        (
            "_rolling_mean_3",
            "_rolling_mean_6",
            "_rolling_mean_12",
            "_rolling_std_6",
            "_rolling_std_12",
        )
    )
}
features = [c for c in features if c not in NO_DISPONIBLES]

print(f"\nExcluidas por disponibilidad: {len(NO_DISPONIBLES)}")
print(sorted(NO_DISPONIBLES))

print(f"\nFeatures usadas: {len(features)}")
print(features)

# ---------------------------------------------------------------
# 3. Barrido
# ---------------------------------------------------------------

cortes = [CORTE_BASE - pd.Timedelta(weeks=SEPARACION_CORTES * i) for i in range(N_CORTES)]

inicio_dataset = d["timestamp"].min()
resultados = []

for i, corte in enumerate(cortes, start=1):
    fin_val = corte + pd.Timedelta(weeks=VALIDACION_SEMANAS)
    corte_parada = corte - pd.Timedelta(weeks=PARADA_SEMANAS)

    # Validacion: identica para todas las ventanas de este corte, de modo que
    # la comparacion entre ellas no dependa de que periodo les toco.
    val = d[(d["timestamp"] >= corte) & (d["timestamp"] < fin_val)]
    val = val[val[TARGET].notna()].copy()
    val["regimen"] = val["tipo_dia"].isin(TIPOS_RAROS).map({True: "raro", False: "ordinario"})

    print(f"\nCorte {i}: validacion {corte.date()} -> {fin_val.date()} ({len(val)} filas)")

    for semanas in VENTANAS_ENTRENAMIENTO:
        if semanas is None:
            inicio = inicio_dataset
            etiqueta = "todo"
        else:
            inicio = corte - pd.Timedelta(weeks=semanas)
            etiqueta = f"{semanas}s"
            # Si la ventana excede el dataset, el entrenamiento seria mas corto
            # de lo declarado y no comparable con los demas cortes.
            if inicio < inicio_dataset:
                print(f"  ventana={etiqueta:5s} excede el dataset, se omite")
                continue

        train = d[(d["timestamp"] >= inicio) & (d["timestamp"] < corte)]
        train = train[train[TARGET].notna()]

        # Las ultimas semanas del entrenamiento se reservan para la parada
        # temprana: asi la validacion no influye en ninguna decision.
        fit = train[train["timestamp"] < corte_parada]
        stop = train[train["timestamp"] >= corte_parada]

        if len(fit) < MIN_FILAS_AJUSTE or len(stop) == 0:
            print(f"  ventana={etiqueta:5s} filas insuficientes, se omite")
            continue

        print(
            f"  ventana={etiqueta:5s} ajuste: {fit['timestamp'].min().date()} -> "
            f"{fit['timestamp'].max().date()}  ({len(fit)} filas)"
        )

        modelo = xgb.XGBRegressor(**PARAMS)
        modelo.fit(
            fit[features],
            fit[TARGET],
            eval_set=[(stop[features], stop[TARGET])],
            verbose=False,
        )

        val_v = val.copy()
        val_v["error"] = modelo.predict(val_v[features]) - val_v[TARGET]

        # Una fila por regimen: el comportamiento difiere radicalmente entre
        # dias ordinarios y festivos, y promediarlos juntos lo ocultaria.
        for regimen, g in val_v.groupby("regimen"):
            resultados.append(
                {
                    "corte": corte.date(),
                    "semanas_entrenamiento": semanas if semanas else 999,
                    "regimen": regimen,
                    "n": len(g),
                    "demanda_media": g[TARGET].mean(),
                    "filas_ajuste": len(fit),
                    "arboles": modelo.best_iteration + 1,
                    "mae": g["error"].abs().mean(),
                    "sesgo": g["error"].mean(),
                }
            )

# ---------------------------------------------------------------
# 4. Resultados
# ---------------------------------------------------------------

r = pd.DataFrame(resultados)
SALIDA.parent.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA, index=False)


def tabla(valores, agg="mean"):
    return (
        r.pivot_table(
            index="semanas_entrenamiento",
            columns="regimen",
            values=valores,
            aggfunc=agg,
        )
        .round(2)
        .to_string()
    )


print("\n" + "=" * 60)
print("SESGO medio entre cortes")
print(tabla("sesgo"))

print("\nMAE medio entre cortes")
print(tabla("mae"))

print("\nDispersion del sesgo entre cortes (std)")
print(tabla("sesgo", "std"))

print("\nCortes evaluados y observaciones totales")
print(
    r.pivot_table(
        index="semanas_entrenamiento",
        columns="regimen",
        values=["corte", "n"],
        aggfunc={"corte": "count", "n": "sum"},
    ).to_string()
)

print(f"\nDetalle guardado en {SALIDA}")
