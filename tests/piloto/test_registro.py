"""Enmascaramiento de secretos en el log."""

import logging

import pytest

from proyecto_grado.piloto.registro import (
    OCULTO,
    cerrar_registro,
    configurar_registro,
    ocultar,
    valores_sensibles,
)

ENTORNO = {
    "REGISTEL_DB_PASSWORD": "clave-muy-secreta",
    "REGISTEL_DB_USER": "usuario_bd",
    "AWS_SECRET_ACCESS_KEY": "abc/def+ghi",
    "API_TOKEN": "tk",
    "REGISTEL_DB_HOST": "127.0.0.1",
    "VACIO_PASSWORD": "",
}


@pytest.mark.unit
def test_solo_las_variables_sensibles():
    valores = valores_sensibles(ENTORNO)
    assert "127.0.0.1" not in valores
    assert {"clave-muy-secreta", "usuario_bd", "abc/def+ghi", "tk"} == set(valores)


@pytest.mark.unit
def test_ocultar_reemplaza_valores():
    texto = "conectando usuario_bd:clave-muy-secreta@127.0.0.1 con abc/def+ghi"
    r = ocultar(texto, ENTORNO)
    assert "clave-muy-secreta" not in r and "usuario_bd" not in r and "abc/def+ghi" not in r
    assert "127.0.0.1" in r and r.count(OCULTO) == 3


@pytest.mark.unit
def test_valor_corto_solo_como_palabra_completa():
    r = ocultar("token=tk; stack tkinter", ENTORNO)
    assert r == f"token={OCULTO}; stack tkinter"


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
        monkeypatch.setenv("NUEVA_SECRET", "cargada-despues")
        logging.getLogger("prueba").warning("valor cargada-despues")
    finally:
        cerrar_registro(manejadores)
    assert "cargada-despues" not in archivo.read_text(encoding="utf-8")


@pytest.mark.unit
def test_usuario_corto_no_se_oculta_dentro_de_otras_palabras():
    entorno = {"USERNAME": "regis", "REGISTEL_DB_PASSWORD": "Clave-Larga-2026!"}
    r = ocultar(
        "C:/Users/regis/x tbl_informacion_registradora c--Users-regis-p pwdClave-Larga-2026!x",
        entorno,
    )
    assert r == (
        f"C:/Users/{OCULTO}/x tbl_informacion_registradora c--Users-{OCULTO}-p pwd{OCULTO}x"
    )
