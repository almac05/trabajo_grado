"""Barrido de la ventana de entrenamiento de XGBoost sobre el periodo de validacion,
con la configuracion seleccionada por la busqueda de hiperparametros.

Repite el barrido de analisis/13_barrido_ventana_diario.py cambiando tres cosas,
y solo tres:
  - Periodo: validacion de la busqueda (2025-12-25 a 2026-04-01, extremos
    inclusivos), leido de configs/modeling/busqueda_hiperparametros.yaml. El
    barrido original evaluaba 2026-04-02 a 2026-06-10.
  - Hiperparametros: trial seleccionado en
    analisis/salidas/busqueda_hiperparametros/seleccion__xgboost.json, sobre los
    fijos XGBOOST_FIJOS. El original usaba PARAMS_XGB (experimentos.py).
  - Datos: el dataset de modelado vigente, cuya columna `pasajeros_total` se
    construye desde PASAJEROS_REALES desde el 2026-08-23. El CSV del barrido
    original (2026-08-10) es anterior a esa correccion.

Protocolo (identico al de la busqueda, hparam_search/runner.py, para XGBoost, y
al del barrido original): por ruta y por jornada operativa (inicio 04:00) con al
menos `min_franjas` franjas, reentrenamiento diario con los datos anteriores al
inicio de la jornada dentro de la ventana; las ultimas `semanas_parada_temprana`
semanas de la ventana se reservan para la parada temprana. El ajuste y la
prediccion se hacen con hparam_search.fits.ajustar_predecir_xgboost, la misma
funcion que uso la busqueda. Ventanas: 8, 13, 26, 52 semanas y registro
completo (codigo 999, desde el primer registro de la ruta). Una ventana que
excede el inicio del dataset se omite, como en el original.

Verificacion incorporada: la ventana de 26 semanas es exactamente la condicion
bajo la que la busqueda evaluo el trial seleccionado, por lo que su MAE y su
sesgo globales deben coincidir con los de seleccion__xgboost.json.

Metricas: MAE y sesgo (prediccion - real) ponderados por observaciones, es decir,
calculados sobre todas las franjas del grupo; por jornada se persisten mae,
sesgo y n, de modo que sum(metrica * n) / sum(n) reproduce los agregados.

Salidas en analisis/salidas/ (sufijo __validacion_hparam):
  - barrido_ventana_diario__validacion_hparam.csv: una fila por jornada y
    ventana, mismas columnas que barrido_ventana_diario.csv.
  - observaciones__barrido_ventana__validacion_hparam.csv: real y prediccion
    por franja, jornada y ventana.
  - resumen__barrido_ventana__validacion_hparam.md: tablas por ventana y
    comparacion del patron de sesgo con el barrido original.
  - manifiesto__barrido_ventana__validacion_hparam.json: origen, parametros,
    conteos, verificacion y resultados principales.

Uso:
    python analisis/31_barrido_ventana_validacion_hparam.py
"""

import json
import time
from datetime import datetime

import numpy as np
import pandas as pd

from proyecto_grado.etl.config import PROJECT_ROOT
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.fits import ajustar_predecir_xgboost
from proyecto_grado.modeling.hparam_search.search_config import cargar_configuracion_busqueda
from proyecto_grado.modeling.hparam_search.spaces import XGBOOST_FIJOS

SUFIJO = "validacion_hparam"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
RUTA_SELECCION = SALIDA / "busqueda_hiperparametros" / "seleccion__xgboost.json"
RUTA_ORIGINAL = SALIDA / "barrido_ventana_diario.csv"
RUTA_DIARIO = SALIDA / f"barrido_ventana_diario__{SUFIJO}.csv"
RUTA_OBS = SALIDA / f"observaciones__barrido_ventana__{SUFIJO}.csv"
RUTA_RESUMEN = SALIDA / f"resumen__barrido_ventana__{SUFIJO}.md"
RUTA_MANIFIESTO = SALIDA / f"manifiesto__barrido_ventana__{SUFIJO}.json"

VENTANAS = [8, 13, 26, 52, None]  # None = registro completo
CODIGO_COMPLETO = 999
ETIQUETA_VENTANA = {8: "8", 13: "13", 26: "26", 52: "52", CODIGO_COMPLETO: "Completo"}
TIPOS_DIA = ["LABORAL", "SABADO", "DOMINGO", "FESTIVO", "FESTIVO_PUENTE"]
HIPERPARAMETROS = [
    "max_depth",
    "min_child_weight",
    "learning_rate",
    "subsample",
    "colsample_bytree",
    "reg_lambda",
    "reg_alpha",
]
ENTEROS = {"max_depth", "min_child_weight"}
TOLERANCIA_VERIFICACION = 1e-6


def cargar_hiperparametros():
    seleccion = json.loads(RUTA_SELECCION.read_text(encoding="utf-8"))
    trial = seleccion["trial_seleccionado"]
    params = {
        clave: int(trial[clave]) if clave in ENTEROS else float(trial[clave])
        for clave in HIPERPARAMETROS
    }
    return seleccion, params


def preparar_ruta(df, ruta, target):
    # Misma preparacion que hparam_search/runner.py::_preparar_ruta.
    d = df[(df["FK_RUTA"] == ruta) & df[target].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    return d


def barrer(df, config, params):
    evaluacion = config.evaluacion
    target = evaluacion.objetivo
    semanas_parada = evaluacion.metodo("XGBoost").semanas_parada_temprana
    min_franjas = evaluacion.min_franjas
    tipos_raros = tuple(evaluacion.tipos_baja_frecuencia)
    inicio_val = config.inicio_validacion
    fin_val = config.fin_validacion

    filas, observaciones, omitidas = [], [], []
    t0 = time.perf_counter()
    for ruta in evaluacion.rutas:
        d = preparar_ruta(df, ruta, target)
        features = seleccionar_features(d)
        inicio_datos = d["timestamp"].min()
        conteo = d.groupby("dia_op").size()
        dias = sorted(
            dia for dia, n in conteo.items() if inicio_val <= dia <= fin_val and n >= min_franjas
        )[:: evaluacion.paso_muestreo]
        print(f"\nRuta {ruta}: {len(dias)} jornadas x {len(VENTANAS)} ventanas", flush=True)

        for i, dia in enumerate(dias, start=1):
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            corte_parada = inicio_dia - pd.Timedelta(weeks=semanas_parada)
            test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
            if len(test) < min_franjas:
                continue
            tipo = test["tipo_dia"].iloc[0]
            regimen = "raro" if tipo in tipos_raros else "ordinario"
            real = test[target].to_numpy()
            linea = f"  [{i:3d}/{len(dias)}] {dia} {tipo:14s}"

            for semanas in VENTANAS:
                codigo = semanas if semanas is not None else CODIGO_COMPLETO
                if semanas is None:
                    inicio_train = inicio_datos
                else:
                    inicio_train = inicio_dia - pd.Timedelta(weeks=semanas)
                    if inicio_train < inicio_datos:
                        omitidas.append((ruta, str(dia), codigo, "ventana excede el dataset"))
                        continue
                train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
                fit_df = train[train["timestamp"] < corte_parada]
                stop_df = train[train["timestamp"] >= corte_parada]
                if len(fit_df) < 500 or len(stop_df) == 0:
                    omitidas.append((ruta, str(dia), codigo, "datos de ajuste insuficientes"))
                    continue

                pred, arboles = ajustar_predecir_xgboost(
                    fit_df, stop_df, test, features, target, params
                )
                error = pred - real
                filas.append(
                    {
                        "route": ruta,
                        "dia_op": dia,
                        "tipo_dia": tipo,
                        "regimen": regimen,
                        "semanas_entrenamiento": codigo,
                        "n": len(test),
                        "demanda_media": real.mean(),
                        "filas_ajuste": len(fit_df),
                        "arboles": arboles,
                        "mae": np.abs(error).mean(),
                        "sesgo": error.mean(),
                    }
                )
                observaciones.append(
                    pd.DataFrame(
                        {
                            "route": ruta,
                            "dia_op": dia,
                            "tipo_dia": tipo,
                            "semanas_entrenamiento": codigo,
                            "timestamp": test["timestamp"].to_numpy(),
                            "real": real,
                            "pred": pred,
                        }
                    )
                )
                linea += f" | {ETIQUETA_VENTANA[codigo]}: {np.abs(error).mean():5.1f}"
            print(linea, flush=True)

    minutos = (time.perf_counter() - t0) / 60
    print(f"\nTiempo total: {minutos:.1f} min", flush=True)
    return pd.DataFrame(filas), pd.concat(observaciones, ignore_index=True), omitidas, minutos


def ponderado(df, claves):
    aux = df.assign(ae_n=df["mae"] * df["n"], e_n=df["sesgo"] * df["n"])
    g = aux.groupby(claves).agg(
        jornadas=("dia_op", "size"), n=("n", "sum"), ae_n=("ae_n", "sum"), e_n=("e_n", "sum")
    )
    g["mae"] = g["ae_n"] / g["n"]
    g["sesgo"] = g["e_n"] / g["n"]
    return g.drop(columns=["ae_n", "e_n"]).reset_index()


def tablas(diario):
    mae_global = ponderado(diario, ["semanas_entrenamiento"]).set_index("semanas_entrenamiento")
    mae_ruta = ponderado(diario, ["semanas_entrenamiento", "route"]).pivot(
        index="semanas_entrenamiento", columns="route", values="mae"
    )
    sesgo_tipo = ponderado(diario, ["route", "semanas_entrenamiento", "tipo_dia"])
    return mae_global, mae_ruta, sesgo_tipo


def direccion(serie):
    """Cambio del sesgo entre la ventana mas corta y el registro completo."""
    return "sube" if serie[CODIGO_COMPLETO] > serie[8] else "baja"


def comparar_patron(sesgo_nuevo, sesgo_original):
    """Por ruta y tipo de dia: sesgo en cada ventana y direccion 8 -> completo,
    en el barrido nuevo y en el original."""
    filas = []
    for ruta in sorted(sesgo_nuevo["route"].unique()):
        for tipo in TIPOS_DIA:
            fila = {"route": ruta, "tipo_dia": tipo}
            for nombre, tabla in (("validacion", sesgo_nuevo), ("original", sesgo_original)):
                sub = tabla.loc[(tabla["route"] == ruta) & (tabla["tipo_dia"] == tipo)]
                if sub.empty:
                    fila[f"jornadas_{nombre}"] = 0
                    fila[f"direccion_{nombre}"] = None
                    continue
                serie = sub.set_index("semanas_entrenamiento")["sesgo"]
                fila[f"jornadas_{nombre}"] = int(sub["jornadas"].iloc[0])
                fila[f"ventana_min_abs_{nombre}"] = int(serie.abs().idxmin())
                for v in serie.index:
                    fila[f"sesgo_{nombre}_{ETIQUETA_VENTANA[v]}"] = serie[v]
                fila[f"direccion_{nombre}"] = direccion(serie)
            fila["misma_direccion"] = (
                fila["direccion_validacion"] == fila["direccion_original"]
                if fila["direccion_validacion"] and fila["direccion_original"]
                else None
            )
            filas.append(fila)
    return pd.DataFrame(filas)


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(f) + " |" for f in filas]
    return "\n".join(lineas)


def escribir_resumen(config, params, diario, mae_global, mae_ruta, sesgo_tipo, comparacion, verif):
    mejor = int(mae_global["mae"].idxmin())
    jornadas_ruta = diario.loc[diario["semanas_entrenamiento"] == 26].groupby("route").size()
    p = [
        "# Barrido de ventana de XGBoost en validación con hiperparámetros seleccionados",
        "",
        "Generado por `analisis/31_barrido_ventana_validacion_hparam.py`.",
        "",
        f"- Periodo: validación de la búsqueda, {config.inicio_validacion} a "
        f"{config.fin_validacion} (extremos inclusivos).",
        f"- Jornadas por ventana: {int(jornadas_ruta.sum())} "
        f"({', '.join(f'ruta {r}: {n}' for r, n in jornadas_ruta.items())}).",
        "- Hiperparámetros: trial seleccionado de `seleccion__xgboost.json` sobre los fijos "
        "`XGBOOST_FIJOS`: "
        + ", ".join(f"`{k}={v:.4g}`" for k, v in params.items())
        + ".",
        "- Protocolo: reentrenamiento diario, "
        f"{config.evaluacion.metodo('XGBoost').semanas_parada_temprana} semanas finales de la "
        "ventana para parada temprana, mismo ajuste que la búsqueda (`ajustar_predecir_xgboost`).",
        "- Métricas ponderadas por observaciones (sobre todas las franjas). Sesgo = predicción − real.",
        "",
        f"**Verificación:** con 26 semanas el barrido reproduce la evaluación del trial seleccionado "
        f"en la búsqueda: MAE {verif['mae_barrido']:.6f} frente a {verif['mae_busqueda']:.6f}; "
        f"sesgo {verif['sesgo_barrido']:.6f} frente a {verif['sesgo_busqueda']:.6f} "
        f"({'coincide' if verif['coincide'] else 'NO coincide'}).",
        "",
        "## MAE ponderado por ventana",
        "",
        tabla_md(
            ["Ventana", "Global", "Ruta 1", "Ruta 3", "Sesgo global"],
            [
                [
                    ETIQUETA_VENTANA[v] + (" (mínimo)" if v == mejor else ""),
                    coma(mae_global.loc[v, "mae"]),
                    coma(mae_ruta.loc[v, 1]),
                    coma(mae_ruta.loc[v, 3]),
                    coma(mae_global.loc[v, "sesgo"]),
                ]
                for v in mae_global.index
            ],
        ),
        "",
        f"Menor MAE global: ventana de {ETIQUETA_VENTANA[mejor]}"
        + (" semanas" if mejor != CODIGO_COMPLETO else "")
        + f" ({coma(mae_global.loc[mejor, 'mae'])}).",
    ]
    for ruta in (1, 3):
        sub = sesgo_tipo.loc[sesgo_tipo["route"] == ruta]
        piv = sub.pivot(index="semanas_entrenamiento", columns="tipo_dia", values="sesgo")
        tipos = [t for t in TIPOS_DIA if t in piv.columns]
        jor = sub.drop_duplicates("tipo_dia").set_index("tipo_dia")["jornadas"]
        p += [
            "",
            f"## Sesgo ponderado por ventana y tipo de día, ruta {ruta}",
            "",
            tabla_md(
                ["Ventana"] + [f"{t} ({int(jor[t])})" for t in tipos],
                [[ETIQUETA_VENTANA[v]] + [coma(piv.loc[v, t]) for t in tipos] for v in piv.index],
            ),
        ]
    p += [
        "",
        "## Patrón de sesgo frente al barrido original",
        "",
        "Barrido original: `barrido_ventana_diario.csv` (2026-04-02 a 2026-06-10, `PARAMS_XGB`, "
        "137 jornadas, dataset anterior a la corrección PASAJEROS_REALES). Dirección = signo del "
        "cambio del sesgo entre 8 semanas y registro completo. «Ventana |sesgo| mín.» = ventana "
        "con el sesgo más cercano a cero.",
        "",
        tabla_md(
            [
                "Ruta",
                "Tipo de día",
                "Jornadas (val. / orig.)",
                "Sesgo 8 → completo (val.)",
                "Sesgo 8 → completo (orig.)",
                "Dirección (val. / orig.)",
                "Ventana |sesgo| mín. (val. / orig.)",
            ],
            [
                [
                    str(f["route"]),
                    f["tipo_dia"],
                    f"{f['jornadas_validacion']} / {f['jornadas_original']}",
                    (
                        f"{coma(f['sesgo_validacion_8'])} → {coma(f['sesgo_validacion_Completo'])}"
                        if f["jornadas_validacion"]
                        else "—"
                    ),
                    f"{coma(f['sesgo_original_8'])} → {coma(f['sesgo_original_Completo'])}",
                    f"{f['direccion_validacion'] or '—'} / {f['direccion_original']}",
                    (
                        f"{ETIQUETA_VENTANA[f['ventana_min_abs_validacion']]} / "
                        if f["jornadas_validacion"]
                        else "— / "
                    )
                    + ETIQUETA_VENTANA[f["ventana_min_abs_original"]],
                ]
                for f in comparacion.to_dict("records")
            ],
        ),
    ]
    RUTA_RESUMEN.write_text("\n".join(p) + "\n", encoding="utf-8")


def main():
    config = cargar_configuracion_busqueda()
    seleccion, params = cargar_hiperparametros()
    assert seleccion["periodo_validacion"] == {
        "inicio": str(config.inicio_validacion),
        "fin": str(config.fin_validacion),
    }, "El periodo de la seleccion no coincide con la configuracion de busqueda."
    print(f"Periodo: {config.inicio_validacion} a {config.fin_validacion}")
    print(f"Objetivo: {config.evaluacion.objetivo}; dataset: {config.evaluacion.ruta_dataset}")
    print(f"Hiperparametros: {params}")

    df = pd.read_parquet(config.evaluacion.ruta_dataset)
    diario, obs, omitidas, minutos = barrer(df, config, params)
    diario.to_csv(RUTA_DIARIO, index=False)
    obs.to_csv(RUTA_OBS, index=False)

    mae_global, mae_ruta, sesgo_tipo = tablas(diario)
    original = pd.read_csv(RUTA_ORIGINAL)
    _, mae_ruta_orig, sesgo_tipo_orig = tablas(original)
    mae_global_orig = ponderado(original, ["semanas_entrenamiento"]).set_index(
        "semanas_entrenamiento"
    )
    comparacion = comparar_patron(sesgo_tipo, sesgo_tipo_orig)

    trial = seleccion["trial_seleccionado"]
    verif = {
        "mae_barrido": float(mae_global.loc[26, "mae"]),
        "mae_busqueda": float(trial["mae_global"]),
        "sesgo_barrido": float(mae_global.loc[26, "sesgo"]),
        "sesgo_busqueda": float(trial["sesgo_global"]),
        "jornadas_barrido": int(mae_global.loc[26, "jornadas"]),
        "jornadas_busqueda": int(trial["n_jornadas"]),
    }
    verif["coincide"] = bool(
        abs(verif["mae_barrido"] - verif["mae_busqueda"]) < TOLERANCIA_VERIFICACION
        and abs(verif["sesgo_barrido"] - verif["sesgo_busqueda"]) < TOLERANCIA_VERIFICACION
        and verif["jornadas_barrido"] == verif["jornadas_busqueda"]
    )

    escribir_resumen(config, params, diario, mae_global, mae_ruta, sesgo_tipo, comparacion, verif)

    mejor = int(mae_global["mae"].idxmin())
    manifiesto = {
        "script": "analisis/31_barrido_ventana_validacion_hparam.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sufijo": SUFIJO,
        "periodo_validacion": {
            "inicio": str(config.inicio_validacion),
            "fin": str(config.fin_validacion),
            "extremos_inclusivos": True,
        },
        "dataset": str(config.evaluacion.ruta_dataset.relative_to(PROJECT_ROOT)),
        "objetivo": config.evaluacion.objetivo,
        "rutas": list(config.evaluacion.rutas),
        "min_franjas": config.evaluacion.min_franjas,
        "paso_muestreo": config.evaluacion.paso_muestreo,
        "semanas_parada_temprana": config.evaluacion.metodo("XGBoost").semanas_parada_temprana,
        "ventanas": [v if v is not None else CODIGO_COMPLETO for v in VENTANAS],
        "codigo_registro_completo": CODIGO_COMPLETO,
        "hiperparametros": {"fuente": str(RUTA_SELECCION.relative_to(PROJECT_ROOT)),
                            "trial": int(trial["trial"]), "fijos": XGBOOST_FIJOS,
                            "seleccionados": params},
        "jornadas_por_ventana_y_ruta": {
            f"{ETIQUETA_VENTANA[v]}__ruta_{r}": int(n)
            for (v, r), n in diario.groupby(["semanas_entrenamiento", "route"]).size().items()
        },
        "combinaciones_omitidas": [
            {"route": r, "dia_op": dia, "ventana": v, "motivo": m} for r, dia, v, m in omitidas
        ],
        "verificacion_26_semanas_vs_busqueda": verif,
        "mae_global_por_ventana": {
            ETIQUETA_VENTANA[v]: float(mae_global.loc[v, "mae"]) for v in mae_global.index
        },
        "mae_por_ventana_y_ruta": {
            f"{ETIQUETA_VENTANA[v]}__ruta_{r}": float(mae_ruta.loc[v, r])
            for v in mae_ruta.index
            for r in mae_ruta.columns
        },
        "ventana_menor_mae_global": ETIQUETA_VENTANA[mejor],
        "barrido_original_mae_global_por_ventana": {
            ETIQUETA_VENTANA[v]: float(mae_global_orig.loc[v, "mae"]) for v in mae_global_orig.index
        },
        "comparacion_patron_sesgo": comparacion.replace({np.nan: None}).to_dict("records"),
        "minutos_ejecucion": round(minutos, 1),
        "salidas": [
            str(p.relative_to(PROJECT_ROOT))
            for p in (RUTA_DIARIO, RUTA_OBS, RUTA_RESUMEN, RUTA_MANIFIESTO)
        ],
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    print("\n" + RUTA_RESUMEN.read_text(encoding="utf-8"))
    print("MAE global del barrido original por ventana (referencia):")
    print(mae_global_orig["mae"].round(2).to_string())
    print(f"\nOmitidas: {len(omitidas)}. Verificacion 26s: {verif}")


if __name__ == "__main__":
    main()
