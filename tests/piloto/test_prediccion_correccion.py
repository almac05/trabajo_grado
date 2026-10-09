"""Prediccion de D+1, historial de predicciones emitidas y factor de 14 dias."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from proyecto_grado.modeling.config import load_scenario_definitions, load_target_config
from proyecto_grado.piloto.config import cargar_configuracion
from proyecto_grado.piloto.correccion import (
    COLUMNAS,
    ErrorHistorial,
    agregar_al_historial,
    calcular_factor,
    emision_vigente,
    filas_backtest,
    filas_emitidas,
    leer_historial,
)
from proyecto_grado.piloto.prediccion import (
    ErrorPrediccion,
    cargar_parametros,
    predecir_jornada,
    prediccion_final,
)
from proyecto_grado.piloto.recomendacion import cargar_modulo, recomendar
from proyecto_grado.piloto.serie import construir_serie
from tests.piloto.conftest import requiere_semilla

RANGO = (0.68, 1.08)


def historial(filas):
    """filas: (origen, id, route, dia_op, hora, pred, regimen)."""
    return pd.DataFrame(
        [
            {
                "id_ejecucion": i,
                "origen": o,
                "version": "definitiva",
                "emitido": "",
                "route": r,
                "dia_op": d,
                "hora": h,
                "tipo_dia": "LABORAL",
                "regimen": reg,
                "pred_xgboost": p,
                "ref52": p,
                "factor": np.nan,
                "pred_final": np.nan,
            }
            for o, i, r, d, h, p, reg in filas
        ],
        columns=COLUMNAS,
    )


def serie_real(filas):
    """filas: (route, dia_op, hora, real)."""
    ts = pd.to_datetime([f"{d} {h}" for _, d, h, _ in filas])
    return pd.DataFrame(
        {
            "FK_RUTA": [r for r, *_ in filas],
            "timestamp": ts,
            "pasajeros_total": [v for *_, v in filas],
        }
    )


def jornada(dia, n, real, pred, origen="backtest", ident="b", ruta=1, regimen="ordinario"):
    horas = [f"{5 + i // 2:02d}:{30 * (i % 2):02d}" for i in range(n)]
    h = historial([(origen, ident, ruta, dia, x, pred, regimen) for x in horas])
    s = serie_real([(ruta, dia, x, real) for x in horas])
    return h, s


# ------------------------------------------------------------------ historial


@pytest.mark.unit
def test_historial_solo_agrega_y_verifica_su_sha(tmp_path):
    assert leer_historial(tmp_path) is None
    h1, _ = jornada("2026-10-01", 3, 1, 1)
    agregar_al_historial(tmp_path, "e1", h1)
    h2, _ = jornada("2026-10-02", 2, 1, 1, ident="e2")
    meta = agregar_al_historial(tmp_path, "e2", h2)
    actual = leer_historial(tmp_path)
    assert len(actual) == 5 and meta["filas_agregadas"] == 2
    assert (tmp_path / "predicciones_emitidas_e1.parquet").exists()
    with pytest.raises(ErrorHistorial, match="No se sobrescribe"):
        agregar_al_historial(tmp_path, "e2", h2)
    # Alterar la version vigente se detecta.
    actual.iloc[:1].to_parquet(tmp_path / "predicciones_emitidas_e2.parquet")
    with pytest.raises(ErrorHistorial, match="SHA-256"):
        leer_historial(tmp_path)


@pytest.mark.unit
def test_historial_rechaza_origen_desconocido(tmp_path):
    h, _ = jornada("2026-10-01", 1, 1, 1, origen="ensayo")
    with pytest.raises(ErrorHistorial, match="Origen"):
        agregar_al_historial(tmp_path, "e1", h)


@pytest.mark.unit
def test_emision_vigente_prefiere_piloto_y_la_mas_reciente():
    h = historial(
        [
            ("backtest", "b", 1, "2026-10-05", "05:00", 10, "ordinario"),
            ("relleno", "r1", 1, "2026-10-05", "05:00", 20, "ordinario"),
            ("relleno", "r2", 1, "2026-10-05", "05:00", 30, "ordinario"),
            ("backtest", "b", 1, "2026-10-06", "05:00", 40, "ordinario"),
            ("piloto", "p", 1, "2026-10-07", "05:00", 50, "ordinario"),
            ("relleno", "r3", 1, "2026-10-07", "05:00", 60, "ordinario"),
        ]
    )
    v = emision_vigente(h).set_index("dia_op")["pred_xgboost"]
    assert v.to_dict() == {"2026-10-05": 30, "2026-10-06": 40, "2026-10-07": 50}


# ------------------------------------------------------------------ factor


@pytest.mark.unit
def test_factor_es_suma_real_sobre_suma_pred_de_la_ventana():
    h1, s1 = jornada("2026-10-10", 10, real=90, pred=100)
    h2, s2 = jornada("2026-10-14", 10, real=80, pred=100)
    h3, s3 = jornada("2026-10-15", 10, real=999, pred=1)  # la propia jornada: fuera
    h4, s4 = jornada("2026-09-30", 10, real=999, pred=1)  # antes de la ventana
    h = pd.concat([h1, h2, h3, h4], ignore_index=True)
    s = pd.concat([s1, s2, s3, s4], ignore_index=True)
    f = calcular_factor(h, s, date(2026, 10, 15), 1, 14, 8, RANGO)
    assert f.aplicado and f.valor == pytest.approx(170 / 200)
    assert (f.franjas, f.jornadas) == (20, 2)
    assert f.ventana == ("2026-10-01", "2026-10-14")
    assert f.advertencias == []


@pytest.mark.unit
def test_factor_excluye_raros_otras_rutas_franjas_sin_real_y_jornadas_cortas():
    h1, s1 = jornada("2026-10-10", 10, real=90, pred=100)
    h2, s2 = jornada("2026-10-11", 10, real=1, pred=100, regimen="raro")
    h3, s3 = jornada("2026-10-12", 10, real=1, pred=100, ruta=3)
    h4, s4 = jornada("2026-10-13", 7, real=1, pred=100)  # menos de 8 observadas
    h5, _ = jornada("2026-10-14", 10, real=1, pred=100)  # sin demanda en la serie
    h = pd.concat([h1, h2, h3, h4, h5], ignore_index=True)
    s = pd.concat([s1, s2, s3, s4], ignore_index=True)
    f = calcular_factor(h, s, date(2026, 10, 15), 1, 14, 8, RANGO)
    assert f.valor == pytest.approx(0.9) and f.jornadas == 1


@pytest.mark.unit
def test_factor_uno_con_ventana_vacia_o_suma_pred_no_positiva():
    f = calcular_factor(historial([]), serie_real([]), date(2026, 10, 15), 1, 14, 8, RANGO)
    assert (f.valor, f.aplicado) == (1.0, False) and "factor 1" in f.advertencias[0]
    h, s = jornada("2026-10-10", 10, real=5, pred=0)
    f = calcular_factor(h, s, date(2026, 10, 15), 1, 14, 8, RANGO)
    assert (f.valor, f.aplicado) == (1.0, False)


@pytest.mark.unit
def test_factor_avisa_fuera_de_rango_y_jornadas_con_pocas_franjas():
    h, s = jornada("2026-10-10", 9, real=50, pred=100)
    f = calcular_factor(h, s, date(2026, 10, 15), 1, 14, 8, RANGO)
    assert f.valor == pytest.approx(0.5)
    assert any("fuera del rango" in a for a in f.advertencias)
    assert any("menos de 10" in a for a in f.advertencias)


@pytest.mark.unit
def test_prediccion_final_c3():
    pred = pd.DataFrame(
        {
            "route": [1, 1, 3],
            "regimen": ["ordinario", "raro", "ordinario"],
            "pred_xgboost": [100.0, 100.0, 50.0],
            "ref52": [7.0, 8.0, 9.0],
        }
    )
    out = prediccion_final(pred, {1: 0.9, 3: 1.1})
    assert out["pred_final"].tolist() == pytest.approx([90.0, 8.0, 55.0])
    with pytest.raises(ErrorPrediccion):
        prediccion_final(pred, {1: 0.9})


@pytest.mark.unit
def test_filas_emitidas():
    pred = prediccion_final(
        pd.DataFrame(
            {
                "route": [1],
                "dia_op": ["2026-10-13"],
                "hora": ["05:00"],
                "tipo_dia": ["LABORAL"],
                "regimen": ["ordinario"],
                "pred_xgboost": [10.0],
                "ref52": [9.0],
            }
        ),
        {1: 1.0},
    )
    f = filas_emitidas(pred, "e", "piloto", datetime(2026, 10, 13, 0, 31))
    assert f.loc[0, "emitido"] == "2026-10-13T00:31:00" and f.loc[0, "origen"] == "piloto"


# ------------------------------------------------------------------ contra los scripts 43 y 44


@requiere_semilla
@pytest.mark.integration
def test_c3_reproduce_los_scripts_43_y_44_el_1_de_octubre():
    """Control 8.4 para una jornada: XGBoost, ref52, factor y C3 (tolerancia 1e-4)."""
    cfg = cargar_configuracion()
    dia = date(2026, 10, 1)
    apto = pd.read_parquet(cfg.entrada("semilla_conjunto_apto"))
    apto = apto[pd.to_datetime(apto["FECHA_INICIAL"]).dt.date < dia]
    serie = construir_serie(
        apto,
        load_target_config(cfg.entrada("objetivos")),
        load_scenario_definitions(cfg.entrada("configuracion_escenarios"))["sin_oferta"],
        dia,
        "prueba",
        "hash",
    )
    p = cargar_parametros(
        cfg.entrada("configuracion_evaluacion"),
        cfg.entrada("hiperparametros_xgboost"),
        cfg.semanas_referencia_larga,
    )
    pred = predecir_jornada(serie, dia, p)
    assert pred.groupby("route").size().to_dict() == {1: 28, 3: 29}

    x43 = pd.read_csv(cfg.entrada("backtest_xgboost"))
    r52 = pd.read_csv(cfg.entrada("backtest_referencia_52s"))
    u = pred.merge(
        x43[x43["dia_op"] == str(dia)], on=["route", "hora"], suffixes=("", "_43")
    ).merge(r52[r52["dia_op"] == str(dia)], on=["route", "hora"])
    assert len(u) == (x43["dia_op"] == str(dia)).sum()
    assert (u["pred_xgboost"] - u["pred_xgboost_43"]).abs().max() < 1e-4
    assert (u["ref52"] - u["pred_media_52s"]).abs().max() < 1e-4

    hist = filas_backtest(
        cfg.entrada("backtest_xgboost"),
        cfg.entrada("backtest_referencia_52s"),
        cfg.fin_backtest,
        p.tipos_raros,
    )
    s44 = pd.read_csv("analisis/salidas/serie_correccion__correccion_nivel_20251127_20261003.csv")
    s44 = s44[(s44["dia_op"] == str(dia)) & (s44["ventana_dias"] == 14)].set_index("route")
    factores = {}
    for ruta in (1, 3):
        f = calcular_factor(
            hist,
            serie,
            dia,
            ruta,
            cfg.ventana_correccion_dias,
            cfg.min_franjas_jornada,
            cfg.rango_factor,
        )
        assert f.valor == pytest.approx(s44.loc[ruta, "factor"], abs=1e-12)
        assert f.franjas == s44.loc[ruta, "franjas_ventana"]
        factores[ruta] = f.valor
    final = prediccion_final(pred, factores)
    obs = pd.read_csv("analisis/salidas/observaciones__correccion_nivel_20251127_20261003.csv")
    u = final.merge(obs[obs["dia_op"] == str(dia)], on=["route", "hora"], suffixes=("", "_o"))
    assert (u["pred_final"] - u["C3 Mixto multiplicativo 14d"]).abs().max() < 1e-4

    modulo = cargar_modulo(
        cfg.entrada("configuracion_recomendacion"),
        cfg.entrada("parametros_recomendacion"),
        cfg.entrada("manifiesto_recomendacion"),
    )
    rec, ajuste = recomendar(final, serie, pd.Timestamp("2026-10-01 04:00"), modulo)
    assert len(rec) == len(final) and ajuste["factible"].all()
    assert (rec.loc[~rec["en_disponibilidad"], "despachos_recomendados"] == 0).all()
