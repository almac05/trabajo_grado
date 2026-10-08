"""Planilla de muestra del modulo de recomendacion para una jornada (--fecha).

Simula que la recomendacion se produjo la vispera, con informacion hasta el
cierre de la jornada anterior (corte: 04:00 de la fecha, inicio de la jornada
operativa). Solo lee data/actualizacion_20261004/, los hiperparametros congelados
de la busqueda y los parametros calibrados del modulo; no consulta la base de
datos ni modifica ningun archivo existente.

1. Datos anteriores al corte: filas del dataset de modelado con timestamp < corte.
   Las franjas de la jornada objetivo son las del horario operativo congelado de
   su ruta y tipo de dia, tomadas de la jornada anterior al corte del mismo tipo
   de dia (el horario solo depende de la ruta, el tipo de dia y la hora). Se
   verifica que las franjas que el dataset tiene para la jornada objetivo esten
   entre ellas. De la jornada objetivo solo se usan las variables predictoras;
   para una franja sin fila en el dataset (solo ocurre en la ultima jornada del
   dataset, cuya grilla termina en la ultima observacion) se usan las variables
   recalculadas del punto 2, y se marca.
2. Verificacion de fuga: las 15 variables de XGBoost de la jornada objetivo se
   recalculan desde el conjunto apto truncado en el corte y desde el calendario,
   y se comparan con las del dataset; los objetivos de entrenamiento tambien.
3. Predictor C3 del preregistro (docs/preregistro_correccion_nivel.md): XGBoost
   con el protocolo congelado en regimen ordinario, multiplicado por el factor de
   14 dias (las 14 jornadas anteriores, cerradas), y la referencia de 52 semanas
   en regimen raro. Las predicciones de la ventana se recalculan con el mismo
   protocolo, cada una con datos anteriores a su jornada.
4. Modulo de recomendacion con las reglas de configs/dispatch/recomendacion.yaml
   (incluido el tope de carga que alli figura) y los parametros calibrados del
   freeze de esa configuracion.
5. Comparacion con la operacion real de la jornada (solo despues de predecir).

Salidas en data/muestra_planilla/ (con su propio .gitignore): planilla,
comparacion, verificaciones en JSON y detalle por franja en CSV. Nunca
sobrescribe.

Uso:
    python scripts/muestra_planilla_20261001.py --fecha 2026-10-01
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, timedelta

import holidays
import numpy as np
import pandas as pd

from proyecto_grado.dispatch.config import cargar_configuracion_recomendacion
from proyecto_grado.dispatch.evaluacion import construir_franjas_evaluacion, franjas_reales
from proyecto_grado.dispatch.parametros import (
    REGIMEN_RARO,
    ParametrosCalibracion,
    filtrar_periodo,
    preparar_despachos,
)
from proyecto_grado.dispatch.reglas import generar_recomendacion, redondeo_aritmetico
from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.fits import ajustar_predecir_xgboost
from proyecto_grado.modeling.hparam_search.reevaluacion import (
    cargar_configuraciones_seleccionadas,
    ejecutar_metodo,
)
from proyecto_grado.modeling.hparam_search.runner import _preparar_ruta

VENTANA_DIAS = 14
SEMANAS_REF_LARGA = 52

ACT = PROJECT_ROOT / "data" / "actualizacion_20261004"
RUTA_DATASET = (
    ACT / "processed" / "modeling" / "modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
)
RUTA_MODEL_READY = (
    ACT / "processed" / "model_ready" / "despachos_model_ready_freeze_20261005_011520.parquet"
)
RUTA_HIPERPARAMETROS = PROJECT_ROOT / "analisis" / "salidas" / "busqueda_hiperparametros"
SALIDA = PROJECT_ROOT / "data" / "muestra_planilla"

# Contraste opcional con las salidas comprometidas del script 43/44 (mismo dataset).
SUF_CN = "correccion_nivel_20251127_20261003"
RUTA_43_XGB = PROJECT_ROOT / "analisis" / "salidas" / f"predicciones__xgboost__{SUF_CN}.csv"
RUTA_44_SERIE = PROJECT_ROOT / "analisis" / "salidas" / f"serie_correccion__{SUF_CN}.csv"

CLASE = {"subutilizada": "baja", "normal": "normal", "sobrecargada": "alta"}
NOTA_PLANILLA = (
    "Si no hay conductores disponibles para cumplir la meta de una franja, registrar SIN CONDUCTOR"
)
LAGS = ("_lag_48", "_lag_96", "_lag_336")
TOL = 1e-4


def sha256(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iguales(a, b, tol=TOL) -> bool:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return bool(
        np.array_equal(np.isnan(a), np.isnan(b))
        and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], atol=tol)
    )


# ------------------------------------------------------- franjas y variables


def agregado_truncado(mr, corte):
    """Pasajeros y despachos por ruta y franja con salida anterior al corte."""
    mr = mr[mr["MODEL_READY_OK"].eq(True) & mr["FK_RUTA"].isin([1, 3])].copy()
    mr["HORA_INICIAL_REAL"] = pd.to_datetime(mr["HORA_INICIAL_REAL"])
    trunc = mr[mr["HORA_INICIAL_REAL"] < corte].copy()
    trunc["ts"] = trunc["HORA_INICIAL_REAL"].dt.floor("30min")
    agg = trunc.groupby(["FK_RUTA", "ts"]).agg(
        pas=("PASAJEROS_REALES", "sum"), n=("PK_INTERVALO_DESPACHO", "count")
    )
    return agg, len(trunc), int((mr["HORA_INICIAL_REAL"] >= corte).sum())


def variables_recalculadas(filas, features, agg, corte, dia):
    """Las variables de XGBoost de `filas` (FK_RUTA, timestamp) recalculadas solo
    con el agregado anterior al corte y con el calendario."""
    fest = set()
    for y in (dia.year - 1, dia.year):
        fest |= set(holidays.Colombia(years=y))
    out = {}
    for col in features:
        esperado = []
        for _, r in filas.iterrows():
            ts = r["timestamp"]
            if col.endswith(LAGS):
                k = int(col.rsplit("_", 1)[1])
                fuente = ts - pd.Timedelta(minutes=30 * k)
                assert fuente < corte, f"{col} de {ts} apunta a {fuente}"
                v = agg.loc[(r["FK_RUTA"], fuente)] if (r["FK_RUTA"], fuente) in agg.index else None
                if v is None:
                    esperado.append(np.nan)
                elif col.startswith("pasajeros_total"):
                    esperado.append(v["pas"])
                else:
                    esperado.append(v["pas"] / v["n"] if v["n"] > 0 else np.nan)
            elif col == "hora_del_dia":
                esperado.append(ts.hour)
            elif col == "dia_semana":
                esperado.append(ts.dayofweek)
            elif col == "es_fin_semana":
                esperado.append(ts.dayofweek >= 5)
            elif col == "es_festivo":
                esperado.append(ts.date() in fest)
            elif col == "hora_sin":
                esperado.append(np.sin(2 * np.pi * (ts.hour * 60 + ts.minute) / 1440))
            elif col == "hora_cos":
                esperado.append(np.cos(2 * np.pi * (ts.hour * 60 + ts.minute) / 1440))
            elif col == "dia_semana_sin":
                esperado.append(np.sin(2 * np.pi * ts.dayofweek / 7))
            elif col == "dia_semana_cos":
                esperado.append(np.cos(2 * np.pi * ts.dayofweek / 7))
            elif col == "dentro_horario_operativo":
                esperado.append(True)
            else:
                raise AssertionError(f"variable sin verificacion definida: {col}")
        out[col] = esperado
    return pd.DataFrame(out, index=filas.index)


def tipo_dia_calendario(dia):
    fest = set(holidays.Colombia(years=dia.year))
    if dia in fest:
        return "FESTIVO_PUENTE" if dia.weekday() == 0 else "FESTIVO"
    return {5: "SABADO", 6: "DOMINGO"}.get(dia.weekday(), "LABORAL")


def franjas_objetivo(ds, hist, dia, corte):
    """Franjas del horario operativo de cada ruta para el tipo de dia de `dia`,
    tomadas de la jornada anterior al corte del mismo tipo de dia."""
    tipo = tipo_dia_calendario(dia)
    filas, info = [], {}
    for ruta in (1, 3):
        h = hist[(hist["FK_RUTA"] == ruta) & (hist["tipo_dia"] == tipo)]
        previa = h["dia_op"].max()
        plantilla = sorted(set(h.loc[h["dia_op"] == previa, "hora"]))
        en_ds = ds[(ds["FK_RUTA"] == ruta) & (ds["dia_op"] == dia)]
        assert set(en_ds["tipo_dia"]) <= {tipo}, (
            f"tipo de dia del dataset distinto del calendario en {dia}"
        )
        sobrantes = set(en_ds["hora"]) - set(plantilla)
        assert not sobrantes, (
            f"ruta {ruta}: franjas del dataset fuera del horario operativo: {sobrantes}"
        )
        faltan = [x for x in plantilla if x not in set(en_ds["hora"])]
        info[str(ruta)] = {
            "tipo_dia": tipo,
            "jornada_plantilla": str(previa),
            "franjas": len(plantilla),
            "franjas_del_dataset": len(en_ds),
            "franjas_reconstruidas": faltan,
        }
        base = pd.DataFrame({"hora": plantilla})
        base["timestamp"] = pd.to_datetime(str(dia) + " " + base["hora"])
        base.loc[base["timestamp"] < corte, "timestamp"] += pd.Timedelta(
            days=1
        )  # franjas despues de medianoche
        base = base.merge(en_ds.drop(columns=["timestamp"]), on="hora", how="left")
        base["FK_RUTA"], base["tipo_dia"], base["dia_op"] = ruta, tipo, dia
        base["franja_reconstruida"] = base["hora"].isin(faltan)
        filas.append(base)
    return pd.concat(filas, ignore_index=True), info


def verificar_fuga(ds, objetivo, features, recalculo, n_antes, n_desde, corte, ventana_inicio, agg):
    out = {
        "corte": str(corte),
        "variables": features,
        "despachos_conjunto_apto_antes_del_corte": n_antes,
        "despachos_conjunto_apto_desde_el_corte_ignorados": n_desde,
    }
    con_fila = ~objetivo["franja_reconstruida"]
    out["variables_iguales_al_recalculo"] = {
        col: iguales(
            objetivo.loc[con_fila, col].astype(float), recalculo.loc[con_fila, col].astype(float)
        )
        for col in features
    }
    out["franjas_reconstruidas"] = int((~con_fila).sum())

    hist = ds[
        (ds["timestamp"] < corte)
        & (ds["timestamp"] >= ventana_inicio)
        & ds["pasajeros_total"].notna()
    ]
    clave = list(zip(hist["FK_RUTA"], hist["timestamp"], strict=True))
    esperado = [agg.loc[c, "pas"] if c in agg.index else np.nan for c in clave]
    out["objetivos_entrenamiento"] = {
        "desde": str(ventana_inicio),
        "franjas": len(hist),
        "iguales_al_conjunto_apto_truncado": iguales(hist["pasajeros_total"], esperado),
    }
    out["max_timestamp_usado"] = str(ds.loc[ds["timestamp"] < corte, "timestamp"].max())
    return out


# ------------------------------------------------------------ prediccion


def referencia(d, test, target, semanas, inicio_dia):
    ent = d[
        (d["timestamp"] >= inicio_dia - pd.Timedelta(weeks=semanas)) & (d["timestamp"] < inicio_dia)
    ]
    medias = ent.groupby(["tipo_dia", "hora"])[target].mean()
    idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
    return pd.Series(medias.reindex(idx).to_numpy()).fillna(ent[target].mean()).to_numpy()


def predecir_objetivo(hist, objetivo, config, params, dia, corte):
    """XGBoost con el protocolo congelado (rama XGBoost de ejecutar_metodo), sobre
    todas las franjas de la jornada objetivo, y referencia de 52 semanas."""
    m = config.metodo("XGBoost")
    filas = []
    for ruta in config.rutas:
        d = _preparar_ruta(hist, ruta, config.objetivo)
        assert d["timestamp"].max() < corte
        features = seleccionar_features(d)
        corte_parada = corte - pd.Timedelta(weeks=m.semanas_parada_temprana)
        train = d[
            (d["timestamp"] >= corte - pd.Timedelta(weeks=m.semanas_entrenamiento))
            & (d["timestamp"] < corte)
        ]
        fit_df, stop_df = (
            train[train["timestamp"] < corte_parada],
            train[train["timestamp"] >= corte_parada],
        )
        test = objetivo[objetivo["FK_RUTA"] == ruta].sort_values("timestamp")
        pred, arboles = ajustar_predecir_xgboost(
            fit_df, stop_df, test, features, config.objetivo, params
        )
        filas.append(
            pd.DataFrame(
                {
                    "route": ruta,
                    "dia_op": str(dia),
                    "timestamp": test["timestamp"].to_numpy(),
                    "hora": test["hora"].to_numpy(),
                    "tipo_dia": test["tipo_dia"].to_numpy(),
                    "franja_reconstruida": test["franja_reconstruida"].to_numpy(),
                    "pred_xgboost": pred.astype(float),
                    "ref52": referencia(d, test, config.objetivo, SEMANAS_REF_LARGA, corte),
                    "arboles": arboles,
                    "franjas_ajuste": len(fit_df),
                    "franjas_parada": len(stop_df),
                }
            )
        )
    return pd.concat(filas, ignore_index=True)


def factor_c3(hist, config, params, tipos_raros, dia):
    """Factor de 14 dias del preregistro: predicciones de XGBoost de cada jornada
    de la ventana (cada una con datos anteriores a esa jornada) y su demanda real."""
    ini = dia - timedelta(days=VENTANA_DIAS)
    fin = dia - timedelta(days=1)
    _, pred = ejecutar_metodo("XGBoost", params, replace(config, inicio=ini, fin=fin), hist)
    pred["dia_op"] = pd.to_datetime(pred["dia_op"]).dt.strftime("%Y-%m-%d")
    assert pd.to_datetime(pred["dia_op"]).max().date() <= fin
    ordi = pred[~pred["tipo_dia"].isin(tipos_raros)]
    res = {}
    for ruta, g in ordi.groupby("route"):
        s_real, s_pred = g["real"].sum(), g["pred_xgboost"].sum()
        res[int(ruta)] = {
            "ventana": [str(ini), str(fin)],
            "jornadas": int(g["dia_op"].nunique()),
            "franjas": len(g),
            "suma_real": float(s_real),
            "suma_pred": float(s_pred),
            "factor": float(s_real / s_pred) if len(g) and s_pred > 0 else 1.0,
            "aplicado": bool(len(g) and s_pred > 0),
        }
    return res, pred


def divisor_usado(rec, usar_tope, minimo):
    d = np.clip(rec["demanda_predicha"].to_numpy(float), 0, None)
    raro = (rec["regimen"] == REGIMEN_RARO).to_numpy()
    por_mediana = redondeo_aritmetico(d / rec["divisor"].to_numpy(float))
    por_tope = np.ceil(d / rec["q3_ordinario"].to_numpy(float)) if usar_tope else np.zeros_like(d)
    criterio = np.where(
        raro,
        "mediana del regimen raro",
        np.where(por_tope > por_mediana, "Q3 (tope de carga)", "mediana del bloque"),
    )
    divisor = np.where(~raro & (por_tope > por_mediana), rec["q3_ordinario"], rec["divisor"])
    base = np.where(~raro & (por_tope > por_mediana), por_tope, por_mediana)
    criterio = np.where(base < minimo, "servicio minimo", criterio)
    return divisor, criterio


# ------------------------------------------------------------------- main


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--fecha", required=True, type=date.fromisoformat, help="Jornada objetivo, AAAA-MM-DD."
    )
    dia = parser.parse_args().fecha
    corte = pd.Timestamp(dia) + pd.Timedelta(hours=4)

    SALIDA.mkdir(parents=True, exist_ok=True)
    ignorar = SALIDA / ".gitignore"
    if not ignorar.exists():
        ignorar.write_text("*\n", encoding="utf-8")
    rutas_out = {
        "planilla": SALIDA / f"planilla_{dia}.xlsx",
        "comparacion": SALIDA / f"comparacion_{dia}.xlsx",
        "verificaciones": SALIDA / f"verificaciones_{dia}.json",
        "detalle": SALIDA / f"detalle_{dia}.csv",
    }
    existentes = [str(r) for r in rutas_out.values() if r.exists()]
    assert not existentes, f"no se sobrescribe: {existentes}"

    config = cargar_configuracion_evaluacion()
    tipos_raros = config.tipos_baja_frecuencia
    params = cargar_configuraciones_seleccionadas(RUTA_HIPERPARAMETROS)["XGBoost"]
    cfg_rec = cargar_configuracion_recomendacion()

    ds = pd.read_parquet(RUTA_DATASET)
    ds["timestamp"] = pd.to_datetime(ds["timestamp"])
    ds["dia_op"] = (ds["timestamp"] - pd.Timedelta(hours=4)).dt.date
    ds["hora"] = ds["timestamp"].dt.strftime("%H:%M")
    assert ds["timestamp"].max() >= corte, f"el dataset no llega a la jornada {dia}"
    hist = ds[ds["timestamp"] < corte].copy()
    objetivo, info_franjas = franjas_objetivo(ds, hist, dia, corte)
    # De la jornada objetivo solo se conservan claves y predictoras; el objetivo se borra.
    for c in ("pasajeros_total", "despachos_count_real", "pasajeros_por_despacho_real", "target"):
        if c in objetivo:
            objetivo[c] = np.nan

    features = seleccionar_features(_preparar_ruta(hist, 1, config.objetivo))
    mr = pd.read_parquet(RUTA_MODEL_READY)
    agg, n_antes, n_desde = agregado_truncado(mr, corte)
    recalculo = variables_recalculadas(objetivo, features, agg, corte, dia)
    rec_mask = objetivo["franja_reconstruida"]
    for col in features:  # solo en franjas sin fila en el dataset, con el tipo del dataset
        objetivo.loc[rec_mask, col] = recalculo.loc[rec_mask, col]
        objetivo[col] = objetivo[col].astype(ds[col].dtype)

    verif = {
        "fecha": str(dia),
        "franjas_objetivo": info_franjas,
        "fuga": verificar_fuga(
            ds,
            objetivo,
            features,
            recalculo,
            n_antes,
            n_desde,
            corte,
            corte - pd.Timedelta(weeks=SEMANAS_REF_LARGA),
            agg,
        ),
    }
    fallos = [k for k, v in verif["fuga"]["variables_iguales_al_recalculo"].items() if not v]
    assert not fallos, (
        f"variables que no coinciden con el recalculo sin datos desde el corte: {fallos}"
    )
    assert verif["fuga"]["objetivos_entrenamiento"]["iguales_al_conjunto_apto_truncado"]

    pred = predecir_objetivo(hist, objetivo, config, params, dia, corte)
    factores, pred_ventana = factor_c3(hist, config, params, tipos_raros, dia)
    pred["regimen"] = np.where(pred["tipo_dia"].isin(tipos_raros), "raro", "ordinario")
    pred["factor"] = pred["route"].map({r: v["factor"] for r, v in factores.items()}).fillna(1.0)
    pred["pred_c3"] = np.where(
        pred["regimen"] == "raro", pred["ref52"], pred["pred_xgboost"] * pred["factor"]
    )
    verif["factor_c3"] = factores

    # Contraste con las salidas del script 43/44 (mismo dataset y protocolo).
    contraste = {}
    if RUTA_43_XGB.exists() and RUTA_44_SERIE.exists():
        p43 = pd.read_csv(RUTA_43_XGB).astype({"route": int, "hora": str})
        p43["dia_op"] = pd.to_datetime(p43["dia_op"]).dt.strftime("%Y-%m-%d")
        u = pred.merge(
            p43[p43["dia_op"] == str(dia)][["route", "hora", "pred_xgboost"]],
            on=["route", "hora"],
            suffixes=("", "_43"),
        )
        v = pred_ventana.merge(
            p43[["route", "dia_op", "hora", "pred_xgboost"]],
            on=["route", "dia_op", "hora"],
            suffixes=("", "_43"),
            how="left",
        )
        s44 = pd.read_csv(RUTA_44_SERIE)
        s44 = s44[(s44["dia_op"] == str(dia)) & (s44["ventana_dias"] == VENTANA_DIAS)].set_index(
            "route"
        )
        contraste = {
            "xgboost_objetivo_franjas_observadas": {
                "franjas": len(u),
                "max_dif": float((u["pred_xgboost"] - u["pred_xgboost_43"]).abs().max()),
            },
            "xgboost_ventana": {
                "franjas": len(v),
                "sin_par": int(v["pred_xgboost_43"].isna().sum()),
                "max_dif": float((v["pred_xgboost"] - v["pred_xgboost_43"]).abs().max()),
            },
            "factor_vs_serie_correccion": {
                str(r): {
                    "script_44": float(s44.loc[r, "factor"]),
                    "dif": abs(factores[r]["factor"] - float(s44.loc[r, "factor"])),
                }
                for r in factores
                if r in s44.index
            },
        }
    verif["contraste_scripts_43_44"] = contraste

    # --- Modulo de recomendacion ---
    raw_freeze = cfg_rec.freeze
    tabla = pd.read_csv(
        PROJECT_ROOT
        / "reports"
        / "tables"
        / "dispatch"
        / f"parametros__recomendacion_despacho__{raw_freeze}.csv"
    )
    man = json.loads(
        (
            PROJECT_ROOT
            / "reports"
            / "tables"
            / "dispatch"
            / f"manifiesto__recomendacion_despacho__{raw_freeze}.json"
        ).read_text(encoding="utf-8")
    )["parametros"]
    parametros = ParametrosCalibracion(
        tabla=tabla,
        capacidad=int(man["capacidad"]),
        jornada_capacidad=date.fromisoformat(man["jornada_capacidad"]),
    )
    base = pred[["route", "dia_op", "hora", "tipo_dia", "regimen"]].assign(
        demanda_predicha=pred["pred_c3"].to_numpy()
    )
    rec, ajuste = generar_recomendacion(
        base,
        parametros,
        cfg_rec.bloques,
        cfg_rec.politica_festivos,
        cfg_rec.usar_tope_carga,
        cfg_rec.servicio_minimo,
    )
    rec["divisor_usado"], rec["criterio"] = divisor_usado(
        rec, cfg_rec.usar_tope_carga, cfg_rec.servicio_minimo
    )
    verif["recomendacion"] = {
        "freeze_parametros": raw_freeze,
        "capacidad": parametros.capacidad,
        "politica_festivos": cfg_rec.politica_festivos,
        "usar_tope_carga": cfg_rec.usar_tope_carga,
        "servicio_minimo": cfg_rec.servicio_minimo,
        "ajuste_factibilidad": ajuste.to_dict("records"),
    }

    # --- Planilla ---
    with pd.ExcelWriter(rutas_out["planilla"], engine="openpyxl") as xw:
        for ruta in (1, 3):
            r = rec[rec["route"] == ruta].sort_values("hora")
            n = r["despachos_recomendados"].to_numpy(dtype=float)
            # Intervalo sugerido: 30 / despachos, redondeo aritmetico (0,5 sube); vacio si 0.
            intervalo = np.where(n > 0, redondeo_aritmetico(30.0 / np.where(n > 0, n, 1.0)), np.nan)
            tabla_r = pd.DataFrame(
                {
                    "Franja": r["hora"],
                    "Pasajeros predichos": r["demanda_predicha"].round(1),
                    "Divisor usado": r["divisor_usado"].round(2),
                    "Criterio del divisor": r["criterio"],
                    "Despachos recomendados": r["despachos_recomendados"],
                    "Intervalo sugerido (min)": pd.array(intervalo, dtype="Int64"),
                    "Régimen": r["regimen"],
                }
            )
            hoja = f"Ruta {ruta}"
            tabla_r.to_excel(xw, sheet_name=hoja, index=False)
            xw.sheets[hoja].cell(row=len(tabla_r) + 3, column=1, value=NOTA_PLANILLA)

    # --- Comparacion con la operacion real (despues de predecir) ---
    td = ds[["FK_RUTA", "timestamp", "tipo_dia"]]
    desp = preparar_despachos(mr, td, cfg_rec.bloques, tipos_raros, cfg_rec.columna_pasajeros)
    reales = franjas_reales(filtrar_periodo(desp[desp["bloque"].notna()], dia, dia))
    # La demanda real del dataset solo entra aqui, despues de recomendar: la funcion de
    # evaluacion la usa para contrastarla con los pasajeros del conjunto apto.
    real_ds = ds[ds["dia_op"] == dia][["FK_RUTA", "hora", "pasajeros_total"]].rename(
        columns={"FK_RUTA": "route", "pasajeros_total": "real"}
    )
    franjas, union = construir_franjas_evaluacion(
        rec.merge(real_ds, on=["route", "hora"], how="left", validate="1:1"), reales
    )
    fuera = reales.merge(
        rec[["route", "dia_op", "hora"]], on=["route", "dia_op", "hora"], how="left", indicator=True
    )
    fuera = fuera[fuera["_merge"] == "left_only"]
    con_fila = franjas["real"].notna() | (franjas["despachos_real"] == 0)
    assert iguales(
        franjas.loc[con_fila, "pasajeros_real"].where(franjas["despachos_real"] > 0),
        franjas.loc[con_fila, "real"],
    ), "pasajeros reales distintos entre conjunto apto y dataset"
    verif["comparacion"] = {
        "union_operacion_real": union,
        "franjas_reales_fuera_de_la_planilla": fuera.drop(columns="_merge").to_dict("records"),
    }

    def clase(s):
        return s.map(CLASE).fillna("sin despachos")

    with pd.ExcelWriter(rutas_out["comparacion"], engine="openpyxl") as xw:
        for ruta in (1, 3):
            f = franjas[franjas["route"] == ruta].sort_values("hora")
            pd.DataFrame(
                {
                    "Franja": f["hora"],
                    "Bloque": f["bloque"],
                    "Despachos recomendados": f["despachos_recomendados"],
                    "Despachos reales": f["despachos_real"],
                    "Pasajeros predichos": f["demanda_predicha"].round(1),
                    "Pasajeros reales": f["pasajeros_real"],
                    "Q1": f["q1"].round(2),
                    "Q3": f["q3"].round(2),
                    "Clase práctica real": clase(f["clase_real"]),
                    "Clase con la recomendación": clase(f["clase_recomendada"]),
                }
            ).to_excel(xw, sheet_name=f"Ruta {ruta}", index=False)

    franjas = franjas.merge(
        pred[["route", "hora", "pred_xgboost", "ref52", "factor", "franja_reconstruida"]],
        on=["route", "hora"],
        validate="1:1",
    )
    franjas.to_csv(rutas_out["detalle"], index=False)

    resumen = []
    for ruta, f in franjas.groupby("route"):
        resumen.append(
            {
                "route": int(ruta),
                "franjas": len(f),
                "franjas_con_despachos_reales": int((f["despachos_real"] > 0).sum()),
                "despachos_recomendados": int(f["despachos_recomendados"].sum()),
                "despachos_reales": int(f["despachos_real"].sum()),
                "pasajeros_predichos": float(f["demanda_predicha"].sum()),
                "pasajeros_reales": float(f["pasajeros_real"].sum()),
                "factor": factores[int(ruta)]["factor"],
                "clase_real": clase(f.loc[f["despachos_real"] > 0, "clase_real"])
                .value_counts()
                .to_dict(),
                "clase_recomendada": clase(f.loc[f["despachos_real"] > 0, "clase_recomendada"])
                .value_counts()
                .to_dict(),
            }
        )
    verif["resumen"] = resumen
    f = franjas.assign(
        dif_despachos=franjas["despachos_recomendados"] - franjas["despachos_real"],
        dif_pasajeros=franjas["demanda_predicha"] - franjas["pasajeros_real"],
    )
    verif["mayores_diferencias"] = {
        "despachos": f.reindex(f["dif_despachos"].abs().sort_values(ascending=False).index)
        .head(8)[["route", "hora", "despachos_recomendados", "despachos_real", "dif_despachos"]]
        .to_dict("records"),
        "pasajeros": f.reindex(f["dif_pasajeros"].abs().sort_values(ascending=False).index)
        .head(8)[["route", "hora", "demanda_predicha", "pasajeros_real", "dif_pasajeros"]]
        .round(1)
        .to_dict("records"),
    }
    verif["entradas"] = {
        "dataset": {
            "ruta": str(RUTA_DATASET.relative_to(PROJECT_ROOT).as_posix()),
            "sha256": sha256(RUTA_DATASET),
        },
        "model_ready": {
            "ruta": str(RUTA_MODEL_READY.relative_to(PROJECT_ROOT).as_posix()),
            "sha256": sha256(RUTA_MODEL_READY),
        },
        "hiperparametros_xgboost": params,
    }
    verif["generado"] = datetime.now().isoformat(timespec="seconds")
    rutas_out["verificaciones"].write_text(
        json.dumps(verif, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "fecha": str(dia),
                "franjas_objetivo": info_franjas,
                "resumen": resumen,
                "contraste": contraste,
            },
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
