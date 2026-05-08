"""CLI para estimar el horario operativo desde las series temporales de despachos.

Lee los Parquet de series temporales, calcula el horario operativo por
(tipo_dia x ruta x granularidad) y regenera las series con las columnas
`dentro_horario_operativo` y `gap_tipo`.

Uso:
    python scripts/estimate_operational_hours.py
    python scripts/estimate_operational_hours.py --ruta 1 --granularidad 60
    python scripts/estimate_operational_hours.py --solo-estimacion
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from proyecto_grado.features.operational_hours import OperationalHoursEstimator  # noqa: E402
from proyecto_grado.features.time_series_builder import TimeSeriesBuilder  # noqa: E402

TIME_SERIES_DIR = PROJECT_ROOT / "data" / "processed" / "time_series"
MODEL_READY_PATH = (
    PROJECT_ROOT / "data" / "processed" / "model_ready" / "despachos_model_ready.parquet"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports" / "tables"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
FEATURES_CONFIG_PATH = PROJECT_ROOT / "configs" / "features.yaml"

_TS_PATTERN = re.compile(r"ts_ruta(\d+)_g(\d+)min")

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_config() -> dict:
    if not FEATURES_CONFIG_PATH.exists():
        logger.warning("configs/features.yaml no encontrado — usando defaults")
        return {}
    with open(FEATURES_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_time_series(
    ruta_filter: int | None, gran_filter: int | None
) -> dict[tuple[int, int], pd.DataFrame]:
    series: dict[tuple[int, int], pd.DataFrame] = {}
    for path in sorted(TIME_SERIES_DIR.glob("ts_ruta*_g*min.parquet")):
        m = _TS_PATTERN.match(path.stem)
        if not m:
            continue
        ruta, gran = int(m.group(1)), int(m.group(2))
        if ruta_filter is not None and ruta != ruta_filter:
            continue
        if gran_filter is not None and gran != gran_filter:
            continue
        df = pd.read_parquet(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        series[(ruta, gran)] = df
        logger.info("Serie cargada: %s (filas=%d)", path.name, len(df))
    return series


def _print_summary(result: pd.DataFrame) -> None:
    display_cols = [
        "tipo_dia",
        "ruta",
        "granularidad_min",
        "hora_inicio_op",
        "hora_fin_op",
        "duracion_operativa_h",
        "n_dias_muestra",
        "pct_cobertura_dentro_horario",
    ]
    cols_present = [c for c in display_cols if c in result.columns]
    print("\n" + "=" * 80)
    print("HORARIOS OPERATIVOS ESTIMADOS")
    print("=" * 80)
    print(result[cols_present].to_string(index=False))
    print("=" * 80 + "\n")


def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="Estima el horario operativo desde las series temporales de Montebello"
    )
    parser.add_argument("--ruta", type=int, default=None, help="Ruta especifica (1 o 3)")
    parser.add_argument(
        "--granularidad",
        type=int,
        choices=[15, 30, 60],
        default=None,
        help="Granularidad en minutos",
    )
    parser.add_argument(
        "--solo-estimacion",
        action="store_true",
        help="Solo estima el horario; no regenera las series temporales",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("ESTIMATE OPERATIONAL HOURS - Proyecto de Grado Montebello")
    logger.info("=" * 70)

    if not TIME_SERIES_DIR.exists() or not any(TIME_SERIES_DIR.glob("ts_ruta*_g*min.parquet")):
        logger.error("No se encontraron series temporales en: %s", TIME_SERIES_DIR)
        logger.error("Ejecuta primero: make build-ts")
        sys.exit(1)

    cfg = _load_config()
    horario_cfg = cfg.get("horario_operativo", {})

    # 1. Cargar series temporales
    series_dict = _load_time_series(args.ruta, args.granularidad)
    if not series_dict:
        logger.error("No se encontraron series con los filtros indicados")
        sys.exit(1)
    logger.info("Series cargadas: %d combinaciones ruta x granularidad", len(series_dict))

    # 2. Estimar horario operativo
    estimator = OperationalHoursEstimator(cfg=horario_cfg)
    result = estimator.fit(series_dict)

    # 3. Guardar resultados
    estimator.save(output_dir=OUTPUT_DIR, report_dir=REPORT_DIR)

    # 4. Generar heatmaps por (ruta x granularidad)
    for ruta, gran in series_dict:
        estimator.plot_heatmap(series_dict, ruta=ruta, gran=gran, output_dir=FIGURES_DIR)

    # 5. Mostrar tabla resumen
    _print_summary(result)

    if args.solo_estimacion:
        logger.info("Flag --solo-estimacion activo. Series no regeneradas.")
        return

    # 6. Regenerar series con nuevas columnas (requiere model-ready)
    if not MODEL_READY_PATH.exists():
        logger.warning("model-ready no encontrado en %s — series no regeneradas", MODEL_READY_PATH)
        logger.warning(
            "Para regenerar, ejecuta: make etl && python scripts/estimate_operational_hours.py"
        )
        return

    logger.info("=" * 70)
    logger.info("Regenerando series temporales con columnas de horario operativo ...")
    logger.info("=" * 70)

    df_ready = pd.read_parquet(MODEL_READY_PATH)
    logger.info("model-ready cargado: filas=%d", len(df_ready))

    builder_cfg = {k: v for k, v in cfg.items() if k != "horario_operativo"}
    if args.ruta is not None:
        builder_cfg["rutas"] = [args.ruta]
    if args.granularidad is not None:
        builder_cfg["granularidades_min"] = [args.granularidad]

    builder = TimeSeriesBuilder(builder_cfg)

    TIME_SERIES_DIR.mkdir(parents=True, exist_ok=True)
    for gran in builder.granularidades_min:
        for ruta in builder.rutas:
            logger.info("Regenerando: ruta=%d gran=%dmin ...", ruta, gran)
            serie = builder.build(df_ready, ruta=ruta, granularidad_min=gran)
            if serie.empty:
                logger.warning("Serie vacia para ruta=%d gran=%d — omitida", ruta, gran)
                continue
            out = TIME_SERIES_DIR / f"ts_ruta{ruta}_g{gran}min.parquet"
            serie.to_parquet(out, index=False)
            has_op = "gap_tipo" in serie.columns
            logger.info(
                "Serie guardada: %s | gap_tipo=%s | filas=%d",
                out.name,
                has_op,
                len(serie),
            )

            if has_op:
                counts = serie["gap_tipo"].value_counts().to_dict()
                logger.info("  gap_tipo dist: %s", counts)

    logger.info("=" * 70)
    logger.info("Estimacion y regeneracion completadas.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
