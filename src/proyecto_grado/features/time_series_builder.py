"""Construccion de la serie temporal agregada a partir del dataset model-ready."""

import logging
from datetime import date
from pathlib import Path
from typing import Literal

import holidays
import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_OP_HOURS_PATH = PROJECT_ROOT / "data" / "processed" / "operational_hours.parquet"

ImputacionGaps = Literal["ffill", "zero", "mark"]

_DEFAULTS: dict = {
    "granularidades_min": [15, 30, 60],
    "franjas_horarias": {
        "MADRUGADA": [0, 5],
        "MANANA": [6, 11],
        "MEDIODIA": [12, 13],
        "TARDE": [14, 18],
        "NOCHE": [19, 23],
    },
    "imputacion_gaps": "zero",
    "cobertura_minima_dias": 30,
    "rutas": [1, 3],
    # Columna fuente para agregar demanda por bin temporal. PASAJEROS es el
    # conteo crudo del dispositivo APC (incluye eventos de puerta inflando el
    # conteo); PASAJEROS_REALES = (PASAJEROS - ALARMAS).clip(lower=0) es la
    # correccion (ver etl/transforms.py::run_block4).
    "columna_pasajeros": "PASAJEROS_REALES",
}


def _load_features_yaml() -> dict:
    """Carga configs/features.yaml si existe; retorna dict vacio si falta."""
    path = PROJECT_ROOT / "configs" / "features.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class TimeSeriesBuilder:
    """Construye la serie temporal agregada por franja horaria desde despachos model-ready.

    Agrega despachos individuales en bins de granularidad_min minutos, calcula
    variables objetivo (pasajeros_total, despachos_count, pasajeros_promedio,
    ocupacion_p95) y enriquece con contexto temporal (tipo_dia, festivos Colombia,
    franja_horaria, etc.). Puede producir la serie por ruta o para todas.

    Parameters
    ----------
    cfg : dict | None
        Configuracion de features. Si es None, carga configs/features.yaml.
        Las claves reconocidas son: granularidades_min, franjas_horarias,
        imputacion_gaps, rutas, cobertura_minima_dias.
        Para compatibilidad, acepta tambien granularidad_min (singular), que se
        convierte internamente a la lista [granularidad_min].
    """

    def __init__(self, cfg: dict | None = None) -> None:
        base: dict = {**_DEFAULTS}
        overrides = cfg if cfg is not None else _load_features_yaml()

        # Backward compat: granularidad_min singular → lista de un elemento
        if "granularidad_min" in overrides and "granularidades_min" not in overrides:
            overrides = {**overrides, "granularidades_min": [int(overrides["granularidad_min"])]}

        base.update(overrides)

        self.granularidades_min: list[int] = [int(g) for g in base["granularidades_min"]]
        self.franjas_horarias: dict[str, list[int]] = base["franjas_horarias"]
        self.imputacion_gaps: ImputacionGaps = base["imputacion_gaps"]
        self.rutas: list[int] = list(base["rutas"])
        self.columna_pasajeros: str = str(base["columna_pasajeros"])
        self._colombia_holidays: dict[int, set[date]] = {}

        logger.info(
            "TimeSeriesBuilder inicializado: granularidades=%s imputacion=%s rutas=%s columna_pasajeros=%s",
            self.granularidades_min,
            self.imputacion_gaps,
            self.rutas,
            self.columna_pasajeros,
        )

    def _get_colombia_holidays(self, year: int) -> set[date]:
        """Retorna el conjunto de fechas festivas en Colombia para un año dado."""
        if year not in self._colombia_holidays:
            self._colombia_holidays[year] = set(holidays.Colombia(years=year))
        return self._colombia_holidays[year]

    def _franja_horaria(self, hora: int) -> str:
        """Clasifica la hora (0-23) en la franja horaria correspondiente."""
        for nombre, rango in self.franjas_horarias.items():
            if rango[0] <= hora <= rango[1]:
                return nombre
        return "NOCHE"

    def _agregar(self, df: pd.DataFrame, granularidad_min: int) -> pd.DataFrame:
        """Agrega despachos por bins de granularidad_min minutos.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame filtrado con HORA_INICIAL_REAL, la columna de pasajeros
            configurada (``self.columna_pasajeros``) y PK_INTERVALO_DESPACHO
            ya limpios.
        granularidad_min : int
            Tamaño del bin temporal en minutos.

        Returns
        -------
        pd.DataFrame
            Una fila por bin temporal con las cuatro variables objetivo.
        """
        freq = f"{granularidad_min}min"
        col = self.columna_pasajeros
        df = df.copy()
        df["_ts_bin"] = df["HORA_INICIAL_REAL"].dt.floor(freq)

        agg = (
            df.groupby("_ts_bin", sort=True)
            .agg(
                pasajeros_total=(col, "sum"),
                despachos_count=("PK_INTERVALO_DESPACHO", "count"),
                pasajeros_promedio=(col, "mean"),
                ocupacion_p95=(col, lambda x: float(np.percentile(x.to_numpy(), 95))),
            )
            .reset_index()
            .rename(columns={"_ts_bin": "timestamp"})
        )
        return agg

    def _completar_grilla(self, agg: pd.DataFrame, granularidad_min: int) -> pd.DataFrame:
        """Expande la serie al grid completo e imputa franjas sin despachos.

        Parameters
        ----------
        agg : pd.DataFrame
            Serie agregada con posibles gaps temporales.
        granularidad_min : int
            Tamaño del bin temporal en minutos.

        Returns
        -------
        pd.DataFrame
            Serie con grilla completa y columna is_gap indicando huecos.
        """
        if agg.empty:
            return agg

        freq = f"{granularidad_min}min"
        grilla = pd.date_range(
            start=agg["timestamp"].min(),
            end=agg["timestamp"].max(),
            freq=freq,
            name="timestamp",
        )
        agg = agg.set_index("timestamp").reindex(grilla).reset_index()

        # Calcular mascara de gaps ANTES de imputar
        gap_mask: pd.Series = agg["despachos_count"].isna()

        obj_cols = ["pasajeros_total", "despachos_count", "pasajeros_promedio", "ocupacion_p95"]

        if self.imputacion_gaps == "ffill":
            agg[obj_cols] = agg[obj_cols].ffill()
        elif self.imputacion_gaps == "zero":
            agg["pasajeros_total"] = agg["pasajeros_total"].fillna(0.0)
            agg["despachos_count"] = agg["despachos_count"].fillna(0).astype("int64")
            agg["pasajeros_promedio"] = agg["pasajeros_promedio"].fillna(0.0)
            agg["ocupacion_p95"] = agg["ocupacion_p95"].fillna(0.0)
        # "mark": dejar NaN, la columna is_gap identifica los huecos

        agg["is_gap"] = gap_mask
        return agg

    def _enriquecer(self, agg: pd.DataFrame) -> pd.DataFrame:
        """Agrega variables de contexto temporal a la serie agregada.

        Parameters
        ----------
        agg : pd.DataFrame
            Serie con grilla completa y variables objetivo ya imputadas.

        Returns
        -------
        pd.DataFrame
            Serie enriquecida con hora_del_dia, tipo_dia, franja_horaria, etc.
        """
        ts: pd.Series = agg["timestamp"]

        agg["hora_del_dia"] = ts.dt.hour.astype("int64")
        agg["dia_semana"] = ts.dt.dayofweek.astype("int64")
        agg["es_fin_semana"] = agg["dia_semana"] >= 5
        agg["mes"] = ts.dt.month.astype("int64")
        agg["semana_anio"] = ts.dt.isocalendar().week.to_numpy().astype("int64")
        agg["trimestre"] = ts.dt.quarter.astype("int64")
        agg["franja_horaria"] = agg["hora_del_dia"].map(self._franja_horaria)

        # Festivos Colombia — construir conjunto para todos los anos del dataset
        years = {d.year for d in ts.dt.date}
        festivos: set[date] = set()
        for y in years:
            festivos |= self._get_colombia_holidays(y)

        fecha_date: pd.Series = ts.dt.date
        agg["es_festivo"] = fecha_date.map(lambda d: d in festivos)

        # tipo_dia vectorizado con np.select
        # FESTIVO_PUENTE: lunes festivo colombiano (Ley Emiliani)
        conditions = [
            agg["es_festivo"] & (agg["dia_semana"] == 0),
            agg["es_festivo"],
            agg["dia_semana"] == 5,
            agg["dia_semana"] == 6,
        ]
        choices = ["FESTIVO_PUENTE", "FESTIVO", "SABADO", "DOMINGO"]
        agg["tipo_dia"] = np.select(conditions, choices, default="LABORAL")

        return agg

    def _enriquecer_con_horario_operativo(self, agg: pd.DataFrame) -> pd.DataFrame:
        """Añade columnas dentro_horario_operativo y gap_tipo si existe el Parquet de horarios.

        Requiere que agg tenga las columnas tipo_dia, FK_RUTA, granularidad_min,
        timestamp e is_gap. Si el archivo de horarios no existe o las columnas
        faltan, retorna agg sin cambios.
        """
        if not _OP_HOURS_PATH.exists():
            return agg
        if "FK_RUTA" not in agg.columns or agg.empty:
            return agg

        try:
            op = pd.read_parquet(_OP_HOURS_PATH)
        except Exception as exc:
            logger.warning("No se pudo cargar operational_hours.parquet: %s", exc)
            return agg

        ruta = int(agg["FK_RUTA"].iloc[0])
        gran = int(agg["granularidad_min"].iloc[0])

        op_sub = op[
            (op["ruta"] == ruta)
            & (op["granularidad_min"] == gran)
            & (op["hora_inicio_op_min"] >= 0)
        ]
        if op_sub.empty:
            return agg

        lookup: dict[str, tuple[int, int]] = {
            str(r["tipo_dia"]): (int(r["hora_inicio_op_min"]), int(r["hora_fin_op_min"]))
            for _, r in op_sub.iterrows()
        }

        agg = agg.copy()
        agg["_minuto_dia"] = agg["timestamp"].dt.hour * 60 + agg["timestamp"].dt.minute
        agg["dentro_horario_operativo"] = False

        for tipo, (inicio, fin) in lookup.items():
            mask = (
                (agg["tipo_dia"] == tipo)
                & (agg["_minuto_dia"] >= inicio)
                & (agg["_minuto_dia"] <= fin)
            )
            agg.loc[mask, "dentro_horario_operativo"] = True

        conditions = [
            ~agg["is_gap"],
            agg["is_gap"] & agg["dentro_horario_operativo"],
        ]
        choices = ["operativo", "gap_anomalo"]
        agg["gap_tipo"] = np.select(conditions, choices, default="fuera_operacion")
        agg = agg.drop(columns=["_minuto_dia"])

        logger.debug(
            "Horario operativo aplicado: ruta=%d gran=%d gap_anomalo=%d fuera_op=%d",
            ruta,
            gran,
            int((agg["gap_tipo"] == "gap_anomalo").sum()),
            int((agg["gap_tipo"] == "fuera_operacion").sum()),
        )
        return agg

    def build(
        self,
        df: pd.DataFrame,
        ruta: int | None = None,
        granularidad_min: int | None = None,
    ) -> pd.DataFrame:
        """Construye la serie temporal para una ruta y granularidad especificas.

        Parameters
        ----------
        df : pd.DataFrame
            Dataset model-ready con al menos HORA_INICIAL_REAL, FK_RUTA,
            la columna de pasajeros configurada (``self.columna_pasajeros``)
            y PK_INTERVALO_DESPACHO.
        ruta : int | None
            Si se indica, filtra solo esa ruta antes de agregar.
            Si es None, agrega todas las rutas juntas.
        granularidad_min : int | None
            Tamaño del bin temporal en minutos. Si es None, usa el primer
            valor de self.granularidades_min.

        Returns
        -------
        pd.DataFrame
            Serie temporal agregada con variables objetivo, contextuales y
            la columna granularidad_min para trazabilidad.
            DataFrame vacio si no hay datos para la ruta indicada.
        """
        if granularidad_min is None:
            granularidad_min = self.granularidades_min[0]

        col = self.columna_pasajeros
        df = df.copy()
        df["HORA_INICIAL_REAL"] = pd.to_datetime(df["HORA_INICIAL_REAL"], errors="coerce")
        df["FK_RUTA"] = pd.to_numeric(df["FK_RUTA"], errors="coerce")
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["HORA_INICIAL_REAL", col, "FK_RUTA"])
        df["FK_RUTA"] = df["FK_RUTA"].astype(int)

        if ruta is not None:
            df = df[df["FK_RUTA"] == ruta].copy()
            logger.info(
                "TimeSeriesBuilder.build ruta=%d gran=%dmin filas_input=%d",
                ruta,
                granularidad_min,
                len(df),
            )
        else:
            logger.info(
                "TimeSeriesBuilder.build todas_rutas gran=%dmin filas_input=%d",
                granularidad_min,
                len(df),
            )

        if df.empty:
            logger.warning("Sin datos para ruta=%s — retornando serie vacia", ruta)
            return pd.DataFrame()

        agg = self._agregar(df, granularidad_min)
        agg = self._completar_grilla(agg, granularidad_min)
        agg = self._enriquecer(agg)
        agg["granularidad_min"] = granularidad_min

        if ruta is not None:
            agg["FK_RUTA"] = ruta

        agg = self._enriquecer_con_horario_operativo(agg)

        logger.info(
            "Serie construida: ruta=%s gran=%dmin filas=%d rango=[%s, %s]",
            ruta,
            granularidad_min,
            len(agg),
            agg["timestamp"].min(),
            agg["timestamp"].max(),
        )
        return agg

    def build_all(self, df: pd.DataFrame) -> dict[tuple[int, int], pd.DataFrame]:
        """Construye la serie temporal para cada combinacion ruta x granularidad.

        Parameters
        ----------
        df : pd.DataFrame
            Dataset model-ready completo (todas las rutas).

        Returns
        -------
        dict[tuple[int, int], pd.DataFrame]
            Clave: (FK_RUTA, granularidad_min). Valor: serie temporal de esa combinacion.
        """
        result: dict[tuple[int, int], pd.DataFrame] = {}
        for r in self.rutas:
            for gran in self.granularidades_min:
                logger.info("Construyendo serie: ruta=%d granularidad=%dmin ...", r, gran)
                result[(r, gran)] = self.build(df, ruta=r, granularidad_min=gran)
        return result
