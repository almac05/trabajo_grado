"""Configuracion de rutas e inicializacion del entorno ETL."""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
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


ETL_YAML_PATH = PROJECT_ROOT / "configs" / "etl.yaml"
MARCADOR_EJECUCION = ".etl_ejecucion.json"


class ErrorRutaETL(RuntimeError):  # noqa: N818
    """Ruta fuera de la raiz alternativa, destino existente o reanudacion invalida."""


@dataclass(frozen=True)
class RutasETL:
    """Rutas de lectura y escritura del ETL.

    Con ``raiz = None`` son las rutas historicas del proyecto y no se aplica
    ninguna restriccion. Con una raiz alternativa, toda lectura o escritura debe
    quedar dentro de ella (``verificar``).
    """

    raiz: Path | None
    data_dir: Path
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    reports_dir: Path
    despachos_csv: str
    batch_dir: str
    qc_dir: str
    gps_dir: str
    progreso_file: str
    model_ready_dir: str
    qc_reports_dir: str
    etl_reports_dir: str
    qc_path: str
    end_path: str

    @property
    def alternativa(self) -> bool:
        """Indica si las rutas estan bajo una raiz alternativa."""
        return self.raiz is not None

    def directorios_salida(self) -> list:
        """Directorios que el ETL necesita crear antes de escribir artefactos."""
        return [
            self.raw_dir,
            self.interim_dir,
            self.processed_dir,
            self.reports_dir,
            self.batch_dir,
            self.qc_dir,
            self.gps_dir,
            self.model_ready_dir,
            self.qc_reports_dir,
            self.etl_reports_dir,
        ]

    def destinos_fijos(self) -> list[str]:
        """Archivos de nombre fijo que escribe el ETL (sin los versionados por fecha)."""
        return [
            self.despachos_csv,
            self.qc_path,
            os.path.join(self.qc_dir, "despachos_gps_ready.parquet"),
            os.path.join(self.qc_dir, "despachos_hard_excluded.parquet"),
            os.path.join(self.qc_reports_dir, "qc_resumen.csv"),
            os.path.join(self.qc_reports_dir, "qc_top_vehiculos.csv"),
            os.path.join(self.qc_reports_dir, "qc_top_rutas.csv"),
            self.end_path,
            self.end_path + ".tmp",
            os.path.join(self.model_ready_dir, "despachos_model_ready.parquet"),
            os.path.join(self.model_ready_dir, "despachos_model_ready.csv"),
        ]

    def verificar(self, ruta):
        """Devuelve la ruta sin cambios; con raiz alternativa exige que este dentro."""
        if self.raiz is None:
            return ruta
        resuelta = Path(ruta).resolve()
        if resuelta != self.raiz and self.raiz not in resuelta.parents:
            raise ErrorRutaETL(f"Ruta fuera de la raiz alternativa {self.raiz}: {resuelta}")
        return ruta

    def verificar_nuevo(self, ruta):
        """Como ``verificar``; con raiz alternativa exige ademas que el archivo no exista."""
        ruta = self.verificar(ruta)
        if self.raiz is not None and os.path.exists(ruta):
            raise ErrorRutaETL(f"El archivo de destino ya existe: {ruta}")
        return ruta


def _construir_rutas(data_dir: Path, reports_dir: Path, raiz: Path | None) -> RutasETL:
    raw_dir = data_dir / "raw"
    interim_dir = data_dir / "interim"
    processed_dir = data_dir / "processed"
    qc_dir = str(interim_dir / "qc")
    gps_dir = str(interim_dir / "gps")
    return RutasETL(
        raiz=raiz,
        data_dir=data_dir,
        raw_dir=raw_dir,
        interim_dir=interim_dir,
        processed_dir=processed_dir,
        reports_dir=reports_dir,
        despachos_csv=str(raw_dir / "despachos_raw_historico.csv"),
        batch_dir=str(interim_dir / "batches_parquet"),
        qc_dir=qc_dir,
        gps_dir=gps_dir,
        progreso_file=str(interim_dir / "progreso_tracking.csv"),
        model_ready_dir=str(processed_dir / "model_ready"),
        qc_reports_dir=str(reports_dir / "qc"),
        etl_reports_dir=str(reports_dir / "etl"),
        qc_path=os.path.join(qc_dir, "despachos_qc.parquet"),
        end_path=os.path.join(gps_dir, "despachos_end.parquet"),
    )


RUTAS_PREDETERMINADAS = _construir_rutas(DATA_DIR, REPORTS_DIR, None)


def rutas_etl(raiz=None) -> RutasETL:
    """Rutas del ETL: las historicas sin argumento, o todas bajo ``raiz``.

    Bajo la raiz se reproduce la estructura de ``data/`` (``raw``, ``interim``,
    ``processed``) y los reportes van a ``<raiz>/reports/tables``. Una raiz
    relativa se resuelve contra la raiz del proyecto.
    """
    if raiz is None:
        return RUTAS_PREDETERMINADAS
    raiz = Path(raiz)
    if not raiz.is_absolute():
        raiz = PROJECT_ROOT / raiz
    raiz = raiz.resolve()
    data_resuelto = DATA_DIR.resolve()
    if raiz == data_resuelto or raiz in data_resuelto.parents:
        raise ErrorRutaETL(f"La raiz alternativa no puede ser data/ ni contenerlo: {raiz}")
    return _construir_rutas(raiz, raiz / "reports" / "tables", raiz)


def preparar_raiz_alternativa(rutas: RutasETL, parametros: dict, reanudar: bool = False) -> None:
    """Valida la raiz alternativa, copia etl.yaml y escribe el marcador de ejecucion.

    Sin ``reanudar``, se detiene si existe alguno de los archivos de destino o el
    marcador. Con ``reanudar``, exige el marcador de una ejecucion previa con los
    mismos parametros. No registra credenciales.
    """
    if rutas.raiz is None:
        raise ErrorRutaETL("preparar_raiz_alternativa requiere una raiz alternativa.")
    marcador = rutas.raiz / MARCADOR_EJECUCION
    if reanudar:
        if not marcador.exists():
            raise ErrorRutaETL(f"--reanudar requiere el marcador {marcador}.")
        previo = json.loads(marcador.read_text(encoding="utf-8"))
        if previo.get("parametros") != parametros:
            raise ErrorRutaETL(
                "Los parametros no coinciden con la ejecucion previa: "
                f"{previo.get('parametros')} frente a {parametros}."
            )
        previo.setdefault("reanudaciones", []).append(datetime.now().isoformat(timespec="seconds"))
        marcador.write_text(json.dumps(previo, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    existentes = [r for r in [*rutas.destinos_fijos(), str(marcador)] if os.path.exists(r)]
    if existentes:
        raise ErrorRutaETL(f"Ya existen archivos de destino en la raiz: {existentes}")
    for d in rutas.directorios_salida():
        os.makedirs(rutas.verificar(d), exist_ok=True)
    copiada = None
    if ETL_YAML_PATH.exists():
        shutil.copyfile(ETL_YAML_PATH, rutas.verificar(rutas.raiz / "etl.yaml"))
        copiada = "etl.yaml"
    contenido = {
        "inicio": datetime.now().isoformat(timespec="seconds"),
        "parametros": parametros,
        "configuracion_copiada": copiada,
    }
    marcador.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_etl_yaml() -> dict:
    """Carga configs/etl.yaml si existe; silencioso si falta."""
    path = ETL_YAML_PATH
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_ETL_CFG = _load_etl_yaml()

RUTAS_OPERATIVAS: list = _ETL_CFG.get("rutas_operativas", [1, 3])
# Raiz alternativa de salida; ausente o null conserva las rutas historicas.
DIRECTORIO_SALIDA = _ETL_CFG.get("directorio_salida")

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
    return RUTAS_PREDETERMINADAS.directorios_salida()


def inicializar_entorno(cargar_env=True, crear_directorios=True, verbose=True, rutas=None):
    """Inicializa dependencias de entorno sin ejecutar esta logica al importar.

    ``rutas`` (``RutasETL``) elige los directorios a crear; por defecto, los
    historicos del proyecto.
    """
    global _ENV_LOADED
    rutas = RUTAS_PREDETERMINADAS if rutas is None else rutas

    if cargar_env and not _ENV_LOADED:
        load_dotenv(PROJECT_ROOT / ".env", override=True)
        _ENV_LOADED = True

    if crear_directorios:
        for d in rutas.directorios_salida():
            os.makedirs(rutas.verificar(d), exist_ok=True)

    if verbose:
        logger.info("Rutas del proyecto listas")
        logger.info("PROJECT_ROOT:    %s", PROJECT_ROOT)
        logger.info("DESPACHOS_CSV:   %s", rutas.despachos_csv)
        logger.info("BATCH_DIR:       %s", rutas.batch_dir)
        logger.info("QC_PATH:         %s", rutas.qc_path)
        logger.info("MODEL_READY_DIR: %s", rutas.model_ready_dir)
        logger.info("QC_REPORTS_DIR:  %s", rutas.qc_reports_dir)
        logger.info("ETL_REPORTS_DIR: %s", rutas.etl_reports_dir)

    return {
        "PROJECT_ROOT": PROJECT_ROOT,
        "DESPACHOS_CSV": rutas.despachos_csv,
        "BATCH_DIR": rutas.batch_dir,
        "QC_PATH": rutas.qc_path,
        "MODEL_READY_DIR": rutas.model_ready_dir,
        "QC_REPORTS_DIR": rutas.qc_reports_dir,
        "ETL_REPORTS_DIR": rutas.etl_reports_dir,
    }
