"""Contrato de configs/piloto/piloto.yaml, entradas congeladas, grupos y entorno."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import date, time
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.fechas import hora_de_texto

RUTA_CONFIG_PREDETERMINADA = PROJECT_ROOT / "configs" / "piloto" / "piloto.yaml"
EXTENSIONES_TEXTO = {".yaml", ".yml", ".json", ".csv", ".md", ".txt"}
VARIABLE_ENTORNO = "PILOTO_ENTORNO"


class ErrorConfiguracionPiloto(ValueError):  # noqa: N818
    """Configuracion invalida o incompleta."""


class ErrorEntradaCongelada(RuntimeError):  # noqa: N818
    """Una entrada congelada falta o su SHA-256 no coincide."""


class Grupo(StrEnum):
    MODULO = "MODULO"
    CONTROL = "CONTROL"
    SOMBRA = "SOMBRA"


class Entorno(StrEnum):
    EC2 = "EC2"
    LOCAL = "LOCAL"


@dataclass(frozen=True)
class EntradaCongelada:
    nombre: str
    ruta: Path
    sha256: str
    solo_fuente_local: bool = False


@dataclass(frozen=True)
class ConfigPiloto:
    candidato: str
    nota_candidato: str
    inicio_jornada: time
    corte_objetivo: time
    sin_bd_desde: time
    sin_bd_hasta: time
    ventana_dias: int
    ventana_dias_domingo: int
    margen_pk: int
    inicio_almacen: date
    ventana_correccion_dias: int
    min_franjas_jornada: int
    rango_factor: tuple[float, float]
    fin_backtest: date
    semanas_referencia_larga: int
    ruta_asignacion_grupos: Path
    directorio_salidas: Path
    esquema_bd: str
    entradas: dict[str, EntradaCongelada] = field(default_factory=dict)
    ruta_config: Path | None = None
    # Nombres de variables de entorno que siempre se ocultan (ademas de las
    # credenciales REGISTEL_/PILOTO_/AWS_; ver piloto.registro).
    variables_sensibles: tuple[str, ...] = ()

    def entrada(self, nombre: str) -> Path:
        try:
            return self.entradas[nombre].ruta
        except KeyError as exc:
            raise ErrorConfiguracionPiloto(f"Entrada congelada no declarada: {nombre}.") from exc


def _seccion(raw: dict, nombre: str) -> dict:
    valor = raw.get(nombre)
    if not isinstance(valor, dict):
        raise ErrorConfiguracionPiloto(f"Falta la seccion {nombre!r} en la configuracion.")
    return valor


def _campo(seccion: dict, nombre: str, contexto: str) -> Any:
    if nombre not in seccion or seccion[nombre] is None:
        raise ErrorConfiguracionPiloto(f"Falta {contexto}.{nombre} en la configuracion.")
    return seccion[nombre]


def _fecha(valor: Any, contexto: str) -> date:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as exc:
        raise ErrorConfiguracionPiloto(f"Fecha invalida en {contexto}: {valor!r}.") from exc


def _ruta(valor: Any, raiz: Path) -> Path:
    ruta = Path(str(valor))
    if ruta.is_absolute():
        raise ErrorConfiguracionPiloto(f"Las rutas deben ser relativas a la raiz: {valor}.")
    return raiz / ruta


def cargar_configuracion(
    ruta: Path = RUTA_CONFIG_PREDETERMINADA, raiz: Path = PROJECT_ROOT
) -> ConfigPiloto:
    """Lee y valida la configuracion de la piloto; las rutas quedan bajo ``raiz``."""
    raw = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    cand = _seccion(raw, "candidato")
    hor = _seccion(raw, "horario")
    ext = _seccion(raw, "extraccion")
    cor = _seccion(raw, "correccion")
    pre = _seccion(raw, "prediccion")
    gru = _seccion(raw, "grupos")
    sal = _seccion(raw, "salidas")
    if str(_campo(hor, "zona", "horario")) != "America/Bogota":
        raise ErrorConfiguracionPiloto("La zona horaria de la piloto es America/Bogota.")

    entradas = {}
    for nombre, e in _seccion(raw, "entradas").items():
        if not isinstance(e, dict):
            raise ErrorConfiguracionPiloto(f"Entrada {nombre!r} mal declarada.")
        sha = str(_campo(e, "sha256", f"entradas.{nombre}")).lower()
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ErrorConfiguracionPiloto(f"SHA-256 invalido en entradas.{nombre}.")
        entradas[nombre] = EntradaCongelada(
            nombre=nombre,
            ruta=_ruta(_campo(e, "ruta", f"entradas.{nombre}"), raiz),
            sha256=sha,
            solo_fuente_local=bool(e.get("solo_fuente_local", False)),
        )

    rango = _campo(cor, "rango_factor", "correccion")
    if not (isinstance(rango, list) and len(rango) == 2 and rango[0] < rango[1]):
        raise ErrorConfiguracionPiloto("correccion.rango_factor debe ser [minimo, maximo].")

    return ConfigPiloto(
        candidato=str(_campo(cand, "nombre", "candidato")),
        nota_candidato=str(_campo(cand, "nota", "candidato")).strip(),
        inicio_jornada=hora_de_texto(_campo(hor, "inicio_jornada", "horario")),
        corte_objetivo=hora_de_texto(_campo(hor, "corte_objetivo", "horario")),
        sin_bd_desde=hora_de_texto(_campo(hor, "sin_bd_desde", "horario")),
        sin_bd_hasta=hora_de_texto(_campo(hor, "sin_bd_hasta", "horario")),
        ventana_dias=int(_campo(ext, "ventana_dias", "extraccion")),
        ventana_dias_domingo=int(_campo(ext, "ventana_dias_domingo", "extraccion")),
        margen_pk=int(_campo(ext, "margen_pk", "extraccion")),
        inicio_almacen=_fecha(_campo(ext, "inicio_almacen", "extraccion"), "inicio_almacen"),
        ventana_correccion_dias=int(_campo(cor, "ventana_dias", "correccion")),
        min_franjas_jornada=int(_campo(cor, "min_franjas_jornada", "correccion")),
        rango_factor=(float(rango[0]), float(rango[1])),
        fin_backtest=_fecha(_campo(cor, "fin_backtest", "correccion"), "fin_backtest"),
        semanas_referencia_larga=int(_campo(pre, "semanas_referencia_larga", "prediccion")),
        ruta_asignacion_grupos=_ruta(_campo(gru, "asignacion", "grupos"), raiz),
        directorio_salidas=_ruta(_campo(sal, "directorio", "salidas"), raiz),
        esquema_bd=str(_campo(sal, "esquema_bd", "salidas")),
        entradas=entradas,
        ruta_config=Path(ruta),
        variables_sensibles=_variables_sensibles(raw.get("registro")),
    )


def _variables_sensibles(seccion: Any) -> tuple[str, ...]:
    """registro.variables_sensibles (opcional): lista de nombres de variables."""
    if seccion is None:
        return ()
    if not isinstance(seccion, dict):
        raise ErrorConfiguracionPiloto("La seccion 'registro' debe ser un mapa.")
    nombres = seccion.get("variables_sensibles") or []
    if not isinstance(nombres, list) or not all(isinstance(n, str) for n in nombres):
        raise ErrorConfiguracionPiloto(
            "registro.variables_sensibles debe ser una lista de nombres."
        )
    return tuple(n.strip().upper() for n in nombres if n.strip())


# --------------------------------------------------------------- SHA-256


def sha256_archivo(ruta: Path) -> str:
    """SHA-256 de un archivo; en los de texto, con finales de linea normalizados a LF."""
    ruta = Path(ruta)
    h = hashlib.sha256()
    if ruta.suffix.lower() in EXTENSIONES_TEXTO:
        h.update(ruta.read_bytes().replace(b"\r\n", b"\n"))
        return h.hexdigest()
    with ruta.open("rb") as f:
        while bloque := f.read(1 << 20):
            h.update(bloque)
    return h.hexdigest()


def verificar_entradas(cfg: ConfigPiloto, fuente_local: bool) -> dict[str, dict[str, str]]:
    """Comprueba el SHA-256 de cada entrada congelada que usa la ejecucion.

    Devuelve {nombre: {ruta, sha256}} para el manifiesto. Si alguna falta o no
    coincide, lanza ``ErrorEntradaCongelada`` con todas las diferencias.
    """
    resultado, problemas = {}, []
    for nombre, e in cfg.entradas.items():
        if e.solo_fuente_local and not fuente_local:
            continue
        relativa = _relativa(e.ruta)
        if not e.ruta.exists():
            problemas.append(f"{nombre}: no existe {relativa}")
            continue
        sha = sha256_archivo(e.ruta)
        if sha != e.sha256:
            problemas.append(f"{nombre}: SHA-256 {sha} distinto del esperado {e.sha256}")
        resultado[nombre] = {"ruta": relativa, "sha256": sha}
    if problemas:
        raise ErrorEntradaCongelada("Entradas congeladas invalidas: " + "; ".join(problemas))
    return resultado


def _relativa(ruta: Path) -> str:
    try:
        return Path(ruta).resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return Path(ruta).as_posix()


# --------------------------------------------------------------- grupos y entorno


def cargar_asignacion_grupos(ruta: Path) -> dict[date, Grupo]:
    """Mapa fecha -> grupo; un archivo sin fechas es un mapa vacio."""
    raw = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ErrorConfiguracionPiloto(f"{ruta}: se esperaba un mapa fecha -> grupo.")
    asignacion = {}
    for clave, valor in raw.items():
        fecha = _fecha(clave, f"asignacion de grupos ({clave})")
        try:
            asignacion[fecha] = Grupo(str(valor).strip().upper())
        except ValueError as exc:
            raise ErrorConfiguracionPiloto(
                f"Grupo invalido para {fecha}: {valor!r} (MODULO, CONTROL o SOMBRA)."
            ) from exc
    return asignacion


def grupo_de(fecha: date, ruta: Path) -> Grupo:
    """Grupo de la jornada; SOMBRA si la fecha no esta asignada."""
    return cargar_asignacion_grupos(ruta).get(fecha, Grupo.SOMBRA)


def entorno() -> Entorno:
    """PILOTO_ENTORNO (EC2 o LOCAL), obligatorio."""
    valor = os.environ.get(VARIABLE_ENTORNO)
    if not valor:
        raise ErrorConfiguracionPiloto(
            f"Falta la variable de entorno {VARIABLE_ENTORNO} (EC2 o LOCAL)."
        )
    try:
        return Entorno(valor.strip().upper())
    except ValueError as exc:
        raise ErrorConfiguracionPiloto(
            f"{VARIABLE_ENTORNO}={valor!r} no es valido: use EC2 o LOCAL."
        ) from exc
