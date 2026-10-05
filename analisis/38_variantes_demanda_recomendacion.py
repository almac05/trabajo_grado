"""Recomendacion de despacho con cuatro fuentes de demanda, a escala de franja y
de bloque horario.

Reutiliza `proyecto_grado.dispatch` con la configuracion por defecto
(configs/dispatch/recomendacion.yaml: politica de festivos `divisor_propio`,
servicio minimo 1) y SIN tope de carga. Solo cambia la demanda que alimenta las
reglas y el ajuste de factibilidad:

  - mixta: prediccion mixta del modulo (XGBoost en regimen ordinario, referencia
    de 52 semanas en raro).
  - real: demanda observada; cota superior (recomendacion con demanda perfecta).
  - ref26: referencia historica de 26 semanas (`pred_ref26` del script 25).
  - combinada: referencia combinada por regimen, 26 s en ordinario y 52 s en raro
    (`pred_combinada` del script 25).

Las cuatro se calibran igual (periodo de calibracion del YAML) y se evaluan en
las franjas de las jornadas comunes del freeze dentro del periodo de evaluacion.

Escalas:
  - franja: la Tabla 2 del modulo (`tabla_clasificacion`): clase real frente a la
    que habria tenido la franja con la recomendacion (demanda real entre
    despachos recomendados).
  - bloque: se suman pasajeros reales, despachos reales y despachos recomendados
    por ruta, jornada y bloque horario, y cada bloque se clasifica con los mismos
    umbrales (Q1 y Q3 de calibracion de su ruta, bloque y regimen; el regimen es
    constante en la jornada) y la misma Tabla 2.

No modifica el modulo, scripts, freezes ni configuracion.

Salidas en analisis/salidas/ (sufijo __variantes_demanda_recomendacion__<freeze>):
  - clasificacion__...csv   Tabla 2 por variante, escala, ruta y bloque
  - proporciones__...csv    proporcion de unidades por clase, por variante y escala
  - unidades_bloque__...csv bloques clasificados (por variante)
  - resumen__...md, manifiesto__...json

Uso:
    python analisis/38_variantes_demanda_recomendacion.py
"""

import json
import logging
from datetime import datetime

import pandas as pd

from proyecto_grado.dispatch.config import cargar_configuracion_recomendacion
from proyecto_grado.dispatch.evaluacion import (
    CLASES,
    clasificar,
    construir_franjas_evaluacion,
    franjas_reales,
    tabla_clasificacion,
)
from proyecto_grado.dispatch.parametros import calibrar, filtrar_periodo, preparar_despachos
from proyecto_grado.dispatch.predictor_mixto import (
    construir_prediccion_mixta,
    verificar_contra_combinada,
)
from proyecto_grado.dispatch.reglas import generar_recomendacion
from proyecto_grado.modeling.config import PROJECT_ROOT

USAR_TOPE = False
VARIANTES = {  # nombre -> columna de demanda
    "mixta": "demanda_predicha",
    "real": "real",
    "ref26": "pred_ref26",
    "combinada": "pred_combinada",
}
CLAVES = ["route", "dia_op", "hora"]
SALIDA = PROJECT_ROOT / "analisis" / "salidas"


def cargar(config):
    e = config.entradas
    mr = pd.read_parquet(e["model_ready"], columns=["FK_RUTA", "HORA_INICIAL_REAL",
                                                    config.columna_pasajeros, "MODEL_READY_OK"])
    td = pd.read_parquet(e["dataset_modelado"], columns=["FK_RUTA", "timestamp", "tipo_dia"])
    desp = preparar_despachos(mr, td, config.bloques, config.tipos_raros, config.columna_pasajeros)
    cal = filtrar_periodo(desp, config.inicio_calibracion, config.fin_calibracion)
    ev = filtrar_periodo(desp, config.inicio_evaluacion, config.fin_evaluacion)
    pred = construir_prediccion_mixta(
        pd.read_csv(e["predicciones_xgboost"]), pd.read_csv(e["predicciones_referencia"]),
        pd.read_csv(e["jornadas_comunes"]), config.tipos_raros,
        config.columna_prediccion_ordinaria, config.columna_prediccion_rara)
    obs = pd.read_csv(e["observaciones_combinada"]).astype({"route": int, "dia_op": str,
                                                            "hora": str})
    verif = verificar_contra_combinada(pred, obs)
    assert verif["coincide"], verif
    pred = pred.merge(obs[[*CLAVES, "pred_ref26", "pred_combinada"]], on=CLAVES,
                      how="left", validate="1:1")
    assert pred[["pred_ref26", "pred_combinada"]].notna().all().all()
    return cal, ev, pred, verif


def a_bloques(franjas):
    """Una fila por ruta, jornada y bloque, con las columnas que usa la Tabla 2."""
    b = (franjas.groupby(["route", "dia_op", "bloque"])
         .agg(regimen=("regimen", "first"), n_regimenes=("regimen", "nunique"),
              q1=("q1", "first"), q3=("q3", "first"),
              n_umbrales=("q3", "nunique"),
              n_franjas=("hora", "size"),
              pasajeros_real=("pasajeros_real", "sum"),
              despachos_real=("despachos_real", "sum"),
              despachos_recomendados=("despachos_recomendados", "sum"))
         .reset_index())
    assert (b["n_regimenes"] == 1).all() and (b["n_umbrales"] == 1).all()
    b["ppd_real"] = (b["pasajeros_real"] / b["despachos_real"]).where(b["despachos_real"] > 0)
    b["clase_real"] = clasificar(b["ppd_real"], b["q1"], b["q3"])
    b["ppd_recomendada"] = b["pasajeros_real"] / b["despachos_recomendados"]
    b["clase_recomendada"] = clasificar(b["ppd_recomendada"], b["q1"], b["q3"])
    return b.drop(columns=["n_regimenes", "n_umbrales"])


def proporciones(unidades, variante, escala):
    """Proporcion por clase, por ruta y para ambas rutas: practica real y recomendacion."""
    filas = []
    con_real = unidades[unidades["despachos_real"] > 0]
    for ruta, g in [*con_real.groupby("route"), ("ambas", con_real)]:
        for origen, col in (("practica_real", "clase_real"), ("recomendacion", "clase_recomendada")):
            fila = {"variante": variante, "escala": escala, "route": str(ruta),
                    "origen": origen, "n_unidades": len(g)}
            for clase in CLASES:
                fila[f"pct_{clase}"] = 100 * (g[col] == clase).mean()
            fila["despachos"] = int(g["despachos_real" if origen == "practica_real"
                                      else "despachos_recomendados"].sum())
            filas.append(fila)
    return filas


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def tabla_md(enc, filas):
    lineas = ["| " + " | ".join(enc) + " |", "|" + "---|" * len(enc)]
    return "\n".join(lineas + ["| " + " | ".join(str(c) for c in f) + " |" for f in filas])


def escribir_resumen(destino, config, prop, clas, ajustes, verif):
    p = [
        "# Recomendación de despacho con cuatro fuentes de demanda",
        "",
        "Generado por `analisis/38_variantes_demanda_recomendacion.py`, con `proyecto_grado.dispatch`"
        f" en su configuración por defecto (política `{config.politica_festivos}`, servicio mínimo "
        f"{config.servicio_minimo}) y **sin tope**. Calibración {config.inicio_calibracion} a "
        f"{config.fin_calibracion}; evaluación {config.inicio_evaluacion} a {config.fin_evaluacion} "
        f"sobre las {verif['franjas_modulo']} franjas de las jornadas comunes de `{config.freeze}`.",
        "",
        "Unidades: franja de 30 min, o bloque horario de una jornada (suma de pasajeros y despachos"
        " de sus franjas), clasificadas con el Q1 y Q3 de calibración de su ruta, bloque y régimen. "
        "La clase de la recomendación usa la demanda real entre los despachos recomendados.",
        "",
    ]
    for escala in ("franja", "bloque"):
        filas = []
        sub = prop[(prop["escala"] == escala) & (prop["route"] == "ambas")]
        real = sub[sub["origen"] == "practica_real"].iloc[0]
        filas.append(["práctica real", real["n_unidades"], coma(real["pct_normal"]),
                      coma(real["pct_sobrecargada"]), coma(real["pct_subutilizada"]),
                      real["despachos"], "—"])
        for variante in VARIANTES:
            f = sub[(sub["origen"] == "recomendacion") & (sub["variante"] == variante)].iloc[0]
            misma = clas[(clas["variante"] == variante) & (clas["escala"] == escala)]
            pct_misma = (misma["pct_misma_clase"] * misma["n_franjas"]).sum() / misma["n_franjas"].sum()
            filas.append([variante, f["n_unidades"], coma(f["pct_normal"]),
                          coma(f["pct_sobrecargada"]), coma(f["pct_subutilizada"]),
                          f["despachos"], coma(pct_misma)])
        p += [f"## Escala {escala}, ambas rutas", "",
              tabla_md(["Origen", "Unidades", "% normal", "% sobrecargada", "% subutilizada",
                        "Despachos", "% misma clase que la real"], filas), ""]

    filas = []
    for escala in ("franja", "bloque"):
        for ruta in ("1", "3"):
            sub = prop[(prop["escala"] == escala) & (prop["route"] == ruta)]
            for origen, variante in [("practica_real", "mixta"),
                                     *[("recomendacion", v) for v in VARIANTES]]:
                f = sub[(sub["origen"] == origen) & (sub["variante"] == variante)].iloc[0]
                nombre = "práctica real" if origen == "practica_real" else variante
                filas.append([escala, ruta, nombre, f["n_unidades"], coma(f["pct_normal"]),
                              coma(f["pct_sobrecargada"]), coma(f["pct_subutilizada"])])
    p += ["## Por ruta", "", tabla_md(["Escala", "Ruta", "Origen", "Unidades", "% normal",
                                       "% sobrecargada", "% subutilizada"], filas), ""]

    p += ["## Ajuste de factibilidad por variante", "",
          tabla_md(["Variante", "Jornadas ajustadas", "Despachos retirados"],
                   [[v, f"{a['ajustadas']} de {a['jornadas']}", a["retirados"]]
                    for v, a in ajustes.items()]), "",
          "La Tabla 2 completa por ruta y bloque está en "
          f"`clasificacion__variantes_demanda_recomendacion__{config.freeze}.csv`.", ""]
    destino.write_text("\n".join(p), encoding="utf-8")


def main():
    logging.basicConfig(level=logging.WARNING)
    config = cargar_configuracion_recomendacion()
    sufijo = f"variantes_demanda_recomendacion__{config.freeze}"
    rutas = {t: SALIDA / f"{t}__{sufijo}.{ext}" for t, ext in (
        ("clasificacion", "csv"), ("proporciones", "csv"), ("unidades_bloque", "csv"),
        ("resumen", "md"), ("manifiesto", "json"))}

    cal, ev, pred, verif = cargar(config)
    parametros = calibrar(cal, config.bloques)
    reales = franjas_reales(ev)
    orden = list(config.nombres_bloques)

    clasif, prop, bloques_todos, ajustes, verif_union = [], [], [], {}, {}
    for variante, columna in VARIANTES.items():
        entrada = pred.assign(demanda_predicha=pred[columna])
        rec, ajuste = generar_recomendacion(entrada, parametros, config.bloques,
                                            config.politica_festivos, USAR_TOPE,
                                            config.servicio_minimo)
        franjas, vu = construir_franjas_evaluacion(rec, reales)
        verif_union[variante] = vu
        ajustes[variante] = {"jornadas": len(ajuste), "ajustadas": int(ajuste["ajustada"].sum()),
                             "retirados": int(ajuste["retirados"].sum())}
        bloques = a_bloques(franjas)
        bloques_todos.append(bloques.assign(variante=variante))
        for escala, unidades in (("franja", franjas), ("bloque", bloques)):
            resumen, _ = tabla_clasificacion(unidades, orden)
            clasif.append(resumen.assign(variante=variante, escala=escala))
            prop += proporciones(unidades, variante, escala)

    clas = pd.concat(clasif, ignore_index=True)
    clas = clas[["variante", "escala", *[c for c in clas.columns if c not in ("variante", "escala")]]]
    prop = pd.DataFrame(prop)
    clas.to_csv(rutas["clasificacion"], index=False)
    prop.to_csv(rutas["proporciones"], index=False)
    pd.concat(bloques_todos, ignore_index=True).to_csv(rutas["unidades_bloque"], index=False)
    escribir_resumen(rutas["resumen"], config, prop, clas, ajustes, verif)

    manifiesto = {
        "script": "analisis/38_variantes_demanda_recomendacion.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "freeze": config.freeze,
        "configuracion": "configs/dispatch/recomendacion.yaml",
        "politica_festivos": config.politica_festivos,
        "usar_tope": USAR_TOPE,
        "servicio_minimo": config.servicio_minimo,
        "capacidad": parametros.capacidad,
        "variantes": VARIANTES,
        "nota_tabla_2": "en la escala bloque, la columna n_franjas de clasificacion cuenta bloques",
        "verificacion_script_25": verif,
        "union_operacion_real": verif_union,
        "ajuste_factibilidad": ajustes,
        "salidas": [str(r.relative_to(PROJECT_ROOT).as_posix()) for r in rutas.values()],
    }
    rutas["manifiesto"].write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2,
                                              default=str), encoding="utf-8")
    print(rutas["resumen"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
