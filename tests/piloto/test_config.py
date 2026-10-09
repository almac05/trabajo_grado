"""Configuracion de la piloto, entradas congeladas, grupos y entorno."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.config import (
    RUTA_CONFIG_PREDETERMINADA,
    ErrorConfiguracionPiloto,
    ErrorEntradaCongelada,
    Grupo,
    cargar_asignacion_grupos,
    cargar_configuracion,
    entorno,
    grupo_de,
    sha256_archivo,
    verificar_entradas,
)


def _config_con_entradas(tmp_path: Path, entradas: dict) -> Path:
    raw = yaml.safe_load(RUTA_CONFIG_PREDETERMINADA.read_text(encoding="utf-8"))
    raw["entradas"] = entradas
    ruta = tmp_path / "piloto.yaml"
    ruta.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return ruta


@pytest.mark.unit
def test_configuracion_versionada_es_valida():
    cfg = cargar_configuracion()
    assert cfg.candidato == "C3"
    assert "decision explicita" in cfg.nota_candidato
    assert cfg.ventana_dias == 7 and cfg.ventana_dias_domingo == 35
    assert cfg.inicio_almacen == date(2026, 9, 27)
    assert cfg.esquema_bd == "bd_montebello_recomendaciones"
    assert cfg.rango_factor == (0.68, 1.08)
    assert all(e.ruta.is_relative_to(PROJECT_ROOT) for e in cfg.entradas.values())


@pytest.mark.unit
def test_sha256_de_texto_normaliza_finales_de_linea(tmp_path):
    lf, crlf = tmp_path / "a.yaml", tmp_path / "b.yaml"
    lf.write_bytes(b"x: 1\ny: 2\n")
    crlf.write_bytes(b"x: 1\r\ny: 2\r\n")
    assert sha256_archivo(lf) == sha256_archivo(crlf)
    bin_lf, bin_crlf = tmp_path / "a.parquet", tmp_path / "b.parquet"
    bin_lf.write_bytes(b"x\n")
    bin_crlf.write_bytes(b"x\r\n")
    assert sha256_archivo(bin_lf) != sha256_archivo(bin_crlf)


@pytest.mark.unit
def test_entrada_que_no_coincide_es_error(tmp_path):
    datos = tmp_path / "datos.csv"
    datos.write_text("a\n1\n", encoding="utf-8")
    bueno = sha256_archivo(datos)
    ruta = _config_con_entradas(
        tmp_path,
        {
            "buena": {"ruta": "datos.csv", "sha256": bueno},
            "mala": {"ruta": "datos.csv", "sha256": "0" * 64},
        },
    )
    cfg = cargar_configuracion(ruta, raiz=tmp_path)
    with pytest.raises(ErrorEntradaCongelada, match="mala"):
        verificar_entradas(cfg, fuente_local=False)


@pytest.mark.unit
def test_entrada_faltante_es_error_y_solo_local_se_omite_con_bd(tmp_path):
    ruta = _config_con_entradas(
        tmp_path,
        {"local": {"ruta": "no_existe.parquet", "sha256": "0" * 64, "solo_fuente_local": True}},
    )
    cfg = cargar_configuracion(ruta, raiz=tmp_path)
    assert verificar_entradas(cfg, fuente_local=False) == {}
    with pytest.raises(ErrorEntradaCongelada, match="no existe"):
        verificar_entradas(cfg, fuente_local=True)


@pytest.mark.unit
def test_ruta_absoluta_se_rechaza(tmp_path):
    ruta = _config_con_entradas(
        tmp_path, {"x": {"ruta": str((tmp_path / "x.csv").resolve()), "sha256": "0" * 64}}
    )
    with pytest.raises(ErrorConfiguracionPiloto, match="relativas"):
        cargar_configuracion(ruta, raiz=tmp_path)


@pytest.mark.unit
def test_asignacion_versionada_esta_vacia():
    cfg = cargar_configuracion()
    assert cargar_asignacion_grupos(cfg.ruta_asignacion_grupos) == {}


@pytest.mark.unit
def test_grupo_por_defecto_es_sombra(tmp_path):
    ruta = tmp_path / "grupos.yaml"
    ruta.write_text("2026-10-20: MODULO\n2026-10-21: control\n", encoding="utf-8")
    assert grupo_de(date(2026, 10, 20), ruta) is Grupo.MODULO
    assert grupo_de(date(2026, 10, 21), ruta) is Grupo.CONTROL
    assert grupo_de(date(2026, 10, 22), ruta) is Grupo.SOMBRA


@pytest.mark.unit
def test_grupo_invalido_es_error(tmp_path):
    ruta = tmp_path / "grupos.yaml"
    ruta.write_text("2026-10-20: TODOS\n", encoding="utf-8")
    with pytest.raises(ErrorConfiguracionPiloto, match="Grupo invalido"):
        grupo_de(date(2026, 10, 20), ruta)


@pytest.mark.unit
def test_entorno_obligatorio(monkeypatch):
    monkeypatch.delenv("PILOTO_ENTORNO", raising=False)
    with pytest.raises(ErrorConfiguracionPiloto, match="PILOTO_ENTORNO"):
        entorno()
    monkeypatch.setenv("PILOTO_ENTORNO", "ec2")
    assert entorno() == "EC2"
    monkeypatch.setenv("PILOTO_ENTORNO", "AZURE")
    with pytest.raises(ErrorConfiguracionPiloto, match="EC2 o LOCAL"):
        entorno()
