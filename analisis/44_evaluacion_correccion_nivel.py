"""Correccion de nivel del predictor mixto: candidatos, seleccion y confirmacion.

Implementa las secciones 1 a 9 de docs/preregistro_correccion_nivel.md sobre las
predicciones continuas del script 43:
  - soporte: jornadas de ruta predichas por XGBoost y por Prophet;
  - correccion multiplicativa y aditiva de XGBoost en regimen ordinario con las
    franjas ordinarias de los ultimos 7, 14 y 28 dias cerrados, por ruta;
  - nueve candidatos, con la referencia de 52 s en regimen raro;
  - metricas (MAE, MedAE, RMSE, WAPE, sesgo) por periodo, globales, por ruta y
    por regimen; seleccion en validacion, confirmacion en evaluacion y
    exploracion en la extension;
  - Tabla 2 del modulo de recomendacion sin tope para el candidato 1 y el
    elegido, a escala de franja y de bloque, en los tres periodos;
  - salidas descriptivas: serie diaria de la correccion, su resumen por periodo
    y la figura del factor de 14 dias con la demanda media diaria.

No modifica ningun archivo existente; salidas nuevas en analisis/salidas/ con el
sufijo de configs/modeling/correccion_nivel_20251127_20261003.yaml.

Uso:
    python analisis/44_evaluacion_correccion_nivel.py
"""

import importlib.util
import json
from datetime import date, datetime, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.dates import DateFormatter, MonthLocator

from proyecto_grado.dispatch.config import cargar_configuracion_recomendacion
from proyecto_grado.dispatch.evaluacion import (
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

RUTA_CONFIG = PROJECT_ROOT / "configs" / "modeling" / "correccion_nivel_20251127_20261003.yaml"
CLAVES = ["route", "dia_op", "hora"]
PERIODOS = ("validacion", "evaluacion", "extension")

# Tabla 2 a escala de bloque y proporciones: mismas funciones del script 42.
_spec = importlib.util.spec_from_file_location("evaluacion_extension", PROJECT_ROOT / "analisis" / "42_evaluacion_extension.py")
_e42 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_e42)


def nombres_candidatos(ventanas):
    c = {1: "C1 Mixto sin correccion"}
    for i, k in enumerate(ventanas):
        c[2 + i] = f"C{2 + i} Mixto multiplicativo {k}d"
        c[2 + len(ventanas) + i] = f"C{2 + len(ventanas) + i} Mixto aditivo {k}d"
    n = 2 + 2 * len(ventanas)
    c[n] = f"C{n} Prophet ordinario"
    c[n + 1] = f"C{n + 1} Promedio XGBoost-Prophet ordinario"
    return dict(sorted(c.items()))


# --------------------------------------------------------------- observaciones


def cargar(salida, sufijo, tipos_raros):
    def leer(nombre):
        d = pd.read_csv(salida / f"{nombre}__{sufijo}.csv")
        d["route"] = d["route"].astype(int)
        d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.strftime("%Y-%m-%d")
        d["hora"] = d["hora"].astype(str)
        return d

    xgb, pro, r52 = leer("predicciones__xgboost"), leer("predicciones__prophet"), leer("referencia_52s")
    jx, jp = (set(zip(d["route"], d["dia_op"], strict=False)) for d in (xgb, pro))
    comun = pd.DataFrame(sorted(jx & jp), columns=["route", "dia_op"])
    obs = (xgb[[*CLAVES, "tipo_dia", "real", "pred_xgboost", "pred_media"]]
           .rename(columns={"pred_media": "ref26"})
           .merge(comun, on=["route", "dia_op"]))
    n = len(obs)
    p = pro[[*CLAVES, "real", "pred_prophet"]].merge(comun, on=["route", "dia_op"])
    assert len(p) == n, "XGBoost y Prophet no tienen las mismas franjas en el soporte"
    obs = obs.merge(p, on=CLAVES, suffixes=("", "_p"), validate="1:1")
    assert len(obs) == n and np.allclose(obs.pop("real_p"), obs["real"])
    obs = obs.merge(r52[[*CLAVES, "pred_media_52s"]].rename(columns={"pred_media_52s": "ref52"}),
                    on=CLAVES, how="left", validate="1:1")
    assert obs["ref52"].notna().all()
    obs["regimen"] = np.where(obs["tipo_dia"].isin(tipos_raros), "raro", "ordinario")
    soporte = {"jornadas_xgboost": len(jx), "jornadas_prophet": len(jp), "jornadas_comunes": len(comun),
               "solo_xgboost": sorted(map(list, jx - jp)), "solo_prophet": sorted(map(list, jp - jx))}
    return obs.sort_values(CLAVES).reset_index(drop=True), soporte


# ----------------------------------------------------------------- correccion


def serie_correccion(obs, ventanas):
    """Factor y termino aditivo por ruta, jornada del soporte y ventana, con las
    franjas ordinarias del soporte de las jornadas [d - k, d - 1]."""
    ordi = obs[obs["regimen"] == "ordinario"].assign(err=lambda x: x["pred_xgboost"] - x["real"])
    diario = (ordi.groupby(["route", "dia_op"])
              .agg(s_real=("real", "sum"), s_pred=("pred_xgboost", "sum"), s_err=("err", "sum"), n=("err", "size"))
              .reset_index())
    diario["fecha"] = pd.to_datetime(diario["dia_op"]).dt.date
    jornadas = obs[["route", "dia_op", "regimen"]].drop_duplicates(["route", "dia_op"])
    filas = []
    for (ruta, dia_op, regimen) in jornadas.itertuples(index=False):
        d = date.fromisoformat(dia_op)
        g = diario[diario["route"] == ruta]
        for k in ventanas:
            w = g[(g["fecha"] >= d - timedelta(days=k)) & (g["fecha"] <= d - timedelta(days=1))]
            assert (w["fecha"] < d).all()  # causalidad (seccion 7)
            n, s_real, s_pred, s_err = int(w["n"].sum()), w["s_real"].sum(), w["s_pred"].sum(), w["s_err"].sum()
            factor = s_real / s_pred if n > 0 and s_pred > 0 else np.nan
            aditivo = s_err / n if n > 0 else np.nan
            filas.append({"route": ruta, "dia_op": dia_op, "regimen": regimen, "ventana_dias": k,
                          "jornadas_ventana": len(w), "franjas_ventana": n,
                          "factor": factor, "aditivo": aditivo,
                          "aplica_multiplicativa": bool(np.isfinite(factor)),
                          "aplica_aditiva": bool(np.isfinite(aditivo)),
                          "max_dia_ventana": str(w["fecha"].max()) if len(w) else None})
    return pd.DataFrame(filas)


def candidatos(obs, serie, ventanas, nombres):
    raro = obs["regimen"] == "raro"
    xgb = obs["pred_xgboost"]
    cols = {nombres[1]: xgb}
    for i, k in enumerate(ventanas):
        s = serie[serie["ventana_dias"] == k][["route", "dia_op", "factor", "aditivo"]]
        m = obs[["route", "dia_op"]].merge(s, on=["route", "dia_op"], how="left", validate="m:1")
        assert len(m) == len(obs)
        cols[nombres[2 + i]] = xgb * m["factor"].fillna(1.0).to_numpy()
        cols[nombres[2 + len(ventanas) + i]] = xgb - m["aditivo"].fillna(0.0).to_numpy()
    n = 2 + 2 * len(ventanas)
    cols[nombres[n]] = obs["pred_prophet"]
    cols[nombres[n + 1]] = (obs["pred_xgboost"] + obs["pred_prophet"]) / 2
    for nombre, ordinario in cols.items():
        obs[nombre] = obs["ref52"].where(raro, ordinario)
    return obs


# ------------------------------------------------------------------- metricas


def periodo_de(dia_op, periodos):
    f = pd.to_datetime(dia_op)
    out = pd.Series(pd.NA, index=dia_op.index, dtype="object")
    for p, (ini, fin) in periodos.items():
        out[(f >= ini) & (f <= fin)] = p
    return out


def tabla_metricas(obs, nombres):
    filas = []
    for periodo, gp in obs.groupby("periodo"):
        cortes = {"global": [("todos", gp)], "por_ruta": [(str(k), g) for k, g in gp.groupby("route")],
                  "por_regimen": list(gp.groupby("regimen"))}
        for corte, grupos in cortes.items():
            for celda, g in grupos:
                for c in nombres.values():
                    filas.append({"periodo": periodo, "corte": corte, "celda": celda, "candidato": c,
                                  "n_jornadas": int(g[["route", "dia_op"]].drop_duplicates().shape[0]),
                                  "n_franjas": len(g), "demanda_media": g["real"].mean(),
                                  **_e42.metricas(g["real"].to_numpy(float), g[c].to_numpy(float))})
    return pd.DataFrame(filas)


def seleccionar(t, nombres, umbral):
    g = t[(t["periodo"] == "validacion") & (t["corte"] == "global")].set_index("candidato")
    m = g["mae"].min()
    finalistas = [c for c in nombres.values() if g.loc[c, "mae"] < (1 + umbral) * m]
    # Desempate: menor |sesgo|; empate exacto, menor numero (orden de `nombres`).
    elegido = min(finalistas, key=lambda c: (abs(g.loc[c, "sesgo"]), list(nombres.values()).index(c)))
    return {"mae_minimo": m, "limite_finalistas": (1 + umbral) * m,
            "finalistas": {c: {"mae": g.loc[c, "mae"], "sesgo": g.loc[c, "sesgo"]} for c in finalistas},
            "elegido": elegido}


def confirmar(t, elegido, c1):
    g = t[(t["periodo"] == "evaluacion") & (t["corte"] == "global")].set_index("candidato")
    if elegido == c1:
        return {"resultado": "no aplica (el elegido es el candidato 1)"}
    mae_ok = g.loc[elegido, "mae"] <= g.loc[c1, "mae"]
    sesgo_ok = abs(g.loc[elegido, "sesgo"]) < abs(g.loc[c1, "sesgo"])
    return {"elegido": {"mae": g.loc[elegido, "mae"], "sesgo": g.loc[elegido, "sesgo"]},
            "candidato_1": {"mae": g.loc[c1, "mae"], "sesgo": g.loc[c1, "sesgo"]},
            "mae_no_mayor": bool(mae_ok), "abs_sesgo_menor": bool(sesgo_ok),
            "resultado": "confirmado" if mae_ok and sesgo_ok else "no confirmado"}


# ----------------------------------------------------------- recomendacion


def recomendacion(raw, obs, variantes, tipos_raros, periodos):
    cfg_rec = cargar_configuracion_recomendacion()
    rec_raw = raw["recomendacion"]
    tope = bool(rec_raw["usar_tope"])
    tabla = pd.read_csv(PROJECT_ROOT / rec_raw["parametros"])
    man = json.loads((PROJECT_ROOT / rec_raw["manifiesto"]).read_text(encoding="utf-8"))["parametros"]
    parametros = ParametrosCalibracion(tabla=tabla, capacidad=int(man["capacidad"]),
                                       jornada_capacidad=date.fromisoformat(man["jornada_capacidad"]))
    mr = pd.read_parquet(PROJECT_ROOT / rec_raw["model_ready"],
                         columns=["FK_RUTA", "HORA_INICIAL_REAL", cfg_rec.columna_pasajeros, "MODEL_READY_OK"])
    td = pd.read_parquet(PROJECT_ROOT / raw["dataset"], columns=["FK_RUTA", "timestamp", "tipo_dia"])
    desp = preparar_despachos(mr, td, cfg_rec.bloques, tipos_raros, cfg_rec.columna_pasajeros)
    orden = list(cfg_rec.nombres_bloques)

    clasif, prop, ajustes, ctx = [], [], [], {}
    for periodo, (ini, fin) in periodos.items():
        ini, fin = ini.date(), fin.date()
        en_periodo = (desp["dia_op"] >= ini) & (desp["dia_op"] <= fin)
        fuera = desp[en_periodo & desp["bloque"].isna()]
        reales = franjas_reales(filtrar_periodo(desp[desp["bloque"].notna()], ini, fin))
        o = obs[obs["periodo"] == periodo]
        base = o[[*CLAVES, "tipo_dia", "regimen", "real"]]
        ctx[periodo] = {"despachos_fuera_de_bloque_excluidos": len(fuera), "union_operacion_real": {}}
        for variante in variantes:
            rec, ajuste = generar_recomendacion(base.assign(demanda_predicha=o[variante].to_numpy()), parametros,
                                                cfg_rec.bloques, cfg_rec.politica_festivos, tope,
                                                cfg_rec.servicio_minimo)
            franjas, v = construir_franjas_evaluacion(rec, reales)
            ctx[periodo]["union_operacion_real"][variante] = v
            ajustes.append({"periodo": periodo, "usar_tope": tope, "variante": variante, "jornadas": len(ajuste),
                            "jornadas_ajustadas": int(ajuste["ajustada"].sum()),
                            "despachos_retirados": int(ajuste["retirados"].sum()),
                            "jornadas_no_factibles": int((~ajuste["factible"]).sum())})
            for escala, unidades in (("franja", franjas), ("bloque", _e42.a_bloques(franjas))):
                resumen, _ = tabla_clasificacion(unidades, orden)
                clasif.append(resumen.assign(periodo=periodo, usar_tope=tope, variante=variante, escala=escala))
                prop += [{"periodo": periodo, **f} for f in _e42.proporciones(unidades, variante, escala, tope)]
    ctx.update({"capacidad": parametros.capacidad, "politica_festivos": cfg_rec.politica_festivos,
                "servicio_minimo": cfg_rec.servicio_minimo, "usar_tope": tope})
    return pd.concat(clasif, ignore_index=True), pd.DataFrame(prop), pd.DataFrame(ajustes), ctx


# ------------------------------------------------------------- descriptivos


def resumen_serie(serie):
    filas = []
    for (periodo, ruta, k), g in serie.dropna(subset=["periodo"]).groupby(["periodo", "route", "ventana_dias"]):
        fila = {"periodo": periodo, "route": ruta, "ventana_dias": k, "jornadas": len(g)}
        for col in ("factor", "aditivo"):
            v = g[col].dropna()
            fila.update({f"{col}_n": len(v), f"{col}_min": v.min(), f"{col}_mediana": v.median(),
                         f"{col}_max": v.max()})
        filas.append(fila)
    return pd.DataFrame(filas)


def figura(obs, serie, periodos, ruta_png):
    """Factor de 14 dias (arriba) y demanda media diaria (abajo), una columna por
    ruta, eje temporal compartido; sin doble eje ni titulo incrustado."""
    tinta, tinta_2, rejilla = "#0b0b0b", "#52514e", "#e4e3df"
    color_ruta = {1: "#2a78d6", 3: "#eb6834"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": tinta_2,
                         "axes.labelcolor": tinta, "axes.spines.top": False, "axes.spines.right": False,
                         "xtick.color": tinta_2, "ytick.color": tinta_2, "text.color": tinta,
                         "savefig.facecolor": "white"})
    ini = periodos["validacion"][0]
    demanda = (obs[obs["periodo"].notna()].groupby(["route", "dia_op"])["real"].mean().reset_index())
    s14 = serie[(serie["ventana_dias"] == 14) & serie["periodo"].notna()]
    fig, ejes = plt.subplots(2, 2, figsize=(12, 6.5), sharex=True, sharey="row")
    for j, ruta in enumerate((1, 3)):
        sf = s14[s14["route"] == ruta]
        sd = demanda[demanda["route"] == ruta]
        for i, (x, y, etiqueta) in enumerate((
                (sf["dia_op"], sf["factor"], "Factor multiplicativo (14 días)"),
                (sd["dia_op"], sd["real"], "Demanda media diaria\n(pasajeros por franja)"))):
            ax = ejes[i, j]
            ax.plot(pd.to_datetime(x), y, color=color_ruta[ruta], linewidth=1.6, marker="o", markersize=2.5)
            ax.grid(True, axis="y", color=rejilla, linewidth=0.8, zorder=0)
            for p in ("evaluacion", "extension"):
                ax.axvline(periodos[p][0], color=tinta_2, linewidth=0.9, linestyle="--", zorder=1)
            if i == 0:
                ax.axhline(1.0, color=tinta_2, linewidth=0.9, zorder=1)
                ax.set_title(f"Ruta {ruta}", fontsize=11, loc="left", color=tinta)
                for p, nombre in (("validacion", "Validación"), ("evaluacion", "Evaluación"),
                                  ("extension", "Extensión")):
                    medio = periodos[p][0] + (periodos[p][1] - periodos[p][0]) / 2
                    ax.text(medio, 1.0, nombre, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                            fontsize=8.5, color=tinta_2)
            if j == 0:
                ax.set_ylabel(etiqueta)
            ax.xaxis.set_major_locator(MonthLocator())
            ax.xaxis.set_major_formatter(DateFormatter("%b\n%Y"))
    ejes[0, 0].set_xlim(ini - pd.Timedelta(days=3), periodos["extension"][1] + pd.Timedelta(days=3))
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------- main


def main():
    raw = yaml.safe_load(RUTA_CONFIG.read_text(encoding="utf-8"))
    sufijo = raw["sufijo"]
    salida = PROJECT_ROOT / raw["salidas"]["directorio"]
    tipos_raros = cargar_configuracion_evaluacion().tipos_baja_frecuencia
    ventanas = list(raw["correccion"]["ventanas_dias"])
    nombres = nombres_candidatos(ventanas)
    periodos = {p: (pd.Timestamp(str(raw["periodos"][p]["inicio"])), pd.Timestamp(str(raw["periodos"][p]["fin"])))
                for p in PERIODOS}
    rutas_salida = {n: salida / f"{n}__{sufijo}.{e}" for n, e in (
        ("observaciones", "csv"), ("metricas", "csv"), ("seleccion", "json"), ("conteos", "csv"),
        ("serie_correccion", "csv"), ("resumen_serie_correccion", "csv"), ("figura_factor_14d", "png"),
        ("clasificacion_recomendacion", "csv"), ("proporciones_recomendacion", "csv"),
        ("ajuste_factibilidad", "csv"), ("manifiesto", "json"))}
    existentes = [str(r) for r in rutas_salida.values() if r.exists()]
    assert not existentes, f"no se sobrescriben salidas: {existentes}"
    man43 = json.loads((salida / f"manifiesto__predicciones__{sufijo}.json").read_text(encoding="utf-8"))
    assert "controles" in man43, "el script 43 no completo sus controles"

    obs, soporte = cargar(salida, sufijo, tipos_raros)
    obs["periodo"] = periodo_de(obs["dia_op"], periodos)
    serie = serie_correccion(obs, ventanas)
    serie["periodo"] = periodo_de(serie["dia_op"], periodos)
    obs = candidatos(obs, serie, ventanas, nombres)
    for k in ventanas:  # banderas de aplicacion por ventana para los conteos
        s = serie[serie["ventana_dias"] == k][["route", "dia_op", "aplica_multiplicativa", "aplica_aditiva"]]
        obs = obs.merge(s.rename(columns={"aplica_multiplicativa": f"aplica_mult_{k}",
                                          "aplica_aditiva": f"aplica_adit_{k}"}), on=["route", "dia_op"])

    # Control (seccion 7): el candidato 1 reproduce el predictor mixto del script 42.
    tol = float(raw["controles"]["tolerancia"])
    prev = pd.read_csv(salida / f"observaciones__{raw['controles']['sufijo_extension']}.csv")
    prev = prev.astype({"route": int, "dia_op": str, "hora": str})
    prev["dia_op"] = pd.to_datetime(prev["dia_op"]).dt.strftime("%Y-%m-%d")
    u = prev[[*CLAVES, _e42.MIXTO]].merge(obs[[*CLAVES, nombres[1]]], on=CLAVES, how="left")
    control_c1 = {"franjas_previo": len(u), "sin_par": int(u[nombres[1]].isna().sum()),
                  "max_dif": float((u[nombres[1]] - u[_e42.MIXTO]).abs().max())}
    assert control_c1["sin_par"] == 0 and control_c1["max_dif"] < tol, f"control del candidato 1: {control_c1}"

    evaluadas = obs[obs["periodo"].notna()].copy()
    t = tabla_metricas(evaluadas, nombres)
    sel = seleccionar(t, nombres, float(raw["seleccion"]["umbral_relativo_mae"]))
    conf = confirmar(t, sel["elegido"], nombres[1])

    filas_conteo = []
    jor = evaluadas.drop_duplicates(["route", "dia_op"])
    jor_ord = jor[jor["regimen"] == "ordinario"]
    for periodo in PERIODOS:
        gp = evaluadas[evaluadas["periodo"] == periodo]
        jp = jor_ord[jor_ord["periodo"] == periodo]
        for num, c in nombres.items():
            fila = {"periodo": periodo, "candidato": c, "franjas_negativas": int((gp[c] < 0).sum()),
                    "jornadas_ordinarias": len(jp), "jornadas_sin_correccion": pd.NA}
            if 2 <= num <= 1 + len(ventanas):
                fila["jornadas_sin_correccion"] = int((~jp[f"aplica_mult_{ventanas[num - 2]}"]).sum())
            elif 2 + len(ventanas) <= num <= 1 + 2 * len(ventanas):
                fila["jornadas_sin_correccion"] = int((~jp[f"aplica_adit_{ventanas[num - 2 - len(ventanas)]}"]).sum())
            filas_conteo.append(fila)
    cont = pd.DataFrame(filas_conteo)

    variantes = list(dict.fromkeys([nombres[1], sel["elegido"]]))
    clasif, prop, ajustes, ctx = recomendacion(raw, evaluadas, variantes, tipos_raros, periodos)

    figura(obs, serie, periodos, rutas_salida["figura_factor_14d"])
    evaluadas.drop(columns=[c for c in evaluadas if c.startswith("aplica_")]).to_csv(
        rutas_salida["observaciones"], index=False)
    t.to_csv(rutas_salida["metricas"], index=False)
    cont.to_csv(rutas_salida["conteos"], index=False)
    serie.to_csv(rutas_salida["serie_correccion"], index=False)
    resumen_serie(serie).to_csv(rutas_salida["resumen_serie_correccion"], index=False)
    clasif.to_csv(rutas_salida["clasificacion_recomendacion"], index=False)
    prop.to_csv(rutas_salida["proporciones_recomendacion"], index=False)
    ajustes.to_csv(rutas_salida["ajuste_factibilidad"], index=False)
    decision = {"candidatos": nombres, "seleccion": sel, "confirmacion": conf}
    rutas_salida["seleccion"].write_text(json.dumps(decision, ensure_ascii=False, indent=2, default=str),
                                         encoding="utf-8")
    manifiesto = {
        "script": "analisis/44_evaluacion_correccion_nivel.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "configuracion": str(RUTA_CONFIG.relative_to(PROJECT_ROOT).as_posix()),
        "preregistro": raw["preregistro"], "sufijo": sufijo,
        "soporte": {**soporte, "franjas": len(obs), "jornadas_evaluadas": int(jor.shape[0]),
                    "por_periodo": {p: {"jornadas": int((jor["periodo"] == p).sum()),
                                        "franjas": int((evaluadas["periodo"] == p).sum()),
                                        "jornadas_raras": int(((jor["periodo"] == p) & (jor["regimen"] == "raro")).sum())}
                                    for p in PERIODOS}},
        "controles": {"predicciones_script_43": man43["controles"], "candidato_1_vs_mixto_script_42": control_c1,
                      "causalidad": "verificada por asercion en cada ventana"},
        "recomendacion": ctx,
        "salidas": [str(r.relative_to(PROJECT_ROOT).as_posix()) for r in rutas_salida.values()],
    }
    rutas_salida["manifiesto"].write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str),
                                          encoding="utf-8")
    print(json.dumps({"soporte": manifiesto["soporte"]["por_periodo"], **decision}, ensure_ascii=False,
                     indent=1, default=str))
    g = t[t["corte"] == "global"].pivot_table(index="candidato", columns="periodo", values=["mae", "sesgo"])
    print(g.round(2).to_string())


if __name__ == "__main__":
    main()
