"""Configuracion de rutas e inicializacion del entorno ETL."""

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# src/proyecto_grado/etl/config.py -> parents[3] = raiz del repo
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUTA_PPAL = str(PROJECT_ROOT)

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports" / "tables"

DESPACHOS_CSV = str(RAW_DIR / "despachos_raw_historico.csv")

BATCH_DIR = str(INTERIM_DIR / "batches_parquet")
QC_DIR = str(INTERIM_DIR / "qc")
GPS_DIR = str(INTERIM_DIR / "gps")
PROGRESO_FILE = str(INTERIM_DIR / "progreso_tracking.csv")

MODEL_READY_DIR = str(PROCESSED_DIR / "model_ready")

QC_REPORTS_DIR = str(REPORTS_DIR / "qc")
ETL_REPORTS_DIR = str(REPORTS_DIR / "etl")

QC_PATH = os.path.join(QC_DIR, "despachos_qc.parquet")
END_PATH = os.path.join(GPS_DIR, "despachos_end.parquet")


def _load_etl_yaml() -> dict:
    """Carga configs/etl.yaml si existe; silencioso si falta."""
    path = PROJECT_ROOT / "configs" / "etl.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_ETL_CFG = _load_etl_yaml()

RUTAS_OPERATIVAS: list = _ETL_CFG.get("rutas_operativas", [1, 3])

GPS_CONFIG: dict = {
    "puntos": {
        "MOJICA": {"lat": 3.416218, "lon": -76.490574},
        "MORICHAL": {"lat": 3.398863, "lon": -76.508078},
    },
    "radio_geocerca_m": 700,
    "radio_validacion_m": 1800,
    "ventanas_busqueda_min": [30, 90, 180],
    **_ETL_CFG.get("gps", {}),
}

TRIP_END_CONFIG: dict = {
    "buffer_min": 20,
    "ventana_min": 180,
    "vel_baja_kmh": 3,
    "vel_retorno_kmh": 12,
    "cola_eval_min": 15,
    "pct_baja": 0.70,
    "usar_msg_apagado": True,
    "w_msg": 0.35,
    "msg_apagado": "Móvil Apagado",
    "tabla_gps": "tbl_forwarding_wtch",
    "checkpoint_every": 500,
    **_ETL_CFG.get("trip_end", {}),
}

QC_CONFIG: dict = {
    "duracion_pctl_soft": 99.0,
    "duracion_max_min_hard": None,
    "pasajeros_pctl_soft": 99.5,
    "pasajeros_max_hard": None,
    "freq_min_soft": 1.0,
    "freq_max_soft": 60.0,
    **_ETL_CFG.get("qc", {}),
}

_ENV_LOADED = False


def _directorios_salida():
    """Directorios que el ETL necesita crear antes de escribir artefactos."""
    return [
        RAW_DIR,
        INTERIM_DIR,
        PROCESSED_DIR,
        REPORTS_DIR,
        BATCH_DIR,
        QC_DIR,
        GPS_DIR,
        MODEL_READY_DIR,
        QC_REPORTS_DIR,
        ETL_REPORTS_DIR,
    ]


def inicializar_entorno(cargar_env=True, crear_directorios=True, verbose=True):
    """Inicializa dependencias de entorno sin ejecutar esta logica al importar."""
    global _ENV_LOADED

    if cargar_env and not _ENV_LOADED:
        load_dotenv(PROJECT_ROOT / ".env")
        _ENV_LOADED = True

    if crear_directorios:
        for d in _directorios_salida():
            os.makedirs(d, exist_ok=True)

    if verbose:
        logger.info("Rutas del proyecto listas")
        logger.info("PROJECT_ROOT:    %s", PROJECT_ROOT)
        logger.info("DESPACHOS_CSV:   %s", DESPACHOS_CSV)
        logger.info("BATCH_DIR:       %s", BATCH_DIR)
        logger.info("QC_PATH:         %s", QC_PATH)
        logger.info("MODEL_READY_DIR: %s", MODEL_READY_DIR)
        logger.info("QC_REPORTS_DIR:  %s", QC_REPORTS_DIR)
        logger.info("ETL_REPORTS_DIR: %s", ETL_REPORTS_DIR)

    return {
        "PROJECT_ROOT": PROJECT_ROOT,
        "DESPACHOS_CSV": DESPACHOS_CSV,
        "BATCH_DIR": BATCH_DIR,
        "QC_PATH": QC_PATH,
        "MODEL_READY_DIR": MODEL_READY_DIR,
        "QC_REPORTS_DIR": QC_REPORTS_DIR,
        "ETL_REPORTS_DIR": ETL_REPORTS_DIR,
    }
