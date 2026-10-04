"""Persistencia de artefactos de la busqueda: espacio de busqueda, tabla
completa de configuraciones probadas y configuracion seleccionada, por
metodo. Vive fuera del arbol de artefactos de la evaluacion comparativa
(``analisis/salidas/``) para no interferir con el freeze existente.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from proyecto_grado.modeling.hparam_search.spaces import ESPACIOS_POR_METODO, FIJOS_POR_METODO

_IDENTIFICADOR = {
    "SARIMA": "sarima",
    "Prophet": "prophet",
    "XGBoost": "xgboost",
    "LSTM": "lstm",
    "GRU": "gru",
    "CNN-LSTM": "cnn_lstm",
}


def _slug(metodo: str) -> str:
    return _IDENTIFICADOR[metodo]


def guardar_espacio_busqueda(metodo: str, n_iter: int, semilla: int, directorio: Path) -> Path:
    payload = {
        "metodo": metodo,
        "n_iter": n_iter,
        "semilla": semilla,
        "espacio": {nombre: list(dist) for nombre, dist in ESPACIOS_POR_METODO[metodo].items()},
        "fijos": FIJOS_POR_METODO[metodo],
    }
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / f"espacio__{_slug(metodo)}.json"
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    return ruta


def guardar_tabla_configuraciones(metodo: str, tabla: pd.DataFrame, directorio: Path) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / f"configuraciones__{_slug(metodo)}.csv"
    tabla.to_csv(ruta, index=False)
    return ruta


def guardar_configuracion_seleccionada(metodo: str, mejor: dict, directorio: Path) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / f"seleccion__{_slug(metodo)}.json"
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(mejor, f, indent=2, ensure_ascii=False, default=str)
    return ruta
