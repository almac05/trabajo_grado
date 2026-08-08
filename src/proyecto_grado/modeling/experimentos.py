"""Utilidades compartidas por los experimentos de modelado.

Este modulo concentra tres decisiones que deben ser identicas en todos los
experimentos: que variables se usan como predictoras, como se construyen las
particiones temporales, y como se entrena y evalua un modelo. Mantenerlas en
un unico lugar garantiza que las metricas de distintos experimentos sean
comparables entre si.

No contiene valores especificos de ningun experimento (ventanas, cortes,
hiperparametros): esos se definen en cada script.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import xgboost as xgb

# --- Exclusiones por fuga o inutilidad -------------------------------------

# Constantes dentro de cada archivo: no aportan informacion al modelo.
_CONSTANTES = {
    "dataset_version",
    "source_hash",
    "granularidad_min",
    "target",
    "target_col",
    "scenario",
    "feature_set",
    "observed_flag",
    "FK_RUTA",
}

# Marcas temporales absolutas: los arboles no extrapolan, y toda fecha futura
# queda por encima del ultimo umbral aprendido. La informacion temporal util
# esta codificada en las variables de calendario.
_MARCAS_TEMPORALES = {
    "timestamp",
    "target_interval_start",
    "target_interval_end",
    "feature_cutoff_timestamp",
}

# El objetivo y las variables que permiten reconstruirlo.
_OBJETIVO = {"pasajeros_total", "pasajeros_por_despacho_real"}

# Banderas que describen el resultado de la franja, es decir, parte de lo que
# se predice.
_BANDERAS = {
    "target_observed",
    "target_pasajeros_total_observed",
    "target_pasajeros_por_despacho_observed",
    "is_gap",
    "gap_tipo",
}

# Texto sin codificar: XGBoost no acepta categoricas de texto directamente.
_TEXTO = {"tipo_dia", "franja_horaria"}

# Alias sin prefijo, verificados identicos a las columnas de pasajeros_total.
_ALIAS = {
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_48",
    "lag_96",
    "lag_336",
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_mean_12",
    "rolling_std_6",
    "rolling_std_12",
}

# Calendario anual: con ventanas de aproximadamente un ciclo, cada valor
# identifica un bloque unico de datos e induce memorizacion.
_CALENDARIO_ANUAL = {"semana_anio", "mes"}

# Variables no consolidadas al momento de decidir el despacho: los pasajeros
# de una franja solo se registran cuando el vehiculo termina el recorrido
# (mediana 159 min).
_SUFIJOS_NO_DISPONIBLES = (
    "_lag_1",
    "_lag_2",
    "_lag_3",
    "_rolling_mean_3",
    "_rolling_mean_6",
    "_rolling_mean_12",
    "_rolling_std_6",
    "_rolling_std_12",
)

# --- Seleccion de variables predictoras -------------------------------------


def seleccionar_features(
    d: pd.DataFrame,
    *,
    excluir_oferta: bool = True,
    excluir_calendario_anual: bool = True,
    excluir_no_disponibles: bool = True,
) -> list[str]:
    """Devuelve las columnas utilizables como variables predictoras.

    Las exclusiones por fuga, marcas temporales, banderas de resultado, texto y
    alias duplicados se aplican siempre. Las tres restantes son opcionales,
    porque cada experimento responde una pregunta distinta:

    excluir_oferta
        Variables derivadas del conteo de despachos. Se excluyen en el escenario
        `sin_oferta`; el escenario `oferta_historica_rezagada` las conserva.
    excluir_calendario_anual
        `semana_anio` y `mes`. Con ventanas cercanas a un ciclo anual, cada
        valor identifica un bloque unico de datos e induce memorizacion.
    excluir_no_disponibles
        Rezagos cortos y ventanas moviles construidas sobre ellos. No estan
        consolidados en el momento de decidir el despacho.
    """
    excluir = _CONSTANTES | _MARCAS_TEMPORALES | _OBJETIVO | _BANDERAS | _TEXTO | _ALIAS

    if excluir_oferta:
        excluir |= {c for c in d.columns if c.startswith("despachos_count_real")}
    if excluir_calendario_anual:
        excluir |= _CALENDARIO_ANUAL
    if excluir_no_disponibles:
        excluir |= {c for c in d.columns if c.endswith(_SUFIJOS_NO_DISPONIBLES)}

    return [c for c in d.columns if c not in excluir and pd.api.types.is_numeric_dtype(d[c])]


# --- Particiones temporales -------------------------------------------------


@dataclass(frozen=True)
class Particion:
    """Los tres bloques temporales de un experimento.

    ajuste
        Observaciones con las que el modelo construye sus arboles.
    parada
        Ultimas semanas antes del corte. Solo se usan para decidir cuando
        detener el entrenamiento; el modelo no aprende de ellas.
    evaluacion
        Posterior al corte. No interviene en ninguna decision de entrenamiento,
        de modo que sus metricas son una estimacion insesgada del desempeno.
    """

    ajuste: pd.DataFrame
    parada: pd.DataFrame
    evaluacion: pd.DataFrame


def particiones_temporales(
    d: pd.DataFrame,
    corte: pd.Timestamp,
    *,
    target: str,
    semanas_entrenamiento: int | None,
    semanas_evaluacion: int = 2,
    semanas_parada: int = 2,
    col_tiempo: str = "timestamp",
) -> Particion:
    """Construye los tres bloques temporales a partir de un corte.

    `semanas_entrenamiento = None` usa todo el historico disponible.

    Los tres bloques son contiguos y no se solapan. Se descartan las filas sin
    valor observado del objetivo, que corresponden a franjas sin operacion.

    Lanza ValueError si la ventana solicitada excede el inicio del conjunto de
    datos: en ese caso el entrenamiento seria mas corto de lo declarado y no
    comparable con el de otros cortes.
    """
    inicio_datos = d[col_tiempo].min()

    if semanas_entrenamiento is None:
        inicio = inicio_datos
    else:
        inicio = corte - pd.Timedelta(weeks=semanas_entrenamiento)
        if inicio < inicio_datos:
            raise ValueError(
                f"La ventana de {semanas_entrenamiento} semanas desde {corte.date()} "
                f"excede el inicio de los datos ({inicio_datos.date()})."
            )

    corte_parada = corte - pd.Timedelta(weeks=semanas_parada)
    fin_evaluacion = corte + pd.Timedelta(weeks=semanas_evaluacion)

    obs = d[d[target].notna()]

    return Particion(
        ajuste=obs[(obs[col_tiempo] >= inicio) & (obs[col_tiempo] < corte_parada)],
        parada=obs[(obs[col_tiempo] >= corte_parada) & (obs[col_tiempo] < corte)],
        evaluacion=obs[(obs[col_tiempo] >= corte) & (obs[col_tiempo] < fin_evaluacion)],
    )


# --- Entrenamiento y evaluacion ---------------------------------------------

# Configuracion adoptada tras el barrido de ventanas. Valores conservadores,
# sin optimizacion: la parada temprana detiene el entrenamiento muy por debajo
# del techo de arboles, lo que indica que el modelo converge por si solo.
PARAMS_XGB = {
    "objective": "reg:absoluteerror",  # aprende la mediana condicional
    "eval_metric": "mae",
    "max_depth": 5,
    "min_child_weight": 5,
    "learning_rate": 0.05,
    "n_estimators": 2000,  # techo; decide la parada temprana
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "early_stopping_rounds": 50,
    "random_state": 42,
}

TIPOS_RAROS = ("FESTIVO", "FESTIVO_PUENTE")


def entrenar_y_evaluar(
    particion: Particion,
    features: list[str],
    *,
    target: str,
    params: dict | None = None,
) -> tuple[pd.DataFrame, xgb.XGBRegressor]:
    """Entrena XGBoost sobre la particion y evalua sobre el bloque reservado.

    Devuelve una copia del bloque de evaluacion con las columnas `y_pred`,
    `error` y `regimen`, junto con el modelo entrenado (necesario para la
    importancia de variables y el numero de arboles seleccionado).

    El error se define como valor predicho menos valor observado: un valor
    positivo indica sobrepredicion.

    Los valores ausentes no se imputan. XGBoost aprende una direccion por
    defecto en cada division, de modo que se conserva la informacion contenida
    en la ausencia: una franja sin rezago disponible es, tipicamente, la
    primera de la jornada.
    """
    modelo = xgb.XGBRegressor(**(params or PARAMS_XGB))
    modelo.fit(
        particion.ajuste[features],
        particion.ajuste[target],
        eval_set=[(particion.parada[features], particion.parada[target])],
        verbose=False,
    )

    ev = particion.evaluacion.copy()
    ev["y_pred"] = modelo.predict(ev[features])
    ev["error"] = ev["y_pred"] - ev[target]
    ev["regimen"] = ev["tipo_dia"].isin(TIPOS_RAROS).map({True: "raro", False: "ordinario"})
    return ev, modelo
