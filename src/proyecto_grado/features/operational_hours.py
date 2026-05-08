"""Estimacion del horario operativo real desde series temporales de despachos.

Calcula por (tipo_dia x ruta x granularidad_min) el rango horario en que opera
el servicio y distingue gaps anomalos de franjas fuera de operacion.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

_TIPOS_DIA_ORDEN: list[str] = [
    "LABORAL",
    "SABADO",
    "DOMINGO",
    "FESTIVO",
    "FESTIVO_PUENTE",
]

_DEFAULTS: dict[str, Any] = {
    "umbral_actividad": 0.10,
    "umbral_anomalia": 0.30,
    "min_dias_muestra": 10,
    "incluir_festivo_puente": True,
}


def _load_horario_cfg() -> dict[str, Any]:
    path = PROJECT_ROOT / "configs" / "features.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        full = yaml.safe_load(f) or {}
    return full.get("horario_operativo", {})


def classify_tipo_dia_ext(dia_semana: int, es_festivo: bool) -> str:
    """Clasifica el tipo de dia con distincion de lunes festivo (puente).

    Parameters
    ----------
    dia_semana : int
        Dia de la semana (0=lunes, …, 6=domingo).
    es_festivo : bool
        True si la fecha es festivo en Colombia.

    Returns
    -------
    str
        Uno de: LABORAL, SABADO, DOMINGO, FESTIVO, FESTIVO_PUENTE.
    """
    if es_festivo:
        return "FESTIVO_PUENTE" if dia_semana == 0 else "FESTIVO"
    if dia_semana == 5:
        return "SABADO"
    if dia_semana == 6:
        return "DOMINGO"
    return "LABORAL"


class OperationalHoursEstimator:
    """Estima el horario operativo de cada ruta desde las series temporales.

    Para cada combinacion (tipo_dia x ruta x granularidad_min) calcula el rango
    horario en que opera el servicio basandose en la frecuencia historica de
    franjas con al menos un despacho. Reporta franjas anomalas (dentro del
    horario pero con baja actividad) y cobertura interna.

    Parameters
    ----------
    cfg : dict | None
        Parametros del bloque `horario_operativo` en features.yaml.
        Si es None, carga desde el archivo de configuracion.
    """

    TIPOS_DIA: list[str] = _TIPOS_DIA_ORDEN

    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        base: dict[str, Any] = {**_DEFAULTS}
        overrides = cfg if cfg is not None else _load_horario_cfg()
        base.update(overrides)

        self.umbral_actividad: float = float(base["umbral_actividad"])
        self.umbral_anomalia: float = float(base["umbral_anomalia"])
        self.min_dias_muestra: int = int(base["min_dias_muestra"])
        self.incluir_festivo_puente: bool = bool(base["incluir_festivo_puente"])
        self.result_: pd.DataFrame = pd.DataFrame()

        logger.info(
            "OperationalHoursEstimator: umbral_act=%.2f umbral_anom=%.2f "
            "min_dias=%d festivo_puente=%s",
            self.umbral_actividad,
            self.umbral_anomalia,
            self.min_dias_muestra,
            self.incluir_festivo_puente,
        )

    def _tipos_activos(self) -> list[str]:
        tipos = ["LABORAL", "SABADO", "DOMINGO", "FESTIVO"]
        if self.incluir_festivo_puente:
            tipos.append("FESTIVO_PUENTE")
        return tipos

    @staticmethod
    def _add_tipo_dia_ext(df: pd.DataFrame) -> pd.DataFrame:
        """Agrega columna tipo_dia_ext con clasificacion extendida (incluye FESTIVO_PUENTE)."""
        df = df.copy()
        df["tipo_dia_ext"] = [
            classify_tipo_dia_ext(int(ds), bool(ef))
            for ds, ef in zip(df["dia_semana"], df["es_festivo"], strict=True)
        ]
        return df

    def _compute_franjas(self, subset: pd.DataFrame) -> pd.DataFrame:
        """Calcula pct_activa por franja (minuto_dia) para un subset de tipo_dia."""
        activos = (
            subset[~subset["is_gap"]]
            .groupby("minuto_dia")["fecha"]
            .nunique()
            .rename("dias_con_despacho")
        )
        total_g = subset.groupby("minuto_dia")["fecha"].nunique().rename("total_dias")
        franjas = pd.DataFrame({"dias_con_despacho": activos, "total_dias": total_g}).fillna(
            {"dias_con_despacho": 0}
        )
        franjas["pct_activa"] = (
            franjas["dias_con_despacho"] / franjas["total_dias"].replace(0, np.nan)
        ).fillna(0.0)
        return franjas.sort_index()

    def _empty_row(self, ruta: int, gran: int, tipo_dia: str, n_dias: int) -> dict[str, Any]:
        return {
            "tipo_dia": tipo_dia,
            "ruta": ruta,
            "granularidad_min": gran,
            "hora_inicio_op": "",
            "hora_fin_op": "",
            "hora_inicio_op_min": -1,
            "hora_fin_op_min": -1,
            "duracion_operativa_h": 0.0,
            "n_dias_muestra": n_dias,
            "n_dias_usado": 0,
            "umbral_usado": self.umbral_actividad,
            "fallback_laboral": False,
            "franjas_anomalas_count": 0,
            "pct_cobertura_dentro_horario": 0.0,
        }

    def _estimate_one(
        self,
        df: pd.DataFrame,
        ruta: int,
        gran: int,
        tipo_dia: str,
        laboral_rows: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """Estima el horario operativo para una combinacion tipo_dia x ruta x granularidad."""
        subset = df[df["tipo_dia_ext"] == tipo_dia].copy()
        n_dias = int(subset["fecha"].nunique())
        fallback_used = False

        if n_dias < self.min_dias_muestra:
            if tipo_dia != "LABORAL" and laboral_rows is not None and not laboral_rows.empty:
                logger.warning(
                    "ruta=%d gran=%d tipo=%s: solo %d dias (< %d) — usando LABORAL como proxy",
                    ruta,
                    gran,
                    tipo_dia,
                    n_dias,
                    self.min_dias_muestra,
                )
                subset = laboral_rows.copy()
                fallback_used = True
            else:
                logger.warning(
                    "ruta=%d gran=%d tipo=%s: solo %d dias (< %d), sin fallback",
                    ruta,
                    gran,
                    tipo_dia,
                    n_dias,
                    self.min_dias_muestra,
                )

        if subset.empty:
            return self._empty_row(ruta, gran, tipo_dia, n_dias)

        n_dias_usado = int(subset["fecha"].nunique())
        franjas = self._compute_franjas(subset)

        activas_mask = franjas["pct_activa"] >= self.umbral_actividad
        if not activas_mask.any():
            return self._empty_row(ruta, gran, tipo_dia, n_dias)

        min_activo = int(franjas[activas_mask].index.min())
        max_activo = int(franjas[activas_mask].index.max())

        hora_inicio_op = f"{min_activo // 60:02d}:{min_activo % 60:02d}"
        hora_fin_op = f"{max_activo // 60:02d}:{max_activo % 60:02d}"
        duracion_h = round((max_activo - min_activo + gran) / 60.0, 2)

        within = franjas[(franjas.index >= min_activo) & (franjas.index <= max_activo)]
        total_en_rango = len(within)
        franjas_anomalas = int((within["pct_activa"] < self.umbral_anomalia).sum())
        activas_en_rango = int(activas_mask.loc[within.index].sum())
        pct_cobertura = round(activas_en_rango / total_en_rango, 4) if total_en_rango > 0 else 0.0

        return {
            "tipo_dia": tipo_dia,
            "ruta": ruta,
            "granularidad_min": gran,
            "hora_inicio_op": hora_inicio_op,
            "hora_fin_op": hora_fin_op,
            "hora_inicio_op_min": min_activo,
            "hora_fin_op_min": max_activo,
            "duracion_operativa_h": duracion_h,
            "n_dias_muestra": n_dias,
            "n_dias_usado": n_dias_usado,
            "umbral_usado": self.umbral_actividad,
            "fallback_laboral": fallback_used,
            "franjas_anomalas_count": franjas_anomalas,
            "pct_cobertura_dentro_horario": pct_cobertura,
        }

    def fit(self, series_dict: dict[tuple[int, int], pd.DataFrame]) -> pd.DataFrame:
        """Estima el horario operativo para cada combinacion del diccionario de series.

        Parameters
        ----------
        series_dict : dict[tuple[int, int], pd.DataFrame]
            Diccionario {(ruta, granularidad_min): DataFrame} con series
            enriquecidas (columnas: timestamp, is_gap, dia_semana, es_festivo).

        Returns
        -------
        pd.DataFrame
            Tabla con horarios operativos por tipo_dia x ruta x granularidad_min.
        """
        rows: list[dict[str, Any]] = []

        for (ruta, gran), df in series_dict.items():
            logger.info("Estimando horario operativo: ruta=%d gran=%dmin ...", ruta, gran)
            if df.empty:
                continue

            required = {"timestamp", "is_gap", "dia_semana", "es_festivo"}
            missing = required - set(df.columns)
            if missing:
                logger.error("Columnas faltantes en serie ruta=%d gran=%d: %s", ruta, gran, missing)
                continue

            df = self._add_tipo_dia_ext(df)
            df = df.copy()
            df["fecha"] = df["timestamp"].dt.date
            df["minuto_dia"] = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute

            laboral_subset = df[df["tipo_dia_ext"] == "LABORAL"].copy()

            for tipo in self._tipos_activos():
                row = self._estimate_one(df, ruta, gran, tipo, laboral_rows=laboral_subset)
                rows.append(row)

        self.result_ = pd.DataFrame(rows)
        logger.info(
            "Estimacion completada: %d combinaciones tipo_dia x ruta x granularidad",
            len(self.result_),
        )
        return self.result_

    def save(self, output_dir: Path, report_dir: Path) -> None:
        """Guarda la tabla de horarios como Parquet y como CSV de resumen."""
        if self.result_.empty:
            logger.warning("Sin resultados. Ejecuta fit() primero.")
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = output_dir / "operational_hours.parquet"
        csv_path = report_dir / "operational_hours_summary.csv"

        self.result_.to_parquet(parquet_path, index=False)
        self.result_.to_csv(csv_path, index=False)
        logger.info("Horarios guardados: %s", parquet_path)
        logger.info("Resumen CSV: %s", csv_path)

    def plot_heatmap(
        self,
        series_dict: dict[tuple[int, int], pd.DataFrame],
        ruta: int,
        gran: int,
        output_dir: Path,
    ) -> Path | None:
        """Genera heatmap de pct_activa por tipo_dia x franja horaria.

        Parameters
        ----------
        series_dict : dict[tuple[int, int], pd.DataFrame]
            Diccionario con las series temporales.
        ruta : int
            Ruta a visualizar.
        gran : int
            Granularidad en minutos.
        output_dir : Path
            Directorio de salida para la imagen PNG.

        Returns
        -------
        Path | None
            Ruta del archivo generado, o None si no hay datos.
        """
        key = (ruta, gran)
        if key not in series_dict or series_dict[key].empty:
            logger.warning("Sin datos para ruta=%d gran=%d — heatmap omitido", ruta, gran)
            return None

        df = self._add_tipo_dia_ext(series_dict[key])
        df = df.copy()
        df["fecha"] = df["timestamp"].dt.date
        df["minuto_dia"] = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute

        tipos = [t for t in self._tipos_activos() if (df["tipo_dia_ext"] == t).any()]
        all_minutes = sorted(df["minuto_dia"].unique())

        matrix: dict[str, list[float]] = {}
        for tipo in tipos:
            sub = df[df["tipo_dia_ext"] == tipo]
            activos_g = sub[~sub["is_gap"]].groupby("minuto_dia")["fecha"].nunique()
            total_g = sub.groupby("minuto_dia")["fecha"].nunique()
            matrix[tipo] = [
                int(activos_g.get(m, 0)) / int(total_g.get(m, 1))
                if int(total_g.get(m, 0)) > 0
                else 0.0
                for m in all_minutes
            ]

        mat_df = pd.DataFrame(matrix, index=all_minutes)

        n_slots = len(all_minutes)
        step = max(1, n_slots // 20)
        y_labels = [
            f"{m // 60:02d}:{m % 60:02d}" if i % step == 0 else ""
            for i, m in enumerate(all_minutes)
        ]

        fig_h = max(8, n_slots // 5)
        fig, ax = plt.subplots(figsize=(len(tipos) * 2 + 2, fig_h))
        im = ax.imshow(mat_df.values, aspect="auto", cmap="YlOrRd", vmin=0.0, vmax=1.0)
        ax.set_xticks(range(len(tipos)))
        ax.set_xticklabels(tipos, rotation=30, ha="right", fontsize=9)
        ax.set_yticks(range(n_slots))
        ax.set_yticklabels(y_labels, fontsize=7)
        ax.set_title(
            f"Cobertura operativa — ruta {ruta} | {gran} min",
            fontsize=11,
            pad=12,
        )
        ax.set_xlabel("Tipo de dia", fontsize=9)
        ax.set_ylabel("Franja horaria (HH:MM)", fontsize=9)
        plt.colorbar(im, ax=ax, label="pct_activa")
        plt.tight_layout()

        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"operational_heatmap_{ruta}_{gran}min.png"
        fig.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        logger.info("Heatmap guardado: %s", out_path)
        return out_path
