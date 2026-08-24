"""Barrido de la ventana de entrenamiento con reentrenamiento diario.

Verifica si el compromiso identificado en el barrido previo se sostiene bajo el
protocolo definitivo. El barrido original evaluaba dos semanas por corte sobre
seis cortes, y su muestra comprendia unicamente dias laborales y sabados. Esta
version evalua una jornada por corte sobre la totalidad del conjunto de prueba,
de modo que incorpora domingos y festivos --precisamente los regimenes donde la
ventana de entrenamiento resulta determinante.

La pregunta es doble: si el sesgo sigue creciendo con la ventana en dias
ordinarios y decreciendo en festivos, y si el punto de cruce se mantiene en
torno a las veintiseis semanas adoptadas.

Uso:
    python analisis/13_barrido_ventana_diario.py
"""

import time
from pathlib import Path

import pandas as pd
import xgboost as xgb

from proyecto_grado.modeling.experimentos import PARAMS_XGB, seleccionar_features

# ---------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")

RUTAS = (1, 3)
TARGET = "pasajeros_total"

INICIO_TEST = pd.Timestamp("2026-04-02")
FIN_TEST = pd.Timestamp("2026-06-10")

# Se omiten 10 y 78 semanas del barrido previo: la primera aportaba poco entre
# 8 y 13, y la segunda excedia el inicio del dataset en buena parte del periodo.
VENTANAS = [8, 13, 26, 52, None]   # None = todo el historico disponible

PARADA_SEMANAS = 2
MIN_FRANJAS = 8

TIPOS_RAROS = ("FESTIVO", "FESTIVO_PUENTE")

# ---------------------------------------------------------------
# 2. Barrido
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)
resultados = []
t_inicio = time.perf_counter()

for ruta in RUTAS:
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    # Las features no dependen de la ventana ni de la jornada.
    features = seleccionar_features(d)
    inicio_datos = d["timestamp"].min()

    conteo = d.groupby("dia_op").size()
    dias = sorted(
        dia for dia, n in conteo.items()
        if INICIO_TEST.date() <= dia <= FIN_TEST.date() and n >= MIN_FRANJAS
    )

    print(f"\n{'=' * 60}")
    print(f"Ruta {ruta}: {len(dias)} jornadas x {len(VENTANAS)} ventanas")

    for i, dia in enumerate(dias, start=1):
        inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
        fin_dia = inicio_dia + pd.Timedelta(days=1)
        corte_parada = inicio_dia - pd.Timedelta(weeks=PARADA_SEMANAS)

        test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
        if len(test) < MIN_FRANJAS:
            continue

        tipo = test["tipo_dia"].iloc[0]
        regimen = "raro" if tipo in TIPOS_RAROS else "ordinario"
        real = test[TARGET].to_numpy()

        linea = f"  [{i:3d}/{len(dias)}] {dia} {tipo:14s}"

        for semanas in VENTANAS:
            if semanas is None:
                inicio_train = inicio_datos
                etiqueta = "todo"
            else:
                inicio_train = inicio_dia - pd.Timedelta(weeks=semanas)
                etiqueta = f"{semanas}s"
                # Si la ventana excede el inicio del dataset, el entrenamiento
                # seria mas corto de lo declarado y no comparable entre dias.
                if inicio_train < inicio_datos:
                    continue

            train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
            fit = train[train["timestamp"] < corte_parada]
            stop = train[train["timestamp"] >= corte_parada]

            if len(fit) < 500 or len(stop) == 0:
                continue

            modelo = xgb.XGBRegressor(**PARAMS_XGB)
            modelo.fit(
                fit[features], fit[TARGET],
                eval_set=[(stop[features], stop[TARGET])],
                verbose=False,
            )
            error = modelo.predict(test[features]) - real

            resultados.append({
                "route": ruta,
                "dia_op": dia,
                "tipo_dia": tipo,
                "regimen": regimen,
                "semanas_entrenamiento": semanas if semanas else 999,
                "n": len(test),
                "demanda_media": real.mean(),
                "filas_ajuste": len(fit),
                "arboles": modelo.best_iteration + 1,
                "mae": abs(error).mean(),
                "sesgo": error.mean(),
            })

            linea += f" | {etiqueta}: {abs(error).mean():5.1f}"

        print(linea)

print(f"\nTiempo total: {(time.perf_counter() - t_inicio) / 60:.1f} min")

# ---------------------------------------------------------------
# 3. Resultados
# ---------------------------------------------------------------

r = pd.DataFrame(resultados)
SALIDA.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA / "barrido_ventana_diario.csv", index=False)


def tabla(valor: str, agg: str = "mean") -> str:
    return (
        r.pivot_table(
            index="semanas_entrenamiento",
            columns=["regimen", "route"],
            values=valor,
            aggfunc=agg,
        )
        .round(2)
        .to_string()
    )


print("\n" + "=" * 70)
print("SESGO MEDIO por ventana, regimen y ruta")
print(tabla("sesgo"))

print("\nMAE MEDIO por ventana, regimen y ruta")
print(tabla("mae"))

print("\nDISPERSION DEL SESGO entre jornadas (std)")
print(tabla("sesgo", "std"))

print("\nDESGLOSE POR TIPO DE DIA (sesgo medio, Ruta 1)")
print(
    r[r["route"] == 1]
    .pivot_table(index="semanas_entrenamiento", columns="tipo_dia", values="sesgo")
    .round(2)
    .to_string()
)

print("\nDESGLOSE POR TIPO DE DIA (sesgo medio, Ruta 3)")
print(
    r[r["route"] == 3]
    .pivot_table(index="semanas_entrenamiento", columns="tipo_dia", values="sesgo")
    .round(2)
    .to_string()
)

print("\nJORNADAS EVALUADAS por ventana y regimen")
print(
    r.pivot_table(
        index="semanas_entrenamiento", columns="regimen",
        values="dia_op", aggfunc="count",
    ).to_string()
)

print(f"\nDetalle guardado en {SALIDA / 'barrido_ventana_diario.csv'}")
