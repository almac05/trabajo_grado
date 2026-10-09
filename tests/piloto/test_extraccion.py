"""Ventana, pk_ancla, fuentes, deduplicado, diferencias y almacen."""

from datetime import date

import pandas as pd
import pytest

from proyecto_grado.piloto.extraccion import (
    ErrorExtraccion,
    FuenteBD,
    FuenteLocal,
    Ventana,
    calcular_pk_ancla,
    calcular_ventana,
    deduplicar,
    diferencias,
    guardar_almacen,
    guardar_instantanea,
    leer_almacen,
    normalizar,
    reemplazar_ventana,
)
from proyecto_grado.piloto.fechas import objetivo_fijado

INICIO = date(2026, 9, 27)


def despachos(filas):
    """filas: (pk, fecha, pasajeros[, pk_registradora])."""
    return pd.DataFrame(
        [
            {
                "FECHA_INICIAL": f,
                "HORA_INICIAL_REAL": f"{f} 05:00:00",
                "FK_RUTA": 1,
                "PASAJEROS": p,
                "PK_INTERVALO_DESPACHO": pk,
                "PK_INFORMACION_REGISTRADORA": r[0] if r else pk * 10,
            }
            for pk, f, p, *r in filas
        ]
    )


# ------------------------------------------------------------------ ventana


@pytest.mark.unit
def test_ventana_ordinaria_de_siete_dias():
    v = calcular_ventana(objetivo_fijado(date(2026, 10, 14)), 7, 35, INICIO, date(2026, 10, 12))
    assert (v.inicio, v.fin, v.dias) == (date(2026, 10, 7), date(2026, 10, 13), 7)
    assert v.motivo == "ordinaria"


@pytest.mark.unit
def test_ventana_de_35_dias_si_la_jornada_objetivo_es_domingo():
    # 2026-11-08 es domingo: D = sabado 2026-11-07.
    v = calcular_ventana(objetivo_fijado(date(2026, 11, 8)), 7, 35, INICIO, date(2026, 11, 6))
    assert v.dias == 35 and v.fin == date(2026, 11, 7) and v.motivo == "domingo"


@pytest.mark.unit
def test_ventana_no_empieza_antes_del_almacen():
    v = calcular_ventana(objetivo_fijado(date(2026, 10, 18)), 7, 35, INICIO, date(2026, 10, 16))
    assert v.inicio == INICIO  # domingo: 35 dias se recortan al inicio del almacen


@pytest.mark.unit
def test_primera_ejecucion_cubre_desde_el_inicio_del_almacen():
    v = calcular_ventana(objetivo_fijado(date(2026, 10, 13)), 7, 35, INICIO, None)
    assert (v.inicio, v.fin) == (INICIO, date(2026, 10, 12))
    assert "ampliada" in v.motivo


@pytest.mark.unit
def test_ejecuciones_perdidas_amplian_la_ventana():
    v = calcular_ventana(objetivo_fijado(date(2026, 10, 20)), 7, 35, INICIO, date(2026, 10, 9))
    assert v.inicio == date(2026, 10, 10) and v.fin == date(2026, 10, 19)


@pytest.mark.unit
def test_ensayo_de_jornada_pasada_con_almacen_mas_adelantado():
    v = calcular_ventana(objetivo_fijado(date(2026, 10, 5)), 7, 35, INICIO, date(2026, 10, 20))
    assert (v.inicio, v.fin) == (date(2026, 9, 28), date(2026, 10, 4))


# ------------------------------------------------------------------ pk_ancla


@pytest.mark.unit
def test_pk_ancla_es_el_menor_pk_de_la_ventana_menos_el_margen():
    local = despachos([(100, "2026-10-01", 1), (9000, "2026-10-06", 1), (9500, "2026-10-07", 1)])
    assert calcular_pk_ancla([local], date(2026, 10, 6), 5000) == 4000
    # Sin despachos locales en la ventana: el mayor PK local.
    assert calcular_pk_ancla([local], date(2026, 10, 9), 100) == 9400
    assert calcular_pk_ancla([pd.DataFrame()], date(2026, 10, 9), 100) == 0


# ------------------------------------------------------------------ fuentes


class _Cursor:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, params=None):
        self.log.append(("execute", sql, params))

    def close(self):
        pass


class _Conexion:
    def __init__(self):
        self.log = []

    def cursor(self, **_):
        return _Cursor(self.log)

    def is_connected(self):
        return True

    def close(self):
        self.log.append(("close",))


@pytest.mark.unit
def test_fuente_bd_usa_la_consulta_del_etl_en_solo_lectura():
    con = _Conexion()
    llamadas = []

    def consultar(conexion, ini, fin, max_pk):
        llamadas.append((ini, fin, max_pk))
        assert ("execute", "SET SESSION TRANSACTION READ ONLY", None) in conexion.log
        return despachos([(5, "2026-10-12", 3)])

    fuente = FuenteBD(
        conectar=lambda bd: con if bd == "bd_montebello_rdw" else None, consultar=consultar
    )
    v = Ventana(date(2026, 10, 6), date(2026, 10, 12), "ordinaria")
    df = fuente.extraer(v, pk_ancla=1000)
    assert llamadas == [("2026-10-06", "2026-10-12 23:59:59", 999)]
    assert len(df) == 1 and ("close",) in con.log


@pytest.mark.unit
def test_fuente_bd_sin_conexion_o_con_fallo_es_error():
    v = Ventana(date(2026, 10, 6), date(2026, 10, 12), "ordinaria")
    with pytest.raises(ErrorExtraccion, match="conectar"):
        FuenteBD(conectar=lambda bd: None, consultar=lambda *a: None).extraer(v, 0)
    with pytest.raises(ErrorExtraccion, match="fallo"):
        FuenteBD(conectar=lambda bd: _Conexion(), consultar=lambda *a: None).extraer(v, 0)


@pytest.mark.unit
def test_fuente_local_aplica_los_filtros_de_la_consulta(tmp_path):
    crudo = despachos(
        [
            (10, "2026-10-05", 1),
            (20, "2026-10-06", 1),
            (30, "2026-10-12", 1),
            (40, "2026-10-13", 1),
            (5, "2026-10-08", 1),
        ]
    )
    ruta = tmp_path / "crudo.csv"
    crudo.to_csv(ruta, index=False)
    df = FuenteLocal(ruta).extraer(Ventana(date(2026, 10, 6), date(2026, 10, 12), "x"), pk_ancla=6)
    assert sorted(df["PK_INTERVALO_DESPACHO"]) == [20, 30]


@pytest.mark.unit
def test_normalizar_lleva_horas_de_mysql_a_texto():
    df = pd.DataFrame(
        {
            "FECHA_INICIAL": [date(2026, 10, 1)],
            "HORA": [pd.Timedelta(hours=4, minutes=5)],
            "PK_INTERVALO_DESPACHO": [1],
        }
    )
    n = normalizar(df)
    assert n.loc[0, "FECHA_INICIAL"] == "2026-10-01"
    assert "04:05:00" in n.loc[0, "HORA"]


# ------------------------------------------------------------------ deduplicado


@pytest.mark.unit
def test_deduplicado_determinista_independiente_del_orden():
    a = despachos([(1, "2026-10-01", 5, 11), (1, "2026-10-01", 7, 12), (2, "2026-10-01", 3, 20)])
    b = a.iloc[::-1].reset_index(drop=True)
    da, info = deduplicar(a)
    db, _ = deduplicar(b)
    pd.testing.assert_frame_equal(da, db)
    assert da.set_index("PK_INTERVALO_DESPACHO").loc[1, "PK_INFORMACION_REGISTRADORA"] == 12
    assert info["duplicados"] == [{"pk": 1, "registros": [11, 12], "conservado": 12}]


# ------------------------------------------------------------------ diferencias y reemplazo


@pytest.mark.unit
def test_diferencias_por_dia():
    v = Ventana(date(2026, 10, 1), date(2026, 10, 3), "x")
    previo = despachos(
        [(1, "2026-10-01", 5), (2, "2026-10-01", 5), (3, "2026-10-02", 5), (9, "2026-09-30", 5)]
    )
    nuevo = despachos(
        [(1, "2026-10-01", 6), (3, "2026-10-02", 5), (4, "2026-10-02", 1), (5, "2026-10-03", 1)]
    )
    d = diferencias(previo, nuevo, v)
    assert d["por_dia"]["2026-10-01"] == {
        "despachos": 1,
        "nuevos": 0,
        "cambiados": 1,
        "retirados": 1,
        "campos_cambiados": {"PASAJEROS": 1},
        "sin_previo": False,
    }
    assert (
        d["por_dia"]["2026-10-02"]["nuevos"] == 1 and d["por_dia"]["2026-10-02"]["cambiados"] == 0
    )
    assert d["por_dia"]["2026-10-03"]["sin_previo"]
    assert d["cambios_dia_mas_antiguo"] is True
    assert d["totales"] == {"despachos": 4, "nuevos": 2, "cambiados": 1, "retirados": 1}


@pytest.mark.unit
def test_diferencias_sin_previo_no_alertan():
    v = Ventana(date(2026, 10, 1), date(2026, 10, 2), "x")
    d = diferencias(pd.DataFrame(), despachos([(1, "2026-10-01", 1)]), v)
    assert not d["cambios_dia_mas_antiguo"] and d["totales"]["nuevos"] == 1


@pytest.mark.unit
def test_diferencias_ignoran_tipos_equivalentes():
    v = Ventana(date(2026, 10, 1), date(2026, 10, 1), "x")
    previo = despachos([(1, "2026-10-01", 5)]).astype({"PASAJEROS": float})
    d = diferencias(previo, despachos([(1, "2026-10-01", 5)]), v)
    assert d["totales"]["cambiados"] == 0


@pytest.mark.unit
def test_reemplazo_por_ventana_recoge_altas_cambios_y_anulaciones():
    v = Ventana(date(2026, 10, 2), date(2026, 10, 3), "x")
    base = despachos([(1, "2026-10-01", 1), (2, "2026-10-02", 1), (3, "2026-10-03", 1)])
    nuevo = despachos([(2, "2026-10-02", 9), (4, "2026-10-03", 1)])
    r = reemplazar_ventana(base, nuevo, v)
    assert list(r["PK_INTERVALO_DESPACHO"]) == [1, 2, 4]
    assert r.set_index("PK_INTERVALO_DESPACHO").loc[2, "PASAJEROS"] == 9


@pytest.mark.unit
def test_reemplazo_detecta_pk_fuera_de_ventana_repetido():
    v = Ventana(date(2026, 10, 2), date(2026, 10, 2), "x")
    base = despachos([(1, "2026-10-01", 1)])
    with pytest.raises(ErrorExtraccion):
        reemplazar_ventana(base, despachos([(1, "2026-10-02", 1)]), v)


# ------------------------------------------------------------------ almacen


@pytest.mark.unit
def test_instantanea_no_se_sobrescribe(tmp_path):
    df = despachos([(1, "2026-10-01", 1)])
    guardar_instantanea(tmp_path, "20261013_003000", df)
    with pytest.raises(FileExistsError):
        guardar_instantanea(tmp_path, "20261013_003000", df)


@pytest.mark.unit
def test_almacen_versionado_y_puntero(tmp_path):
    assert leer_almacen(tmp_path).cubierto_hasta is None
    crudo = despachos([(1, "2026-10-01", 1)])
    apto = pd.DataFrame({"PK_INTERVALO_DESPACHO": [1]})
    guardar_almacen(tmp_path, "a", crudo, apto, date(2026, 10, 1), mover_puntero=False)
    assert leer_almacen(tmp_path).id_ejecucion is None
    guardar_almacen(tmp_path, "b", crudo, apto, date(2026, 10, 1), mover_puntero=True)
    alm = leer_almacen(tmp_path)
    assert alm.id_ejecucion == "b" and alm.cubierto_hasta == date(2026, 10, 1)
    assert len(alm.crudo) == 1
    with pytest.raises(FileExistsError):
        guardar_almacen(tmp_path, "b", crudo, apto, date(2026, 10, 1), mover_puntero=True)
