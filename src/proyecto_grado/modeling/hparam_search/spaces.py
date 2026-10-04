"""Espacios de busqueda y muestreo aleatorio para los seis metodos.

Cada distribucion se declara como una tupla ``(tipo, *args)``:

- ``("randint", low, high)``       entero uniforme en ``[low, high]`` (inclusivo)
- ``("uniform", low, high)``       real uniforme en ``[low, high]``
- ``("loguniform", low, high)``    real uniforme en escala logaritmica
- ``("choice", valores)``          valor discreto entre ``valores``

Los hiperparametros que la propuesta revisada fija (no se buscan) quedan
documentados como comentario junto a cada espacio, no como entradas del dict.
"""

from __future__ import annotations

import numpy as np

Distribucion = tuple
EspacioBusqueda = dict[str, Distribucion]

# SARIMA: d y D quedan fijos en los valores actuales (d=0, D=0) y el periodo
# estacional se mantiene en s=27. Solo se buscan las ordenes p, q, P, Q.
#
# Acotado tras medir el costo real de una corrida: con s=27, P=2 o Q=2
# disparan el ajuste MLE muy por encima de lo calibrado (~121 s/ajuste
# sostenido con P,Q<=2, frente a 9.55 s/ajuste en el punto de referencia
# p=2,q=1,P=1,Q=1). Se acota P,Q<=1 y p,q<=2 para mantener el costo por
# ajuste cercano al de la configuracion de referencia, que sigue dentro del
# espacio acotado.
ESPACIO_SARIMA: EspacioBusqueda = {
    "p": ("randint", 0, 2),
    "q": ("randint", 0, 2),
    "P": ("randint", 0, 1),
    "Q": ("randint", 0, 1),
}
SARIMA_FIJOS = {"d": 0, "D": 0, "s": 27}

ESPACIO_PROPHET: EspacioBusqueda = {
    "changepoint_prior_scale": ("loguniform", 0.001, 0.5),
    "seasonality_prior_scale": ("loguniform", 0.01, 10.0),
    "holidays_prior_scale": ("loguniform", 0.01, 10.0),
    "seasonality_mode": ("choice", ["additive", "multiplicative"]),
    "changepoint_range": ("uniform", 0.8, 0.95),
}

# XGBoost: early_stopping_rounds queda fijo en 50 (valor de produccion) y se
# saca del espacio. objective, eval_metric, n_estimators (techo) y
# random_state tambien quedan fijos, como en PARAMS_XGB.
ESPACIO_XGBOOST: EspacioBusqueda = {
    "max_depth": ("randint", 3, 9),
    "min_child_weight": ("randint", 1, 10),
    "learning_rate": ("loguniform", 0.01, 0.3),
    "subsample": ("uniform", 0.6, 1.0),
    "colsample_bytree": ("uniform", 0.6, 1.0),
    "reg_lambda": ("loguniform", 0.1, 10.0),
    "reg_alpha": ("loguniform", 1e-3, 1.0),
}
XGBOOST_FIJOS = {
    "objective": "reg:absoluteerror",
    "eval_metric": "mae",
    "n_estimators": 2000,
    "early_stopping_rounds": 50,
    "random_state": 42,
}

# LSTM/GRU/CNN-LSTM: pasos queda fijo en 28 (una jornada operativa) y se saca
# del espacio. epocas (techo), semilla de inicializacion y arquitectura base
# tambien quedan fijos salvo lo declarado abajo.
_ESPACIO_RED_BASE: EspacioBusqueda = {
    "unidades": ("choice", [32, 64, 128]),
    "lr": ("loguniform", 1e-4, 1e-2),
    "paciencia": ("choice", [15, 30, 50]),
}
ESPACIO_LSTM: EspacioBusqueda = dict(_ESPACIO_RED_BASE)
ESPACIO_GRU: EspacioBusqueda = dict(_ESPACIO_RED_BASE)
ESPACIO_CNN_LSTM: EspacioBusqueda = {
    **_ESPACIO_RED_BASE,
    "filtros": ("choice", [16, 32, 64]),
    "nucleo": ("choice", [3, 5]),
}
RED_FIJOS = {"pasos": 28, "epocas": 3000, "semilla_init": 42}

ESPACIOS_POR_METODO: dict[str, EspacioBusqueda] = {
    "SARIMA": ESPACIO_SARIMA,
    "Prophet": ESPACIO_PROPHET,
    "XGBoost": ESPACIO_XGBOOST,
    "LSTM": ESPACIO_LSTM,
    "GRU": ESPACIO_GRU,
    "CNN-LSTM": ESPACIO_CNN_LSTM,
}

FIJOS_POR_METODO: dict[str, dict] = {
    "SARIMA": SARIMA_FIJOS,
    "Prophet": {},
    "XGBoost": XGBOOST_FIJOS,
    "LSTM": RED_FIJOS,
    "GRU": RED_FIJOS,
    "CNN-LSTM": RED_FIJOS,
}


def _muestrear_valor(rng: np.random.Generator, distribucion: Distribucion):
    tipo = distribucion[0]
    if tipo == "randint":
        _, low, high = distribucion
        return int(rng.integers(low, high + 1))
    if tipo == "uniform":
        _, low, high = distribucion
        return float(rng.uniform(low, high))
    if tipo == "loguniform":
        _, low, high = distribucion
        return float(np.exp(rng.uniform(np.log(low), np.log(high))))
    if tipo == "choice":
        _, valores = distribucion
        indice = int(rng.integers(0, len(valores)))
        return valores[indice]
    raise ValueError(f"Tipo de distribucion no soportado: {tipo!r}")


def muestrear_configuraciones(
    metodo: str,
    n_iter: int,
    semilla: int,
) -> list[dict]:
    """Genera ``n_iter`` configuraciones aleatorias unicas para ``metodo``.

    Cada metodo usa su propio generador, inicializado con la misma semilla,
    de modo que la busqueda es reproducible e independiente entre metodos.
    Se descartan duplicados exactos (posibles en espacios discretos pequenos
    como SARIMA) y se resamplea hasta completar ``n_iter`` configuraciones
    distintas o agotar los intentos razonables.
    """
    if metodo not in ESPACIOS_POR_METODO:
        raise ValueError(f"Metodo no soportado: {metodo!r}")
    espacio = ESPACIOS_POR_METODO[metodo]
    rng = np.random.default_rng(semilla)

    vistos: set[tuple] = set()
    configuraciones: list[dict] = []
    intentos = 0
    intentos_maximos = max(1000, n_iter * 50)
    while len(configuraciones) < n_iter and intentos < intentos_maximos:
        intentos += 1
        config = {nombre: _muestrear_valor(rng, dist) for nombre, dist in espacio.items()}
        clave = tuple(sorted(config.items()))
        if clave in vistos:
            continue
        vistos.add(clave)
        configuraciones.append(config)

    if len(configuraciones) < n_iter:
        raise ValueError(
            f"No fue posible muestrear {n_iter} configuraciones distintas para "
            f"{metodo} (espacio discreto agotado tras {intentos} intentos; "
            f"se obtuvieron {len(configuraciones)})."
        )
    return configuraciones
