"""Tests unitarios para TimeSeriesBuilder y TimeSeriesValidator."""

import numpy as np
import pandas as pd
import pytest

from proyecto_grado.features.time_series_builder import TimeSeriesBuilder
from proyecto_grado.features.validators import TimeSeriesValidator

# ---------------------------------------------------------------------------
# Fixtures y helpers
# ---------------------------------------------------------------------------

CFG_60: dict = {
    "granularidad_min": 60,
    "franjas_horarias": {
        "MADRUGADA": [0, 5],
        "MANANA": [6, 11],
        "MEDIODIA": [12, 13],
        "TARDE": [14, 18],
        "NOCHE": [19, 23],
    },
    "imputacion_gaps": "zero",
    "rutas": [1, 3],
}


def _make_df(n: int = 20, ruta: int = 1, start: str = "2024-04-16") -> pd.DataFrame:
    """Genera n despachos en intervalos de 10 minutos desde start."""
    rng = pd.date_range(start=start, periods=n, freq="10min")
    return pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": range(1, n + 1),
            "HORA_INICIAL_REAL": rng,
            "PASAJEROS": [20] * n,
            "FK_RUTA": ruta,
        }
    )


def _make_df_days(n_days: int, ruta: int = 1, start: str = "2024-01-01") -> pd.DataFrame:
    """Genera despachos cada 10 minutos durante n_days dias completos."""
    rng = pd.date_range(start=start, periods=n_days * 24 * 6, freq="10min")
    n = len(rng)
    return pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": range(1, n + 1),
            "HORA_INICIAL_REAL": rng,
            "PASAJEROS": [20] * n,
            "FK_RUTA": ruta,
        }
    )


# ---------------------------------------------------------------------------
# Agregacion correcta de variables objetivo
# ---------------------------------------------------------------------------


class TestAgregacion:
    def test_despachos_count_por_bin(self):
        """despachos_count debe contar los despachos reales de cada bin horario."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2, 3, 4],
                "HORA_INICIAL_REAL": pd.to_datetime(
                    [
                        "2024-04-16 08:00",
                        "2024-04-16 08:45",
                        "2024-04-16 09:10",
                        "2024-04-16 09:50",
                    ]
                ),
                "PASAJEROS": [10, 20, 30, 40],
                "FK_RUTA": [1, 1, 1, 1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        cnt_08 = serie.loc[
            serie["timestamp"] == pd.Timestamp("2024-04-16 08:00"), "despachos_count"
        ].iloc[0]
        cnt_09 = serie.loc[
            serie["timestamp"] == pd.Timestamp("2024-04-16 09:00"), "despachos_count"
        ].iloc[0]
        assert cnt_08 == 2
        assert cnt_09 == 2

    def test_pasajeros_total_es_suma(self):
        """pasajeros_total debe ser la suma de PASAJEROS en el bin."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 08:45"]),
                "PASAJEROS": [10, 20],
                "FK_RUTA": [1, 1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        total = serie.loc[
            serie["timestamp"] == pd.Timestamp("2024-04-16 08:00"), "pasajeros_total"
        ].iloc[0]
        assert total == pytest.approx(30.0)

    def test_pasajeros_promedio_es_media(self):
        """pasajeros_promedio debe ser la media de PASAJEROS en el bin."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 08:30"]),
                "PASAJEROS": [10.0, 30.0],
                "FK_RUTA": [1, 1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        prom = serie.loc[
            serie["timestamp"] == pd.Timestamp("2024-04-16 08:00"), "pasajeros_promedio"
        ].iloc[0]
        assert prom == pytest.approx(20.0)

    def test_ocupacion_p95_es_percentil(self):
        """ocupacion_p95 debe ser el percentil 95 de PASAJEROS en el bin."""
        pasajeros = list(range(1, 21))
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": range(1, 21),
                "HORA_INICIAL_REAL": [pd.Timestamp("2024-04-16 08:00")] * 20,
                "PASAJEROS": pasajeros,
                "FK_RUTA": [1] * 20,
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        p95 = serie.loc[
            serie["timestamp"] == pd.Timestamp("2024-04-16 08:00"), "ocupacion_p95"
        ].iloc[0]
        assert p95 == pytest.approx(np.percentile(pasajeros, 95))


# ---------------------------------------------------------------------------
# Derivacion de tipo_dia y festivos Colombia
# ---------------------------------------------------------------------------


class TestTipoDia:
    def test_laboral(self):
        """Martes no festivo = LABORAL."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00"]),  # martes
                "PASAJEROS": [10],
                "FK_RUTA": [1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)
        assert serie["tipo_dia"].iloc[0] == "LABORAL"

    def test_sabado(self):
        """Sabado no festivo = SABADO."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-20 08:00"]),  # sabado
                "PASAJEROS": [10],
                "FK_RUTA": [1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)
        assert serie["tipo_dia"].iloc[0] == "SABADO"

    def test_domingo(self):
        """Domingo no festivo = DOMINGO."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-21 08:00"]),  # domingo
                "PASAJEROS": [10],
                "FK_RUTA": [1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)
        assert serie["tipo_dia"].iloc[0] == "DOMINGO"

    def test_festivo_colombia_primero_enero(self):
        """1 de enero 2024 (lunes) es FESTIVO_PUENTE; es_festivo siempre True."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-01-01 08:00"]),
                "PASAJEROS": [10],
                "FK_RUTA": [1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)
        assert bool(serie["es_festivo"].iloc[0])
        # 1-ene-2024 es lunes → FESTIVO_PUENTE (Ley Emiliani)
        assert serie["tipo_dia"].iloc[0] == "FESTIVO_PUENTE"

    def test_dia_laboral_no_es_festivo(self):
        """Martes comun no debe marcarse como festivo."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00"]),
                "PASAJEROS": [10],
                "FK_RUTA": [1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)
        assert not bool(serie["es_festivo"].iloc[0])

    def test_es_fin_semana_sabado_domingo(self):
        """es_fin_semana debe ser True solo para sabado y domingo."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2, 3],
                "HORA_INICIAL_REAL": pd.to_datetime(
                    ["2024-04-16 08:00", "2024-04-20 08:00", "2024-04-21 08:00"]
                ),
                "PASAJEROS": [10, 10, 10],
                "FK_RUTA": [1, 1, 1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        def _fin_semana_en(ts_str: str) -> bool:
            return bool(
                serie.loc[serie["timestamp"] == pd.Timestamp(ts_str), "es_fin_semana"].iloc[0]
            )

        assert not _fin_semana_en("2024-04-16 08:00")  # martes
        assert _fin_semana_en("2024-04-20 08:00")  # sabado
        assert _fin_semana_en("2024-04-21 08:00")  # domingo


# ---------------------------------------------------------------------------
# Manejo de gaps
# ---------------------------------------------------------------------------


class TestGaps:
    def test_gap_imputado_con_cero(self):
        """Con imputacion_gaps=zero, franjas sin despachos tienen pasajeros_total=0."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 11:00"]),
                "PASAJEROS": [10, 20],
                "FK_RUTA": [1, 1],
            }
        )
        cfg = {**CFG_60, "imputacion_gaps": "zero"}
        builder = TimeSeriesBuilder(cfg)
        serie = builder.build(df, ruta=1)

        gaps = serie[serie["is_gap"]]
        assert len(gaps) == 2  # 09:00 y 10:00
        assert (gaps["pasajeros_total"] == 0.0).all()
        assert (gaps["despachos_count"] == 0).all()

    def test_gap_marcado_con_nan(self):
        """Con imputacion_gaps=mark, franjas sin despachos tienen NaN en objetivos."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 11:00"]),
                "PASAJEROS": [10, 20],
                "FK_RUTA": [1, 1],
            }
        )
        cfg = {**CFG_60, "imputacion_gaps": "mark"}
        builder = TimeSeriesBuilder(cfg)
        serie = builder.build(df, ruta=1)

        gaps = serie[serie["is_gap"]]
        assert len(gaps) == 2
        assert gaps["pasajeros_total"].isna().all()

    def test_is_gap_false_en_franjas_con_datos(self):
        """Franjas con despachos reales no deben marcarse como gap."""
        df = _make_df(n=10, ruta=1)
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        con_datos = serie[~serie["is_gap"]]
        assert len(con_datos) > 0
        assert (con_datos["despachos_count"] > 0).all()

    def test_gap_ffill_propaga_valor_anterior(self):
        """Con imputacion_gaps=ffill, la franja sin datos toma el valor anterior."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 10:00"]),
                "PASAJEROS": [50, 30],
                "FK_RUTA": [1, 1],
            }
        )
        cfg = {**CFG_60, "imputacion_gaps": "ffill"}
        builder = TimeSeriesBuilder(cfg)
        serie = builder.build(df, ruta=1)

        gap_09 = serie.loc[serie["timestamp"] == pd.Timestamp("2024-04-16 09:00")]
        assert not gap_09.empty
        assert gap_09["pasajeros_total"].iloc[0] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Rutas independientes
# ---------------------------------------------------------------------------


class TestRutasIndependientes:
    def test_rutas_no_mezclan_datos(self):
        """build(ruta=1) no debe incluir pasajeros de ruta=3."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 08:00"]),
                "PASAJEROS": [10, 999],
                "FK_RUTA": [1, 3],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        total = serie.loc[
            serie["timestamp"] == pd.Timestamp("2024-04-16 08:00"), "pasajeros_total"
        ].iloc[0]
        assert total == pytest.approx(10.0)

    def test_build_all_produce_serie_por_ruta(self):
        """build_all retorna dict con clave (ruta, granularidad_min) por combinacion."""
        df1 = _make_df_days(n_days=5, ruta=1, start="2024-04-01")
        df3 = _make_df_days(n_days=5, ruta=3, start="2024-06-01")
        df_all = pd.concat([df1, df3], ignore_index=True)

        builder = TimeSeriesBuilder(CFG_60)
        series = builder.build_all(df_all)

        assert (1, 60) in series and (3, 60) in series
        assert not series[(1, 60)].empty
        assert not series[(3, 60)].empty

    def test_series_rutas_no_solapan_en_tiempo(self):
        """Series de rutas con fechas distintas no deben solapar temporalmente."""
        df1 = _make_df_days(n_days=5, ruta=1, start="2024-04-01")
        df3 = _make_df_days(n_days=5, ruta=3, start="2024-06-01")
        df_all = pd.concat([df1, df3], ignore_index=True)

        builder = TimeSeriesBuilder(CFG_60)
        series = builder.build_all(df_all)

        assert series[(1, 60)]["timestamp"].max() < series[(3, 60)]["timestamp"].min()

    def test_fk_ruta_en_serie_es_correcto(self):
        """La columna FK_RUTA en la serie debe coincidir con la ruta solicitada."""
        df = _make_df(n=12, ruta=3)
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=3)

        assert (serie["FK_RUTA"] == 3).all()


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


class TestValidator:
    def test_serie_larga_es_valida(self):
        """Serie de 31 dias continua debe pasar la validacion."""
        df = _make_df_days(n_days=31, ruta=1)
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        validator = TimeSeriesValidator(granularidad_min=60, cobertura_minima_dias=30)
        report = validator.validate(serie, ruta=1)

        assert report.valida, f"Errores inesperados: {report.errores}"

    def test_serie_vacia_no_es_valida(self):
        """Serie vacia debe reportar error."""
        validator = TimeSeriesValidator()
        report = validator.validate(pd.DataFrame(), ruta=1)

        assert not report.valida
        assert any("vacia" in e.lower() for e in report.errores)

    def test_cobertura_insuficiente_reporta_error(self):
        """Serie de 2 dias no cumple el minimo de 30."""
        df = _make_df(n=10, ruta=1, start="2024-04-16")
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        validator = TimeSeriesValidator(granularidad_min=60, cobertura_minima_dias=30)
        report = validator.validate(serie, ruta=1)

        assert not report.valida
        assert not report.cobertura_ok

    def test_gaps_contabilizados_correctamente(self):
        """El reporte debe contar exactamente los gaps detectados."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 11:00"]),
                "PASAJEROS": [10, 20],
                "FK_RUTA": [1, 1],
            }
        )
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        validator = TimeSeriesValidator(granularidad_min=60, cobertura_minima_dias=0)
        report = validator.validate(serie, ruta=1)

        assert report.gaps_detectados == 2  # 09:00 y 10:00

    def test_serie_sin_errores_es_valida(self):
        """ValidationReport.valida es True cuando errores esta vacio."""
        df = _make_df_days(n_days=31, ruta=1)
        builder = TimeSeriesBuilder(CFG_60)
        serie = builder.build(df, ruta=1)

        validator = TimeSeriesValidator(granularidad_min=60, cobertura_minima_dias=30)
        report = validator.validate(serie, ruta=1)

        assert report.valida == (len(report.errores) == 0)


# ---------------------------------------------------------------------------
# Multi-granularidad
# ---------------------------------------------------------------------------

CFG_MULTI: dict = {
    "granularidades_min": [15, 30, 60],
    "franjas_horarias": {
        "MADRUGADA": [0, 5],
        "MANANA": [6, 11],
        "MEDIODIA": [12, 13],
        "TARDE": [14, 18],
        "NOCHE": [19, 23],
    },
    "imputacion_gaps": "zero",
    "rutas": [1, 3],
}


def _make_df_days_multi(n_days: int = 5) -> pd.DataFrame:
    """Genera datos para ambas rutas durante n_days dias completos."""
    df1 = _make_df_days(n_days, ruta=1)
    df3 = _make_df_days(n_days, ruta=3)
    return pd.concat([df1, df3], ignore_index=True)


class TestMultiGranularidad:
    def test_build_all_genera_seis_series(self):
        """build_all con 3 granularidades x 2 rutas debe retornar 6 entradas."""
        df = _make_df_days_multi(n_days=5)
        builder = TimeSeriesBuilder(CFG_MULTI)
        resultado = builder.build_all(df)
        assert len(resultado) == 6

    def test_g15_tiene_aprox_4x_filas_que_g60(self):
        """g15min tiene ~4x mas filas que g60min (tolerancia +-5%)."""
        df = _make_df_days(n_days=10, ruta=1)
        builder = TimeSeriesBuilder({"granularidades_min": [15, 60], "rutas": [1]})
        s15 = builder.build(df, ruta=1, granularidad_min=15)
        s60 = builder.build(df, ruta=1, granularidad_min=60)
        ratio = len(s15) / len(s60)
        assert 3.8 <= ratio <= 4.2

    def test_columna_granularidad_min_correcta(self):
        """Cada serie debe incluir la columna granularidad_min con el valor correcto."""
        df = _make_df_days(n_days=5, ruta=1)
        builder = TimeSeriesBuilder({"granularidades_min": [30], "rutas": [1]})
        serie = builder.build(df, ruta=1, granularidad_min=30)
        assert "granularidad_min" in serie.columns
        assert (serie["granularidad_min"] == 30).all()

    def test_gaps_crecen_al_reducir_granularidad(self):
        """Con datos dispersos, g15min tiene mas gaps que g60min."""
        df = pd.DataFrame(
            {
                "PK_INTERVALO_DESPACHO": [1, 2],
                "HORA_INICIAL_REAL": pd.to_datetime(["2024-04-16 08:00", "2024-04-16 12:00"]),
                "PASAJEROS": [10, 20],
                "FK_RUTA": [1, 1],
            }
        )
        builder = TimeSeriesBuilder({"granularidades_min": [15, 60], "rutas": [1]})
        s15 = builder.build(df, ruta=1, granularidad_min=15)
        s60 = builder.build(df, ruta=1, granularidad_min=60)
        assert int(s15["is_gap"].sum()) >= int(s60["is_gap"].sum())
