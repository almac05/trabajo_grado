"""
Cálculo de headway observado e indicadores de irregularidad.

Headway = minutos entre salidas consecutivas de cualquier vehículo
          de la misma ruta, ordenadas por HORA_INICIAL_REAL,
          dentro del horario operativo (04h–19h).

Indicadores principales
-----------------------
headway_mean      : promedio del intervalo entre salidas
headway_std       : desviación estándar
cv_headway        : std / mean  ← KPI principal de irregularidad
headway_p50       : mediana
headway_p95       : percentil 95
bunching_pct      : % intervalos < 3 min  (buses "pegados")
excess_wait_pct   : % intervalos > 30 min (espera excesiva)

Referencia: Ceder (2016), Chen, Liu & Zhu (2020) — citados en
el marco teórico del anteproyecto.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

HORA_OP_INICIO = 4
HORA_OP_FIN = 19
BUNCHING_MIN = 3
EXCESO_MIN = 30

TIPO_DIA_MAP = {
    0: "LABORAL",
    1: "LABORAL",
    2: "LABORAL",
    3: "LABORAL",
    4: "LABORAL",
    5: "SABADO",
    6: "DOMINGO",
}


class HeadwayAnalyzer:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = self._preparar(df)

    def _preparar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        mask = (
            df["MODEL_READY_OK"].eq(True)
            & df["HORA_INICIAL_REAL"].notna()
            & df["HORA_INICIO_H"].between(HORA_OP_INICIO, HORA_OP_FIN)
        )
        df = df.loc[mask].copy()

        df["HORA_INICIAL_REAL"] = pd.to_datetime(df["HORA_INICIAL_REAL"])
        df["FECHA_INICIAL"] = pd.to_datetime(df["FECHA_INICIAL"])
        df["fecha_dia"] = df["FECHA_INICIAL"].dt.date
        df["tipo_dia"] = df["DIA_SEMANA"].map(TIPO_DIA_MAP).fillna("LABORAL")

        df["franja"] = pd.cut(
            df["HORA_INICIO_H"].astype(float),
            bins=[4, 9, 12, 15, 19],
            labels=["PICO_MANANA", "MEDIODIA", "PICO_TARDE", "TARDE_VALLE"],
            right=True,
        ).astype(str)

        df = df.sort_values(["FK_RUTA", "fecha_dia", "HORA_INICIAL_REAL"]).reset_index(drop=True)

        df["headway_min"] = (
            df.groupby(["FK_RUTA", "fecha_dia"])["HORA_INICIAL_REAL"]
            .diff()
            .dt.total_seconds()
            .div(60)
        )

        df = df.loc[df["headway_min"].between(0.1, 120)].copy()

        logger.info(
            "HeadwayAnalyzer: %d intervalos válidos de %d rutas × días",
            len(df),
            df.groupby(["FK_RUTA", "fecha_dia"]).ngroups,
        )
        return df

    def _stats(self, series: pd.Series) -> pd.Series:
        mean = series.mean()
        std = series.std()
        return pd.Series(
            {
                "n_intervalos": len(series),
                "headway_mean": round(mean, 2),
                "headway_std": round(std, 2),
                "cv_headway": round(std / mean, 3) if mean > 0 else np.nan,
                "headway_p50": round(series.median(), 2),
                "headway_p95": round(series.quantile(0.95), 2),
                "bunching_pct": round(100 * (series < BUNCHING_MIN).mean(), 2),
                "excess_wait_pct": round(100 * (series > EXCESO_MIN).mean(), 2),
            }
        )

    def _agg(self, groupby: list[str]) -> pd.DataFrame:
        rows = []
        for keys, grp in self._df.groupby(groupby):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(groupby, keys, strict=False))
            row.update(self._stats(grp["headway_min"]).to_dict())
            rows.append(row)
        return pd.DataFrame(rows)

    def summary(self) -> pd.DataFrame:
        """Resumen global por ruta — tabla principal del baseline."""
        return self._agg(["FK_RUTA"])

    def by_franja(self) -> pd.DataFrame:
        """Detalle por ruta × franja horaria × tipo de día."""
        return self._agg(["FK_RUTA", "franja", "tipo_dia"])

    def by_hour(self) -> pd.DataFrame:
        """Detalle por ruta × hora exacta × tipo de día."""
        return self._agg(["FK_RUTA", "HORA_INICIO_H", "tipo_dia"])

    def save(self, output_dir: str | Path = "reports/tables/baseline") -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.summary().to_csv(out / "headway_summary.csv", index=False)
        self.by_franja().to_csv(out / "headway_by_franja.csv", index=False)
        self.by_hour().to_csv(out / "headway_by_hour.csv", index=False)
        logger.info("Headway guardado → %s", out)
