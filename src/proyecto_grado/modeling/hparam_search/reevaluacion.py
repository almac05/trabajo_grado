"""Reejecuta la evaluacion comparativa (periodo canonico 2026-04-02 a
2026-06-10, `configs/modeling/evaluacion_comparativa.yaml`) aplicando a cada
metodo la configuracion seleccionada por la busqueda de hiperparametros.

Genera un freeze nuevo (identificador propio `freeze_YYYYMMDD_HHMMSS`, con
timestamp de ejecucion) sin sobrescribir los artefactos del freeze anterior
(`freeze_20260823_203700`): los CSV de salida usan el mismo directorio
(`analisis/salidas/`) pero el sufijo de version cambia.

No modifica ningun script de evaluacion comparativa
(`scripts/run_*_comparative_evaluation.py`) ni `evaluation_config.py` /
`evaluation_aggregation.py`: reproduce su misma logica de particion,
reentrenamiento y columnas de salida, parametrizada por los hiperparametros
seleccionados en vez de las constantes fijas de esos scripts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import (
    ConfiguracionEvaluacionComparativa,
    cargar_configuracion_evaluacion,
)
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
from proyecto_grado.modeling.hparam_search.runner import (
    _TIPO_ID_RED,
    _calendario_festivos,
    _dias_candidatos,
    _preparar_ruta,
    dispositivo,
)

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

_MAE_COL = {m: f"mae_{i}" for m, i in _IDENTIFICADOR.items()}
_SESGO_COL = {m: f"sesgo_{i}" for m, i in _IDENTIFICADOR.items()}
_RANGO_PRED_COL = {m: f"rango_pred_{i}" for m, i in _IDENTIFICADOR.items()}

_CAST = {
    "SARIMA": {"p": int, "q": int, "P": int, "Q": int},
    "Prophet": {
        "changepoint_prior_scale": float,
        "seasonality_prior_scale": float,
        "holidays_prior_scale": float,
        "seasonality_mode": str,
        "changepoint_range": float,
    },
    "XGBoost": {
        "max_depth": int,
        "min_child_weight": int,
        "learning_rate": float,
        "subsample": float,
        "colsample_bytree": float,
        "reg_lambda": float,
        "reg_alpha": float,
    },
    "LSTM": {"unidades": int, "lr": float, "paciencia": int},
    "GRU": {"unidades": int, "lr": float, "paciencia": int},
    "CNN-LSTM": {"unidades": int, "lr": float, "paciencia": int, "filtros": int, "nucleo": int},
}


def nuevo_freeze_id(cuando: pd.Timestamp | None = None) -> str:
    """Genera un identificador de freeze nuevo, formato freeze_AAAAMMDD_HHMMSS."""
    cuando = cuando or pd.Timestamp.now()
    return f"freeze_{cuando.strftime('%Y%m%d_%H%M%S')}"


def cargar_configuraciones_seleccionadas(directorio: Path) -> dict[str, dict]:
    """Lee seleccion__<id>.json de cada metodo y devuelve solo los
    hiperparametros (con el tipo correcto), descartando metricas/metadatos."""
    resultado: dict[str, dict] = {}
    for metodo, campos in _CAST.items():
        ruta = directorio / f"seleccion__{_IDENTIFICADOR[metodo]}.json"
        with ruta.open(encoding="utf-8") as f:
            payload = json.load(f)
        trial = payload["trial_seleccionado"]
        resultado[metodo] = {campo: tipo(trial[campo]) for campo, tipo in campos.items()}
    return resultado


def _artefacto(identificador: str, freeze: str, tipo: str) -> Path:
    return SALIDA / f"{tipo}__{identificador}__{freeze}.csv"


def ejecutar_metodo(
    metodo: str,
    params: dict,
    config: ConfiguracionEvaluacionComparativa,
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corre el walk-forward diario de ``metodo`` sobre el periodo canonico de
    evaluacion (``config.inicio``/``config.fin``), con los hiperparametros
    seleccionados. Devuelve (resumen, predicciones), mismo esquema de
    columnas que produce el script original de ese metodo."""
    metodo_cfg = config.metodo(metodo)
    target = config.objetivo
    col_pred = _COLUMNA_PRED[metodo]
    mae_col, sesgo_col, rango_col = _MAE_COL[metodo], _SESGO_COL[metodo], _RANGO_PRED_COL[metodo]

    inicio_test = pd.Timestamp(config.inicio)
    fin_test = pd.Timestamp(config.fin)
    semanas_entrenamiento = metodo_cfg.semanas_entrenamiento
    semanas_parada = metodo_cfg.semanas_parada_temprana
    min_franjas = config.min_franjas
    paso_muestreo = config.paso_muestreo
    tipos_festivos = config.tipos_baja_frecuencia

    resumen, predicciones = [], []

    for ruta in config.rutas:
        d = _preparar_ruta(df, ruta, target)
        dias = _dias_candidatos(d, inicio_test, fin_test, min_franjas, paso_muestreo)

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
                t0 = time.perf_counter()
                try:
                    if metodo == "SARIMA":
                        pred, aic = ajustar_predecir_sarima(train[target], len(test), params)
                    else:
                        pred = ajustar_predecir_prophet(train, test, festivos, target, params)
                        aic = None
                except Exception as exc:
                    print(f"  [{metodo}] ruta {ruta} {dia}: fallo el ajuste: {exc}")
                    continue
                segundos = time.perf_counter() - t0
                real = test[target].to_numpy()
                extra_resumen = {"aic": aic} if metodo == "SARIMA" else {}

            elif metodo == "XGBoost":
                corte_parada = inicio_dia - pd.Timedelta(weeks=semanas_parada)
                train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
                fit_df = train[train["timestamp"] < corte_parada]
                stop_df = train[train["timestamp"] >= corte_parada]
                test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
                if len(test) < min_franjas or len(fit_df) < 500 or len(stop_df) == 0:
                    continue
                tipo = test["tipo_dia"].iloc[0]
                t0 = time.perf_counter()
                pred, arboles = ajustar_predecir_xgboost(
                    fit_df, stop_df, test, features, target, params
                )
                segundos = time.perf_counter() - t0
                real = test[target].to_numpy()
                extra_resumen = {"arboles": arboles}

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
                dia_previo = dia - pd.Timedelta(days=1)
                prev = d[d["dia_op"] == dia_previo]
                if len(prev) < min_franjas:
                    continue
                tipo = test["tipo_dia"].iloc[0]
                seq, msk = secuencia_de(prev, target)
                cal = test.iloc[0][CALENDARIO].to_numpy(dtype=float)
                t0 = time.perf_counter()
                pred_full, epocas = entrenar_predecir_red(
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
                segundos = time.perf_counter() - t0
                n = min(len(test), PASOS)
                real = test[target].to_numpy()[:n]
                pred = pred_full[:n]
                test = test.iloc[:n]
                extra_resumen = {"epocas": epocas, "ejemplos_ajuste": len(ejemplos_ajuste[3])}

            # --- Referencia: media historica por tipo de dia y franja, misma ventana ---
            entrenamiento = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
            medias = entrenamiento.groupby(["tipo_dia", "hora"])[target].mean()
            idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
            pred_media = medias.reindex(idx).to_numpy()
            n_sin_media = pd.isna(pred_media).sum()
            pred_media = pd.Series(pred_media).fillna(entrenamiento[target].mean()).to_numpy()

            error = pred - real
            err_media = pred_media - real

            resumen.append(
                {
                    "route": ruta,
                    "dia_op": dia,
                    "tipo_dia": tipo,
                    "n": len(test),
                    "demanda_media": real.mean(),
                    mae_col: np.abs(error).mean(),
                    sesgo_col: error.mean(),
                    rango_col: pred.max() - pred.min(),
                    "rango_real": real.max() - real.min(),
                    "mae_media": np.abs(err_media).mean(),
                    "sesgo_media": err_media.mean(),
                    "celdas_sin_media": int(n_sin_media),
                    "segundos": segundos,
                    **extra_resumen,
                }
            )
            predicciones.append(
                pd.DataFrame(
                    {
                        "route": ruta,
                        "dia_op": dia,
                        "tipo_dia": tipo,
                        "hora": test["hora"].to_numpy(),
                        "real": real,
                        col_pred: pred,
                        "pred_media": pred_media,
                    }
                )
            )

    r = pd.DataFrame(resumen)
    p = (
        pd.concat(predicciones, ignore_index=True)
        if predicciones
        else pd.DataFrame(
            columns=["route", "dia_op", "tipo_dia", "hora", "real", col_pred, "pred_media"]
        )
    )
    return r, p


def ejecutar_freeze_nuevo(
    directorio_seleccion: Path,
    freeze: str | None = None,
    verbose: bool = True,
) -> dict:
    """Corre los seis metodos con sus configuraciones seleccionadas sobre el
    periodo canonico de evaluacion, persiste predicciones__/resumen__ bajo un
    freeze nuevo, y copias de compatibilidad *_multiples_dias.csv para
    SARIMA/Prophet/XGBoost (de las que dependen los cuadros de dia de semana,
    amplitud y jornadas festivas en analisis/14_cuadros_mecanismos.py)."""
    config = cargar_configuracion_evaluacion()
    freeze = freeze or nuevo_freeze_id()
    configuraciones = cargar_configuraciones_seleccionadas(directorio_seleccion)
    df = pd.read_parquet(config.ruta_dataset)

    artefactos = {}
    for metodo, params in configuraciones.items():
        if verbose:
            print(f"\n{'=' * 60}\n{metodo} (freeze {freeze})\n{'=' * 60}\nparams={params}")
        resumen, predicciones = ejecutar_metodo(metodo, params, config, df)
        identificador = _IDENTIFICADOR[metodo]

        ruta_resumen = _artefacto(identificador, freeze, "resumen")
        ruta_predicciones = _artefacto(identificador, freeze, "predicciones")
        SALIDA.mkdir(parents=True, exist_ok=True)
        resumen.to_csv(ruta_resumen, index=False)
        predicciones.to_csv(ruta_predicciones, index=False)
        artefactos[metodo] = {"resumen": ruta_resumen, "predicciones": ruta_predicciones}

        if identificador in ("sarima", "prophet", "xgboost"):
            ruta_multiples = SALIDA / f"{identificador}_multiples_dias.csv"
            resumen.to_csv(ruta_multiples, index=False)
            artefactos[metodo]["multiples_dias"] = ruta_multiples

        if verbose:
            print(f"jornadas: {resumen[['route', 'dia_op']].drop_duplicates().shape[0]}")
            print(f"guardado: {ruta_resumen.name}, {ruta_predicciones.name}")

    return {"freeze": freeze, "config": config, "artefactos": artefactos}
