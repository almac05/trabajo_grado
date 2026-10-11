"""Avisos por SNS: alerta de fallos, vigilante de las 05:00 y aviso de exito."""

import json
from datetime import datetime

import boto3
import pytest
from botocore.stub import ANY, Stubber

from proyecto_grado.piloto import alerta, avisos, verificacion
from proyecto_grado.piloto.fechas import ZONA
from proyecto_grado.piloto.nocturno import Dependencias, avisar_ok

ARN = "arn:aws:sns:us-east-2:123456789012:alertas-tesis"


class SNSFalso:
    def __init__(self, fallar=False):
        self.mensajes = []
        self.fallar = fallar

    def publish(self, TopicArn, Subject, Message):  # noqa: N803 - firma de boto3
        if self.fallar:
            raise RuntimeError("sin permiso sns:Publish")
        self.mensajes.append({"TopicArn": TopicArn, "Subject": Subject, "Message": Message})
        return {"MessageId": "m-1"}


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv("PILOTO_SNS_TOPIC", ARN)
    monkeypatch.setenv("REGISTEL_DB_PASSWORD", "clave-ultra-secreta")


def manifiesto(salidas, ident, modo="nocturno", estado="OK", jornada="2026-10-13"):
    carpeta = salidas / "ejecuciones" / ident
    carpeta.mkdir(parents=True)
    m = {"id_ejecucion": ident, "modo": modo, "estado": estado, "objetivo": {"d_mas_1": jornada}}
    (carpeta / "manifiesto.json").write_text(json.dumps(m), encoding="utf-8")


# ------------------------------------------------------------------ avisos


@pytest.mark.unit
def test_region_del_arn():
    assert avisos.region_de(ARN) == "us-east-2"
    assert avisos.region_de("no-es-un-arn") is None


@pytest.mark.unit
def test_publicar_con_stubber(entorno):
    cliente = boto3.client(
        "sns", region_name="us-east-2", aws_access_key_id="x", aws_secret_access_key="x"
    )
    with Stubber(cliente) as st:
        st.add_response(
            "publish", {"MessageId": "abc"}, {"TopicArn": ARN, "Subject": "Asunto", "Message": ANY}
        )
        assert avisos.publicar("Asunto", "cuerpo", cliente=cliente) == "abc"
        st.assert_no_pending_responses()


@pytest.mark.unit
def test_publicar_oculta_secretos_y_recorta_el_asunto(entorno):
    sns = SNSFalso()
    avisos.publicar("x" * 150 + " clave-ultra-secreta", "fallo clave-ultra-secreta", cliente=sns)
    m = sns.mensajes[0]
    assert len(m["Subject"]) == 100 and "clave-ultra-secreta" not in m["Message"]
    assert "[OCULTO]" in m["Message"]


@pytest.mark.unit
def test_errores_de_publicacion(monkeypatch):
    monkeypatch.delenv("PILOTO_SNS_TOPIC", raising=False)
    with pytest.raises(avisos.ErrorAviso, match="PILOTO_SNS_TOPIC"):
        avisos.publicar("a", "b", cliente=SNSFalso())
    monkeypatch.setenv("PILOTO_SNS_TOPIC", ARN)
    with pytest.raises(avisos.ErrorAviso, match="SNS"):
        avisos.publicar("a", "b", cliente=SNSFalso(fallar=True))


# ------------------------------------------------------------------ alerta de systemd


@pytest.mark.unit
def test_alerta_incluye_unidad_estado_y_journal_sin_secretos(tmp_path, entorno):
    (tmp_path / "ESTADO_ULTIMA_EJECUCION.txt").write_text("Estado: ERROR\n", encoding="utf-8")
    sns = SNSFalso()
    codigo = alerta.main(
        ["--unidad", "despacho-nocturno.service", "--directorio-salidas", str(tmp_path)],
        cliente=sns,
        journal=lambda u: f"{u}: password=clave-ultra-secreta\nlinea 2",
    )
    assert codigo == 0
    m = sns.mensajes[0]
    assert "despacho-nocturno.service" in m["Subject"]
    assert "Estado: ERROR" in m["Message"] and "linea 2" in m["Message"]
    assert "clave-ultra-secreta" not in m["Message"]


@pytest.mark.unit
def test_alerta_sin_poder_publicar_sale_con_1(tmp_path, entorno, capsys):
    codigo = alerta.main(
        ["--unidad", "u", "--directorio-salidas", str(tmp_path)],
        cliente=SNSFalso(fallar=True),
        journal=lambda u: "clave-ultra-secreta",
    )
    assert codigo == 1 and "clave-ultra-secreta" not in capsys.readouterr().err


# ------------------------------------------------------------------ vigilante


@pytest.mark.unit
def test_vigilante_con_corrida_valida_no_alerta(tmp_path, entorno):
    manifiesto(tmp_path, "20261013_003000")
    sns = SNSFalso()
    ahora = datetime(2026, 10, 13, 5, 0, tzinfo=ZONA)
    assert verificacion.main(["--directorio-salidas", str(tmp_path)], cliente=sns, ahora=ahora) == 0
    assert sns.mensajes == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "existentes",
    [
        [],  # el temporizador ni se disparo
        [("20261013_003000", "nocturno", "ERROR", "2026-10-13")],
        [("20261013_010000", "ensayo", "OK", "2026-10-13")],
        [("20261012_003000", "nocturno", "OK", "2026-10-12")],  # la de ayer
    ],
)
def test_vigilante_alerta_sin_corrida_valida_de_hoy(tmp_path, entorno, existentes):
    for ident, modo, estado, jornada in existentes:
        manifiesto(tmp_path, ident, modo, estado, jornada)
    sns = SNSFalso()
    ahora = datetime(2026, 10, 13, 5, 0, tzinfo=ZONA)
    assert verificacion.main(["--directorio-salidas", str(tmp_path)], cliente=sns, ahora=ahora) == 1
    assert "2026-10-13" in sns.mensajes[0]["Subject"]


@pytest.mark.unit
def test_vigilante_sin_poder_alertar_sale_con_2(tmp_path, entorno):
    ahora = datetime(2026, 10, 13, 5, 0, tzinfo=ZONA)
    codigo = verificacion.main(
        ["--directorio-salidas", str(tmp_path)], cliente=SNSFalso(fallar=True), ahora=ahora
    )
    assert codigo == 2


# ------------------------------------------------------------------ aviso de exito


@pytest.mark.unit
def test_aviso_de_exito_solo_con_piloto_avisar_ok(entorno, monkeypatch):
    m = {
        "id_ejecucion": "20261013_003000",
        "modo": "nocturno",
        "estado": "OK",
        "objetivo": {"d_mas_1": "2026-10-13"},
        "grupo": "SOMBRA",
        "segundos": 312.4,
        "bd": {"filas": 57},
        "factor": {"1": {"valor": 0.87}, "3": {"valor": 0.91}},
        "advertencias": ["Ruta 1: aviso"],
        "entorno": "EC2",
    }
    sns = SNSFalso()
    d = Dependencias(cliente_sns=lambda: sns)
    monkeypatch.delenv("PILOTO_AVISAR_OK", raising=False)
    avisar_ok(m, d)
    assert sns.mensajes == []
    monkeypatch.setenv("PILOTO_AVISAR_OK", "1")
    avisar_ok(m, d)
    texto = sns.mensajes[0]["Message"]
    assert "2026-10-13" in sns.mensajes[0]["Subject"]
    assert "Filas escritas en la base: 57" in texto and "312.4 s" in texto
    # Un fallo del aviso no lanza excepciones.
    avisar_ok(m, Dependencias(cliente_sns=lambda: SNSFalso(fallar=True)))
