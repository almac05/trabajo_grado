"""Orden transaccional y contrato de bd_montebello_recomendaciones."""

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest

from proyecto_grado.piloto.fechas import ZONA
from proyecto_grado.piloto.salida_bd import (
    SQL_ABRIR,
    SQL_CERRAR,
    SQL_ERROR,
    SQL_RECOMENDACION,
    CierreCorrida,
    ErrorSalidaBD,
    EscritorBD,
    filas_recomendaciones,
)


class Cursor:
    def __init__(self, con):
        self.con = con
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.con.log.append(("execute", sql, params))
        if self.con.fallar_en and self.con.fallar_en in sql:
            raise RuntimeError("fallo simulado")
        self.rowcount = self.con.rowcount

    def executemany(self, sql, filas):
        self.con.log.append(("executemany", sql, list(filas)))
        if self.con.fallar_en == "executemany":
            raise RuntimeError("fallo simulado")

    def close(self):
        pass


class Conexion:
    def __init__(self, fallar_en=None, rowcount=1):
        self.log = []
        self.fallar_en = fallar_en
        self.rowcount = rowcount

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.log.append(("commit",))

    def rollback(self):
        self.log.append(("rollback",))

    def close(self):
        self.log.append(("close",))


def ops(con):
    return [(o[0], o[1][:40] if len(o) > 1 else None) for o in con.log]


def rec():
    return pd.DataFrame(
        {
            "route": [1, 1, 3],
            "dia_op": ["2026-10-13"] * 3,
            "hora": ["23:30", "05:00", "04:30"],
            "bloque": ["cierre", "pico_manana", "madrugada"],
            "tipo_dia": "LABORAL",
            "regimen": "ordinario",
            "demanda_predicha": [10.123, 80.0, 5.0],
            "divisor_usado": [20.0, 25.456, np.nan],
            "despachos_recomendados": [1, 3, 0],
            "despachos_regla_normal": [1, 3, 1],
            "en_disponibilidad": [True, True, False],
        }
    )


def cierre(**k):
    base = {
        "fin": datetime(2026, 10, 13, 5, 45, tzinfo=UTC),
        "estado": "OK",
        "advertencias": ["a", "b"],
        "version_dataset": "f" * 64,
        "factores": {1: 0.8699866, 3: 0.91162},
        "filas": filas_recomendaciones(rec(), "20261013_003000", "SOMBRA"),
        "ruta_s3": None,
    }
    base.update(k)
    return CierreCorrida(**base)


@pytest.mark.unit
def test_filas_siguen_el_contrato():
    f = filas_recomendaciones(rec(), "id", "MODULO")
    assert [x[2:5] for x in f] == [
        (1, "05:00:00", "05:30:00"),
        (1, "23:30:00", "00:00:00"),
        (3, "04:30:00", "05:00:00"),
    ]
    pico, _cierre, madrugada = f
    assert pico[1] == date(2026, 10, 13) and pico[-1] == "MODULO"
    assert pico[9] == 25.46 and pico[10] == 3 and pico[11] is None and pico[12] == 10.0
    assert pico[13] == 1
    # Fuera de disponibilidad: meta 0, sugerencia de la regla normal, sin intervalo.
    assert madrugada[9] is None and madrugada[10] == 0 and madrugada[11] == 1
    assert madrugada[12] is None and madrugada[13] == 0
    assert all(len(x) == SQL_RECOMENDACION.count("%s") for x in f)


@pytest.mark.unit
def test_abrir_y_cerrar_en_orden_y_una_sola_transaccion_final():
    con = Conexion()
    e = EscritorBD(conectar=lambda: con)
    inicio = datetime(2026, 10, 13, 0, 30, tzinfo=ZONA)
    e.abrir_corrida("20261013_003000", date(2026, 10, 13), inicio, "LOCAL", "a" * 40)
    e.cerrar_corrida("20261013_003000", cierre())
    # Una conexion por operacion, cerrada al terminar; el cierre en una sola transaccion.
    assert [o[0] for o in con.log] == [
        "execute",
        "commit",
        "close",
        "executemany",
        "execute",
        "commit",
        "close",
    ]
    assert con.log[0][1] == SQL_ABRIR and con.log[0][2][2] == datetime(2026, 10, 13, 0, 30)
    assert "version_dataset" in SQL_ABRIR and SQL_ABRIR.endswith("NULL)")
    assert con.log[3][1] == SQL_RECOMENDACION and len(con.log[3][2]) == 3
    assert con.log[4][1] == SQL_CERRAR
    params = con.log[4][2]
    assert params[0] == datetime(2026, 10, 13, 0, 45)  # 05:45 UTC = 00:45 Colombia
    assert params[1:4] == ("OK", "a; b", "f" * 64)
    assert params[4:7] == (0.86999, 0.91162, 3)
    assert params[-1] == "20261013_003000"


@pytest.mark.unit
@pytest.mark.parametrize(
    "fallar_en",
    ["executemany", "UPDATE bd_montebello_recomendaciones.corridas SET fin = %s, estado = %s"],
)
def test_fallo_al_cerrar_hace_rollback_y_marca_error(fallar_en):
    con = Conexion(fallar_en=fallar_en)
    e = EscritorBD(conectar=lambda: con)
    with pytest.raises(ErrorSalidaBD):
        e.cerrar_corrida("id", cierre())
    tipos = [o[0] for o in con.log]
    i = tipos.index("rollback")
    # Ningun commit antes del rollback: las recomendaciones no quedan a medias.
    assert "commit" not in tipos[:i] and tipos[i + 1] == "close"
    # Luego, en otra conexion, la corrida queda en ERROR.
    assert con.log[-3][1] == SQL_ERROR and tipos[-2:] == ["commit", "close"]


@pytest.mark.unit
def test_corrida_que_no_esta_en_curso_es_error():
    con = Conexion(rowcount=0)
    with pytest.raises(ErrorSalidaBD, match="EN_CURSO"):
        EscritorBD(conectar=lambda: con).cerrar_corrida("id", cierre())
    assert ("rollback",) in con.log


@pytest.mark.unit
def test_mensaje_de_error_sin_credenciales(monkeypatch):
    monkeypatch.setenv("REGISTEL_DB_PASSWORD", "clave-secreta-123")
    con = Conexion()
    EscritorBD(conectar=lambda: con).cerrar_corrida(
        "id", cierre(estado="ERROR", mensaje_error="fallo con clave-secreta-123", filas=[])
    )
    assert [o[0] for o in con.log] == ["execute", "commit", "close"]
    assert "clave-secreta-123" not in str(con.log)


@pytest.mark.unit
def test_solo_escribe_en_el_esquema_de_la_piloto():
    with pytest.raises(ErrorSalidaBD):
        EscritorBD(conectar=lambda: Conexion(), esquema="bd_montebello_rdw")
    for sql in (SQL_ABRIR, SQL_RECOMENDACION, SQL_CERRAR, SQL_ERROR):
        assert "bd_montebello_recomendaciones." in sql and "bd_montebello_rdw" not in sql
