"""
Análisis de productividad por despacho.

Calcula pasajeros transportados por despacho, agregado por
semana y segmentado por ruta. Reporta tanto el valor bruto
como el ajustado por tendencia (regresión OLS), para aislar
el efecto operativo del modelo predictivo de los factores
exógenos del entorno (competencia modal, demografía, etc.).

Estructura de salida: formato long (una fila por semana × ruta).

Indicadores principales
-----------------------
- productividad_bruta      : pasajeros/despacho semanal por ruta
- tendencia_ols            : línea de tendencia estimada por OLS
- productividad_ajustada   : residual + media (aísla efecto operativo)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ProductivityAnalyzer:
    """
    Calcula productividad por despacho con ajuste por tendencia,
    en formato long (semana × ruta).
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = self._preparar(df)

    def _preparar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        mask = df["MODEL_READY_OK"].eq(True) & df["PASAJEROS"].notna()
        df = df.loc[mask].copy()
        df["FECHA_INICIAL"] = pd.to_datetime(df["FECHA_INICIAL"])
        df["semana"] = df["FECHA_INICIAL"].dt.to_period("W").dt.start_time

        logger.info(
            "ProductivityAnalyzer: %d despachos elegibles | Período: %s a %s",
            len(df),
            df["FECHA_INICIAL"].min().date(),
            df["FECHA_INICIAL"].max().date(),
        )
        return df

    def _agregar_semanal_por_ruta(self) -> pd.DataFrame:
        """Agrega despachos y pasajeros por (semana × ruta). Formato long."""
        agg = (
            self._df.groupby(["FK_RUTA", "semana"])
            .agg(
                pasajeros_total=("PASAJEROS", "sum"),
                despachos_total=("PASAJEROS", "count"),
            )
            .reset_index()
        )
        agg["productividad_bruta"] = (agg["pasajeros_total"] / agg["despachos_total"]).round(2)

        # Excluir primera y última semana de cada ruta (suelen ser parciales)
        agg["semana_completa"] = True
        for ruta in agg["FK_RUTA"].unique():
            idx = agg[agg["FK_RUTA"] == ruta].sort_values("semana").index
            if len(idx) > 2:
                agg.loc[idx[0], "semana_completa"] = False
                agg.loc[idx[-1], "semana_completa"] = False

        return agg

    def _ajustar_tendencia_ruta(self, sub_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """Ajusta OLS simple por ruta: productividad ~ tiempo."""
        sub = sub_df[sub_df["semana_completa"]].sort_values("semana").copy()
        sub = sub.reset_index(drop=True)
        sub["t"] = np.arange(len(sub))

        x = sub["t"].values.astype(float)
        y = sub["productividad_bruta"].values.astype(float)
        n = len(x)

        b = (n * (x * y).sum() - x.sum() * y.sum()) / (n * (x**2).sum() - x.sum() ** 2)
        a = (y.sum() - b * x.sum()) / n
        media_y = y.mean()

        sub["tendencia_ols"] = (a + b * sub["t"]).round(2)
        # Residual + media para que la "ajustada" tenga la misma escala
        sub["productividad_ajustada"] = (
            sub["productividad_bruta"] - sub["tendencia_ols"] + media_y
        ).round(2)

        params = {
            "intercepto": round(a, 3),
            "slope_semanal": round(b, 3),
            "slope_mensual_estimado": round(b * 4.33, 3),
            "media_bruta": round(media_y, 2),
            "n_semanas": n,
        }
        return sub, params

    # ── API pública ────────────────────────────────────────────────────────

    def serie_semanal(self) -> pd.DataFrame:
        """
        Productividad bruta y ajustada por (semana × ruta).
        Formato long: una fila por cada combinación.
        """
        agg = self._agregar_semanal_por_ruta()
        resultados = []
        for ruta in sorted(agg["FK_RUTA"].unique()):
            sub = agg[agg["FK_RUTA"] == ruta]
            ajustada, _ = self._ajustar_tendencia_ruta(sub)
            resultados.append(ajustada)
        out = pd.concat(resultados, ignore_index=True)
        cols = [
            "semana",
            "FK_RUTA",
            "pasajeros_total",
            "despachos_total",
            "productividad_bruta",
            "tendencia_ols",
            "productividad_ajustada",
        ]
        return out[cols].sort_values(["semana", "FK_RUTA"]).reset_index(drop=True)

    def summary(self) -> pd.DataFrame:
        """Resumen consolidado por ruta."""
        agg = self._agregar_semanal_por_ruta()
        filas = []
        for ruta in sorted(agg["FK_RUTA"].unique()):
            sub = agg[agg["FK_RUTA"] == ruta]
            ajustada, params = self._ajustar_tendencia_ruta(sub)
            filas.append(
                {
                    "FK_RUTA": int(ruta),
                    "n_semanas_validas": params["n_semanas"],
                    "productividad_promedio_bruta": params["media_bruta"],
                    "productividad_p50": round(ajustada["productividad_bruta"].median(), 2),
                    "productividad_std": round(ajustada["productividad_bruta"].std(), 2),
                    "tendencia_slope_semanal": params["slope_semanal"],
                    "tendencia_slope_mensual_est": params["slope_mensual_estimado"],
                    "primera_semana_estimada": round(ajustada["tendencia_ols"].iloc[0], 2),
                    "ultima_semana_estimada": round(ajustada["tendencia_ols"].iloc[-1], 2),
                    "caida_total_periodo": round(
                        ajustada["tendencia_ols"].iloc[0] - ajustada["tendencia_ols"].iloc[-1], 2
                    ),
                }
            )
        return pd.DataFrame(filas)

    def save(self, output_dir: str | Path = "reports/tables/baseline") -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        self.serie_semanal().to_csv(out / "productivity_weekly_series.csv", index=False)
        self.summary().to_csv(out / "productivity_summary.csv", index=False)
        self._write_text_report(self.summary(), out / "productivity_report.txt")
        logger.info("Productivity reports saved → %s", out)

    def _write_text_report(self, summary: pd.DataFrame, path: Path) -> None:
        lines = [
            "=" * 65,
            "PRODUCTIVIDAD POR DESPACHO — EMPRESA MONTEBELLO",
            "Pasajeros transportados por despacho, semanal por ruta",
            "=" * 65,
            "",
            "DEFINICIÓN",
            "----------",
            "productividad = pasajeros_total / despachos_total",
            "                (por semana, por ruta)",
            "",
            "Se reportan dos versiones:",
            "  1. Bruta:     valor observado semana × ruta",
            "  2. Ajustada: residual + media tras quitar tendencia OLS",
            "                (aísla efecto operativo de deriva estructural)",
            "",
        ]

        for _, row in summary.iterrows():
            r = int(row["FK_RUTA"])
            lines += [
                "─" * 65,
                f"RUTA {r}",
                "─" * 65,
                f"  Semanas válidas analizadas    : {int(row['n_semanas_validas'])}",
                f"  Productividad promedio bruta  : {row['productividad_promedio_bruta']} pas/despacho",
                f"  Mediana (p50)                 : {row['productividad_p50']} pas/despacho",
                f"  Desviación estándar           : {row['productividad_std']} pas/despacho",
                "",
                "  TENDENCIA OLS",
                f"    Slope semanal               : {row['tendencia_slope_semanal']} pas/semana",
                f"    Slope mensual (≈)           : {row['tendencia_slope_mensual_est']} pas/mes",
                f"    Valor estimado 1ª semana    : {row['primera_semana_estimada']} pas/despacho",
                f"    Valor estimado última       : {row['ultima_semana_estimada']} pas/despacho",
                f"    Caída total del período     : {row['caida_total_periodo']} pas/despacho",
                "",
            ]

        lines += [
            "=" * 65,
            "INTERPRETACIÓN",
            "=" * 65,
            "La tendencia decreciente refleja factores exógenos al",
            "sistema de despacho (competencia modal, cambios",
            "demográficos del corredor, etc.). El modelo predictivo",
            "no puede revertir esta tendencia estructural.",
            "",
            "La productividad ajustada por tendencia es la métrica",
            "correcta para evaluar el efecto operativo del modelo",
            "en Fase 4 — mide la mejora atribuible a un despacho",
            "mejor sincronizado con la demanda esperada, aislando",
            "la deriva del entorno.",
            "",
            "META DEL PROYECTO (Fase 4)",
            "--------------------------",
            "Demostrar que la productividad ajustada con simulación",
            "del modelo predictivo es superior a la productividad",
            "ajustada del baseline empírico, en al menos una de las",
            "dos rutas, con significancia estadística.",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
