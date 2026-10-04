"""Orquesta la busqueda aleatoria de un metodo: muestrea configuraciones,
evalua cada una sobre el periodo de validacion con el mismo protocolo de
particiones/reentrenamiento de la evaluacion comparativa, selecciona por MAE
global y persiste los tres artefactos exigidos (espacio, tabla completa,
configuracion seleccionada).
"""

from __future__ import annotations

import pandas as pd

from proyecto_grado.modeling.hparam_search.metrics import metricas_configuracion
from proyecto_grado.modeling.hparam_search.persist import (
    guardar_configuracion_seleccionada,
    guardar_espacio_busqueda,
    guardar_tabla_configuraciones,
)
from proyecto_grado.modeling.hparam_search.runner import evaluar_configuracion
from proyecto_grado.modeling.hparam_search.search_config import (
    ConfiguracionBusquedaHiperparametros,
)
from proyecto_grado.modeling.hparam_search.spaces import muestrear_configuraciones


def _aplanar_metricas(prefijo: str, metricas: dict) -> dict:
    if not metricas:
        return {}
    return {f"{prefijo}_{clave}": valor for clave, valor in metricas.items()}


def ejecutar_busqueda(
    metodo: str,
    config: ConfiguracionBusquedaHiperparametros,
    df: pd.DataFrame | None = None,
    verbose: bool = True,
) -> dict:
    """Corre la busqueda completa para un metodo y persiste los artefactos.

    Devuelve un dict con la tabla completa (``DataFrame``), la configuracion
    seleccionada y las rutas de los artefactos persistidos.
    """
    import time

    if df is None:
        df = pd.read_parquet(config.evaluacion.ruta_dataset)

    configuraciones = muestrear_configuraciones(metodo, config.n_iter, config.semilla)

    filas = []
    for indice, params in enumerate(configuraciones):
        t0 = time.perf_counter()
        observaciones, segundos = evaluar_configuracion(metodo, params, config, df=df)
        metricas = metricas_configuracion(observaciones, config.evaluacion.umbral_mape)

        fila = {
            "trial": indice,
            **params,
            "mae_global": metricas["global"].get("mae"),
            "sesgo_global": metricas["global"].get("sesgo"),
            "rmse_global": metricas["global"].get("rmse"),
            "wape_global": metricas["global"].get("wape"),
            "n_jornadas": metricas["n_jornadas"],
            "segundos": segundos,
        }
        for ruta, m in metricas["por_ruta"].items():
            fila[f"mae_ruta_{ruta}"] = m["mae"]
            fila[f"sesgo_ruta_{ruta}"] = m["sesgo"]
        for tipo, m in metricas["por_tipo_dia"].items():
            fila[f"mae_tipo_{tipo}"] = m["mae"]
            fila[f"sesgo_tipo_{tipo}"] = m["sesgo"]
        filas.append(fila)

        if verbose:
            print(
                f"[{metodo}] trial {indice + 1}/{len(configuraciones)} "
                f"MAE={fila['mae_global']:.3f} sesgo={fila['sesgo_global']:+.3f} "
                f"({time.perf_counter() - t0:.1f}s) params={params}"
            )

    tabla = pd.DataFrame(filas)
    if tabla["mae_global"].isna().all():
        raise ValueError(
            f"Ninguna configuracion de {metodo} produjo observaciones validas "
            "en el periodo de validacion."
        )
    mejor_indice = tabla["mae_global"].idxmin()
    mejor = tabla.loc[mejor_indice].to_dict()

    directorio = config.directorio_salida
    ruta_espacio = guardar_espacio_busqueda(metodo, config.n_iter, config.semilla, directorio)
    ruta_tabla = guardar_tabla_configuraciones(metodo, tabla, directorio)
    ruta_seleccion = guardar_configuracion_seleccionada(
        metodo,
        {
            "metodo": metodo,
            "criterio_seleccion": "mae_global (unico criterio)",
            "n_iter": config.n_iter,
            "semilla": config.semilla,
            "periodo_validacion": {
                "inicio": str(config.inicio_validacion),
                "fin": str(config.fin_validacion),
            },
            "trial_seleccionado": mejor,
        },
        directorio,
    )

    return {
        "tabla": tabla,
        "mejor": mejor,
        "artefactos": {
            "espacio": ruta_espacio,
            "tabla": ruta_tabla,
            "seleccion": ruta_seleccion,
        },
    }
