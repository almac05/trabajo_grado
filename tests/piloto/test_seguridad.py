"""Reglas que no se negocian: sin escrituras en las bases operacionales y sin .env versionado."""

import ast
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT

BASES_PROTEGIDAS = re.compile(r"bd_montebello_rdw(_gps)?\b", re.IGNORECASE)
PALABRAS_ESCRITURA = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|TRUNCATE)\b", re.IGNORECASE
)
SENTENCIA_ESCRITURA = re.compile(
    r"\b(INSERT\s+(IGNORE\s+)?INTO|UPDATE\s+[`\w.{}]+\s+SET|DELETE\s+FROM|REPLACE\s+INTO|"
    r"CREATE\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|TRIGGER|PROCEDURE)|"
    r"DROP\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|TRIGGER|PROCEDURE)|ALTER\s+TABLE|TRUNCATE\s+)",
    re.IGNORECASE,
)
ESQUEMA_PILOTO = "bd_montebello_recomendaciones"
UNICO_MODULO_QUE_ESCRIBE = "salida_bd.py"

PILOTO = PROJECT_ROOT / "src" / "proyecto_grado" / "piloto"
# Codigo del ETL que la piloto ejecuta con conexiones a las bases operacionales.
ETL_REUTILIZADO = [
    PROJECT_ROOT / "src" / "proyecto_grado" / "etl" / n
    for n in (
        "db.py",
        "extract.py",
        "gps.py",
        "trip_end.py",
        "transforms.py",
        "qc.py",
        "model_ready.py",
    )
]


def _docstrings(arbol: ast.AST) -> set[int]:
    ids = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            cuerpo = nodo.body
            if (
                cuerpo
                and isinstance(cuerpo[0], ast.Expr)
                and isinstance(cuerpo[0].value, ast.Constant)
            ):
                ids.add(id(cuerpo[0].value))
    return ids


def cadenas(codigo: str) -> list[tuple[int, str]]:
    """Literales de texto del codigo (sin docstrings), con su linea.

    Los literales adyacentes ya vienen unidos por el analizador; en las f-strings
    se toma el texto de sus partes constantes.
    """
    arbol = ast.parse(codigo)
    excluir = _docstrings(arbol)
    salida = []
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Constant)
            and isinstance(nodo.value, str)
            and id(nodo) not in excluir
        ):
            salida.append((nodo.lineno, nodo.value))
        elif isinstance(nodo, ast.JoinedStr):
            partes = [v.value for v in nodo.values if isinstance(v, ast.Constant)]
            salida.append((nodo.lineno, "{}".join(partes)))
    return salida


def violaciones(codigo: str, nombre: str, puede_escribir: bool) -> list[str]:
    errores = []
    for linea, texto in cadenas(codigo):
        if BASES_PROTEGIDAS.search(texto) and PALABRAS_ESCRITURA.search(texto):
            errores.append(
                f"{nombre}:{linea}: escritura dirigida a una base operacional: {texto!r}"
            )
        if SENTENCIA_ESCRITURA.search(texto):
            if not puede_escribir:
                errores.append(
                    f"{nombre}:{linea}: sentencia de escritura fuera de salida_bd: {texto!r}"
                )
            elif ESQUEMA_PILOTO + "." not in texto:
                errores.append(
                    f"{nombre}:{linea}: escritura sin el esquema {ESQUEMA_PILOTO}: {texto!r}"
                )
    return errores


def archivos_piloto() -> list[Path]:
    return sorted(PILOTO.rglob("*.py")) + sorted(
        (PROJECT_ROOT / "scripts" / "piloto").rglob("*.py")
    )


@pytest.mark.unit
def test_el_detector_encuentra_escrituras_prohibidas():
    malo = (
        'Q = "DELETE FROM bd_montebello_rdw.tbl_intervalo_despacho WHERE 1"\n'
        'def f(t):\n    return f"update {t} set x = 1 -- bd_montebello_rdw_gps"\n'
        'R = ("INSERT INTO corridas "\n     "VALUES (%s)")\n'
    )
    errores = violaciones(malo, "malo.py", puede_escribir=False)
    # Dos escrituras a bases protegidas y tres sentencias fuera de salida_bd.
    assert len(errores) == 5
    assert any("DELETE FROM bd_montebello_rdw" in e for e in errores)
    assert any("update {} set" in e for e in errores)
    assert violaciones('S = "INSERT INTO corridas VALUES (1)"', "salida_bd.py", True)
    assert not violaciones('"""Nunca INSERT en bd_montebello_rdw."""\nx = 1\n', "doc.py", False)
    assert not violaciones('Q = "SELECT * FROM bd_montebello_rdw.t"', "lectura.py", False)


@pytest.mark.unit
def test_la_piloto_no_escribe_en_las_bases_operacionales():
    errores = []
    for ruta in archivos_piloto():
        puede = ruta.name == UNICO_MODULO_QUE_ESCRIBE and ruta.parent == PILOTO
        errores += violaciones(ruta.read_text(encoding="utf-8"), ruta.name, puede)
    assert not errores, "\n".join(errores)


@pytest.mark.unit
def test_salida_bd_escribe_solo_en_el_esquema_de_la_piloto():
    codigo = (PILOTO / UNICO_MODULO_QUE_ESCRIBE).read_text(encoding="utf-8")
    sentencias = [t for _, t in cadenas(codigo) if SENTENCIA_ESCRITURA.search(t)]
    assert len(sentencias) == 4
    assert all(f"{ESQUEMA_PILOTO}." in s for s in sentencias)


@pytest.mark.unit
def test_el_etl_reutilizado_solo_lee():
    errores = []
    for ruta in ETL_REUTILIZADO:
        errores += violaciones(ruta.read_text(encoding="utf-8"), ruta.name, puede_escribir=False)
    assert not errores, "\n".join(errores)


@pytest.mark.unit
def test_sin_credenciales_en_la_configuracion_versionada():
    for ruta in (PROJECT_ROOT / "configs" / "piloto").glob("*"):
        texto = ruta.read_text(encoding="utf-8")
        assert not re.search(r"(?i)(password|secret|token|aws_access_key)\s*[:=]\s*\S", texto), ruta


# ------------------------------------------------------------------ .env


def _git(*args) -> str:
    return subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.unit
def test_ningun_env_versionado():
    versionados = [
        r
        for r in _git("ls-files").splitlines()
        if re.search(r"(^|/)\.env(\.|$)", r) and not r.endswith(".env.example")
    ]
    assert not versionados, versionados


@pytest.mark.unit
def test_env_ignorado_por_git():
    for nombre in (".env", ".env.local", "configs/piloto/.env"):
        assert _git("check-ignore", "--no-index", nombre).strip() == nombre


@pytest.mark.unit
def test_hook_de_pre_commit_bloquea_env():
    cfg = yaml.safe_load((PROJECT_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [h for r in cfg["repos"] if r["repo"] == "local" for h in r["hooks"]]
    hook = next(h for h in hooks if h["id"] == "bloquear-env")
    assert hook["language"] == "fail"
    patron, excluir = re.compile(hook["files"]), re.compile(hook["exclude"])
    for ruta in (".env", "configs/.env", ".env.produccion"):
        assert patron.search(ruta) and not excluir.search(ruta), ruta
    assert excluir.search(".env.example")
    assert not patron.search("docs/entorno.md")
