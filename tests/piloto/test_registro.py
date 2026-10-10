"""Enmascaramiento de las credenciales del proyecto en el log."""

import logging

import pytest

from proyecto_grado.piloto import registro
from proyecto_grado.piloto.registro import (
    OCULTO,
    cerrar_registro,
    configurar_registro,
    es_sensible,
    ocultar,
    registrar_variables_sensibles,
    valores_sensibles,
)

ENTORNO = {
    "REGISTEL_DB_PASSWORD": "clave-muy-secreta",
    "REGISTEL_DB_USER": "reco_proceso",
    "AWS_SECRET_ACCESS_KEY": "abc/def+ghi",
    "PILOTO_API_TOKEN": "tk9",
    "REGISTEL_DB_HOST": "127.0.0.1",
    "PILOTO_S3_BUCKET": "registel-montebello-despacho",
    "REGISTEL_VACIO_PASSWORD": "",
    # Variables del sistema operativo: no son credenciales del proyecto.
    "USERNAME": "regis",
    "USERPROFILE": "C:\\Users\\regis",
    "HOME": "/opt/despacho",
    "USER": "despacho",
    "LOGNAME": "despacho",
    "SSH_AUTH_SOCK_KEY": "x",
}


@pytest.fixture(autouse=True)
def sin_adicionales():
    previo = set(registro._ADICIONALES)
    registro._ADICIONALES.clear()
    yield
    registro._ADICIONALES.clear()
    registro._ADICIONALES.update(previo)


@pytest.mark.unit
def test_solo_credenciales_del_proyecto():
    assert set(valores_sensibles(ENTORNO)) == {
        "clave-muy-secreta",
        "reco_proceso",
        "abc/def+ghi",
        "tk9",
    }
    for nombre in (
        "USERNAME",
        "USERPROFILE",
        "HOME",
        "USER",
        "LOGNAME",
        "REGISTEL_DB_HOST",
        "PILOTO_S3_BUCKET",
        "SSH_AUTH_SOCK_KEY",
    ):
        assert not es_sensible(nombre), nombre


@pytest.mark.unit
def test_variables_declaradas_en_la_configuracion():
    assert not es_sensible("CLAVE_EXTERNA")
    registrar_variables_sensibles(["clave_externa", " "])
    assert es_sensible("CLAVE_EXTERNA")
    assert ocultar("valor: qq7", {"CLAVE_EXTERNA": "qq7"}) == f"valor: {OCULTO}"


@pytest.mark.unit
def test_ocultar_en_cualquier_posicion():
    texto = "conectando reco_proceso:clave-muy-secreta@127.0.0.1 con abc/def+ghi"
    r = ocultar(texto, ENTORNO)
    assert "clave-muy-secreta" not in r and "reco_proceso" not in r and "abc/def+ghi" not in r
    assert "127.0.0.1" in r and r.count(OCULTO) == 3


@pytest.mark.unit
def test_contrasena_corta_pegada_a_texto_se_oculta():
    r = ocultar("xxtk9yy token=tk9", ENTORNO)
    assert r == f"xx{OCULTO}yy token={OCULTO}"


@pytest.mark.unit
def test_usuario_del_sistema_no_se_oculta():
    texto = "C:/Users/regis/x tbl_informacion_registradora /opt/despacho/proyecto_grado"
    assert ocultar(texto, ENTORNO) == texto


@pytest.mark.unit
def test_log_y_traza_enmascarados(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTEL_DB_PASSWORD", "clave-muy-secreta")
    archivo = tmp_path / "ejecucion.log"
    manejadores = configurar_registro(archivo)
    try:
        log = logging.getLogger("prueba.registro")
        log.info("password=%s", "clave-muy-secreta")
        try:
            raise RuntimeError("fallo con clave-muy-secreta")
        except RuntimeError:
            log.exception("error")
    finally:
        cerrar_registro(manejadores)
    contenido = archivo.read_text(encoding="utf-8")
    assert "clave-muy-secreta" not in contenido
    assert contenido.count(OCULTO) >= 2
    assert "RuntimeError" in contenido


@pytest.mark.unit
def test_valores_cargados_despues_de_configurar(tmp_path, monkeypatch):
    archivo = tmp_path / "ejecucion.log"
    manejadores = configurar_registro(archivo)
    try:
        monkeypatch.setenv("PILOTO_NUEVA_SECRET", "cargada-despues")
        logging.getLogger("prueba").warning("valor cargada-despues")
    finally:
        cerrar_registro(manejadores)
    assert "cargada-despues" not in archivo.read_text(encoding="utf-8")
