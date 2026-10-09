"""Bloques 4-8 del ETL por ventana y serie de 30 minutos (seccion 2 del diseno).

- ``procesar_ventana``: los despachos crudos de la ventana pasan por los bloques
  4 a 8 con las funciones del ETL sin cambios, en una raiz alternativa propia
  (``etl/<id>/``). En modo local no hay base de datos: las horas de salida ya
  imputadas vienen en el crudo de la semilla y el fin de viaje estimado se
  precarga en el punto de control del bloque 7 desde la semilla; cualquier
  intento de consultar el GPS se cuenta y no se resuelve.
- ``conjunto_apto_piloto``: la semilla antes de ``inicio_almacen`` unida al
  conjunto apto del almacen de la piloto.
- ``construir_serie``: reconstruye la serie completa con ``TimeSeriesBuilder``
  y el horario operativo congelado, la extiende con las franjas de D+1 (sin
  demanda) usando los mismos metodos del constructor, y agrega las variables
  con ``add_modeling_features``, como ``modeling.dataset.build_modeling_dataset``.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from proyecto_grado.features.time_series_builder import TimeSeriesBuilder
from proyecto_grado.modeling.config import ScenarioDefinition, TargetConfig
from proyecto_grado.modeling.dataset import (
    MODELING_COLUMNS,
    build_time_series,
    prepare_scenario_dataset,
)
from proyecto_grado.modeling.features import add_modeling_features, validate_lag_features
from proyecto_grado.piloto.extraccion import PK, fechas_de

logger = logging.getLogger(__name__)

COLUMNAS_FIN_VIAJE = [PK, "RECORRIDO_COMPLETO", "HORA_FIN_ESTIMADA", "FIN_TIPO", "HORA_FIN_FUENTE"]
OBJETIVOS_SERIE = ["pasajeros_total", "despachos_count", "pasajeros_promedio", "ocupacion_p95"]


class ErrorSerie(RuntimeError):  # noqa: N818
    """El procesamiento por ventana o la serie no son utilizables."""


# --------------------------------------------------------------- bloques 4-8


@dataclass
class GPSLocal:
    """Sustituto sin conexion del GPS para el modo local.

    ``fin_viaje``: estimaciones del bloque 7 de la semilla (despachos_end.parquet).
    Cuenta las consultas que los bloques 5 y 7 habrian hecho a la base.
    """

    fin_viaje: pd.DataFrame
    consultas: dict[str, int] = field(
        default_factory=lambda: {"placa": 0, "rastreo_salida": 0, "rastreo_fin": 0}
    )

    @classmethod
    def desde_archivo(cls, ruta: Path) -> GPSLocal:
        return cls(pd.read_parquet(ruta, columns=COLUMNAS_FIN_VIAJE))


class _SinConexion:
    """Conexion que no existe: cualquier consulta directa es un error."""

    def cursor(self, *a, **k):
        raise ErrorSerie("Consulta a la base en modo local.")

    def is_connected(self):
        return False

    def ping(self, *a, **k):
        pass

    def close(self):
        pass


@contextlib.contextmanager
def _sin_base(gps: GPSLocal):
    """Sustituye, mientras dura el bloque, el acceso a la base de los bloques 5 y 7."""
    from proyecto_grado.etl import gps as m_gps
    from proyecto_grado.etl import trip_end as m_fin

    sin = _SinConexion()

    def contar(clave, valor):
        def f(*a, **k):
            gps.consultas[clave] += 1
            return valor() if callable(valor) else valor

        return f

    reemplazos = [
        (m_gps, "conectar_bd", lambda *a, **k: sin),
        (m_gps, "asegurar_conexion", lambda *a, **k: sin),
        (m_gps, "cerrar_conexion", lambda *a, **k: None),
        (m_gps, "obtener_placa", contar("placa", None)),
        (m_gps, "obtener_detalle_rastreo", contar("rastreo_salida", pd.DataFrame)),
        (m_fin, "conectar_bd", lambda *a, **k: sin),
        (m_fin, "asegurar_conexion", lambda *a, **k: sin),
        (m_fin, "cerrar_conexion", lambda *a, **k: None),
        (m_fin, "fetch_gps_events_by_time_window", contar("rastreo_fin", pd.DataFrame)),
    ]
    originales = [(m, n, getattr(m, n)) for m, n, _ in reemplazos]
    try:
        for m, n, v in reemplazos:
            setattr(m, n, v)
        yield
    finally:
        for m, n, v in originales:
            setattr(m, n, v)


def procesar_ventana(
    crudo: pd.DataFrame, raiz_etl: Path, gps_local: GPSLocal | None = None
) -> tuple[pd.DataFrame, dict]:
    """Bloques 4 a 8 sobre los despachos de la ventana; devuelve el conjunto apto.

    ``raiz_etl`` no debe existir: todos los archivos intermedios del ETL quedan
    ahi (raiz alternativa de ``etl.config.rutas_etl``).
    """
    from proyecto_grado.etl.config import inicializar_entorno, rutas_etl
    from proyecto_grado.etl.gps import run_block5
    from proyecto_grado.etl.model_ready import run_block8
    from proyecto_grado.etl.qc import run_block6
    from proyecto_grado.etl.transforms import run_block4
    from proyecto_grado.etl.trip_end import run_block7

    raiz_etl = Path(raiz_etl)
    if raiz_etl.exists():
        raise ErrorSerie(f"La raiz del ETL de la ventana ya existe: {raiz_etl}")
    info: dict = {"crudo": len(crudo)}
    if crudo.empty:
        info.update({"bloque4": 0, "conjunto_apto": 0})
        return pd.DataFrame(), info

    rutas = rutas_etl(raiz_etl)
    inicializar_entorno(verbose=False, rutas=rutas)
    contexto = _sin_base(gps_local) if gps_local is not None else contextlib.nullcontext()
    with contexto:
        d = run_block4(crudo)
        info["bloque4"] = len(d)
        d = run_block5(d, rutas=rutas)
        run_block6(d, rutas=rutas)
        if gps_local is not None:
            pks = set(pd.to_numeric(d[PK]).astype(int))
            previo = gps_local.fin_viaje[gps_local.fin_viaje[PK].isin(pks)]
            previo.to_parquet(rutas.end_path, index=False)
            info["fin_viaje_precargado"] = len(previo)
        fin = run_block7(rutas=rutas)
        apto = run_block8(rutas=rutas)
    info.update(
        {
            "bloque7": len(fin),
            "fin_viaje_fuente": fin["HORA_FIN_FUENTE"].value_counts(dropna=False).to_dict(),
            "conjunto_apto": len(apto),
        }
    )
    if gps_local is not None:
        info["consultas_gps_sin_resolver"] = dict(gps_local.consultas)
    return apto.reset_index(drop=True), info


def conjunto_apto_piloto(
    semilla: pd.DataFrame, almacen: pd.DataFrame, inicio_almacen: date
) -> pd.DataFrame:
    """Semilla con FECHA_INICIAL < inicio_almacen, mas el conjunto apto de la piloto."""
    anterior = semilla[fechas_de(semilla) < inicio_almacen]
    if len(almacen) and (fechas_de(almacen) < inicio_almacen).any():
        raise ErrorSerie("El almacen tiene despachos anteriores a inicio_almacen.")
    partes = [anterior] + ([almacen] if len(almacen) else [])
    junto = pd.concat(partes, ignore_index=True)
    junto["FECHA_INICIAL"] = pd.to_datetime(junto["FECHA_INICIAL"])
    if junto[PK].duplicated().any():
        raise ErrorSerie("Despachos repetidos entre la semilla y el almacen.")
    return junto.sort_values(PK, kind="mergesort").reset_index(drop=True)


# --------------------------------------------------------------- serie


def _constructor(cfg: TargetConfig) -> TimeSeriesBuilder:
    # Misma configuracion que modeling.dataset.build_time_series.
    return TimeSeriesBuilder(
        {
            "granularidades_min": [cfg.granularity_min],
            "rutas": list(cfg.routes),
            "imputacion_gaps": cfg.gap_imputation,
        }
    )


def extender_grilla(
    serie: pd.DataFrame, hasta: date, cfg: TargetConfig, inicio_jornada_h: int = 4
) -> pd.DataFrame:
    """Agrega a la serie de una ruta las franjas hasta el cierre de la jornada ``hasta``.

    Las franjas nuevas no tienen demanda (``is_gap``), como las que el
    constructor completa entre observaciones; el calendario y el horario
    operativo se calculan con los mismos metodos del constructor.
    """
    paso = pd.Timedelta(minutes=cfg.granularity_min)
    fin = pd.Timestamp(hasta) + pd.Timedelta(days=1, hours=inicio_jornada_h) - paso
    ultimo = serie["timestamp"].max()
    if ultimo >= fin:
        return serie
    nuevas = pd.DataFrame({"timestamp": pd.date_range(ultimo + paso, fin, freq=paso)})
    for c in OBJETIVOS_SERIE:
        nuevas[c] = float("nan")
    nuevas["is_gap"] = True
    constructor = _constructor(cfg)
    nuevas = constructor._enriquecer(nuevas)
    nuevas["granularidad_min"] = cfg.granularity_min
    nuevas["FK_RUTA"] = int(serie["FK_RUTA"].iloc[0])
    nuevas = constructor._enriquecer_con_horario_operativo(nuevas)
    nuevas = nuevas[[c for c in serie.columns if c in nuevas.columns]]
    return pd.concat([serie, nuevas], ignore_index=True)


def construir_serie(
    conjunto_apto: pd.DataFrame,
    cfg: TargetConfig,
    escenario: ScenarioDefinition,
    hasta: date | None,
    version: str,
    hash_fuente: str,
) -> pd.DataFrame:
    """Dataset de modelado del escenario, como ``build_multitarget_datasets``.

    Reproduce ``modeling.dataset.build_modeling_dataset`` sobre un conjunto apto
    en memoria y, con ``hasta``, extiende la grilla de cada ruta hasta el cierre
    de esa jornada antes de calcular las variables.
    """
    fuente = conjunto_apto[
        conjunto_apto["MODEL_READY_OK"].eq(True) & conjunto_apto["FK_RUTA"].isin(cfg.routes)
    ]
    if fuente.empty:
        raise ErrorSerie("El conjunto apto no tiene despachos de las rutas de la piloto.")
    series = build_time_series(fuente, cfg)
    if hasta is not None:
        series = {r: extender_grilla(s, hasta, cfg) for r, s in series.items()}

    # --- Igual que build_modeling_dataset (modeling/dataset.py) ---
    full = pd.concat(series.values(), ignore_index=True)
    full["dataset_version"] = version
    full["source_hash"] = hash_fuente
    featured = add_modeling_features(full, target_col=cfg.target)
    validate_lag_features(featured, target_col=cfg.target)
    validate_lag_features(featured, target_col="pasajeros_por_despacho_real")
    validate_lag_features(featured, target_col="despachos_count_real")
    featured["target_interval_start"] = pd.to_datetime(featured["timestamp"])
    featured["target_interval_end"] = featured["target_interval_start"] + pd.Timedelta(
        minutes=int(cfg.granularity_min)
    )
    featured["feature_cutoff_timestamp"] = featured["target_interval_start"]
    if cfg.operational_only:
        featured = featured[featured["dentro_horario_operativo"].eq(True)].copy()
    if cfg.target == "pasajeros_por_despacho_real":
        featured["target_observed"] = featured["target_pasajeros_por_despacho_observed"]
    else:
        featured["target_observed"] = featured["target_pasajeros_total_observed"]
    base = featured[MODELING_COLUMNS].sort_values(["FK_RUTA", "timestamp"]).reset_index(drop=True)
    dataset, _ = prepare_scenario_dataset(base, cfg, escenario)
    return dataset


def guardar_serie(serie: pd.DataFrame, ruta: Path) -> Path:
    """Guarda la serie versionada de la ejecucion; nunca sobrescribe."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        raise FileExistsError(f"No se sobrescribe: {ruta}")
    serie.to_parquet(ruta, index=False)
    return ruta
