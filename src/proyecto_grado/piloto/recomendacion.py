"""Modulo de recomendacion sin cambios (seccion 5 del diseno).

``generar_recomendacion`` con la configuracion de la piloto
(configs/dispatch/recomendacion_piloto.yaml: sin tope y con disponibilidad
habitual), los parametros calibrados del freeze y su capacidad conjunta. La
factibilidad se aplica por fecha a las dos rutas juntas. La disponibilidad
habitual se calcula con los despachos por franja de la serie anteriores al
corte, como en scripts/muestra_planilla_20261001.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from proyecto_grado.dispatch.config import (
    ConfiguracionRecomendacion,
    cargar_configuracion_recomendacion,
)
from proyecto_grado.dispatch.parametros import ParametrosCalibracion
from proyecto_grado.dispatch.planilla import divisor_y_criterio
from proyecto_grado.dispatch.reglas import disponibilidad_habitual, generar_recomendacion

COLUMNA_DISPONIBILIDAD = "en_disponibilidad"


@dataclass(frozen=True)
class Modulo:
    config: ConfiguracionRecomendacion
    parametros: ParametrosCalibracion

    def como_dict(self) -> dict:
        disp = self.config.disponibilidad_habitual
        return {
            "freeze_parametros": self.config.freeze,
            "capacidad": self.parametros.capacidad,
            "jornada_capacidad": self.parametros.jornada_capacidad.isoformat(),
            "politica_festivos": self.config.politica_festivos,
            "usar_tope_carga": self.config.usar_tope_carga,
            "servicio_minimo": self.config.servicio_minimo,
            "disponibilidad_habitual": (
                None
                if disp is None
                else {"umbral": disp.umbral, "ventana_semanas": disp.ventana_semanas}
            ),
        }


def cargar_modulo(ruta_config: Path, ruta_parametros: Path, ruta_manifiesto: Path) -> Modulo:
    cfg = cargar_configuracion_recomendacion(ruta_config)
    for ruta in (ruta_parametros, ruta_manifiesto):
        if cfg.freeze not in Path(ruta).name:
            raise ValueError(f"{Path(ruta).name} no corresponde al freeze {cfg.freeze}.")
    man = json.loads(Path(ruta_manifiesto).read_text(encoding="utf-8"))["parametros"]
    parametros = ParametrosCalibracion(
        tabla=pd.read_csv(ruta_parametros),
        capacidad=int(man["capacidad"]),
        jornada_capacidad=date.fromisoformat(man["jornada_capacidad"]),
    )
    return Modulo(cfg, parametros)


def historial_despachos(serie: pd.DataFrame, corte: pd.Timestamp) -> pd.DataFrame:
    """Despachos por ruta, jornada y franja de la serie anteriores al corte."""
    h = serie[serie["timestamp"] < corte]
    return pd.DataFrame(
        {
            "route": h["FK_RUTA"].astype(int).to_numpy(),
            "dia_op": (h["timestamp"] - pd.Timedelta(hours=4)).dt.date.to_numpy(),
            "tipo_dia": h["tipo_dia"].to_numpy(),
            "hora": h["timestamp"].dt.strftime("%H:%M").to_numpy(),
            "despachos": h["despachos_count_real"].fillna(0).to_numpy(),
        }
    )


def recomendar(
    pred: pd.DataFrame, serie: pd.DataFrame, corte: pd.Timestamp, modulo: Modulo
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recomendacion por franja de la jornada y ajuste de factibilidad por fecha."""
    cfg = modulo.config
    base = pred[["route", "dia_op", "hora", "tipo_dia", "regimen"]].assign(
        demanda_predicha=pred["pred_final"].to_numpy()
    )
    columna = None
    if cfg.disponibilidad_habitual is not None:
        historial = historial_despachos(serie, corte)
        if len(historial) and historial["dia_op"].max() >= pd.Timestamp(corte).date():
            raise ValueError("El historial de despachos incluye la jornada objetivo.")
        base = disponibilidad_habitual(
            base,
            historial,
            cfg.disponibilidad_habitual.umbral,
            cfg.disponibilidad_habitual.ventana_semanas,
        )
        columna = COLUMNA_DISPONIBILIDAD
    rec, ajuste = generar_recomendacion(
        base,
        modulo.parametros,
        cfg.bloques,
        cfg.politica_festivos,
        cfg.usar_tope_carga,
        cfg.servicio_minimo,
        columna_disponibilidad=columna,
    )
    rec["divisor_usado"], rec["criterio"] = divisor_y_criterio(
        rec, cfg.usar_tope_carga, cfg.servicio_minimo
    )
    if COLUMNA_DISPONIBILIDAD not in rec:
        rec[COLUMNA_DISPONIBILIDAD] = True
    return rec, ajuste
