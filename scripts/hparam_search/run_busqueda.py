"""Corre la busqueda aleatoria de hiperparametros para uno o varios metodos.

No modifica ningun script ni artefacto de la evaluacion comparativa. Persiste
en analisis/salidas/busqueda_hiperparametros/ el espacio de busqueda, la
tabla completa de configuraciones probadas y la configuracion seleccionada,
por metodo.

Uso:
    python scripts/hparam_search/run_busqueda.py --metodo XGBoost
    python scripts/hparam_search/run_busqueda.py --metodo all --n-iter 10
"""

from __future__ import annotations

import argparse

import pandas as pd

from proyecto_grado.modeling.hparam_search.search import ejecutar_busqueda
from proyecto_grado.modeling.hparam_search.search_config import cargar_configuracion_busqueda
from proyecto_grado.modeling.hparam_search.spaces import ESPACIOS_POR_METODO

METODOS = tuple(ESPACIOS_POR_METODO)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metodo", choices=(*METODOS, "all"), required=True, help="Metodo a buscar, o 'all'"
    )
    parser.add_argument(
        "--n-iter", type=int, default=None, help="Sobrescribe n_iter de la configuracion"
    )
    args = parser.parse_args()

    config = cargar_configuracion_busqueda()
    if args.n_iter is not None:
        config = type(config)(
            evaluacion=config.evaluacion,
            inicio_validacion=config.inicio_validacion,
            fin_validacion=config.fin_validacion,
            n_iter=args.n_iter,
            semilla=config.semilla,
            directorio_salida=config.directorio_salida,
        )

    print(f"Periodo de validacion: {config.inicio_validacion} a {config.fin_validacion}")
    print(f"n_iter={config.n_iter} semilla={config.semilla}")
    print(f"Salidas en: {config.directorio_salida}\n")

    metodos = METODOS if args.metodo == "all" else (args.metodo,)
    df = pd.read_parquet(config.evaluacion.ruta_dataset)

    for metodo in metodos:
        print(f"\n{'=' * 60}\nBuscando {metodo}\n{'=' * 60}")
        resultado = ejecutar_busqueda(metodo, config, df=df)
        mejor = resultado["mejor"]
        print(
            f"\nSeleccionado {metodo}: trial {mejor['trial']} "
            f"MAE={mejor['mae_global']:.3f} sesgo={mejor['sesgo_global']:+.3f}"
        )
        for nombre, ruta in resultado["artefactos"].items():
            print(f"  {nombre}: {ruta}")


if __name__ == "__main__":
    main()
