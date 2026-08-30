"""Agregacion estricta de metricas sobre predicciones ya almacenadas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT, file_sha256
from proyecto_grado.modeling.evaluation_config import (
    ConfiguracionEvaluacionComparativa,
    validar_nombre_predicciones,
)

CLAVES_FRANJA = ["route", "dia_op", "hora"]
CLAVES_JORNADA = ["route", "dia_op"]
METODOS_EQUIVALENCIA = ("SARIMA", "Prophet", "XGBoost", "LSTM", "CNN-LSTM")
COLUMNAS_METRICAS = (
    "n",
    "demanda_media",
    "mae",
    "rmse",
    "wape",
    "sesgo",
    "mape_parcial",
    "n_mape",
)


class ErrorValidacionProcedencia(RuntimeError):  # noqa: N818
    """Indica que un artefacto no satisface el contrato de procedencia."""


@dataclass(frozen=True)
class FuentePrediccion:
    """Fuente declarada para un metodo o una referencia auxiliar."""

    nombre: str
    identificador_artefacto: str
    artefacto: Path
    artefacto_original: Path
    columna_prediccion: str
    es_referencia: bool


@dataclass
class ResultadoAgregacion:
    """Tablas y evidencia producidas por una agregacion valida."""

    global_sin_redondear: pd.DataFrame
    regimen_sin_redondear: pd.DataFrame
    tipo_dia_sin_redondear: pd.DataFrame
    global_interseccion_anterior: pd.DataFrame
    jornadas_comunes: set[tuple[int, object]]
    jornadas_anteriores: set[tuple[int, object]]
    max_diferencia_equivalencia: float
    comparacion_referencias: pd.DataFrame
    manifiesto: pd.DataFrame


def _ruta_relativa(ruta: Path) -> str:
    try:
        return ruta.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return ruta.as_posix()


def construir_fuentes(config: ConfiguracionEvaluacionComparativa) -> list[FuentePrediccion]:
    """Construye las seis fuentes obligatorias y las dos referencias."""
    fuentes = [
        FuentePrediccion(
            nombre=nombre,
            identificador_artefacto=metodo.identificador,
            artefacto=metodo.artefacto_predicciones,
            artefacto_original=metodo.artefacto_original,
            columna_prediccion=metodo.columna_prediccion,
            es_referencia=False,
        )
        for nombre, metodo in config.metodos.items()
    ]
    fuentes.extend(
        FuentePrediccion(
            nombre=nombre,
            identificador_artefacto=referencia.metodo_fuente,
            artefacto=referencia.artefacto,
            artefacto_original=referencia.artefacto_original,
            columna_prediccion=referencia.columna_prediccion,
            es_referencia=True,
        )
        for nombre, referencia in config.referencias.items()
    )
    return fuentes


def validar_version_dataset(
    config: ConfiguracionEvaluacionComparativa,
) -> tuple[str, int]:
    """Comprueba la version interna del Parquet y devuelve su hash y fecha."""
    ruta = config.ruta_dataset
    if not ruta.is_file():
        raise ErrorValidacionProcedencia(f"No existe el dataset declarado: {ruta}.")
    try:
        versiones = pd.read_parquet(ruta, columns=["dataset_version"])["dataset_version"].dropna()
    except Exception as exc:
        raise ErrorValidacionProcedencia(
            f"No se pudo leer dataset_version del Parquet {ruta}."
        ) from exc
    unicas = set(versiones.astype(str).unique())
    if unicas != {config.dataset_version}:
        raise ErrorValidacionProcedencia(
            "La version esperada no coincide con dataset_version del Parquet: "
            f"esperada={config.dataset_version}, observadas={sorted(unicas)}."
        )
    return file_sha256(ruta), ruta.stat().st_mtime_ns


def cargar_fechas_originales(config: ConfiguracionEvaluacionComparativa) -> pd.DataFrame:
    """Carga el registro inmutable capturado antes de los movimientos."""
    ruta = config.registro_fechas_originales
    if not ruta.is_file():
        raise ErrorValidacionProcedencia(f"Falta el registro de fechas originales: {ruta}.")
    fechas = pd.read_csv(ruta)
    requeridas = {
        "artefacto",
        "fecha_modificacion_original_utc",
        "fecha_modificacion_original_ns",
    }
    faltantes = requeridas - set(fechas.columns)
    if faltantes:
        raise ErrorValidacionProcedencia(f"El registro de fechas no contiene {sorted(faltantes)}.")
    if fechas["artefacto"].duplicated().any():
        raise ErrorValidacionProcedencia("El registro contiene artefactos duplicados.")
    fechas = fechas.copy()
    fechas["fecha_modificacion_original_ns"] = pd.to_numeric(
        fechas["fecha_modificacion_original_ns"], errors="raise"
    ).astype("int64")
    return fechas.set_index("artefacto", drop=False)


def validar_claves_unicas(datos: pd.DataFrame, nombre: str) -> None:
    """Rechaza claves duplicadas por ruta, jornada y franja."""
    faltantes = set(CLAVES_FRANJA) - set(datos.columns)
    if faltantes:
        raise ErrorValidacionProcedencia(
            f"{nombre} no contiene las claves requeridas {sorted(faltantes)}."
        )
    duplicadas = datos.duplicated(CLAVES_FRANJA, keep=False)
    if duplicadas.any():
        muestra = datos.loc[duplicadas, CLAVES_FRANJA].head(5).to_dict("records")
        raise ErrorValidacionProcedencia(
            f"{nombre} contiene claves duplicadas por ruta, jornada y franja: {muestra}."
        )


def cargar_fuente(
    fuente: FuentePrediccion,
    config: ConfiguracionEvaluacionComparativa,
    fechas: pd.DataFrame,
    fecha_dataset_ns: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Valida y carga una fuente sin omitir silenciosamente ningun defecto."""
    validar_nombre_predicciones(
        fuente.artefacto, fuente.identificador_artefacto, config.dataset_version
    )
    if not fuente.artefacto.is_file():
        tipo = "referencia" if fuente.es_referencia else "metodo obligatorio"
        raise ErrorValidacionProcedencia(
            f"Falta el artefacto del {tipo} {fuente.nombre}: {fuente.artefacto}."
        )

    original = _ruta_relativa(fuente.artefacto_original)
    if original not in fechas.index:
        raise ErrorValidacionProcedencia(
            f"No existe fecha original registrada para {fuente.nombre}: {original}."
        )
    registro = fechas.loc[original]
    fecha_original_ns = int(registro["fecha_modificacion_original_ns"])
    if fecha_original_ns < fecha_dataset_ns:
        raise ErrorValidacionProcedencia(
            f"El artefacto de {fuente.nombre} es anterior al dataset segun la fecha "
            f"registrada: {registro['fecha_modificacion_original_utc']}."
        )

    datos_originales = pd.read_csv(fuente.artefacto)
    requeridas = {"route", "dia_op", "hora", "tipo_dia", "real", fuente.columna_prediccion}
    faltantes = requeridas - set(datos_originales.columns)
    if faltantes:
        raise ErrorValidacionProcedencia(
            f"{fuente.artefacto.name} no contiene las columnas {sorted(faltantes)}."
        )
    validar_claves_unicas(datos_originales, fuente.artefacto.name)

    datos = datos_originales[
        datos_originales["real"].notna() & datos_originales[fuente.columna_prediccion].notna()
    ].copy()
    try:
        datos["dia_op"] = pd.to_datetime(datos["dia_op"], errors="raise").dt.date
    except (TypeError, ValueError) as exc:
        raise ErrorValidacionProcedencia(
            f"{fuente.artefacto.name} contiene jornadas invalidas."
        ) from exc
    if datos.empty:
        raise ErrorValidacionProcedencia(
            f"{fuente.artefacto.name} no contiene predicciones validas."
        )

    evidencia = {
        "artefacto": _ruta_relativa(fuente.artefacto),
        "artefacto_original": original,
        "fecha_modificacion_original_utc": registro["fecha_modificacion_original_utc"],
        "fecha_modificacion_original_ns": fecha_original_ns,
        "filas": len(datos_originales),
        "jornada_min": min(datos["dia_op"]).isoformat(),
        "jornada_max": max(datos["dia_op"]).isoformat(),
    }
    return datos, evidencia


def calcular_metricas(
    real: np.ndarray, pred: np.ndarray, umbral_mape: float
) -> dict[str, float | int]:
    """Calcula indicadores sobre observaciones, sin promediar por jornada."""
    error = pred - real
    absoluto = np.abs(error)
    mascara = real >= umbral_mape
    mape = 100 * np.mean(absoluto[mascara] / real[mascara]) if mascara.any() else np.nan
    return {
        "n": len(real),
        "demanda_media": real.mean(),
        "mae": absoluto.mean(),
        "rmse": np.sqrt(np.mean(error**2)),
        "wape": 100 * absoluto.sum() / real.sum(),
        "sesgo": error.mean(),
        "mape_parcial": mape,
        "n_mape": int(mascara.sum()),
    }


def calcular_tablas(
    datos: dict[str, tuple[pd.DataFrame, str]],
    jornadas: set[tuple[int, object]],
    config: ConfiguracionEvaluacionComparativa,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calcula las tres desagregaciones sobre un conjunto explicito."""
    filas_global: list[dict[str, object]] = []
    filas_regimen: list[dict[str, object]] = []
    filas_tipo: list[dict[str, object]] = []
    for nombre, (datos_fuente, columna) in datos.items():
        mascara = [
            (ruta, dia) in jornadas
            for ruta, dia in zip(datos_fuente["route"], datos_fuente["dia_op"], strict=False)
        ]
        seleccion = datos_fuente[mascara].copy()
        seleccion["regimen"] = (
            seleccion["tipo_dia"]
            .isin(config.tipos_baja_frecuencia)
            .map({True: "raro", False: "ordinario"})
        )

        for ruta, grupo in seleccion.groupby("route"):
            filas_global.append(
                {
                    "metodo": nombre,
                    "route": ruta,
                    **calcular_metricas(
                        grupo["real"].to_numpy(),
                        grupo[columna].to_numpy(),
                        config.umbral_mape,
                    ),
                }
            )
        for (ruta, regimen), grupo in seleccion.groupby(["route", "regimen"]):
            filas_regimen.append(
                {
                    "metodo": nombre,
                    "route": ruta,
                    "regimen": regimen,
                    **calcular_metricas(
                        grupo["real"].to_numpy(),
                        grupo[columna].to_numpy(),
                        config.umbral_mape,
                    ),
                }
            )
        for (ruta, tipo_dia), grupo in seleccion.groupby(["route", "tipo_dia"]):
            filas_tipo.append(
                {
                    "metodo": nombre,
                    "route": ruta,
                    "tipo_dia": tipo_dia,
                    **calcular_metricas(
                        grupo["real"].to_numpy(),
                        grupo[columna].to_numpy(),
                        config.umbral_mape,
                    ),
                }
            )
    return (
        pd.DataFrame(filas_global),
        pd.DataFrame(filas_regimen),
        pd.DataFrame(filas_tipo),
    )


def cargar_jornadas_anteriores(
    config: ConfiguracionEvaluacionComparativa,
) -> set[tuple[int, object]]:
    """Carga el conjunto exacto capturado antes de consolidar."""
    if not config.jornadas_pre_consolidacion.is_file():
        raise ErrorValidacionProcedencia(
            f"Falta la referencia de jornadas: {config.jornadas_pre_consolidacion}."
        )
    jornadas = pd.read_csv(config.jornadas_pre_consolidacion)
    faltantes = set(CLAVES_JORNADA) - set(jornadas.columns)
    if faltantes:
        raise ErrorValidacionProcedencia(
            f"La referencia de jornadas no contiene {sorted(faltantes)}."
        )
    if jornadas.duplicated(CLAVES_JORNADA).any():
        raise ErrorValidacionProcedencia("La referencia de jornadas contiene duplicados.")
    jornadas["dia_op"] = pd.to_datetime(jornadas["dia_op"], errors="raise").dt.date
    return set(zip(jornadas["route"], jornadas["dia_op"], strict=False))


def _comparar_tabla(
    actual: pd.DataFrame,
    referencia: pd.DataFrame,
    claves: list[str],
    tolerancia: float,
) -> float:
    columnas = [*claves, *COLUMNAS_METRICAS]
    izquierda = actual[columnas].sort_values(claves).reset_index(drop=True)
    derecha = referencia[columnas].sort_values(claves).reset_index(drop=True)
    if not izquierda[claves].equals(derecha[claves]):
        raise ErrorValidacionProcedencia(f"Las claves de equivalencia difieren para {claves}.")
    maximo = 0.0
    for columna in COLUMNAS_METRICAS:
        valores_actuales = pd.to_numeric(izquierda[columna], errors="coerce").to_numpy()
        valores_referencia = pd.to_numeric(derecha[columna], errors="coerce").to_numpy()
        if not np.array_equal(np.isnan(valores_actuales), np.isnan(valores_referencia)):
            raise ErrorValidacionProcedencia(f"La presencia de nulos difiere en {columna}.")
        diferencia = np.abs(valores_actuales - valores_referencia)
        diferencia = diferencia[~np.isnan(diferencia)]
        local = float(diferencia.max()) if len(diferencia) else 0.0
        maximo = max(maximo, local)
    if maximo > tolerancia:
        raise ErrorValidacionProcedencia(
            f"La equivalencia excede la tolerancia {tolerancia}: {maximo}."
        )
    return maximo


def verificar_equivalencia(
    tablas_anteriores: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame],
    config: ConfiguracionEvaluacionComparativa,
    tolerancia: float = 1e-10,
) -> float:
    """Compara cinco metodos y la referencia de 26 semanas con la captura."""
    if not config.metricas_pre_consolidacion.is_file():
        raise ErrorValidacionProcedencia(
            f"Falta la referencia de metricas: {config.metricas_pre_consolidacion}."
        )
    referencia = pd.read_csv(config.metricas_pre_consolidacion)
    nombres_actuales = [*METODOS_EQUIVALENCIA, "Referencia (26s)"]
    referencia = referencia[referencia["metodo"].isin([*METODOS_EQUIVALENCIA, "Referencia"])].copy()
    referencia["metodo"] = referencia["metodo"].replace({"Referencia": "Referencia (26s)"})
    maximos = []
    especificaciones = (
        ("global", tablas_anteriores[0], ["metodo", "route"]),
        ("regimen", tablas_anteriores[1], ["metodo", "route", "regimen"]),
        ("tipo_dia", tablas_anteriores[2], ["metodo", "route", "tipo_dia"]),
    )
    for desagregacion, actual, claves in especificaciones:
        actual = actual[actual["metodo"].isin(nombres_actuales)]
        esperada = referencia[referencia["desagregacion"] == desagregacion]
        maximos.append(_comparar_tabla(actual, esperada, claves, tolerancia))
    return max(maximos, default=0.0)


def comparar_referencias(
    tabla_tipo: pd.DataFrame,
    jornadas: set[tuple[int, object]],
    config: ConfiguracionEvaluacionComparativa,
) -> pd.DataFrame:
    """Anade el conteo almacenado de respaldos a las metricas de dias raros."""
    filas = tabla_tipo[
        tabla_tipo["metodo"].isin(config.referencias)
        & tabla_tipo["tipo_dia"].isin(config.tipos_baja_frecuencia)
    ].copy()
    conteos: list[pd.DataFrame] = []
    metodos_por_id = {m.identificador: m for m in config.metodos.values()}
    for nombre, referencia in config.referencias.items():
        metodo = metodos_por_id[referencia.metodo_fuente]
        if not metodo.artefacto_resumen.is_file():
            raise ErrorValidacionProcedencia(
                f"Falta el resumen requerido para {nombre}: {metodo.artefacto_resumen}."
            )
        resumen = pd.read_csv(metodo.artefacto_resumen)
        requeridas = {"route", "dia_op", "tipo_dia", "celdas_sin_media"}
        faltantes = requeridas - set(resumen.columns)
        if faltantes:
            raise ErrorValidacionProcedencia(
                f"{metodo.artefacto_resumen.name} no contiene {sorted(faltantes)}."
            )
        if resumen.duplicated(CLAVES_JORNADA).any():
            raise ErrorValidacionProcedencia(
                f"{metodo.artefacto_resumen.name} contiene jornadas duplicadas."
            )
        resumen["dia_op"] = pd.to_datetime(resumen["dia_op"], errors="raise").dt.date
        mascara = [
            (ruta, dia) in jornadas
            for ruta, dia in zip(resumen["route"], resumen["dia_op"], strict=False)
        ]
        resumen = resumen[
            np.asarray(mascara) & resumen["tipo_dia"].isin(config.tipos_baja_frecuencia).to_numpy()
        ]
        agrupado = (
            resumen.groupby(["route", "tipo_dia"], as_index=False)["celdas_sin_media"]
            .sum()
            .assign(metodo=nombre)
        )
        conteos.append(agrupado)
    celdas = pd.concat(conteos, ignore_index=True)
    return filas.merge(celdas, on=["metodo", "route", "tipo_dia"], how="left")


def ejecutar_agregacion(
    config: ConfiguracionEvaluacionComparativa,
) -> ResultadoAgregacion:
    """Valida procedencia, calcula metricas y escribe solo salidas agregadas."""
    hash_dataset, fecha_dataset_ns = validar_version_dataset(config)
    fechas = cargar_fechas_originales(config)
    fuentes = construir_fuentes(config)

    datos: dict[str, tuple[pd.DataFrame, str]] = {}
    evidencias: dict[str, dict[str, object]] = {}
    versiones: set[str] = set()
    for fuente in fuentes:
        datos_fuente, evidencia = cargar_fuente(fuente, config, fechas, fecha_dataset_ns)
        datos[fuente.nombre] = (datos_fuente, fuente.columna_prediccion)
        evidencias[fuente.nombre] = evidencia
        versiones.add(fuente.artefacto.name.rsplit("__", maxsplit=1)[1].removesuffix(".csv"))
    if versiones != {config.dataset_version}:
        raise ErrorValidacionProcedencia(
            f"Coexisten versiones distintas en los artefactos seleccionados: {versiones}."
        )

    jornadas_por_fuente = {
        nombre: set(zip(d["route"], d["dia_op"], strict=False)) for nombre, (d, _) in datos.items()
    }
    jornadas_comunes = set.intersection(*jornadas_por_fuente.values())
    if not jornadas_comunes:
        raise ErrorValidacionProcedencia("No existen jornadas comunes entre las fuentes.")

    tablas = calcular_tablas(datos, jornadas_comunes, config)
    jornadas_anteriores = cargar_jornadas_anteriores(config)
    tablas_anteriores = calcular_tablas(datos, jornadas_anteriores, config)
    max_diferencia = verificar_equivalencia(tablas_anteriores, config)
    comparacion = comparar_referencias(tablas[2], jornadas_comunes, config)

    config.directorio_salida.mkdir(parents=True, exist_ok=True)
    for desagregacion, tabla in zip(("global", "regimen", "tipo_dia"), tablas, strict=True):
        tabla.round(2).to_csv(config.ruta_metricas(desagregacion), index=False)

    manifiesto_filas = []
    for nombre, metodo in config.metodos.items():
        evidencia = evidencias[nombre]
        manifiesto_filas.append(
            {
                "metodo": nombre,
                "artefacto": evidencia["artefacto"],
                "dataset_version": config.dataset_version,
                "dataset_sha256": hash_dataset,
                "artefacto_sha256": file_sha256(metodo.artefacto_predicciones),
                "fecha_modificacion_original_utc": evidencia["fecha_modificacion_original_utc"],
                "fecha_modificacion_original_ns": evidencia["fecha_modificacion_original_ns"],
                "filas": evidencia["filas"],
                "jornada_min": evidencia["jornada_min"],
                "jornada_max": evidencia["jornada_max"],
            }
        )
    manifiesto = pd.DataFrame(manifiesto_filas)
    manifiesto.to_csv(config.manifiesto, index=False)

    return ResultadoAgregacion(
        global_sin_redondear=tablas[0],
        regimen_sin_redondear=tablas[1],
        tipo_dia_sin_redondear=tablas[2],
        global_interseccion_anterior=tablas_anteriores[0],
        jornadas_comunes=jornadas_comunes,
        jornadas_anteriores=jornadas_anteriores,
        max_diferencia_equivalencia=max_diferencia,
        comparacion_referencias=comparacion,
        manifiesto=manifiesto,
    )
