"""Esquema versionado de bd_montebello_recomendaciones: vistas por grupo y sin secretos."""

import ipaddress
import re

import pytest

from proyecto_grado.modeling.config import PROJECT_ROOT

ESQUEMA = PROJECT_ROOT / "deploy" / "mysql" / "esquema_recomendaciones.sql"
MARCADOR = "<CONTRASENA_LARGA>"
ESTADOS_VISIBLES = {"OK", "ADVERTENCIA", "CONTINGENCIA"}


def _sin_comentarios(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def _vista(nombre: str) -> str:
    """Cuerpo de CREATE ... VIEW <nombre> AS ... ; sin comentarios y en una linea."""
    sql = _sin_comentarios(ESQUEMA.read_text(encoding="utf-8"))
    m = re.search(rf"\bVIEW\s+`?{nombre}`?\s+AS\b(.*?);", sql, re.IGNORECASE | re.DOTALL)
    assert m, f"No esta la vista {nombre}"
    return " ".join(m.group(1).split())


def _grupos_filtrados(cuerpo: str) -> set[str]:
    """Valores de las condiciones sobre grupo (= 'X' o IN ('X', ...))."""
    condiciones = re.findall(
        r"\b(?:\w+\.)?grupo\s*(?:=\s*'(\w+)'|IN\s*\(([^)]*)\))", cuerpo, re.IGNORECASE
    )
    assert condiciones, "La vista no filtra por grupo"
    grupos = set()
    for igual, lista in condiciones:
        grupos |= {igual} if igual else set(re.findall(r"'(\w+)'", lista))
    return {g.upper() for g in grupos}


def _estados_filtrados(cuerpo: str) -> set[str]:
    m = re.search(r"\bc\.estado\s+IN\s*\(([^)]*)\)", cuerpo, re.IGNORECASE)
    assert m, "La vista no filtra por estado de la corrida"
    return {e.upper() for e in re.findall(r"'(\w+)'", m.group(1))}


@pytest.mark.unit
def test_vista_vigente_solo_muestra_modulo():
    cuerpo = _vista("v_recomendaciones_vigentes")
    assert _grupos_filtrados(cuerpo) == {"MODULO"}
    assert _estados_filtrados(cuerpo) == ESTADOS_VISIBLES
    # Un OR en el WHERE podria dejar pasar CONTROL o SOMBRA.
    assert not re.search(r"\bOR\b", cuerpo, re.IGNORECASE)


@pytest.mark.unit
def test_vista_de_prueba_incluye_sombra_y_no_control():
    cuerpo = _vista("v_recomendaciones_prueba")
    assert _grupos_filtrados(cuerpo) == {"MODULO", "SOMBRA"}
    assert _estados_filtrados(cuerpo) == ESTADOS_VISIBLES
    assert not re.search(r"\bOR\b", cuerpo, re.IGNORECASE)


@pytest.mark.unit
def test_esquema_sin_contrasenas_ni_ip_publicas():
    texto = ESQUEMA.read_text(encoding="utf-8")
    contrasenas = re.findall(
        r"(?:IDENTIFIED\s+BY(?:\s+PASSWORD)?|PASSWORD\s*(?:=|\())\s*'([^']*)'",
        texto,
        re.IGNORECASE,
    )
    assert contrasenas, "Se esperaba al menos el marcador de contrasena"
    assert set(contrasenas) == {MARCADOR}
    for ip in re.findall(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])", texto):
        try:
            direccion = ipaddress.ip_address(ip)
        except ValueError:
            continue
        assert not direccion.is_global, f"IP publica en el esquema: {ip}"
