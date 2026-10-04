"""Importancia de variables de XGBoost en el freeze, ablacion de los rezagos y
redundancia entre predictoras.

Tres partes, sobre las 134 jornadas comunes del freeze `freeze_20260922_203820`
(66 de la ruta 1 y 68 de la ruta 3; un ajuste diario por jornada y ruta, 134
ajustes en total). No modifica scripts, freezes ni configuracion: solo lee el
dataset de modelado, la seleccion de hiperparametros y los artefactos del freeze.

1. Importancia. Se repite cada ajuste diario de XGBoost del freeze con el mismo
   protocolo de `hparam_search/reevaluacion.py` (26 semanas, las 2 ultimas para
   parada temprana, configuracion seleccionada, `ajustar_predecir_xgboost`
   equivalente) y se verifica que reproduce las predicciones persistidas. De cada
   ajuste se toma la ganancia total (`total_gain`) por variable, se expresa como
   porcentaje del total del ajuste y se promedia sobre los ajustes de cada ruta.
   Se agrupa por concepto: hora, dia de la semana, festivo y fin de semana,
   rezagos de demanda y rezagos de productividad.

2. Ablacion. Se reentrena XGBoost con la misma configuracion y el mismo protocolo
   excluyendo los seis rezagos (demanda y productividad a 1, 2 y 7 dias). Los
   hiperparametros no se reajustan. Se reporta MAE, MedAE y sesgo globales, por
   ruta y por regimen, junto a XGBoost completo (predicciones del freeze) y la
   referencia de 26 semanas (`pred_media` del artefacto de XGBoost del freeze).

3. Redundancia. Matriz de correlaciones de Spearman entre las 14 predictoras
   informativas (se omite `dentro_horario_operativo`, constante en el dataset),
   por ruta, sobre las franjas que alimentan los ajustes del periodo: desde 26
   semanas antes del inicio de la evaluacion hasta su ultima jornada. Describe la
   redundancia entre variables que codifican la misma informacion, no su
   relacion con la demanda.

Salidas en analisis/salidas/ (sufijo __importancia_ablacion_xgboost):
  - importancia_por_ajuste__importancia_ablacion_xgboost.csv
  - importancia__importancia_ablacion_xgboost.csv (por variable y por concepto)
  - observaciones__importancia_ablacion_xgboost.csv
  - metricas__importancia_ablacion_xgboost.csv
  - spearman__importancia_ablacion_xgboost.csv
  - figura_spearman__importancia_ablacion_xgboost.png / .pdf
  - resumen__importancia_ablacion_xgboost.md
  - manifiesto__importancia_ablacion_xgboost.json

Uso:
    python analisis/34_importancia_ablacion_xgboost.py
"""

import json
import time
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from matplotlib.colors import LinearSegmentedColormap

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.reevaluacion import cargar_configuraciones_seleccionadas
from proyecto_grado.modeling.hparam_search.runner import _preparar_ruta
from proyecto_grado.modeling.hparam_search.spaces import XGBOOST_FIJOS

SUFIJO = "importancia_ablacion_xgboost"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
FREEZE = "freeze_20260922_203820"
RUTA_COMUNES = SALIDA / f"jornadas_comunes__{FREEZE}.csv"
RUTA_XGB_FREEZE = SALIDA / f"predicciones__xgboost__{FREEZE}.csv"
RUTA_METRICAS_FREEZE = SALIDA / f"metricas__comparacion_modelos__{FREEZE}__global.csv"
DIRECTORIO_SELECCION = SALIDA / "busqueda_hiperparametros"

RUTA_IMP_AJUSTE = SALIDA / f"importancia_por_ajuste__{SUFIJO}.csv"
RUTA_IMP = SALIDA / f"importancia__{SUFIJO}.csv"
RUTA_OBS = SALIDA / f"observaciones__{SUFIJO}.csv"
RUTA_METRICAS = SALIDA / f"metricas__{SUFIJO}.csv"
RUTA_SPEARMAN = SALIDA / f"spearman__{SUFIJO}.csv"
RUTA_FIGURA = SALIDA / f"figura_spearman__{SUFIJO}"
RUTA_RESUMEN = SALIDA / f"resumen__{SUFIJO}.md"
RUTA_MANIFIESTO = SALIDA / f"manifiesto__{SUFIJO}.json"

N_JORNADAS_COMUNES = 134
INICIO_EVALUACION = pd.Timestamp("2026-04-02")
TOLERANCIA_REPRODUCCION = 1e-3  # XGBoost predice en float32

REZAGOS = [
    "pasajeros_total_lag_48",
    "pasajeros_total_lag_96",
    "pasajeros_total_lag_336",
    "pasajeros_por_despacho_lag_48",
    "pasajeros_por_despacho_lag_96",
    "pasajeros_por_despacho_lag_336",
]
CONCEPTOS = {
    "Hora": ["hora_del_dia", "hora_sin", "hora_cos"],
    "Dia de la semana": ["dia_semana", "dia_semana_sin", "dia_semana_cos"],
    "Festivo y fin de semana": ["es_festivo", "es_fin_semana"],
    "Rezagos de demanda": REZAGOS[:3],
    "Rezagos de productividad": REZAGOS[3:],
    "Horario operativo (constante)": ["dentro_horario_operativo"],
}
CONSTANTE = "dentro_horario_operativo"
INFORMATIVAS = [v for c, vs in CONCEPTOS.items() for v in vs if v != CONSTANTE]
ETIQUETAS = {
    "hora_del_dia": "hora del día",
    "hora_sin": "hora (seno)",
    "hora_cos": "hora (coseno)",
    "dia_semana": "día de la semana",
    "dia_semana_sin": "día semana (seno)",
    "dia_semana_cos": "día semana (coseno)",
    "es_festivo": "festivo",
    "es_fin_semana": "fin de semana",
    "pasajeros_total_lag_48": "demanda −1 día",
    "pasajeros_total_lag_96": "demanda −2 días",
    "pasajeros_total_lag_336": "demanda −7 días",
    "pasajeros_por_despacho_lag_48": "productividad −1 día",
    "pasajeros_por_despacho_lag_96": "productividad −2 días",
    "pasajeros_por_despacho_lag_336": "productividad −7 días",
}

COMPLETO = "XGBoost completo"
SIN_REZAGOS = "XGBoost sin rezagos"
REF26 = "Referencia (26s)"
METODOS = {COMPLETO: "pred_xgboost", SIN_REZAGOS: "pred_sin_rezagos", REF26: "pred_media"}

# Estilo, como en analisis/29_figuras_reunion.py. Escala divergente azul <-> rojo
# con punto medio gris neutro.
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
DIVERGENTE = LinearSegmentedColormap.from_list(
    "azul_gris_rojo", ["#1c5cab", "#86b6ef", "#f0efec", "#ef9796", "#b3302f"]
)
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "text.color": TINTA,
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "savefig.facecolor": "white",
})


# ---------------------------------------------------------------- ajustes diarios


def ajustar(fit_df, stop_df, test_df, features, target, params):
    """Igual que hparam_search.fits.ajustar_predecir_xgboost, conservando el modelo."""
    modelo = xgb.XGBRegressor(**{**XGBOOST_FIJOS, **params})
    modelo.fit(
        fit_df[features], fit_df[target],
        eval_set=[(stop_df[features], stop_df[target])], verbose=False,
    )
    return modelo, modelo.predict(test_df[features])


def ejecutar_ajustes(config, df, params):
    target = config.objetivo
    semanas = config.metodo("XGBoost").semanas_entrenamiento
    semanas_parada = config.metodo("XGBoost").semanas_parada_temprana
    tipos_raros = tuple(config.tipos_baja_frecuencia)

    comunes = pd.read_csv(RUTA_COMUNES)
    comunes["dia_op"] = pd.to_datetime(comunes["dia_op"]).dt.date
    assert len(comunes) == N_JORNADAS_COMUNES

    importancias, observaciones, features_por_ruta = [], [], {}
    t0 = time.perf_counter()
    for ruta, g in comunes.groupby("route"):
        d = _preparar_ruta(df, ruta, target)
        completas = seleccionar_features(d)
        reducidas = [f for f in completas if f not in REZAGOS]
        assert set(completas) - set(reducidas) == set(REZAGOS), completas
        assert set(completas) == set(INFORMATIVAS) | {CONSTANTE}, completas
        features_por_ruta[int(ruta)] = {"completas": completas, "sin_rezagos": reducidas}

        for i, dia in enumerate(sorted(g["dia_op"]), start=1):
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            corte = inicio_dia - pd.Timedelta(weeks=semanas_parada)
            train = d[(d["timestamp"] >= inicio_dia - pd.Timedelta(weeks=semanas))
                      & (d["timestamp"] < inicio_dia)]
            fit_df, stop_df = train[train["timestamp"] < corte], train[train["timestamp"] >= corte]
            test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]

            modelo, pred = ajustar(fit_df, stop_df, test, completas, target, params)
            modelo_red, pred_red = ajustar(fit_df, stop_df, test, reducidas, target, params)

            ganancia = pd.Series(modelo.get_booster().get_score(importance_type="total_gain"))
            ganancia = ganancia.reindex(completas).fillna(0.0)
            importancias.append(pd.DataFrame({
                "route": ruta, "dia_op": dia, "tipo_dia": test["tipo_dia"].iloc[0],
                "arboles": modelo.best_iteration + 1,
                "variable": completas, "ganancia_total": ganancia.to_numpy(),
                "porcentaje": 100 * ganancia.to_numpy() / ganancia.sum(),
            }))
            tipo = test["tipo_dia"].iloc[0]
            observaciones.append(pd.DataFrame({
                "route": ruta, "dia_op": dia, "tipo_dia": tipo,
                "regimen": "raro" if tipo in tipos_raros else "ordinario",
                "hora": test["hora"].to_numpy(), "real": test[target].to_numpy(),
                "pred_xgboost_reajuste": pred, "pred_sin_rezagos": pred_red,
                "arboles_sin_rezagos": modelo_red.best_iteration + 1,
            }))
            print(f"  ruta {ruta} [{i:2d}/{len(g)}] {dia} {tipo:14s} "
                  f"arboles {modelo.best_iteration + 1:4d} / {modelo_red.best_iteration + 1:4d}",
                  flush=True)
    minutos = (time.perf_counter() - t0) / 60
    return (pd.concat(importancias, ignore_index=True),
            pd.concat(observaciones, ignore_index=True), features_por_ruta, minutos)


def unir_freeze(obs):
    freeze = pd.read_csv(RUTA_XGB_FREEZE)
    freeze["dia_op"] = pd.to_datetime(freeze["dia_op"]).dt.date
    unido = obs.merge(
        freeze[["route", "dia_op", "hora", "real", "pred_xgboost", "pred_media"]],
        on=["route", "dia_op", "hora"], how="inner", suffixes=("", "_freeze"),
    )
    assert len(unido) == len(obs), (len(unido), len(obs))
    assert np.allclose(unido["real"], unido["real_freeze"])
    dif = float((unido["pred_xgboost_reajuste"] - unido["pred_xgboost"]).abs().max())
    assert dif < TOLERANCIA_REPRODUCCION, f"El reajuste no reproduce el freeze: {dif}"
    return unido.drop(columns="real_freeze"), dif


# ------------------------------------------------------------------- importancia


def resumir_importancia(imp):
    concepto_de = {v: c for c, vs in CONCEPTOS.items() for v in vs}
    imp = imp.assign(concepto=imp["variable"].map(concepto_de))
    por_variable = (
        imp.groupby(["route", "concepto", "variable"])["porcentaje"]
        .agg(media="mean", desviacion="std", minimo="min", maximo="max")
        .reset_index().assign(nivel="variable")
    )
    por_ajuste_concepto = imp.groupby(["route", "dia_op", "concepto"])["porcentaje"].sum().reset_index()
    por_concepto = (
        por_ajuste_concepto.groupby(["route", "concepto"])["porcentaje"]
        .agg(media="mean", desviacion="std", minimo="min", maximo="max")
        .reset_index().assign(nivel="concepto", variable=None)
    )
    n = imp.groupby("route")["dia_op"].nunique().rename("n_ajustes").reset_index()
    return pd.concat([por_concepto, por_variable], ignore_index=True).merge(n, on="route")


# ---------------------------------------------------------------------- metricas


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
    filas = []
    for desagregacion, ruta, regimen, g in grupos:
        for nombre, col in METODOS.items():
            filas.append({"desagregacion": desagregacion, "route": ruta, "regimen": regimen,
                          "metodo": nombre, "n_jornadas": g["jornada"].nunique(),
                          **metricas(g["real"].to_numpy(), g[col].to_numpy())})
    return pd.DataFrame(filas)


def verificar_freeze(tabla):
    freeze = pd.read_csv(RUTA_METRICAS_FREEZE).set_index("metodo")
    glob = tabla[tabla["desagregacion"] == "global"].set_index("metodo")
    filas = []
    for nombre, nombre_freeze in ((COMPLETO, "XGBoost"), (REF26, "Referencia (26s)")):
        filas.append({"metodo": nombre, "mae": glob.loc[nombre, "mae"],
                      "mae_freeze": freeze.loc[nombre_freeze, "mae"],
                      "n": int(glob.loc[nombre, "n"]), "n_freeze": int(freeze.loc[nombre_freeze, "n"])})
    v = pd.DataFrame(filas)
    v["coincide"] = ((v["mae"] - v["mae_freeze"]).abs() < 1e-4) & (v["n"] == v["n_freeze"])
    assert v["coincide"].all(), v
    return v


# --------------------------------------------------------------------- spearman


def correlaciones(config, df, ultima_jornada):
    inicio = INICIO_EVALUACION + pd.Timedelta(hours=4) - pd.Timedelta(
        weeks=config.metodo("XGBoost").semanas_entrenamiento)
    fin = pd.Timestamp(ultima_jornada) + pd.Timedelta(days=1, hours=4)
    matrices, filas = {}, {}
    for ruta in config.rutas:
        d = _preparar_ruta(df, ruta, config.objetivo)
        d = d[(d["timestamp"] >= inicio) & (d["timestamp"] < fin)]
        x = d[INFORMATIVAS].astype(float)
        matrices[ruta] = x.corr(method="spearman")
        filas[ruta] = len(x)
    largo = pd.concat(
        [m.rename_axis("variable_1").reset_index()
         .melt(id_vars="variable_1", var_name="variable_2", value_name="spearman")
         .assign(route=r) for r, m in matrices.items()],
        ignore_index=True,
    )
    return matrices, largo, filas, (inicio, fin)


def figura_spearman(matrices, filas, ventana):
    etiquetas = [ETIQUETAS[v] for v in INFORMATIVAS]
    limites = np.cumsum([len([v for v in vs if v != CONSTANTE])
                         for c, vs in CONCEPTOS.items()])[:-2]
    fig, ejes = plt.subplots(1, 2, figsize=(16, 8.2), constrained_layout=True)
    for ax, (ruta, m) in zip(ejes, matrices.items()):
        valores = m.loc[INFORMATIVAS, INFORMATIVAS].to_numpy()
        img = ax.imshow(valores, cmap=DIVERGENTE, vmin=-1, vmax=1)
        for i in range(len(INFORMATIVAS)):
            for j in range(len(INFORMATIVAS)):
                v = valores[i, j]
                ax.text(j, i, f"{v:.2f}".replace(".", ",").replace("-", "−"), ha="center",
                        va="center", fontsize=7, color="white" if abs(v) > 0.6 else TINTA)
        for b in limites:  # separa los conceptos
            ax.axhline(b - 0.5, color="white", lw=2.5)
            ax.axvline(b - 0.5, color="white", lw=2.5)
        ax.set_xticks(range(len(etiquetas)), etiquetas, rotation=55, ha="right")
        ax.set_yticks(range(len(etiquetas)), etiquetas)
        ax.tick_params(length=0)
        for lado in ax.spines.values():
            lado.set_visible(False)
        ax.set_title(f"Ruta {ruta} ({filas[ruta]:,} franjas)".replace(",", "."), loc="left")
    barra = fig.colorbar(img, ax=ejes, shrink=0.7, pad=0.01)
    barra.set_label("correlación de Spearman")
    barra.outline.set_visible(False)
    fig.suptitle("Redundancia entre las 14 variables predictoras informativas de XGBoost",
                 x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.01, -0.02,
             f"Franjas de {ventana[0]:%Y-%m-%d} a {ventana[1]:%Y-%m-%d} (26 semanas previas a la "
             "evaluación más el periodo de evaluación). Bloques: hora, día de la semana, festivo y "
             "fin de semana, rezagos de demanda, rezagos de productividad.\nMuestra redundancia "
             "entre predictoras, no su relación con la demanda. Spearman solo capta relaciones "
             "monótonas: la relación entre el día de la semana y su seno o coseno no lo es.",
             fontsize=9, color=TINTA_2, ha="left", va="top")
    for ext in ("png", "pdf"):
        fig.savefig(f"{RUTA_FIGURA}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------- resumen


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",").replace("-", "−")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    return "\n".join(lineas + ["| " + " | ".join(f) + " |" for f in filas])


def escribir_resumen(ctx):
    imp = ctx["importancia"]
    con = imp[imp["nivel"] == "concepto"].pivot(index="concepto", columns="route")
    var = imp[imp["nivel"] == "variable"].pivot(index="variable", columns="route")
    n_aj = imp.drop_duplicates("route").set_index("route")["n_ajustes"]
    rutas = sorted(n_aj.index)
    orden_var = var[("media", rutas[0])].sort_values(ascending=False).index
    met = ctx["metricas"]

    p = [
        "# Importancia, ablación de rezagos y redundancia de las variables de XGBoost",
        "",
        "Generado por `analisis/34_importancia_ablacion_xgboost.py`.",
        "",
        f"- Freeze `{FREEZE}`, 134 jornadas comunes, un ajuste diario por jornada y ruta: "
        + ", ".join(f"ruta {r}: {n_aj[r]} ajustes" for r in rutas) + ".",
        "- Protocolo de la reevaluación del freeze: 26 semanas de entrenamiento, las 2 últimas "
        "para parada temprana, configuración seleccionada por la búsqueda (trial 8).",
        f"- Verificación: el reajuste reproduce las predicciones del freeze (diferencia máxima "
        f"{ctx['dif_reproduccion']:.1e}); el MAE global de XGBoost completo y de la referencia "
        "de 26 s coincide con `metricas__comparacion_modelos__freeze_20260922_203820__global.csv`.",
        "",
        "## 1. Importancia por ganancia total",
        "",
        "Ganancia total de cada variable como porcentaje de la ganancia total del ajuste, "
        "promediada sobre los ajustes diarios de cada ruta (entre paréntesis, desviación estándar "
        "entre ajustes).",
        "",
        "### Por concepto",
        "",
        tabla_md(
            ["Concepto"] + [f"Ruta {r} (%)" for r in rutas],
            [[c] + [f"{coma(con.loc[c, ('media', r)], 1)} ({coma(con.loc[c, ('desviacion', r)], 1)})"
                    for r in rutas] for c in CONCEPTOS],
        ),
        "",
        "### Por variable",
        "",
        tabla_md(
            ["Variable"] + [f"Ruta {r} (%)" for r in rutas],
            [[f"`{v}`"] + [f"{coma(var.loc[v, ('media', r)], 1)} ({coma(var.loc[v, ('desviacion', r)], 1)})"
                           for r in rutas] for v in orden_var],
        ),
        "",
        "## 2. Ablación: XGBoost sin los seis rezagos",
        "",
        "Mismo protocolo y misma configuración de hiperparámetros, sin reajustarlos, con las "
        f"{len(ctx['features']['sin_rezagos'])} variables restantes (calendario, hora y "
        "codificaciones cíclicas; una de ellas, `dentro_horario_operativo`, es constante). "
        f"Árboles por ajuste (mediana): completo {ctx['arboles_completo']:.0f}, "
        f"sin rezagos {ctx['arboles_sin_rezagos']:.0f}.",
        "",
        tabla_md(
            ["Desagregación", "Ruta", "Régimen", "Método", "n / jornadas", "MAE", "MedAE", "Sesgo",
             "WAPE %"],
            [[f["desagregacion"], f["route"], f["regimen"], f["metodo"],
              f"{f['n']} / {f['n_jornadas']}", coma(f["mae"]), coma(f["medae"]), coma(f["sesgo"]),
              coma(f["wape"], 1)] for f in met.to_dict("records")],
        ),
        "",
        "## 3. Redundancia entre predictoras (Spearman)",
        "",
        f"Figura: `{RUTA_FIGURA.name}.png`. Matriz completa: `{RUTA_SPEARMAN.name}`. Franjas de "
        f"{ctx['ventana'][0]:%Y-%m-%d} a {ctx['ventana'][1]:%Y-%m-%d}. Describe la redundancia "
        "entre variables que codifican la misma información, no su relación con la demanda.",
        "",
        "Pares con |ρ| ≥ 0,7 en alguna ruta:",
        "",
        tabla_md(
            ["Variable 1", "Variable 2"] + [f"ρ ruta {r}" for r in rutas],
            [[f"`{a}`", f"`{b}`"] + [coma(ctx["matrices"][r].loc[a, b]) for r in rutas]
             for a, b in ctx["pares_altos"]],
        ),
    ]
    RUTA_RESUMEN.write_text("\n".join(p) + "\n", encoding="utf-8")


# -------------------------------------------------------------------------- main


def main():
    config = cargar_configuracion_evaluacion()
    df = pd.read_parquet(config.ruta_dataset)
    params = cargar_configuraciones_seleccionadas(DIRECTORIO_SELECCION)["XGBoost"]
    print(f"Hiperparametros XGBoost: {params}")

    imp, obs, features, minutos = ejecutar_ajustes(config, df, params)
    obs, dif = unir_freeze(obs)
    resumen_imp = resumir_importancia(imp)
    tabla = tabla_metricas(obs)
    verif = verificar_freeze(tabla)

    matrices, largo, filas_corr, ventana = correlaciones(config, df, obs["dia_op"].max())
    figura_spearman(matrices, filas_corr, ventana)
    pares = [(a, b) for i, a in enumerate(INFORMATIVAS) for b in INFORMATIVAS[i + 1:]
             if max(abs(m.loc[a, b]) for m in matrices.values()) >= 0.7]

    imp.to_csv(RUTA_IMP_AJUSTE, index=False)
    resumen_imp.to_csv(RUTA_IMP, index=False)
    obs.to_csv(RUTA_OBS, index=False)
    tabla.to_csv(RUTA_METRICAS, index=False)
    largo.to_csv(RUTA_SPEARMAN, index=False)

    arboles = imp.drop_duplicates(["route", "dia_op"])["arboles"]
    arboles_red = obs.drop_duplicates(["route", "dia_op"])["arboles_sin_rezagos"]
    escribir_resumen({
        "importancia": resumen_imp, "metricas": tabla, "dif_reproduccion": dif,
        "features": features[config.rutas[0]], "arboles_completo": arboles.median(),
        "arboles_sin_rezagos": arboles_red.median(), "matrices": matrices,
        "ventana": ventana, "pares_altos": pares,
    })

    manifiesto = {
        "script": "analisis/34_importancia_ablacion_xgboost.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sufijo": SUFIJO,
        "freeze": FREEZE,
        "dataset": str(config.ruta_dataset.relative_to(PROJECT_ROOT)),
        "hiperparametros": {"fijos": XGBOOST_FIJOS, "seleccionados": params},
        "protocolo": {"semanas_entrenamiento": config.metodo("XGBoost").semanas_entrenamiento,
                      "semanas_parada_temprana": config.metodo("XGBoost").semanas_parada_temprana},
        "ajustes_por_ruta": {str(r): int(n) for r, n in
                             imp.groupby("route")["dia_op"].nunique().items()},
        "features": {str(r): f for r, f in features.items()},
        "rezagos_excluidos_en_ablacion": REZAGOS,
        "conceptos": CONCEPTOS,
        "importancia": "total_gain por ajuste, porcentaje del total del ajuste, media por ruta",
        "max_dif_reajuste_vs_freeze": dif,
        "verificacion_freeze": verif.to_dict("records"),
        "spearman": {"variables": INFORMATIVAS, "inicio": str(ventana[0]), "fin": str(ventana[1]),
                     "franjas_por_ruta": {str(r): n for r, n in filas_corr.items()},
                     "pares_abs_rho_ge_0_7": [list(p) for p in pares]},
        "metricas_globales": {
            f["metodo"]: {k: f[k] for k in ("mae", "medae", "sesgo", "wape")}
            for f in tabla[tabla["desagregacion"] == "global"].to_dict("records")
        },
        "minutos_ejecucion": round(minutos, 1),
        "salidas": [str(r.relative_to(PROJECT_ROOT)) for r in (
            RUTA_IMP_AJUSTE, RUTA_IMP, RUTA_OBS, RUTA_METRICAS, RUTA_SPEARMAN,
            RUTA_FIGURA.with_suffix(".png"), RUTA_FIGURA.with_suffix(".pdf"),
            RUTA_RESUMEN, RUTA_MANIFIESTO)],
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"\nTiempo: {minutos:.1f} min. Resumen: {RUTA_RESUMEN}")


if __name__ == "__main__":
    main()
