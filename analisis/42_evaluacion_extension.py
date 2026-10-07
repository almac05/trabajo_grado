"""Evaluacion fuera de muestra del sistema congelado (2026-06-11 a 2026-10-03).

Lee las predicciones del script 41 y, sobre el soporte comun de los seis metodos,
calcula metricas para los seis metodos, las dos referencias, la referencia
combinada (26 s en regimen ordinario, 52 s en raro) y el predictor mixto
(XGBoost en ordinario, referencia de 52 s en raro): MAE, MedAE, RMSE, WAPE y
sesgo (prediccion - real), globales, por ruta, por regimen y por tipo de dia,
con jornadas y franjas de cada celda. Las mismas metricas se calculan para el
periodo de evaluacion del freeze freeze_20260922_203820, para contrastar:
  1. XGBoost y la referencia de 26 s equivalentes en MAE global (|dif| < 2 %).
  2. |sesgo| global de XGBoost menor que el de las dos referencias y las tres redes.
  3. El predictor mixto supera a XGBoost en regimen raro (MAE; se informan
     tambien MedAE, WAPE y |sesgo|).
  4. Si el sesgo de las referencias es mayor que en el periodo de evaluacion.

Modulo de recomendacion, sin recalibrar: parametros persistidos de la
calibracion original (2025-12-25 a 2026-04-01) y su capacidad conjunta;
politica de festivos y servicio minimo de configs/dispatch/recomendacion.yaml.
Se evalua sin tope (como el analisis 38) y con tope (valor configurado). Tabla 2
a escala de franja y de bloque horario (bloques de una jornada) para la demanda
de la prediccion mixta, la demanda real (cota superior) y la referencia de 26 s,
junto con la practica real; y jornadas con ajuste de factibilidad.

No modifica ningun archivo existente; salidas nuevas en analisis/salidas/ con el
sufijo de configs/modeling/evaluacion_extension_20260611_20261003.yaml.

Uso:
    python analisis/42_evaluacion_extension.py
"""

import json
from datetime import date, datetime

import numpy as np
import pandas as pd
import yaml

from proyecto_grado.dispatch.config import cargar_configuracion_recomendacion
from proyecto_grado.dispatch.evaluacion import (
    CLASES,
    clasificar,
    construir_franjas_evaluacion,
    franjas_reales,
    tabla_clasificacion,
)
from proyecto_grado.dispatch.parametros import (
    ParametrosCalibracion,
    filtrar_periodo,
    preparar_despachos,
)
from proyecto_grado.dispatch.reglas import generar_recomendacion
from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion

RUTA_CONFIG = PROJECT_ROOT / "configs" / "modeling" / "evaluacion_extension_20260611_20261003.yaml"
METODOS = {  # nombre -> (identificador, columna)
    "SARIMA": ("sarima", "pred_sarima"),
    "Prophet": ("prophet", "pred_prophet"),
    "XGBoost": ("xgboost", "pred_xgboost"),
    "LSTM": ("lstm", "pred_lstm"),
    "GRU": ("gru", "pred_gru"),
    "CNN-LSTM": ("cnn_lstm", "pred_cnn_lstm"),
}
REF26, REF52 = "Referencia (26s)", "Referencia (52s)"
COMBINADA = "Combinada (26s/52s)"
MIXTO = "Mixto (XGBoost ordinario / 52s raro)"
PREDICTORES = [*METODOS, REF26, REF52, COMBINADA, MIXTO]
REDES = ("LSTM", "GRU", "CNN-LSTM")
CLAVES = ["route", "dia_op", "hora"]
UMBRAL_EQUIVALENCIA = 0.02


# --------------------------------------------------------------- observaciones


def cargar_observaciones(salida, sufijo, tipos_raros):
    """Tabla ancha por franja del soporte comun con las diez predicciones."""
    comunes = pd.read_csv(salida / f"jornadas_comunes__{sufijo}.csv").astype({"route": int, "dia_op": str})
    base = None
    franjas_por_metodo = {}
    for nombre, (ident, col) in METODOS.items():
        d = pd.read_csv(salida / f"predicciones__{ident}__{sufijo}.csv").astype(
            {"route": int, "dia_op": str, "hora": str})
        d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.strftime("%Y-%m-%d")
        d = d.merge(comunes, on=["route", "dia_op"])
        franjas_por_metodo[nombre] = len(d)
        keep = d[[*CLAVES, "tipo_dia", "real", col]].rename(columns={col: nombre})
        if ident == "xgboost":
            keep[REF26] = d["pred_media"].to_numpy()
        if ident == "gru":
            keep[REF52] = d["pred_media"].to_numpy()
        if base is None:
            base = keep
        else:
            n_antes = len(base)
            base = base.merge(keep.drop(columns=["tipo_dia"]), on=CLAVES, how="inner",
                              suffixes=("", "__otro"), validate="1:1")
            assert np.allclose(base.pop("real__otro"), base["real"]), nombre
            assert len(base) == n_antes == len(keep), f"franjas distintas en {nombre}"
    base["regimen"] = np.where(base["tipo_dia"].isin(tipos_raros), "raro", "ordinario")
    raro = base["regimen"] == "raro"
    base[COMBINADA] = base[REF52].where(raro, base[REF26])
    base[MIXTO] = base[REF52].where(raro, base["XGBoost"])
    return base, franjas_por_metodo


# ------------------------------------------------------------------- metricas


def metricas(real, pred):
    e = pred - real
    a = np.abs(e)
    return {"mae": a.mean(), "medae": float(np.median(a)), "rmse": float(np.sqrt(np.mean(e ** 2))),
            "wape": 100 * a.sum() / real.sum(), "sesgo": e.mean()}


def tabla_metricas(obs, periodo):
    cortes = {"global": [("todos", obs)],
              "por_ruta": [(str(k), g) for k, g in obs.groupby("route")],
              "por_regimen": list(obs.groupby("regimen")),
              "por_tipo_dia": list(obs.groupby("tipo_dia"))}
    filas = []
    for corte, grupos in cortes.items():
        for celda, g in grupos:
            for p in PREDICTORES:
                filas.append({"periodo": periodo, "corte": corte, "celda": celda, "metodo": p,
                              "n_jornadas": int(g[["route", "dia_op"]].drop_duplicates().shape[0]),
                              "n_franjas": len(g), "demanda_media": g["real"].mean(),
                              **metricas(g["real"].to_numpy(float), g[p].to_numpy(float))})
    return pd.DataFrame(filas)


def valor(t, periodo, corte, celda, metodo, col):
    s = t[(t["periodo"] == periodo) & (t["corte"] == corte) & (t["celda"] == celda) & (t["metodo"] == metodo)]
    return float(s[col].iloc[0])


def contraste(t):
    out = {}
    for periodo in ("evaluacion", "extension"):
        xgb = valor(t, periodo, "global", "todos", "XGBoost", "mae")
        r26 = valor(t, periodo, "global", "todos", REF26, "mae")
        sesgos = {m: abs(valor(t, periodo, "global", "todos", m, "sesgo")) for m in [*METODOS, REF26, REF52]}
        raro = {m: {k: valor(t, periodo, "por_regimen", "raro", m, k) for k in ("mae", "medae", "wape", "sesgo")}
                for m in (MIXTO, "XGBoost")}
        out[periodo] = {
            "1_equivalencia_mae": {"xgboost": xgb, "referencia_26s": r26, "dif_relativa": (xgb - r26) / r26,
                                   "se_mantiene": abs(xgb - r26) / r26 < UMBRAL_EQUIVALENCIA},
            "2_sesgo_xgboost": {"abs_sesgo": sesgos,
                                "se_mantiene": all(sesgos["XGBoost"] < sesgos[m] for m in (REF26, REF52, *REDES))},
            "3_mixto_raro": {"metricas": raro,
                             "se_mantiene": raro[MIXTO]["mae"] < raro["XGBoost"]["mae"],
                             "medae_menor": raro[MIXTO]["medae"] < raro["XGBoost"]["medae"],
                             "wape_menor": raro[MIXTO]["wape"] < raro["XGBoost"]["wape"],
                             "abs_sesgo_menor": abs(raro[MIXTO]["sesgo"]) < abs(raro["XGBoost"]["sesgo"])},
            "4_sesgo_referencias": {
                f"{m}|{celda}": valor(t, periodo, corte, celda, m, "sesgo")
                for m in (REF26, REF52, COMBINADA)
                for corte, celda in (("global", "todos"), ("por_regimen", "ordinario"), ("por_regimen", "raro"))},
        }
    out["4_sesgo_referencias_mayor_en_extension"] = {
        k: out["extension"]["4_sesgo_referencias"][k] > out["evaluacion"]["4_sesgo_referencias"][k]
        for k in out["extension"]["4_sesgo_referencias"]}
    return out


# ----------------------------------------------------------- recomendacion


def a_bloques(franjas):
    """Una fila por ruta, jornada y bloque, con las columnas de la Tabla 2."""
    b = (franjas.groupby(["route", "dia_op", "bloque"])
         .agg(regimen=("regimen", "first"), n_regimenes=("regimen", "nunique"),
              q1=("q1", "first"), q3=("q3", "first"), n_umbrales=("q3", "nunique"),
              pasajeros_real=("pasajeros_real", "sum"), despachos_real=("despachos_real", "sum"),
              despachos_recomendados=("despachos_recomendados", "sum"))
         .reset_index())
    assert (b["n_regimenes"] == 1).all() and (b["n_umbrales"] == 1).all()
    b["ppd_real"] = (b["pasajeros_real"] / b["despachos_real"]).where(b["despachos_real"] > 0)
    b["clase_real"] = clasificar(b["ppd_real"], b["q1"], b["q3"])
    b["ppd_recomendada"] = b["pasajeros_real"] / b["despachos_recomendados"]
    b["clase_recomendada"] = clasificar(b["ppd_recomendada"], b["q1"], b["q3"])
    return b.drop(columns=["n_regimenes", "n_umbrales"])


def proporciones(unidades, variante, escala, tope):
    filas = []
    con_real = unidades[unidades["despachos_real"] > 0]
    for ruta, g in [*con_real.groupby("route"), ("ambas", con_real)]:
        for origen, col in (("practica_real", "clase_real"), ("recomendacion", "clase_recomendada")):
            fila = {"usar_tope": tope, "variante": variante, "escala": escala, "route": str(ruta),
                    "origen": origen, "n_unidades": len(g),
                    "despachos": int(g["despachos_real" if origen == "practica_real" else "despachos_recomendados"].sum())}
            for clase in CLASES:
                fila[f"pct_{clase}"] = 100 * (g[col] == clase).mean()
            if origen == "recomendacion":
                fila["pct_misma_clase"] = 100 * (g["clase_real"] == g["clase_recomendada"]).mean()
            filas.append(fila)
    return filas


def recomendacion(raw, obs, tipos_raros):
    cfg_rec = cargar_configuracion_recomendacion()
    rec_raw = raw["recomendacion"]
    tabla = pd.read_csv(PROJECT_ROOT / rec_raw["parametros"])
    man = json.loads((PROJECT_ROOT / rec_raw["manifiesto"]).read_text(encoding="utf-8"))["parametros"]
    parametros = ParametrosCalibracion(tabla=tabla, capacidad=int(man["capacidad"]),
                                       jornada_capacidad=date.fromisoformat(man["jornada_capacidad"]))

    mr = pd.read_parquet(PROJECT_ROOT / rec_raw["model_ready"],
                         columns=["FK_RUTA", "HORA_INICIAL_REAL", cfg_rec.columna_pasajeros, "MODEL_READY_OK"])
    td = pd.read_parquet(PROJECT_ROOT / raw["dataset"], columns=["FK_RUTA", "timestamp", "tipo_dia"])
    desp = preparar_despachos(mr, td, cfg_rec.bloques, tipos_raros, cfg_rec.columna_pasajeros)
    inicio, fin = (date.fromisoformat(str(raw["periodo"][k])) for k in ("inicio", "fin"))
    # Despachos antes del primer bloque (04:00): no tienen franja predicha; se excluyen y se cuentan.
    en_periodo = (desp["dia_op"] >= inicio) & (desp["dia_op"] <= fin)
    fuera_bloque = desp[en_periodo & desp["bloque"].isna()]
    reales = franjas_reales(filtrar_periodo(desp[desp["bloque"].notna()], inicio, fin))

    base = obs[[*CLAVES, "tipo_dia", "regimen", "real"]].copy()
    variantes = {"mixta": obs[MIXTO], "real": obs["real"], "ref26": obs[REF26]}
    orden = list(cfg_rec.nombres_bloques)
    clasif, prop, ajustes, verif = [], [], [], {}
    for tope in (False, True):
        for variante, demanda in variantes.items():
            rec, ajuste = generar_recomendacion(base.assign(demanda_predicha=demanda.to_numpy()), parametros,
                                                cfg_rec.bloques, cfg_rec.politica_festivos, tope,
                                                cfg_rec.servicio_minimo)
            franjas, v = construir_franjas_evaluacion(rec, reales)
            verif[f"{variante}|tope={tope}"] = v
            ajustes.append({"usar_tope": tope, "variante": variante, "jornadas": len(ajuste),
                            "jornadas_ajustadas": int(ajuste["ajustada"].sum()),
                            "despachos_retirados": int(ajuste["retirados"].sum()),
                            "jornadas_no_factibles": int((~ajuste["factible"]).sum())})
            for escala, unidades in (("franja", franjas), ("bloque", a_bloques(franjas))):
                resumen, _ = tabla_clasificacion(unidades, orden)
                clasif.append(resumen.assign(usar_tope=tope, variante=variante, escala=escala))
                prop += proporciones(unidades, variante, escala, tope)
    contexto = {"capacidad": parametros.capacidad, "politica_festivos": cfg_rec.politica_festivos,
                "servicio_minimo": cfg_rec.servicio_minimo, "union_operacion_real": verif,
                "despachos_fuera_de_bloque_excluidos": fuera_bloque[["route", "dia_op", "hora"]].astype(str).to_dict("records")}
    return pd.concat(clasif, ignore_index=True), pd.DataFrame(prop), pd.DataFrame(ajustes), contexto


# ------------------------------------------------------------------- main


def jornadas_por_tipo(raw, obs):
    td = pd.read_parquet(PROJECT_ROOT / raw["dataset"], columns=["FK_RUTA", "timestamp", "tipo_dia"])
    td["dia_op"] = (td["timestamp"] - pd.Timedelta(hours=4)).dt.normalize()
    inicio, fin = (pd.Timestamp(str(raw["periodo"][k])) for k in ("inicio", "fin"))
    td = td[(td["dia_op"] >= inicio) & (td["dia_op"] <= fin)]
    cal = td.drop_duplicates("dia_op").groupby("tipo_dia").size().rename("dias_calendario")
    dataset = td.drop_duplicates(["FK_RUTA", "dia_op"]).groupby("tipo_dia").size().rename("jornadas_ruta_en_dataset")
    soporte = obs.drop_duplicates(["route", "dia_op"]).groupby("tipo_dia").size().rename("jornadas_ruta_soporte_comun")
    return pd.concat([cal, dataset, soporte], axis=1).fillna(0).astype(int).reset_index()


def main():
    raw = yaml.safe_load(RUTA_CONFIG.read_text(encoding="utf-8"))
    sufijo, freeze = raw["sufijo"], raw["freeze_evaluacion"]
    salida = PROJECT_ROOT / raw["salidas"]["directorio"]
    tipos_raros = cargar_configuracion_evaluacion().tipos_baja_frecuencia
    rutas_salida = {n: salida / f"{n}__{sufijo}.{e}" for n, e in (
        ("metricas", "csv"), ("contraste", "json"), ("jornadas_tipo_dia", "csv"), ("observaciones", "csv"),
        ("clasificacion_recomendacion", "csv"), ("proporciones_recomendacion", "csv"),
        ("ajuste_factibilidad", "csv"), ("manifiesto", "json"))}
    existentes = [str(r) for r in rutas_salida.values() if r.exists()]
    assert not existentes, f"no se sobrescriben salidas: {existentes}"

    obs, franjas_metodo = cargar_observaciones(salida, sufijo, tipos_raros)
    obs_eval, _ = cargar_observaciones(salida, freeze, tipos_raros)
    t = pd.concat([tabla_metricas(obs_eval, "evaluacion"), tabla_metricas(obs, "extension")], ignore_index=True)
    cont = contraste(t)
    tipos = jornadas_por_tipo(raw, obs)
    clasif, prop, ajustes, ctx = recomendacion(raw, obs, tipos_raros)

    t.to_csv(rutas_salida["metricas"], index=False)
    rutas_salida["contraste"].write_text(json.dumps(cont, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tipos.to_csv(rutas_salida["jornadas_tipo_dia"], index=False)
    obs.to_csv(rutas_salida["observaciones"], index=False)
    clasif.to_csv(rutas_salida["clasificacion_recomendacion"], index=False)
    prop.to_csv(rutas_salida["proporciones_recomendacion"], index=False)
    ajustes.to_csv(rutas_salida["ajuste_factibilidad"], index=False)
    manifiesto = {
        "script": "analisis/42_evaluacion_extension.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "configuracion": str(RUTA_CONFIG.relative_to(PROJECT_ROOT).as_posix()),
        "sufijo": sufijo, "freeze_evaluacion": freeze,
        "soporte": {"jornadas": int(obs[["route", "dia_op"]].drop_duplicates().shape[0]), "franjas": len(obs),
                    "franjas_por_metodo_en_soporte": franjas_metodo,
                    "evaluacion_jornadas": int(obs_eval[["route", "dia_op"]].drop_duplicates().shape[0]),
                    "evaluacion_franjas": len(obs_eval)},
        "recomendacion": ctx,
        "salidas": [str(r.relative_to(PROJECT_ROOT).as_posix()) for r in rutas_salida.values()],
    }
    rutas_salida["manifiesto"].write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"soporte": manifiesto["soporte"], "contraste": cont}, ensure_ascii=False, indent=1, default=str))
    print(tipos.to_string(index=False))
    print(ajustes.to_string(index=False))


if __name__ == "__main__":
    main()
