"""Pruebas unitarias para proyecto_grado.etl.extract."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

import proyecto_grado.etl.extract as _extract

# ---------------------------------------------------------------------------
# obtener_despachos
# ---------------------------------------------------------------------------


def test_obtener_despachos_sin_conexion_retorna_none():
    """Retorna None y no lanza cuando la conexión es None."""
    result = _extract.obtener_despachos(None, "2024-01-01", "2024-12-31", 0)

    assert result is None


def test_obtener_despachos_con_datos_retorna_dataframe():
    """Con una conexión mock que devuelve filas, retorna un DataFrame."""
    rows = [{"PK_INTERVALO_DESPACHO": 1, "FK_RUTA": 1, "PASAJEROS": 20}]
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows

    mock_con = MagicMock()
    mock_con.cursor.return_value = mock_cursor

    result = _extract.obtener_despachos(mock_con, "2024-01-01", "2024-12-31", 0)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["PK_INTERVALO_DESPACHO"] == 1


def test_obtener_despachos_sin_filas_retorna_dataframe_vacio():
    """Con cursor que devuelve lista vacía, retorna DataFrame vacío."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_con = MagicMock()
    mock_con.cursor.return_value = mock_cursor

    result = _extract.obtener_despachos(mock_con, "2024-01-01", "2024-12-31", 0)

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_obtener_despachos_captura_error_mysql():
    """Si el cursor lanza mysql.connector.Error, retorna None."""
    from mysql.connector import Error

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Error("Query failed")

    mock_con = MagicMock()
    mock_con.cursor.return_value = mock_cursor

    result = _extract.obtener_despachos(mock_con, "2024-01-01", "2024-12-31", 0)

    assert result is None


# ---------------------------------------------------------------------------
# actualizar_despachos_desde_bd
# ---------------------------------------------------------------------------


def test_actualizar_despachos_usa_max_pk_del_csv_existente(monkeypatch):
    """max_pk se extrae del CSV existente para la extracción incremental."""
    existing = pd.DataFrame({"PK_INTERVALO_DESPACHO": [10, 20, 30], "PLACA": ["A", "B", "C"]})
    captured_pks = []

    def mock_obtener(con, fi, ff, max_pk):
        captured_pks.append(max_pk)
        return pd.DataFrame()

    monkeypatch.setattr(_extract, "cargar_csv_si_existe", lambda _: existing)
    monkeypatch.setattr(_extract, "conectar_bd", lambda db: MagicMock())
    monkeypatch.setattr(_extract, "obtener_despachos", mock_obtener)
    monkeypatch.setattr(_extract, "cerrar_conexion", lambda con: None)
    monkeypatch.setattr(_extract, "guardar_csv", lambda df, p: None)

    _extract.actualizar_despachos_desde_bd()

    assert captured_pks[0] == 30


def test_actualizar_despachos_usa_max_pk_cero_sin_csv(monkeypatch):
    """Cuando no hay CSV existente, max_pk empieza en 0."""
    captured_pks = []

    def mock_obtener(con, fi, ff, max_pk):
        captured_pks.append(max_pk)
        return pd.DataFrame()

    monkeypatch.setattr(_extract, "cargar_csv_si_existe", lambda _: None)
    monkeypatch.setattr(_extract, "conectar_bd", lambda db: MagicMock())
    monkeypatch.setattr(_extract, "obtener_despachos", mock_obtener)
    monkeypatch.setattr(_extract, "cerrar_conexion", lambda con: None)
    monkeypatch.setattr(_extract, "guardar_csv", lambda df, p: None)

    _extract.actualizar_despachos_desde_bd()

    assert captured_pks[0] == 0


def test_actualizar_despachos_elimina_duplicados_por_pk(monkeypatch):
    """Los duplicados de PK_INTERVALO_DESPACHO se eliminan al hacer concat."""
    existing = pd.DataFrame({"PK_INTERVALO_DESPACHO": [1, 2], "PLACA": ["A", "B"]})
    nuevos = pd.DataFrame({"PK_INTERVALO_DESPACHO": [2, 3], "PLACA": ["B_nuevo", "C"]})

    monkeypatch.setattr(_extract, "cargar_csv_si_existe", lambda _: existing)
    monkeypatch.setattr(_extract, "conectar_bd", lambda db: MagicMock())
    monkeypatch.setattr(_extract, "obtener_despachos", lambda *_: nuevos)
    monkeypatch.setattr(_extract, "cerrar_conexion", lambda con: None)
    monkeypatch.setattr(_extract, "guardar_csv", lambda df, p: None)

    result = _extract.actualizar_despachos_desde_bd()

    assert set(result["PK_INTERVALO_DESPACHO"]) == {1, 2, 3}
    assert len(result) == 3


def test_actualizar_despachos_lanza_error_si_bd_falla(monkeypatch):
    """RuntimeError si obtener_despachos devuelve None (BD inaccesible)."""
    monkeypatch.setattr(_extract, "cargar_csv_si_existe", lambda _: None)
    monkeypatch.setattr(_extract, "conectar_bd", lambda db: MagicMock())
    monkeypatch.setattr(_extract, "obtener_despachos", lambda *_: None)
    monkeypatch.setattr(_extract, "cerrar_conexion", lambda con: None)

    with pytest.raises(RuntimeError):
        _extract.actualizar_despachos_desde_bd()
