"""Calibra el tiempo real por ajuste de cada metodo, antes de comprometer la
busqueda completa.

Corre una sola configuracion (los valores de produccion actuales) sobre unas
pocas jornadas del periodo de validacion, para los seis metodos, y reporta
el tiempo promedio por ajuste. No persiste artefactos de busqueda: solo
informa para dimensionar ``n_iter`` y el tiempo total.

Uso:
    python scripts/hparam_search/run_calibracion.py --dias 3
"""

from __future__ import annotations

import argparse
import time

import pandas as pd

from proyecto_grado.modeling.hparam_search.runner import evaluar_configuracion
from proyecto_grado.modeling.hparam_search.search_config import cargar_configuracion_busqueda

# Configuraciones "de referencia": los valores de produccion actuales de cada
# metodo, expresados en el formato que esperan las funciones de fits.py.
CONFIG_REFERENCIA = {
    "SARIMA": {"p": 2, "q": 1, "P": 1, "Q": 1},
    "Prophet": {
        "changepoint_prior_scale": 0.05,  # valor por defecto de Prophet
        "seasonality_prior_scale": 10.0,
        "holidays_prior_scale": 10.0,
        "seasonality_mode": "additive",
        "changepoint_range": 0.8,
    },
    "XGBoost": {
        "max_depth": 5,
        "min_child_weight": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "reg_alpha": 0.0,
    },
    "LSTM": {"unidades": 64, "lr": 0.001, "paciencia": 30},
    "GRU": {"unidades": 64, "lr": 0.001, "paciencia": 30},
    "CNN-LSTM": {"unidades": 64, "lr": 0.001, "paciencia": 30, "filtros": 32, "nucleo": 3},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dias", type=int, default=3, help="Jornadas por ruta a calibrar")
    args = parser.parse_args()

    config = cargar_configuracion_busqueda()
    df = pd.read_parquet(config.evaluacion.ruta_dataset)

    print(
        f"Periodo de validacion (calibracion): {config.inicio_validacion} a {config.fin_validacion}"
    )
    print(f"Jornadas por ruta usadas para calibrar: {args.dias}\n")

    resultados = []
    for metodo, params in CONFIG_REFERENCIA.items():
        t0 = time.perf_counter()
        observaciones, segundos_internos = evaluar_configuracion(
            metodo, params, config, df=df, dias_limite=args.dias
        )
        segundos_totales = time.perf_counter() - t0
        n_ajustes = observaciones[["route", "dia_op"]].drop_duplicates().shape[0]
        seg_por_ajuste = segundos_totales / n_ajustes if n_ajustes else float("nan")
        resultados.append(
            {
                "metodo": metodo,
                "ajustes_calibrados": n_ajustes,
                "segundos_totales": round(segundos_totales, 2),
                "segundos_por_ajuste": round(seg_por_ajuste, 2),
            }
        )
        print(
            f"{metodo:10s} {n_ajustes:2d} ajustes en {segundos_totales:7.2f}s "
            f"-> {seg_por_ajuste:6.2f}s/ajuste"
        )

    tabla = pd.DataFrame(resultados)
    print("\n" + tabla.to_string(index=False))


if __name__ == "__main__":
    main()
