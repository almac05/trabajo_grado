"""Pruebas unitarias para proyecto_grado.etl.db."""

from unittest.mock import MagicMock, patch

import pandas as pd

import proyecto_grado.etl.db as _db

# ---------------------------------------------------------------------------
# conectar_bd
# ---------------------------------------------------------------------------


def test_conectar_bd_retorna_conexion_exitosa(monkeypatch):
    """Cuando mysql conecta correctamente, retorna el objeto de conexión."""
    mock_con = MagicMock()
    mock_con.is_connected.return_value = True

    monkeypatch.setattr(_db, "inicializar_entorno", lambda **kwargs: None)

    with patch("mysql.connector.connect", return_value=mock_con):
        con = _db.conectar_bd("test_db")

    assert con is mock_con


def test_conectar_bd_retorna_none_en_error(monkeypatch):
    """Cuando mysql lanza Error, retorna None en lugar de propagar la excepción."""
    from mysql.connector import Error

    monkeypatch.setattr(_db, "inicializar_entorno", lambda **kwargs: None)

    with patch("mysql.connector.connect", side_effect=Error("Connection refused")):
        con = _db.conectar_bd("test_db")

    assert con is None


# ---------------------------------------------------------------------------
# cerrar_conexion
# ---------------------------------------------------------------------------


def test_cerrar_conexion_cierra_conexion_activa():
    """cerrar_conexion llama a .close() si la conexión está activa."""
    mock_con = MagicMock()
    mock_con.is_connected.return_value = True

    _db.cerrar_conexion(mock_con)

    mock_con.close.assert_called_once()


def test_cerrar_conexion_tolera_none():
    """cerrar_conexion no lanza si se le pasa None."""
    _db.cerrar_conexion(None)


def test_cerrar_conexion_tolera_conexion_inactiva():
    """cerrar_conexion no llama a .close() si la conexión ya está cerrada."""
    mock_con = MagicMock()
    mock_con.is_connected.return_value = False

    _db.cerrar_conexion(mock_con)

    mock_con.close.assert_not_called()


# ---------------------------------------------------------------------------
# asegurar_conexion
# ---------------------------------------------------------------------------


def test_asegurar_conexion_reconecta_si_recibe_none(monkeypatch):
    """asegurar_conexion crea nueva conexión cuando se le pasa None."""
    mock_con = MagicMock()
    mock_con.is_connected.return_value = True

    monkeypatch.setattr(_db, "conectar_bd", lambda db: mock_con)

    result = _db.asegurar_conexion(None, "test_db")

    assert result is mock_con


def test_asegurar_conexion_retorna_conexion_activa():
    """asegurar_conexion devuelve la misma conexión si sigue activa."""
    mock_con = MagicMock()
    mock_con.is_connected.return_value = True
    mock_con.ping.return_value = None

    result = _db.asegurar_conexion(mock_con, "test_db")

    assert result is mock_con


# ---------------------------------------------------------------------------
# cargar_csv_si_existe
# ---------------------------------------------------------------------------


def test_cargar_csv_si_existe_retorna_none_si_no_hay_archivo(tmp_path):
    """Retorna None cuando el archivo no existe."""
    result = _db.cargar_csv_si_existe(str(tmp_path / "inexistente.csv"))

    assert result is None


def test_cargar_csv_si_existe_carga_dataframe(tmp_path):
    """Carga el CSV como DataFrame cuando el archivo existe."""
    csv_path = tmp_path / "test.csv"
    pd.DataFrame({"A": [1, 2], "B": [3, 4]}).to_csv(csv_path, index=False)

    result = _db.cargar_csv_si_existe(str(csv_path))

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result.columns) == ["A", "B"]


# ---------------------------------------------------------------------------
# guardar_csv
# ---------------------------------------------------------------------------


def test_guardar_csv_crea_directorio_y_guarda(tmp_path):
    """guardar_csv crea los directorios necesarios y escribe el archivo."""
    dest = tmp_path / "subdir" / "output.csv"
    df = pd.DataFrame({"X": [10, 20]})

    _db.guardar_csv(df, str(dest))

    assert dest.exists()
    loaded = pd.read_csv(dest)
    assert loaded["X"].tolist() == [10, 20]
