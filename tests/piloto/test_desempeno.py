"""Desempeno de la jornada D contra la prediccion emitida la noche anterior."""

import math
from datetime import date, datetime

import pandas as pd
import pytest

from proyecto_grado.piloto import correccion as corr
from proyecto_grado.piloto import desempeno as desemp
from proyecto_grado.piloto.config import RUTA_CONFIG_PREDETERMINADA, cargar_configuracion
from proyecto_grado.piloto.fechas import ZONA, objetivo_fijado

D = date(2026, 10, 12)
HORAS = ["05:00", "05:30", "06:00", "06:30"]


def serie(reales: dict[int, list[float]], dia: date = D) -> pd.DataFrame:
    filas = []
    for ruta, valores in reales.items():
        for hora, real in zip(HORAS, valores, strict=True):
            filas.append(
                {
                    "FK_RUTA": ruta,
                    "timestamp": pd.Timestamp(f"{dia} {hora}"),
                    "pasajeros_total": real,
                }
            )
    # Una franja de la jornada siguiente (sin dato) que no debe contar.
    filas.append({"FK_RUTA": 1, "timestamp": pd.Timestamp(f"{dia} 23:30"), "pasajeros_total": None})
    return pd.DataFrame(filas)


def emision(id_ejecucion, origen, ruta, preds, dia: date = D, horas=HORAS) -> pd.DataFrame:
    n = len(preds)
    return pd.DataFrame(
        {
            "id_ejecucion": id_ejecucion,
            "origen": origen,
            "version": "definitiva",
            "emitido": "",
            "route": [ruta] * n,
            "dia_op": [dia.isoformat()] * n,
            "hora": horas[:n],
            "tipo_dia": ["LABORAL"] * n,
            "regimen": ["ordinario"] * n,
            "pred_xgboost": preds,
            "ref52": preds,
            "factor": [1.0] * n,
            "pred_final": preds,
        }
    )


def historial(*partes) -> pd.DataFrame:
    return corr._normalizar(pd.concat(partes, ignore_index=True))


# ------------------------------------------------------------------ calculo


@pytest.mark.unit
def test_metricas_de_resultado_conocido():
    """real [10, 20, 0, 5] y pred [12, 18, 2, 5]: errores [2, -2, 2, 0]."""
    h = historial(
        emision("backtest_x", "backtest", 1, [1.0, 1.0, 1.0, 1.0]),
        emision("20261011_003000", "piloto", 1, [99.0, 99.0, 99.0, 99.0]),
        emision("20261012_003000", "piloto", 1, [12.0, 18.0, 2.0, 5.0]),  # la vigente
    )
    r = desemp.evaluar_jornada(h, serie({1: [10, 20, 0, 5]}), D, (1,), umbral_mape=10)["1"]
    assert r["n_franjas"] == 4
    assert r["mae"] == pytest.approx(1.5)
    assert r["rmse"] == pytest.approx(math.sqrt(3))
    assert r["sesgo"] == pytest.approx(0.5)
    assert r["total_real"] == 35 and r["total_pred"] == 37
    assert r["sesgo_pct"] == pytest.approx(2 / 35 * 100)  # (37 - 35) / 35
    assert r["wape"] == pytest.approx(6 / 35 * 100)
    assert r["id_corrida_prediccion"] == "20261012_003000"


@pytest.mark.unit
def test_mape_con_franjas_de_real_cero():
    """MAPE u10 solo con real >= 10; u1 con real > 0 (el 0 nunca entra)."""
    h = historial(emision("p", "piloto", 1, [12.0, 18.0, 2.0, 5.0]))
    r = desemp.evaluar_jornada(h, serie({1: [10, 20, 0, 5]}), D, (1,), umbral_mape=10)["1"]
    assert r["n_mape_u10"] == 2 and r["mape_u10"] == pytest.approx(15.0)  # (20% + 10%) / 2
    assert r["n_mape_u1"] == 3 and r["mape_u1"] == pytest.approx(10.0)  # (20% + 10% + 0%) / 3
    # Todas las franjas con real 0: MAPE sin franjas (NaN) y sin division por cero.
    r0 = desemp.evaluar_jornada(h, serie({1: [0, 0, 0, 0]}), D, (1,), umbral_mape=10)["1"]
    assert r0["n_mape_u1"] == 0 and math.isnan(r0["mape_u1"])
    assert math.isnan(r0["sesgo_pct"]) and math.isnan(r0["wape"])
    assert r0["mae"] == pytest.approx(37 / 4)


@pytest.mark.unit
def test_sin_prediccion_emitida_se_omite_con_motivo():
    s = serie({1: [10, 20, 0, 5], 3: [1, 2, 3, 4]})
    # Ruta 3 solo tiene relleno y backtest: no son predicciones emitidas.
    h = historial(
        emision("p", "piloto", 1, [12.0, 18.0, 2.0, 5.0]),
        emision("r", "relleno", 3, [1.0, 2.0, 3.0, 4.0]),
        emision("b", "backtest", 3, [1.0, 2.0, 3.0, 4.0]),
        emision("p0", "piloto", 3, [1.0, 2.0, 3.0, 4.0], dia=date(2026, 10, 11)),  # otra jornada
    )
    r = desemp.evaluar_jornada(h, s, D, (1, 3), umbral_mape=10)
    assert "motivo" not in r["1"]
    assert r["3"] == {"motivo": "sin_prediccion_emitida"}
    assert desemp.evaluar_jornada(None, s, D, (1, 3), 10) == {
        "1": {"motivo": "sin_prediccion_emitida"},
        "3": {"motivo": "sin_prediccion_emitida"},
    }


@pytest.mark.unit
def test_sin_reales_o_sin_franjas_comunes():
    h = historial(emision("p", "piloto", 1, [12.0, 18.0, 2.0, 5.0]))
    assert desemp.evaluar_jornada(h, serie({3: [1, 2, 3, 4]}), D, (1,), 10)["1"] == {
        "motivo": "sin_reales"
    }
    otras = historial(emision("p", "piloto", 1, [1.0], horas=["12:00"]))
    assert desemp.evaluar_jornada(otras, serie({1: [10, 20, 0, 5]}), D, (1,), 10)["1"] == {
        "motivo": "sin_franjas_comunes"
    }


# ------------------------------------------------------------------ indicadores


@pytest.mark.unit
def test_indicadores_una_fila_por_ruta_y_reemplazo_atomico(tmp_path):
    h = historial(emision("p", "piloto", 1, [12.0, 18.0, 2.0, 5.0]))
    por_ruta = desemp.evaluar_jornada(h, serie({1: [10, 20, 0, 5]}), D, (1, 3), 10)
    filas = desemp.filas_indicadores(por_ruta, D, "SOMBRA", "20261013_003000")
    assert list(filas.columns) == desemp.COLUMNAS and len(filas) == 1
    assert filas.iloc[0][["fecha", "ruta", "grupo", "id_ejecucion"]].tolist() == [
        "2026-10-12",
        1,
        "SOMBRA",
        "20261013_003000",
    ]
    ruta = desemp.guardar_indicadores(tmp_path / "indicadores", D, filas)
    assert ruta.name == "2026-10-12.parquet"
    filas["id_ejecucion"] = "20261013_020000"
    desemp.guardar_indicadores(tmp_path / "indicadores", D, filas)
    leido = pd.read_parquet(ruta)
    assert leido["id_ejecucion"].tolist() == ["20261013_020000"]
    assert sorted(p.name for p in (tmp_path / "indicadores").iterdir()) == [ruta.name]


# ------------------------------------------------------------------ orquestador


def ejecucion(salidas):
    from proyecto_grado.piloto.nocturno import Ejecucion

    return Ejecucion(
        id="20261013_003000",
        inicio=datetime(2026, 10, 13, 0, 30, tzinfo=ZONA),
        carpeta=salidas,
        salidas=salidas,
    )


def _reloj():
    return datetime(2026, 10, 13, 0, 31, tzinfo=ZONA)


@pytest.mark.unit
def test_orquestador_guarda_bloque_e_indicadores(tmp_path):
    from proyecto_grado.piloto.nocturno import Dependencias, Estado, evaluar_desempeno

    cfg = cargar_configuracion(RUTA_CONFIG_PREDETERMINADA)
    e = ejecucion(tmp_path)
    h = historial(emision("p", "piloto", 1, [12.0, 18.0, 2.0, 5.0]))
    ctx = {}
    objetivo = objetivo_fijado(date(2026, 10, 13))
    s = serie({1: [10, 20, 0, 5], 3: [0, 0, 0, 0]})
    evaluar_desempeno(e, cfg, h, s, objetivo, ctx, Dependencias(reloj=_reloj))
    b = e.manifiesto["desempeno"]
    assert b["jornada"] == "2026-10-12" and b["umbral_mape"] == 10
    assert b["por_ruta"]["3"] == {"motivo": "sin_prediccion_emitida"}
    assert b["por_ruta"]["1"]["mape_u10"] == pytest.approx(15.0)
    assert ctx["indicadores"] == tmp_path / "indicadores" / "2026-10-12.parquet"
    assert b["archivo"]["sha256"] and e.manifiesto["pasos"]["desempeno"]["estado"] == "OK"
    assert e.estado == Estado.EN_CURSO and e.advertencias == []


@pytest.mark.unit
def test_orquestador_nunca_falla_por_el_desempeno(tmp_path, monkeypatch):
    from proyecto_grado.piloto import nocturno

    def falla(*a, **k):
        raise RuntimeError("serie rota")

    monkeypatch.setattr(nocturno.desemp, "evaluar_jornada", falla)
    cfg = cargar_configuracion(RUTA_CONFIG_PREDETERMINADA)
    e = ejecucion(tmp_path)
    ctx = {}
    nocturno.evaluar_desempeno(
        e,
        cfg,
        None,
        serie({1: [1, 1, 1, 1]}),
        objetivo_fijado(date(2026, 10, 13)),
        ctx,
        nocturno.Dependencias(reloj=_reloj),
    )
    b = e.manifiesto["desempeno"]
    assert b["motivo"].startswith("error: RuntimeError: serie rota")
    assert "indicadores" not in ctx and e.estado == nocturno.Estado.EN_CURSO
    assert e.manifiesto["pasos"]["desempeno"]["estado"] == "OK"

    # Sin prediccion emitida: motivo por ruta y sin archivo.
    monkeypatch.undo()
    e2 = ejecucion(tmp_path / "b")
    nocturno.evaluar_desempeno(
        e2,
        cfg,
        None,
        serie({1: [1, 1, 1, 1]}),
        objetivo_fijado(date(2026, 10, 13)),
        {},
        nocturno.Dependencias(reloj=_reloj),
    )
    assert e2.manifiesto["desempeno"]["motivo"] == (
        "ruta 1: sin_prediccion_emitida; ruta 3: sin_prediccion_emitida"
    )
    assert not (tmp_path / "b" / "indicadores").exists()


@pytest.mark.unit
def test_corrida_anticipada_no_evalua_una_jornada_incompleta(tmp_path):
    from dataclasses import replace

    from proyecto_grado.piloto.nocturno import Dependencias, evaluar_desempeno

    cfg = cargar_configuracion(RUTA_CONFIG_PREDETERMINADA)
    e = ejecucion(tmp_path)
    objetivo = replace(objetivo_fijado(date(2026, 10, 13)), anticipada=True)
    evaluar_desempeno(
        e, cfg, None, serie({1: [1, 1, 1, 1]}), objetivo, {}, Dependencias(reloj=_reloj)
    )
    assert e.manifiesto["desempeno"]["motivo"].startswith("jornada_incompleta")
