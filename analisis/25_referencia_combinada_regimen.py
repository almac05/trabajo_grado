"""Predictor de referencia combinado: media historica de 26 semanas en
jornadas de regimen ordinario y de 52 semanas en jornadas de regimen
excepcional (asignado por tipo_dia), frente a XGBoost (configuracion
seleccionada por la busqueda de hiperparametros) y las dos referencias
simples (26s, 52s).

Se evalua en dos periodos:
  - Validacion de la busqueda de hiperparametros: 2025-12-25 a 2026-04-01.
    Todas las predicciones se calculan aqui mismo (no hay artefactos
    persistidos de ese periodo).
  - Evaluacion del freeze `freeze_20260922_203820`, restringida a sus 134
    jornadas comunes (`analisis/salidas/jornadas_comunes__freeze_20260922_203820.csv`).
    XGBoost y las dos referencias simples se leen de los artefactos ya
    persistidos de ese freeze (`predicciones__xgboost__...csv`,
    `predicciones__gru__...csv`); solo el predictor combinado se calcula de
    nuevo, sobre exactamente esas mismas jornadas.

No modifica ningun script existente ni ningun artefacto del freeze
`freeze_20260922_203820` (solo los lee).

Uso:
    python analisis/25_referencia_combinada_regimen.py
"""

from __future__ import annotations

import json

import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_aggregation import calcular_metricas
from proyecto_grado.modeling.evaluation_config import (
    ConfiguracionEvaluacionComparativa,
    cargar_configuracion_evaluacion,
)
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.fits import ajustar_predecir_xgboost
from proyecto_grado.modeling.hparam_search.reevaluacion import cargar_configuraciones_seleccionadas
from proyecto_grado.modeling.hparam_search.runner import _dias_candidatos, _preparar_ruta

SALIDA = PROJECT_ROOT / "analisis" / "salidas"
FREEZE_REEVALUACION = "freeze_20260922_203820"
SUFIJO = "referencia_combinada_regimen"

DIRECTORIO_SELECCION = SALIDA / "busqueda_hiperparametros"
VALIDACION_INICIO = pd.Timestamp("2025-12-25")
VALIDACION_FIN = pd.Timestamp("2026-04-01")

SEMANAS_ORDINARIO = 26
SEMANAS_EXCEPCIONAL = 52
SEMANAS_PARADA_XGB = 2  # igual que metodos_obligatorios.XGBoost.semanas_parada_temprana


def _regimen(tipo_dia: str, tipos_baja_frecuencia: tuple[str, ...]) -> str:
    return "raro" if tipo_dia in tipos_baja_frecuencia else "ordinario"


def _media_historica(train: pd.DataFrame, test: pd.DataFrame, target: str) -> "pd.Series[float]":
    medias = train.groupby(["tipo_dia", "hora"])[target].mean()
    idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
    pred = medias.reindex(idx).to_numpy()
    return pd.Series(pred).fillna(train[target].mean()).to_numpy()


def _calcular_periodo_validacion(
    config: ConfiguracionEvaluacionComparativa,
    df: pd.DataFrame,
    params_xgb: dict,
) -> pd.DataFrame:
    """Calcula, dia a dia, las cuatro predicciones (combinada, xgboost,
    referencia 26s, referencia 52s) sobre el periodo de validacion."""
    target = config.objetivo
    min_franjas = config.min_franjas
    paso_muestreo = config.paso_muestreo
    tipos_festivos = config.tipos_baja_frecuencia

    filas = []
    for ruta in config.rutas:
        d = _preparar_ruta(df, ruta, target)
        dias = _dias_candidatos(d, VALIDACION_INICIO, VALIDACION_FIN, min_franjas, paso_muestreo)
        features = seleccionar_features(d)

        for dia in dias:
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
            if len(test) < min_franjas:
                continue
            tipo = test["tipo_dia"].iloc[0]
            regimen = _regimen(tipo, tipos_festivos)
            semanas_combinada = SEMANAS_ORDINARIO if regimen == "ordinario" else SEMANAS_EXCEPCIONAL

            def _ventana(semanas: int) -> pd.DataFrame:
                inicio_train = inicio_dia - pd.Timedelta(weeks=semanas)
                return d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]

            train_combinada = _ventana(semanas_combinada)
            train_26 = _ventana(SEMANAS_ORDINARIO)
            train_52 = _ventana(SEMANAS_EXCEPCIONAL)
            if len(train_combinada) < 500 or len(train_26) < 500 or len(train_52) < 500:
                continue

            corte_parada = inicio_dia - pd.Timedelta(weeks=SEMANAS_PARADA_XGB)
            fit_df = train_26[train_26["timestamp"] < corte_parada]
            stop_df = train_26[train_26["timestamp"] >= corte_parada]
            if len(fit_df) < 500 or len(stop_df) == 0:
                continue

            pred_combinada = _media_historica(train_combinada, test, target)
            pred_ref26 = _media_historica(train_26, test, target)
            pred_ref52 = _media_historica(train_52, test, target)
            pred_xgboost, _arboles = ajustar_predecir_xgboost(
                fit_df, stop_df, test, features, target, params_xgb
            )

            filas.append(pd.DataFrame({
                "route": ruta, "dia_op": dia, "tipo_dia": tipo, "regimen": regimen,
                "hora": test["hora"].to_numpy(), "real": test[target].to_numpy(),
                "pred_combinada": pred_combinada,
                "pred_xgboost": pred_xgboost,
                "pred_ref26": pred_ref26,
                "pred_ref52": pred_ref52,
            }))

    return pd.concat(filas, ignore_index=True)


def _calcular_periodo_evaluacion(
    config: ConfiguracionEvaluacionComparativa,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula el predictor combinado sobre exactamente las 134 jornadas
    comunes del freeze de reevaluacion, y lo une con XGBoost y las dos
    referencias simples ya persistidas en ese freeze (solo lectura)."""
    target = config.objetivo
    tipos_festivos = config.tipos_baja_frecuencia

    comunes = pd.read_csv(SALIDA / f"jornadas_comunes__{FREEZE_REEVALUACION}.csv")
    comunes["dia_op"] = pd.to_datetime(comunes["dia_op"]).dt.date
    dias_por_ruta: dict[int, list] = {
        ruta: sorted(g["dia_op"]) for ruta, g in comunes.groupby("route")
    }

    filas = []
    for ruta, dias in dias_por_ruta.items():
        d = _preparar_ruta(df, ruta, target)
        for dia in dias:
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
            if test.empty:
                continue
            tipo = test["tipo_dia"].iloc[0]
            regimen = _regimen(tipo, tipos_festivos)
            semanas_combinada = SEMANAS_ORDINARIO if regimen == "ordinario" else SEMANAS_EXCEPCIONAL
            inicio_train = inicio_dia - pd.Timedelta(weeks=semanas_combinada)
            train_combinada = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
            if len(train_combinada) < 500:
                continue
            pred_combinada = _media_historica(train_combinada, test, target)
            filas.append(pd.DataFrame({
                "route": ruta, "dia_op": dia, "tipo_dia": tipo, "regimen": regimen,
                "hora": test["hora"].to_numpy(), "real": test[target].to_numpy(),
                "pred_combinada": pred_combinada,
            }))
    combinada = pd.concat(filas, ignore_index=True)

    xgb_freeze = pd.read_csv(SALIDA / f"predicciones__xgboost__{FREEZE_REEVALUACION}.csv")
    xgb_freeze["dia_op"] = pd.to_datetime(xgb_freeze["dia_op"]).dt.date
    gru_freeze = pd.read_csv(SALIDA / f"predicciones__gru__{FREEZE_REEVALUACION}.csv")
    gru_freeze["dia_op"] = pd.to_datetime(gru_freeze["dia_op"]).dt.date

    xgb_freeze = xgb_freeze.rename(columns={"pred_media": "pred_ref26"})
    gru_freeze = gru_freeze.rename(columns={"pred_media": "pred_ref52"})[
        ["route", "dia_op", "hora", "pred_ref52"]
    ]

    combinado = combinada.merge(
        xgb_freeze[["route", "dia_op", "hora", "pred_xgboost", "pred_ref26"]],
        on=["route", "dia_op", "hora"], how="inner",
    ).merge(gru_freeze, on=["route", "dia_op", "hora"], how="inner")
    return combinado


def _tabla_metricas(datos: pd.DataFrame, config: ConfiguracionEvaluacionComparativa) -> pd.DataFrame:
    """Global, por ruta y por regimen, para las cuatro fuentes."""
    fuentes = {
        "Combinada (26s/52s por regimen)": "pred_combinada",
        "XGBoost": "pred_xgboost",
        "Referencia (26s)": "pred_ref26",
        "Referencia (52s)": "pred_ref52",
    }
    filas = []
    for nombre, columna in fuentes.items():
        dr = datos.dropna(subset=["real", columna])

        def _fila(grupo: pd.DataFrame, **claves) -> dict:
            m = calcular_metricas(grupo["real"].to_numpy(), grupo[columna].to_numpy(), config.umbral_mape)
            n_jornadas = grupo[["route", "dia_op"]].drop_duplicates().shape[0]
            return {"metodo": nombre, **claves, "n_jornadas": n_jornadas, **m}

        filas.append(_fila(dr, desagregacion="global"))
        for ruta, grupo in dr.groupby("route"):
            filas.append(_fila(grupo, desagregacion="por_ruta", route=ruta))
        for regimen, grupo in dr.groupby("regimen"):
            filas.append(_fila(grupo, desagregacion="por_regimen", regimen=regimen))
    return pd.DataFrame(filas)


def main() -> None:
    config = cargar_configuracion_evaluacion()
    df = pd.read_parquet(config.ruta_dataset)
    configuraciones = cargar_configuraciones_seleccionadas(DIRECTORIO_SELECCION)
    params_xgb = configuraciones["XGBoost"]

    print(f"Parametros XGBoost (seleccionados por la busqueda): {params_xgb}\n")

    print("Calculando periodo de validacion (2025-12-25 a 2026-04-01)...")
    datos_validacion = _calcular_periodo_validacion(config, df, params_xgb)
    tabla_validacion = _tabla_metricas(datos_validacion, config)

    print("Calculando periodo de evaluacion "
          f"(freeze {FREEZE_REEVALUACION}, 134 jornadas comunes)...")
    datos_evaluacion = _calcular_periodo_evaluacion(config, df)
    tabla_evaluacion = _tabla_metricas(datos_evaluacion, config)

    ruta_validacion_obs = SALIDA / f"observaciones__{SUFIJO}__validacion.csv"
    ruta_validacion_met = SALIDA / f"metricas__{SUFIJO}__validacion.csv"
    ruta_evaluacion_obs = SALIDA / f"observaciones__{SUFIJO}__{FREEZE_REEVALUACION}.csv"
    ruta_evaluacion_met = SALIDA / f"metricas__{SUFIJO}__{FREEZE_REEVALUACION}.csv"

    datos_validacion.to_csv(ruta_validacion_obs, index=False)
    tabla_validacion.round(4).to_csv(ruta_validacion_met, index=False)
    datos_evaluacion.to_csv(ruta_evaluacion_obs, index=False)
    tabla_evaluacion.round(4).to_csv(ruta_evaluacion_met, index=False)

    manifiesto = {
        "freeze_reevaluacion_referencia": FREEZE_REEVALUACION,
        "periodo_validacion": {"inicio": "2025-12-25", "fin": "2026-04-01"},
        "params_xgboost_usados": params_xgb,
        "n_jornadas_validacion": datos_validacion[["route", "dia_op"]].drop_duplicates().shape[0],
        "n_jornadas_evaluacion": datos_evaluacion[["route", "dia_op"]].drop_duplicates().shape[0],
        "artefactos": {
            "observaciones_validacion": str(ruta_validacion_obs),
            "metricas_validacion": str(ruta_validacion_met),
            "observaciones_evaluacion": str(ruta_evaluacion_obs),
            "metricas_evaluacion": str(ruta_evaluacion_met),
        },
    }
    ruta_manifiesto = SALIDA / f"manifiesto__{SUFIJO}.json"
    with ruta_manifiesto.open("w", encoding="utf-8") as f:
        json.dump(manifiesto, f, indent=2, ensure_ascii=False, default=str)

    pd.set_option("display.width", 200)
    print(f"\n{'=' * 70}\nVALIDACION 2025-12-25 a 2026-04-01 "
          f"({manifiesto['n_jornadas_validacion']} jornadas)\n{'=' * 70}")
    print(tabla_validacion.round(2).to_string(index=False))

    print(f"\n{'=' * 70}\nEVALUACION freeze {FREEZE_REEVALUACION} "
          f"({manifiesto['n_jornadas_evaluacion']} jornadas)\n{'=' * 70}")
    print(tabla_evaluacion.round(2).to_string(index=False))

    print(f"\nArtefactos:")
    for nombre, ruta in manifiesto["artefactos"].items():
        print(f"  {nombre}: {ruta}")
    print(f"  manifiesto: {ruta_manifiesto}")


if __name__ == "__main__":
    main()
