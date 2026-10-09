"""El camino de XGBoost y el orquestador de la piloto se importan sin torch ni prophet."""

import subprocess
import sys

import pytest

# Modulos que deben importarse sin torch ni prophet. El orquestador se agrega
# cuando existe; la prueba falla si deja de poder importarse.
MODULOS = [
    "proyecto_grado.modeling.hparam_search.fits",
    "proyecto_grado.modeling.hparam_search.runner",
    "proyecto_grado.modeling.hparam_search.reevaluacion",
]

_BLOQUEO = """
import importlib
import importlib.abc
import sys

class _Bloqueo(importlib.abc.MetaPathFinder):
    # Simula un entorno sin torch ni prophet instalados.
    def find_spec(self, nombre, path=None, target=None):
        if nombre.split(".")[0] in ("torch", "prophet"):
            raise ModuleNotFoundError(f"No module named {nombre!r}")
        return None

sys.meta_path.insert(0, _Bloqueo())
for modulo in __MODULOS__:
    importlib.import_module(modulo)
cargados = sorted(m for m in sys.modules if m.split(".")[0] in ("torch", "prophet"))
assert not cargados, cargados
print("ok")
"""


def _importar_sin_torch(modulos: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _BLOQUEO.replace("__MODULOS__", repr(modulos))],
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.unit
def test_modulos_se_importan_sin_torch_ni_prophet():
    r = _importar_sin_torch(MODULOS)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().endswith("ok")


@pytest.mark.unit
def test_el_bloqueo_detecta_un_import_de_torch():
    r = _importar_sin_torch(["torch"])
    assert r.returncode != 0
