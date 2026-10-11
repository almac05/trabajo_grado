"""Archivos de despliegue en EC2: unidades de systemd, plantillas y scripts."""

import re
import shutil
import subprocess

import pytest

from proyecto_grado.modeling.config import PROJECT_ROOT

DEPLOY = PROJECT_ROOT / "deploy" / "ec2"
SCRIPTS = PROJECT_ROOT / "scripts" / "piloto"
UNIDADES = [
    "tunel-ionos.service",
    "despacho-nocturno.service",
    "despacho-nocturno.timer",
    "despacho-alerta@.service",
    "despacho-verificacion.service",
    "despacho-verificacion.timer",
]


def _bash_utilizable() -> str | None:
    """Ruta de un bash que funciona (en Windows, el de WSL sin distribucion no sirve)."""
    candidatos = [shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"]
    for bash in filter(None, candidatos):
        try:
            r = subprocess.run([bash, "-c", "echo ok"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0 and r.stdout.strip() == "ok":
            return bash
    return None


BASH = _bash_utilizable()
requiere_bash = pytest.mark.skipif(BASH is None, reason="Requiere un bash utilizable.")


def unidad(nombre: str) -> dict[str, dict[str, list[str]]]:
    """Secciones -> clave -> valores (las claves repetidas se acumulan)."""
    texto = (DEPLOY / nombre).read_text(encoding="utf-8").replace("\\\n", " ")
    secciones: dict[str, dict[str, list[str]]] = {}
    actual = None
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("["):
            actual = secciones.setdefault(linea.strip("[]"), {})
            continue
        clave, _, valor = linea.partition("=")
        actual.setdefault(clave, []).append(" ".join(valor.split()))
    return secciones


@pytest.mark.unit
def test_existen_todas_las_unidades_y_plantillas():
    for nombre in [*UNIDADES, "env.ejemplo", "tunel.env.ejemplo", "instalar.sh", "README.md"]:
        assert (DEPLOY / nombre).is_file(), nombre
    assert (SCRIPTS / "esperar_puerto.sh").is_file() and (SCRIPTS / "alerta.sh").is_file()


@pytest.mark.unit
def test_tunel_no_se_puede_habilitar_y_se_detiene_solo():
    u = unidad("tunel-ionos.service")
    assert "Install" not in u
    assert u["Unit"]["StopWhenUnneeded"] == ["yes"]
    s = u["Service"]
    assert (
        s["User"] == ["despacho"] and s["Restart"] == ["on-failure"] and s["RestartSec"] == ["30"]
    )
    cmd = s["ExecStart"][0]
    for opcion in (
        "IdentitiesOnly=yes",
        "BatchMode=yes",
        "ExitOnForwardFailure=yes",
        "ServerAliveInterval=30",
        "ServerAliveCountMax=3",
        "StrictHostKeyChecking=yes",
    ):
        assert f"-o {opcion}" in cmd, opcion
    assert "-N -L 3306:127.0.0.1:3306 ${PILOTO_TUNEL_DESTINO}" in cmd
    assert s["EnvironmentFile"] == ["/opt/despacho/tunel.env"]


@pytest.mark.unit
def test_servicio_nocturno():
    u = unidad("despacho-nocturno.service")
    assert u["Unit"]["Requires"] == ["tunel-ionos.service"]
    assert "tunel-ionos.service" in u["Unit"]["After"][0]
    assert u["Unit"]["OnFailure"] == ["despacho-alerta@%n.service"]
    s = u["Service"]
    assert s["Type"] == ["oneshot"] and s["User"] == ["despacho"]
    assert s["WorkingDirectory"] == ["/opt/despacho/proyecto_grado"]
    assert s["EnvironmentFile"] == ["/opt/despacho/.env"]
    assert set(s["Environment"][0].split()) == {
        "TZ=America/Bogota",
        "PILOTO_ENTORNO=EC2",
        "PYTHONIOENCODING=utf-8",
        "LANG=C.UTF-8",
    }
    assert "esperar_puerto.sh 127.0.0.1 3306 60" in s["ExecStartPre"][0]
    assert s["ExecStart"] == [
        "/opt/despacho/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno "
        "--escribir-bd --subir-s3"
    ]
    assert s["ExecStopPost"] == ["+/bin/systemctl stop tunel-ionos.service"]
    assert s["TimeoutStartSec"] == ["2h"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("timer", "hora"),
    [("despacho-nocturno.timer", "00:30:00"), ("despacho-verificacion.timer", "05:00:00")],
)
def test_temporizadores_en_hora_de_colombia(timer, hora):
    t = unidad(timer)["Timer"]
    assert t["OnCalendar"] == [f"*-*-* {hora} America/Bogota"]
    assert t["Persistent"] == ["true"] and t["RandomizedDelaySec"] == ["0"]
    assert unidad(timer)["Install"]["WantedBy"] == ["timers.target"]


@pytest.mark.unit
def test_alerta_y_verificacion():
    a = unidad("despacho-alerta@.service")["Service"]
    assert a["SupplementaryGroups"] == ["systemd-journal"] and a["User"] == ["despacho"]
    assert a["ExecStart"][0].endswith("scripts/piloto/alerta.sh %i")
    v = unidad("despacho-verificacion.service")
    assert "OnFailure" not in v.get("Unit", {})  # evita alertas dobles
    assert v["Service"]["ExecStart"][0].endswith("python -m proyecto_grado.piloto.verificacion")


@pytest.mark.unit
def test_plantillas_de_entorno_sin_valores_secretos():
    variables = {}
    for linea in (DEPLOY / "env.ejemplo").read_text(encoding="utf-8").splitlines():
        if linea and not linea.startswith("#"):
            k, _, v = linea.partition("=")
            variables[k] = v
    assert variables == {
        "REGISTEL_DB_HOST": "127.0.0.1",
        "REGISTEL_DB_PORT": "3306",
        "REGISTEL_DB_USER": "",
        "REGISTEL_DB_PASSWORD": "",
        "PILOTO_S3_BUCKET": "registel-montebello-despacho",
        "PILOTO_S3_PREFIJO": "piloto",
        "PILOTO_SNS_TOPIC": "",
        "PILOTO_AVISAR_OK": "1",
    }
    tunel = (DEPLOY / "tunel.env.ejemplo").read_text(encoding="utf-8")
    assert re.search(r"^PILOTO_TUNEL_DESTINO=$", tunel, re.MULTILINE)


@pytest.mark.unit
def test_sin_ip_ni_usuario_del_vps_en_archivos_versionados():
    archivos = [p for p in [*DEPLOY.iterdir(), *SCRIPTS.iterdir()] if p.is_file()]
    for ruta in (p for p in archivos if p.suffix != ".pyc"):
        texto = ruta.read_text(encoding="utf-8")
        ips = set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", texto)) - {"127.0.0.1"}
        assert not ips, (ruta.name, ips)
        assert not re.search(r"[\w.-]+@\d{1,3}(?:\.\d{1,3}){3}", texto), ruta.name
        assert not re.search(r"(?i)aws_(secret_)?access_key", texto), ruta.name


@pytest.mark.unit
def test_instalar_rechaza_ramas_y_no_activa_timers_por_defecto():
    texto = (DEPLOY / "instalar.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in texto
    assert "refs/remotes/origin/$REF" in texto and "checkout --quiet --detach" in texto
    assert "'$UV' sync --frozen\"" in texto and "--extra" not in texto
    assert "--activar-timers) ACTIVAR=1" in texto and "ACTIVAR=0" in texto
    assert "systemctl enable --now" in texto
    assert "disable tunel-ionos.service" in texto


@pytest.mark.unit
@requiere_bash
@pytest.mark.parametrize(
    "script",
    [DEPLOY / "instalar.sh", SCRIPTS / "esperar_puerto.sh", SCRIPTS / "alerta.sh"],
    ids=lambda p: p.name,
)
def test_scripts_con_sintaxis_valida(script):
    assert "set -euo pipefail" in script.read_text(encoding="utf-8")
    r = subprocess.run([BASH, "-n", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.unit
@requiere_bash
def test_esperar_puerto_agota_el_tiempo():
    r = subprocess.run(
        [BASH, str(SCRIPTS / "esperar_puerto.sh"), "127.0.0.1", "9", "1"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 1 and "no respondio" in r.stderr
