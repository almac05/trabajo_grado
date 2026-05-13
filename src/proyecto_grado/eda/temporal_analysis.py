"""Análisis Exploratorio de Datos temporal para las series de demanda Montebello."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import acf, adfuller, pacf

from proyecto_grado.etl.config import MODEL_READY_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

_TS_FILE_PATTERN = re.compile(r"ts_ruta(\d+)_g(\d+)min")

_TIME_SERIES_DIR = PROJECT_ROOT / "data" / "processed" / "time_series"
_EDA_DIR = PROJECT_ROOT / "data" / "processed" / "eda"
_MODEL_READY_PATH = Path(MODEL_READY_DIR) / "despachos_model_ready.parquet"
_REPORTS_DIR = PROJECT_ROOT / "reports" / "tables"

WEEKDAY_NAMES = {
    0: "Lunes",
    1: "Martes",
    2: "Miercoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sabado",
    6: "Domingo",
}


def _annotate_pico_valle(df: pd.DataFrame) -> pd.DataFrame:
    """Anota horas pico (media > p75 del día) y valle (media < p25)."""
    p75_d = df["media"].quantile(0.75)
    p25_d = df["media"].quantile(0.25)
    df = df.copy()
    df["es_pico"] = df["media"] > p75_d
    df["es_valle"] = df["media"] < p25_d

    mean_pico_vals = df.loc[df["es_pico"], "media"]
    mean_valle_vals = df.loc[df["es_valle"], "media"]
    mean_pico = float(mean_pico_vals.mean()) if not mean_pico_vals.empty else np.nan
    mean_valle = float(mean_valle_vals.mean()) if not mean_valle_vals.empty else np.nan

    if pd.notna(mean_valle) and mean_valle > 0 and pd.notna(mean_pico):
        ratio: float = mean_pico / mean_valle
    else:
        ratio = np.nan

    df["ratio_pico_valle"] = ratio
    df["horas_pico"] = ",".join(str(int(h)) for h in sorted(df.loc[df["es_pico"], "hora_del_dia"]))
    df["horas_valle"] = ",".join(
        str(int(h)) for h in sorted(df.loc[df["es_valle"], "hora_del_dia"])
    )
    return df


class TemporalEDA:
    """Calcula y persiste análisis EDA temporal de la demanda Montebello.

    Todos los análisis se restringen a franjas ``gap_tipo == 'operativo'`` salvo
    indicación explícita. Los métodos retornan DataFrames serializables para que
    el dashboard los consuma sin recalcular.

    Parameters
    ----------
    ts_dir:
        Directorio de series temporales (``ts_ruta*_g*min.parquet``).
        Si es ``None`` usa el path por defecto del proyecto.
    eda_dir:
        Directorio de salida de artefactos EDA.
        Si es ``None`` usa ``data/processed/eda/``.
    model_ready_path:
        Parquet model-ready para correlación de features.
        Si es ``None`` usa el path canónico del proyecto.
    """

    def __init__(
        self,
        ts_dir: Path | None = None,
        eda_dir: Path | None = None,
        model_ready_path: Path | None = None,
    ) -> None:
        self.ts_dir = Path(ts_dir) if ts_dir else _TIME_SERIES_DIR
        self.eda_dir = Path(eda_dir) if eda_dir else _EDA_DIR
        self.model_ready_path = Path(model_ready_path) if model_ready_path else _MODEL_READY_PATH
        self.eda_dir.mkdir(parents=True, exist_ok=True)
        self._series_cache: dict[tuple[int, int], pd.DataFrame] | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_series(self) -> dict[tuple[int, int], pd.DataFrame]:
        """Carga series temporales desde disco, filtrando a ``gap_tipo=='operativo'``."""
        if self._series_cache is not None:
            return self._series_cache

        series: dict[tuple[int, int], pd.DataFrame] = {}
        for path in sorted(self.ts_dir.glob("ts_ruta*_g*min.parquet")):
            m = _TS_FILE_PATTERN.match(path.stem)
            if not m:
                continue
            ruta, gran = int(m.group(1)), int(m.group(2))
            df = pd.read_parquet(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
            if "gap_tipo" in df.columns:
                df = df[df["gap_tipo"] == "operativo"].copy()
            series[(ruta, gran)] = df
            logger.info("Serie operativo cargada: ruta=%d gran=%dmin n=%d", ruta, gran, len(df))

        self._series_cache = series
        return series

    # ------------------------------------------------------------------
    # 1.1  Perfil intradía
    # ------------------------------------------------------------------

    def perfil_intraday(self) -> dict[tuple[int, int], pd.DataFrame]:
        """Perfil de demanda intradía: estadísticas por hora x tipo_dia.

        Calcula media, mediana, p25, p75, p95 de ``pasajeros_total`` por hora
        del día para cada combinación ruta x granularidad x tipo_dia.
        Identifica horas pico (media > p75 del día) y horas valle (media < p25).

        Returns
        -------
        dict[(ruta, gran), pd.DataFrame]
            Columnas: tipo_dia, hora_del_dia, media, mediana, p25, p75, p95,
            es_pico, es_valle, ratio_pico_valle, horas_pico, horas_valle.
        """
        series = self._load_series()
        results: dict[tuple[int, int], pd.DataFrame] = {}

        for (ruta, gran), df in series.items():
            if df.empty or "hora_del_dia" not in df.columns:
                continue

            has_tipo_dia = "tipo_dia" in df.columns
            group_keys = ["tipo_dia", "hora_del_dia"] if has_tipo_dia else ["hora_del_dia"]

            grp = df.groupby(group_keys, dropna=False)["pasajeros_total"]
            stats = pd.DataFrame(
                {
                    "media": grp.mean(),
                    "mediana": grp.median(),
                    "p25": grp.quantile(0.25),
                    "p75": grp.quantile(0.75),
                    "p95": grp.quantile(0.95),
                }
            ).reset_index()

            if has_tipo_dia:
                chunks: list[pd.DataFrame] = []
                for _tipo_dia, sub in stats.groupby("tipo_dia"):
                    chunks.append(_annotate_pico_valle(sub.copy()))
                result = pd.concat(chunks, ignore_index=True)
            else:
                result = _annotate_pico_valle(stats)

            out_path = self.eda_dir / f"perfil_intraday_{ruta}_g{gran}min.parquet"
            result.to_parquet(out_path, index=False)
            results[(ruta, gran)] = result
            logger.info("perfil_intraday: ruta=%d gran=%dmin → %s", ruta, gran, out_path.name)

        return results

    # ------------------------------------------------------------------
    # 1.2  Perfil semanal
    # ------------------------------------------------------------------

    def perfil_semanal(self) -> dict[tuple[int, int], pd.DataFrame]:
        """Demanda total/promedio por día de semana con índice de variabilidad.

        Returns
        -------
        dict[(ruta, gran), pd.DataFrame]
            Columnas: dia_semana, nombre_dia, demanda_total, demanda_promedio,
            variabilidad, es_max, es_min.
        """
        series = self._load_series()
        results: dict[tuple[int, int], pd.DataFrame] = {}

        for (ruta, gran), df in series.items():
            if df.empty or "dia_semana" not in df.columns:
                continue

            grp = df.groupby("dia_semana", dropna=False)["pasajeros_total"]
            prom = grp.mean()
            stats = pd.DataFrame(
                {
                    "demanda_total": grp.sum(),
                    "demanda_promedio": prom,
                    "variabilidad": grp.std() / prom.where(prom > 0),
                }
            ).reset_index()

            stats["nombre_dia"] = stats["dia_semana"].map(WEEKDAY_NAMES)
            max_prom = stats["demanda_promedio"].max()
            min_prom = stats["demanda_promedio"].min()
            stats["es_max"] = stats["demanda_promedio"] == max_prom
            stats["es_min"] = stats["demanda_promedio"] == min_prom

            out_path = self.eda_dir / f"perfil_semanal_{ruta}_g{gran}min.parquet"
            stats.to_parquet(out_path, index=False)
            results[(ruta, gran)] = stats
            logger.info("perfil_semanal: ruta=%d gran=%dmin → %s", ruta, gran, out_path.name)

        return results

    # ------------------------------------------------------------------
    # 1.3  Perfil mensual y tendencia
    # ------------------------------------------------------------------

    def perfil_mensual(self) -> dict[int, pd.DataFrame]:
        """Demanda mensual/semanal con tendencia OLS y detección de meses atípicos.

        Usa granularidad 60 min por preferencia (cae a la primera disponible).
        La tendencia lineal se ajusta sobre la serie diaria agregada.

        Returns
        -------
        dict[ruta, pd.DataFrame]
            Columnas: periodo, tipo_periodo, demanda_total, tendencia_slope,
            tendencia_intercept, es_atipico.
        """
        series = self._load_series()
        rutas = sorted({r for r, _ in series})
        results: dict[int, pd.DataFrame] = {}

        for ruta in rutas:
            df: pd.DataFrame | None = None
            for pref_gran in [60, 30, 15]:
                candidate = series.get((ruta, pref_gran))
                if candidate is not None and not candidate.empty:
                    df = candidate.copy()
                    break
            if df is None:
                continue

            ts = pd.to_datetime(df["timestamp"])
            df["_mes"] = ts.dt.to_period("M")
            df["_semana"] = ts.dt.to_period("W")
            df["_fecha"] = ts.dt.date

            mensual = (
                df.groupby("_mes")["pasajeros_total"]
                .sum()
                .rename("demanda_total")
                .reset_index()
                .rename(columns={"_mes": "periodo"})
            )
            mensual["tipo_periodo"] = "mes"
            mensual["periodo"] = mensual["periodo"].astype(str)

            semanal = (
                df.groupby("_semana")["pasajeros_total"]
                .sum()
                .rename("demanda_total")
                .reset_index()
                .rename(columns={"_semana": "periodo"})
            )
            semanal["tipo_periodo"] = "semana"
            semanal["periodo"] = semanal["periodo"].astype(str)

            # OLS trend on daily aggregated series
            diario = (
                df.groupby("_fecha")["pasajeros_total"]
                .sum()
                .rename("demanda")
                .reset_index()
                .sort_values("_fecha")
                .reset_index(drop=True)
            )
            slope = intercept = np.nan
            if len(diario) >= 3:
                x = np.arange(len(diario), dtype=float)
                y = diario["demanda"].values.astype(float)
                valid = ~np.isnan(y)
                if valid.sum() >= 3:
                    try:
                        ols = sm.OLS(y[valid], sm.add_constant(x[valid])).fit()
                        intercept = float(ols.params[0])
                        slope = float(ols.params[1])
                    except Exception as exc:
                        logger.warning("OLS fallido ruta=%d: %s", ruta, exc)

            # Atypical months: |demanda - mu| > 2 sigma
            mu = mensual["demanda_total"].mean()
            sigma = mensual["demanda_total"].std()
            mensual["es_atipico"] = (mensual["demanda_total"] - mu).abs() > 2 * sigma
            semanal["es_atipico"] = False

            for part in [mensual, semanal]:
                part["tendencia_slope"] = slope
                part["tendencia_intercept"] = intercept

            result = pd.concat([mensual, semanal], ignore_index=True)
            out_path = self.eda_dir / f"perfil_mensual_{ruta}.parquet"
            result.to_parquet(out_path, index=False)
            results[ruta] = result
            logger.info(
                "perfil_mensual: ruta=%d slope=%.4f intercept=%.2f → %s",
                ruta,
                slope if not np.isnan(slope) else 0.0,
                intercept if not np.isnan(intercept) else 0.0,
                out_path.name,
            )

        return results

    # ------------------------------------------------------------------
    # 1.4  Estacionalidad y autocorrelación
    # ------------------------------------------------------------------

    def autocorrelacion(self) -> dict[tuple[int, int], pd.DataFrame]:
        """ACF, PACF y test ADF sobre franjas operativas por ruta x granularidad.

        Los lags con |ACF| > 0.3 son candidatos a ventana de lookback para
        LSTM/GRU. El test ADF determina si la serie es estacionaria (p < 0.05).

        Returns
        -------
        dict[(ruta, gran), pd.DataFrame]
            Columnas: lag, acf_value, pacf_value, es_significativo_acf,
            es_significativo_pacf, lags_relevantes_acf, adf_statistic,
            adf_pvalue, adf_is_stationary, ruta, granularidad_min.
        """
        series = self._load_series()
        results: dict[tuple[int, int], pd.DataFrame] = {}

        for (ruta, gran), df in series.items():
            if df.empty or "pasajeros_total" not in df.columns:
                continue

            y = df.sort_values("timestamp")["pasajeros_total"].dropna().values.astype(float)
            n = len(y)

            if n < 50:
                logger.warning(
                    "Serie demasiado corta para ACF/PACF: ruta=%d gran=%d n=%d",
                    ruta,
                    gran,
                    n,
                )
                continue

            max_lags = min(48, n // 4)
            signif = 1.96 / np.sqrt(n)

            # ACF
            try:
                acf_vals, acf_ci = acf(y, nlags=max_lags, alpha=0.05, fft=True)
            except Exception as exc:
                logger.warning("ACF fallido ruta=%d gran=%d: %s", ruta, gran, exc)
                continue

            # PACF — ywm es más robusto que ols para series largas
            try:
                pacf_vals, _ = pacf(y, nlags=max_lags, alpha=0.05, method="ywm")
            except Exception as exc:
                logger.warning("PACF fallido ruta=%d gran=%d: %s", ruta, gran, exc)
                pacf_vals = np.full(max_lags + 1, np.nan)

            # ADF
            adf_stat = adf_pval = np.nan
            adf_stationary = False
            try:
                adf_res = adfuller(y, autolag="AIC")
                adf_stat = float(adf_res[0])
                adf_pval = float(adf_res[1])
                adf_stationary = bool(adf_pval < 0.05)
            except Exception as exc:
                logger.warning("ADF fallido ruta=%d gran=%d: %s", ruta, gran, exc)

            lags = np.arange(max_lags + 1)
            result_df = pd.DataFrame(
                {
                    "lag": lags,
                    "acf_value": acf_vals,
                    "pacf_value": pacf_vals,
                    "acf_ci_lower": acf_ci[:, 0] - acf_vals,
                    "acf_ci_upper": acf_ci[:, 1] - acf_vals,
                    "es_significativo_acf": np.abs(acf_vals) > signif,
                    "es_significativo_pacf": np.abs(pacf_vals) > signif,
                    "lags_relevantes_acf": np.abs(acf_vals) > 0.3,
                    "adf_statistic": adf_stat,
                    "adf_pvalue": adf_pval,
                    "adf_is_stationary": adf_stationary,
                    "ruta": ruta,
                    "granularidad_min": gran,
                }
            )

            out_path = self.eda_dir / f"autocorr_{ruta}_g{gran}min.parquet"
            result_df.to_parquet(out_path, index=False)
            results[(ruta, gran)] = result_df
            n_rel = int((np.abs(acf_vals[1:]) > 0.3).sum())
            logger.info(
                "autocorr: ruta=%d gran=%d ADF_p=%.4f estacionaria=%s n_lags_relevantes=%d",
                ruta,
                gran,
                adf_pval,
                adf_stationary,
                n_rel,
            )

        return results

    # ------------------------------------------------------------------
    # 1.5  Detección de valores atípicos
    # ------------------------------------------------------------------

    def atipicos(self) -> dict[tuple[int, int], pd.DataFrame]:
        """Detección de atípicos por IQR global y Z-score dentro de tipo_dia.

        El Z-score se calcula por separado en cada grupo ``tipo_dia`` para no
        penalizar el patrón dominical al compararlo con LABORAL.

        Returns
        -------
        dict[(ruta, gran), pd.DataFrame]
            Solo incluye filas donde al menos un método detecta atípico.
            Columnas: timestamp, fecha, hora_del_dia, tipo_dia, pasajeros_total,
            es_atipico_iqr, es_atipico_zscore, zscore_tipo_dia, metodo_deteccion,
            limite_inf_iqr, limite_sup_iqr, pct_atipicos.
        """
        series = self._load_series()
        results: dict[tuple[int, int], pd.DataFrame] = {}

        for (ruta, gran), df in series.items():
            if df.empty or "pasajeros_total" not in df.columns:
                continue

            data = df.copy()
            data["pasajeros_total"] = pd.to_numeric(data["pasajeros_total"], errors="coerce")
            data = data.dropna(subset=["pasajeros_total"])

            # IQR method (sobre todas las franjas operativas)
            q1 = data["pasajeros_total"].quantile(0.25)
            q3 = data["pasajeros_total"].quantile(0.75)
            iqr = q3 - q1
            lo = q1 - 1.5 * iqr
            hi = q3 + 1.5 * iqr
            data["es_atipico_iqr"] = (data["pasajeros_total"] < lo) | (data["pasajeros_total"] > hi)
            data["limite_inf_iqr"] = lo
            data["limite_sup_iqr"] = hi

            # Z-score within tipo_dia group
            def _zscore(s: pd.Series) -> pd.Series:
                mu, sigma = s.mean(), s.std()
                if sigma == 0 or np.isnan(sigma):
                    return pd.Series(0.0, index=s.index)
                return (s - mu) / sigma

            if "tipo_dia" in data.columns:
                data["zscore_tipo_dia"] = data.groupby("tipo_dia", dropna=False)[
                    "pasajeros_total"
                ].transform(_zscore)
            else:
                data["zscore_tipo_dia"] = _zscore(data["pasajeros_total"])

            data["es_atipico_zscore"] = data["zscore_tipo_dia"].abs() > 3
            data["es_atipico"] = data["es_atipico_iqr"] | data["es_atipico_zscore"]

            data["metodo_deteccion"] = ""
            both = data["es_atipico_iqr"] & data["es_atipico_zscore"]
            data.loc[both, "metodo_deteccion"] = "ambos"
            data.loc[data["es_atipico_iqr"] & ~data["es_atipico_zscore"], "metodo_deteccion"] = (
                "IQR"
            )
            data.loc[~data["es_atipico_iqr"] & data["es_atipico_zscore"], "metodo_deteccion"] = (
                "zscore"
            )

            pct = float(data["es_atipico"].sum() / len(data) * 100)
            data["pct_atipicos"] = pct

            if "timestamp" in data.columns:
                data["fecha"] = pd.to_datetime(data["timestamp"]).dt.strftime("%Y-%m-%d")

            keep_cols = [
                c
                for c in [
                    "timestamp",
                    "fecha",
                    "hora_del_dia",
                    "tipo_dia",
                    "pasajeros_total",
                    "es_atipico_iqr",
                    "es_atipico_zscore",
                    "zscore_tipo_dia",
                    "metodo_deteccion",
                    "limite_inf_iqr",
                    "limite_sup_iqr",
                    "pct_atipicos",
                ]
                if c in data.columns
            ]

            atipicos_df = data.loc[data["es_atipico"], keep_cols].copy()

            out_path = self.eda_dir / f"atipicos_{ruta}_g{gran}min.parquet"
            atipicos_df.to_parquet(out_path, index=False)
            results[(ruta, gran)] = atipicos_df
            logger.info(
                "atipicos: ruta=%d gran=%d n=%d pct=%.2f%%",
                ruta,
                gran,
                len(atipicos_df),
                pct,
            )

        return results

    # ------------------------------------------------------------------
    # 1.6  Correlación de features
    # ------------------------------------------------------------------

    def correlacion_features(self) -> pd.DataFrame:
        """Correlación Spearman entre PASAJEROS y todas las features numéricas.

        Usa el dataset model-ready (registros individuales de despacho).
        Codifica categóricas como enteros antes de calcular la correlación.

        Returns
        -------
        pd.DataFrame
            Columnas: feature, correlacion_spearman, abs_correlacion, rank.
            Ordenado por correlación absoluta descendente.
        """
        if not self.model_ready_path.exists():
            logger.warning("model_ready no encontrado: %s", self.model_ready_path)
            return pd.DataFrame()

        df = pd.read_parquet(self.model_ready_path)

        target_col = next(
            (c for c in ["PASAJEROS", "pasajeros", "pasajeros_total"] if c in df.columns),
            None,
        )
        if target_col is None:
            logger.warning("No se encontró columna objetivo en model_ready")
            return pd.DataFrame()

        df_enc = df.copy()
        for col in df_enc.select_dtypes(include=["str", "object", "category"]).columns:
            df_enc[col] = df_enc[col].astype("category").cat.codes

        numeric = df_enc.select_dtypes(include=np.number).columns.tolist()
        features = [c for c in numeric if c != target_col]
        target = pd.to_numeric(df_enc[target_col], errors="coerce")

        correlations: dict[str, float] = {}
        for col in features:
            feat = pd.to_numeric(df_enc[col], errors="coerce")
            valid = target.notna() & feat.notna()
            if valid.sum() < 10:
                continue
            try:
                corr = target[valid].corr(feat[valid], method="spearman")
                if not np.isnan(corr):
                    correlations[col] = float(corr)
            except Exception:
                pass

        if not correlations:
            return pd.DataFrame()

        result = (
            pd.Series(correlations, name="correlacion_spearman")
            .rename_axis("feature")
            .reset_index()
        )
        result["abs_correlacion"] = result["correlacion_spearman"].abs()
        result = result.sort_values("abs_correlacion", ascending=False).reset_index(drop=True)
        result["rank"] = result.index + 1

        out_path = self.eda_dir / "correlacion_features.parquet"
        result.to_parquet(out_path, index=False)
        logger.info(
            "correlacion_features: top=%s corr=%.3f",
            result.iloc[0]["feature"] if not result.empty else "N/A",
            result.iloc[0]["abs_correlacion"] if not result.empty else 0.0,
        )
        return result

    # ------------------------------------------------------------------
    # run_all
    # ------------------------------------------------------------------

    def run_all(self) -> dict[str, Any]:
        """Ejecuta todos los análisis EDA y retorna el diccionario de resultados."""
        logger.info("Iniciando EDA temporal completo...")
        results = {
            "perfil_intraday": self.perfil_intraday(),
            "perfil_semanal": self.perfil_semanal(),
            "perfil_mensual": self.perfil_mensual(),
            "autocorrelacion": self.autocorrelacion(),
            "atipicos": self.atipicos(),
            "correlacion_features": self.correlacion_features(),
        }
        logger.info("EDA temporal completado. Artefactos en: %s", self.eda_dir)
        return results


def calcular_gaps_horario_operativo(
    series_dict: dict[tuple[int, int], pd.DataFrame],
    operational_hours_df: pd.DataFrame,
    output_dir: Path | None = None,
) -> pd.DataFrame:
    """Recalcula el análisis de gaps restringiéndolo al horario operativo estimado.

    Para cada combinación (ruta x granularidad_min x tipo_dia) filtra las franjas
    cuyo timestamp cae dentro de [hora_inicio_op_min, hora_fin_op_min] y calcula
    n_franjas_op, n_gaps_op y pct_gaps_op. Los valores sin filtro horario (24h)
    se incluyen como columnas de comparación directa para evidenciar cuánto
    inflaban los gaps nocturnos estructurales el porcentaje reportado.

    Parameters
    ----------
    series_dict : dict[tuple[int, int], pd.DataFrame]
        Diccionario {(ruta, granularidad_min): DataFrame} producido por
        TimeSeriesBuilder.build_all(). Cada DataFrame debe tener las columnas
        timestamp, is_gap y tipo_dia.
    operational_hours_df : pd.DataFrame
        DataFrame cargado desde operational_hours.parquet con las columnas
        tipo_dia, ruta, granularidad_min, hora_inicio_op_min, hora_fin_op_min.
    output_dir : Path | None
        Directorio de salida para gaps_horario_operativo.csv.
        Si es None, usa reports/tables/ del proyecto.

    Returns
    -------
    pd.DataFrame
        Tabla con columnas: granularidad_min, ruta, tipo_dia,
        n_franjas_op, n_gaps_op, pct_gaps_op,
        n_franjas_24h, n_gaps_24h, pct_gaps_24h.
        Imprime en consola el resumen agregado por (granularidad_min x ruta).
    """
    rows: list[dict] = []

    for (ruta, gran), df in series_dict.items():
        if df.empty:
            continue

        required = {"timestamp", "is_gap", "tipo_dia"}
        missing = required - set(df.columns)
        if missing:
            logger.warning(
                "calcular_gaps_horario_operativo: columnas faltantes ruta=%d gran=%d: %s",
                ruta,
                gran,
                missing,
            )
            continue

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["is_gap"] = df["is_gap"].fillna(False).astype(bool)
        df["_minuto_dia"] = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute

        op_sub = operational_hours_df[
            (operational_hours_df["ruta"] == ruta)
            & (operational_hours_df["granularidad_min"] == gran)
            & (operational_hours_df["hora_inicio_op_min"] >= 0)
        ]
        lookup: dict[str, tuple[int, int]] = {
            str(r["tipo_dia"]): (int(r["hora_inicio_op_min"]), int(r["hora_fin_op_min"]))
            for _, r in op_sub.iterrows()
        }

        for tipo_dia, grp in df.groupby("tipo_dia", dropna=False):
            tipo_str = str(tipo_dia)
            n_24h = len(grp)
            n_gaps_24h = int(grp["is_gap"].sum())
            pct_24h = round(100.0 * n_gaps_24h / n_24h, 2) if n_24h > 0 else 0.0

            if tipo_str not in lookup:
                logger.debug(
                    "Sin horario operativo para ruta=%d gran=%d tipo=%s — se registra sin filtro",
                    ruta,
                    gran,
                    tipo_str,
                )
                rows.append(
                    {
                        "granularidad_min": gran,
                        "ruta": ruta,
                        "tipo_dia": tipo_str,
                        "n_franjas_op": 0,
                        "n_gaps_op": 0,
                        "pct_gaps_op": None,
                        "n_franjas_24h": n_24h,
                        "n_gaps_24h": n_gaps_24h,
                        "pct_gaps_24h": pct_24h,
                    }
                )
                continue

            inicio, fin = lookup[tipo_str]
            grp_op = grp[(grp["_minuto_dia"] >= inicio) & (grp["_minuto_dia"] <= fin)]

            n_op = len(grp_op)
            n_gaps_op = int(grp_op["is_gap"].sum())
            pct_op = round(100.0 * n_gaps_op / n_op, 2) if n_op > 0 else 0.0

            rows.append(
                {
                    "granularidad_min": gran,
                    "ruta": ruta,
                    "tipo_dia": tipo_str,
                    "n_franjas_op": n_op,
                    "n_gaps_op": n_gaps_op,
                    "pct_gaps_op": pct_op,
                    "n_franjas_24h": n_24h,
                    "n_gaps_24h": n_gaps_24h,
                    "pct_gaps_24h": pct_24h,
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        logger.warning("calcular_gaps_horario_operativo: sin resultados.")
        return result

    out_dir = Path(output_dir) if output_dir else _REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "gaps_horario_operativo.csv"
    result.to_csv(csv_path, index=False)
    logger.info("Gaps horario operativo guardado: %s", csv_path)

    # Resumen agregado por (granularidad_min x ruta): promedio ponderado por tipo_dia
    valid = result.dropna(subset=["pct_gaps_op"])
    if not valid.empty:
        agg_rows: list[dict] = []
        for (gran_g, ruta_g), grp_g in valid.groupby(["granularidad_min", "ruta"]):
            n_op_tot = int(grp_g["n_franjas_op"].sum())
            n_gaps_op_tot = int(grp_g["n_gaps_op"].sum())
            n_24h_tot = int(grp_g["n_franjas_24h"].sum())
            n_gaps_24h_tot = int(grp_g["n_gaps_24h"].sum())
            pct_op = round(100.0 * n_gaps_op_tot / n_op_tot, 2) if n_op_tot > 0 else 0.0
            pct_24h = round(100.0 * n_gaps_24h_tot / n_24h_tot, 2) if n_24h_tot > 0 else 0.0
            agg_rows.append(
                {
                    "granularidad_min": gran_g,
                    "ruta": ruta_g,
                    "n_franjas_op": n_op_tot,
                    "n_gaps_op": n_gaps_op_tot,
                    "pct_gaps_op": pct_op,
                    "n_franjas_24h": n_24h_tot,
                    "pct_gaps_24h": pct_24h,
                    "reduccion_pct_pts": round(pct_24h - pct_op, 2),
                }
            )
        agg = pd.DataFrame(agg_rows)
        sep = "=" * 70
        print(f"\n{sep}")
        print("  Gaps: horario operativo vs 24h  (promedio ponderado por tipo_dia)")
        print(sep)
        print(agg.to_string(index=False))
        print(f"{sep}\n")
        logger.info("Resumen gaps horario operativo:\n%s", agg.to_string(index=False))

    return result
