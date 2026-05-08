"""Pruebas unitarias para proyecto_grado.etl.utils."""

import pandas as pd

from proyecto_grado.etl.utils import display


def test_display_es_invocable_con_string(capsys):
    """display no lanza al recibir un string."""
    display("texto de prueba")


def test_display_es_invocable_con_dataframe(capsys):
    """display no lanza al recibir un DataFrame."""
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    display(df)


def test_display_es_invocable_con_tipos_basicos(capsys):
    """display no lanza al recibir enteros ni dicts."""
    display(42)
    display({"clave": "valor"})
