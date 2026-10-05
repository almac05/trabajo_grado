"""Calibracion de los parametros de la recomendacion de despacho.

A partir de los despachos individuales del conjunto apto para modelado:

- Jornada operativa: fecha de la hora de salida menos cuatro horas.
- Franja: hora de salida truncada a 30 minutos; su tipo de dia se toma del
  dataset de modelado (no se redefine la regla de festivos).
- Regimen raro: tipo de dia en ``tipos_baja_frecuencia`` del contrato comparativo.
- Cuantiles con interpolacion lineal, como en analisis/36_pasajeros_por_despacho.py:
  Q1, mediana y Q3 por ruta y bloque en regimen ordinario y por ruta en regimen raro.
- Capacidad: maximo de despachos de ambas rutas en una jornada del periodo.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from pandas.api.typing import DataFrameGroupBy

from proyecto_grado.dispatch.config import BloqueHorario

logger = logging.getLogger(__name__)

REGIMEN_ORDINARIO = "ordinario"
REGIMEN_RARO = "raro"
BLOQUE_TODOS = "todos"
HORAS_DESFASE_JORNADA = 4
COLUMNAS_PARAMETROS = [
    "route",
    "regimen",
    "bloque",
    "n_despachos",
    "n_jornadas",
    "q1",
    "mediana",
    "q3",
]
PATRON_BLOQUE_SCRIPT_36 = re.compile(r"\((\d{2}):00")


class ErrorDatosRecomendacion(ValueError):  # noqa: N818
    """Indica que los datos de entrada no permiten calibrar o recomendar."""


@dataclass(frozen=True)
class ParametrosCalibracion:
    """Tabla de cuantiles por ruta, regimen y bloque, y capacidad conjunta."""

    tabla: pd.DataFrame
    capacidad: int
    jornada_capacidad: date


def asignar_bloque(horas: pd.Series, bloques: Sequence[BloqueHorario]) -> pd.Series:
    """Nombre del bloque de cada hora entera; ``None`` antes del primer bloque."""
    inicios = np.array([bloque.hora_inicio for bloque in bloques])
    nombres = np.array([bloque.nombre for bloque in bloques], dtype=object)
    posicion = np.searchsorted(inicios, horas.to_numpy(dtype=int), side="right") - 1
    valores = np.where(posicion >= 0, nombres[np.clip(posicion, 0, None)], None)
    return pd.Series(valores, index=horas.index, dtype=object)


def regimen_de(tipo_dia: pd.Series, tipos_raros: Sequence[str]) -> pd.Series:
    """Regimen raro u ordinario segun el tipo de dia."""
    return pd.Series(
        np.where(tipo_dia.isin(list(tipos_raros)), REGIMEN_RARO, REGIMEN_ORDINARIO),
        index=tipo_dia.index,
    )


def preparar_despachos(
    model_ready: pd.DataFrame,
    tipo_dia_franjas: pd.DataFrame,
    bloques: Sequence[BloqueHorario],
    tipos_raros: Sequence[str],
    columna_pasajeros: str = "PASAJEROS_REALES",
) -> pd.DataFrame:
    """Un registro por despacho con ruta, jornada, franja, bloque, tipo de dia y regimen.

    ``tipo_dia_franjas`` lleva ``FK_RUTA``, ``timestamp`` y ``tipo_dia`` por franja.
    El dataset de modelado solo trae las franjas del horario operativo; a un
    despacho aislado fuera de el se le asigna el tipo de dia de las demas franjas
    de su ruta y jornada en el mismo dataset (``tipo_dia_fuente = "jornada"``). Si
    tampoco hay jornada, el tipo de dia queda nulo.
    """
    datos = model_ready
    if "MODEL_READY_OK" in datos.columns:
        datos = datos[datos["MODEL_READY_OK"].astype(bool)]
    inicio = pd.to_datetime(datos["HORA_INICIAL_REAL"])
    franja = inicio.dt.floor("30min")
    despachos = pd.DataFrame(
        {
            "route": datos["FK_RUTA"].astype(int).to_numpy(),
            "dia_op": (inicio - pd.Timedelta(hours=HORAS_DESFASE_JORNADA)).dt.date.to_numpy(),
            "franja": franja.to_numpy(),
            "hora": franja.dt.strftime("%H:%M").to_numpy(),
            "bloque": asignar_bloque(franja.dt.hour, bloques).to_numpy(),
            "pasajeros": datos[columna_pasajeros].astype(float).to_numpy(),
        }
    )
    tipos = (
        tipo_dia_franjas[["FK_RUTA", "timestamp", "tipo_dia"]]
        .drop_duplicates(["FK_RUTA", "timestamp"])
        .rename(columns={"FK_RUTA": "route", "timestamp": "franja"})
    )
    tipos["franja"] = pd.to_datetime(tipos["franja"]).astype(despachos["franja"].dtype)
    despachos = despachos.merge(tipos, on=["route", "franja"], how="left", validate="m:1")
    despachos["tipo_dia_fuente"] = pd.Series("franja", index=despachos.index, dtype=object).where(
        despachos["tipo_dia"].notna(), None
    )

    tipos["dia_op"] = (tipos["franja"] - pd.Timedelta(hours=HORAS_DESFASE_JORNADA)).dt.date
    por_jornada = tipos.groupby(["route", "dia_op"])["tipo_dia"].agg(["first", "nunique"])
    ambiguas = por_jornada[por_jornada["nunique"] > 1]
    if len(ambiguas):
        raise ErrorDatosRecomendacion(
            f"{len(ambiguas)} jornadas con mas de un tipo de dia en el dataset de modelado."
        )
    sin_tipo = despachos["tipo_dia"].isna()
    if sin_tipo.any():
        claves = pd.MultiIndex.from_arrays(
            [despachos.loc[sin_tipo, "route"], despachos.loc[sin_tipo, "dia_op"]]
        )
        despachos.loc[sin_tipo, "tipo_dia"] = por_jornada["first"].reindex(claves).to_numpy()
        recuperados = sin_tipo & despachos["tipo_dia"].notna()
        despachos.loc[recuperados, "tipo_dia_fuente"] = "jornada"
        logger.info(
            "%d despachos fuera de las franjas del dataset de modelado: %d toman el tipo de "
            "dia de su jornada y %d quedan sin tipo de dia.",
            int(sin_tipo.sum()),
            int(recuperados.sum()),
            int((sin_tipo & ~recuperados).sum()),
        )
    despachos["regimen"] = regimen_de(despachos["tipo_dia"], tipos_raros)
    return despachos


def filtrar_periodo(despachos: pd.DataFrame, inicio: date, fin: date) -> pd.DataFrame:
    """Despachos cuya jornada esta en [inicio, fin]; exige tipo de dia y bloque."""
    en_periodo = despachos[(despachos["dia_op"] >= inicio) & (despachos["dia_op"] <= fin)]
    sin_tipo = int(en_periodo["tipo_dia"].isna().sum())
    sin_bloque = int(en_periodo["bloque"].isna().sum())
    if sin_tipo or sin_bloque:
        raise ErrorDatosRecomendacion(
            f"Entre {inicio} y {fin} hay {sin_tipo} despachos sin tipo de dia en el dataset "
            f"de modelado y {sin_bloque} fuera de los bloques horarios."
        )
    return en_periodo.reset_index(drop=True)


def _cuantiles(grupos: DataFrameGroupBy) -> pd.DataFrame:
    return grupos.agg(
        n_despachos=("pasajeros", "size"),
        n_jornadas=("dia_op", "nunique"),
        q1=("pasajeros", lambda s: float(np.quantile(s, 0.25))),
        mediana=("pasajeros", lambda s: float(np.quantile(s, 0.5))),
        q3=("pasajeros", lambda s: float(np.quantile(s, 0.75))),
    ).reset_index()


def calcular_tabla_parametros(
    despachos: pd.DataFrame, bloques: Sequence[BloqueHorario]
) -> pd.DataFrame:
    """Cuantiles por ruta y bloque en regimen ordinario y por ruta en regimen raro."""
    ordinario = despachos[despachos["regimen"] == REGIMEN_ORDINARIO]
    raro = despachos[despachos["regimen"] == REGIMEN_RARO]
    tabla_ordinaria = _cuantiles(ordinario.groupby(["route", "bloque"]))
    tabla_ordinaria["regimen"] = REGIMEN_ORDINARIO
    tabla_rara = _cuantiles(raro.groupby("route"))
    tabla_rara["regimen"] = REGIMEN_RARO
    tabla_rara["bloque"] = BLOQUE_TODOS

    rutas = sorted(despachos["route"].unique())
    nombres = [bloque.nombre for bloque in bloques]
    esperadas = {(r, b) for r in rutas for b in nombres}
    faltantes = esperadas - set(
        zip(tabla_ordinaria["route"], tabla_ordinaria["bloque"], strict=True)
    )
    if faltantes:
        raise ErrorDatosRecomendacion(
            f"Sin despachos ordinarios de calibracion en (ruta, bloque): {sorted(faltantes)}."
        )
    faltantes_raro = set(rutas) - set(tabla_rara["route"])
    if faltantes_raro:
        raise ErrorDatosRecomendacion(
            f"Sin despachos de regimen raro en calibracion para las rutas {sorted(faltantes_raro)}."
        )

    orden = {nombre: posicion for posicion, nombre in enumerate([*nombres, BLOQUE_TODOS])}
    tabla = pd.concat([tabla_ordinaria, tabla_rara], ignore_index=True)[COLUMNAS_PARAMETROS]
    return tabla.sort_values(
        ["route", "regimen", "bloque"],
        key=lambda s: s.map(orden) if s.name == "bloque" else s,
    ).reset_index(drop=True)


def calcular_capacidad(despachos: pd.DataFrame) -> tuple[int, date]:
    """Maximo de despachos conjuntos de todas las rutas en una jornada, y esa jornada."""
    por_jornada = despachos.groupby("dia_op").size()
    jornada = por_jornada.idxmax()
    return int(por_jornada.max()), jornada


def calibrar(
    despachos_calibracion: pd.DataFrame, bloques: Sequence[BloqueHorario]
) -> ParametrosCalibracion:
    """Tabla de parametros y capacidad a partir de los despachos del periodo de calibracion."""
    tabla = calcular_tabla_parametros(despachos_calibracion, bloques)
    capacidad, jornada = calcular_capacidad(despachos_calibracion)
    logger.info("Capacidad conjunta: %d despachos (jornada %s).", capacidad, jornada)
    return ParametrosCalibracion(tabla=tabla, capacidad=capacidad, jornada_capacidad=jornada)


def asociar_parametros(franjas: pd.DataFrame, tabla: pd.DataFrame) -> pd.DataFrame:
    """Agrega a cada franja los cuantiles de su regimen y los ordinarios de su bloque.

    ``q1``, ``mediana`` y ``q3``: los de la ruta y el bloque en regimen ordinario, o
    los de la ruta en regimen raro. ``mediana_ordinaria`` y ``q3_ordinario``: los de
    la ruta y el bloque en regimen ordinario, sea cual sea el regimen de la franja.
    """
    ordinaria = tabla[tabla["regimen"] == REGIMEN_ORDINARIO][
        ["route", "bloque", "q1", "mediana", "q3"]
    ]
    rara = tabla[tabla["regimen"] == REGIMEN_RARO][["route", "q1", "mediana", "q3"]]
    salida = franjas.merge(
        ordinaria.rename(
            columns={"q1": "q1_ordinario", "mediana": "mediana_ordinaria", "q3": "q3_ordinario"}
        ),
        on=["route", "bloque"],
        how="left",
        validate="m:1",
    ).merge(
        rara.rename(columns={"q1": "q1_raro", "mediana": "mediana_rara", "q3": "q3_raro"}),
        on="route",
        how="left",
        validate="m:1",
    )
    es_raro = salida["regimen"] == REGIMEN_RARO
    for cuantil, ordinario, raro in (
        ("q1", "q1_ordinario", "q1_raro"),
        ("mediana", "mediana_ordinaria", "mediana_rara"),
        ("q3", "q3_ordinario", "q3_raro"),
    ):
        salida[cuantil] = salida[raro].where(es_raro, salida[ordinario])
    faltantes = int(salida[["q1", "mediana", "q3", "mediana_ordinaria"]].isna().any(axis=1).sum())
    if faltantes:
        raise ErrorDatosRecomendacion(f"{faltantes} franjas sin parametros de calibracion.")
    return salida.drop(columns=["q1_ordinario", "q1_raro", "mediana_rara", "q3_raro"])


def _bloque_por_etiqueta_36(etiqueta: str, bloques: Sequence[BloqueHorario]) -> str | None:
    if etiqueta == BLOQUE_TODOS:
        return BLOQUE_TODOS
    coincidencia = PATRON_BLOQUE_SCRIPT_36.search(etiqueta)
    if coincidencia is None:
        return None
    hora = int(coincidencia.group(1))
    return next((b.nombre for b in bloques if b.hora_inicio == hora), None)


def verificar_contra_script_36(
    tabla: pd.DataFrame,
    distribucion: pd.DataFrame,
    bloques: Sequence[BloqueHorario],
    tolerancia: float = 1e-9,
) -> pd.DataFrame:
    """Compara los cuantiles calibrados con las filas de validacion del script 36.

    Tres comparaciones: ``bloque`` (filas del clasificador del script 36, ambos
    regimenes juntos) y ``regimen_x_bloque`` (solo regimen ordinario) frente a los
    parametros ordinarios por ruta y bloque; ``regimen`` (raro) frente a los
    parametros raros por ruta.
    """
    validacion = distribucion[distribucion["periodo"] == "validacion"].copy()
    validacion["route"] = validacion["route"].astype(int)
    validacion["bloque_modulo"] = [
        _bloque_por_etiqueta_36(str(etiqueta), bloques) for etiqueta in validacion["bloque"]
    ]
    referencias = {
        "bloque": validacion[validacion["corte"] == "bloque"],
        "regimen_x_bloque": validacion[
            (validacion["corte"] == "regimen_x_bloque")
            & (validacion["regimen"] == REGIMEN_ORDINARIO)
        ],
        "regimen": validacion[
            (validacion["corte"] == "regimen") & (validacion["regimen"] == REGIMEN_RARO)
        ],
    }
    filas = []
    for corte, referencia in referencias.items():
        regimen = REGIMEN_RARO if corte == "regimen" else REGIMEN_ORDINARIO
        propia = tabla[tabla["regimen"] == regimen]
        unido = propia.merge(
            referencia[["route", "bloque_modulo", "bloque", "n_despachos", "q1", "mediana", "q3"]],
            left_on=["route", "bloque"],
            right_on=["route", "bloque_modulo"],
            how="outer",
            suffixes=("", "_36"),
            indicator=True,
        )
        for registro in unido.to_dict("records"):
            fila = {
                "corte_36": corte,
                "regimen_modulo": regimen,
                "route": registro["route"],
                "bloque": registro["bloque"]
                if pd.notna(registro["bloque"])
                else registro["bloque_modulo"],
                "bloque_36": registro["bloque_36"],
                "presente_en": str(registro["_merge"]),
                "n_despachos": registro["n_despachos"],
                "n_despachos_36": registro["n_despachos_36"],
            }
            coincide = registro["_merge"] == "both"
            for cuantil in ("q1", "mediana", "q3"):
                diferencia = registro[cuantil] - registro[f"{cuantil}_36"]
                fila[cuantil] = registro[cuantil]
                fila[f"{cuantil}_36"] = registro[f"{cuantil}_36"]
                fila[f"dif_{cuantil}"] = diferencia
                if cuantil in ("mediana", "q3"):
                    coincide = coincide and bool(abs(diferencia) <= tolerancia)
            fila["coincide_mediana_q3"] = bool(coincide)
            filas.append(fila)
    resultado = pd.DataFrame(filas)
    for corte, grupo in resultado.groupby("corte_36", sort=False):
        distintas = int((~grupo["coincide_mediana_q3"]).sum())
        if distintas:
            logger.warning(
                "Script 36, corte %s: %d de %d celdas con mediana o Q3 distintas.",
                corte,
                distintas,
                len(grupo),
            )
        else:
            logger.info("Script 36, corte %s: %d celdas coinciden.", corte, len(grupo))
    return resultado
