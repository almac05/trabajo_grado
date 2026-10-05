"""Calibra, recomienda y evalua la recomendacion de despacho por franja.

1. Calibracion: cuantiles de pasajeros por despacho y capacidad conjunta en el
   periodo de calibracion; verificacion contra el script 36.
2. Prediccion mixta por regimen sobre las jornadas comunes del freeze;
   verificacion contra la referencia combinada del script 25.
3. Recomendacion y evaluacion en el periodo de evaluacion para las cuatro
   combinaciones de politica de festivos y uso del tope de carga.

Las salidas van a ``reports/tables/dispatch/`` con el sufijo del freeze, junto con
un manifiesto de entradas, parametros y verificaciones.

Uso:
    python scripts/run_recomendacion_despacho.py
    python scripts/run_recomendacion_despacho.py --config configs/dispatch/recomendacion.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from proyecto_grado.dispatch.config import (
    POLITICAS_FESTIVOS,
    ConfiguracionRecomendacion,
    cargar_configuracion_recomendacion,
)
from proyecto_grado.dispatch.evaluacion import (
    construir_franjas_evaluacion,
    franjas_reales,
    tabla_clasificacion,
    tabla_comparacion_despachos,
    tabla_jornadas,
)
from proyecto_grado.dispatch.parametros import (
    ParametrosCalibracion,
    calibrar,
    filtrar_periodo,
    preparar_despachos,
    verificar_contra_script_36,
)
from proyecto_grado.dispatch.predictor_mixto import (
    construir_prediccion_mixta,
    verificar_contra_combinada,
)
from proyecto_grado.dispatch.reglas import generar_recomendacion
from proyecto_grado.modeling.config import PROJECT_ROOT

logger = logging.getLogger("run_recomendacion_despacho")

SUFIJO = "recomendacion_despacho"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--config",
        default=None,
        help="YAML de la recomendacion (por defecto configs/dispatch/recomendacion.yaml).",
    )
    parser.add_argument(
        "--config-evaluacion",
        default=None,
        help="YAML comparativo (por defecto configs/modeling/evaluacion_comparativa.yaml).",
    )
    parser.add_argument("--log-level", default="INFO", help="Nivel de registro.")
    return parser.parse_args()


def _relativa(ruta: Path) -> str:
    return ruta.resolve().relative_to(PROJECT_ROOT).as_posix()


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _ruta_salida(config: ConfiguracionRecomendacion, tipo: str, extension: str = "csv") -> Path:
    return config.directorio_salida / f"{tipo}__{SUFIJO}__{config.freeze}.{extension}"


def _evaluar_combinaciones(
    config: ConfiguracionRecomendacion,
    prediccion: pd.DataFrame,
    parametros: ParametrosCalibracion,
    reales: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], list[dict[str, Any]]]:
    tablas: dict[str, list[pd.DataFrame]] = {}
    resumen: list[dict[str, Any]] = []
    orden_bloques = list(config.nombres_bloques)
    for politica, usar_tope in product(POLITICAS_FESTIVOS, (True, False)):
        logger.info("Combinacion: politica=%s, usar_tope=%s.", politica, usar_tope)
        recomendacion, ajuste = generar_recomendacion(
            prediccion,
            parametros,
            config.bloques,
            politica,
            usar_tope,
            config.servicio_minimo,
        )
        franjas, verificacion = construir_franjas_evaluacion(recomendacion, reales)
        clasificacion, matriz = tabla_clasificacion(franjas, orden_bloques)
        jornadas, jornadas_detalle = tabla_jornadas(franjas, ajuste, orden_bloques)
        resultado = {
            "franjas": franjas,
            "ajuste_jornadas": ajuste,
            "comparacion_despachos": tabla_comparacion_despachos(franjas, orden_bloques),
            "clasificacion": clasificacion,
            "matriz_clasificacion": matriz,
            "jornadas": jornadas,
            "jornadas_detalle": jornadas_detalle,
        }
        for nombre, tabla in resultado.items():
            tabla.insert(0, "usar_tope", usar_tope)
            tabla.insert(0, "politica_festivos", politica)
            tablas.setdefault(nombre, []).append(tabla)
        resumen.append(
            {
                "politica_festivos": politica,
                "usar_tope": usar_tope,
                "configurada": (
                    politica == config.politica_festivos and usar_tope == config.usar_tope_carga
                ),
                "union_operacion_real": verificacion,
                "jornadas": len(ajuste),
                "jornadas_ajustadas": int(ajuste["ajustada"].sum()),
                "jornadas_no_factibles": int((~ajuste["factible"]).sum()),
                "despachos_retirados": int(ajuste["retirados"].sum()),
                "despachos_recomendados": int(franjas["despachos_recomendados"].sum()),
                "despachos_reales": int(franjas["despachos_real"].sum()),
                "franjas_bajo_minimo": int(
                    (franjas["despachos_recomendados"] < config.servicio_minimo).sum()
                ),
            }
        )
    return {
        nombre: pd.concat(partes, ignore_index=True) for nombre, partes in tablas.items()
    }, resumen


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    config = cargar_configuracion_recomendacion(args.config, args.config_evaluacion)
    entradas = config.entradas

    logger.info("Leyendo despachos y tipo de dia por franja.")
    model_ready = pd.read_parquet(
        entradas["model_ready"],
        columns=["FK_RUTA", "HORA_INICIAL_REAL", config.columna_pasajeros, "MODEL_READY_OK"],
    )
    tipo_dia = pd.read_parquet(
        entradas["dataset_modelado"], columns=["FK_RUTA", "timestamp", "tipo_dia"]
    )
    despachos = preparar_despachos(
        model_ready, tipo_dia, config.bloques, config.tipos_raros, config.columna_pasajeros
    )
    calibracion = filtrar_periodo(despachos, config.inicio_calibracion, config.fin_calibracion)
    evaluacion = filtrar_periodo(despachos, config.inicio_evaluacion, config.fin_evaluacion)
    logger.info(
        "Despachos aptos: %d; calibracion: %d (%d jornadas); evaluacion: %d (%d jornadas).",
        len(despachos),
        len(calibracion),
        calibracion["dia_op"].nunique(),
        len(evaluacion),
        evaluacion["dia_op"].nunique(),
    )

    parametros = calibrar(calibracion, config.bloques)
    verificacion_36 = verificar_contra_script_36(
        parametros.tabla, pd.read_csv(entradas["distribucion_script_36"]), config.bloques
    )

    prediccion = construir_prediccion_mixta(
        pd.read_csv(entradas["predicciones_xgboost"]),
        pd.read_csv(entradas["predicciones_referencia"]),
        pd.read_csv(entradas["jornadas_comunes"]),
        config.tipos_raros,
        config.columna_prediccion_ordinaria,
        config.columna_prediccion_rara,
    )
    verificacion_combinada = verificar_contra_combinada(
        prediccion, pd.read_csv(entradas["observaciones_combinada"])
    )

    tablas, resumen = _evaluar_combinaciones(
        config, prediccion, parametros, franjas_reales(evaluacion)
    )

    config.directorio_salida.mkdir(parents=True, exist_ok=True)
    salidas = {
        "parametros": parametros.tabla,
        "verificacion_script_36": verificacion_36,
        "prediccion_mixta": prediccion,
        **tablas,
    }
    rutas_salida = []
    for tipo, tabla in salidas.items():
        ruta = _ruta_salida(config, tipo)
        tabla.to_csv(ruta, index=False)
        rutas_salida.append(_relativa(ruta))
        logger.info("Escrito %s (%d filas).", _relativa(ruta), len(tabla))

    ruta_manifiesto = _ruta_salida(config, "manifiesto", "json")
    por_corte = verificacion_36.groupby("corte_36")["coincide_mediana_q3"]
    manifiesto = {
        "script": "scripts/run_recomendacion_despacho.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "freeze": config.freeze,
        "entradas": {
            nombre: {"ruta": _relativa(ruta), "sha256": _sha256(ruta)}
            for nombre, ruta in entradas.items()
        },
        "parametros": {
            "columna_pasajeros": config.columna_pasajeros,
            "columna_prediccion_ordinaria": config.columna_prediccion_ordinaria,
            "columna_prediccion_rara": config.columna_prediccion_rara,
            "periodo_calibracion": [str(config.inicio_calibracion), str(config.fin_calibracion)],
            "periodo_evaluacion": [str(config.inicio_evaluacion), str(config.fin_evaluacion)],
            "tipos_raros": list(config.tipos_raros),
            "bloques": {b.nombre: b.hora_inicio for b in config.bloques},
            "politica_festivos_configurada": config.politica_festivos,
            "usar_tope_configurado": config.usar_tope_carga,
            "servicio_minimo": config.servicio_minimo,
            "capacidad": parametros.capacidad,
            "jornada_capacidad": str(parametros.jornada_capacidad),
            "despachos_calibracion": len(calibracion),
            "jornadas_calibracion": int(calibracion["dia_op"].nunique()),
            "despachos_evaluacion": len(evaluacion),
            "despachos_tipo_dia_de_la_jornada": {
                "calibracion": int((calibracion["tipo_dia_fuente"] == "jornada").sum()),
                "evaluacion": int((evaluacion["tipo_dia_fuente"] == "jornada").sum()),
            },
            "tabla": parametros.tabla.to_dict("records"),
        },
        "verificaciones": {
            "script_36": {
                corte: {
                    "celdas": int(serie.size),
                    "coinciden_mediana_q3": int(serie.sum()),
                    "max_abs_dif_mediana": float(
                        verificacion_36.loc[serie.index, "dif_mediana"].abs().max()
                    ),
                    "max_abs_dif_q3": float(verificacion_36.loc[serie.index, "dif_q3"].abs().max()),
                }
                for corte, serie in por_corte
            },
            "referencia_combinada": verificacion_combinada,
            "fuentes_prediccion": prediccion["fuente"].value_counts().to_dict(),
            "combinaciones": resumen,
        },
        "salidas": [*rutas_salida, _relativa(ruta_manifiesto)],
    }
    ruta_manifiesto.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    logger.info("Manifiesto: %s", _relativa(ruta_manifiesto))


if __name__ == "__main__":
    main()
