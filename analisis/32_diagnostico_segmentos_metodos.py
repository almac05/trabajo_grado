"""Diagnostico por segmentos: que metodo tiene menor MAE y menor |sesgo| en cada
bloque horario, franja, tipo de dia, regimen y nivel de demanda esperada, y si
ese ganador se mantiene entre el periodo de validacion y el de evaluacion.

Es solo un diagnostico: no construye ninguna regla de seleccion.

Periodos y fuentes (solo lectura; no modifica scripts, freezes ni configuracion):
  - Evaluacion, 2026-04-02 a 2026-06-10, sobre las 134 jornadas comunes del
    freeze `freeze_20260922_203820`
    (`jornadas_comunes__freeze_20260922_203820.csv`). Ocho metodos del freeze:
    los seis de `predicciones__<metodo>__freeze_20260922_203820.csv`, la
    referencia de 26 semanas (`pred_media` del artefacto de XGBoost) y la de 52
    semanas (`pred_media` del artefacto de GRU), como en el agregador canonico.
    Se anade la referencia combinada de `25_referencia_combinada_regimen.py`
    (`observaciones__referencia_combinada_regimen__freeze_20260922_203820.csv`).
  - Validacion, 2025-12-25 a 2026-04-01. Solo hay predicciones por franja
    persistidas para: XGBoost con 26 semanas
    (`observaciones__barrido_ventana__validacion_hparam.csv`, script 31) y las
    referencias de 26 s, 52 s y combinada
    (`observaciones__referencia_combinada_regimen__validacion.csv`, script 25).
    SARIMA, Prophet, LSTM, GRU y CNN-LSTM solo tienen metricas agregadas por
    configuracion en `busqueda_hiperparametros/configuraciones__*.csv`.

Cortes (por ruta y ambas rutas combinadas): bloque horario, franja de 30 min
(secundario), tipo de dia, regimen, nivel de demanda esperada (cuartiles de la
prediccion de la referencia de 26 semanas, umbrales por ruta calculados en
validacion y aplicados a evaluacion), nivel de demanda observada (descriptivo,
no utilizable para decidir en la operacion) y bloque horario x regimen.

Metricas por celda: MAE, sesgo (prediccion - real), WAPE, n y jornadas. Celda
pequena: n < 100 o jornadas < 5.

Ganadores: por celda, el metodo de menor MAE y el de menor |sesgo|. En
evaluacion se calculan sobre los metodos comunes a ambos periodos (base de la
comparacion de persistencia) y sobre los nueve metodos (informativo).

Salidas en analisis/salidas/ (sufijo __diagnostico_segmentos):
  - metricas__diagnostico_segmentos.csv
  - ganadores__diagnostico_segmentos.csv
  - persistencia__diagnostico_segmentos.csv
  - umbrales__diagnostico_segmentos.csv
  - resumen__diagnostico_segmentos.md
  - manifiesto__diagnostico_segmentos.json

Uso:
    python analisis/32_diagnostico_segmentos_metodos.py
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion

SUFIJO = "diagnostico_segmentos"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
FREEZE = "freeze_20260922_203820"

RUTA_COMUNES = SALIDA / f"jornadas_comunes__{FREEZE}.csv"
RUTA_COMBINADA_EVAL = SALIDA / f"observaciones__referencia_combinada_regimen__{FREEZE}.csv"
RUTA_COMBINADA_VAL = SALIDA / "observaciones__referencia_combinada_regimen__validacion.csv"
RUTA_XGB_VAL = SALIDA / "observaciones__barrido_ventana__validacion_hparam.csv"
RUTA_METRICAS_FREEZE = SALIDA / f"metricas__comparacion_modelos__{FREEZE}__global.csv"
RUTA_METRICAS_25_EVAL = SALIDA / f"metricas__referencia_combinada_regimen__{FREEZE}.csv"
RUTA_METRICAS_25_VAL = SALIDA / "metricas__referencia_combinada_regimen__validacion.csv"

RUTA_METRICAS = SALIDA / f"metricas__{SUFIJO}.csv"
RUTA_GANADORES = SALIDA / f"ganadores__{SUFIJO}.csv"
RUTA_PERSISTENCIA = SALIDA / f"persistencia__{SUFIJO}.csv"
RUTA_UMBRALES = SALIDA / f"umbrales__{SUFIJO}.csv"
RUTA_RESUMEN = SALIDA / f"resumen__{SUFIJO}.md"
RUTA_MANIFIESTO = SALIDA / f"manifiesto__{SUFIJO}.json"

# Metodos del freeze: nombre -> (identificador del artefacto, columna).
METODOS_FREEZE = {
    "SARIMA": ("sarima", "pred_sarima"),
    "Prophet": ("prophet", "pred_prophet"),
    "XGBoost": ("xgboost", "pred_xgboost"),
    "LSTM": ("lstm", "pred_lstm"),
    "GRU": ("gru", "pred_gru"),
    "CNN-LSTM": ("cnn_lstm", "pred_cnn_lstm"),
    "Referencia (26s)": ("xgboost", "pred_media"),
    "Referencia (52s)": ("gru", "pred_media"),
}
COMBINADA = "Combinada (26s/52s)"
METODOS_EVAL = [*METODOS_FREEZE, COMBINADA]
METODOS_VAL = ["XGBoost", "Referencia (26s)", "Referencia (52s)", COMBINADA]
METODOS_NO_DISPONIBLES_VAL = ["SARIMA", "Prophet", "LSTM", "GRU", "CNN-LSTM"]
METODO_NIVEL = "Referencia (26s)"

N_JORNADAS_COMUNES = 134
MIN_N = 100
MIN_JORNADAS = 5
TOLERANCIA = 1e-6
EMPATE = 1e-9

BLOQUES = [  # (etiqueta, hora inicial inclusiva, hora final exclusiva)
    ("madrugada (04:00-04:59)", 4, 5),
    ("pico manana (05:00-06:59)", 5, 7),
    ("manana (07:00-09:59)", 7, 10),
    ("valle (10:00-13:59)", 10, 14),
    ("pico tarde (14:00-15:59)", 14, 16),
    ("cierre (16:00 en adelante)", 16, 24),
]
TIPOS_DIA = ["LABORAL", "SABADO", "DOMINGO", "FESTIVO", "FESTIVO_PUENTE"]
REGIMENES = ["ordinario", "raro"]
NIVELES = ["N1 (bajo)", "N2 (medio-bajo)", "N3 (medio-alto)", "N4 (alto)"]
CORTES = {
    "bloque": "Bloque horario",
    "franja": "Franja de 30 minutos",
    "tipo_dia": "Tipo de dia",
    "regimen": "Regimen",
    "nivel_esperado": "Nivel de demanda esperada (cuartiles de la referencia 26s)",
    "nivel_observado": "Nivel de demanda observada (descriptivo)",
    "bloque_x_regimen": "Bloque horario x regimen",
}
RUTAS = ["1", "3", "ambas"]


# --------------------------------------------------------------------------- datos


def _fecha(serie):
    return pd.to_datetime(serie).dt.date


def cargar_evaluacion(tipos_raros):
    comunes = pd.read_csv(RUTA_COMUNES)
    comunes["dia_op"] = _fecha(comunes["dia_op"])
    assert len(comunes) == N_JORNADAS_COMUNES, len(comunes)
    claves = ["route", "dia_op", "hora"]

    base = None
    filas_por_metodo = {}
    for nombre, (ident, columna) in METODOS_FREEZE.items():
        p = pd.read_csv(SALIDA / f"predicciones__{ident}__{FREEZE}.csv")
        p["dia_op"] = _fecha(p["dia_op"])
        p = p.merge(comunes, on=["route", "dia_op"], how="inner")
        p = p[p["real"].notna() & p[columna].notna()]
        filas_por_metodo[nombre] = len(p)
        p = p[[*claves, "tipo_dia", "real", columna]].rename(columns={columna: nombre})
        if base is None:
            base = p
        else:
            base = base.merge(p, on=[*claves, "tipo_dia", "real"], how="inner")

    comb = pd.read_csv(RUTA_COMBINADA_EVAL)
    comb["dia_op"] = _fecha(comb["dia_op"])
    filas_por_metodo[COMBINADA] = len(comb)
    base = base.merge(
        comb[[*claves, "real", "pred_combinada"]].rename(columns={"pred_combinada": COMBINADA}),
        on=[*claves, "real"],
        how="inner",
    )
    # Todas las fuentes cubren exactamente las mismas franjas: la union no pierde filas.
    assert set(filas_por_metodo.values()) == {len(base)}, (filas_por_metodo, len(base))
    base["regimen"] = np.where(base["tipo_dia"].isin(tipos_raros), "raro", "ordinario")
    return base, filas_por_metodo


def cargar_validacion():
    comb = pd.read_csv(RUTA_COMBINADA_VAL)
    comb["dia_op"] = _fecha(comb["dia_op"])
    xgb = pd.read_csv(RUTA_XGB_VAL)
    xgb = xgb[xgb["semanas_entrenamiento"] == 26].copy()
    xgb["dia_op"] = _fecha(xgb["dia_op"])
    xgb["hora"] = pd.to_datetime(xgb["timestamp"]).dt.strftime("%H:%M")

    base = comb.rename(
        columns={
            "pred_combinada": COMBINADA,
            "pred_ref26": "Referencia (26s)",
            "pred_ref52": "Referencia (52s)",
            "pred_xgboost": "xgb_script25",
        }
    ).merge(
        xgb[["route", "dia_op", "hora", "real", "pred"]].rename(columns={"pred": "XGBoost"}),
        on=["route", "dia_op", "hora", "real"],
        how="inner",
    )
    assert len(base) == len(comb) == len(xgb), (len(base), len(comb), len(xgb))
    # XGBoost 26s del script 31 y el recalculado por el script 25 deben coincidir.
    dif_xgb = float((base["XGBoost"] - base["xgb_script25"]).abs().max())
    return base.drop(columns="xgb_script25"), dif_xgb


def bloque_de(hora):
    h = int(hora[:2])
    for etiqueta, ini, fin in BLOQUES:
        if ini <= h < fin:
            return etiqueta
    return "fuera de bloque"


def umbrales_cuartiles(datos, columna):
    return {
        ruta: g[columna].quantile([0.25, 0.5, 0.75]).to_numpy()
        for ruta, g in datos.groupby("route")
    }


def asignar_nivel(datos, columna, umbrales):
    nivel = pd.Series(index=datos.index, dtype=object)
    for ruta, q in umbrales.items():
        m = datos["route"] == ruta
        nivel[m] = pd.cut(
            datos.loc[m, columna], bins=[-np.inf, *q, np.inf], labels=NIVELES, right=True
        ).astype(str)
    return nivel


def anadir_segmentos(datos, umb_esperado, umb_observado):
    d = datos.copy()
    d["bloque"] = d["hora"].map(bloque_de)
    d["franja"] = d["hora"]
    d["nivel_esperado"] = asignar_nivel(d, METODO_NIVEL, umb_esperado)
    d["nivel_observado"] = asignar_nivel(d, "real", umb_observado)
    d["bloque_x_regimen"] = d["bloque"] + " x " + d["regimen"]
    d["jornada"] = d["route"].astype(str) + "_" + d["dia_op"].astype(str)
    return d


# ------------------------------------------------------------------------ metricas


def metricas_segmentos(datos, metodos, periodo):
    largo = datos.melt(
        id_vars=["route", "jornada", "real", *CORTES],
        value_vars=metodos,
        var_name="metodo",
        value_name="pred",
    )
    largo["error"] = largo["pred"] - largo["real"]
    largo["abs_error"] = largo["error"].abs()

    tablas = []
    for corte in CORTES:
        for ruta in RUTAS:
            sub = largo if ruta == "ambas" else largo[largo["route"].astype(str) == ruta]
            g = sub.groupby([corte, "metodo"]).agg(
                n=("real", "size"),
                n_jornadas=("jornada", "nunique"),
                suma_real=("real", "sum"),
                suma_abs=("abs_error", "sum"),
                suma_error=("error", "sum"),
            )
            g = g.reset_index().rename(columns={corte: "segmento"})
            g.insert(0, "route", ruta)
            g.insert(0, "corte", corte)
            tablas.append(g)
    t = pd.concat(tablas, ignore_index=True)
    t["demanda_media"] = t["suma_real"] / t["n"]
    t["mae"] = t["suma_abs"] / t["n"]
    t["sesgo"] = t["suma_error"] / t["n"]
    t["wape"] = 100 * t["suma_abs"] / t["suma_real"]
    t["celda_pequena"] = (t["n"] < MIN_N) | (t["n_jornadas"] < MIN_JORNADAS)
    t.insert(0, "periodo", periodo)
    return t.drop(columns=["suma_real", "suma_abs", "suma_error"])


def ganadores(metricas, metodos, conjunto):
    claves = ["periodo", "corte", "route", "segmento"]
    m = metricas[metricas["metodo"].isin(metodos)].copy()
    m["abs_sesgo"] = m["sesgo"].abs()
    filas = []
    for clave, g in m.groupby(claves, sort=False):
        # Todas las fuentes comparten franjas, de modo que n y jornadas son unicos por celda.
        assert g["n"].nunique() == 1 and g["n_jornadas"].nunique() == 1, clave
        mae_min = g.loc[g["mae"].idxmin()]
        ses_min = g.loc[g["abs_sesgo"].idxmin()]
        # La combinada coincide con la referencia de 26 s en regimen ordinario y con la de
        # 52 s en el raro: los empates exactos se reportan como tales, no por orden de columna.
        empate_mae = g.loc[(g["mae"] - mae_min["mae"]).abs() < EMPATE, "metodo"].tolist()
        empate_ses = g.loc[(g["abs_sesgo"] - ses_min["abs_sesgo"]).abs() < EMPATE, "metodo"].tolist()
        orden = g[~g["metodo"].isin(empate_mae)].sort_values("mae")
        filas.append(
            {
                **dict(zip(claves, clave, strict=True)),
                "conjunto": conjunto,
                "n_metodos": len(g),
                "n": int(g["n"].iloc[0]),
                "n_jornadas": int(g["n_jornadas"].iloc[0]),
                "celda_pequena": bool(g["celda_pequena"].iloc[0]),
                "ganador_mae": " = ".join(empate_mae),
                "mae_ganador": mae_min["mae"],
                "segundo_mae": orden["metodo"].iloc[0] if len(orden) else None,
                "margen_mae_segundo": orden["mae"].iloc[0] - mae_min["mae"]
                if len(orden)
                else np.nan,
                "ganador_sesgo": " = ".join(empate_ses),
                "sesgo_ganador": ses_min["sesgo"],
            }
        )
    return pd.DataFrame(filas)


def persistencia(gan_val, gan_eval_comunes, gan_eval_todos):
    claves = ["corte", "route", "segmento"]
    cols = ["n", "n_jornadas", "celda_pequena", "ganador_mae", "mae_ganador",
            "margen_mae_segundo", "ganador_sesgo", "sesgo_ganador"]
    v = gan_val[claves + cols].add_suffix("_val").rename(columns={f"{c}_val": c for c in claves})
    e = gan_eval_comunes[claves + cols].add_suffix("_eval").rename(
        columns={f"{c}_eval": c for c in claves}
    )
    t = gan_eval_todos[claves + ["ganador_mae", "mae_ganador", "ganador_sesgo", "sesgo_ganador"]]
    t = t.rename(columns={
        "ganador_mae": "ganador_mae_eval_todos",
        "mae_ganador": "mae_ganador_eval_todos",
        "ganador_sesgo": "ganador_sesgo_eval_todos",
        "sesgo_ganador": "sesgo_ganador_eval_todos",
    })
    p = v.merge(e, on=claves, how="inner").merge(t, on=claves, how="left")
    p["mantiene_ganador_mae"] = p["ganador_mae_val"] == p["ganador_mae_eval"]
    p["mantiene_ganador_sesgo"] = p["ganador_sesgo_val"] == p["ganador_sesgo_eval"]
    p["ganador_mae_val_es_ganador_eval_todos"] = p["ganador_mae_val"] == p["ganador_mae_eval_todos"]
    p["alguna_celda_pequena"] = p["celda_pequena_val"] | p["celda_pequena_eval"]
    solo_val = gan_val.merge(gan_eval_comunes[claves], on=claves, how="left", indicator=True)
    solo_eval = gan_eval_comunes.merge(gan_val[claves], on=claves, how="left", indicator=True)
    ausentes = {
        nombre: [
            " / ".join(map(str, fila))
            for fila in tabla.loc[tabla["_merge"] == "left_only", claves].itertuples(index=False)
        ]
        for nombre, tabla in (("solo_validacion", solo_val), ("solo_evaluacion", solo_eval))
    }
    return p, ausentes


# ---------------------------------------------------------------------- verificacion


def verificar(met_eval, met_val, dif_xgb):
    """Las metricas globales recalculadas deben reproducir las ya persistidas."""
    glob_eval = met_eval[(met_eval["corte"] == "regimen") & (met_eval["route"] == "ambas")]
    glob_eval = glob_eval.groupby("metodo").apply(
        lambda g: pd.Series({"n": g["n"].sum(), "mae": (g["mae"] * g["n"]).sum() / g["n"].sum()}),
        include_groups=False,
    )
    freeze = pd.read_csv(RUTA_METRICAS_FREEZE).set_index("metodo")
    r25e = pd.read_csv(RUTA_METRICAS_25_EVAL)
    r25e = r25e[r25e["desagregacion"] == "global"].set_index("metodo")
    r25v = pd.read_csv(RUTA_METRICAS_25_VAL)
    r25v = r25v[r25v["desagregacion"] == "global"].set_index("metodo")
    glob_val = met_val[(met_val["corte"] == "regimen") & (met_val["route"] == "ambas")]
    glob_val = glob_val.groupby("metodo").apply(
        lambda g: (g["mae"] * g["n"]).sum() / g["n"].sum(), include_groups=False
    )

    filas = []
    for metodo in METODOS_FREEZE:
        filas.append({"periodo": "evaluacion", "metodo": metodo, "fuente": RUTA_METRICAS_FREEZE.name,
                      "mae_recalculado": glob_eval.loc[metodo, "mae"],
                      "mae_persistido": freeze.loc[metodo, "mae"],
                      "n_recalculado": int(glob_eval.loc[metodo, "n"]),
                      "n_persistido": int(freeze.loc[metodo, "n"])})
    filas.append({"periodo": "evaluacion", "metodo": COMBINADA, "fuente": RUTA_METRICAS_25_EVAL.name,
                  "mae_recalculado": glob_eval.loc[COMBINADA, "mae"],
                  "mae_persistido": r25e.loc["Combinada (26s/52s por regimen)", "mae"],
                  "n_recalculado": int(glob_eval.loc[COMBINADA, "n"]),
                  "n_persistido": int(r25e.loc["Combinada (26s/52s por regimen)", "n"])})
    nombres_25 = {"XGBoost": "XGBoost", "Referencia (26s)": "Referencia (26s)",
                  "Referencia (52s)": "Referencia (52s)",
                  COMBINADA: "Combinada (26s/52s por regimen)"}
    for metodo in METODOS_VAL:
        filas.append({"periodo": "validacion", "metodo": metodo, "fuente": RUTA_METRICAS_25_VAL.name,
                      "mae_recalculado": glob_val.loc[metodo],
                      "mae_persistido": r25v.loc[nombres_25[metodo], "mae"],
                      "n_recalculado": None, "n_persistido": None})
    v = pd.DataFrame(filas)
    # Los CSV persistidos estan redondeados a 4 decimales.
    v["coincide"] = (v["mae_recalculado"] - v["mae_persistido"]).abs() < 1e-4
    v.loc[v["n_persistido"].notna(), "coincide"] &= (
        v["n_recalculado"] == v["n_persistido"]
    )
    return v, dif_xgb < TOLERANCIA


# ---------------------------------------------------------------------------- resumen


def coma(valor, decimales=2):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    return f"{valor:.{decimales}f}".replace(".", ",")


def tabla_md(encabezado, filas):
    def celda(c):
        return str(c).replace("|", "\\|")

    lineas = ["| " + " | ".join(map(celda, encabezado)) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(map(celda, f)) + " |" for f in filas]
    return "\n".join(lineas)


def orden_segmentos(corte, segmentos):
    if corte == "bloque":
        base = [b[0] for b in BLOQUES]
    elif corte == "tipo_dia":
        base = TIPOS_DIA
    elif corte == "regimen":
        base = REGIMENES
    elif corte in ("nivel_esperado", "nivel_observado"):
        base = NIVELES
    elif corte == "bloque_x_regimen":
        base = [f"{b[0]} x {r}" for b in BLOQUES for r in REGIMENES]
    else:
        base = sorted(segmentos)
    return [s for s in base if s in set(segmentos)] + sorted(set(segmentos) - set(base))


def marca(pequena):
    return " †" if pequena else ""


def si_no(valor):
    return "sí" if valor else "no"


def tabla_ganadores(corte, gan_val, gan_ec, gan_et, rutas=RUTAS):
    claves = ["corte", "route", "segmento"]
    v = gan_val[gan_val["corte"] == corte].set_index(claves[1:])
    ec = gan_ec[gan_ec["corte"] == corte].set_index(claves[1:])
    et = gan_et[gan_et["corte"] == corte].set_index(claves[1:])
    filas = []
    for ruta in rutas:
        segs = orden_segmentos(corte, ec.loc[ruta].index.tolist() if ruta in ec.index else [])
        segs = orden_segmentos(
            corte, set(segs) | set(v.loc[ruta].index if ruta in v.index.get_level_values(0) else [])
        )
        for seg in segs:
            fv = v.loc[(ruta, seg)] if (ruta, seg) in v.index else None
            fe = ec.loc[(ruta, seg)] if (ruta, seg) in ec.index else None
            ft = et.loc[(ruta, seg)] if (ruta, seg) in et.index else None

            def nj(f):
                return f"{int(f['n'])} / {int(f['n_jornadas'])}{marca(f['celda_pequena'])}" if f is not None else "—"

            def gm(f):
                return f"{f['ganador_mae']} ({coma(f['mae_ganador'])})" if f is not None else "—"

            def gs(f):
                return f"{f['ganador_sesgo']} ({coma(f['sesgo_ganador'])})" if f is not None else "—"

            ambos = fv is not None and fe is not None
            filas.append([
                ruta, seg, nj(fv), gm(fv), nj(fe), gm(fe), gm(ft),
                si_no(fv["ganador_mae"] == fe["ganador_mae"]) if ambos else "—",
                gs(fv), gs(fe), gs(ft),
                si_no(fv["ganador_sesgo"] == fe["ganador_sesgo"]) if ambos else "—",
            ])
    return tabla_md(
        ["Ruta", "Segmento", "Val. n / jorn.", "Val. menor MAE", "Eval. n / jorn.",
         "Eval. menor MAE (comunes)", "Eval. menor MAE (9 métodos)", "¿Mantiene MAE?",
         "Val. menor |sesgo|", "Eval. menor |sesgo| (comunes)", "Eval. menor |sesgo| (9 métodos)",
         "¿Mantiene sesgo?"],
        filas,
    )


def tabla_metodos_bloque(metricas, metodos, ruta="ambas"):
    m = metricas[(metricas["corte"] == "bloque") & (metricas["route"] == ruta)]
    segs = orden_segmentos("bloque", m["segmento"].unique())
    filas = []
    for metodo in metodos:
        fila = [metodo]
        for s in segs:
            c = m[(m["segmento"] == s) & (m["metodo"] == metodo)].iloc[0]
            fila.append(f"{coma(c['mae'])} / {coma(c['sesgo'])} / {coma(c['wape'], 1)}")
        filas.append(fila)
    n_fila = ["n / jornadas"] + [
        f"{int(m[m['segmento'] == s]['n'].iloc[0])} / {int(m[m['segmento'] == s]['n_jornadas'].iloc[0])}"
        for s in segs
    ]
    return tabla_md(["Método"] + segs, [n_fila] + filas)


def escribir_resumen(ctx):
    p = [
        "# Diagnóstico por segmentos: método ganador en validación y en evaluación",
        "",
        "Generado por `analisis/32_diagnostico_segmentos_metodos.py`. Diagnóstico descriptivo: "
        "no define ninguna regla de selección.",
        "",
        "- Evaluación: 2026-04-02 a 2026-06-10, 134 jornadas comunes del freeze "
        f"`{FREEZE}` ({ctx['n_eval']} franjas). Nueve métodos: los ocho del freeze y la "
        "referencia combinada del script 25.",
        "- Validación: 2025-12-25 a 2026-04-01, "
        f"{ctx['jornadas_val']} jornadas ({ctx['n_val']} franjas).",
        "- Métricas ponderadas por observaciones. Sesgo = predicción − real. "
        "WAPE = 100·Σ|error| / Σreal.",
        f"- † = celda pequeña (n < {MIN_N} o menos de {MIN_JORNADAS} jornadas).",
        "- «Comunes» = métodos con predicciones en ambos periodos; la persistencia del ganador "
        "se evalúa sobre ese conjunto. La columna «9 métodos» es informativa.",
        "- «A = B» indica empate exacto. La combinada es idéntica a la referencia de 26 s en "
        "régimen ordinario y a la de 52 s en régimen raro, por lo que empata con una de ellas "
        "en toda celda de un solo régimen.",
        "",
        "## Disponibilidad de predicciones por franja en validación",
        "",
        tabla_md(
            ["Método", "Validación", "Fuente"],
            [[m, "sí", f] for m, f in ctx["fuentes_val"].items()]
            + [[m, "no", "solo métricas agregadas por configuración "
                f"(`busqueda_hiperparametros/configuraciones__{METODOS_FREEZE[m][0]}.csv`)"]
               for m in METODOS_NO_DISPONIBLES_VAL],
        ),
        "",
        "## Verificación",
        "",
        "MAE global recalculado frente al persistido por el freeze y por el script 25; "
        "XGBoost 26 s del script 31 frente al recalculado en el script 25 "
        f"(diferencia máxima por franja: {ctx['dif_xgb']:.2e}).",
        "",
        tabla_md(
            ["Periodo", "Método", "MAE recalculado", "MAE persistido", "Coincide"],
            [[f["periodo"], f["metodo"], coma(f["mae_recalculado"], 4),
              coma(f["mae_persistido"], 4), si_no(f["coincide"])]
             for f in ctx["verificacion"].to_dict("records")],
        ),
        "",
        "## Umbrales de nivel de demanda (calculados en validación, por ruta)",
        "",
        "Nivel esperado: cuartiles de la predicción de la referencia de 26 semanas, conocida antes "
        "de la franja. Nivel observado: cuartiles de la demanda real; **solo descriptivo, no "
        "utilizable para decidir en la operación**, porque la demanda real no se conoce de "
        "antemano. Intervalos cerrados por la derecha: N1 ≤ Q25 < N2 ≤ Q50 < N3 ≤ Q75 < N4.",
        "",
        tabla_md(
            ["Base", "Ruta", "Q25", "Q50", "Q75"],
            [[f["base"], f["route"], coma(f["q25"]), coma(f["q50"]), coma(f["q75"])]
             for f in ctx["umbrales"].to_dict("records")],
        ),
        "",
        "## Métricas por bloque horario, ambas rutas (MAE / sesgo / WAPE %)",
        "",
        "### Validación",
        "",
        tabla_metodos_bloque(ctx["met_val"], METODOS_VAL),
        "",
        "### Evaluación",
        "",
        tabla_metodos_bloque(ctx["met_eval"], METODOS_EVAL),
    ]
    principales = ["bloque", "tipo_dia", "regimen", "nivel_esperado", "bloque_x_regimen"]
    for corte in principales:
        p += ["", f"## Ganadores: {CORTES[corte].lower()}", "",
              tabla_ganadores(corte, ctx["gan_val"], ctx["gan_ec"], ctx["gan_et"])]
    p += [
        "", "## Ganadores: nivel de demanda observada (descriptivo, no operativo)", "",
        "Este corte usa la demanda real de la franja, que no se conoce al momento de decidir. "
        "Se incluye solo para contrastarlo con el nivel esperado.", "",
        tabla_ganadores("nivel_observado", ctx["gan_val"], ctx["gan_ec"], ctx["gan_et"]),
        "", "## Ganadores: franja de 30 minutos, ambas rutas (tabla secundaria)", "",
        "El detalle por ruta está en `ganadores__diagnostico_segmentos.csv`.", "",
        tabla_ganadores("franja", ctx["gan_val"], ctx["gan_ec"], ctx["gan_et"], rutas=["ambas"]),
    ]

    pers = ctx["persistencia"]
    p += ["", "## Resumen de persistencia por corte", "",
          tabla_md(
              ["Corte", "Segmentos en ambos periodos", "Mantiene MAE", "Mantiene MAE (sin †)",
               "Mantiene |sesgo|", "Mantiene |sesgo| (sin †)"],
              [[CORTES[c],
                str(len(g)),
                str(int(g["mantiene_ganador_mae"].sum())),
                f"{int(g.loc[~g['alguna_celda_pequena'], 'mantiene_ganador_mae'].sum())} de "
                f"{int((~g['alguna_celda_pequena']).sum())}",
                str(int(g["mantiene_ganador_sesgo"].sum())),
                f"{int(g.loc[~g['alguna_celda_pequena'], 'mantiene_ganador_sesgo'].sum())} de "
                f"{int((~g['alguna_celda_pequena']).sum())}"]
               for c, g in pers.groupby("corte", sort=False)],
          )]
    for criterio, col, col_v, col_e in (
        ("menor MAE", "mantiene_ganador_mae", "mae_ganador_val", "mae_ganador_eval"),
        ("menor |sesgo|", "mantiene_ganador_sesgo", "sesgo_ganador_val", "sesgo_ganador_eval"),
    ):
        gcol = "ganador_mae_val" if col.endswith("mae") else "ganador_sesgo_val"
        sub = pers[pers[col]]
        filas = []
        for corte in CORTES:
            s = sub[sub["corte"] == corte]
            for ruta in RUTAS:
                sr = s[s["route"] == ruta]
                for seg in orden_segmentos(corte, sr["segmento"].tolist()):
                    f = sr[sr["segmento"] == seg].iloc[0]
                    filas.append([CORTES[corte], ruta, seg + marca(f["alguna_celda_pequena"]),
                                  f[gcol], coma(f[col_v]), coma(f[col_e]),
                                  f"{int(f['n_val'])} / {int(f['n_eval'])}"])
        p += ["", f"## Segmentos donde el ganador por {criterio} se mantiene entre periodos", "",
              f"{len(filas)} segmentos (sobre los métodos comunes). Valor del ganador en cada "
              "periodo; n de validación / evaluación.", "",
              tabla_md(["Corte", "Ruta", "Segmento", "Ganador", "Valor val.", "Valor eval.",
                        "n val. / eval."], filas)]
    if ctx["ausentes"]["solo_validacion"] or ctx["ausentes"]["solo_evaluacion"]:
        p += ["", "## Segmentos presentes en un solo periodo", "",
              "- Solo validación: " + (", ".join(ctx["ausentes"]["solo_validacion"]) or "ninguno"),
              "- Solo evaluación: " + (", ".join(ctx["ausentes"]["solo_evaluacion"]) or "ninguno")]
    RUTA_RESUMEN.write_text("\n".join(p) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------- main


def main():
    config = cargar_configuracion_evaluacion()
    tipos_raros = tuple(config.tipos_baja_frecuencia)

    eval_base, filas_eval = cargar_evaluacion(tipos_raros)
    val_base, dif_xgb = cargar_validacion()
    print(f"Evaluacion: {len(eval_base)} franjas; validacion: {len(val_base)} franjas")

    umb_esp = umbrales_cuartiles(val_base, METODO_NIVEL)
    umb_obs = umbrales_cuartiles(val_base, "real")
    umbrales = pd.DataFrame(
        [{"base": base, "route": r, "q25": q[0], "q50": q[1], "q75": q[2]}
         for base, umb in (("prediccion referencia 26s (esperado)", umb_esp),
                           ("demanda observada (descriptivo)", umb_obs))
         for r, q in umb.items()]
    )

    val = anadir_segmentos(val_base, umb_esp, umb_obs)
    ev = anadir_segmentos(eval_base, umb_esp, umb_obs)
    assert (val["bloque"] != "fuera de bloque").all() and (ev["bloque"] != "fuera de bloque").all()

    met_val = metricas_segmentos(val, METODOS_VAL, "validacion")
    met_eval = metricas_segmentos(ev, METODOS_EVAL, "evaluacion")
    metricas = pd.concat([met_val, met_eval], ignore_index=True)

    comunes = [m for m in METODOS_EVAL if m in METODOS_VAL]
    gan_val = ganadores(met_val, METODOS_VAL, "comunes")
    gan_ec = ganadores(met_eval, comunes, "comunes")
    gan_et = ganadores(met_eval, METODOS_EVAL, "todos")
    gan = pd.concat([gan_val, gan_ec, gan_et], ignore_index=True)
    pers, ausentes = persistencia(gan_val, gan_ec, gan_et)

    verificacion, xgb_ok = verificar(met_eval, met_val, dif_xgb)
    print(verificacion.to_string(index=False))
    assert verificacion["coincide"].all() and xgb_ok, "La verificacion no se cumple."

    metricas.to_csv(RUTA_METRICAS, index=False)
    gan.to_csv(RUTA_GANADORES, index=False)
    pers.to_csv(RUTA_PERSISTENCIA, index=False)
    umbrales.to_csv(RUTA_UMBRALES, index=False)

    fuentes_val = {
        "XGBoost": f"`{RUTA_XGB_VAL.name}` (26 semanas, script 31)",
        "Referencia (26s)": f"`{RUTA_COMBINADA_VAL.name}` (script 25)",
        "Referencia (52s)": f"`{RUTA_COMBINADA_VAL.name}` (script 25)",
        COMBINADA: f"`{RUTA_COMBINADA_VAL.name}` (script 25)",
    }
    ctx = {
        "n_eval": len(ev), "n_val": len(val), "jornadas_val": val["jornada"].nunique(),
        "fuentes_val": fuentes_val, "dif_xgb": dif_xgb, "verificacion": verificacion,
        "umbrales": umbrales, "met_val": met_val, "met_eval": met_eval,
        "gan_val": gan_val, "gan_ec": gan_ec, "gan_et": gan_et,
        "persistencia": pers, "ausentes": ausentes,
    }
    escribir_resumen(ctx)

    resumen_pers = {
        c: {
            "segmentos_en_ambos": int(len(g)),
            "mantiene_mae": int(g["mantiene_ganador_mae"].sum()),
            "mantiene_sesgo": int(g["mantiene_ganador_sesgo"].sum()),
            "celdas_con_alguna_pequena": int(g["alguna_celda_pequena"].sum()),
        }
        for c, g in pers.groupby("corte", sort=False)
    }
    manifiesto = {
        "script": "analisis/32_diagnostico_segmentos_metodos.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sufijo": SUFIJO,
        "freeze_evaluacion": FREEZE,
        "periodo_evaluacion": {"inicio": "2026-04-02", "fin": "2026-06-10",
                               "jornadas": int(ev["jornada"].nunique()), "franjas": len(ev)},
        "periodo_validacion": {"inicio": "2025-12-25", "fin": "2026-04-01",
                               "jornadas": int(val["jornada"].nunique()), "franjas": len(val)},
        "metodos_evaluacion": METODOS_EVAL,
        "metodos_validacion_disponibles": METODOS_VAL,
        "metodos_validacion_no_disponibles": METODOS_NO_DISPONIBLES_VAL,
        "metodos_comunes": comunes,
        "filas_por_metodo_evaluacion": filas_eval,
        "entradas": [str(r.relative_to(PROJECT_ROOT)) for r in (
            RUTA_COMUNES, RUTA_COMBINADA_EVAL, RUTA_COMBINADA_VAL, RUTA_XGB_VAL,
            RUTA_METRICAS_FREEZE, RUTA_METRICAS_25_EVAL, RUTA_METRICAS_25_VAL,
            *(SALIDA / f"predicciones__{i}__{FREEZE}.csv"
              for i in sorted({v[0] for v in METODOS_FREEZE.values()})),
        )],
        "bloques": {b[0]: [b[1], b[2]] for b in BLOQUES},
        "tipos_baja_frecuencia": list(tipos_raros),
        "celda_pequena": {"n_menor_que": MIN_N, "jornadas_menor_que": MIN_JORNADAS},
        "umbrales": umbrales.to_dict("records"),
        "verificacion": verificacion.replace({np.nan: None}).to_dict("records"),
        "max_dif_xgboost_script31_vs_script25": dif_xgb,
        "persistencia_por_corte": resumen_pers,
        "segmentos_un_solo_periodo": ausentes,
        "salidas": [str(r.relative_to(PROJECT_ROOT)) for r in (
            RUTA_METRICAS, RUTA_GANADORES, RUTA_PERSISTENCIA, RUTA_UMBRALES,
            RUTA_RESUMEN, RUTA_MANIFIESTO)],
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    print("\nUmbrales:\n" + umbrales.round(2).to_string(index=False))
    print("\nPersistencia por corte:")
    for c, r in resumen_pers.items():
        print(f"  {c:18s} {r}")
    print(f"\nResumen: {RUTA_RESUMEN}")


if __name__ == "__main__":
    main()
