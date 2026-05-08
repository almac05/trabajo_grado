"""Pruebas unitarias para OperationalHoursEstimator y la funcion classify_tipo_dia_ext."""

from datetime import date

import holidays as holidays_lib
import numpy as np
import pandas as pd

from proyecto_grado.features.operational_hours import (
    OperationalHoursEstimator,
    classify_tipo_dia_ext,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CFG_TEST = {
    "umbral_actividad": 0.10,
    "umbral_anomalia": 0.30,
    "min_dias_muestra": 2,  # umbral bajo para datos sinteticos
    "incluir_festivo_puente": True,
}


def _make_series_for_tipo(
    tipo_dia: str,
    n_days: int,
    gran: int,
    service_start_h: int,
    service_end_h: int,
    ruta: int = 1,
    base_date: str = "2024-05-06",  # lunes no festivo
) -> pd.DataFrame:
    """Crea un DataFrame sintetico de serie temporal para un tipo de dia.

    Asigna is_gap=False entre service_start_h y service_end_h (inclusive),
    y is_gap=True fuera de ese rango.
    """
    # Mapeo tipo_dia → (dia_semana, es_festivo)
    tipo_map: dict[str, tuple[int, bool]] = {
        "LABORAL": (0, False),  # lunes no festivo
        "SABADO": (5, False),
        "DOMINGO": (6, False),
        "FESTIVO": (2, True),  # miercoles festivo
        "FESTIVO_PUENTE": (0, True),  # lunes festivo
    }
    dia_semana, es_festivo = tipo_map[tipo_dia]

    rows = []
    start = pd.Timestamp(base_date)
    for day_offset in range(n_days):
        day = start + pd.Timedelta(days=day_offset * 7)  # mismo dia de semana c/semana
        slots = pd.date_range(day, periods=24 * 60 // gran, freq=f"{gran}min")
        for ts in slots:
            h = ts.hour
            rows.append(
                {
                    "timestamp": ts,
                    "is_gap": not (service_start_h <= h <= service_end_h),
                    "dia_semana": dia_semana,
                    "es_festivo": es_festivo,
                    "FK_RUTA": ruta,
                    "granularidad_min": gran,
                    "pasajeros_total": 10.0 if (service_start_h <= h <= service_end_h) else 0.0,
                    "despachos_count": 1 if (service_start_h <= h <= service_end_h) else 0,
                }
            )

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _make_combined_series(gran: int = 60, n_days_each: int = 15) -> pd.DataFrame:
    """Combina LABORAL (5-22h) y FESTIVO (8-18h) en una sola serie."""
    laboral = _make_series_for_tipo("LABORAL", n_days_each, gran, 5, 22)
    festivo = _make_series_for_tipo("FESTIVO", n_days_each, gran, 8, 18)
    return pd.concat([laboral, festivo], ignore_index=True)


# ---------------------------------------------------------------------------
# Tests: classify_tipo_dia_ext
# ---------------------------------------------------------------------------


class TestClassifyTipoDiaExt:
    def test_festivo_puente_lunes_festivo(self):
        """Lunes festivo debe clasificar como FESTIVO_PUENTE."""
        assert classify_tipo_dia_ext(dia_semana=0, es_festivo=True) == "FESTIVO_PUENTE"

    def test_festivo_no_lunes(self):
        """Festivo en miercoles es FESTIVO (no puente)."""
        assert classify_tipo_dia_ext(dia_semana=2, es_festivo=True) == "FESTIVO"

    def test_sabado_no_festivo(self):
        assert classify_tipo_dia_ext(dia_semana=5, es_festivo=False) == "SABADO"

    def test_domingo_no_festivo(self):
        assert classify_tipo_dia_ext(dia_semana=6, es_festivo=False) == "DOMINGO"

    def test_lunes_no_festivo(self):
        assert classify_tipo_dia_ext(dia_semana=0, es_festivo=False) == "LABORAL"

    def test_viernes_no_festivo(self):
        assert classify_tipo_dia_ext(dia_semana=4, es_festivo=False) == "LABORAL"

    def test_jan6_2025_es_festivo_puente(self):
        """6 de enero de 2025 (Reyes Magos) es lunes festivo en Colombia."""
        jan6 = date(2025, 1, 6)
        co_holidays = set(holidays_lib.Colombia(years=2025))
        assert jan6 in co_holidays, "El 6-ene-2025 debe ser festivo en Colombia"
        assert jan6.weekday() == 0, "El 6-ene-2025 debe ser lunes"
        result = classify_tipo_dia_ext(dia_semana=jan6.weekday(), es_festivo=True)
        assert result == "FESTIVO_PUENTE"


# ---------------------------------------------------------------------------
# Tests: OperationalHoursEstimator
# ---------------------------------------------------------------------------


class TestOperationalHoursEstimator:
    def _build_series_dict(
        self, gran: int = 60, n_days: int = 15
    ) -> dict[tuple[int, int], pd.DataFrame]:
        df = _make_combined_series(gran=gran, n_days_each=n_days)
        return {(1, gran): df}

    def test_fit_retorna_dataframe_no_vacio(self):
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        assert not result.empty

    def test_fit_columnas_requeridas(self):
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        expected_cols = {
            "tipo_dia",
            "ruta",
            "granularidad_min",
            "hora_inicio_op",
            "hora_fin_op",
            "hora_inicio_op_min",
            "hora_fin_op_min",
            "duracion_operativa_h",
            "n_dias_muestra",
            "n_dias_usado",
            "umbral_usado",
            "fallback_laboral",
            "franjas_anomalas_count",
            "pct_cobertura_dentro_horario",
        }
        assert expected_cols.issubset(set(result.columns))

    def test_festivo_vs_laboral_horarios_distintos(self):
        """FESTIVO (8-18h) y LABORAL (5-22h) deben producir horarios distintos."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())

        laboral = result[result["tipo_dia"] == "LABORAL"].iloc[0]
        festivo = result[result["tipo_dia"] == "FESTIVO"].iloc[0]

        assert laboral["hora_inicio_op"] != "" and festivo["hora_inicio_op"] != ""

        # Al menos 30 minutos de diferencia en inicio o fin
        diff_inicio = abs(int(laboral["hora_inicio_op_min"]) - int(festivo["hora_inicio_op_min"]))
        diff_fin = abs(int(laboral["hora_fin_op_min"]) - int(festivo["hora_fin_op_min"]))
        assert diff_inicio >= 30 or diff_fin >= 30, (
            f"LABORAL ({laboral['hora_inicio_op']}-{laboral['hora_fin_op']}) y "
            f"FESTIVO ({festivo['hora_inicio_op']}-{festivo['hora_fin_op']}) "
            "deberan diferir al menos 30 minutos"
        )

    def test_laboral_horario_correcto(self):
        """Para datos sinteticos 5-22h, el estimador debe detectar inicio=05:00, fin=22:00."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        laboral = result[result["tipo_dia"] == "LABORAL"].iloc[0]
        assert laboral["hora_inicio_op"] == "05:00"
        assert laboral["hora_fin_op"] == "22:00"

    def test_festivo_horario_correcto(self):
        """Para datos sinteticos 8-18h en FESTIVO, el estimador debe detectar inicio=08:00, fin=18:00."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        festivo = result[result["tipo_dia"] == "FESTIVO"].iloc[0]
        assert festivo["hora_inicio_op"] == "08:00"
        assert festivo["hora_fin_op"] == "18:00"

    def test_horario_rango_continuo(self):
        """hora_inicio_op_min <= hora_fin_op_min para todos los registros con horario valido."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        validos = result[result["hora_inicio_op"] != ""]
        assert (validos["hora_inicio_op_min"] <= validos["hora_fin_op_min"]).all()

    def test_pct_cobertura_no_excede_uno(self):
        """pct_cobertura_dentro_horario debe ser siempre <= 1.0."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        assert (result["pct_cobertura_dentro_horario"] <= 1.0).all()
        assert (result["pct_cobertura_dentro_horario"] >= 0.0).all()

    def test_duracion_operativa_positiva(self):
        """duracion_operativa_h debe ser positiva para horarios validos."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        validos = result[result["hora_inicio_op"] != ""]
        assert (validos["duracion_operativa_h"] > 0).all()

    def test_fallback_laboral_con_pocos_dias(self):
        """Tipo de dia con < min_dias_muestra usa LABORAL como proxy."""
        # min_dias_muestra=10 pero solo 3 dias de FESTIVO → fallback activo
        cfg_alto = {**_CFG_TEST, "min_dias_muestra": 10}
        df = _make_combined_series(gran=60, n_days_each=3)
        series_dict = {(1, 60): df}
        est = OperationalHoursEstimator(cfg=cfg_alto)
        result = est.fit(series_dict)
        festivo = result[result["tipo_dia"] == "FESTIVO"]
        if not festivo.empty:
            assert bool(festivo.iloc[0]["fallback_laboral"])

    def test_franjas_anomalas_count_no_negativo(self):
        """franjas_anomalas_count debe ser >= 0."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        assert (result["franjas_anomalas_count"] >= 0).all()

    def test_fit_sin_datos_retorna_vacio(self):
        """fit() con un diccionario vacio retorna DataFrame vacio."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit({})
        assert result.empty

    def test_fit_con_dataframe_vacio_omitido(self):
        """Series vacias deben ignorarse sin error."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit({(1, 60): pd.DataFrame()})
        assert result.empty

    def test_tipos_dia_presentes(self):
        """El resultado incluye LABORAL y FESTIVO cuando hay datos de ambos."""
        est = OperationalHoursEstimator(cfg=_CFG_TEST)
        result = est.fit(self._build_series_dict())
        tipos = set(result["tipo_dia"].unique())
        assert "LABORAL" in tipos
        assert "FESTIVO" in tipos


# ---------------------------------------------------------------------------
# Tests: gap_tipo en TimeSeriesBuilder (logica del np.select)
# ---------------------------------------------------------------------------


class TestGapTipoLogica:
    """Verifica la logica de clasificacion gap_tipo de forma aislada."""

    def _apply_gap_tipo(self, is_gap: list[bool], dentro: list[bool]) -> list[str]:
        agg = pd.DataFrame({"is_gap": is_gap, "dentro_horario_operativo": dentro})
        conditions = [~agg["is_gap"], agg["is_gap"] & agg["dentro_horario_operativo"]]
        choices = ["operativo", "gap_anomalo"]
        agg["gap_tipo"] = np.select(conditions, choices, default="fuera_operacion")
        return agg["gap_tipo"].tolist()

    def test_tres_categorias_correctas(self):
        tipos = self._apply_gap_tipo(
            is_gap=[False, True, True],
            dentro=[True, True, False],
        )
        assert tipos == ["operativo", "gap_anomalo", "fuera_operacion"]

    def test_gap_tipo_valores_validos(self):
        """gap_tipo solo toma los tres valores definidos y no tiene nulos."""
        agg = pd.DataFrame(
            {
                "is_gap": [False] * 6 + [True] * 6,
                "dentro_horario_operativo": [True, False] * 6,
            }
        )
        conditions = [~agg["is_gap"], agg["is_gap"] & agg["dentro_horario_operativo"]]
        choices = ["operativo", "gap_anomalo"]
        agg["gap_tipo"] = np.select(conditions, choices, default="fuera_operacion")

        valid_values = {"operativo", "gap_anomalo", "fuera_operacion"}
        assert agg["gap_tipo"].isin(valid_values).all(), "gap_tipo contiene valor inesperado"
        assert agg["gap_tipo"].notna().all(), "gap_tipo tiene nulos"

    def test_sin_gap_siempre_operativo(self):
        """Filas sin gap siempre son 'operativo', independientemente de dentro_horario."""
        tipos = self._apply_gap_tipo(
            is_gap=[False, False],
            dentro=[True, False],
        )
        assert all(t == "operativo" for t in tipos)

    def test_gap_fuera_horario_es_fuera_operacion(self):
        tipos = self._apply_gap_tipo(
            is_gap=[True],
            dentro=[False],
        )
        assert tipos == ["fuera_operacion"]
