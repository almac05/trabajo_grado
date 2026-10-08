"""Analisis de las planillas de muestra del 2026-09-21 al 2026-10-03.

Lee los detalles por franja que deja scripts/muestra_planilla_20261001.py
(data/muestra_planilla/detalle_<fecha>.csv) y calcula, sin modificar ninguna
configuracion:

1. Por jornada y ruta: pasajeros y despachos predichos/recomendados y reales, y la
   descomposicion de la diferencia de despachos (recomendados - reales):
     - tope de carga: recomendados con la configuracion actual menos los
       recomendados sin tope, en todas las franjas;
     - servicio minimo en franjas sin despachos reales: en esas franjas, los
       recomendados sin tope menos los que daria la misma regla sin servicio
       minimo (minimo 0);
     - resto (divisor y redondeo): la diferencia restante.
2. Divisor por ruta y bloque (mediana y Q3 calibrados, y cuantas franjas uso
   cada criterio) frente al promedio y la mediana de pasajeros por despacho
   observados en las 13 jornadas (regimen ordinario, por despacho, la misma
   unidad de la calibracion).
3. Franjas desde las 16:00: porcentaje de jornadas con al menos un despacho, por
   ruta y tipo de dia, en las 8 semanas anteriores al 2026-09-21.
4. Variantes del modulo sobre la misma demanda predicha:
     A. configuracion actual (con tope de carga);
     B. sin tope;
     C. A, con servicio minimo solo en franjas con servicio en al menos el 50 %
        de las jornadas del mismo tipo de dia en las 8 semanas previas a cada
        jornada;
     D. B con la regla de C.
   Totales recomendados frente a reales y porcentaje de franjas baja, normal y
   alta (franja de 30 min y hora), sobre las unidades con despachos reales.
5. Variantes de oferta, todas sin tope de carga:
     E. disponibilidad habitual: 0 despachos en las franjas con servicio en menos
        del 50 % (sensibilidad: 30 % y 70 %) de las jornadas del mismo tipo de
        dia en las 8 semanas previas; en las demas, la regla sin tope con minimo 1;
     G. (sensibilidad) E50 con un limite diario por ruta: la mediana de despachos
        reales de las 4 jornadas previas del mismo tipo de dia. El exceso se
        retira con reglas.aplicar_factibilidad (por ruta y jornada).
   Totales dentro y fuera de la disponibilidad, franjas con despachos reales
   fuera de ella, clases con esas franjas incluidas o excluidas, y lo mismo solo
   para jornadas LABORAL; vehiculos distintos por jornada y ruta en las 8 semanas
   previas; y oferta en patio para E50 con la definicion del analisis 28
   (analisis/28_disponibilidad_patio_intervalos_largos.py).

Salidas en data/muestra_planilla/analisis_*.csv.

Uso:
    python scripts/analisis_muestras_planilla.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from proyecto_grado.analytics.fleet_availability import FleetAvailabilityAnalyzer
from proyecto_grado.dispatch.config import cargar_configuracion_recomendacion
from proyecto_grado.dispatch.evaluacion import clasificar
from proyecto_grado.dispatch.parametros import REGIMEN_RARO, preparar_despachos
from proyecto_grado.dispatch.reglas import aplicar_factibilidad, despachos_ordinario, despachos_raro
from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion

FECHAS = [date(2026, 9, 21) + timedelta(days=i) for i in range(13)]
ACT = PROJECT_ROOT / "data" / "actualizacion_20261004"
RUTA_DATASET = (
    ACT / "processed" / "modeling" / "modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
)
RUTA_MODEL_READY = (
    ACT / "processed" / "model_ready" / "despachos_model_ready_freeze_20261005_011520.parquet"
)
SALIDA = PROJECT_ROOT / "data" / "muestra_planilla"
SEMANAS_SERVICIO = 8
UMBRAL_SERVICIO = 0.5
CLASE = {"subutilizada": "baja", "normal": "normal", "sobrecargada": "alta"}
UMBRALES_E = (0.3, 0.5, 0.7)
JORNADAS_LIMITE = 4


def despachos(f, usar_tope, minimo):
    """Regla del modulo (reglas.despachos_ordinario / despachos_raro) con un
    servicio minimo por franja: `minimo` es un arreglo de 0 y 1."""
    raro = (f["regimen"] == REGIMEN_RARO).to_numpy()
    out = {}
    for m in (0, 1):
        o = despachos_ordinario(
            f["demanda_predicha"], f["mediana_ordinaria"], f["q3_ordinario"], usar_tope, m
        )
        r = despachos_raro(f["demanda_predicha"], f["divisor"], m)
        out[m] = np.where(raro, r, o)
    return np.where(np.asarray(minimo) == 1, out[1], out[0]).astype(int)


def servicio_previo(ds, f):
    """Fraccion de jornadas del mismo tipo de dia, en las 8 semanas previas a cada
    jornada, en que la franja tuvo al menos un despacho."""
    ds = ds.copy()
    ds["con_servicio"] = ds["despachos_count_real"].fillna(0) > 0
    out = []
    for (ruta, dia_op, tipo), g in f.groupby(["route", "dia_op", "tipo_dia"]):
        d = date.fromisoformat(dia_op)
        ini = d - timedelta(weeks=SEMANAS_SERVICIO)
        h = ds[
            (ds["FK_RUTA"] == ruta)
            & (ds["tipo_dia"] == tipo)
            & (ds["dia_op"] >= ini)
            & (ds["dia_op"] < d)
        ]
        jornadas = h["dia_op"].nunique()
        frac = h.groupby("hora")["con_servicio"].sum() / jornadas
        out.append(
            g[["route", "dia_op", "hora"]].assign(
                jornadas_previas=jornadas, frac_servicio=g["hora"].map(frac).fillna(0.0).to_numpy()
            )
        )
    return pd.concat(out, ignore_index=True)


def clases(unidades, col_desp):
    ppd = unidades["pasajeros_real"] / unidades[col_desp]
    return clasificar(ppd, unidades["q1"], unidades["q3"]).map(CLASE)


def porcentajes(unidades, col_desp):
    con = unidades[unidades["despachos_real"] > 0]
    c = clases(con, col_desp)
    return {
        "unidades": len(con),
        **{f"pct_{k}": 100 * (c == k).mean() for k in ("baja", "normal", "alta")},
    }


def por_hora(f, cols):
    f = f.assign(hora_reloj=f["hora"].str.slice(0, 2))
    g = f.groupby(["route", "dia_op", "hora_reloj"])
    h = g.agg(
        **{c: (c, "sum") for c in ["pasajeros_real", "despachos_real", *cols]},
        q1=("q1", "first"),
        q3=("q3", "first"),
        n_q=("q3", "nunique"),
    ).reset_index()
    assert (h["n_q"] == 1).all(), "una hora con dos juegos de cuantiles"
    return h


# ------------------------------------------------- variantes de oferta (E, G)


def limite_oferta(ds, f):
    """Mediana de despachos reales de las ultimas 4 jornadas del mismo tipo de dia
    anteriores al corte, por ruta (franjas del horario operativo del dataset)."""
    diario = (
        ds.assign(n=ds["despachos_count_real"].fillna(0))
        .groupby(["FK_RUTA", "dia_op", "tipo_dia"])["n"]
        .sum()
        .reset_index()
    )
    filas = []
    for (ruta, dia_op, tipo), _ in f.groupby(["route", "dia_op", "tipo_dia"]):
        d = date.fromisoformat(dia_op)
        prev = diario[
            (diario["FK_RUTA"] == ruta) & (diario["tipo_dia"] == tipo) & (diario["dia_op"] < d)
        ]
        prev = prev.sort_values("dia_op").tail(JORNADAS_LIMITE)
        filas.append(
            {
                "route": ruta,
                "dia_op": dia_op,
                "tipo_dia": tipo,
                "jornadas_previas": ", ".join(str(x) for x in prev["dia_op"]),
                "despachos_previos": ", ".join(str(int(x)) for x in prev["n"]),
                "limite": float(prev["n"].median()),
            }
        )
    return pd.DataFrame(filas)


def variante_g(f, col_e, limites):
    """E con un limite diario por ruta, reutilizando reglas.aplicar_factibilidad:
    retira un despacho a la vez de la franja cuya carga predicha por despacho
    resultante es menor, sin bajar de 1 en las franjas dentro de la disponibilidad
    (las de fuera ya tienen 0 y no entran al ajuste)."""
    g = f[col_e].to_numpy().copy()
    resumen = []
    for (ruta, dia_op), sub in f.groupby(["route", "dia_op"]):
        lim = limites.loc[
            (limites["route"] == ruta) & (limites["dia_op"] == dia_op), "limite"
        ].iloc[0]
        cap = int(np.floor(lim))
        dentro = sub[sub[col_e] >= 1]
        ajust, jornada = aplicar_factibilidad(
            dentro.assign(dia_op=f"{dia_op}|{ruta}"),
            cap,
            1,
            columna_demanda="demanda_predicha",
            columna_despachos=col_e,
        )
        pos = dict(zip(dentro["hora"], dentro.index, strict=True))
        for _, r in ajust.iterrows():
            g[pos[r["hora"]]] = r["despachos_recomendados"]
        j = jornada.iloc[0]
        resumen.append(
            {
                "route": ruta,
                "dia_op": dia_op,
                "limite": lim,
                "limite_entero": cap,
                "E": int(sub[col_e].sum()),
                "G": int(j["total_recomendado"]),
                "retirados": int(j["retirados"]),
                "limite_alcanzado": bool(j["factible"]),
            }
        )
    return g, pd.DataFrame(resumen)


def porcentajes_version(unidades, col_desp, fuera_col):
    """Porcentajes sobre unidades con despachos reales: incluidas (las de fuera de
    la disponibilidad se clasifican con la recomendacion; si es 0, alta) y
    excluidas (se quitan las unidades con despachos reales fuera)."""
    con = unidades[unidades["despachos_real"] > 0]
    out = {}
    for version, u in (("incluidas", con), ("excluidas", con[~con[fuera_col]])):
        c = clases(u, col_desp)
        out[version] = {
            "unidades": len(u),
            **{f"pct_{k}": 100 * (c == k).mean() for k in ("baja", "normal", "alta")},
        }
    out["fuera_con_reales"] = int(con[fuera_col].sum())
    return out


def patio(f, col, cfg_rec):
    """Punto 5: oferta en patio con la definicion del analisis 28
    (FleetAvailabilityAnalyzer._reconstruir_timeline, sin modificar)."""
    mr = pd.read_parquet(
        RUTA_MODEL_READY,
        columns=[
            "PLACA",
            "FK_RUTA",
            "FECHA_INICIAL",
            "HORA_INICIAL_REAL",
            "HORA_FIN_FINAL",
            "MODEL_READY_OK",
        ],
    )
    mr = mr[mr["FK_RUTA"].isin([1, 3])]
    an = FleetAvailabilityAnalyzer(mr)
    filas = []
    for dia_op, g in f.groupby("dia_op"):
        d = date.fromisoformat(dia_op)
        tl = an._reconstruir_timeline(an._df[an._df["fecha_dia"] == d].copy())
        en_patio = tl[tl["estado"] == "EN_PATIO"]
        ini, fin = en_patio["inicio"].to_numpy(), en_patio["fin"].to_numpy()
        for _, r in g.iterrows():
            t0 = pd.Timestamp(f"{dia_op} {r['hora']}").to_datetime64()
            t1 = t0 + np.timedelta64(30, "m")
            filas.append(
                {
                    "route": r["route"],
                    "dia_op": dia_op,
                    "hora": r["hora"],
                    "tipo_dia": r["tipo_dia"],
                    "bloque": r["bloque"],
                    "recomendados": int(r[col]),
                    "reales": int(r["despachos_real"]),
                    "vehiculos_patio_en_la_franja": int(((ini < t1) & (fin > t0)).sum()),
                    "vehiculos_patio_al_cierre": int(((ini <= t1) & (fin > t1)).sum()),
                }
            )
    p = pd.DataFrame(filas)
    p["faltantes"] = (p["recomendados"] - p["reales"]).clip(lower=0)
    p["sobrantes"] = (p["reales"] - p["recomendados"]).clip(lower=0)
    orden = {b: i for i, b in enumerate(cfg_rec.nombres_bloques)}
    p["orden_bloque"] = p["bloque"].map(orden)
    return p


def oferta(f, ds, mr, td, cfg_rec, tipos_raros):
    f = f.copy()
    for u in UMBRALES_E:
        f[f"fuera_{int(u * 100)}"] = f["frac_servicio"] < u
        f[f"var_E{int(u * 100)}"] = np.where(f[f"fuera_{int(u * 100)}"], 0, f["var_B"])
    limites = limite_oferta(ds, f)
    f["var_G"], resumen_g = variante_g(f, "var_E50", limites)
    reales_dia = (
        f.groupby(["route", "dia_op"])["despachos_real"].sum().rename("reales").reset_index()
    )
    resumen_g = resumen_g.merge(reales_dia, on=["route", "dia_op"]).merge(
        limites[["route", "dia_op", "tipo_dia", "jornadas_previas", "despachos_previos"]],
        on=["route", "dia_op"],
    )
    resumen_g["error_limite"] = resumen_g["limite"] - resumen_g["reales"]
    resumen_g.to_csv(SALIDA / "analisis_limite_oferta.csv", index=False)

    variantes = {
        "B": ("var_B", "fuera_50"),
        "E30": ("var_E30", "fuera_30"),
        "E50": ("var_E50", "fuera_50"),
        "E70": ("var_E70", "fuera_70"),
        "G": ("var_G", "fuera_50"),
    }
    hor_cols = [c for c, _ in variantes.values()]
    filas, fuera_det = [], []
    for alcance, ff in (("todas", f), ("LABORAL", f[f["tipo_dia"] == "LABORAL"])):
        h = ff.assign(hora_reloj=ff["hora"].str.slice(0, 2))
        hh = (
            h.groupby(["route", "dia_op", "hora_reloj"])
            .agg(
                **{c: (c, "sum") for c in ["pasajeros_real", "despachos_real", *hor_cols]},
                q1=("q1", "first"),
                q3=("q3", "first"),
            )
            .reset_index()
        )
        for _, fc in set(variantes.values()):
            # Hora excluida si alguna de sus franjas con despachos reales esta fuera.
            marca = (
                (h[fc] & (h["despachos_real"] > 0))
                .groupby([h["route"], h["dia_op"], h["hora_reloj"]])
                .any()
            )
            hh[fc] = hh.set_index(["route", "dia_op", "hora_reloj"]).index.map(marca).to_numpy()
        for ruta in ("1", "3", "ambas"):
            fr = ff if ruta == "ambas" else ff[ff["route"] == int(ruta)]
            hr = hh if ruta == "ambas" else hh[hh["route"] == int(ruta)]
            for v, (col, fc) in [
                ("Practica real", ("despachos_real", "fuera_50")),
                *variantes.items(),
            ]:
                dentro, fuera = fr[~fr[fc]], fr[fr[fc]]
                fila = {
                    "alcance": alcance,
                    "route": ruta,
                    "variante": v,
                    "umbral_disponibilidad": fc[-2:],
                    "despachos": int(fr[col].sum()),
                    "reales": int(fr["despachos_real"].sum()),
                    "despachos_dentro": int(dentro[col].sum()),
                    "reales_dentro": int(dentro["despachos_real"].sum()),
                    "despachos_fuera": int(fuera[col].sum()),
                    "reales_fuera": int(fuera["despachos_real"].sum()),
                    "franjas_fuera": len(fuera),
                }
                for esc, u in (("franja", fr), ("hora", hr)):
                    pv = porcentajes_version(u, col, fc)
                    fila[f"{esc}_fuera_con_reales"] = pv["fuera_con_reales"]
                    for version in ("incluidas", "excluidas"):
                        for k, x in pv[version].items():
                            fila[f"{esc}_{version}_{k}"] = x
                filas.append(fila)
    for u in UMBRALES_E:
        fc = f"fuera_{int(u * 100)}"
        x = f[f[fc] & (f["despachos_real"] > 0)]
        fuera_det.append(
            x.assign(umbral=int(u * 100))[
                [
                    "umbral",
                    "route",
                    "dia_op",
                    "tipo_dia",
                    "hora",
                    "bloque",
                    "frac_servicio",
                    "despachos_real",
                    "pasajeros_real",
                ]
            ]
        )
    pd.DataFrame(filas).to_csv(SALIDA / "analisis_variantes_oferta.csv", index=False)
    pd.concat(fuera_det, ignore_index=True).to_csv(
        SALIDA / "analisis_fuera_disponibilidad.csv", index=False
    )
    f.to_csv(SALIDA / "analisis_franjas_oferta.csv", index=False)

    # Vehiculos distintos por jornada y ruta en las 8 semanas previas al 2026-09-21.
    v = pd.read_parquet(
        RUTA_MODEL_READY, columns=["PLACA", "FK_RUTA", "HORA_INICIAL_REAL", "MODEL_READY_OK"]
    )
    v = v[v["MODEL_READY_OK"].eq(True) & v["FK_RUTA"].isin([1, 3])].copy()
    v["dia_op"] = (pd.to_datetime(v["HORA_INICIAL_REAL"]) - pd.Timedelta(hours=4)).dt.date
    ini, fin = FECHAS[0] - timedelta(weeks=SEMANAS_SERVICIO), FECHAS[0] - timedelta(days=1)
    v = v[(v["dia_op"] >= ini) & (v["dia_op"] <= fin)]
    tipo = ds.drop_duplicates(["dia_op"]).set_index("dia_op")["tipo_dia"]
    porruta = v.groupby(["FK_RUTA", "dia_op"])["PLACA"].nunique().reset_index()
    ambas = v.groupby("dia_op")["PLACA"].nunique().reset_index().assign(FK_RUTA="ambas")
    veh = pd.concat([porruta, ambas], ignore_index=True)
    veh["tipo_dia"] = veh["dia_op"].map(tipo)
    vres = (
        veh.groupby(["FK_RUTA", "tipo_dia"])["PLACA"]
        .agg(jornadas="size", minimo="min", mediana="median", maximo="max")
        .reset_index()
    )
    vres.insert(0, "ventana", f"{ini} a {fin}")
    vres.to_csv(SALIDA / "analisis_vehiculos_por_jornada.csv", index=False)

    # Punto 5: oferta en patio para E50.
    p = patio(f, "var_E50", cfg_rec)
    p.to_csv(SALIDA / "analisis_patio_E50.csv", index=False)


def main():
    cfg_rec = cargar_configuracion_recomendacion()
    tipos_raros = cargar_configuracion_evaluacion().tipos_baja_frecuencia
    f = pd.concat([pd.read_csv(SALIDA / f"detalle_{d}.csv") for d in FECHAS], ignore_index=True)
    f["hora"] = f["hora"].astype(str)
    f["dia_op"] = f["dia_op"].astype(str)
    assert f["despachos_retirados"].eq(0).all(), (
        "hubo ajuste de factibilidad: revisar la descomposicion"
    )

    ds = pd.read_parquet(
        RUTA_DATASET, columns=["FK_RUTA", "timestamp", "tipo_dia", "despachos_count_real"]
    )
    ds["dia_op"] = (ds["timestamp"] - pd.Timedelta(hours=4)).dt.date
    ds["hora"] = ds["timestamp"].dt.strftime("%H:%M")

    # ---- variantes ----
    uno = np.ones(len(f), dtype=int)
    sp = servicio_previo(ds, f)
    f = f.merge(sp, on=["route", "dia_op", "hora"], validate="1:1")
    elegible = (f["frac_servicio"] >= UMBRAL_SERVICIO).astype(int).to_numpy()
    f["var_A"] = despachos(f, True, uno)
    f["var_B"] = despachos(f, False, uno)
    f["var_C"] = despachos(f, True, elegible)
    f["var_D"] = despachos(f, False, elegible)
    f["B_sin_minimo"] = despachos(f, False, np.zeros(len(f), dtype=int))
    assert (f["var_A"] == f["despachos_recomendados"]).all(), (
        "la variante A no reproduce la planilla"
    )
    capacidad = json.loads(
        (
            PROJECT_ROOT
            / "reports"
            / "tables"
            / "dispatch"
            / f"manifiesto__recomendacion_despacho__{cfg_rec.freeze}.json"
        ).read_text(encoding="utf-8")
    )["parametros"]["capacidad"]
    maximo = f.groupby("dia_op")[["var_A", "var_B", "var_C", "var_D"]].sum().max()
    assert (maximo <= int(capacidad)).all(), (
        f"alguna variante supera la capacidad {capacidad}: {maximo.to_dict()}"
    )

    # ---- 1. por jornada y ruta, con descomposicion ----
    sin_real = f["despachos_real"] == 0
    filas = []
    for (dia_op, ruta), g in f.groupby(["dia_op", "route"]):
        s = sin_real[g.index]
        dif = int(g["despachos_recomendados"].sum() - g["despachos_real"].sum())
        tope = int((g["var_A"] - g["var_B"]).sum())
        minimo = int((g["var_B"] - g["B_sin_minimo"])[s].sum())
        filas.append(
            {
                "dia_op": dia_op,
                "tipo_dia": g["tipo_dia"].iloc[0],
                "route": ruta,
                "pasajeros_predichos": g["demanda_predicha"].sum(),
                "pasajeros_reales": g["pasajeros_real"].sum(),
                "despachos_recomendados": int(g["despachos_recomendados"].sum()),
                "despachos_reales": int(g["despachos_real"].sum()),
                "diferencia": dif,
                "parte_servicio_minimo_sin_reales": minimo,
                "parte_tope": tope,
                "parte_resto": dif - minimo - tope,
                "franjas_sin_reales": int(s.sum()),
                "recomendados_en_franjas_sin_reales": int(g.loc[s, "despachos_recomendados"].sum()),
                "factor": g["factor"].iloc[0],
            }
        )
    jornadas = pd.DataFrame(filas)
    jornadas.to_csv(SALIDA / "analisis_jornadas.csv", index=False)

    # ---- 2. divisor frente a lo observado ----
    mr = pd.read_parquet(
        RUTA_MODEL_READY,
        columns=["FK_RUTA", "HORA_INICIAL_REAL", "PASAJEROS_REALES", "MODEL_READY_OK"],
    )
    td = pd.read_parquet(RUTA_DATASET, columns=["FK_RUTA", "timestamp", "tipo_dia"])
    desp = preparar_despachos(mr, td, cfg_rec.bloques, tipos_raros, cfg_rec.columna_pasajeros)
    desp = desp[
        desp["dia_op"].isin(FECHAS) & (desp["regimen"] != REGIMEN_RARO) & desp["bloque"].notna()
    ]
    obs = (
        desp.groupby(["route", "bloque"])["pasajeros"]
        .agg(despachos_observados="size", promedio="mean", mediana_observada="median")
        .reset_index()
    )
    crit = (
        f[f["regimen"] != REGIMEN_RARO]
        .groupby(["route", "bloque"])
        .agg(
            mediana_calibrada=("mediana_ordinaria", "first"),
            q3_calibrado=("q3_ordinario", "first"),
            franjas=("hora", "size"),
            franjas_mediana=("criterio", lambda s: int((s == "mediana del bloque").sum())),
            franjas_q3=("criterio", lambda s: int((s == "Q3 (tope de carga)").sum())),
            franjas_minimo=("criterio", lambda s: int((s == "servicio minimo").sum())),
        )
        .reset_index()
    )
    orden = {b: i for i, b in enumerate(cfg_rec.nombres_bloques)}
    divisores = crit.merge(obs, on=["route", "bloque"], how="outer").sort_values(
        ["route", "bloque"], key=lambda s: s.map(orden) if s.name == "bloque" else s
    )
    divisores.to_csv(SALIDA / "analisis_divisores.csv", index=False)

    # ---- 3. servicio desde las 16:00 en las 8 semanas previas al 2026-09-21 ----
    ini, fin = FECHAS[0] - timedelta(weeks=SEMANAS_SERVICIO), FECHAS[0] - timedelta(days=1)
    h = ds[(ds["dia_op"] >= ini) & (ds["dia_op"] <= fin) & (ds["hora"] >= "16:00")].copy()
    h["con_servicio"] = h["despachos_count_real"].fillna(0) > 0
    jor = (
        ds[(ds["dia_op"] >= ini) & (ds["dia_op"] <= fin)]
        .groupby(["FK_RUTA", "tipo_dia"])["dia_op"]
        .nunique()
    )
    serv = (
        h.groupby(["FK_RUTA", "tipo_dia", "hora"])["con_servicio"]
        .sum()
        .rename("jornadas_con_servicio")
        .reset_index()
    )
    serv["jornadas"] = serv.set_index(["FK_RUTA", "tipo_dia"]).index.map(jor)
    serv["pct"] = 100 * serv["jornadas_con_servicio"] / serv["jornadas"]
    serv.insert(0, "ventana", f"{ini} a {fin}")
    serv.to_csv(SALIDA / "analisis_servicio_desde_16h.csv", index=False)

    # ---- 4. variantes ----
    hor = por_hora(f, ["var_A", "var_B", "var_C", "var_D"])
    var = []
    for ruta in ("1", "3", "ambas"):
        ff = f if ruta == "ambas" else f[f["route"] == int(ruta)]
        hh = hor if ruta == "ambas" else hor[hor["route"] == int(ruta)]
        for v, col in (
            ("Practica real", "despachos_real"),
            ("A", "var_A"),
            ("B", "var_B"),
            ("C", "var_C"),
            ("D", "var_D"),
        ):
            fila = {
                "route": ruta,
                "variante": v,
                "despachos": int(ff[col].sum()),
                "despachos_reales": int(ff["despachos_real"].sum()),
                "franjas_cero_recomendados": int((ff[col] == 0).sum()),
                "franjas_cero_con_despachos_reales": int(
                    ((ff[col] == 0) & (ff["despachos_real"] > 0)).sum()
                ),
            }
            fila.update({f"franja_{k}": x for k, x in porcentajes(ff, col).items()})
            fila.update({f"hora_{k}": x for k, x in porcentajes(hh, col).items()})
            var.append(fila)
    variantes = pd.DataFrame(var)
    variantes.to_csv(SALIDA / "analisis_variantes.csv", index=False)
    f.to_csv(SALIDA / "analisis_franjas.csv", index=False)

    oferta(f, ds, mr, td, cfg_rec, tipos_raros)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(jornadas.round(1).to_string(index=False))
    print(divisores.round(2).to_string(index=False))
    print(serv.round(1).to_string(index=False))
    print(variantes.round(1).to_string(index=False))
    print("franjas no elegibles para el minimo (C/D):", int((elegible == 0).sum()), "de", len(f))
    print(
        f.loc[
            elegible == 0,
            [
                "route",
                "dia_op",
                "hora",
                "tipo_dia",
                "frac_servicio",
                "demanda_predicha",
                "var_A",
                "var_C",
                "var_B",
                "var_D",
                "despachos_real",
            ],
        ]
        .round(2)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
