"""Consolida metricas del freeze nuevo: global, por ruta, por tipo de dia y
por regimen, sobre el soporte comun de los seis metodos.

No reutiliza ``evaluation_aggregation.ejecutar_agregacion``: esa funcion esta
acoplada por diseno a comprobaciones de equivalencia/regresion contra el
freeze anterior (``referencia_metricas_pre_consolidacion.csv``,
``referencia_jornadas_pre_consolidacion.csv``), pensadas como guardarraya de
una consolidacion unica y ya cerrada, no como un flujo repetible para un
freeze nuevo. Si reutiliza ``calcular_metricas``, la misma funcion que usa la
evaluacion comparativa oficial, para que los numeros sean comparables.
"""

from __future__ import annotations

import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_aggregation import calcular_metricas
from proyecto_grado.modeling.evaluation_config import ConfiguracionEvaluacionComparativa

SALIDA = PROJECT_ROOT / "analisis" / "salidas"

_IDENTIFICADOR = {
    "SARIMA": "sarima",
    "Prophet": "prophet",
    "XGBoost": "xgboost",
    "LSTM": "lstm",
    "GRU": "gru",
    "CNN-LSTM": "cnn_lstm",
}
_COLUMNA_PRED = {
    "SARIMA": "pred_sarima",
    "Prophet": "pred_prophet",
    "XGBoost": "pred_xgboost",
    "LSTM": "pred_lstm",
    "GRU": "pred_gru",
    "CNN-LSTM": "pred_cnn_lstm",
}


def cargar_predicciones_freeze(freeze: str) -> dict[str, pd.DataFrame]:
    datos = {}
    for metodo, identificador in _IDENTIFICADOR.items():
        ruta = SALIDA / f"predicciones__{identificador}__{freeze}.csv"
        d = pd.read_csv(ruta)
        d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.date
        datos[metodo] = d
    return datos


def soporte_comun(datos: dict[str, pd.DataFrame]) -> set[tuple]:
    """Interseccion de (route, dia_op) entre los seis metodos. Las dos
    referencias de media historica comparten el soporte de su metodo fuente
    (XGBoost / GRU) por construccion, ya que su columna ``pred_media`` vive en
    el mismo archivo de predicciones."""
    conjuntos = [set(zip(d["route"], d["dia_op"], strict=False)) for d in datos.values()]
    return set.intersection(*conjuntos)


def _restringir(d: pd.DataFrame, comun: set[tuple]) -> pd.DataFrame:
    mascara = [par in comun for par in zip(d["route"], d["dia_op"], strict=False)]
    return d[mascara]


def consolidar_freeze_nuevo(
    freeze: str, config: ConfiguracionEvaluacionComparativa
) -> dict[str, pd.DataFrame | set]:
    datos = cargar_predicciones_freeze(freeze)
    comun = soporte_comun(datos)

    fuentes: dict[str, tuple[pd.DataFrame, str]] = {
        metodo: (d, _COLUMNA_PRED[metodo]) for metodo, d in datos.items()
    }
    fuentes["Referencia (26s)"] = (datos["XGBoost"], "pred_media")
    fuentes["Referencia (52s)"] = (datos["GRU"], "pred_media")

    filas_global, filas_ruta, filas_tipo, filas_regimen = [], [], [], []

    for nombre, (d, col_pred) in fuentes.items():
        dr = _restringir(d, comun).dropna(subset=["real", col_pred])
        regimen = (
            dr["tipo_dia"]
            .isin(config.tipos_baja_frecuencia)
            .map({True: "raro", False: "ordinario"})
        )

        def _fila_base(grupo: pd.DataFrame, col_pred: str = col_pred) -> dict:
            m = calcular_metricas(
                grupo["real"].to_numpy(), grupo[col_pred].to_numpy(), config.umbral_mape
            )
            m["n_jornadas"] = grupo[["route", "dia_op"]].drop_duplicates().shape[0]
            return m

        filas_global.append({"metodo": nombre, **_fila_base(dr)})
        for ruta, grupo in dr.groupby("route"):
            filas_ruta.append({"metodo": nombre, "route": ruta, **_fila_base(grupo)})
        for tipo, grupo in dr.groupby("tipo_dia"):
            filas_tipo.append({"metodo": nombre, "tipo_dia": tipo, **_fila_base(grupo)})
        for reg, grupo in dr.groupby(regimen):
            filas_regimen.append({"metodo": nombre, "regimen": reg, **_fila_base(grupo)})

    return {
        "global": pd.DataFrame(filas_global),
        "por_ruta": pd.DataFrame(filas_ruta),
        "por_tipo_dia": pd.DataFrame(filas_tipo),
        "por_regimen": pd.DataFrame(filas_regimen),
        "soporte_comun": comun,
    }
