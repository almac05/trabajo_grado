"""Sorteo de grupos: el script reproduce la asignacion versionada y esta balanceada."""

import importlib.util
from collections import Counter
from datetime import date

import pytest

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.config import cargar_asignacion_grupos, cargar_configuracion

_spec = importlib.util.spec_from_file_location(
    "sorteo_grupos", PROJECT_ROOT / "scripts" / "piloto" / "sorteo_grupos.py"
)
sorteo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sorteo)

ESPERADO = {
    date(2026, 10, 19): "CONTROL",
    date(2026, 10, 20): "CONTROL",
    date(2026, 10, 21): "CONTROL",
    date(2026, 10, 22): "MODULO",
    date(2026, 10, 23): "CONTROL",
    date(2026, 10, 24): "MODULO",
    date(2026, 10, 25): "CONTROL",
    date(2026, 10, 26): "MODULO",
    date(2026, 10, 27): "MODULO",
    date(2026, 10, 28): "MODULO",
    date(2026, 10, 29): "CONTROL",
    date(2026, 10, 30): "MODULO",
}


@pytest.mark.unit
def test_script_reproduce_la_asignacion_versionada():
    assert sorteo.sortear() == ESPERADO
    versionada = cargar_asignacion_grupos(cargar_configuracion().ruta_asignacion_grupos)
    assert {d: str(g) for d, g in versionada.items()} == sorteo.sortear()


@pytest.mark.unit
def test_script_imprime_el_yaml_y_el_conteo(capsys):
    sorteo.main()
    salida = capsys.readouterr().out.splitlines()
    assert salida[:-1] == [f"{d.isoformat()}: {g}" for d, g in ESPERADO.items()]
    assert salida[-1] == "# MODULO: 6, CONTROL: 6"


@pytest.mark.unit
def test_balance_por_bloques():
    a = sorteo.sortear()
    assert Counter(a.values()) == {"MODULO": 6, "CONTROL": 6}
    for wd in range(5):
        assert sorted(g for d, g in a.items() if d.weekday() == wd) == ["CONTROL", "MODULO"]
    assert a[date(2026, 10, 24)] != a[date(2026, 10, 25)]
