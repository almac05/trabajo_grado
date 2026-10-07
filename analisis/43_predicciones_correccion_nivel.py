"""Predicciones continuas para la correccion de nivel (2025-11-27 a 2026-10-03).

Implementa la seccion 1 de docs/preregistro_correccion_nivel.md. Reutiliza sin
cambios el protocolo del freeze freeze_20260922_203820
(`proyecto_grado.modeling.hparam_search.reevaluacion.ejecutar_metodo`) para
XGBoost y Prophet, con reentrenamiento diario y ventanas de 26 semanas. La
referencia de 26 s es la columna pred_media de XGBoost; la de 52 s se calcula
con la misma formula del protocolo (media por tipo de dia y franja en la
ventana, con la media de la ventana como respaldo) sobre las franjas de XGBoost.

Controles (seccion 7): en 2026-06-11 a 2026-10-03, XGBoost y Prophet deben
coincidir con las salidas del script 41, y la referencia de 52 s con pred_media
de GRU de ese script. Si un control falla, se detiene.

Salidas nuevas en analisis/salidas/ con el sufijo del YAML:
  predicciones__<metodo>__<sufijo>.csv, resumen__<metodo>__<sufijo>.csv,
  referencia_52s__<sufijo>.csv, manifiesto__predicciones__<sufijo>.json.
Un metodo cuyas salidas ya existen no se recalcula; nunca se sobrescriben archivos.

Uso:
    python analisis/43_predicciones_correccion_nivel.py
"""

import hashlib
import json
import time
from dataclasses import replace
from datetime import date, datetime

import pandas as pd
import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion
from proyecto_grado.modeling.hparam_search.reevaluacion import (
    _COLUMNA_PRED,
    _IDENTIFICADOR,
    cargar_configuraciones_seleccionadas,
    ejecutar_metodo,
)
from proyecto_grado.modeling.hparam_search.runner import _preparar_ruta

RUTA_CONFIG = PROJECT_ROOT / "configs" / "modeling" / "correccion_nivel_20251127_20261003.yaml"
CLAVES = ["route", "dia_op", "hora"]


def sha256(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def referencia(df, pred, target, semanas) -> pd.DataFrame:
    """Media historica por tipo de dia y franja con ventana de `semanas`, como
    en ejecutar_metodo, para cada franja de `pred`."""
    filas = []
    for ruta, g in pred.groupby("route"):
        d = _preparar_ruta(df, ruta, target)
        for dia in sorted(g["dia_op"].unique()):
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
            entrenamiento = d[(d["timestamp"] >= inicio_dia - pd.Timedelta(weeks=semanas))
                              & (d["timestamp"] < inicio_dia)]
            medias = entrenamiento.groupby(["tipo_dia", "hora"])[target].mean()
            idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
            valores = pd.Series(medias.reindex(idx).to_numpy())
            filas.append(pd.DataFrame({
                "route": ruta, "dia_op": dia, "hora": test["hora"].to_numpy(),
                "pred_media_52s": valores.fillna(entrenamiento[target].mean()).to_numpy(),
                "sin_media": valores.isna().to_numpy(),
            }))
    ref = pd.concat(filas, ignore_index=True)
    n = len(pred)
    ref = pred[CLAVES].merge(ref, on=CLAVES, how="left", validate="1:1")
    assert len(ref) == n and ref["pred_media_52s"].notna().all(), "referencia de 52 s incompleta"
    return ref


def normalizar(d):
    d = d.copy()
    d["route"] = d["route"].astype(int)
    d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.strftime("%Y-%m-%d")
    d["hora"] = d["hora"].astype(str)
    return d


def comparar(nuevo, previo, columnas) -> dict:
    """Diferencias en las franjas de las jornadas de `previo`."""
    nuevo, previo = normalizar(nuevo), normalizar(previo)
    jornadas = previo[["route", "dia_op"]].drop_duplicates()
    nuevo = nuevo.merge(jornadas, on=["route", "dia_op"])
    u = nuevo.merge(previo, on=CLAVES, how="outer", suffixes=("_nuevo", "_previo"), indicator=True)
    ambos = u[u["_merge"] == "both"]
    out = {"franjas_previo": len(previo), "franjas_nuevo_en_jornadas_previo": len(nuevo),
           "solo_en_uno": int((u["_merge"] != "both").sum())}
    for c_nuevo, c_previo in columnas:
        a = ambos[f"{c_nuevo}_nuevo" if c_nuevo == c_previo else c_nuevo]
        b = ambos[f"{c_previo}_previo" if c_nuevo == c_previo else c_previo]
        out[f"max_dif_{c_nuevo}"] = float((a - b).abs().max())
    return out


def main():
    raw = yaml.safe_load(RUTA_CONFIG.read_text(encoding="utf-8"))
    assert raw["corrida"]["extremos_inclusivos"] is True
    base = cargar_configuracion_evaluacion()
    inicio, fin = (date.fromisoformat(str(raw["corrida"][k])) for k in ("inicio", "fin"))
    config = replace(base, inicio=inicio, fin=fin)
    sufijo = raw["sufijo"]
    salida = PROJECT_ROOT / raw["salidas"]["directorio"]
    ruta_dataset = PROJECT_ROOT / raw["dataset"]
    seleccion = cargar_configuraciones_seleccionadas(PROJECT_ROOT / raw["seleccion_hiperparametros"])
    manifiesto_ruta = salida / f"manifiesto__predicciones__{sufijo}.json"
    manifiesto = (json.loads(manifiesto_ruta.read_text(encoding="utf-8")) if manifiesto_ruta.exists()
                  else {"metodos": {}})

    df = pd.read_parquet(ruta_dataset)
    preds = {}
    for metodo in raw["metodos"]:
        ident = _IDENTIFICADOR[metodo]
        ruta_pred = salida / f"predicciones__{ident}__{sufijo}.csv"
        ruta_res = salida / f"resumen__{ident}__{sufijo}.csv"
        if ruta_pred.exists() and ruta_res.exists():
            print(f"{metodo}: ya existe, se omite")
            preds[metodo] = pd.read_csv(ruta_pred)
            continue
        assert not ruta_pred.exists() and not ruta_res.exists(), f"salida parcial de {metodo}"
        print(f"\n{'=' * 60}\n{metodo} {seleccion[metodo]}\n{'=' * 60}")
        t0 = time.perf_counter()
        resumen, pred = ejecutar_metodo(metodo, seleccion[metodo], config, df)
        resumen.to_csv(ruta_res, index=False)
        pred.to_csv(ruta_pred, index=False)
        preds[metodo] = pred
        manifiesto["metodos"][metodo] = {
            "parametros": seleccion[metodo], "columna": _COLUMNA_PRED[metodo],
            "semanas_entrenamiento": config.metodo(metodo).semanas_entrenamiento,
            "semanas_parada_temprana": config.metodo(metodo).semanas_parada_temprana,
            "jornadas": int(resumen[["route", "dia_op"]].drop_duplicates().shape[0]),
            "franjas": len(pred), "minutos": round((time.perf_counter() - t0) / 60, 1),
        }
        manifiesto_ruta.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"{metodo}: {manifiesto['metodos'][metodo]}")

    semanas = int(raw["semanas_referencia_larga"])
    ruta_ref = salida / f"referencia_52s__{sufijo}.csv"
    if ruta_ref.exists():
        ref = pd.read_csv(ruta_ref)
    else:
        xgb = preds["XGBoost"].copy()
        xgb["dia_op"] = pd.to_datetime(xgb["dia_op"]).dt.date
        ref = referencia(df, xgb, config.objetivo, semanas)
        ref.to_csv(ruta_ref, index=False)

    # --- Controles de reproduccion (seccion 7) ---
    ext, tol = raw["controles"]["sufijo_extension"], float(raw["controles"]["tolerancia"])
    controles = {}
    for metodo in raw["metodos"]:
        ident, col = _IDENTIFICADOR[metodo], _COLUMNA_PRED[metodo]
        previo = pd.read_csv(salida / f"predicciones__{ident}__{ext}.csv")
        columnas = [(col, col), ("real", "real")] + ([("pred_media", "pred_media")] if metodo == "XGBoost" else [])
        controles[metodo] = comparar(preds[metodo], previo, columnas)
    # GRU trunca la jornada a sus pasos y exige la jornada previa: se comparan las franjas de GRU.
    gru = normalizar(pd.read_csv(salida / f"predicciones__gru__{ext}.csv"))[[*CLAVES, "pred_media"]]
    u = gru.merge(normalizar(ref), on=CLAVES, how="left")
    controles["referencia_52s_vs_gru"] = {
        "franjas_gru": len(gru), "sin_par": int(u["pred_media_52s"].isna().sum()),
        "max_dif": float((u["pred_media_52s"] - u["pred_media"]).abs().max()),
    }
    manifiesto.update({
        "script": "analisis/43_predicciones_correccion_nivel.py",
        "configuracion": str(RUTA_CONFIG.relative_to(PROJECT_ROOT).as_posix()),
        "preregistro": raw["preregistro"],
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "corrida": [str(inicio), str(fin)],
        "dataset": {"ruta": raw["dataset"], "sha256": sha256(ruta_dataset)},
        "contrato_base": {"rutas": list(config.rutas), "objetivo": config.objetivo,
                          "min_franjas": config.min_franjas, "paso_muestreo": config.paso_muestreo,
                          "tipos_baja_frecuencia": list(config.tipos_baja_frecuencia)},
        "referencia_52s": {"semanas": semanas, "franjas": len(ref),
                           "franjas_sin_media": int(ref["sin_media"].sum())},
        "controles": controles,
    })
    manifiesto_ruta.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(controles, indent=1))

    fallos = []
    for metodo in raw["metodos"]:
        c = controles[metodo]
        if c["solo_en_uno"] or any(v >= tol for k, v in c.items() if k.startswith("max_dif")):
            fallos.append(metodo)
    c = controles["referencia_52s_vs_gru"]
    if c["sin_par"] or not c["max_dif"] < tol:
        fallos.append("referencia_52s")
    assert not fallos, f"controles de reproduccion fallidos: {fallos}"
    print("Controles de reproduccion superados.")


if __name__ == "__main__":
    main()
