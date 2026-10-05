"""Reglas de recomendacion de despachos por franja y ajuste de factibilidad.

Regimen ordinario: el mayor entre la demanda dividida por la mediana (redondeo
aritmetico, 0,5 sube) y, si el tope de carga esta activo, la demanda dividida
por Q3 redondeada hacia arriba; nunca menos que el servicio minimo.

Regimen raro: la demanda dividida por la mediana rara de la ruta
(``divisor_propio``) o por la mediana ordinaria de la ruta y el bloque
(``divisor_ordinario``), con redondeo aritmetico y el mismo minimo.

Factibilidad: si el total de la jornada (ambas rutas) supera la capacidad, se
retira un despacho a la vez de la franja cuyo valor de pasajeros por despacho
resultante sea el menor, sin bajar del minimo. Los empates se resuelven por
ruta y hora.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd

from proyecto_grado.dispatch.config import POLITICAS_FESTIVOS, BloqueHorario
from proyecto_grado.dispatch.parametros import (
    REGIMEN_RARO,
    ErrorDatosRecomendacion,
    ParametrosCalibracion,
    asignar_bloque,
    asociar_parametros,
)

logger = logging.getLogger(__name__)

ArregloFlotante = npt.NDArray[np.float64]


def redondeo_aritmetico(valores: npt.ArrayLike) -> ArregloFlotante:
    """Redondeo en el que 0,5 sube (a diferencia de ``round``, que va al par).

    Usa la parte fraccionaria exacta ``x - floor(x)`` en lugar de ``floor(x + 0,5)``,
    que puede fallar por la suma en coma flotante.
    """
    x = np.asarray(valores, dtype=float)
    piso = np.floor(x)
    return np.asarray(piso + (x - piso >= 0.5), dtype=float)


def despachos_ordinario(
    demanda: npt.ArrayLike,
    mediana: npt.ArrayLike,
    q3: npt.ArrayLike,
    usar_tope: bool,
    minimo: int,
) -> ArregloFlotante:
    """Despachos en regimen ordinario."""
    d = np.clip(np.asarray(demanda, dtype=float), 0.0, None)
    por_mediana = redondeo_aritmetico(d / np.asarray(mediana, dtype=float))
    if usar_tope:
        por_tope = np.ceil(d / np.asarray(q3, dtype=float))
        por_mediana = np.maximum(por_mediana, por_tope)
    return np.asarray(np.maximum(por_mediana, minimo), dtype=float)


def despachos_raro(demanda: npt.ArrayLike, divisor: npt.ArrayLike, minimo: int) -> ArregloFlotante:
    """Despachos en regimen raro."""
    d = np.clip(np.asarray(demanda, dtype=float), 0.0, None)
    return np.asarray(
        np.maximum(redondeo_aritmetico(d / np.asarray(divisor, dtype=float)), minimo),
        dtype=float,
    )


def recomendar_despachos(
    franjas: pd.DataFrame,
    politica_festivos: str,
    usar_tope: bool,
    minimo: int,
    columna_demanda: str = "demanda_predicha",
) -> pd.DataFrame:
    """Despachos por franja antes del ajuste de factibilidad.

    ``franjas`` debe traer ``regimen``, la demanda y las columnas de
    ``asociar_parametros``: ``mediana`` (la del regimen), ``mediana_ordinaria`` y
    ``q3_ordinario``.
    """
    if politica_festivos not in POLITICAS_FESTIVOS:
        raise ErrorDatosRecomendacion(f"Politica de festivos desconocida: {politica_festivos!r}.")
    salida = franjas.copy()
    es_raro = (salida["regimen"] == REGIMEN_RARO).to_numpy()
    divisor_raro = (
        salida["mediana"] if politica_festivos == "divisor_propio" else salida["mediana_ordinaria"]
    )
    salida["divisor"] = np.where(es_raro, divisor_raro, salida["mediana_ordinaria"])
    ordinario = despachos_ordinario(
        salida[columna_demanda],
        salida["mediana_ordinaria"],
        salida["q3_ordinario"],
        usar_tope,
        minimo,
    )
    raro = despachos_raro(salida[columna_demanda], divisor_raro, minimo)
    salida["despachos_sin_ajuste"] = np.where(es_raro, raro, ordinario).astype(int)
    return salida


def aplicar_factibilidad(
    franjas: pd.DataFrame,
    capacidad: int,
    minimo: int,
    columna_demanda: str = "demanda_predicha",
    columna_despachos: str = "despachos_sin_ajuste",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ajusta los despachos de cada jornada a la capacidad conjunta.

    Devuelve las franjas con ``despachos_recomendados`` y ``despachos_retirados``, y
    un resumen por jornada (``dia_op``) con el total antes y despues del ajuste.
    """
    salida = franjas.sort_values(["dia_op", "route", "hora"]).reset_index(drop=True)
    recomendados = salida[columna_despachos].to_numpy(dtype=int).copy()
    demanda = np.clip(salida[columna_demanda].to_numpy(dtype=float), 0.0, None)
    if (recomendados < minimo).any():
        raise ErrorDatosRecomendacion("Hay franjas con menos despachos que el servicio minimo.")

    filas = []
    for dia, posiciones in salida.groupby("dia_op", sort=True).indices.items():
        n = recomendados[posiciones]
        d = demanda[posiciones]
        total_inicial = int(n.sum())
        while n.sum() > capacidad:
            reducibles = n > minimo
            if not reducibles.any():
                logger.warning(
                    "Jornada %s: %d despachos con todas las franjas en el minimo; "
                    "no se alcanza la capacidad %d.",
                    dia,
                    int(n.sum()),
                    capacidad,
                )
                break
            resultante = np.where(reducibles, d / np.maximum(n - 1, 1), np.inf)
            n[int(np.argmin(resultante))] -= 1
        recomendados[posiciones] = n
        filas.append(
            {
                "dia_op": dia,
                "rutas": int(salida.loc[posiciones, "route"].nunique()),
                "total_sin_ajuste": total_inicial,
                "total_recomendado": int(n.sum()),
                "retirados": total_inicial - int(n.sum()),
                "ajustada": total_inicial > capacidad,
                "factible": int(n.sum()) <= capacidad,
            }
        )
    salida["despachos_recomendados"] = recomendados
    salida["despachos_retirados"] = salida[columna_despachos].to_numpy(dtype=int) - recomendados
    jornadas = pd.DataFrame(filas)
    logger.info(
        "Factibilidad (capacidad %d): %d de %d jornadas ajustadas, %d despachos retirados.",
        capacidad,
        int(jornadas["ajustada"].sum()) if len(jornadas) else 0,
        len(jornadas),
        int(jornadas["retirados"].sum()) if len(jornadas) else 0,
    )
    return salida, jornadas


def generar_recomendacion(
    prediccion: pd.DataFrame,
    parametros: ParametrosCalibracion,
    bloques: Sequence[BloqueHorario],
    politica_festivos: str,
    usar_tope: bool,
    minimo: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bloque, parametros, reglas y factibilidad sobre la prediccion mixta."""
    franjas = prediccion.copy()
    horas = franjas["hora"].str.slice(0, 2).astype(int)
    franjas["bloque"] = asignar_bloque(horas, bloques)
    if franjas["bloque"].isna().any():
        raise ErrorDatosRecomendacion("Hay franjas predichas fuera de los bloques horarios.")
    franjas = asociar_parametros(franjas, parametros.tabla)
    franjas = recomendar_despachos(franjas, politica_festivos, usar_tope, minimo)
    return aplicar_factibilidad(franjas, parametros.capacidad, minimo)
