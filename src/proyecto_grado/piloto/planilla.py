"""Planilla Excel de la jornada (seccion 6 del diseno, con los cambios de la fase 1).

``planillas/planilla_<AAAA-MM-DD>_<estado>_<grupo>.xlsx``; si ya existe, se crea
``..._v2``, ``..._v3`` y el motivo queda en el log. Nunca se sobrescribe.

Hojas:
- Resumen: jornada, tipo de dia, regimen, estado, grupo, marcas de corrida
  anticipada o tardia, advertencias en lenguaje llano, factor por ruta, ultimo
  dato usado e identificador de la ejecucion.
- Por bloque: ruta, bloque, horario, pasajeros predichos y meta de despachos.
- Por franja: ruta, bloque y las columnas de ``dispatch.planilla.tabla_planilla``.

Cambios frente al diseno original: el despachador si ve los pasajeros predichos,
y no hay columnas para el despachador (la adherencia se mide despues contra los
despachos reales de la base).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from proyecto_grado.dispatch.config import BloqueHorario
from proyecto_grado.dispatch.planilla import NOTA_SIN_META, escribir_hoja, tabla_planilla

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatosPlanilla:
    fecha: str
    estado: str
    grupo: str
    id_ejecucion: str
    tipo_dia: str
    regimen: str
    factores: dict[int, float]
    ultimo_dato: str
    anticipada: bool = False
    tardia: bool = False
    advertencias: Sequence[str] = field(default_factory=tuple)


def nombre_disponible(directorio: Path, fecha: str, estado: str, grupo: str) -> tuple[Path, int]:
    """Primer nombre libre: sin sufijo, luego _v2, _v3..."""
    base = f"planilla_{fecha}_{estado}_{grupo}"
    version = 1
    ruta = Path(directorio) / f"{base}.xlsx"
    while ruta.exists():
        version += 1
        ruta = Path(directorio) / f"{base}_v{version}.xlsx"
    return ruta, version


def horario_bloques(bloques: Sequence[BloqueHorario]) -> dict[str, str]:
    """Texto del horario de cada bloque; el ultimo queda abierto."""
    textos = {}
    for i, b in enumerate(bloques):
        if i + 1 < len(bloques):
            textos[b.nombre] = f"{b.hora_inicio:02d}:00 a {bloques[i + 1].hora_inicio:02d}:00"
        else:
            textos[b.nombre] = f"desde las {b.hora_inicio:02d}:00"
    return textos


def tabla_resumen(d: DatosPlanilla) -> pd.DataFrame:
    filas = [
        ("Jornada", d.fecha),
        ("Estado", d.estado),
        ("Grupo", d.grupo),
        ("Tipo de día", d.tipo_dia),
        ("Régimen", d.regimen),
    ]
    if d.anticipada:
        filas.append(
            (
                "Corrida anticipada",
                "Sí: se calculó antes de cerrar la jornada anterior; sus datos están incompletos.",
            )
        )
    if d.tardia:
        filas.append(("Corrida tardía", "Sí: se calculó después del inicio del servicio (04:00)."))
    for ruta, f in sorted(d.factores.items()):
        filas.append((f"Factor de corrección ruta {ruta}", round(float(f), 4)))
    filas += [("Datos hasta", d.ultimo_dato), ("Ejecución", d.id_ejecucion)]
    if d.advertencias:
        filas += [("Advertencia", a) for a in d.advertencias]
    else:
        filas.append(("Advertencias", "Ninguna"))
    return pd.DataFrame(filas, columns=["Campo", "Valor"])


def tabla_por_bloque(rec: pd.DataFrame, bloques: Sequence[BloqueHorario]) -> pd.DataFrame:
    orden = {b.nombre: i for i, b in enumerate(bloques)}
    horario = horario_bloques(bloques)
    g = (
        rec.groupby(["route", "bloque"])
        .agg(
            pasajeros=("demanda_predicha", "sum"),
            meta=("despachos_recomendados", "sum"),
            sin_meta=("en_disponibilidad", lambda s: int((~s.astype(bool)).sum())),
        )
        .reset_index()
    )
    g = g.sort_values(["route", "bloque"], key=lambda c: c.map(orden) if c.name == "bloque" else c)
    return pd.DataFrame(
        {
            "Ruta": g["route"].to_numpy(),
            "Bloque": g["bloque"].to_numpy(),
            "Horario": g["bloque"].map(horario).to_numpy(),
            "Pasajeros predichos": g["pasajeros"].round(1).to_numpy(),
            "Meta de despachos": g["meta"].astype(int).to_numpy(),
            "Franjas sin meta": g["sin_meta"].to_numpy(),
        }
    )


def tabla_por_franja(rec: pd.DataFrame, usar_tope: bool, minimo: int) -> pd.DataFrame:
    partes = []
    for ruta, r in rec.groupby("route", sort=True):
        r = r.sort_values("hora")
        t = tabla_planilla(r, usar_tope, minimo)
        t.insert(0, "Bloque", r["bloque"].to_numpy())
        t.insert(0, "Ruta", int(ruta))
        partes.append(t)
    return pd.concat(partes, ignore_index=True)


def escribir_planilla(
    directorio: Path,
    datos: DatosPlanilla,
    rec: pd.DataFrame,
    bloques: Sequence[BloqueHorario],
    usar_tope: bool,
    minimo: int,
) -> Path:
    """Escribe la planilla con un nombre libre y devuelve su ruta."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    ruta, version = nombre_disponible(directorio, datos.fecha, datos.estado, datos.grupo)
    if version > 1:
        logger.warning(
            "Ya existe una planilla de %s con estado %s y grupo %s: se emite la version %d (%s).",
            datos.fecha,
            datos.estado,
            datos.grupo,
            version,
            ruta.name,
        )
    pie = [
        f"Jornada {datos.fecha} · Estado {datos.estado} · Grupo {datos.grupo} · "
        f"Ejecución {datos.id_ejecucion}"
    ]
    temporal = ruta.with_name(ruta.stem + ".tmp.xlsx")
    with pd.ExcelWriter(temporal, engine="openpyxl") as xw:
        escribir_hoja(xw, "Resumen", tabla_resumen(datos), [])
        escribir_hoja(xw, "Por bloque", tabla_por_bloque(rec, bloques), pie)
        escribir_hoja(
            xw, "Por franja", tabla_por_franja(rec, usar_tope, minimo), [NOTA_SIN_META, *pie]
        )
    if ruta.exists():  # creada por otro proceso entre la eleccion del nombre y ahora
        temporal.unlink()
        raise FileExistsError(f"No se sobrescribe: {ruta}")
    os.replace(temporal, ruta)
    return ruta
