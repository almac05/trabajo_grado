"""Reglas de recomendacion de despachos por franja y ajuste de factibilidad.

Regimen ordinario: el mayor entre la demanda dividida por la mediana (redondeo
aritmetico, 0,5 sube) y, si el tope de carga esta activo, la demanda dividida
por Q3 redondeada hacia arriba; nunca menos que el servicio minimo.

Regimen raro: la demanda dividida por la mediana rara de la ruta
(``divisor_propio``) o por la mediana ordinaria de la ruta y el bloque
(``divisor_ordinario``), con redondeo aritmetico y el mismo minimo.

Disponibilidad habitual (opcional): una franja esta en disponibilidad habitual
si tuvo al menos un despacho en una proporcion igual o mayor al umbral de las
jornadas del mismo tipo de dia en las semanas anteriores al corte. Fuera de ella
la meta es 0, sea cual sea la demanda predicha; dentro, rigen las reglas
anteriores con el servicio minimo.

Factibilidad: si el total de la jornada (ambas rutas) supera la capacidad, se
retira un despacho a la vez de la franja cuyo valor de pasajeros por despacho
resultante sea el menor, sin bajar del minimo (0 fuera de la disponibilidad
habitual). Los empates se resuelven por ruta y hora.
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


def disponibilidad_habitual(
    franjas: pd.DataFrame,
    historial: pd.DataFrame,
    umbral: float,
    ventana_semanas: int,
) -> pd.DataFrame:
    """Marca las franjas en disponibilidad habitual.

    ``franjas`` trae ``route``, ``dia_op`` (la jornada objetivo, cuyo inicio es el
    corte), ``tipo_dia`` y ``hora``. ``historial`` trae una fila por ruta, jornada
    y franja de las jornadas pasadas, con ``route``, ``dia_op``, ``tipo_dia``,
    ``hora`` y ``despachos``; una franja sin despachos en una jornada figura con 0
    o sin fila, y cada jornada con al menos una fila cuenta en el denominador.

    Para cada franja se usan solo las jornadas de su ruta y tipo de dia con
    ``dia_op`` en [corte - ventana_semanas semanas, corte - 1 dia]: ningun dato
    de la jornada objetivo ni posterior entra en el calculo. La fraccion de
    servicio es la proporcion de esas jornadas con al menos un despacho en la
    franja, y la franja esta en disponibilidad habitual si es >= ``umbral``. Sin
    jornadas del tipo de dia en la ventana no hay evidencia para excluir: la
    franja queda en disponibilidad y ``jornadas_previas`` es 0.

    Devuelve ``franjas`` con ``jornadas_previas``, ``frac_servicio`` y
    ``en_disponibilidad``.
    """
    if not 0 < umbral <= 1:
        raise ErrorDatosRecomendacion(f"El umbral debe estar en (0, 1]: {umbral}.")
    if ventana_semanas < 1:
        raise ErrorDatosRecomendacion(
            f"La ventana debe ser de al menos 1 semana: {ventana_semanas}."
        )
    salida = franjas.copy()
    objetivo = pd.to_datetime(salida["dia_op"]).dt.date
    hist = historial.copy()
    hist["dia_op"] = pd.to_datetime(hist["dia_op"]).dt.date
    hist["con_servicio"] = hist["despachos"].fillna(0) > 0

    jornadas = np.zeros(len(salida), dtype=int)
    fraccion = np.full(len(salida), np.nan)
    grupos = salida.groupby([salida["route"], objetivo, salida["tipo_dia"]]).indices
    for (ruta, dia, tipo), posiciones in grupos.items():
        inicio = dia - pd.Timedelta(weeks=ventana_semanas)
        ventana = hist[
            (hist["route"] == ruta)
            & (hist["tipo_dia"] == tipo)
            & (hist["dia_op"] >= inicio)
            & (hist["dia_op"] < dia)
        ]
        n = ventana["dia_op"].nunique()
        jornadas[posiciones] = n
        if n:
            con_servicio = ventana[ventana["con_servicio"]].groupby("hora")["dia_op"].nunique()
            horas = pd.Series(salida["hora"].to_numpy()[posiciones])
            fraccion[posiciones] = horas.map(con_servicio).fillna(0).to_numpy() / n
    salida["jornadas_previas"] = jornadas
    salida["frac_servicio"] = fraccion
    salida["en_disponibilidad"] = (jornadas == 0) | (fraccion >= umbral)
    return salida


def intervalo_sugerido(despachos: npt.ArrayLike, minutos_franja: int = 30) -> ArregloFlotante:
    """Minutos entre salidas: la franja dividida por los despachos, parte entera;
    sin valor (NaN) si no hay despachos."""
    n = np.asarray(despachos, dtype=float)
    con = n > 0
    return np.where(con, np.floor(minutos_franja / np.where(con, n, 1.0)), np.nan)


def recomendar_despachos(
    franjas: pd.DataFrame,
    politica_festivos: str,
    usar_tope: bool,
    minimo: int,
    columna_demanda: str = "demanda_predicha",
    columna_disponibilidad: str | None = None,
) -> pd.DataFrame:
    """Despachos por franja antes del ajuste de factibilidad.

    ``franjas`` debe traer ``regimen``, la demanda y las columnas de
    ``asociar_parametros``: ``mediana`` (la del regimen), ``mediana_ordinaria`` y
    ``q3_ordinario``. Con ``columna_disponibilidad``, las franjas con ``False`` en
    esa columna reciben 0 despachos, y ``despachos_regla_normal`` guarda, solo como
    informacion, lo que habria dado la regla (divisor, redondeo y minimo).
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
    despachos = np.where(es_raro, raro, ordinario)
    if columna_disponibilidad is not None:
        disponible = salida[columna_disponibilidad].astype(bool).to_numpy()
        salida["despachos_regla_normal"] = despachos.astype(int)
        despachos = np.where(disponible, despachos, 0)
    salida["despachos_sin_ajuste"] = despachos.astype(int)
    return salida


def aplicar_factibilidad(
    franjas: pd.DataFrame,
    capacidad: int,
    minimo: int,
    columna_demanda: str = "demanda_predicha",
    columna_despachos: str = "despachos_sin_ajuste",
    columna_disponibilidad: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ajusta los despachos de cada jornada a la capacidad conjunta.

    Devuelve las franjas con ``despachos_recomendados`` y ``despachos_retirados``, y
    un resumen por jornada (``dia_op``) con el total antes y despues del ajuste.
    Con ``columna_disponibilidad``, el minimo de las franjas con ``False`` es 0.
    """
    salida = franjas.sort_values(["dia_op", "route", "hora"]).reset_index(drop=True)
    recomendados = salida[columna_despachos].to_numpy(dtype=int).copy()
    demanda = np.clip(salida[columna_demanda].to_numpy(dtype=float), 0.0, None)
    minimos = np.full(len(salida), minimo, dtype=int)
    if columna_disponibilidad is not None:
        minimos[~salida[columna_disponibilidad].astype(bool).to_numpy()] = 0
    if (recomendados < minimos).any():
        raise ErrorDatosRecomendacion("Hay franjas con menos despachos que el servicio minimo.")

    filas = []
    for dia, posiciones in salida.groupby("dia_op", sort=True).indices.items():
        n = recomendados[posiciones]
        d = demanda[posiciones]
        m = minimos[posiciones]
        total_inicial = int(n.sum())
        while n.sum() > capacidad:
            reducibles = n > m
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
    columna_disponibilidad: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bloque, parametros, reglas y factibilidad sobre la prediccion mixta.

    Con ``columna_disponibilidad`` (ver ``disponibilidad_habitual``), las franjas
    fuera de la disponibilidad habitual reciben 0 despachos y no entran al ajuste.
    """
    franjas = prediccion.copy()
    horas = franjas["hora"].str.slice(0, 2).astype(int)
    franjas["bloque"] = asignar_bloque(horas, bloques)
    if franjas["bloque"].isna().any():
        raise ErrorDatosRecomendacion("Hay franjas predichas fuera de los bloques horarios.")
    franjas = asociar_parametros(franjas, parametros.tabla)
    franjas = recomendar_despachos(
        franjas, politica_festivos, usar_tope, minimo, columna_disponibilidad=columna_disponibilidad
    )
    return aplicar_factibilidad(
        franjas, parametros.capacidad, minimo, columna_disponibilidad=columna_disponibilidad
    )
