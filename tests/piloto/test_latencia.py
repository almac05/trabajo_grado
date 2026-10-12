"""Script de latencia de los registros de registradora (con una conexion simulada)."""

import importlib.util
from datetime import date, datetime

import pandas as pd
import pytest

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.fechas import ZONA

_spec = importlib.util.spec_from_file_location(
    "latencia_registros", PROJECT_ROOT / "scripts" / "piloto" / "latencia_registros.py"
)
lat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lat)

COLUMNAS = [
    ("PK_INFORMACION_REGISTRADORA", "int(11)"),
    ("FECHA_SALIDA_BASE_SALIDA", "date"),
    ("HORA_INGRESO", "time"),
    ("FECHA_MODIFICACION", "datetime"),
    ("FECHA_CREACION", "datetime"),
]


@pytest.mark.unit
def test_detectar_columna():
    assert lat.detectar_columna(COLUMNAS, None) == "FECHA_CREACION"
    assert lat.detectar_columna(COLUMNAS, "fecha_modificacion") == "FECHA_MODIFICACION"
    with pytest.raises(lat.ErrorLatencia, match="no fecha y hora"):
        lat.detectar_columna(COLUMNAS, "HORA_INGRESO")
    with pytest.raises(lat.ErrorLatencia, match="no tiene"):
        lat.detectar_columna(COLUMNAS, "NO_EXISTE")
    with pytest.raises(lat.ErrorLatencia, match="FECHA_MODIFICACION"):
        lat.detectar_columna([c for c in COLUMNAS if c[0] != "FECHA_CREACION"], None)


@pytest.mark.unit
def test_consulta_solo_lectura_y_columna_validada():
    sql = lat.consulta("FECHA_CREACION")
    assert sql.startswith("SELECT") and "r.`FECHA_CREACION`" in sql and sql.count("%s") == 4
    # FK_RUTA esta en tbl_informacion_registradora (r), no en tbl_intervalo_despacho (d).
    assert "r.FK_RUTA AS ruta" in sql and "r.FK_RUTA IN (1, 3)" in sql and "d.FK_RUTA" not in sql
    for palabra in ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER"):
        assert palabra not in sql
    with pytest.raises(lat.ErrorLatencia):
        lat.consulta("X`; DROP TABLE t; --")


@pytest.mark.unit
def test_resumir_umbrales_respecto_a_la_jornada():
    registros = pd.DataFrame(
        {
            "pk": [1, 2, 3, 4, 5, 6],
            "jornada": [date(2026, 10, 1)] * 6,
            "ruta": [1] * 6,
            "creado": [
                datetime(2026, 10, 1, 9, 0),  # a tiempo
                datetime(2026, 10, 1, 21, 30),  # > 21:00
                datetime(2026, 10, 1, 23, 50),  # > 21:00 y > 23:42
                datetime(2026, 10, 2, 0, 45),  # tambien > 00:30 del dia siguiente
                datetime(2026, 10, 2, 5, 0),  # tambien > 04:00 del dia siguiente
                None,
            ],
        }
    )
    por_dia, total = lat.resumir(registros)
    assert total["registros"] == 6 and total["despachos"] == 6
    assert total["despues_21_00_n"] == 4
    assert total["despues_23_42_n"] == 3
    assert total["despues_00_30_dia_siguiente_n"] == 2
    assert total["despues_04_00_dia_siguiente_n"] == 1
    assert total["sin_hora_creacion_n"] == 1
    assert por_dia.loc[0, "despues_21_00_fraccion"] == pytest.approx(4 / 6)


class Cursor:
    def __init__(self, log, zona="-05:00"):
        self.log, self.ultimo, self.zona = log, None, zona

    def execute(self, sql, params=None):
        self.log.append((sql, params))
        self.ultimo = sql

    def fetchall(self):
        if self.ultimo == "SELECT @@session.time_zone":
            return [(self.zona.encode(),)]
        if self.ultimo.startswith("SHOW COLUMNS"):
            return [(n.encode(), t.encode()) for n, t in COLUMNAS]  # bytes, como mysql-connector
        return [
            (10, date(2026, 10, 1), 1, datetime(2026, 10, 1, 23, 50)),
            (11, date(2026, 10, 2), 3, datetime(2026, 10, 2, 8, 0)),
        ]

    def close(self):
        pass


class Conexion:
    def __init__(self, zona="-05:00"):
        self.log, self.cerrada, self.zona = [], False, zona

    def cursor(self):
        return Cursor(self.log, self.zona)

    def close(self):
        self.cerrada = True


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hora", "conecta"), [((3, 59), True), ((4, 0), False), ((20, 59), False), ((21, 0), True)]
)
def test_proteccion_de_horario(tmp_path, hora, conecta):
    con = Conexion()
    ahora = datetime(2026, 10, 13, *hora, tzinfo=ZONA)
    salida = (
        tmp_path.relative_to(PROJECT_ROOT) if tmp_path.is_relative_to(PROJECT_ROOT) else tmp_path
    )
    codigo = lat.main(["--directorio-salidas", str(salida)], conectar=lambda bd: con, ahora=ahora)
    assert (codigo == 0) is conecta and bool(con.log) is conecta


@pytest.mark.unit
def test_salidas_en_solo_lectura_y_sin_sobrescribir(tmp_path):
    con = Conexion()
    ahora = datetime(2026, 10, 13, 22, 0, tzinfo=ZONA)
    salida = tmp_path / "diag"
    assert (
        lat.main(["--directorio-salidas", str(salida)], conectar=lambda bd: con, ahora=ahora) == 0
    )
    assert con.log[0] == ("SET SESSION TRANSACTION READ ONLY", None) and con.cerrada
    assert con.log[1] == ("SET time_zone = '-05:00'", None)
    _sql, params = con.log[-1]
    assert params == (date(2026, 9, 13), date(2026, 10, 12), date(2026, 9, 13), date(2026, 10, 12))
    csv = salida / "latencia_registros_20261013_220000.csv"
    md = salida / "latencia_registros_20261013_220000.md"
    informe = md.read_text(encoding="utf-8")
    assert csv.exists() and "FECHA_CREACION" in informe
    assert "Zona horaria de la sesion MySQL: `-05:00`" in informe
    assert len(pd.read_csv(csv)) == 2
    with pytest.raises(FileExistsError):
        lat.main(["--directorio-salidas", str(salida)], conectar=lambda bd: Conexion(), ahora=ahora)


@pytest.mark.unit
def test_sesion_fuera_de_colombia_no_consulta(tmp_path, capsys):
    con = Conexion(zona="SYSTEM")
    ahora = datetime(2026, 10, 13, 22, 0, tzinfo=ZONA)
    codigo = lat.main(
        ["--directorio-salidas", str(tmp_path / "diag")], conectar=lambda bd: con, ahora=ahora
    )
    assert codigo == 1 and "time_zone SYSTEM" in capsys.readouterr().err
    assert not any(sql.startswith("SELECT d.") for sql, _ in con.log) and con.cerrada
