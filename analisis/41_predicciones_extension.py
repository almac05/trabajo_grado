"""Predicciones del sistema congelado sobre el periodo 2026-06-11 a 2026-10-03.

Reutiliza sin cambios el protocolo del freeze freeze_20260922_203820
(`proyecto_grado.modeling.hparam_search.reevaluacion.ejecutar_metodo`):
reentrenamiento diario, ventanas de 26 semanas (SARIMA, Prophet, XGBoost) y 52
(redes), parada temprana de 2 semanas, min_franjas y referencias de media
historica por tipo de dia y franja con la ventana de cada metodo. Los
hiperparametros son los seleccionados por la busqueda; nada se reajusta.

Solo cambian el periodo y el dataset, declarados en
configs/modeling/evaluacion_extension_20260611_20261003.yaml. El resto del
contrato sale de configs/modeling/evaluacion_comparativa.yaml.

Antes de predecir, verifica que el protocolo reproduce el freeze: reejecuta
XGBoost en el periodo de evaluacion original, con el dataset original, y lo
compara con predicciones__xgboost__freeze_20260922_203820.csv.

Salidas nuevas en analisis/salidas/ con el sufijo del YAML:
  predicciones__<metodo>__<sufijo>.csv, resumen__<metodo>__<sufijo>.csv,
  jornadas_comunes__<sufijo>.csv, manifiesto__predicciones__<sufijo>.json.
Un metodo cuyas salidas ya existen no se recalcula (permite reanudar); nunca se
sobrescriben archivos.

Uso:
    python analisis/41_predicciones_extension.py
"""

import argparse
import hashlib
import json
import time
from dataclasses import replace
from datetime import date, datetime

import pandas as pd
import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion
from proyecto_grado.modeling.hparam_search.consolidacion_freeze_nuevo import soporte_comun
from proyecto_grado.modeling.hparam_search.reevaluacion import (
    _COLUMNA_PRED,
    _IDENTIFICADOR,
    cargar_configuraciones_seleccionadas,
    ejecutar_metodo,
)

RUTA_CONFIG = PROJECT_ROOT / "configs" / "modeling" / "evaluacion_extension_20260611_20261003.yaml"


def cargar_extension():
    raw = yaml.safe_load(RUTA_CONFIG.read_text(encoding="utf-8"))
    assert raw["periodo"]["extremos_inclusivos"] is True
    base = cargar_configuracion_evaluacion()
    inicio, fin = (date.fromisoformat(str(raw["periodo"][k])) for k in ("inicio", "fin"))
    assert inicio > base.fin, "el periodo nuevo debe empezar despues del de evaluacion"
    return raw, base, replace(base, inicio=inicio, fin=fin)


def sha256(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verificar_reproduccion(base, params) -> dict:
    """XGBoost en el periodo y dataset originales frente al freeze."""
    df = pd.read_parquet(base.ruta_dataset)
    _, pred = ejecutar_metodo("XGBoost", params, base, df)
    ref = pd.read_csv(PROJECT_ROOT / "analisis" / "salidas" / "predicciones__xgboost__freeze_20260922_203820.csv")
    pred["dia_op"] = pd.to_datetime(pred["dia_op"]).dt.strftime("%Y-%m-%d")
    u = ref.merge(pred, on=["route", "dia_op", "hora"], suffixes=("_freeze", "_nuevo"), how="outer", indicator=True)
    ambos = u[u["_merge"] == "both"]
    return {
        "franjas_freeze": len(ref), "franjas_reejecucion": len(pred),
        "solo_en_uno": int((u["_merge"] != "both").sum()),
        "max_dif_pred_xgboost": float((ambos["pred_xgboost_freeze"] - ambos["pred_xgboost_nuevo"]).abs().max()),
        "max_dif_pred_media": float((ambos["pred_media_freeze"] - ambos["pred_media_nuevo"]).abs().max()),
        "max_dif_real": float((ambos["real_freeze"] - ambos["real_nuevo"]).abs().max()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sin-verificacion", action="store_true",
                        help="Omite la reejecucion de XGBoost en el periodo original.")
    args = parser.parse_args()

    raw, base, config = cargar_extension()
    sufijo = raw["sufijo"]
    salida = PROJECT_ROOT / raw["salidas"]["directorio"]
    ruta_dataset = PROJECT_ROOT / raw["dataset"]
    seleccion = cargar_configuraciones_seleccionadas(PROJECT_ROOT / raw["seleccion_hiperparametros"])
    manifiesto_ruta = salida / f"manifiesto__predicciones__{sufijo}.json"
    manifiesto = (json.loads(manifiesto_ruta.read_text(encoding="utf-8")) if manifiesto_ruta.exists()
                  else {"metodos": {}})

    if not args.sin_verificacion and "verificacion_reproduccion" not in manifiesto:
        print("Verificando la reproduccion del freeze con XGBoost...")
        manifiesto["verificacion_reproduccion"] = verificar_reproduccion(base, seleccion["XGBoost"])
        print(manifiesto["verificacion_reproduccion"])
        # El freeze guarda pred_xgboost en float32 (~7 cifras): tolerancia 1e-4 pasajeros.
        assert manifiesto["verificacion_reproduccion"]["max_dif_pred_xgboost"] < 1e-4, "no reproduce el freeze"

    df = pd.read_parquet(ruta_dataset)
    for metodo, params in seleccion.items():
        ident = _IDENTIFICADOR[metodo]
        ruta_pred = salida / f"predicciones__{ident}__{sufijo}.csv"
        ruta_res = salida / f"resumen__{ident}__{sufijo}.csv"
        if ruta_pred.exists() and ruta_res.exists():
            print(f"{metodo}: ya existe, se omite")
            continue
        assert not ruta_pred.exists() and not ruta_res.exists(), f"salida parcial de {metodo}"
        print(f"\n{'=' * 60}\n{metodo} {params}\n{'=' * 60}")
        t0 = time.perf_counter()
        resumen, pred = ejecutar_metodo(metodo, params, config, df)
        resumen.to_csv(ruta_res, index=False)
        pred.to_csv(ruta_pred, index=False)
        manifiesto["metodos"][metodo] = {
            "parametros": params, "columna": _COLUMNA_PRED[metodo],
            "semanas_entrenamiento": config.metodo(metodo).semanas_entrenamiento,
            "semanas_parada_temprana": config.metodo(metodo).semanas_parada_temprana,
            "jornadas": int(resumen[["route", "dia_op"]].drop_duplicates().shape[0]),
            "franjas": len(pred), "minutos": round((time.perf_counter() - t0) / 60, 1),
        }
        manifiesto_ruta.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"{metodo}: {manifiesto['metodos'][metodo]}")

    datos = {}
    for metodo, ident in _IDENTIFICADOR.items():
        d = pd.read_csv(salida / f"predicciones__{ident}__{sufijo}.csv")
        d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.date
        datos[metodo] = d
    comun = sorted(soporte_comun(datos))
    ruta_comun = salida / f"jornadas_comunes__{sufijo}.csv"
    if not ruta_comun.exists():
        pd.DataFrame(comun, columns=["route", "dia_op"]).to_csv(ruta_comun, index=False)
    manifiesto.update({
        "script": "analisis/41_predicciones_extension.py",
        "configuracion": str(RUTA_CONFIG.relative_to(PROJECT_ROOT).as_posix()),
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "periodo": [str(config.inicio), str(config.fin)],
        "dataset": {"ruta": raw["dataset"], "sha256": sha256(ruta_dataset)},
        "contrato_base": {"rutas": list(config.rutas), "objetivo": config.objetivo,
                          "min_franjas": config.min_franjas, "paso_muestreo": config.paso_muestreo,
                          "tipos_baja_frecuencia": list(config.tipos_baja_frecuencia)},
        "jornadas_comunes": len(comun),
    })
    manifiesto_ruta.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nJornadas comunes: {len(comun)}")


if __name__ == "__main__":
    main()
