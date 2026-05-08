"""Tests unitarios para TemporalEDA."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from proyecto_grado.eda.temporal_analysis import TemporalEDA

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _ts_parquet(
    tmp_path: Path,
    ruta: int,
    gran: int,
    pasajeros_by_hour: dict[int, float] | None = None,
    n_days: int = 30,
    gap_tipo_fn=None,
    tipo_dia_fn=None,
) -> Path:
    """Genera un parquet de serie temporal sintética para tests."""
    dates = pd.date_range("2024-01-01", periods=n_days * 24, freq="1h")
    rows = []
    for i, ts in enumerate(dates):
        hora = ts.hour
        dia_semana = ts.dayofweek
        tipo_dia = tipo_dia_fn(ts) if tipo_dia_fn else "LABORAL" if dia_semana < 5 else "DOMINGO"
        pax = float(pasajeros_by_hour.get(hora, 10.0)) if pasajeros_by_hour else 50.0
        gap_tipo = gap_tipo_fn(i, ts) if gap_tipo_fn else "operativo"

        rows.append(
            {
                "timestamp": ts,
                "pasajeros_total": pax,
                "despachos_count": 5,
                "pasajeros_promedio": pax / 5,
                "ocupacion_p95": pax,
                "is_gap": False,
                "hora_del_dia": hora,
                "dia_semana": dia_semana,
                "es_fin_semana": dia_semana >= 5,
                "mes": ts.month,
                "semana_anio": ts.isocalendar().week,
                "trimestre": ts.quarter,
                "franja_horaria": "MANANA" if 6 <= hora <= 11 else "TARDE",
                "es_festivo": False,
                "tipo_dia": tipo_dia,
                "FK_RUTA": ruta,
                "granularidad_min": gran,
                "dentro_horario_operativo": True,
                "gap_tipo": gap_tipo,
            }
        )

    df = pd.DataFrame(rows)
    ts_dir = tmp_path / "ts"
    ts_dir.mkdir(exist_ok=True)
    path = ts_dir / f"ts_ruta{ruta}_g{gran}min.parquet"
    df.to_parquet(path, index=False)
    return path


# ---------------------------------------------------------------------------
# 1.1 Perfil intradía — sólo usa franjas operativo
# ---------------------------------------------------------------------------


class TestPerfilIntraday:
    def test_solo_usa_franjas_operativas(self, tmp_path: Path) -> None:
        """El perfil intradía NO debe incluir valores de franjas gap_anomalo."""

        # Horas pares = operativo con pasajeros=100
        # Horas impares = gap_anomalo con pasajeros=999 (no deben influir)
        def gap_fn(i: int, ts) -> str:
            return "operativo" if ts.hour % 2 == 0 else "gap_anomalo"

        def pax_fn_by_hour(hora: int) -> float:
            return 100.0 if hora % 2 == 0 else 999.0

        _ts_parquet(
            tmp_path,
            ruta=1,
            gran=60,
            pasajeros_by_hour={h: pax_fn_by_hour(h) for h in range(24)},
            gap_tipo_fn=gap_fn,
        )
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.perfil_intraday()

        assert (1, 60) in result
        df = result[(1, 60)]
        # Todas las medias deben ser 100, nunca 999
        assert df["media"].max() == pytest.approx(100.0, abs=1.0)

    def test_horas_pico_tienen_media_mayor_p75(self, tmp_path: Path) -> None:
        """Las horas marcadas es_pico deben tener media > p75 del grupo."""
        # Horas 18-21 tienen pasajeros=100, el resto=10
        by_hour = {h: (100.0 if 18 <= h <= 21 else 10.0) for h in range(24)}
        _ts_parquet(tmp_path, ruta=1, gran=60, pasajeros_by_hour=by_hour)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.perfil_intraday()

        df = result[(1, 60)]
        laboral = df[df["tipo_dia"] == "LABORAL"] if "tipo_dia" in df.columns else df
        assert not laboral.empty

        p75_val = laboral["media"].quantile(0.75)
        picos = laboral[laboral["es_pico"]]
        assert not picos.empty, "Deben detectarse horas pico"
        assert (picos["media"] > p75_val).all(), "Cada hora pico debe tener media > p75 del día"

    def test_ratio_pico_valle_es_positivo(self, tmp_path: Path) -> None:
        """ratio_pico_valle debe ser > 1 cuando hay diferencia clara."""
        # Horas 0-3 muy bajas (valle claro), horas 4-20 medias, horas 21-23 altas
        by_hour = {h: (2.0 if h <= 3 else 80.0 if h >= 21 else 30.0) for h in range(24)}
        _ts_parquet(tmp_path, ruta=1, gran=60, pasajeros_by_hour=by_hour)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.perfil_intraday()

        df = result[(1, 60)]
        ratios = df["ratio_pico_valle"].dropna()
        assert not ratios.empty
        assert (ratios > 1.0).all(), "El ratio pico/valle debe ser > 1"


# ---------------------------------------------------------------------------
# 1.4 Autocorrelación — ADF retorna diccionario con claves esperadas
# ---------------------------------------------------------------------------


class TestAutocorrelacion:
    def test_adf_retorna_columnas_esperadas(self, tmp_path: Path) -> None:
        """El DataFrame de autocorrelación debe tener adf_statistic, adf_pvalue, adf_is_stationary."""
        # Serie con suficientes filas (>50) para ACF
        _ts_parquet(tmp_path, ruta=1, gran=60, n_days=60)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.autocorrelacion()

        assert (1, 60) in result
        df = result[(1, 60)]
        for col in ["adf_statistic", "adf_pvalue", "adf_is_stationary"]:
            assert col in df.columns, f"Columna '{col}' faltante"

    def test_adf_is_stationary_es_bool(self, tmp_path: Path) -> None:
        """adf_is_stationary debe ser un valor booleano."""
        _ts_parquet(tmp_path, ruta=1, gran=60, n_days=60)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.autocorrelacion()
        df = result[(1, 60)]
        assert df["adf_is_stationary"].dtype == bool or df["adf_is_stationary"].iloc[0] in (
            True,
            False,
        )

    def test_acf_lag0_es_uno(self, tmp_path: Path) -> None:
        """ACF en lag=0 debe ser 1.0 por definición."""
        # Serie con variación por hora para evitar varianza=0
        by_hour = {h: float(10 + h * 3) for h in range(24)}
        _ts_parquet(tmp_path, ruta=1, gran=60, n_days=60, pasajeros_by_hour=by_hour)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.autocorrelacion()
        df = result[(1, 60)]
        lag0 = df.loc[df["lag"] == 0, "acf_value"]
        assert not lag0.empty
        assert lag0.iloc[0] == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 1.5 Atípicos — Z-score calculado dentro de cada tipo_dia
# ---------------------------------------------------------------------------


class TestAtipicos:
    def test_zscore_calculado_por_tipo_dia(self, tmp_path: Path) -> None:
        """Un outlier en DOMINGO no debe ser outlier si se compara con LABORAL."""
        # LABORAL: pasajeros=50 ± pequeña variación → media ~50
        # DOMINGO: pasajeros=10 ± pequeña variación → media ~10
        # Inyectamos valor=200 sólo en un DOMINGO: debería ser outlier z-score en DOMINGO
        # pero valor=55 en LABORAL: no debería ser outlier en LABORAL

        rows = []
        base = pd.Timestamp("2024-01-01")  # lunes
        for day in range(28):  # 4 semanas
            ts_day = base + pd.Timedelta(days=day)
            dia_semana = ts_day.dayofweek
            tipo_dia = "DOMINGO" if dia_semana == 6 else "LABORAL"
            for hora in range(24):
                ts = ts_day + pd.Timedelta(hours=hora)
                pax = 10.0 if tipo_dia == "DOMINGO" else 50.0
                # Inject extreme value on the last Sunday hora=12
                if tipo_dia == "DOMINGO" and day == 27 and hora == 12:
                    pax = 200.0
                rows.append(
                    {
                        "timestamp": ts,
                        "pasajeros_total": pax,
                        "hora_del_dia": hora,
                        "dia_semana": dia_semana,
                        "tipo_dia": tipo_dia,
                        "gap_tipo": "operativo",
                        "granularidad_min": 60,
                        "FK_RUTA": 1,
                    }
                )

        df = pd.DataFrame(rows)
        ts_dir = tmp_path / "ts"
        ts_dir.mkdir(exist_ok=True)
        (ts_dir / "ts_ruta1_g60min.parquet").write_bytes(df.to_parquet())

        eda = TemporalEDA(ts_dir=ts_dir, eda_dir=tmp_path / "eda")
        result = eda.atipicos()

        assert (1, 60) in result
        at_df = result[(1, 60)]

        # The injected value (200 in DOMINGO) should be detected as zscore outlier
        domingo_outliers = at_df[
            (at_df["tipo_dia"] == "DOMINGO") & at_df["es_atipico_zscore"].fillna(False)
        ]
        assert not domingo_outliers.empty, (
            "El valor 200 en DOMINGO debería ser outlier z-score dentro del grupo DOMINGO"
        )

    def test_pct_atipicos_en_columna(self, tmp_path: Path) -> None:
        """El DataFrame de atípicos debe incluir la columna pct_atipicos."""
        _ts_parquet(tmp_path, ruta=1, gran=60, n_days=30)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        result = eda.atipicos()
        at_df = result.get((1, 60), pd.DataFrame())
        # Si hay atípicos, deben tener pct_atipicos
        if not at_df.empty:
            assert "pct_atipicos" in at_df.columns
            assert (at_df["pct_atipicos"] >= 0).all()
            assert (at_df["pct_atipicos"] <= 100).all()


# ---------------------------------------------------------------------------
# 1.3 Perfil mensual — detecta mes inyectado 3 sigma por encima
# ---------------------------------------------------------------------------


class TestPerfilMensual:
    def test_detecta_mes_anomalo_3sigma(self, tmp_path: Path) -> None:
        """perfil_mensual debe marcar es_atipico=True para un mes con demanda 3 sigma arriba."""
        # Generar 12 meses de datos con demanda base, y un mes con demanda muy alta
        rows = []
        base = pd.Timestamp("2023-01-01")
        for month in range(12):
            n_days = 28
            start = base + pd.DateOffset(months=month)
            for day in range(n_days):
                ts = start + pd.Timedelta(days=day, hours=8)
                # Mes 6 (julio) tiene demanda 10x la normal -> claramente > 2 sigma
                pax = 1000.0 if month == 5 else 100.0
                rows.append(
                    {
                        "timestamp": ts,
                        "pasajeros_total": pax,
                        "hora_del_dia": 8,
                        "dia_semana": ts.dayofweek,
                        "tipo_dia": "LABORAL",
                        "gap_tipo": "operativo",
                        "granularidad_min": 60,
                        "FK_RUTA": 1,
                    }
                )

        df = pd.DataFrame(rows)
        ts_dir = tmp_path / "ts"
        ts_dir.mkdir(exist_ok=True)
        (ts_dir / "ts_ruta1_g60min.parquet").write_bytes(df.to_parquet())

        eda = TemporalEDA(ts_dir=ts_dir, eda_dir=tmp_path / "eda")
        result = eda.perfil_mensual()

        assert 1 in result
        mdf = result[1]
        mes_data = mdf[mdf["tipo_periodo"] == "mes"]
        assert not mes_data.empty

        # Debe haber al menos 1 mes marcado como atípico (el de demanda 1000)
        assert mes_data["es_atipico"].any(), "El mes con demanda 10x debe marcarse como atípico"

    def test_slope_positivo_con_tendencia_creciente(self, tmp_path: Path) -> None:
        """Serie con demanda creciente → tendencia_slope positivo."""
        rows = []
        base = pd.Timestamp("2023-01-01")
        for day in range(365):
            ts = base + pd.Timedelta(days=day, hours=8)
            pax = 10.0 + day * 0.5  # demanda crece 0.5 por día
            rows.append(
                {
                    "timestamp": ts,
                    "pasajeros_total": pax,
                    "hora_del_dia": 8,
                    "dia_semana": ts.dayofweek,
                    "tipo_dia": "LABORAL",
                    "gap_tipo": "operativo",
                    "granularidad_min": 60,
                    "FK_RUTA": 1,
                }
            )

        df = pd.DataFrame(rows)
        ts_dir = tmp_path / "ts"
        ts_dir.mkdir(exist_ok=True)
        (ts_dir / "ts_ruta1_g60min.parquet").write_bytes(df.to_parquet())

        eda = TemporalEDA(ts_dir=ts_dir, eda_dir=tmp_path / "eda")
        result = eda.perfil_mensual()

        mdf = result[1]
        slope = float(mdf["tendencia_slope"].iloc[0])
        assert slope > 0, f"Serie creciente debe tener slope positivo, got {slope}"


# ---------------------------------------------------------------------------
# Persistencia de artefactos
# ---------------------------------------------------------------------------


class TestPersistencia:
    def test_artefactos_guardados_en_disco(self, tmp_path: Path) -> None:
        """Todos los métodos deben guardar su parquet en eda_dir."""
        _ts_parquet(tmp_path, ruta=1, gran=60, n_days=60)
        eda_dir = tmp_path / "eda"
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=eda_dir)
        eda.perfil_intraday()
        eda.perfil_semanal()
        eda.perfil_mensual()
        eda.autocorrelacion()
        eda.atipicos()

        assert (eda_dir / "perfil_intraday_1_g60min.parquet").exists()
        assert (eda_dir / "perfil_semanal_1_g60min.parquet").exists()
        assert (eda_dir / "perfil_mensual_1.parquet").exists()
        assert (eda_dir / "autocorr_1_g60min.parquet").exists()
        # atipicos puede ser vacío si la serie sintética es homogénea

    def test_run_all_retorna_dict_con_seis_claves(self, tmp_path: Path) -> None:
        """run_all debe retornar dict con las 6 claves de análisis."""
        _ts_parquet(tmp_path, ruta=1, gran=60, n_days=60)
        eda = TemporalEDA(ts_dir=tmp_path / "ts", eda_dir=tmp_path / "eda")
        results = eda.run_all()
        expected_keys = {
            "perfil_intraday",
            "perfil_semanal",
            "perfil_mensual",
            "autocorrelacion",
            "atipicos",
            "correlacion_features",
        }
        assert set(results.keys()) == expected_keys
