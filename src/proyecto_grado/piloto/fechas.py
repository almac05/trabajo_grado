"""Fechas de la piloto, siempre en hora de Colombia.

Es el unico lugar donde se decide "hoy". Nunca se usa la hora del sistema
operativo (la instancia EC2 esta en UTC): toda hora se convierte a
``America/Bogota`` y las horas sin zona se rechazan.

La jornada operativa empieza a las 04:00: un instante pertenece a la jornada de
la fecha de (instante - 4 h). Una corrida que empieza en el dia calendario X:

- antes de las 12:00 predice la jornada X con D = X - 1 completa; si empieza
  desde las 04:00 es *tardia* (el servicio de X ya empezo);
- desde las 12:00 predice la jornada X + 1 con D = X aun en curso: es
  *anticipada* (D incompleto).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Bogota")
INICIO_JORNADA = time(4, 0)
CORTE_OBJETIVO = time(12, 0)
SIN_BD_DESDE = time(4, 0)
SIN_BD_HASTA = time(21, 0)


class ErrorFecha(ValueError):  # noqa: N818
    """Hora sin zona horaria o fecha objetivo invalida."""


@dataclass(frozen=True)
class Objetivo:
    """Jornada a predecir (``d_mas_1``) y la ultima jornada de datos (``d``)."""

    d: date
    d_mas_1: date
    tardia: bool
    anticipada: bool
    fijada: bool  # True si vino de --fecha-objetivo y no del reloj

    def como_dict(self) -> dict:
        return {
            "d": self.d.isoformat(),
            "d_mas_1": self.d_mas_1.isoformat(),
            "tardia": self.tardia,
            "anticipada": self.anticipada,
            "fijada": self.fijada,
        }


def a_bogota(instante: datetime) -> datetime:
    """El instante en hora de Colombia; rechaza horas sin zona horaria."""
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ErrorFecha(f"Hora sin zona horaria: {instante!r}.")
    return instante.astimezone(ZONA)


def ahora_bogota() -> datetime:
    """Hora actual de Colombia (independiente de la zona del sistema operativo)."""
    return datetime.now(tz=ZONA)


def jornada_de(instante: datetime, inicio: time = INICIO_JORNADA) -> date:
    """Jornada operativa a la que pertenece un instante."""
    local = a_bogota(instante)
    return (local - timedelta(hours=inicio.hour, minutes=inicio.minute)).date()


def jornada_objetivo(
    ahora: datetime,
    inicio: time = INICIO_JORNADA,
    corte: time = CORTE_OBJETIVO,
) -> Objetivo:
    """Jornada objetivo de una corrida que empieza en ``ahora``."""
    local = a_bogota(ahora)
    hoy, hora = local.date(), local.time()
    if hora < corte:
        return Objetivo(
            d=hoy - timedelta(days=1),
            d_mas_1=hoy,
            tardia=hora >= inicio,
            anticipada=False,
            fijada=False,
        )
    return Objetivo(
        d=hoy, d_mas_1=hoy + timedelta(days=1), tardia=False, anticipada=True, fijada=False
    )


def objetivo_fijado(d_mas_1: date) -> Objetivo:
    """Objetivo de --fecha-objetivo (ensayos con jornadas pasadas)."""
    return Objetivo(
        d=d_mas_1 - timedelta(days=1), d_mas_1=d_mas_1, tardia=False, anticipada=False, fijada=True
    )


def horario_bd_permitido(
    ahora: datetime, desde: time = SIN_BD_DESDE, hasta: time = SIN_BD_HASTA
) -> bool:
    """False en [desde, hasta) hora de Colombia: no se consulta la base real."""
    hora = a_bogota(ahora).time()
    return not (desde <= hora < hasta)


def id_ejecucion(instante: datetime) -> str:
    """Identificador AAAAMMDD_HHMMSS de la ejecucion, en hora de Colombia."""
    return a_bogota(instante).strftime("%Y%m%d_%H%M%S")


def hora_de_texto(valor: str) -> time:
    """Hora HH:MM de la configuracion."""
    try:
        return time.fromisoformat(str(valor))
    except ValueError as exc:
        raise ErrorFecha(f"Hora invalida: {valor!r}.") from exc
