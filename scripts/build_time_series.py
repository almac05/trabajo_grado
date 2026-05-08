"""Script CLI para construir la serie temporal agregada desde el dataset model-ready.

Uso desde la raiz del proyecto:
    python scripts/build_time_series.py
    python scripts/build_time_series.py --ruta 1
    python scripts/build_time_series.py --granularidad 30

Salidas:
    data/processed/time_series/ts_ruta{ruta}_g{gran}min.parquet  (una por combinacion)
    reports/tables/time_series_summary.csv
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

from proyecto_grado.features.time_series_builder import TimeSeriesBuilder
from proyecto_grado.features.validators import TimeSeriesValidator

PROJECT_ROOT = Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)

MODEL_READY_PATH = (
    PROJECT_ROOT / "data" / "processed" / "model_ready" / "despachos_model_ready.parquet"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "time_series"
REPORT_DIR = PROJECT_ROOT / "reports" / "tables"
FEATURES_CONFIG_PATH = PROJECT_ROOT / "configs" / "features.yaml"


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_features_config() -> dict:
    if not FEATURES_CONFIG_PATH.exists():
        logger.warning("configs/features.yaml no encontrado — usando defaults")
        return {}
    with open(FEATURES_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    """Orquesta la construccion y validacion de la serie temporal por ruta y granularidad."""
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="Construye la serie temporal agregada desde el dataset model-ready"
    )
    parser.add_argument(
        "--ruta",
        type=int,
        default=None,
        help="Ruta especifica a procesar (1 o 3). Por defecto procesa todas.",
    )
    parser.add_argument(
        "--granularidad",
        type=int,
        choices=[15, 30, 60],
        default=None,
        help="Granularidad en minutos. Sobreescribe configs/features.yaml (produce solo esa granularidad).",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("BUILD TIME SERIES - Proyecto de Grado Montebello")
    logger.info("=" * 70)

    cfg = _load_features_config()
    if args.granularidad is not None:
        cfg["granularidades_min"] = [args.granularidad]
        cfg.pop("granularidad_min", None)
        logger.info("Granularidad sobreescrita por CLI: %d min", args.granularidad)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not MODEL_READY_PATH.exists():
        logger.error("No existe model-ready en: %s", MODEL_READY_PATH)
        logger.error("Ejecuta primero: make etl")
        sys.exit(1)

    logger.info("Cargando model-ready desde: %s", MODEL_READY_PATH)
    df = pd.read_parquet(MODEL_READY_PATH)
    logger.info("Dataset cargado: filas=%d cols=%d", len(df), df.shape[1])

    builder = TimeSeriesBuilder(cfg)

    rutas_a_procesar: list[int] = [args.ruta] if args.ruta is not None else builder.rutas
    granularidades = builder.granularidades_min
    summary_rows: list[dict] = []

    for gran in granularidades:
        for ruta in rutas_a_procesar:
            logger.info("-" * 50)
            logger.info("Procesando ruta %d | granularidad %d min ...", ruta, gran)

            serie = builder.build(df, ruta=ruta, granularidad_min=gran)
            validator = TimeSeriesValidator(
                granularidad_min=gran,
                cobertura_minima_dias=int(cfg.get("cobertura_minima_dias", 30)),
            )
            report = validator.validate(serie, ruta=ruta)

            if not serie.empty:
                out_path = OUTPUT_DIR / f"ts_ruta{ruta}_g{gran}min.parquet"
                serie.to_parquet(out_path, index=False)
                logger.info("Serie guardada: %s", out_path)
                logger.info("Schema: %s", dict(serie.dtypes))

            n_franjas = report.n_filas
            n_gaps = report.gaps_detectados
            pct_gaps = round(100.0 * n_gaps / n_franjas, 1) if n_franjas > 0 else 0.0
            pasajeros_total = float(serie["pasajeros_total"].sum()) if not serie.empty else 0.0

            summary_rows.append(
                {
                    "granularidad_min": gran,
                    "ruta": ruta,
                    "n_franjas": n_franjas,
                    "n_gaps": n_gaps,
                    "pct_gaps": pct_gaps,
                    "pasajeros_total": pasajeros_total,
                    "valida": report.valida,
                    "errores": "; ".join(report.errores) if report.errores else "",
                    "advertencias": "; ".join(report.advertencias) if report.advertencias else "",
                }
            )

    summary = pd.DataFrame(summary_rows)
    report_path = REPORT_DIR / "time_series_summary.csv"
    summary.to_csv(report_path, index=False)
    logger.info("Reporte de resumen guardado: %s", report_path)

    display_cols = [
        "granularidad_min",
        "ruta",
        "n_franjas",
        "n_gaps",
        "pct_gaps",
        "pasajeros_total",
    ]
    logger.info("\n%s", summary[display_cols].to_string(index=False))

    logger.info("=" * 70)
    logger.info("Build completado.")
    logger.info("=" * 70)

    if not summary["valida"].all():
        logger.error("Una o mas series no pasaron la validacion. Revisa el reporte.")
        sys.exit(1)


if __name__ == "__main__":
    main()
