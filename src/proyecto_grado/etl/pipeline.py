"""Orquestador del pipeline ETL de Proyecto de Grado.

La logica esta modularizada por capas en este paquete:
- config: rutas e inicializacion
- db: acceso a MySQL y CSV
- extract: extraccion incremental
- transforms: transformaciones basicas
- gps: geocerca e imputacion GPS
- qc: calidad y coherencia operacional
- trip_end: clasificacion de fin de recorrido
- model_ready: dataset final y metadata
"""

import logging

from . import config as _config
from .extract import run_block3
from .gps import (
    RUN_VALIDATION,
    run_block5,
    run_radio_validation,
)
from .model_ready import run_block8, run_block9
from .qc import (
    run_block6,
)
from .transforms import run_block4
from .trip_end import (
    run_block7,
)

logger = logging.getLogger(__name__)

_ENV_LOADED = False


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def inicializar_entorno(cargar_env=True, crear_directorios=True, verbose=True):
    """Inicializa el entorno y mantiene la fachada sincronizada con config."""
    global _ENV_LOADED

    result = _config.inicializar_entorno(
        cargar_env=cargar_env,
        crear_directorios=crear_directorios,
        verbose=verbose,
    )
    _ENV_LOADED = _config._ENV_LOADED
    return result


def main() -> None:
    """Orquesta la ejecucion secuencial de los Bloques 3-9 del pipeline ETL."""
    _setup_logging()
    inicializar_entorno(verbose=True)

    logger.info("=" * 70)
    logger.info("PIPELINE ETL - Proyecto de Grado Montebello")
    logger.info("=" * 70)

    despachos = run_block3()
    despachos = run_block4(despachos)
    if RUN_VALIDATION:
        run_radio_validation(despachos, n_muestras=100)
    despachos = run_block5(despachos)
    run_block6(despachos)
    run_block7()
    run_block8()
    run_block9()

    logger.info("=" * 70)
    logger.info("Pipeline ETL completado exitosamente.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
