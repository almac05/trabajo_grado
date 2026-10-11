"""Desempeno del modelo en la jornada D (la que acaba de cerrar).

Compara los pasajeros reales de D (de la serie de la corrida) con la prediccion
EMITIDA para D la noche anterior (filas de origen ``piloto`` del historial de
solo agregar; ``pred_final``), por ruta, sobre las franjas de 30 min del
horario operativo que tienen real y prediccion.

No hay formulas nuevas: MAE, RMSE, WAPE, sesgo (pasajeros/franja) y MAPE
parcial salen de ``calcular_metricas`` (la misma funcion de la evaluacion
comparativa). El MAPE se calcula dos veces: con el umbral del capitulo
(real >= 10) y con umbral 1, que en conteos enteros equivale a real > 0.
SesgoPct = sesgo / demanda_media x 100 = (Sum pred - Sum real) / Sum real x 100.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from proyecto_grado.modeling.evaluation_aggregation import calcular_metricas
from proyecto_grado.piloto import correccion as corr

UMBRAL_MAPE_POSITIVO = 1.0  # conteos enteros: real >= 1 equivale a real > 0
ORIGEN_EMITIDO = "piloto"
COLUMNAS = [
    "fecha",
    "ruta",
    "grupo",
    "n_franjas",
    "mae",
    "rmse",
    "wape",
    "sesgo",
    "sesgo_pct",
    "mape_u10",
    "n_mape_u10",
    "mape_u1",
    "n_mape_u1",
    "total_real",
    "total_pred",
    "id_corrida_prediccion",
    "id_ejecucion",
]


def _f(x) -> float:
    return float(x) if x is not None and np.isfinite(x) else float("nan")


def evaluar_ruta(emitidas: pd.DataFrame, observadas: pd.DataFrame, umbral_mape: float) -> dict:
    """Metricas de una ruta y jornada, o ``{"motivo": ...}`` si no se puede evaluar."""
    if emitidas.empty:
        return {"motivo": "sin_prediccion_emitida"}
    if observadas.empty:
        return {"motivo": "sin_reales"}
    vigente = corr.emision_vigente(emitidas)
    u = vigente.merge(observadas, on=["route", "dia_op", "hora"], how="inner", validate="1:1")
    u = u.dropna(subset=["real", "pred_final"])
    if u.empty:
        return {"motivo": "sin_franjas_comunes"}
    real = u["real"].to_numpy(float)
    pred = u["pred_final"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        m10 = calcular_metricas(real, pred, umbral_mape)
        m1 = calcular_metricas(real, pred, UMBRAL_MAPE_POSITIVO)
    total_real = float(real.sum())
    sesgo_pct = 100 * m10["sesgo"] / m10["demanda_media"] if total_real > 0 else float("nan")
    return {
        "n_franjas": int(m10["n"]),
        "mae": _f(m10["mae"]),
        "rmse": _f(m10["rmse"]),
        "wape": _f(m10["wape"]) if total_real > 0 else float("nan"),
        "sesgo": _f(m10["sesgo"]),
        "sesgo_pct": _f(sesgo_pct),
        "mape_u10": _f(m10["mape_parcial"]),
        "n_mape_u10": int(m10["n_mape"]),
        "mape_u1": _f(m1["mape_parcial"]),
        "n_mape_u1": int(m1["n_mape"]),
        "total_real": total_real,
        "total_pred": float(pred.sum()),
        "id_corrida_prediccion": str(vigente["id_ejecucion"].iloc[0]),
    }


def evaluar_jornada(
    historial: pd.DataFrame | None,
    serie: pd.DataFrame,
    dia: date,
    rutas: tuple[int, ...],
    umbral_mape: float,
) -> dict[str, dict]:
    """Resultado por ruta (clave str) para la jornada ``dia``."""
    d = dia.isoformat()
    obs = corr.demanda_observada(serie)
    obs = obs[obs["dia_op"] == d]
    if historial is None or historial.empty:
        emitidas = pd.DataFrame(columns=corr.COLUMNAS)
    else:
        emitidas = historial[
            (historial["origen"] == ORIGEN_EMITIDO) & (historial["dia_op"].astype(str) == d)
        ]
    return {
        str(r): evaluar_ruta(
            emitidas[emitidas["route"].astype(int) == r], obs[obs["route"] == r], umbral_mape
        )
        for r in rutas
    }


def filas_indicadores(
    por_ruta: dict[str, dict], dia: date, grupo: str, id_ejecucion: str
) -> pd.DataFrame:
    """Una fila por ruta evaluada (las omitidas no generan fila)."""
    filas = [
        {
            "fecha": dia.isoformat(),
            "ruta": int(r),
            "grupo": grupo,
            **v,
            "id_ejecucion": id_ejecucion,
        }
        for r, v in por_ruta.items()
        if "motivo" not in v
    ]
    return pd.DataFrame(filas, columns=COLUMNAS)


def guardar_indicadores(directorio: Path, dia: date, filas: pd.DataFrame) -> Path:
    """indicadores/<D>.parquet con reemplazo atomico (una corrida posterior lo sobrescribe)."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / f"{dia.isoformat()}.parquet"
    temporal = ruta.with_name(ruta.name + ".tmp")
    filas.to_parquet(temporal, index=False)
    os.replace(temporal, ruta)
    return ruta
