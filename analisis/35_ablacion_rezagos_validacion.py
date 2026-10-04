"""XGBoost sin los seis rezagos en el periodo de validacion (2025-12-25 a
2026-04-01) y predictor mixto: XGBoost completo en regimen ordinario y XGBoost
sin rezagos en regimen raro.

Complementa a `34_importancia_ablacion_xgboost.py`, que hizo la misma ablacion
sobre las 134 jornadas comunes del periodo de evaluacion. No modifica scripts,
freezes ni configuracion.

Fuentes (solo lectura):
  - `observaciones__referencia_combinada_regimen__validacion.csv` (script 25):
    real, regimen, XGBoost completo (identico al de 26 semanas del script 31),
    referencias de 26 y 52 semanas y referencia combinada, por franja, para las
    192 jornadas de validacion.
  - Dataset de modelado y seleccion de hiperparametros de XGBoost (trial 8).

Protocolo de XGBoost sin rezagos: el de la busqueda y del script 31. Por ruta y
jornada (inicio 04:00), ventana de 26 semanas, las 2 ultimas para parada
temprana, `hparam_search.fits.ajustar_predecir_xgboost` con la configuracion
seleccionada (sin reajustar hiperparametros), y las variables de
`seleccionar_features` menos los seis rezagos de demanda y productividad. Se
evalua sobre exactamente las mismas jornadas y franjas del script 25.
Verificacion: un reajuste de XGBoost completo en la primera jornada de cada ruta
debe reproducir las predicciones persistidas.

Metodos reportados (MAE, MedAE, sesgo = prediccion - real, WAPE; globales, por
ruta, por regimen y por ruta y regimen):
  - XGBoost completo
  - XGBoost sin rezagos
  - Mixto completo / sin rezagos (completo en ordinario, sin rezagos en raro)
  - Mixto XGBoost / 52s (completo en ordinario, referencia 52 s en raro)
  - Combinada (26 s en ordinario, 52 s en raro)
  - Referencia (26s)

Salidas en analisis/salidas/ (sufijo __ablacion_rezagos_validacion):
  - observaciones__ablacion_rezagos_validacion.csv
  - metricas__ablacion_rezagos_validacion.csv
  - resumen__ablacion_rezagos_validacion.md
  - manifiesto__ablacion_rezagos_validacion.json

Uso:
    python analisis/35_ablacion_rezagos_validacion.py
"""

import json
import time
from datetime import datetime

import numpy as np
import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.fits import ajustar_predecir_xgboost
from proyecto_grado.modeling.hparam_search.reevaluacion import cargar_configuraciones_seleccionadas
from proyecto_grado.modeling.hparam_search.runner import _preparar_ruta

SUFIJO = "ablacion_rezagos_validacion"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
RUTA_OBS_25 = SALIDA / "observaciones__referencia_combinada_regimen__validacion.csv"
RUTA_METRICAS_25 = SALIDA / "metricas__referencia_combinada_regimen__validacion.csv"
DIRECTORIO_SELECCION = SALIDA / "busqueda_hiperparametros"

RUTA_OBS = SALIDA / f"observaciones__{SUFIJO}.csv"
RUTA_METRICAS = SALIDA / f"metricas__{SUFIJO}.csv"
RUTA_RESUMEN = SALIDA / f"resumen__{SUFIJO}.md"
RUTA_MANIFIESTO = SALIDA / f"manifiesto__{SUFIJO}.json"

VALIDACION_INICIO = "2025-12-25"
VALIDACION_FIN = "2026-04-01"
SEMANAS_ENTRENAMIENTO = 26
TOLERANCIA_REPRODUCCION = 1e-3  # XGBoost predice en float32

REZAGOS = [
    "pasajeros_total_lag_48",
    "pasajeros_total_lag_96",
    "pasajeros_total_lag_336",
    "pasajeros_por_despacho_lag_48",
    "pasajeros_por_despacho_lag_96",
    "pasajeros_por_despacho_lag_336",
]

METODOS = {  # nombre -> columna
    "XGBoost completo": "pred_xgboost",
    "XGBoost sin rezagos": "pred_sin_rezagos",
    "Mixto completo / sin rezagos": "pred_mixto_sin_rezagos",
    "Mixto XGBoost / 52s": "pred_mixto_ref52",
    "Combinada (26s/52s)": "pred_combinada",
    "Referencia (26s)": "pred_ref26",
}
NOMBRES_25 = {
    "XGBoost completo": "XGBoost",
    "Combinada (26s/52s)": "Combinada (26s/52s por regimen)",
    "Referencia (26s)": "Referencia (26s)",
}


def ajustar_dia(d, dia, features, target, params, semanas_parada):
    inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
    fin_dia = inicio_dia + pd.Timedelta(days=1)
    corte = inicio_dia - pd.Timedelta(weeks=semanas_parada)
    train = d[(d["timestamp"] >= inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO))
              & (d["timestamp"] < inicio_dia)]
    fit_df, stop_df = train[train["timestamp"] < corte], train[train["timestamp"] >= corte]
    test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
    pred, arboles = ajustar_predecir_xgboost(fit_df, stop_df, test, features, target, params)
    return test, pred, arboles


def reentrenar(config, df, obs25, params):
    target = config.objetivo
    semanas_parada = config.metodo("XGBoost").semanas_parada_temprana
    filas, verificacion, features_usadas = [], [], {}
    t0 = time.perf_counter()
    for ruta, g in obs25.groupby("route"):
        d = _preparar_ruta(df, ruta, target)
        completas = seleccionar_features(d)
        reducidas = [f for f in completas if f not in REZAGOS]
        assert set(completas) - set(reducidas) == set(REZAGOS), completas
        features_usadas[int(ruta)] = reducidas
        dias = sorted(g["dia_op"].unique())

        # Verificacion del protocolo: XGBoost completo en la primera jornada.
        test, pred, _ = ajustar_dia(d, dias[0], completas, target, params, semanas_parada)
        persistido = g[g["dia_op"] == dias[0]]
        assert list(test["hora"]) == list(persistido["hora"])
        verificacion.append({"route": int(ruta), "dia_op": str(dias[0]),
                             "max_dif": float(np.abs(pred - persistido["pred_xgboost"]).max())})

        for i, dia in enumerate(dias, start=1):
            test, pred, arboles = ajustar_dia(d, dia, reducidas, target, params, semanas_parada)
            filas.append(pd.DataFrame({
                "route": ruta, "dia_op": dia, "hora": test["hora"].to_numpy(),
                "real_reajuste": test[target].to_numpy(), "pred_sin_rezagos": pred,
                "arboles_sin_rezagos": arboles,
            }))
            print(f"  ruta {ruta} [{i:3d}/{len(dias)}] {dia} arboles {arboles}", flush=True)
    minutos = (time.perf_counter() - t0) / 60
    return pd.concat(filas, ignore_index=True), verificacion, features_usadas, minutos


def metricas(real, pred):
    error = pred - real
    absoluto = np.abs(error)
    return {"n": len(real), "demanda_media": real.mean(), "mae": absoluto.mean(),
            "medae": np.median(absoluto), "sesgo": error.mean(),
            "wape": 100 * absoluto.sum() / real.sum()}


def tabla_metricas(obs):
    obs = obs.assign(jornada=obs["route"].astype(str) + "_" + obs["dia_op"].astype(str))
    grupos = [("global", "ambas", "todos", obs)]
    grupos += [("por_ruta", str(r), "todos", g) for r, g in obs.groupby("route")]
    grupos += [("por_regimen", "ambas", reg, g) for reg, g in obs.groupby("regimen")]
    grupos += [("por_ruta_y_regimen", str(r), reg, g)
               for (r, reg), g in obs.groupby(["route", "regimen"])]
    filas = []
    for desagregacion, ruta, regimen, g in grupos:
        for nombre, col in METODOS.items():
            filas.append({"periodo": "validacion", "desagregacion": desagregacion, "route": ruta,
                          "regimen": regimen, "metodo": nombre,
                          "n_jornadas": g["jornada"].nunique(),
                          **metricas(g["real"].to_numpy(), g[col].to_numpy())})
    return pd.DataFrame(filas)


def verificar_25(tabla):
    ref = pd.read_csv(RUTA_METRICAS_25)
    ref = ref[ref["desagregacion"] == "global"].set_index("metodo")
    glob = tabla[tabla["desagregacion"] == "global"].set_index("metodo")
    filas = [{"metodo": m, "mae": glob.loc[m, "mae"], "mae_script25": ref.loc[m25, "mae"],
              "n": int(glob.loc[m, "n"]), "n_script25": int(ref.loc[m25, "n"])}
             for m, m25 in NOMBRES_25.items()]
    v = pd.DataFrame(filas)
    v["coincide"] = ((v["mae"] - v["mae_script25"]).abs() < 1e-4) & (v["n"] == v["n_script25"])
    assert v["coincide"].all(), v
    return v


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",").replace("-", "−")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    return "\n".join(lineas + ["| " + " | ".join(f) + " |" for f in filas])


def bloque_md(tabla, desagregacion, titulo):
    sub = tabla[tabla["desagregacion"] == desagregacion]
    filas = []
    for _, g in sub.groupby(["route", "regimen"], sort=False):
        mejor = g["mae"].min()
        for f in g.to_dict("records"):
            filas.append([f["route"], f["regimen"],
                          f["metodo"] + (" ◆" if f["mae"] - mejor < 1e-9 else ""),
                          f"{f['n']} / {f['n_jornadas']}", coma(f["mae"]), coma(f["medae"]),
                          coma(f["sesgo"]), coma(f["wape"], 1)])
    return [f"## {titulo}", "", tabla_md(
        ["Ruta", "Régimen", "Método", "n / jornadas", "MAE", "MedAE", "Sesgo", "WAPE %"], filas
    ), ""]


def escribir_resumen(tabla, obs, verif_protocolo, verif_25, features, arboles):
    n_jor = obs.groupby("route")["dia_op"].nunique()
    raras = obs[obs["regimen"] == "raro"].groupby("route")["dia_op"].nunique()
    p = [
        "# XGBoost sin rezagos y predictor mixto en el periodo de validación",
        "",
        "Generado por `analisis/35_ablacion_rezagos_validacion.py`.",
        "",
        f"- Validación: {VALIDACION_INICIO} a {VALIDACION_FIN}, {len(obs)} franjas, "
        + ", ".join(f"ruta {r}: {n} jornadas ({raras.get(r, 0)} de régimen raro)"
                    for r, n in n_jor.items()) + ". Mismas jornadas y franjas que el script 25.",
        "- XGBoost sin rezagos: configuración seleccionada (trial 8) sin reajustar, 26 semanas, "
        "2 de parada temprana, variables de `seleccionar_features` sin los seis rezagos ("
        + ", ".join(f"`{f}`" for f in features) + f"). Árboles por ajuste (mediana): {arboles:.0f}.",
        "- Mixto completo / sin rezagos: XGBoost completo en régimen ordinario, XGBoost sin "
        "rezagos en régimen raro. Mixto XGBoost / 52s: XGBoost completo en ordinario, referencia "
        "de 52 semanas en raro. Combinada: 26 s en ordinario, 52 s en raro.",
        "- Dentro de cada régimen, cada mixto coincide con uno de sus componentes; en régimen "
        "ordinario los dos mixtos son idénticos a XGBoost completo.",
        "- Sesgo = predicción − real. WAPE = 100·Σ|error| / Σreal. ◆ = menor MAE del grupo.",
        "- Verificación: el reajuste de XGBoost completo en la primera jornada de cada ruta "
        "reproduce lo persistido (diferencia máxima "
        + ", ".join(f"ruta {v['route']}: {v['max_dif']:.1e}" for v in verif_protocolo)
        + "); el MAE global de XGBoost completo, la combinada y la referencia de 26 s coincide "
        f"con `{RUTA_METRICAS_25.name}` ({'sí' if verif_25['coincide'].all() else 'NO'}).",
        "",
    ]
    p += bloque_md(tabla, "global", "Global")
    p += bloque_md(tabla, "por_ruta", "Por ruta")
    p += bloque_md(tabla, "por_regimen", "Por régimen")
    p += bloque_md(tabla, "por_ruta_y_regimen", "Por ruta y régimen")
    RUTA_RESUMEN.write_text("\n".join(p), encoding="utf-8")


def main():
    config = cargar_configuracion_evaluacion()
    df = pd.read_parquet(config.ruta_dataset)
    params = cargar_configuraciones_seleccionadas(DIRECTORIO_SELECCION)["XGBoost"]
    print(f"Hiperparametros XGBoost: {params}")

    obs25 = pd.read_csv(RUTA_OBS_25)
    obs25["dia_op"] = pd.to_datetime(obs25["dia_op"]).dt.date
    assert str(obs25["dia_op"].min()) >= VALIDACION_INICIO
    assert str(obs25["dia_op"].max()) <= VALIDACION_FIN

    nuevas, verif_protocolo, features, minutos = reentrenar(config, df, obs25, params)
    assert all(v["max_dif"] < TOLERANCIA_REPRODUCCION for v in verif_protocolo), verif_protocolo

    obs = obs25.merge(nuevas, on=["route", "dia_op", "hora"], how="inner")
    assert len(obs) == len(obs25) == len(nuevas), (len(obs), len(obs25), len(nuevas))
    assert np.allclose(obs["real"], obs["real_reajuste"])
    obs = obs.drop(columns="real_reajuste")
    raro = obs["regimen"] == "raro"
    obs["pred_mixto_sin_rezagos"] = np.where(raro, obs["pred_sin_rezagos"], obs["pred_xgboost"])
    obs["pred_mixto_ref52"] = np.where(raro, obs["pred_ref52"], obs["pred_xgboost"])

    tabla = tabla_metricas(obs)
    verif_25 = verificar_25(tabla)

    obs.to_csv(RUTA_OBS, index=False)
    tabla.to_csv(RUTA_METRICAS, index=False)
    arboles = obs.drop_duplicates(["route", "dia_op"])["arboles_sin_rezagos"].median()
    escribir_resumen(tabla, obs, verif_protocolo, verif_25, features[config.rutas[0]], arboles)

    manifiesto = {
        "script": "analisis/35_ablacion_rezagos_validacion.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sufijo": SUFIJO,
        "periodo_validacion": {"inicio": VALIDACION_INICIO, "fin": VALIDACION_FIN},
        "dataset": str(config.ruta_dataset.relative_to(PROJECT_ROOT)),
        "hiperparametros_seleccionados": params,
        "protocolo": {"semanas_entrenamiento": SEMANAS_ENTRENAMIENTO,
                      "semanas_parada_temprana": config.metodo("XGBoost").semanas_parada_temprana},
        "rezagos_excluidos": REZAGOS,
        "features_sin_rezagos": {str(r): f for r, f in features.items()},
        "jornadas_por_ruta": {str(r): int(n) for r, n in obs.groupby("route")["dia_op"].nunique().items()},
        "franjas": len(obs),
        "franjas_raras": int(raro.sum()),
        "definicion_mixtos": {
            "Mixto completo / sin rezagos": "pred_xgboost en ordinario; pred_sin_rezagos en raro",
            "Mixto XGBoost / 52s": "pred_xgboost en ordinario; pred_ref52 en raro",
        },
        "verificacion_protocolo": verif_protocolo,
        "verificacion_script25": verif_25.to_dict("records"),
        "metricas_globales": {
            f["metodo"]: {k: f[k] for k in ("mae", "medae", "sesgo", "wape")}
            for f in tabla[tabla["desagregacion"] == "global"].to_dict("records")
        },
        "minutos_ejecucion": round(minutos, 1),
        "entradas": [str(r.relative_to(PROJECT_ROOT)) for r in (RUTA_OBS_25, RUTA_METRICAS_25)],
        "salidas": [str(r.relative_to(PROJECT_ROOT))
                    for r in (RUTA_OBS, RUTA_METRICAS, RUTA_RESUMEN, RUTA_MANIFIESTO)],
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    cols = ["desagregacion", "route", "regimen", "metodo", "n", "mae", "medae", "sesgo", "wape"]
    print(tabla[tabla["desagregacion"] != "por_ruta_y_regimen"][cols].round(2).to_string(index=False))
    print(f"\nTiempo: {minutos:.1f} min. Resumen: {RUTA_RESUMEN}")


if __name__ == "__main__":
    main()
