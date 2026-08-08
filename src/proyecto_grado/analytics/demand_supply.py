"""
Análisis de desajuste demanda-oferta (load factor).

load_factor = pasajeros_total_bin / (despachos_count × capacidad_vehiculo)

Estados
-------
SOBRECARGA : load_factor > 0.85
SUBCARGA   : load_factor < 0.40
OPTIMO     : entre 0.40 y 0.85

Nota: capacidad_vehiculo debe validarse con Montebello.
El default de 80 es un estimado conservador para buses urbanos.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CAP_DEFAULT = 80
U_SOBRE = 0.85
U_SUB = 0.40


class DemandSupplyAnalyzer:
    def __init__(
        self,
        df_ts: pd.DataFrame,
        capacidad_vehiculo: int = CAP_DEFAULT,
    ) -> None:
        self.cap = capacidad_vehiculo
        self._df = self._preparar(df_ts)

    def _preparar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        mask = (
            df["dentro_horario_operativo"].eq(True)
            & df["is_gap"].eq(False)
            & df["despachos_count"].gt(0)
        )
        df = df.loc[mask].copy()

        df["capacidad_ofertada"] = df["despachos_count"] * self.cap
        df["load_factor"] = df["pasajeros_total"] / df["capacidad_ofertada"]

        df["estado_bin"] = np.select(
            [df["load_factor"].gt(U_SOBRE), df["load_factor"].lt(U_SUB)],
            ["SOBRECARGA", "SUBCARGA"],
            default="OPTIMO",
        )
        df["desajuste_abs"] = (df["pasajeros_total"] - df["capacidad_ofertada"]).abs()

        logger.info(
            "DemandSupplyAnalyzer: %d bins operativos | cap=%d pas/veh",
            len(df),
            self.cap,
        )
        return df

    def _stats(self, grp: pd.DataFrame) -> pd.Series:
        lf = grp["load_factor"]
        return pd.Series(
            {
                "n_bins": len(grp),
                "load_factor_mean": round(float(lf.mean()), 3),
                "load_factor_p50": round(float(lf.median()), 3),
                "load_factor_p95": round(float(lf.quantile(0.95)), 3),
                "sobrecarga_pct": round(100 * float(lf.gt(U_SOBRE).mean()), 2),
                "subcarga_pct": round(100 * float(lf.lt(U_SUB).mean()), 2),
                "optimo_pct": round(100 * float(lf.between(U_SUB, U_SOBRE).mean()), 2),
                "desajuste_abs_mean": round(float(grp["desajuste_abs"].mean()), 1),
            }
        )

    def _agg(self, groupby: list[str]) -> pd.DataFrame:
        rows = []
        for keys, grp in self._df.groupby(groupby):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(groupby, keys, strict=False))
            row.update(self._stats(grp).to_dict())
            rows.append(row)
        return pd.DataFrame(rows)

    def summary(self) -> pd.DataFrame:
        return self._agg(["FK_RUTA"])

    def by_franja(self) -> pd.DataFrame:
        return self._agg(["FK_RUTA", "franja_horaria", "tipo_dia"])

    def distribution(self) -> pd.DataFrame:
        dist = self._df.groupby(["FK_RUTA", "estado_bin"]).size().reset_index(name="n_bins")
        dist["pct"] = dist.groupby("FK_RUTA")["n_bins"].transform(
            lambda g: round(100 * g / g.sum(), 2)
        )
        return dist

    def save(self, output_dir: str | Path = "reports/tables/baseline") -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.summary().to_csv(out / "demand_supply_summary.csv", index=False)
        self.by_franja().to_csv(out / "demand_supply_by_franja.csv", index=False)
        self.distribution().to_csv(out / "load_factor_distribution.csv", index=False)
        logger.info("Demand-supply guardado → %s", out)
