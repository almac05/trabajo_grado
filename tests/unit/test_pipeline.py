import contextlib
import importlib
import io
import sys


def test_import_pipeline_no_ejecuta_inicializacion():
    sys.modules.pop("proyecto_grado.etl.pipeline", None)

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        module = importlib.import_module("proyecto_grado.etl.pipeline")

    assert stdout.getvalue() == ""
    assert module._ENV_LOADED is False
    assert callable(module.main)
