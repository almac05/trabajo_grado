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

Uso:
    python -m proyecto_grado.etl.pipeline
    python -m proyecto_grado.etl.pipeline --directorio-salida data/actualizacion_20261004 \
        --fecha-fin 2026-10-03 [--reanudar]

Sin ``--directorio-salida`` (ni la clave ``directorio_salida`` de configs/etl.yaml)
el ETL usa las rutas historicas de siempre. Con un directorio alternativo, todas
las lecturas y escrituras de datos quedan dentro de el, se detiene si algun
archivo de destino ya existe, y solo lee fuera de el .env y configs/etl.yaml
(que copia en la raiz).
"""

import argparse
import logging
from datetime import date

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


def inicializar_entorno(cargar_env=True, crear_directorios=True, verbose=True, rutas=None):
    """Inicializa el entorno y mantiene la fachada sincronizada con config."""
    global _ENV_LOADED

    result = _config.inicializar_entorno(
        cargar_env=cargar_env,
        crear_directorios=crear_directorios,
        verbose=verbose,
        rutas=rutas,
    )
    _ENV_LOADED = _config._ENV_LOADED
    return result


def _fecha(valor: str) -> str:
    return date.fromisoformat(valor).isoformat()


def parse_args(argv=None) -> argparse.Namespace:
    """Argumentos de linea de comandos del ETL."""
    parser = argparse.ArgumentParser(description="Pipeline ETL (Bloques 3-9).")
    parser.add_argument(
        "--directorio-salida",
        default=None,
        help="Raiz alternativa para todas las salidas (prevalece sobre configs/etl.yaml).",
    )
    parser.add_argument(
        "--fecha-fin",
        type=_fecha,
        default=None,
        help="Ultima fecha a extraer, AAAA-MM-DD (por defecto, hoy).",
    )
    parser.add_argument(
        "--reanudar",
        action="store_true",
        help="Continua una ejecucion previa en el mismo directorio alternativo.",
    )
    return parser.parse_args(argv)


def resolver_rutas(args: argparse.Namespace) -> _config.RutasETL:
    """Rutas segun el argumento, la clave de configuracion o los valores por defecto."""
    raiz = args.directorio_salida or _config.DIRECTORIO_SALIDA
    if raiz is None:
        if args.reanudar:
            raise _config.ErrorRutaETL("--reanudar solo aplica con un directorio alternativo.")
        return _config.RUTAS_PREDETERMINADAS
    return _config.rutas_etl(raiz)


def main(argv=None) -> None:
    """Orquesta la ejecucion secuencial de los Bloques 3-9 del pipeline ETL."""
    _setup_logging()
    args = parse_args(argv)
    rutas = resolver_rutas(args)
    if rutas.alternativa:
        _config.preparar_raiz_alternativa(
            rutas,
            {"fecha_ini": "2024-04-16", "fecha_fin": args.fecha_fin},
            reanudar=args.reanudar,
        )
    inicializar_entorno(verbose=True, rutas=rutas)

    logger.info("=" * 70)
    logger.info("PIPELINE ETL - Proyecto de Grado Montebello")
    if rutas.alternativa:
        logger.info("Directorio alternativo: %s (reanudar=%s)", rutas.raiz, args.reanudar)
    logger.info("=" * 70)

    despachos = run_block3(fecha_fin=args.fecha_fin, rutas=rutas)
    despachos = run_block4(despachos)
    if RUN_VALIDATION:
        run_radio_validation(despachos, n_muestras=100)
    despachos = run_block5(despachos, rutas=rutas)
    run_block6(despachos, rutas=rutas)
    run_block7(rutas=rutas)
    run_block8(rutas=rutas)
    run_block9(rutas=rutas)

    logger.info("=" * 70)
    logger.info("Pipeline ETL completado exitosamente.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
