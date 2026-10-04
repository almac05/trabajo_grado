"""Agregacion de metricas de una configuracion: global, por ruta y por tipo
de dia. Reutiliza ``calcular_metricas`` de evaluation_aggregation, la misma
funcion que usa la evaluacion comparativa, aplicada a las observaciones
agrupadas por ``runner.evaluar_configuracion``.

El unico criterio de seleccion es el MAE global (agregado sobre todo el
periodo de validacion, ambas rutas). El sesgo y el desglose por tipo de dia
se calculan y se persisten como informacion adicional; no intervienen en la
eleccion de la configuracion ganadora.
"""

from __future__ import annotations

import pandas as pd

from proyecto_grado.modeling.evaluation_aggregation import calcular_metricas


def metricas_configuracion(observaciones: pd.DataFrame, umbral_mape: float) -> dict:
    """Calcula MAE/sesgo (y el resto de indicadores) global, por ruta y por
    tipo de dia para una configuracion ya evaluada.

    ``observaciones`` es el DataFrame devuelto por
    ``runner.evaluar_configuracion``: columnas ``route``, ``dia_op``,
    ``tipo_dia``, ``real``, ``pred``.
    """
    if observaciones.empty:
        return {"global": {}, "por_ruta": {}, "por_tipo_dia": {}, "n_jornadas": 0}

    real = observaciones["real"].to_numpy()
    pred = observaciones["pred"].to_numpy()
    global_ = calcular_metricas(real, pred, umbral_mape)

    por_ruta = {}
    for ruta, grupo in observaciones.groupby("route"):
        por_ruta[str(ruta)] = calcular_metricas(
            grupo["real"].to_numpy(), grupo["pred"].to_numpy(), umbral_mape
        )

    por_tipo_dia = {}
    for tipo, grupo in observaciones.groupby("tipo_dia"):
        por_tipo_dia[str(tipo)] = calcular_metricas(
            grupo["real"].to_numpy(), grupo["pred"].to_numpy(), umbral_mape
        )

    return {
        "global": global_,
        "por_ruta": por_ruta,
        "por_tipo_dia": por_tipo_dia,
        "n_jornadas": observaciones[["route", "dia_op"]].drop_duplicates().shape[0],
    }
