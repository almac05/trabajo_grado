"""Evaluacion de la recomendacion de despacho frente a la operacion real.

Por franja: demanda real y predicha, despachos reales y recomendados, y la clase
de carga real (pasajeros por despacho frente al Q1 y Q3 de calibracion de su
regimen: ruta y bloque en ordinario, ruta en raro). Las franjas sin despachos
reales llevan la clase ``sin_despachos``.

Tres tablas, por ruta y bloque horario (con ``todos`` como agregado):

1. Por clase real, proporcion de franjas con recomendacion mayor, igual o menor.
2. Clase que habria tenido la franja con la recomendacion (demanda real entre
   despachos recomendados) frente a la clase real.
3. Por jornada, total recomendado frente al real y jornadas con ajuste de
   factibilidad.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from proyecto_grado.dispatch.parametros import BLOQUE_TODOS

logger = logging.getLogger(__name__)

CLASES = ("sobrecargada", "normal", "subutilizada")
SIN_DESPACHOS = "sin_despachos"
COMPARACIONES = ("mayor", "igual", "menor")
CLASE_TODAS = "todas"


def franjas_reales(despachos: pd.DataFrame) -> pd.DataFrame:
    """Pasajeros y despachos reales por ruta, jornada y franja."""
    reales = (
        despachos.groupby(["route", "dia_op", "hora"])
        .agg(pasajeros_real=("pasajeros", "sum"), despachos_real=("pasajeros", "size"))
        .reset_index()
    )
    reales["dia_op"] = reales["dia_op"].astype(str)
    return reales


def clasificar(pasajeros_por_despacho: pd.Series, q1: pd.Series, q3: pd.Series) -> pd.Series:
    """Sobrecargada si supera Q3, subutilizada si esta bajo Q1; sin valor, sin despachos."""
    clase = np.select(
        [
            pasajeros_por_despacho.isna(),
            pasajeros_por_despacho > q3,
            pasajeros_por_despacho < q1,
        ],
        [SIN_DESPACHOS, "sobrecargada", "subutilizada"],
        default="normal",
    )
    return pd.Series(clase, index=pasajeros_por_despacho.index, dtype=object)


def construir_franjas_evaluacion(
    recomendacion: pd.DataFrame, reales: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int | float]]:
    """Une la recomendacion con la operacion real y clasifica cada franja."""
    franjas = recomendacion.merge(
        reales, on=["route", "dia_op", "hora"], how="left", validate="1:1"
    )
    franjas["pasajeros_real"] = franjas["pasajeros_real"].fillna(0.0)
    franjas["despachos_real"] = franjas["despachos_real"].fillna(0).astype(int)
    con_despachos = franjas["despachos_real"] > 0
    franjas["ppd_real"] = (franjas["pasajeros_real"] / franjas["despachos_real"]).where(
        con_despachos
    )
    franjas["clase_real"] = clasificar(franjas["ppd_real"], franjas["q1"], franjas["q3"])
    franjas["ppd_recomendada"] = franjas["pasajeros_real"] / franjas["despachos_recomendados"]
    franjas["clase_recomendada"] = clasificar(
        franjas["ppd_recomendada"], franjas["q1"], franjas["q3"]
    )
    diferencia = franjas["despachos_recomendados"] - franjas["despachos_real"]
    franjas["comparacion"] = np.select(
        [diferencia > 0, diferencia < 0], ["mayor", "menor"], default="igual"
    )

    jornadas = recomendacion[["route", "dia_op"]].drop_duplicates()
    reales_en_jornadas = reales.merge(jornadas, on=["route", "dia_op"], how="inner")
    claves = ["route", "dia_op", "hora"]
    fuera = reales_en_jornadas.merge(recomendacion[claves], on=claves, how="left", indicator=True)
    fuera = fuera[fuera["_merge"] == "left_only"]
    verificacion: dict[str, int | float] = {
        "franjas": len(franjas),
        "franjas_sin_despachos_reales": int((~con_despachos).sum()),
        "max_dif_demanda_real_vs_artefacto": float(
            (franjas["pasajeros_real"] - franjas["real"]).abs().max()
        ),
        "franjas_reales_fuera_de_la_prediccion": len(fuera),
        "despachos_reales_fuera_de_la_prediccion": int(fuera["despachos_real"].sum()),
    }
    logger.info("Union con la operacion real: %s", verificacion)
    return franjas, verificacion


def _con_todos(franjas: pd.DataFrame) -> pd.DataFrame:
    """Duplica las franjas con ``bloque = todos`` para el agregado de la ruta."""
    return pd.concat([franjas, franjas.assign(bloque=BLOQUE_TODOS)], ignore_index=True)


def _ordenar(tabla: pd.DataFrame, orden_bloques: list[str]) -> pd.DataFrame:
    orden = {nombre: i for i, nombre in enumerate([BLOQUE_TODOS, *orden_bloques])}
    return tabla.sort_values(
        ["route", "bloque"], key=lambda s: s.map(orden) if s.name == "bloque" else s, kind="stable"
    ).reset_index(drop=True)


def tabla_comparacion_despachos(franjas: pd.DataFrame, orden_bloques: list[str]) -> pd.DataFrame:
    """Proporcion de franjas con recomendacion mayor, igual o menor, por clase real."""
    datos = _con_todos(franjas)
    datos = pd.concat([datos, datos.assign(clase_real=CLASE_TODAS)], ignore_index=True)
    conteo = (
        datos.groupby(["route", "bloque", "clase_real", "comparacion"])
        .size()
        .unstack("comparacion", fill_value=0)
        .reindex(columns=list(COMPARACIONES), fill_value=0)
    )
    tabla = conteo.reset_index()
    tabla["n_franjas"] = conteo.sum(axis=1).to_numpy()
    for comparacion in COMPARACIONES:
        tabla = tabla.rename(columns={comparacion: f"n_{comparacion}"})
        tabla[f"pct_{comparacion}"] = 100 * tabla[f"n_{comparacion}"] / tabla["n_franjas"]
    orden_clases = {c: i for i, c in enumerate([CLASE_TODAS, *CLASES, SIN_DESPACHOS])}
    tabla = tabla.sort_values("clase_real", key=lambda s: s.map(orden_clases), kind="stable")
    return _ordenar(tabla, orden_bloques)


def tabla_clasificacion(
    franjas: pd.DataFrame, orden_bloques: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clase real frente a la que habria tenido la franja con la recomendacion.

    El resumen se calcula sobre las franjas con despachos reales (donde la clase
    real esta definida); las franjas sin despachos reales se cuentan aparte. La
    matriz cruza clase real y clase con la recomendacion para todas las franjas.
    """
    datos = _con_todos(franjas)
    filas = []
    for (ruta, bloque), grupo in datos.groupby(["route", "bloque"]):
        con_real = grupo[grupo["despachos_real"] > 0]
        fila: dict[str, object] = {
            "route": ruta,
            "bloque": bloque,
            "n_franjas": len(con_real),
            "n_sin_despachos_reales": len(grupo) - len(con_real),
        }
        for clase in CLASES:
            n_real = int((con_real["clase_real"] == clase).sum())
            n_rec = int((con_real["clase_recomendada"] == clase).sum())
            fila[f"pct_{clase}_real"] = 100 * n_real / len(con_real) if len(con_real) else np.nan
            fila[f"pct_{clase}_recomendada"] = (
                100 * n_rec / len(con_real) if len(con_real) else np.nan
            )
        fila["pct_misma_clase"] = (
            100 * float((con_real["clase_real"] == con_real["clase_recomendada"]).mean())
            if len(con_real)
            else np.nan
        )
        filas.append(fila)
    resumen = _ordenar(pd.DataFrame(filas), orden_bloques)
    matriz = (
        datos.groupby(["route", "bloque", "clase_real", "clase_recomendada"])
        .size()
        .rename("n_franjas")
        .reset_index()
    )
    return resumen, _ordenar(matriz, orden_bloques)


def tabla_jornadas(
    franjas: pd.DataFrame, jornadas_ajuste: pd.DataFrame, orden_bloques: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Totales por jornada, recomendado frente a real, y jornadas con ajuste.

    Devuelve el resumen por ruta y bloque y el detalle por ruta, bloque y jornada.
    ``jornadas_con_ajuste`` cuenta las jornadas en que se aplico la factibilidad
    (sobre ambas rutas); ``jornadas_con_retiro``, aquellas en que el ajuste retiro
    despachos de esa ruta y bloque.
    """
    datos = _con_todos(franjas)
    detalle = (
        datos.groupby(["route", "bloque", "dia_op"])
        .agg(
            despachos_recomendados=("despachos_recomendados", "sum"),
            despachos_real=("despachos_real", "sum"),
            despachos_retirados=("despachos_retirados", "sum"),
        )
        .reset_index()
        .merge(jornadas_ajuste[["dia_op", "ajustada"]], on="dia_op", how="left", validate="m:1")
    )
    detalle["diferencia"] = detalle["despachos_recomendados"] - detalle["despachos_real"]
    resumen = (
        detalle.groupby(["route", "bloque"])
        .agg(
            n_jornadas=("dia_op", "size"),
            total_recomendado=("despachos_recomendados", "sum"),
            total_real=("despachos_real", "sum"),
            media_recomendada_jornada=("despachos_recomendados", "mean"),
            media_real_jornada=("despachos_real", "mean"),
            media_diferencia_jornada=("diferencia", "mean"),
            jornadas_recomendado_mayor=("diferencia", lambda s: int((s > 0).sum())),
            jornadas_recomendado_igual=("diferencia", lambda s: int((s == 0).sum())),
            jornadas_recomendado_menor=("diferencia", lambda s: int((s < 0).sum())),
            jornadas_con_ajuste=("ajustada", "sum"),
            jornadas_con_retiro=("despachos_retirados", lambda s: int((s > 0).sum())),
            despachos_retirados=("despachos_retirados", "sum"),
        )
        .reset_index()
    )
    resumen["diferencia_pct"] = (
        100 * (resumen["total_recomendado"] - resumen["total_real"]) / resumen["total_real"]
    )
    return _ordenar(resumen, orden_bloques), _ordenar(detalle, orden_bloques)
