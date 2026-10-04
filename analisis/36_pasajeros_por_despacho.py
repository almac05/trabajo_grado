"""Distribucion de pasajeros por despacho (PASAJEROS_REALES) por ruta, regimen y
bloque horario, en validacion y en evaluacion; clasificacion de las franjas de
evaluacion por carga relativa a los cuartiles de validacion; y capacidad de la
flota en evaluacion.

Fuente (solo lectura): el conjunto apto para modelado del dataset vigente,
`data/processed/model_ready/despachos_model_ready_freeze_20260823_203700.parquet`
(el `source_path` de configs/modeling/targets.yaml), una fila por despacho con
`MODEL_READY_OK`. No modifica scripts, freezes ni configuracion.

Definiciones:
  - Jornada operativa: fecha de HORA_INICIAL_REAL menos 4 horas (como en el
    modelado). Periodos por jornada, extremos inclusivos: validacion
    2025-12-25 a 2026-04-01; evaluacion 2026-04-02 a 2026-06-10 (todas las
    jornadas con despachos, no solo las 134 comunes del freeze).
  - Tipo de dia y regimen: festivos de Colombia (`holidays.Colombia`), con la
    regla de TimeSeriesBuilder._enriquecer; raro = FESTIVO o FESTIVO_PUENTE. Se
    verifica contra el `tipo_dia` del dataset de modelado.
  - Bloque horario: hora de inicio del despacho, con los bloques de
    `32_diagnostico_segmentos_metodos.py`.
  - Cuantiles: Q1, mediana, Q3 y P90 de PASAJEROS_REALES por despacho
    (interpolacion lineal). Intervalos de confianza del 95 % por bootstrap por
    jornada (los despachos de una jornada no son independientes), 1000 replicas.

Criterio de variacion apreciable (propio de este diagnostico, explicito para que
pueda cambiarse): una diferencia entre periodos es apreciable si su IC 95 %
excluye el cero y su magnitud es al menos el 10 % del valor de validacion. Entre
bloques, la variacion de un cuantil es apreciable si el rango entre bloques
(maximo menos minimo) es al menos el 10 % del valor de la ruta completa.

Clasificacion de franjas: para cada franja de 30 minutos con despachos, pasajeros
por despacho = suma de PASAJEROS_REALES / numero de despachos. Sobrecargada si
supera el Q3 de validacion de su ruta y bloque, subutilizada si esta por debajo
del Q1, normal en otro caso. Como el valor de la franja es un promedio de varios
despachos, su dispersion es menor que la de los despachos individuales y la
proporcion esperada en cada extremo es menor del 25 % aun sin cambio alguno; por
eso se aplica la misma clasificacion a las franjas de validacion como linea base.

Capacidad: por ruta, maximo de despachos en una jornada de evaluacion y
vehiculos activos (PLACA unicas con despachos, como en
scripts/diagnostico_reduccion_flota.py) en el periodo y por jornada.

Salidas en analisis/salidas/ (sufijo __pasajeros_por_despacho):
  - distribucion__pasajeros_por_despacho.csv
  - comparacion_periodos__pasajeros_por_despacho.csv
  - variacion_bloques__pasajeros_por_despacho.csv
  - franjas__pasajeros_por_despacho.csv
  - clasificacion_franjas__pasajeros_por_despacho.csv
  - capacidad_flota__pasajeros_por_despacho.csv
  - resumen__pasajeros_por_despacho.md
  - manifiesto__pasajeros_por_despacho.json

Uso:
    python analisis/36_pasajeros_por_despacho.py
"""

import json
from datetime import date, datetime

import holidays
import numpy as np
import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion

SUFIJO = "pasajeros_por_despacho"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
RUTA_MODEL_READY = (
    PROJECT_ROOT / "data" / "processed" / "model_ready"
    / "despachos_model_ready_freeze_20260823_203700.parquet"
)
COLUMNA = "PASAJEROS_REALES"

RUTA_DISTRIBUCION = SALIDA / f"distribucion__{SUFIJO}.csv"
RUTA_COMPARACION = SALIDA / f"comparacion_periodos__{SUFIJO}.csv"
RUTA_VARIACION = SALIDA / f"variacion_bloques__{SUFIJO}.csv"
RUTA_FRANJAS = SALIDA / f"franjas__{SUFIJO}.csv"
RUTA_CLASIFICACION = SALIDA / f"clasificacion_franjas__{SUFIJO}.csv"
RUTA_CAPACIDAD = SALIDA / f"capacidad_flota__{SUFIJO}.csv"
RUTA_RESUMEN = SALIDA / f"resumen__{SUFIJO}.md"
RUTA_MANIFIESTO = SALIDA / f"manifiesto__{SUFIJO}.json"

PERIODOS = {
    "validacion": (date(2025, 12, 25), date(2026, 4, 1)),
    "evaluacion": (date(2026, 4, 2), date(2026, 6, 10)),
}
BLOQUES = [  # igual que 32_diagnostico_segmentos_metodos.py
    ("madrugada (04:00-04:59)", 4, 5),
    ("pico manana (05:00-06:59)", 5, 7),
    ("manana (07:00-09:59)", 7, 10),
    ("valle (10:00-13:59)", 10, 14),
    ("pico tarde (14:00-15:59)", 14, 16),
    ("cierre (16:00 en adelante)", 16, 24),
]
ORDEN_BLOQUES = [b[0] for b in BLOQUES]
CUANTILES = {"q1": 0.25, "mediana": 0.5, "q3": 0.75, "p90": 0.9}
N_BOOTSTRAP = 1000
SEMILLA = 42
UMBRAL_RELATIVO = 0.10


# --------------------------------------------------------------------------- datos


def bloque_de(hora):
    for etiqueta, ini, fin in BLOQUES:
        if ini <= hora < fin:
            return etiqueta
    return "fuera de bloque"


def tipo_dia_de(fecha, festivos):
    # Misma regla que TimeSeriesBuilder._enriquecer.
    dow = fecha.weekday()
    if fecha in festivos:
        return "FESTIVO_PUENTE" if dow == 0 else "FESTIVO"
    return {5: "SABADO", 6: "DOMINGO"}.get(dow, "LABORAL")


def cargar_despachos(tipos_raros):
    d = pd.read_parquet(RUTA_MODEL_READY)
    assert d["MODEL_READY_OK"].eq(True).all()
    d = d.copy()
    d["inicio"] = pd.to_datetime(d["HORA_INICIAL_REAL"])
    d["dia_op"] = (d["inicio"] - pd.Timedelta(hours=4)).dt.date
    d["route"] = d["FK_RUTA"].astype(int)
    anios = {f.year for f in d["dia_op"]}
    festivos = set(holidays.Colombia(years=sorted(anios)))
    d["tipo_dia"] = [tipo_dia_de(f, festivos) for f in d["dia_op"]]
    d["regimen"] = np.where(d["tipo_dia"].isin(tipos_raros), "raro", "ordinario")
    d["bloque"] = d["inicio"].dt.hour.map(bloque_de)
    d["franja"] = d["inicio"].dt.floor("30min")
    d["periodo"] = None
    for nombre, (ini, fin) in PERIODOS.items():
        d.loc[(d["dia_op"] >= ini) & (d["dia_op"] <= fin), "periodo"] = nombre
    d["jornada"] = d["route"].astype(str) + "_" + d["dia_op"].astype(str)
    return d


def verificar_contra_modelado(desp, ruta_dataset):
    """Suma de PASAJEROS_REALES y conteo por franja frente al dataset de modelado,
    y tipo de dia frente al suyo."""
    m = pd.read_parquet(ruta_dataset, columns=["FK_RUTA", "timestamp", "pasajeros_total",
                                               "despachos_count_real", "tipo_dia"])
    m = m[m["despachos_count_real"].fillna(0) > 0]
    agg = desp.groupby(["route", "franja"]).agg(
        suma=(COLUMNA, "sum"), n=(COLUMNA, "size"), tipo_dia=("tipo_dia", "first")).reset_index()
    unido = agg.merge(m, left_on=["route", "franja"], right_on=["FK_RUTA", "timestamp"],
                      how="inner", suffixes=("", "_modelado"))
    return {
        "franjas_comparadas": len(unido),
        "max_dif_pasajeros": float((unido["suma"] - unido["pasajeros_total"]).abs().max()),
        "max_dif_despachos": float((unido["n"] - unido["despachos_count_real"]).abs().max()),
        "franjas_tipo_dia_distinto": int((unido["tipo_dia"] != unido["tipo_dia_modelado"]).sum()),
    }


# --------------------------------------------------------------------- cuantiles


def por_jornada(grupo):
    return [g[COLUMNA].to_numpy(dtype=float) for _, g in grupo.groupby("jornada")]


def bootstrap(arrays, rng):
    """Replicas bootstrap por jornada de los cuatro cuantiles: matriz (N, 4)."""
    k = len(arrays)
    salida = np.empty((N_BOOTSTRAP, len(CUANTILES)))
    for b in range(N_BOOTSTRAP):
        valores = np.concatenate([arrays[i] for i in rng.integers(0, k, k)])
        salida[b] = np.quantile(valores, list(CUANTILES.values()))
    return salida


def celdas(desp):
    """(periodo, corte, route, regimen, bloque) -> despachos de la celda."""
    out = {}
    for (periodo, ruta), g in desp.groupby(["periodo", "route"]):
        out[(periodo, "ruta", ruta, "todos", "todos")] = g
        for reg, gr in g.groupby("regimen"):
            out[(periodo, "regimen", ruta, reg, "todos")] = gr
        for blo, gb in g.groupby("bloque"):
            out[(periodo, "bloque", ruta, "todos", blo)] = gb
        for (reg, blo), gx in g.groupby(["regimen", "bloque"]):
            out[(periodo, "regimen_x_bloque", ruta, reg, blo)] = gx
    return out


def distribucion(desp, rng):
    filas, replicas = [], {}
    for clave, g in celdas(desp).items():
        valores = g[COLUMNA].to_numpy(dtype=float)
        q = np.quantile(valores, list(CUANTILES.values()))
        arrays = por_jornada(g)
        reps = bootstrap(arrays, rng)
        replicas[clave] = reps
        fila = dict(zip(["periodo", "corte", "route", "regimen", "bloque"], clave, strict=True))
        fila.update({"n_despachos": len(valores), "n_jornadas": len(arrays),
                     "media": valores.mean()})
        for j, nombre in enumerate(CUANTILES):
            fila[nombre] = q[j]
            fila[f"{nombre}_ic_inf"] = np.quantile(reps[:, j], 0.025)
            fila[f"{nombre}_ic_sup"] = np.quantile(reps[:, j], 0.975)
        filas.append(fila)
    return pd.DataFrame(filas), replicas


def comparar_periodos(dist, replicas):
    claves = ["corte", "route", "regimen", "bloque"]
    v = dist[dist["periodo"] == "validacion"].set_index(claves)
    e = dist[dist["periodo"] == "evaluacion"].set_index(claves)
    filas = []
    for clave in v.index.intersection(e.index):
        rv = replicas[("validacion", *clave)]
        re_ = replicas[("evaluacion", *clave)]
        fila = dict(zip(claves, clave, strict=True))
        fila.update({"n_despachos_val": int(v.loc[clave, "n_despachos"]),
                     "n_despachos_eval": int(e.loc[clave, "n_despachos"]),
                     "n_jornadas_val": int(v.loc[clave, "n_jornadas"]),
                     "n_jornadas_eval": int(e.loc[clave, "n_jornadas"])})
        apreciables = []
        for j, nombre in enumerate(CUANTILES):
            val, ev = v.loc[clave, nombre], e.loc[clave, nombre]
            dif = re_[:, j] - rv[:, j]
            inf, sup = np.quantile(dif, [0.025, 0.975])
            excluye = inf > 0 or sup < 0
            grande = abs(ev - val) >= UMBRAL_RELATIVO * val
            fila.update({f"{nombre}_val": val, f"{nombre}_eval": ev, f"{nombre}_dif": ev - val,
                         f"{nombre}_dif_pct": 100 * (ev - val) / val,
                         f"{nombre}_dif_ic_inf": inf, f"{nombre}_dif_ic_sup": sup,
                         f"{nombre}_ic_excluye_0": excluye,
                         f"{nombre}_apreciable": bool(excluye and grande)})
            if excluye and grande:
                apreciables.append(nombre)
        fila["cuantiles_apreciables"] = ", ".join(apreciables)
        filas.append(fila)
    return pd.DataFrame(filas)


def variacion_bloques(dist):
    filas = []
    for (periodo, ruta), g in dist[dist["corte"] == "bloque"].groupby(["periodo", "route"]):
        total = dist[(dist["periodo"] == periodo) & (dist["corte"] == "ruta")
                     & (dist["route"] == ruta)].iloc[0]
        for nombre in CUANTILES:
            gi = g.set_index("bloque")[nombre]
            rango = gi.max() - gi.min()
            filas.append({
                "periodo": periodo, "route": ruta, "cuantil": nombre,
                "valor_ruta": total[nombre], "minimo": gi.min(), "bloque_minimo": gi.idxmin(),
                "maximo": gi.max(), "bloque_maximo": gi.idxmax(), "rango": rango,
                "rango_pct_ruta": 100 * rango / total[nombre],
                "apreciable": bool(rango >= UMBRAL_RELATIVO * total[nombre]),
            })
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ clasificacion


def clasificar_franjas(desp, dist):
    umbrales = dist[(dist["periodo"] == "validacion") & (dist["corte"] == "bloque")]
    umbrales = umbrales.set_index(["route", "bloque"])[["q1", "q3"]]
    franjas = (
        desp[desp["periodo"].notna()]
        .groupby(["periodo", "route", "dia_op", "tipo_dia", "regimen", "franja", "bloque"])
        .agg(pasajeros=(COLUMNA, "sum"), despachos=(COLUMNA, "size"))
        .reset_index()
    )
    franjas["pasajeros_por_despacho"] = franjas["pasajeros"] / franjas["despachos"]
    franjas = franjas.join(umbrales.rename(columns={"q1": "q1_val", "q3": "q3_val"}),
                           on=["route", "bloque"])
    franjas["clase"] = np.select(
        [franjas["pasajeros_por_despacho"] > franjas["q3_val"],
         franjas["pasajeros_por_despacho"] < franjas["q1_val"]],
        ["sobrecargada", "subutilizada"], default="normal",
    )
    filas = []
    for (periodo, ruta), g in franjas.groupby(["periodo", "route"]):
        grupos = [("todos", g)] + [(b, gb) for b, gb in g.groupby("bloque")]
        for bloque, gb in grupos:
            conteo = gb["clase"].value_counts()
            fila = {"periodo": periodo, "route": ruta, "bloque": bloque, "n_franjas": len(gb),
                    "despachos_por_franja_mediana": gb["despachos"].median()}
            for clase in ("sobrecargada", "normal", "subutilizada"):
                fila[f"n_{clase}"] = int(conteo.get(clase, 0))
                fila[f"pct_{clase}"] = 100 * conteo.get(clase, 0) / len(gb)
            filas.append(fila)
    return franjas, pd.DataFrame(filas)


# ----------------------------------------------------------------------- capacidad


def capacidad(desp):
    ev = desp[desp["periodo"] == "evaluacion"]
    filas = []
    grupos = [(str(r), g) for r, g in ev.groupby("route")] + [("ambas", ev)]
    for ruta, g in grupos:
        por_dia = g.groupby("dia_op").agg(despachos=(COLUMNA, "size"),
                                          vehiculos=("PLACA", "nunique"),
                                          tipo_dia=("tipo_dia", "first"))
        dia_max = por_dia["despachos"].idxmax()
        laboral = por_dia[por_dia["tipo_dia"] == "LABORAL"]
        filas.append({
            "route": ruta, "jornadas": len(por_dia),
            "max_despachos_jornada": int(por_dia["despachos"].max()),
            "jornada_max_despachos": str(dia_max),
            "tipo_dia_jornada_max": por_dia.loc[dia_max, "tipo_dia"],
            "mediana_despachos_jornada_laboral": float(laboral["despachos"].median()),
            "vehiculos_activos_periodo": int(g["PLACA"].nunique()),
            "max_vehiculos_jornada": int(por_dia["vehiculos"].max()),
            "mediana_vehiculos_jornada_laboral": float(laboral["vehiculos"].median()),
            "vehiculos_en_jornada_max_despachos": int(por_dia.loc[dia_max, "vehiculos"]),
        })
    return pd.DataFrame(filas)


# ------------------------------------------------------------------------ resumen


def coma(valor, decimales=1):
    return f"{valor:.{decimales}f}".replace(".", ",").replace("-", "−")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    return "\n".join(lineas + ["| " + " | ".join(str(c) for c in f) + " |" for f in filas])


def orden(df, col="bloque"):
    clave = {b: i for i, b in enumerate(["todos", "ordinario", "raro", *ORDEN_BLOQUES])}
    return df.sort_values(by=col, key=lambda s: s.map(clave))


def tabla_distribucion(dist, periodo):
    filas = []
    for corte in ("ruta", "regimen", "bloque"):
        sub = dist[(dist["periodo"] == periodo) & (dist["corte"] == corte)]
        for ruta in sorted(sub["route"].unique()):
            s = sub[sub["route"] == ruta]
            s = orden(s, "regimen" if corte == "regimen" else "bloque")
            for f in s.to_dict("records"):
                celda = {"ruta": "ruta completa", "regimen": f"régimen {f['regimen']}",
                         "bloque": f["bloque"]}[corte]
                filas.append([ruta, celda, f"{f['n_despachos']} / {f['n_jornadas']}",
                              coma(f["q1"]), coma(f["mediana"]), coma(f["q3"]), coma(f["p90"]),
                              f"[{coma(f['mediana_ic_inf'])}; {coma(f['mediana_ic_sup'])}]"])
    return tabla_md(["Ruta", "Celda", "Despachos / jornadas", "Q1", "Mediana", "Q3", "P90",
                     "IC 95 % mediana"], filas)


def escribir_resumen(ctx):
    dist, comp, var, clas, cap, verif = (ctx[k] for k in
                                         ("dist", "comp", "var", "clas", "cap", "verif"))
    p = [
        "# Pasajeros por despacho: distribución, carga por franja y capacidad de la flota",
        "",
        "Generado por `analisis/36_pasajeros_por_despacho.py`.",
        "",
        f"- Fuente: `{RUTA_MODEL_READY.relative_to(PROJECT_ROOT).as_posix()}`, columna "
        f"`{COLUMNA}`, una fila por despacho. Validación {PERIODOS['validacion'][0]} a "
        f"{PERIODOS['validacion'][1]}; evaluación {PERIODOS['evaluacion'][0]} a "
        f"{PERIODOS['evaluacion'][1]} (todas las jornadas con despachos; jornada = inicio − 4 h).",
        f"- Verificación frente al dataset de modelado ({verif['franjas_comparadas']} franjas): "
        f"diferencia máxima en pasajeros por franja {verif['max_dif_pasajeros']:.0f}, en despachos "
        f"{verif['max_dif_despachos']:.0f}; franjas con tipo de día distinto: "
        f"{verif['franjas_tipo_dia_distinto']}.",
        "- Bloques del diagnóstico por segmentos, por hora de inicio del despacho. Régimen raro = "
        "FESTIVO o FESTIVO_PUENTE.",
        f"- IC 95 % por bootstrap por jornada ({N_BOOTSTRAP} réplicas).",
        "- **Criterio de «apreciable» (propio de este diagnóstico):** entre periodos, IC 95 % de la "
        "diferencia que excluye el cero y magnitud ≥ 10 % del valor de validación; entre bloques, "
        "rango entre bloques ≥ 10 % del valor de la ruta completa.",
        "",
    ]
    for periodo in PERIODOS:
        p += [f"## Distribución por despacho: {periodo}", "", tabla_distribucion(dist, periodo), ""]

    p += ["## Variación entre bloques horarios", "",
          "Rango de cada cuantil entre los seis bloques, como porcentaje del valor de la ruta "
          "completa.", "",
          tabla_md(["Periodo", "Ruta", "Cuantil", "Ruta completa", "Mínimo (bloque)",
                    "Máximo (bloque)", "Rango % ", "¿Apreciable?"],
                   [[f["periodo"], f["route"], f["cuantil"], coma(f["valor_ruta"]),
                     f"{coma(f['minimo'])} ({f['bloque_minimo']})",
                     f"{coma(f['maximo'])} ({f['bloque_maximo']})",
                     coma(f["rango_pct_ruta"]), "sí" if f["apreciable"] else "no"]
                    for f in var.to_dict("records")]), ""]

    filas = []
    for f in orden(comp[comp["corte"].isin(["ruta", "regimen", "bloque"])]
                   .sort_values(["route", "corte"]), "bloque").sort_values(
                       ["route", "corte"], kind="stable").to_dict("records"):
        celda = {"ruta": "ruta completa", "regimen": f"régimen {f['regimen']}",
                 "bloque": f["bloque"]}[f["corte"]]
        filas.append([f["route"], celda,
                      *[f"{coma(f[f'{q}_val'])} → {coma(f[f'{q}_eval'])} "
                        f"({'+' if f[f'{q}_dif'] >= 0 else ''}{coma(f[f'{q}_dif_pct'])} %)"
                        + (" **◆**" if f[f"{q}_apreciable"] else "")
                        for q in ("q1", "mediana", "q3", "p90")]])
    p += ["## Comparación entre periodos (validación → evaluación)", "",
          "◆ = diferencia apreciable según el criterio indicado. El detalle con IC está en "
          f"`{RUTA_COMPARACION.name}`.", "",
          tabla_md(["Ruta", "Celda", "Q1", "Mediana", "Q3", "P90"], filas), ""]

    p += ["## Clasificación de franjas por pasajeros por despacho", "",
          "Umbrales: Q1 y Q3 de validación (por despacho) de la ruta y el bloque. La misma "
          "clasificación aplicada a las franjas de validación es la línea base: como la franja "
          "promedia varios despachos, ni siquiera sin cambio alguno cabe esperar un 25 % en cada "
          "extremo.", ""]
    filas = []
    for ruta in sorted(clas["route"].unique()):
        for bloque in ["todos", *ORDEN_BLOQUES]:
            ev = clas[(clas["periodo"] == "evaluacion") & (clas["route"] == ruta)
                      & (clas["bloque"] == bloque)]
            va = clas[(clas["periodo"] == "validacion") & (clas["route"] == ruta)
                      & (clas["bloque"] == bloque)]
            if ev.empty:
                continue
            ev, va = ev.iloc[0], va.iloc[0]
            filas.append([ruta, bloque, str(ev["n_franjas"]),
                          coma(ev["pct_sobrecargada"]), coma(ev["pct_normal"]),
                          coma(ev["pct_subutilizada"]),
                          f"{coma(va['pct_sobrecargada'])} / {coma(va['pct_normal'])} / "
                          f"{coma(va['pct_subutilizada'])}"])
    p += [tabla_md(["Ruta", "Bloque", "Franjas eval.", "% sobrecargada", "% normal",
                    "% subutilizada", "Línea base validación (sobre / normal / sub)"], filas), ""]

    p += ["## Capacidad de la flota en evaluación", "",
          "Vehículos activos = placas distintas con al menos un despacho. Los mismos vehículos "
          "operan en ambas rutas, por lo que la fila «ambas» es la flota total.", "",
          tabla_md(["Ruta", "Jornadas", "Máx. despachos en una jornada (fecha, tipo)",
                    "Mediana despachos jornada laboral", "Vehículos activos en el periodo",
                    "Máx. vehículos en una jornada", "Mediana vehículos jornada laboral"],
                   [[f["route"], str(f["jornadas"]),
                     f"{f['max_despachos_jornada']} ({f['jornada_max_despachos']}, "
                     f"{f['tipo_dia_jornada_max']})",
                     coma(f["mediana_despachos_jornada_laboral"], 0),
                     str(f["vehiculos_activos_periodo"]), str(f["max_vehiculos_jornada"]),
                     coma(f["mediana_vehiculos_jornada_laboral"], 0)]
                    for f in cap.to_dict("records")]), ""]
    RUTA_RESUMEN.write_text("\n".join(p), encoding="utf-8")


# --------------------------------------------------------------------------- main


def main():
    config = cargar_configuracion_evaluacion()
    tipos_raros = tuple(config.tipos_baja_frecuencia)
    desp = cargar_despachos(tipos_raros)
    verif = verificar_contra_modelado(desp, config.ruta_dataset)
    assert verif["max_dif_pasajeros"] == 0 and verif["max_dif_despachos"] == 0, verif
    assert verif["franjas_tipo_dia_distinto"] == 0, verif

    en_periodo = desp[desp["periodo"].notna()]
    assert (en_periodo["bloque"] != "fuera de bloque").all()
    rng = np.random.default_rng(SEMILLA)
    dist, replicas = distribucion(en_periodo, rng)
    comp = comparar_periodos(dist, replicas)
    var = variacion_bloques(dist)
    franjas, clas = clasificar_franjas(en_periodo, dist)
    cap = capacidad(en_periodo)

    dist.to_csv(RUTA_DISTRIBUCION, index=False)
    comp.to_csv(RUTA_COMPARACION, index=False)
    var.to_csv(RUTA_VARIACION, index=False)
    franjas.to_csv(RUTA_FRANJAS, index=False)
    clas.to_csv(RUTA_CLASIFICACION, index=False)
    cap.to_csv(RUTA_CAPACIDAD, index=False)
    escribir_resumen({"dist": dist, "comp": comp, "var": var, "clas": clas, "cap": cap,
                      "verif": verif})

    resumen_periodos = {
        p: {"jornadas": int(g["jornada"].nunique()), "despachos": len(g),
            "jornadas_raras": int(g.loc[g["regimen"] == "raro", "jornada"].nunique())}
        for p, g in en_periodo.groupby("periodo")
    }
    manifiesto = {
        "script": "analisis/36_pasajeros_por_despacho.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sufijo": SUFIJO,
        "fuente": str(RUTA_MODEL_READY.relative_to(PROJECT_ROOT)),
        "columna_pasajeros": COLUMNA,
        "periodos": {k: [str(a), str(b)] for k, (a, b) in PERIODOS.items()},
        "conteos": resumen_periodos,
        "bloques": {b[0]: [b[1], b[2]] for b in BLOQUES},
        "tipos_baja_frecuencia": list(tipos_raros),
        "cuantiles": CUANTILES,
        "bootstrap": {"replicas": N_BOOTSTRAP, "unidad": "jornada", "semilla": SEMILLA},
        "criterio_apreciable": {
            "entre_periodos": "IC 95 % de la diferencia excluye 0 y |dif| >= 10 % del valor de validacion",
            "entre_bloques": "rango entre bloques >= 10 % del valor de la ruta completa",
        },
        "verificacion_dataset_modelado": verif,
        "capacidad": cap.to_dict("records"),
        "salidas": [str(r.relative_to(PROJECT_ROOT)) for r in (
            RUTA_DISTRIBUCION, RUTA_COMPARACION, RUTA_VARIACION, RUTA_FRANJAS,
            RUTA_CLASIFICACION, RUTA_CAPACIDAD, RUTA_RESUMEN, RUTA_MANIFIESTO)],
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Periodos: {resumen_periodos}\nVerificacion: {verif}\nResumen: {RUTA_RESUMEN}")


if __name__ == "__main__":
    main()
