"""Registro de la ejecucion con enmascaramiento de secretos.

Todo texto que sale de la piloto (log, manifiesto, mensaje de error en la base,
estado de la ultima ejecucion, avisos) pasa por ``ocultar``: el valor de cada
credencial del proyecto se reemplaza por ``[OCULTO]`` en cualquier posicion,
aunque este pegado a otras letras.

Son credenciales del proyecto:
- las variables cuyo nombre empieza por REGISTEL_, PILOTO_ o AWS_ y contiene
  PASSWORD, SECRET, TOKEN, KEY o USER (p. ej. REGISTEL_DB_PASSWORD,
  REGISTEL_DB_USER, AWS_SECRET_ACCESS_KEY);
- las que se declaran en ``registro.variables_sensibles`` de piloto.yaml.

Las variables del sistema operativo (USERNAME, USERPROFILE, HOME, USER,
LOGNAME...) no son credenciales y no se ocultan. Los valores se leen en cada
llamada, asi que tambien cubren las variables cargadas de .env despues de
configurar el registro.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Mapping
from pathlib import Path

OCULTO = "[OCULTO]"
PREFIJOS_PROYECTO = ("REGISTEL_", "PILOTO_", "AWS_")
PALABRAS_SENSIBLES = ("PASSWORD", "SECRET", "TOKEN", "KEY", "USER")

FORMATO = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

# Nombres declarados en piloto.yaml (registro.variables_sensibles).
_ADICIONALES: set[str] = set()


def registrar_variables_sensibles(nombres: Iterable[str]) -> None:
    """Agrega nombres de variables cuyo valor siempre se oculta."""
    _ADICIONALES.update(str(n).strip().upper() for n in nombres if str(n).strip())


def es_sensible(nombre: str) -> bool:
    nombre = nombre.upper()
    if nombre in _ADICIONALES:
        return True
    return nombre.startswith(PREFIJOS_PROYECTO) and any(p in nombre for p in PALABRAS_SENSIBLES)


def valores_sensibles(entorno: Mapping[str, str] | None = None) -> list[str]:
    """Valores no vacios de las credenciales del proyecto, de mayor a menor largo."""
    entorno = os.environ if entorno is None else entorno
    valores = {v for k, v in entorno.items() if es_sensible(k) and v and v.strip()}
    return sorted(valores, key=len, reverse=True)


def ocultar(texto: str, entorno: Mapping[str, str] | None = None) -> str:
    """El texto con cada credencial del proyecto reemplazada por [OCULTO], en cualquier posicion."""
    if not texto:
        return texto
    for valor in valores_sensibles(entorno):
        texto = texto.replace(valor, OCULTO)
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
