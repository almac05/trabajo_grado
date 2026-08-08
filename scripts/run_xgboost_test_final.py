"""Evaluacion de la configuracion elegida sobre el test final.

Configuracion adoptada tras el barrido de ventanas (analisis 03-05):
  - Ventana de entrenamiento: 26 semanas.
  - Sin variables de calendario anual (semana_anio, mes): con ventanas largas
    inducen memorizacion, porque cada valor identifica un bloque unico.
  - Sin rezagos cortos ni medias moviles: los pasajeros de una franja solo se
    consolidan cuando el vehiculo termina el recorrido (mediana 159 min), de
    modo que no estan disponibles en el momento de decidir el despacho.

ADVERTENCIA: el test final se evalua UNA SOLA VEZ. Si se mira el resultado y
se ajusta la configuracion, deja de ser un test limpio y no queda periodo de
reserva para sustituirlo.

Uso:
    python analisis/06_test_final.py
"""

from pathlib import Path

import pandas as pd
import xgboost as xgb

# ---------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA_DIR = Path("analisis/salidas")

RUTAS = [1, 3]
TARGET = "pasajeros_total"

# Test final: ultimas 10 semanas del dataset. El barrido de ventanas uso cortes
# anteriores al 19 de marzo, asi que este periodo nunca se toco.
CORTE = pd.Timestamp("2026-04-02 04:00:00")
FIN = pd.Timestamp("2026-06-11 04:00:00")

SEMANAS_ENTRENAMIENTO = 26
PARADA_SEMANAS = 2

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
# Seleccion de features
# ---------------------------------------------------------------

EXCLUIR_BASE = {
    # constantes dentro del archivo
    "dataset_version",
    "source_hash",
    "granularidad_min",
    "target",
    "target_col",
    "scenario",
    "feature_set",
    "observed_flag",
    "FK_RUTA",
    # marcas temporales: los arboles no extrapolan
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
    # calendario anual: induce memorizacion con ventanas largas
    "semana_anio",
    "mes",
}

SUFIJOS_NO_DISPONIBLES = (
    "_lag_1",
    "_lag_2",
    "_lag_3",
    "_rolling_mean_3",
    "_rolling_mean_6",
    "_rolling_mean_12",
    "_rolling_std_6",
    "_rolling_std_12",
)


def seleccionar_features(d: pd.DataFrame) -> list[str]:
    """Devuelve las features disponibles en el momento de la decision."""
    excluir = set(EXCLUIR_BASE)
    # Escenario sin_oferta: sin informacion de despachos. Ademas el conteo
    # tampoco se consolida hasta que el vehiculo retorna.
    excluir |= {c for c in d.columns if c.startswith("despachos_count_real")}
    excluir |= {c for c in d.columns if c.endswith(SUFIJOS_NO_DISPONIBLES)}
    return [c for c in d.columns if c not in excluir and pd.api.types.is_numeric_dtype(d[c])]


# ---------------------------------------------------------------
# Evaluacion
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)

corte_parada = CORTE - pd.Timedelta(weeks=PARADA_SEMANAS)
inicio = CORTE - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)

print(f"Ventana de entrenamiento: {SEMANAS_ENTRENAMIENTO} semanas")
print(f"Ajuste:          {inicio.date()} -> {corte_parada.date()}")
print(f"Parada temprana: {corte_parada.date()} -> {CORTE.date()}")
print(f"Test final:      {CORTE.date()} -> {FIN.date()}")

predicciones = []
importancias = []

for ruta in RUTAS:
    d = df[df["FK_RUTA"] == ruta].copy().sort_values("timestamp")
    features = seleccionar_features(d)

    if ruta == RUTAS[0]:
        print(f"\nFeatures usadas: {len(features)}")
        for c in features:
            print(f"  {c}")

    train = d[(d["timestamp"] >= inicio) & (d["timestamp"] < CORTE)]
    train = train[train[TARGET].notna()]
    fit = train[train["timestamp"] < corte_parada]
    stop = train[train["timestamp"] >= corte_parada]

    test = d[(d["timestamp"] >= CORTE) & (d["timestamp"] < FIN)]
    test = test[test[TARGET].notna()].copy()

    modelo = xgb.XGBRegressor(**PARAMS)
    modelo.fit(
        fit[features],
        fit[TARGET],
        eval_set=[(stop[features], stop[TARGET])],
        verbose=False,
    )

    test["y_pred"] = modelo.predict(test[features])
    test["error"] = test["y_pred"] - test[TARGET]
    test["route"] = ruta
    test["regimen"] = test["tipo_dia"].isin(TIPOS_RAROS).map({True: "raro", False: "ordinario"})
    test["dia_op"] = (test["timestamp"] - pd.Timedelta(hours=4)).dt.date

    predicciones.append(test)

    imp = pd.Series(modelo.get_booster().get_score(importance_type="gain"))
    importancias.append(imp.rename(f"ruta_{ruta}"))

    print(
        f"\nRuta {ruta}: ajuste {len(fit)} filas | parada {len(stop)} | "
        f"test {len(test)} | arboles {modelo.best_iteration + 1}"
    )

p = pd.concat(predicciones, ignore_index=True)

# ---------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------


def resumen(g: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "n": len(g),
            "demanda_media": g[TARGET].mean(),
            "mae": g["error"].abs().mean(),
            "sesgo": g["error"].mean(),
            "sesgo_pct": 100 * g["error"].mean() / g[TARGET].mean(),
            "pct_sobrepred": 100 * (g["error"] > 0).mean(),
        }
    )


print("\n" + "=" * 70)
print("RESULTADOS DEL TEST FINAL — por regimen")
print(p.groupby(["route", "regimen"]).apply(resumen, include_groups=False).round(2).to_string())

print("\nPor tipo de dia")
print(p.groupby(["route", "tipo_dia"]).apply(resumen, include_groups=False).round(2).to_string())

print("\nSesgo por hora (verificacion de cancelacion de errores)")
print(
    p.pivot_table(index="hora_del_dia", columns="route", values="error", aggfunc="mean")
    .round(2)
    .to_string()
)

print("\nDias con mayor sobreprediccion")
por_dia = (
    p.groupby(["route", "dia_op"])
    .agg(
        n=("error", "size"),
        sesgo=("error", "mean"),
        real=(TARGET, "mean"),
        tipo=("tipo_dia", "first"),
    )
    .reset_index()
)
print(por_dia.sort_values("sesgo", ascending=False).head(10).round(2).to_string(index=False))

print("\nImportancia de variables (gain)")
imp = pd.concat(importancias, axis=1).fillna(0)
print(imp.sort_values(imp.columns[0], ascending=False).round(1).to_string())

SALIDA_DIR.mkdir(parents=True, exist_ok=True)
cols = [
    "route",
    "timestamp",
    "dia_op",
    "tipo_dia",
    "regimen",
    "hora_del_dia",
    TARGET,
    "y_pred",
    "error",
]
p[cols].to_csv(SALIDA_DIR / "test_final_predicciones.csv", index=False)
por_dia.to_csv(SALIDA_DIR / "test_final_por_dia.csv", index=False)
imp.to_csv(SALIDA_DIR / "test_final_importancia.csv")

print(f"\nArtefactos guardados en {SALIDA_DIR}")
