"""Prediccion de la jornada D+1 (seccion 3 del diseno).

- Franjas: las de D+1 dentro del horario operativo congelado, tal como las deja
  ``serie.construir_serie``. A diferencia del backtesting, que solo predecia las
  franjas observadas, aqui se predicen todas las del horario operativo (no hay
  franjas observadas de un dia futuro).
- XGBoost: rama XGBoost de ``modeling.hparam_search.reevaluacion.ejecutar_metodo``
  con ``seleccionar_features`` y ``ajustar_predecir_xgboost``; 26 semanas de
  entrenamiento antes de las 04:00 de D+1, las 2 ultimas para la parada
  temprana, hiperparametros de la busqueda y ``random_state = 42``.
- Referencia de 52 semanas: la formula del script 43 (media por tipo de dia y
  franja en la ventana, con la media de la ventana como respaldo).
- XGBoost se calcula siempre, tambien en regimen raro, para el historial.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.fits import ajustar_predecir_xgboost
from proyecto_grado.modeling.hparam_search.reevaluacion import _CAST
from proyecto_grado.modeling.hparam_search.runner import _preparar_ruta

REGIMEN_RARO, REGIMEN_ORDINARIO = "raro", "ordinario"


class ErrorPrediccion(RuntimeError):  # noqa: N818
    """No se puede predecir la jornada con el protocolo congelado."""


@dataclass(frozen=True)
class ParametrosPrediccion:
    rutas: tuple[int, ...]
    objetivo: str
    semanas_entrenamiento: int
    semanas_parada: int
    semanas_referencia: int
    tipos_raros: tuple[str, ...]
    min_franjas: int
    hiperparametros: dict

    def como_dict(self) -> dict:
        return {
            "rutas": list(self.rutas),
            "objetivo": self.objetivo,
            "semanas_entrenamiento": self.semanas_entrenamiento,
            "semanas_parada_temprana": self.semanas_parada,
            "semanas_referencia": self.semanas_referencia,
            "tipos_raros": list(self.tipos_raros),
            "min_franjas": self.min_franjas,
            "hiperparametros_xgboost": self.hiperparametros,
        }


def cargar_hiperparametros_xgboost(ruta: Path) -> dict:
    """Hiperparametros del trial seleccionado, con los tipos de reevaluacion._CAST."""
    trial = json.loads(Path(ruta).read_text(encoding="utf-8"))["trial_seleccionado"]
    return {campo: tipo(trial[campo]) for campo, tipo in _CAST["XGBoost"].items()}


def cargar_parametros(ruta_evaluacion: Path, ruta_hiperparametros: Path, semanas_ref: int):
    """Contrato de evaluacion comparativa (sin cambios) e hiperparametros de XGBoost."""
    ev = cargar_configuracion_evaluacion(ruta_evaluacion)
    m = ev.metodo("XGBoost")
    return ParametrosPrediccion(
        rutas=tuple(int(r) for r in ev.rutas),
        objetivo=ev.objetivo,
        semanas_entrenamiento=int(m.semanas_entrenamiento),
        semanas_parada=int(m.semanas_parada_temprana),
        semanas_referencia=int(semanas_ref),
        tipos_raros=tuple(ev.tipos_baja_frecuencia),
        min_franjas=int(ev.min_franjas),
        hiperparametros=cargar_hiperparametros_xgboost(ruta_hiperparametros),
    )


def corte_de(dia: date, inicio_jornada_h: int = 4) -> pd.Timestamp:
    """Inicio de la jornada (04:00): todo dato usado es anterior a este instante."""
    return pd.Timestamp(dia) + pd.Timedelta(hours=inicio_jornada_h)


def regimen(tipo_dia: pd.Series, tipos_raros: tuple[str, ...]) -> np.ndarray:
    return np.where(tipo_dia.isin(tipos_raros), REGIMEN_RARO, REGIMEN_ORDINARIO)


def franjas_de_jornada(serie: pd.DataFrame, dia: date, ruta: int) -> pd.DataFrame:
    """Franjas de la jornada en la serie (horario operativo), con dia_op y hora."""
    corte = corte_de(dia)
    t = serie[
        (serie["FK_RUTA"] == ruta)
        & (serie["timestamp"] >= corte)
        & (serie["timestamp"] < corte + pd.Timedelta(days=1))
    ].copy()
    t = t.sort_values("timestamp").reset_index(drop=True)
    t["dia_op"] = (t["timestamp"] - pd.Timedelta(hours=4)).dt.date
    t["hora"] = t["timestamp"].dt.strftime("%H:%M")
    return t


def referencia(d: pd.DataFrame, test: pd.DataFrame, objetivo: str, semanas: int, corte):
    """Formula de la referencia del script 43 (``referencia``), para una jornada."""
    ent = d[(d["timestamp"] >= corte - pd.Timedelta(weeks=semanas)) & (d["timestamp"] < corte)]
    medias = ent.groupby(["tipo_dia", "hora"])[objetivo].mean()
    idx = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
    valores = pd.Series(medias.reindex(idx).to_numpy())
    return valores.fillna(ent[objetivo].mean()).to_numpy(), valores.isna().to_numpy()


def predecir_jornada(serie: pd.DataFrame, dia: date, p: ParametrosPrediccion) -> pd.DataFrame:
    """pred_xgboost y ref52 para todas las franjas de ``dia`` de cada ruta.

    Solo usa filas de la serie anteriores a las 04:00 de ``dia`` para entrenar;
    de la jornada objetivo solo se leen sus variables predictoras.
    """
    corte = corte_de(dia)
    historia = serie[serie["timestamp"] < corte]
    filas = []
    for ruta in p.rutas:
        d = _preparar_ruta(historia, ruta, p.objetivo)
        if d.empty:
            raise ErrorPrediccion(f"Ruta {ruta}: sin historia antes de {corte}.")
        features = seleccionar_features(d)
        corte_parada = corte - pd.Timedelta(weeks=p.semanas_parada)
        train = d[d["timestamp"] >= corte - pd.Timedelta(weeks=p.semanas_entrenamiento)]
        fit_df = train[train["timestamp"] < corte_parada]
        stop_df = train[train["timestamp"] >= corte_parada]
        test = franjas_de_jornada(serie, dia, ruta)
        if test.empty:
            raise ErrorPrediccion(f"Ruta {ruta}: la serie no tiene franjas de {dia}.")
        if len(fit_df) < 500 or len(stop_df) == 0:
            raise ErrorPrediccion(
                f"Ruta {ruta}: entrenamiento insuficiente ({len(fit_df)} franjas de ajuste, "
                f"{len(stop_df)} de parada)."
            )
        pred, arboles = ajustar_predecir_xgboost(
            fit_df, stop_df, test, features, p.objetivo, p.hiperparametros
        )
        ref, sin_media = referencia(d, test, p.objetivo, p.semanas_referencia, corte)
        filas.append(
            pd.DataFrame(
                {
                    "route": ruta,
                    "dia_op": dia.isoformat(),
                    "timestamp": test["timestamp"].to_numpy(),
                    "hora": test["hora"].to_numpy(),
                    "tipo_dia": test["tipo_dia"].to_numpy(),
                    "pred_xgboost": pred.astype(float),
                    "ref52": ref.astype(float),
                    "ref52_sin_media": sin_media,
                    "variables_nulas": test[features].isna().sum(axis=1).to_numpy(),
                    "arboles": arboles,
                    "franjas_ajuste": len(fit_df),
                    "franjas_parada": len(stop_df),
                    "ultimo_dato": str(d["timestamp"].max()),
                }
            )
        )
    out = pd.concat(filas, ignore_index=True)
    out["regimen"] = regimen(out["tipo_dia"], p.tipos_raros)
    return out


def prediccion_final(pred: pd.DataFrame, factores: dict[int, float]) -> pd.DataFrame:
    """C3: XGBoost por el factor de su ruta en regimen ordinario; ref52 en raro."""
    out = pred.copy()
    out["factor"] = out["route"].map(factores).astype(float)
    if out["factor"].isna().any():
        raise ErrorPrediccion("Falta el factor de alguna ruta.")
    out["pred_final"] = np.where(
        out["regimen"] == REGIMEN_RARO, out["ref52"], out["pred_xgboost"] * out["factor"]
    )
    return out
