"""Recorrido walk-forward sobre el periodo de validacion, para un metodo y
una configuracion de hiperparametros dados.

Reproduce el mismo protocolo de particiones y reentrenamiento que usan los
scripts de evaluacion comparativa (ventana deslizante de
``semanas_entrenamiento``, reentrenamiento diario, mismo corte de parada
temprana), aplicado al periodo de validacion en vez del periodo de
evaluacion. No lee ni escribe ningun artefacto de la evaluacion comparativa.
"""

from __future__ import annotations

import time
from functools import cache

import pandas as pd

from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.fits import (
    CALENDARIO,
    PASOS,
    ajustar_predecir_prophet,
    ajustar_predecir_sarima,
    ajustar_predecir_xgboost,
    construir_ejemplos,
    entrenar_predecir_red,
    secuencia_de,
)
from proyecto_grado.modeling.hparam_search.search_config import (
    ConfiguracionBusquedaHiperparametros,
)


@cache
def dispositivo():
    """Dispositivo de torch para las redes; torch se importa solo al usarlas."""
    import torch

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def __getattr__(nombre: str):
    # Compatibilidad: ``DISPOSITIVO`` se resuelve al primer acceso (PEP 562).
    if nombre == "DISPOSITIVO":
        return dispositivo()
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


_TIPO_ID_RED = {"LSTM": "lstm", "GRU": "gru", "CNN-LSTM": "cnn_lstm"}


def _preparar_ruta(df: pd.DataFrame, ruta: int, target: str) -> pd.DataFrame:
    d = df[(df["FK_RUTA"] == ruta) & df[target].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")
    return d


def _dias_candidatos(
    d: pd.DataFrame, inicio: pd.Timestamp, fin: pd.Timestamp, min_franjas: int, paso_muestreo: int
) -> list:
    conteo = d.groupby("dia_op").size()
    candidatos = [
        dia for dia, n in conteo.items() if inicio.date() <= dia <= fin.date() and n >= min_franjas
    ]
    return sorted(candidatos)[::paso_muestreo]


def _calendario_festivos(d: pd.DataFrame, tipos_festivos: tuple[str, ...]) -> pd.DataFrame:
    fest = d[d["tipo_dia"].isin(tipos_festivos)].copy()
    fest["fecha"] = (fest["timestamp"] - pd.Timedelta(hours=4)).dt.normalize()
    return (
        fest[["tipo_dia", "fecha"]]
        .drop_duplicates()
        .rename(columns={"tipo_dia": "holiday", "fecha": "ds"})
        .reset_index(drop=True)
    )


def evaluar_configuracion(
    metodo: str,
    params: dict,
    config: ConfiguracionBusquedaHiperparametros,
    df: pd.DataFrame | None = None,
    dias_limite: int | None = None,
) -> tuple[pd.DataFrame, float]:
    """Corre el walk-forward diario sobre el periodo de validacion.

    Devuelve las observaciones agrupadas (``route``, ``dia_op``, ``tipo_dia``,
    ``real``, ``pred``) y el tiempo total en segundos. ``dias_limite`` acota
    el numero de jornadas por ruta -- solo para calibracion de tiempos, no se
    usa en la busqueda completa.
    """
    metodo_eval = config.evaluacion.metodo(metodo)
    target = config.evaluacion.objetivo
    if df is None:
        df = pd.read_parquet(config.evaluacion.ruta_dataset)

    inicio_val = pd.Timestamp(config.inicio_validacion)
    fin_val = pd.Timestamp(config.fin_validacion)
    semanas_entrenamiento = metodo_eval.semanas_entrenamiento
    semanas_parada = metodo_eval.semanas_parada_temprana
    min_franjas = config.evaluacion.min_franjas
    paso_muestreo = config.evaluacion.paso_muestreo
    tipos_festivos = config.evaluacion.tipos_baja_frecuencia

    filas = []
    t_inicio = time.perf_counter()

    for ruta in config.evaluacion.rutas:
        d = _preparar_ruta(df, ruta, target)
        dias = _dias_candidatos(d, inicio_val, fin_val, min_franjas, paso_muestreo)
        if dias_limite is not None:
            dias = dias[:dias_limite]

        features = seleccionar_features(d) if metodo == "XGBoost" else None
        festivos = _calendario_festivos(d, tipos_festivos) if metodo == "Prophet" else None

        for dia in dias:
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            inicio_train = inicio_dia - pd.Timedelta(weeks=semanas_entrenamiento)

            if metodo in ("SARIMA", "Prophet"):
                train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
                test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
                if len(test) < min_franjas or len(train) < 500:
                    continue
                tipo = test["tipo_dia"].iloc[0]
                try:
                    if metodo == "SARIMA":
                        pred, _aic = ajustar_predecir_sarima(train[target], len(test), params)
                    else:
                        pred = ajustar_predecir_prophet(train, test, festivos, target, params)
                except Exception:
                    continue
                real = test[target].to_numpy()

            elif metodo == "XGBoost":
                corte_parada = inicio_dia - pd.Timedelta(weeks=semanas_parada)
                train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
                fit_df = train[train["timestamp"] < corte_parada]
                stop_df = train[train["timestamp"] >= corte_parada]
                test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
                if len(test) < min_franjas or len(fit_df) < 500 or len(stop_df) == 0:
                    continue
                tipo = test["tipo_dia"].iloc[0]
                pred, _arboles = ajustar_predecir_xgboost(
                    fit_df, stop_df, test, features, target, params
                )
                real = test[target].to_numpy()

            else:  # LSTM / GRU / CNN-LSTM
                tipo_id = _TIPO_ID_RED[metodo]
                corte_parada = inicio_dia - pd.Timedelta(weeks=semanas_parada)
                ajuste = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < corte_parada)]
                parada = d[(d["timestamp"] >= corte_parada) & (d["timestamp"] < inicio_dia)]
                test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
                if len(test) < min_franjas:
                    continue

                ejemplos_ajuste = construir_ejemplos(ajuste, target, min_franjas)
                ejemplos_parada = construir_ejemplos(parada, target, min_franjas)
                if len(ejemplos_ajuste[3]) < 50 or len(ejemplos_parada[3]) < 3:
                    continue

                tipo = test["tipo_dia"].iloc[0]
                dia_previo = dia - pd.Timedelta(days=1)
                prev = d[d["dia_op"] == dia_previo]
                if len(prev) < min_franjas:
                    continue

                seq, msk = secuencia_de(prev, target)
                cal = test.iloc[0][CALENDARIO].to_numpy(dtype=float)
                pred_full, _epocas = entrenar_predecir_red(
                    tipo_id,
                    ejemplos_ajuste,
                    ejemplos_parada,
                    seq,
                    msk,
                    cal,
                    len(CALENDARIO),
                    params,
                    dispositivo(),
                )
                n = min(len(test), PASOS)
                real = test[target].to_numpy()[:n]
                pred = pred_full[:n]

            filas.append(
                pd.DataFrame(
                    {"route": ruta, "dia_op": dia, "tipo_dia": tipo, "real": real, "pred": pred}
                )
            )

    segundos = time.perf_counter() - t_inicio
    if not filas:
        return pd.DataFrame(columns=["route", "dia_op", "tipo_dia", "real", "pred"]), segundos
    return pd.concat(filas, ignore_index=True), segundos
