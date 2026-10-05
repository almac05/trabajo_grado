"""Predictor mixto por regimen: XGBoost en regimen ordinario y referencia en raro.

La referencia es la media historica de 52 semanas (``pred_media`` del artefacto
de GRU del freeze). Si a una franja ordinaria le falta la prediccion de XGBoost,
se usa la referencia como respaldo y se registra.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd

from proyecto_grado.dispatch.parametros import REGIMEN_RARO, ErrorDatosRecomendacion, regimen_de

logger = logging.getLogger(__name__)

CLAVES_FRANJA = ["route", "dia_op", "hora"]
FUENTE_XGBOOST = "xgboost"
FUENTE_REFERENCIA = "referencia"
FUENTE_RESPALDO = "respaldo_referencia"


def construir_prediccion_mixta(
    xgboost: pd.DataFrame,
    referencia: pd.DataFrame,
    jornadas: pd.DataFrame,
    tipos_raros: Sequence[str],
    columna_xgboost: str = "pred_xgboost",
    columna_referencia: str = "pred_media",
) -> pd.DataFrame:
    """Demanda predicha por franja de las jornadas comunes.

    Las franjas son las del artefacto de referencia restringidas a ``jornadas``
    (pares ruta, jornada); la prediccion de XGBoost se une por ruta, jornada y hora.
    """
    jornadas = jornadas[["route", "dia_op"]].astype({"route": int, "dia_op": str})
    base = referencia[[*CLAVES_FRANJA, "tipo_dia", "real", columna_referencia]].astype(
        {"route": int, "dia_op": str, "hora": str}
    )
    base = base.merge(jornadas, on=["route", "dia_op"], how="inner")
    if base.duplicated(CLAVES_FRANJA).any():
        raise ErrorDatosRecomendacion("El artefacto de referencia tiene franjas duplicadas.")
    jornadas_sin_franjas = len(jornadas) - len(base[["route", "dia_op"]].drop_duplicates())
    if jornadas_sin_franjas:
        logger.warning("%d jornadas comunes sin franjas en la referencia.", jornadas_sin_franjas)

    xgb = xgboost[[*CLAVES_FRANJA, columna_xgboost]].astype(
        {"route": int, "dia_op": str, "hora": str}
    )
    xgb = xgb.merge(jornadas, on=["route", "dia_op"], how="inner")
    if xgb.duplicated(CLAVES_FRANJA).any():
        raise ErrorDatosRecomendacion("El artefacto de XGBoost tiene franjas duplicadas.")
    pred = base.merge(xgb, on=CLAVES_FRANJA, how="left", validate="1:1")
    pred = pred.rename(
        columns={columna_xgboost: "pred_xgboost", columna_referencia: "pred_referencia"}
    )
    pred["regimen"] = regimen_de(pred["tipo_dia"], tipos_raros)

    es_raro = pred["regimen"] == REGIMEN_RARO
    falta_xgb = pred["pred_xgboost"].isna()
    pred["fuente"] = np.select(
        [es_raro, falta_xgb], [FUENTE_REFERENCIA, FUENTE_RESPALDO], default=FUENTE_XGBOOST
    )
    pred["demanda_predicha"] = pred["pred_referencia"].where(
        es_raro | falta_xgb, pred["pred_xgboost"]
    )
    respaldos = pred[pred["fuente"] == FUENTE_RESPALDO]
    if len(respaldos):
        logger.warning(
            "%d franjas ordinarias sin prediccion de XGBoost; se usa la referencia: %s",
            len(respaldos),
            respaldos[CLAVES_FRANJA].to_dict("records"),
        )
    else:
        logger.info("Todas las franjas ordinarias tienen prediccion de XGBoost.")
    if pred["demanda_predicha"].isna().any():
        raise ErrorDatosRecomendacion("Hay franjas sin prediccion de XGBoost ni de referencia.")
    logger.info(
        "Prediccion mixta: %d franjas en %d jornadas (%s).",
        len(pred),
        len(pred[["route", "dia_op"]].drop_duplicates()),
        pred["fuente"].value_counts().to_dict(),
    )
    columnas = [
        *CLAVES_FRANJA,
        "tipo_dia",
        "regimen",
        "real",
        "pred_xgboost",
        "pred_referencia",
        "fuente",
        "demanda_predicha",
    ]
    return pred[columnas].sort_values(CLAVES_FRANJA).reset_index(drop=True)


def verificar_contra_combinada(
    prediccion: pd.DataFrame, observaciones: pd.DataFrame, tolerancia: float = 1e-6
) -> dict[str, int | float | bool]:
    """Compara la prediccion mixta con las observaciones del script 25.

    ``pred_combinada`` del script 25 usa la referencia de 26 semanas en regimen
    ordinario y la de 52 en raro, de modo que solo coincide con la prediccion
    mixta en regimen raro. La verificacion es por componente: mismas franjas y
    regimen; en raro, demanda predicha igual a ``pred_combinada`` y ``pred_ref52``;
    en ordinario, igual a la columna ``pred_xgboost`` del script 25 (o a
    ``pred_ref52`` en las franjas de respaldo); y referencia igual a ``pred_ref52``
    en todas las franjas. Se informa tambien la diferencia con ``pred_combinada``
    en ordinario, que no es un error.
    """
    obs = observaciones[
        [*CLAVES_FRANJA, "regimen", "real", "pred_combinada", "pred_xgboost", "pred_ref52"]
    ].astype({"route": int, "dia_op": str, "hora": str})
    unido = prediccion.merge(
        obs, on=CLAVES_FRANJA, how="outer", suffixes=("", "_25"), indicator=True
    )
    ambos = unido[unido["_merge"] == "both"]
    raro = ambos[ambos["regimen"] == REGIMEN_RARO]
    ordinario = ambos[ambos["regimen"] != REGIMEN_RARO]
    esperado_ordinario = ordinario["pred_xgboost_25"].where(
        ordinario["fuente"] != FUENTE_RESPALDO, ordinario["pred_ref52"]
    )

    def _maximo(serie: pd.Series) -> float:
        return float(serie.abs().max()) if len(serie) else 0.0

    def _distintas(serie: pd.Series) -> int:
        return int((serie.abs() > tolerancia).sum())

    dif_raro_combinada = raro["demanda_predicha"] - raro["pred_combinada"]
    dif_raro_ref52 = raro["demanda_predicha"] - raro["pred_ref52"]
    dif_ordinario = ordinario["demanda_predicha"] - esperado_ordinario
    dif_referencia = ambos["pred_referencia"] - ambos["pred_ref52"]
    dif_ordinario_combinada = ordinario["demanda_predicha"] - ordinario["pred_combinada"]
    resultado: dict[str, int | float | bool] = {
        "franjas_modulo": len(prediccion),
        "franjas_script_25": len(obs),
        "franjas_comunes": len(ambos),
        "solo_modulo": int((unido["_merge"] == "left_only").sum()),
        "solo_script_25": int((unido["_merge"] == "right_only").sum()),
        "regimen_distinto": int((ambos["regimen"] != ambos["regimen_25"]).sum()),
        "max_dif_real": _maximo(ambos["real"] - ambos["real_25"]),
        "franjas_raras": len(raro),
        "raro_max_dif_pred_combinada": _maximo(dif_raro_combinada),
        "raro_distintas_pred_combinada": _distintas(dif_raro_combinada),
        "raro_distintas_pred_ref52": _distintas(dif_raro_ref52),
        "franjas_ordinarias": len(ordinario),
        "ordinario_max_dif_pred_xgboost": _maximo(dif_ordinario),
        "ordinario_distintas_pred_xgboost": _distintas(dif_ordinario),
        "referencia_distintas_pred_ref52": _distintas(dif_referencia),
        "ordinario_max_dif_pred_combinada_informativo": _maximo(dif_ordinario_combinada),
        "tolerancia": tolerancia,
    }
    resultado["coincide"] = bool(
        resultado["solo_modulo"] == 0
        and resultado["solo_script_25"] == 0
        and resultado["regimen_distinto"] == 0
        and resultado["raro_distintas_pred_combinada"] == 0
        and resultado["raro_distintas_pred_ref52"] == 0
        and resultado["ordinario_distintas_pred_xgboost"] == 0
        and resultado["referencia_distintas_pred_ref52"] == 0
    )
    nivel = logging.INFO if resultado["coincide"] else logging.WARNING
    logger.log(nivel, "Verificacion contra el script 25: %s", resultado)
    return resultado
