"""Bloques 4-8 por ventana y serie de 30 minutos con las franjas de D+1."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from proyecto_grado.modeling.config import load_scenario_definitions, load_target_config
from proyecto_grado.modeling.experimentos import seleccionar_features
from proyecto_grado.modeling.hparam_search.runner import _preparar_ruta
from proyecto_grado.piloto.extraccion import (
    FuenteLocal,
    Ventana,
    calcular_pk_ancla,
    deduplicar,
)
from proyecto_grado.piloto.serie import (
    ErrorSerie,
    GPSLocal,
    _constructor,
    _sin_base,
    _SinConexion,
    conjunto_apto_piloto,
    construir_serie,
    extender_grilla,
    procesar_ventana,
)
from tests.piloto.conftest import (
    SEMILLA_APTO,
    SEMILLA_CRUDO,
    SEMILLA_DATASET,
    SEMILLA_FIN,
    SEMILLA_OBJETIVOS,
    requiere_horario,
    requiere_semilla,
)

CLAVES = ["FK_RUTA", "timestamp"]


@pytest.mark.unit
def test_sin_base_cuenta_consultas_y_restaura_las_funciones():
    from proyecto_grado.etl import gps as m_gps
    from proyecto_grado.etl import trip_end as m_fin

    original = (
        m_gps.conectar_bd,
        m_gps.obtener_detalle_rastreo,
        m_fin.fetch_gps_events_by_time_window,
    )
    local = GPSLocal(pd.DataFrame())
    with _sin_base(local):
        assert isinstance(m_gps.conectar_bd("bd_montebello_rdw_gps"), _SinConexion)
        assert m_gps.obtener_detalle_rastreo(None, 0, 1, "X").empty
        assert m_fin.fetch_gps_events_by_time_window(None, "X", 0, 1).empty
    assert local.consultas == {"placa": 0, "rastreo_salida": 1, "rastreo_fin": 1}
    assert (
        m_gps.conectar_bd,
        m_gps.obtener_detalle_rastreo,
        m_fin.fetch_gps_events_by_time_window,
    ) == original


@pytest.mark.unit
def test_sin_conexion_no_permite_consultas():
    with pytest.raises(ErrorSerie):
        _SinConexion().cursor()


@pytest.mark.unit
def test_procesar_ventana_no_reutiliza_una_raiz(tmp_path):
    with pytest.raises(ErrorSerie, match="ya existe"):
        procesar_ventana(pd.DataFrame({"x": [1]}), tmp_path)
    apto, info = procesar_ventana(pd.DataFrame(), tmp_path / "nueva")
    assert apto.empty and info["conjunto_apto"] == 0


@pytest.mark.unit
def test_conjunto_apto_piloto_corta_la_semilla_en_el_inicio_del_almacen():
    semilla = pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2, 3],
            "FECHA_INICIAL": ["2026-09-25", "2026-09-26", "2026-09-27"],
        }
    )
    almacen = pd.DataFrame({"PK_INTERVALO_DESPACHO": [4], "FECHA_INICIAL": ["2026-09-27"]})
    r = conjunto_apto_piloto(semilla, almacen, date(2026, 9, 27))
    assert list(r["PK_INTERVALO_DESPACHO"]) == [1, 2, 4]
    with pytest.raises(ErrorSerie, match="anteriores"):
        conjunto_apto_piloto(semilla, semilla, date(2026, 9, 27))
    with pytest.raises(ErrorSerie, match="repetidos"):
        conjunto_apto_piloto(semilla, almacen.assign(PK_INTERVALO_DESPACHO=1), date(2026, 9, 27))


@requiere_horario
@pytest.mark.unit
def test_extender_grilla_agrega_franjas_sin_demanda_hasta_el_cierre():
    cfg = load_target_config()
    ts = pd.date_range("2026-10-12 05:00", "2026-10-12 19:00", freq="30min")
    serie = pd.DataFrame(
        {
            "timestamp": ts,
            "pasajeros_total": 10.0,
            "despachos_count": 1.0,
            "pasajeros_promedio": 10.0,
            "ocupacion_p95": 10.0,
            "is_gap": False,
        }
    )
    b = _constructor(cfg)
    serie = b._enriquecer(serie)
    serie["granularidad_min"] = 30
    serie["FK_RUTA"] = 1
    serie = b._enriquecer_con_horario_operativo(serie)
    ext = extender_grilla(serie, date(2026, 10, 13), cfg)
    nuevas = ext.iloc[len(serie) :]
    assert nuevas["timestamp"].min() == pd.Timestamp("2026-10-12 19:30")
    assert nuevas["timestamp"].max() == pd.Timestamp("2026-10-14 03:30")
    assert nuevas["is_gap"].all() and nuevas["pasajeros_total"].isna().all()
    assert set(nuevas["FK_RUTA"]) == {1}
    # 2026-10-12 es lunes festivo: FESTIVO_PUENTE; el 13 es laboral.
    tipo = nuevas.set_index(nuevas["timestamp"].dt.date)["tipo_dia"]
    assert set(tipo.loc[[date(2026, 10, 12)]]) == {"FESTIVO_PUENTE"}
    assert set(tipo.loc[[date(2026, 10, 13)]]) == {"LABORAL"}
    assert list(ext.columns) == list(serie.columns)
    assert extender_grilla(ext, date(2026, 10, 13), cfg) is ext


@requiere_semilla
@pytest.mark.integration
def test_ventana_local_y_serie_reproducen_la_semilla(tmp_path):
    """Controles 8.2 y 8.3 en modo local: ventana del 27 al 30 de septiembre."""
    v = Ventana(date(2026, 9, 27), date(2026, 9, 30), "prueba")
    semilla_crudo = pd.read_csv(SEMILLA_CRUDO)
    semilla_apto = pd.read_parquet(SEMILLA_APTO)
    ancla = calcular_pk_ancla([semilla_crudo], v.inicio, 5000)
    crudo, _ = deduplicar(FuenteLocal(SEMILLA_CRUDO).extraer(v, ancla))
    apto, info = procesar_ventana(crudo, tmp_path / "etl", GPSLocal.desde_archivo(SEMILLA_FIN))
    assert info["consultas_gps_sin_resolver"] == {"placa": 0, "rastreo_salida": 0, "rastreo_fin": 0}

    fechas = pd.to_datetime(semilla_apto["FECHA_INICIAL"]).dt.date
    ref = semilla_apto[fechas.between(v.inicio, v.fin)]
    m = apto.merge(ref, on="PK_INTERVALO_DESPACHO", suffixes=("", "_s"), validate="1:1")
    assert len(m) == len(apto) == len(ref)
    for c in [
        "PASAJEROS_REALES",
        "FK_RUTA",
        "HORA_INICIAL_REAL",
        "HORA_FIN_FINAL",
        "HORA_FIN_FUENTE",
    ]:
        assert (m[c] == m[f"{c}_s"]).all(), c

    cfg = load_target_config(SEMILLA_OBJETIVOS)
    escenario = load_scenario_definitions()["sin_oferta"]
    total = conjunto_apto_piloto(semilla_apto, apto, v.inicio)
    serie = construir_serie(total, cfg, escenario, date(2026, 10, 1), "prueba", "hash")
    ds = pd.read_parquet(SEMILLA_DATASET)
    assert list(serie.columns) == list(ds.columns)
    corte = pd.Timestamp("2026-10-01 04:00")
    fin = corte + pd.Timedelta(days=1)
    features = seleccionar_features(_preparar_ruta(ds, 1, "pasajeros_total"))
    tramos = [
        (pd.Timestamp.min, corte, [*features, "pasajeros_total", "despachos_count_real"]),
        (corte, fin, features),  # D+1: solo las variables (sin demanda)
    ]
    for desde, hasta, columnas in tramos:
        a = serie[(serie["timestamp"] >= desde) & (serie["timestamp"] < hasta)]
        b = ds[(ds["timestamp"] >= desde) & (ds["timestamp"] < hasta)]
        u = a.merge(b, on=CLAVES, suffixes=("", "_d"), how="outer", indicator=True)
        assert (u["_merge"] == "both").all()
        for c in columnas:
            x, y = u[c].astype(float), u[f"{c}_d"].astype(float)
            assert (np.isclose(x, y) | (x.isna() & y.isna())).all(), c
    assert serie.loc[serie["timestamp"] >= corte, "pasajeros_total"].isna().all()
