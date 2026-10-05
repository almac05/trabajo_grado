"""Pruebas del modulo de recomendacion de despacho con datos sinteticos."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from proyecto_grado.dispatch.config import (
    BloqueHorario,
    ErrorConfiguracionRecomendacion,
    cargar_configuracion_recomendacion,
)
from proyecto_grado.dispatch.evaluacion import (
    clasificar,
    construir_franjas_evaluacion,
    franjas_reales,
    tabla_comparacion_despachos,
)
from proyecto_grado.dispatch.parametros import (
    asignar_bloque,
    calcular_capacidad,
    calcular_tabla_parametros,
    preparar_despachos,
)
from proyecto_grado.dispatch.predictor_mixto import (
    FUENTE_REFERENCIA,
    FUENTE_RESPALDO,
    FUENTE_XGBOOST,
    construir_prediccion_mixta,
)
from proyecto_grado.dispatch.reglas import (
    aplicar_factibilidad,
    despachos_ordinario,
    despachos_raro,
    recomendar_despachos,
    redondeo_aritmetico,
)

BLOQUES = (
    BloqueHorario("madrugada", 4),
    BloqueHorario("pico_manana", 5),
    BloqueHorario("manana", 7),
    BloqueHorario("valle", 10),
    BloqueHorario("pico_tarde", 14),
    BloqueHorario("cierre", 16),
)
TIPOS_RAROS = ("FESTIVO", "FESTIVO_PUENTE")


def _franjas(demandas: list[float], regimen: str = "ordinario") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "route": 1,
            "dia_op": "2026-04-06",
            "hora": [f"{6 + i // 2:02d}:{30 * (i % 2):02d}" for i in range(len(demandas))],
            "regimen": regimen,
            "demanda_predicha": demandas,
            "mediana": 22.0 if regimen == "raro" else 54.0,
            "mediana_ordinaria": 54.0,
            "q3_ordinario": 65.0,
        }
    )


# ------------------------------------------------------------------------- reglas


@pytest.mark.unit
def test_150_pasajeros_con_mediana_54_y_q3_65_dan_3_despachos() -> None:
    assert despachos_ordinario([150.0], 54.0, 65.0, usar_tope=True, minimo=1)[0] == 3
    assert despachos_ordinario([150.0], 54.0, 65.0, usar_tope=False, minimo=1)[0] == 3


@pytest.mark.unit
def test_70_pasajeros_dan_2_con_tope_y_1_sin_tope() -> None:
    assert despachos_ordinario([70.0], 54.0, 65.0, usar_tope=True, minimo=1)[0] == 2
    assert despachos_ordinario([70.0], 54.0, 65.0, usar_tope=False, minimo=1)[0] == 1


@pytest.mark.unit
def test_redondeo_aritmetico_sube_los_medios() -> None:
    assert redondeo_aritmetico(2.5) == 3
    assert round(2.5) == 2  # el redondeo de Python iria al par
    np.testing.assert_array_equal(
        redondeo_aritmetico([0.5, 1.5, 2.4999, 3.5, 4.5, 2.0]), [1, 2, 2, 4, 5, 2]
    )
    # 135 / 54 = 2,5 exacto: sin tope, la regla de la mediana da 3.
    assert despachos_ordinario([135.0], 54.0, 65.0, usar_tope=False, minimo=1)[0] == 3


@pytest.mark.unit
@pytest.mark.parametrize("minimo", [1, 2])
def test_nunca_menos_despachos_que_el_minimo(minimo: int) -> None:
    demandas = [0.0, -5.0, 3.0, 20.0]
    assert (despachos_ordinario(demandas, 54.0, 65.0, True, minimo) >= minimo).all()
    assert (despachos_ordinario(demandas, 54.0, 65.0, False, minimo) >= minimo).all()
    assert (despachos_raro(demandas, 22.0, minimo) >= minimo).all()

    recomendadas = recomendar_despachos(_franjas(demandas), "divisor_propio", True, minimo)
    ajustadas, jornadas = aplicar_factibilidad(recomendadas, capacidad=0, minimo=minimo)
    assert (ajustadas["despachos_recomendados"] >= minimo).all()
    assert not jornadas["factible"].iloc[0]


@pytest.mark.unit
def test_regimen_raro_usa_el_divisor_de_la_politica() -> None:
    franjas = _franjas([50.0], regimen="raro")
    propio = recomendar_despachos(franjas, "divisor_propio", True, 1)
    ordinario = recomendar_despachos(franjas, "divisor_ordinario", True, 1)
    assert propio["despachos_sin_ajuste"].iloc[0] == 2  # 50 / 22 = 2,27
    assert ordinario["despachos_sin_ajuste"].iloc[0] == 1  # 50 / 54 = 0,93
    # El tope de carga solo aplica en regimen ordinario.
    sin_tope = recomendar_despachos(franjas, "divisor_ordinario", False, 1)
    assert sin_tope["despachos_sin_ajuste"].iloc[0] == 1


@pytest.mark.unit
def test_factibilidad_retira_primero_de_la_franja_menos_cargada() -> None:
    franjas = _franjas([100.0, 300.0]).assign(despachos_sin_ajuste=[4, 4])
    ajustadas, jornadas = aplicar_factibilidad(franjas, capacidad=7, minimo=1)
    # Al retirar uno: 100 / 3 = 33 frente a 300 / 3 = 100; se retira de la primera.
    assert ajustadas["despachos_recomendados"].tolist() == [3, 4]
    assert ajustadas["despachos_retirados"].tolist() == [1, 0]
    assert bool(jornadas["ajustada"].iloc[0])
    assert jornadas["total_recomendado"].iloc[0] == 7

    # Con mas retiros se reevalua tras cada uno: 100/2 = 50 < 300/3 = 100,
    # luego 100/1 = 100 frente a 300/3 = 100 (empate: primera en orden), etc.
    ajustadas, _ = aplicar_factibilidad(franjas, capacidad=5, minimo=1)
    assert ajustadas["despachos_recomendados"].tolist() == [1, 4]


@pytest.mark.unit
def test_factibilidad_no_toca_jornadas_dentro_de_la_capacidad() -> None:
    franjas = _franjas([100.0, 300.0]).assign(despachos_sin_ajuste=[2, 6])
    ajustadas, jornadas = aplicar_factibilidad(franjas, capacidad=8, minimo=1)
    assert ajustadas["despachos_recomendados"].tolist() == [2, 6]
    assert not bool(jornadas["ajustada"].iloc[0])


# --------------------------------------------------------------- predictor mixto


def _artefactos() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    referencia = pd.DataFrame(
        {
            "route": [1, 1, 1, 3],
            "dia_op": ["2026-04-06", "2026-04-06", "2026-04-07", "2026-04-06"],
            "tipo_dia": ["LABORAL", "LABORAL", "FESTIVO", "LABORAL"],
            "hora": ["06:00", "06:30", "06:00", "06:00"],
            "real": [100.0, 120.0, 30.0, 90.0],
            "pred_gru": [0.0, 0.0, 0.0, 0.0],
            "pred_media": [95.0, 110.0, 25.0, 80.0],
        }
    )
    xgboost = pd.DataFrame(
        {
            "route": [1, 1, 3],
            "dia_op": ["2026-04-06", "2026-04-07", "2026-04-06"],
            "hora": ["06:00", "06:00", "06:00"],
            "pred_xgboost": [101.0, 40.0, 88.0],
        }
    )
    jornadas = pd.DataFrame({"route": [1, 1], "dia_op": ["2026-04-06", "2026-04-07"]})
    return xgboost, referencia, jornadas


@pytest.mark.unit
def test_respaldo_con_la_referencia_cuando_falta_xgboost(caplog: pytest.LogCaptureFixture) -> None:
    xgboost, referencia, jornadas = _artefactos()
    with caplog.at_level("WARNING", logger="proyecto_grado.dispatch.predictor_mixto"):
        pred = construir_prediccion_mixta(xgboost, referencia, jornadas, TIPOS_RAROS)

    pred = pred.set_index(["route", "dia_op", "hora"])
    # La ruta 3 no esta en las jornadas comunes.
    assert len(pred) == 3
    ordinaria = pred.loc[(1, "2026-04-06", "06:00")]
    respaldo = pred.loc[(1, "2026-04-06", "06:30")]
    rara = pred.loc[(1, "2026-04-07", "06:00")]
    assert ordinaria["fuente"] == FUENTE_XGBOOST and ordinaria["demanda_predicha"] == 101.0
    assert respaldo["fuente"] == FUENTE_RESPALDO and respaldo["demanda_predicha"] == 110.0
    assert rara["fuente"] == FUENTE_REFERENCIA and rara["demanda_predicha"] == 25.0
    assert "sin prediccion de XGBoost" in caplog.text


# --------------------------------------------------------------------- calibracion


@pytest.mark.unit
def test_asignar_bloque_por_hora_de_inicio() -> None:
    horas = pd.Series([3, 4, 5, 6, 7, 9, 10, 13, 14, 15, 16, 23])
    assert asignar_bloque(horas, BLOQUES).tolist() == [
        None,
        "madrugada",
        "pico_manana",
        "pico_manana",
        "manana",
        "manana",
        "valle",
        "valle",
        "pico_tarde",
        "pico_tarde",
        "cierre",
        "cierre",
    ]


@pytest.mark.unit
def test_preparar_despachos_toma_el_tipo_de_dia_del_dataset() -> None:
    model_ready = pd.DataFrame(
        {
            "FK_RUTA": [1, 1, 1],
            # 03:50 pertenece a la jornada anterior; 04:10 cae fuera de las franjas del dataset.
            "HORA_INICIAL_REAL": pd.to_datetime(
                ["2026-04-06 06:10", "2026-04-07 03:50", "2026-04-07 04:10"]
            ),
            "PASAJEROS_REALES": [40, 20, 30],
            "MODEL_READY_OK": [True, True, True],
        }
    )
    tipo_dia = pd.DataFrame(
        {
            "FK_RUTA": [1, 1, 1],
            "timestamp": pd.to_datetime(
                ["2026-04-06 06:00", "2026-04-07 03:30", "2026-04-07 05:00"]
            ),
            "tipo_dia": ["FESTIVO_PUENTE", "FESTIVO_PUENTE", "LABORAL"],
        }
    )
    despachos = preparar_despachos(model_ready, tipo_dia, BLOQUES, TIPOS_RAROS)
    assert despachos["dia_op"].tolist() == [date(2026, 4, 6), date(2026, 4, 6), date(2026, 4, 7)]
    assert despachos["hora"].tolist() == ["06:00", "03:30", "04:00"]
    assert despachos["tipo_dia"].tolist() == ["FESTIVO_PUENTE", "FESTIVO_PUENTE", "LABORAL"]
    assert despachos["tipo_dia_fuente"].tolist() == ["franja", "franja", "jornada"]
    assert despachos["regimen"].tolist() == ["raro", "raro", "ordinario"]


@pytest.mark.unit
def test_tabla_de_parametros_y_capacidad() -> None:
    filas = []
    for ruta in (1, 3):
        for bloque in BLOQUES:
            for pasajeros in (10, 20, 30, 40):
                filas.append((ruta, date(2026, 1, 5), bloque.nombre, "ordinario", pasajeros))
        filas += [(ruta, date(2026, 1, 6), "valle", "raro", p) for p in (5, 15)]
    despachos = pd.DataFrame(filas, columns=["route", "dia_op", "bloque", "regimen", "pasajeros"])
    tabla = calcular_tabla_parametros(despachos, BLOQUES)

    assert len(tabla) == 14
    ordinaria = tabla[(tabla["route"] == 1) & (tabla["bloque"] == "valle")].iloc[0]
    assert (ordinaria["q1"], ordinaria["mediana"], ordinaria["q3"]) == (17.5, 25.0, 32.5)
    rara = tabla[(tabla["route"] == 3) & (tabla["regimen"] == "raro")].iloc[0]
    assert rara["bloque"] == "todos" and rara["mediana"] == 10.0
    assert calcular_capacidad(despachos) == (48, date(2026, 1, 5))


# ---------------------------------------------------------------------- evaluacion


@pytest.mark.unit
def test_clasificacion_y_comparacion_con_lo_real() -> None:
    ppd = pd.Series([70.0, 50.0, 20.0, np.nan])
    assert clasificar(
        ppd, pd.Series(35.0, index=ppd.index), pd.Series(65.0, index=ppd.index)
    ).tolist() == [
        "sobrecargada",
        "normal",
        "subutilizada",
        "sin_despachos",
    ]

    recomendacion = _franjas([150.0, 70.0]).assign(
        bloque="pico_manana",
        q1=36.0,
        q3=65.0,
        despachos_recomendados=[3, 2],
        despachos_retirados=0,
        real=[150.0, 70.0],
    )
    despachos = pd.DataFrame(
        {
            "route": 1,
            "dia_op": [date(2026, 4, 6)] * 3,
            "hora": ["06:00", "06:00", "06:30"],
            "pasajeros": [80.0, 70.0, 70.0],
        }
    )
    franjas, verificacion = construir_franjas_evaluacion(recomendacion, franjas_reales(despachos))
    assert franjas["clase_real"].tolist() == ["sobrecargada", "sobrecargada"]
    assert franjas["comparacion"].tolist() == ["mayor", "mayor"]
    assert franjas["clase_recomendada"].tolist() == ["normal", "subutilizada"]
    assert verificacion["max_dif_demanda_real_vs_artefacto"] == 0.0

    tabla = tabla_comparacion_despachos(franjas, [b.nombre for b in BLOQUES])
    fila = tabla[(tabla["bloque"] == "todos") & (tabla["clase_real"] == "sobrecargada")].iloc[0]
    assert fila["n_franjas"] == 2 and fila["pct_mayor"] == 100.0


# ------------------------------------------------------------------- configuracion


@pytest.mark.unit
def test_carga_configuracion_de_recomendacion() -> None:
    config = cargar_configuracion_recomendacion()
    assert config.freeze == "freeze_20260922_203820"
    assert config.inicio_calibracion == date(2025, 12, 25)
    assert config.fin_calibracion == date(2026, 4, 1)
    assert config.inicio_evaluacion == date(2026, 4, 2)
    assert config.fin_evaluacion == date(2026, 6, 10)
    assert config.bloques == BLOQUES
    assert config.politica_festivos == "divisor_propio"
    assert config.usar_tope_carga is True
    assert config.servicio_minimo == 1
    assert config.tipos_raros == TIPOS_RAROS


@pytest.mark.unit
@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("politica_festivos", "otra", "politica_festivos"),
        ("servicio_minimo", 0, "servicio_minimo"),
        ("usar_tope_carga", "si", "usar_tope_carga"),
    ],
)
def test_rechaza_reglas_invalidas(tmp_path: Path, campo: str, valor: object, mensaje: str) -> None:
    raw = yaml.safe_load(Path("configs/dispatch/recomendacion.yaml").read_text(encoding="utf-8"))
    raw["reglas"][campo] = valor
    ruta = tmp_path / "recomendacion.yaml"
    ruta.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ErrorConfiguracionRecomendacion, match=mensaje):
        cargar_configuracion_recomendacion(ruta)
