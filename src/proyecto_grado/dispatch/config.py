"""Carga y validacion de la configuracion de la recomendacion de despacho.

Reutiliza el contrato de evaluacion comparativa para el periodo de evaluacion y
los tipos de dia de baja frecuencia (regimen raro); le suma el periodo de
calibracion, los bloques horarios y los parametros de las reglas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped, unused-ignore]

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import (
    ConfiguracionEvaluacionComparativa,
    cargar_configuracion_evaluacion,
)

RUTA_CONFIG_PREDETERMINADA = PROJECT_ROOT / "configs" / "dispatch" / "recomendacion.yaml"
POLITICAS_FESTIVOS = ("divisor_propio", "divisor_ordinario")
ENTRADAS_ESPERADAS = (
    "model_ready",
    "dataset_modelado",
    "predicciones_xgboost",
    "predicciones_referencia",
    "jornadas_comunes",
    "observaciones_combinada",
    "distribucion_script_36",
)
PATRON_FREEZE = re.compile(r"^freeze_\d{8}_\d{6}$")


class ErrorConfiguracionRecomendacion(ValueError):  # noqa: N818
    """Indica que la configuracion de recomendacion no satisface el contrato."""


@dataclass(frozen=True)
class BloqueHorario:
    """Bloque horario definido por su hora de inicio; termina en el siguiente."""

    nombre: str
    hora_inicio: int


@dataclass(frozen=True)
class DisponibilidadHabitual:
    """Regla de disponibilidad habitual (ver reglas.disponibilidad_habitual)."""

    umbral: float
    ventana_semanas: int

    def __post_init__(self) -> None:
        if not 0 < self.umbral <= 1:
            raise ErrorConfiguracionRecomendacion(
                f"disponibilidad_habitual.umbral debe estar en (0, 1]: {self.umbral}."
            )
        if self.ventana_semanas < 1:
            raise ErrorConfiguracionRecomendacion(
                "disponibilidad_habitual.ventana_semanas debe ser al menos 1."
            )


@dataclass(frozen=True)
class ConfiguracionRecomendacion:
    """Contrato inmutable de la calibracion, recomendacion y evaluacion."""

    evaluacion: ConfiguracionEvaluacionComparativa
    freeze: str
    entradas: dict[str, Path]
    columna_pasajeros: str
    columna_prediccion_ordinaria: str
    columna_prediccion_rara: str
    inicio_calibracion: date
    fin_calibracion: date
    bloques: tuple[BloqueHorario, ...]
    politica_festivos: str
    usar_tope_carga: bool
    servicio_minimo: int
    directorio_salida: Path
    disponibilidad_habitual: DisponibilidadHabitual | None = None

    def __post_init__(self) -> None:
        if self.inicio_calibracion > self.fin_calibracion:
            raise ErrorConfiguracionRecomendacion(
                "El inicio del periodo de calibracion es posterior al fin."
            )
        if self.fin_calibracion >= self.evaluacion.inicio:
            raise ErrorConfiguracionRecomendacion(
                "El periodo de calibracion debe terminar antes del inicio del periodo de "
                f"evaluacion ({self.evaluacion.inicio}); fin={self.fin_calibracion}."
            )
        if self.politica_festivos not in POLITICAS_FESTIVOS:
            raise ErrorConfiguracionRecomendacion(
                f"politica_festivos debe ser una de {POLITICAS_FESTIVOS}: "
                f"{self.politica_festivos!r}."
            )
        if self.servicio_minimo < 1:
            raise ErrorConfiguracionRecomendacion("servicio_minimo debe ser al menos 1.")
        horas = [bloque.hora_inicio for bloque in self.bloques]
        if not horas or horas != sorted(set(horas)) or horas[0] < 0 or horas[-1] > 23:
            raise ErrorConfiguracionRecomendacion(
                "bloques_horarios debe declarar horas de inicio unicas, crecientes y en [0, 23]."
            )
        nombres = [bloque.nombre for bloque in self.bloques]
        if len(set(nombres)) != len(nombres):
            raise ErrorConfiguracionRecomendacion("Los nombres de los bloques deben ser unicos.")

    @property
    def inicio_evaluacion(self) -> date:
        """Inicio del periodo de evaluacion del contrato comparativo."""
        return self.evaluacion.inicio

    @property
    def fin_evaluacion(self) -> date:
        """Fin del periodo de evaluacion del contrato comparativo."""
        return self.evaluacion.fin

    @property
    def tipos_raros(self) -> tuple[str, ...]:
        """Tipos de dia del regimen raro."""
        return self.evaluacion.tipos_baja_frecuencia

    @property
    def nombres_bloques(self) -> tuple[str, ...]:
        """Nombres de los bloques en orden horario."""
        return tuple(bloque.nombre for bloque in self.bloques)


def _mapa(raw: Any, campo: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ErrorConfiguracionRecomendacion(f"Falta el bloque {campo}.")
    return raw


def _ruta_proyecto(valor: Any, campo: str) -> Path:
    if not valor:
        raise ErrorConfiguracionRecomendacion(f"Falta la ruta {campo}.")
    ruta = Path(str(valor))
    if ruta.is_absolute():
        raise ErrorConfiguracionRecomendacion(
            f"{campo} debe ser una ruta relativa al proyecto: {ruta}."
        )
    return PROJECT_ROOT / ruta


def _fecha(valor: Any, campo: str) -> date:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as exc:
        raise ErrorConfiguracionRecomendacion(f"{campo} debe usar el formato AAAA-MM-DD.") from exc


def _texto(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor:
        raise ErrorConfiguracionRecomendacion(f"{campo} debe ser un texto no vacio.")
    return valor


def _bloques(raw: Any) -> tuple[BloqueHorario, ...]:
    if not isinstance(raw, list) or not raw:
        raise ErrorConfiguracionRecomendacion("bloques_horarios debe ser una lista no vacia.")
    bloques: list[BloqueHorario] = []
    for posicion, item in enumerate(raw):
        entrada = _mapa(item, f"bloques_horarios[{posicion}]")
        hora = entrada.get("hora_inicio")
        if isinstance(hora, bool) or not isinstance(hora, int):
            raise ErrorConfiguracionRecomendacion(
                f"bloques_horarios[{posicion}].hora_inicio debe ser un entero."
            )
        bloques.append(
            BloqueHorario(
                nombre=_texto(entrada.get("nombre"), f"bloques_horarios[{posicion}].nombre"),
                hora_inicio=hora,
            )
        )
    return tuple(bloques)


def _disponibilidad(raw: Any) -> DisponibilidadHabitual | None:
    if raw is None:
        return None
    entrada = _mapa(raw, "reglas.disponibilidad_habitual")
    umbral = entrada.get("umbral")
    ventana = entrada.get("ventana_semanas")
    if isinstance(umbral, bool) or not isinstance(umbral, int | float):
        raise ErrorConfiguracionRecomendacion("disponibilidad_habitual.umbral debe ser numerico.")
    if isinstance(ventana, bool) or not isinstance(ventana, int):
        raise ErrorConfiguracionRecomendacion(
            "disponibilidad_habitual.ventana_semanas debe ser un entero."
        )
    return DisponibilidadHabitual(umbral=float(umbral), ventana_semanas=ventana)


def cargar_configuracion_recomendacion(
    ruta: str | Path | None = None,
    ruta_evaluacion: str | Path | None = None,
) -> ConfiguracionRecomendacion:
    """Carga configs/dispatch/recomendacion.yaml (u otra ruta) y valida el contrato."""
    ruta_config = Path(ruta) if ruta is not None else RUTA_CONFIG_PREDETERMINADA
    if not ruta_config.is_absolute():
        ruta_config = PROJECT_ROOT / ruta_config
    if not ruta_config.is_file():
        raise FileNotFoundError(f"No existe la configuracion de recomendacion: {ruta_config}.")
    with ruta_config.open(encoding="utf-8") as archivo:
        raw = yaml.safe_load(archivo)
    raw = _mapa(raw, "raiz de la configuracion")

    freeze = str(raw.get("freeze", ""))
    if PATRON_FREEZE.fullmatch(freeze) is None:
        raise ErrorConfiguracionRecomendacion(f"freeze no cumple el patron esperado: {freeze!r}.")

    entradas_raw = _mapa(raw.get("entradas"), "entradas")
    faltantes = [nombre for nombre in ENTRADAS_ESPERADAS if nombre not in entradas_raw]
    if faltantes:
        raise ErrorConfiguracionRecomendacion(f"Faltan entradas: {', '.join(faltantes)}.")
    entradas = {
        nombre: _ruta_proyecto(entradas_raw[nombre], f"entradas.{nombre}")
        for nombre in ENTRADAS_ESPERADAS
    }

    columnas = _mapa(raw.get("columnas"), "columnas")
    calibracion = _mapa(raw.get("calibracion"), "calibracion")
    periodo = _mapa(calibracion.get("periodo"), "calibracion.periodo")
    if periodo.get("extremos_inclusivos") is not True:
        raise ErrorConfiguracionRecomendacion(
            "El periodo de calibracion debe declarar ambos extremos inclusivos."
        )
    reglas = _mapa(raw.get("reglas"), "reglas")
    usar_tope = reglas.get("usar_tope_carga", True)
    if not isinstance(usar_tope, bool):
        raise ErrorConfiguracionRecomendacion("reglas.usar_tope_carga debe ser booleano.")
    minimo = reglas.get("servicio_minimo", 1)
    if isinstance(minimo, bool) or not isinstance(minimo, int):
        raise ErrorConfiguracionRecomendacion("reglas.servicio_minimo debe ser un entero.")
    salidas = _mapa(raw.get("salidas"), "salidas")

    return ConfiguracionRecomendacion(
        evaluacion=cargar_configuracion_evaluacion(ruta_evaluacion),
        freeze=freeze,
        entradas=entradas,
        columna_pasajeros=_texto(columnas.get("pasajeros"), "columnas.pasajeros"),
        columna_prediccion_ordinaria=_texto(
            columnas.get("prediccion_ordinaria"), "columnas.prediccion_ordinaria"
        ),
        columna_prediccion_rara=_texto(columnas.get("prediccion_rara"), "columnas.prediccion_rara"),
        inicio_calibracion=_fecha(periodo.get("inicio"), "calibracion.periodo.inicio"),
        fin_calibracion=_fecha(periodo.get("fin"), "calibracion.periodo.fin"),
        bloques=_bloques(raw.get("bloques_horarios")),
        politica_festivos=str(reglas.get("politica_festivos", "divisor_propio")),
        usar_tope_carga=usar_tope,
        servicio_minimo=minimo,
        directorio_salida=_ruta_proyecto(salidas.get("directorio"), "salidas.directorio"),
        disponibilidad_habitual=_disponibilidad(reglas.get("disponibilidad_habitual")),
    )
