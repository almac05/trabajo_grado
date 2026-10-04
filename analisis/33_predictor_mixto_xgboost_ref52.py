"""Predictor mixto: XGBoost en las franjas de regimen ordinario y la referencia
de 52 semanas en las de regimen raro, frente a XGBoost solo, las referencias de
26 y 52 semanas y la referencia combinada (26 s ordinario / 52 s raro).

Periodos y fuentes (solo lectura; no modifica scripts, freezes ni configuracion):
  - Validacion, 2025-12-25 a 2026-04-01:
    `observaciones__referencia_combinada_regimen__validacion.csv` (script 25).
    Su XGBoost (26 semanas, hiperparametros seleccionados) es identico franja a
    franja al de `observaciones__barrido_ventana__validacion_hparam.csv`
    (script 31); se verifica aqui.
  - Evaluacion, 2026-04-02 a 2026-06-10, 134 jornadas comunes del freeze
    `freeze_20260922_203820`:
    `observaciones__referencia_combinada_regimen__freeze_20260922_203820.csv`
    (script 25), cuyo XGBoost y referencias simples provienen de los artefactos
    del freeze.

El regimen de cada franja es el de esos archivos (raro = FESTIVO o
FESTIVO_PUENTE). Por construccion, dentro de cada regimen el mixto coincide con
uno de sus componentes: con XGBoost en el ordinario y con la referencia de 52 s
(igual a la combinada) en el raro. Las diferencias aparecen en los agregados
global y por ruta.

Metricas sobre observaciones: MAE, MedAE (mediana del error absoluto), sesgo
(prediccion - real) y WAPE = 100 * sum|error| / sum(real).

Salidas en analisis/salidas/ (sufijo __predictor_mixto_xgboost_ref52):
  - metricas__predictor_mixto_xgboost_ref52.csv
  - resumen__predictor_mixto_xgboost_ref52.md
  - manifiesto__predictor_mixto_xgboost_ref52.json

Uso:
    python analisis/33_predictor_mixto_xgboost_ref52.py
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd

from proyecto_grado.etl.config import PROJECT_ROOT

SUFIJO = "predictor_mixto_xgboost_ref52"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
FREEZE = "freeze_20260922_203820"

ENTRADAS = {
    "validacion": SALIDA / "observaciones__referencia_combinada_regimen__validacion.csv",
    "evaluacion": SALIDA / f"observaciones__referencia_combinada_regimen__{FREEZE}.csv",
}
METRICAS_25 = {
    "validacion": SALIDA / "metricas__referencia_combinada_regimen__validacion.csv",
    "evaluacion": SALIDA / f"metricas__referencia_combinada_regimen__{FREEZE}.csv",
}
RUTA_XGB_31 = SALIDA / "observaciones__barrido_ventana__validacion_hparam.csv"

RUTA_METRICAS = SALIDA / f"metricas__{SUFIJO}.csv"
RUTA_RESUMEN = SALIDA / f"resumen__{SUFIJO}.md"
RUTA_MANIFIESTO = SALIDA / f"manifiesto__{SUFIJO}.json"

MIXTO = "Mixto (XGBoost ordinario / 52s raro)"
METODOS = {  # nombre -> columna
    MIXTO: "pred_mixto",
    "XGBoost": "pred_xgboost",
    "Referencia (26s)": "pred_ref26",
    "Referencia (52s)": "pred_ref52",
    "Combinada (26s/52s)": "pred_combinada",
}
NOMBRES_25 = {
    "XGBoost": "XGBoost",
    "Referencia (26s)": "Referencia (26s)",
    "Referencia (52s)": "Referencia (52s)",
    "Combinada (26s/52s)": "Combinada (26s/52s por regimen)",
}
N_JORNADAS_EVALUACION = 134
TOLERANCIA = 1e-4  # los CSV del script 25 estan redondeados a 4 decimales


def cargar(periodo):
    d = pd.read_csv(ENTRADAS[periodo])
    assert set(d["regimen"]) <= {"ordinario", "raro"}, set(d["regimen"])
    d["pred_mixto"] = np.where(d["regimen"] == "raro", d["pred_ref52"], d["pred_xgboost"])
    d["jornada"] = d["route"].astype(str) + "_" + d["dia_op"].astype(str)
    return d


def metricas(real, pred):
    error = pred - real
    absoluto = np.abs(error)
    return {
        "n": len(real),
        "demanda_media": real.mean(),
        "mae": absoluto.mean(),
        "medae": np.median(absoluto),
        "sesgo": error.mean(),
        "wape": 100 * absoluto.sum() / real.sum(),
    }


def tabla(datos, periodo):
    grupos = [("global", "ambas", "todos", datos)]
    grupos += [("por_ruta", str(r), "todos", g) for r, g in datos.groupby("route")]
    grupos += [("por_regimen", "ambas", reg, g) for reg, g in datos.groupby("regimen")]
    grupos += [
        ("por_ruta_y_regimen", str(r), reg, g) for (r, reg), g in datos.groupby(["route", "regimen"])
    ]
    filas = []
    for desagregacion, ruta, regimen, g in grupos:
        for nombre, col in METODOS.items():
            filas.append({
                "periodo": periodo,
                "desagregacion": desagregacion,
                "route": ruta,
                "regimen": regimen,
                "metodo": nombre,
                "n_jornadas": g["jornada"].nunique(),
                **metricas(g["real"].to_numpy(), g[col].to_numpy()),
            })
    return pd.DataFrame(filas)


def verificar(datos, met):
    """Reproduce el MAE persistido por el script 25 y el XGBoost del script 31."""
    filas = []
    for periodo, t in met.items():
        ref = pd.read_csv(METRICAS_25[periodo])
        for nombre, nombre_25 in NOMBRES_25.items():
            for desagregacion, clave, valor in (
                ("global", None, None),
                *[("por_ruta", "route", r) for r in (1, 3)],
                *[("por_regimen", "regimen", reg) for reg in ("ordinario", "raro")],
            ):
                r = ref[(ref["metodo"] == nombre_25) & (ref["desagregacion"] == desagregacion)]
                propio = t[(t["metodo"] == nombre) & (t["desagregacion"] == desagregacion)]
                if clave == "route":
                    r = r[r["route"] == valor]
                    propio = propio[propio["route"] == str(valor)]
                elif clave == "regimen":
                    r = r[r["regimen"] == valor]
                    propio = propio[propio["regimen"] == valor]
                filas.append({
                    "periodo": periodo, "metodo": nombre, "desagregacion": desagregacion,
                    "grupo": valor, "mae": float(propio["mae"].iloc[0]),
                    "mae_script25": float(r["mae"].iloc[0]),
                    "n": int(propio["n"].iloc[0]), "n_script25": int(r["n"].iloc[0]),
                })
    v = pd.DataFrame(filas)
    v["coincide"] = ((v["mae"] - v["mae_script25"]).abs() < TOLERANCIA) & (v["n"] == v["n_script25"])

    xgb = pd.read_csv(RUTA_XGB_31)
    xgb = xgb[xgb["semanas_entrenamiento"] == 26].copy()
    xgb["hora"] = pd.to_datetime(xgb["timestamp"]).dt.strftime("%H:%M")
    unido = datos["validacion"].merge(
        xgb[["route", "dia_op", "hora", "pred"]], on=["route", "dia_op", "hora"], how="inner"
    )
    assert len(unido) == len(datos["validacion"]) == len(xgb)
    dif_xgb = float((unido["pred"] - unido["pred_xgboost"]).abs().max())
    return v, dif_xgb


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(f) + " |" for f in filas]
    return "\n".join(lineas)


def bloque_md(t, desagregacion, titulo):
    sub = t[t["desagregacion"] == desagregacion]
    filas = []
    for (ruta, regimen), g in sub.groupby(["route", "regimen"], sort=False):
        mejor = g["mae"].min()
        for f in g.to_dict("records"):
            filas.append([
                ruta, regimen, f["metodo"] + (" ◆" if f["mae"] - mejor < 1e-9 else ""),
                f"{f['n']} / {f['n_jornadas']}", coma(f["mae"]), coma(f["medae"]),
                coma(f["sesgo"]), coma(f["wape"], 1),
            ])
    return [f"### {titulo}", "", tabla_md(
        ["Ruta", "Régimen", "Método", "n / jornadas", "MAE", "MedAE", "Sesgo", "WAPE %"], filas
    ), ""]


def escribir_resumen(met, verif, dif_xgb):
    p = [
        "# Predictor mixto: XGBoost en régimen ordinario, referencia de 52 semanas en régimen raro",
        "",
        "Generado por `analisis/33_predictor_mixto_xgboost_ref52.py`.",
        "",
        "- Validación: 2025-12-25 a 2026-04-01. Evaluación: 2026-04-02 a 2026-06-10, 134 jornadas "
        f"comunes del freeze `{FREEZE}`. Fuente: observaciones del script 25 en ambos periodos.",
        "- Régimen raro = FESTIVO o FESTIVO_PUENTE. Dentro de cada régimen el mixto coincide con "
        "XGBoost (ordinario) o con la referencia de 52 s, que es igual a la combinada (raro).",
        "- Métricas sobre observaciones. Sesgo = predicción − real. "
        "WAPE = 100·Σ|error| / Σreal. ◆ = menor MAE del grupo (incluye empates).",
        f"- Verificación: MAE y n de XGBoost y de las tres referencias reproducen los del script 25 "
        f"({'sí' if verif['coincide'].all() else 'NO'}); XGBoost de validación frente al del "
        f"script 31: diferencia máxima {dif_xgb:.1e}.",
        "",
    ]
    for periodo, t in met.items():
        p += [f"## {periodo.capitalize()}", ""]
        p += bloque_md(t, "global", "Global")
        p += bloque_md(t, "por_ruta", "Por ruta")
        p += bloque_md(t, "por_regimen", "Por régimen")
        p += bloque_md(t, "por_ruta_y_regimen", "Por ruta y régimen")
    RUTA_RESUMEN.write_text("\n".join(p), encoding="utf-8")


def main():
    datos = {periodo: cargar(periodo) for periodo in ENTRADAS}
    assert datos["evaluacion"]["jornada"].nunique() == N_JORNADAS_EVALUACION
    met = {periodo: tabla(d, periodo) for periodo, d in datos.items()}
    verif, dif_xgb = verificar(datos, met)
    assert verif["coincide"].all() and dif_xgb < 1e-6, verif[~verif["coincide"]]

    todas = pd.concat(met.values(), ignore_index=True)
    todas.to_csv(RUTA_METRICAS, index=False)
    escribir_resumen(met, verif, dif_xgb)

    globales = todas[todas["desagregacion"] == "global"]
    manifiesto = {
        "script": "analisis/33_predictor_mixto_xgboost_ref52.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sufijo": SUFIJO,
        "definicion_mixto": "pred_xgboost si regimen == 'ordinario'; pred_ref52 si regimen == 'raro'",
        "entradas": [str(r.relative_to(PROJECT_ROOT)) for r in (*ENTRADAS.values(),
                                                               *METRICAS_25.values(), RUTA_XGB_31)],
        "periodos": {
            p: {"franjas": len(d), "jornadas": int(d["jornada"].nunique()),
                "franjas_raras": int((d["regimen"] == "raro").sum())}
            for p, d in datos.items()
        },
        "verificacion_script25_coincide": bool(verif["coincide"].all()),
        "max_dif_xgboost_script31_vs_script25": dif_xgb,
        "metricas_globales": {
            p: {f["metodo"]: {k: f[k] for k in ("mae", "medae", "sesgo", "wape")}
                for f in g.to_dict("records")}
            for p, g in globales.groupby("periodo")
        },
        "salidas": [str(r.relative_to(PROJECT_ROOT)) for r in (RUTA_METRICAS, RUTA_RESUMEN,
                                                              RUTA_MANIFIESTO)],
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    pd.set_option("display.width", 200)
    cols = ["periodo", "desagregacion", "route", "regimen", "metodo", "n", "n_jornadas",
            "mae", "medae", "sesgo", "wape"]
    print(todas[todas["desagregacion"] != "por_ruta_y_regimen"][cols].round(2).to_string(index=False))
    print(f"\nResumen: {RUTA_RESUMEN}")


if __name__ == "__main__":
    main()
