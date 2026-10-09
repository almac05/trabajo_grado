"""Registro de la ejecucion con enmascaramiento de secretos.

Todo texto que sale de la piloto (log, manifiesto, mensaje de error en la base,
estado de la ultima ejecucion) pasa por ``ocultar``: el valor de cualquier
variable de entorno cuyo nombre contenga PASSWORD, SECRET, TOKEN, KEY o USER se
reemplaza por ``[OCULTO]``. Los valores se leen en cada llamada, asi que tambien
cubren las variables que se cargan de .env despues de configurar el registro.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from pathlib import Path

OCULTO = "[OCULTO]"
PALABRAS_SENSIBLES = ("PASSWORD", "SECRET", "TOKEN", "KEY", "USER")
# Los valores mas cortos se ocultan solo como palabra completa, para no
# destrozar el texto (p. ej. un valor "1" no reemplaza cada digito 1).
LARGO_MINIMO_SUBCADENA = 4

FORMATO = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def es_sensible(nombre: str) -> bool:
    nombre = nombre.upper()
    return any(p in nombre for p in PALABRAS_SENSIBLES)


def valores_sensibles(entorno: Mapping[str, str] | None = None) -> list[str]:
    """Valores no vacios de las variables sensibles, de mayor a menor largo."""
    entorno = os.environ if entorno is None else entorno
    valores = {v for k, v in entorno.items() if es_sensible(k) and v and v.strip()}
    return sorted(valores, key=len, reverse=True)


def ocultar(texto: str, entorno: Mapping[str, str] | None = None) -> str:
    """El texto con los valores sensibles del entorno reemplazados por [OCULTO]."""
    if not texto:
        return texto
    for valor in valores_sensibles(entorno):
        if len(valor) >= LARGO_MINIMO_SUBCADENA:
            texto = texto.replace(valor, OCULTO)
        else:
            texto = re.sub(rf"(?<!\w){re.escape(valor)}(?!\w)", OCULTO, texto)
    return texto


class FormateadorSeguro(logging.Formatter):
    """Formatea el registro completo (incluidas las trazas) y oculta los secretos."""

    def format(self, record: logging.LogRecord) -> str:
        return ocultar(super().format(record))


def configurar_registro(archivo: Path | None, nivel: int = logging.INFO) -> list[logging.Handler]:
    """Manejadores de consola y, si se indica, de archivo, ambos con enmascaramiento.

    Reemplaza los manejadores del registrador raiz para que ningun mensaje
    (tampoco los de los modulos del ETL que se reutilizan) salga sin pasar por
    ``FormateadorSeguro``. Devuelve los manejadores creados.
    """
    raiz = logging.getLogger()
    for h in list(raiz.handlers):
        raiz.removeHandler(h)
        h.close()
    formateador = FormateadorSeguro(FORMATO, FORMATO_FECHA)
    manejadores: list[logging.Handler] = [logging.StreamHandler()]
    if archivo is not None:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        manejadores.append(logging.FileHandler(archivo, encoding="utf-8"))
    for h in manejadores:
        h.setFormatter(formateador)
        raiz.addHandler(h)
    raiz.setLevel(nivel)
    return manejadores


def cerrar_registro(manejadores: list[logging.Handler]) -> None:
    raiz = logging.getLogger()
    for h in manejadores:
        raiz.removeHandler(h)
        h.close()
