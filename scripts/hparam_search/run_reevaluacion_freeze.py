"""Reejecuta la evaluacion comparativa (periodo canonico 2026-04-02 a
2026-06-10) aplicando a cada metodo la configuracion seleccionada por la
busqueda de hiperparametros, bajo un freeze nuevo (no sobrescribe el
anterior), y consolida metricas globales/por ruta/por tipo de dia/por
regimen sobre el soporte comun de los seis metodos.

No modifica ningun script de evaluacion comparativa existente.

Uso:
    python scripts/hparam_search/run_reevaluacion_freeze.py
"""

from __future__ import annotations

import json

import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.hparam_search.consolidacion_freeze_nuevo import (
    consolidar_freeze_nuevo,
)
from proyecto_grado.modeling.hparam_search.reevaluacion import ejecutar_freeze_nuevo

DIRECTORIO_SELECCION = PROJECT_ROOT / "analisis" / "salidas" / "busqueda_hiperparametros"
SALIDA = PROJECT_ROOT / "analisis" / "salidas"
JORNADAS_ANTERIORES = SALIDA / "referencia_jornadas_pre_consolidacion.csv"


def _soporte_anterior() -> set[tuple]:
    anteriores = pd.read_csv(JORNADAS_ANTERIORES)
    anteriores["dia_op"] = pd.to_datetime(anteriores["dia_op"]).dt.date
    return set(zip(anteriores["route"], anteriores["dia_op"], strict=False))


def main() -> None:
    resultado = ejecutar_freeze_nuevo(DIRECTORIO_SELECCION)
    freeze = resultado["freeze"]
    config = resultado["config"]

    print(f"\n{'#' * 60}\nFreeze nuevo: {freeze}\n{'#' * 60}")

    consolidado = consolidar_freeze_nuevo(freeze, config)
    comun_nuevo = consolidado["soporte_comun"]
    comun_anterior = _soporte_anterior()

    for nombre, tabla in (
        ("global", consolidado["global"]),
        ("regimen", consolidado["por_regimen"]),
        ("tipo_dia", consolidado["por_tipo_dia"]),
    ):
        ruta = SALIDA / f"metricas__comparacion_modelos__{freeze}__{nombre}.csv"
        tabla.round(4).to_csv(ruta, index=False)
        print(f"\n=== {nombre} ===")
        print(tabla.round(2).to_string(index=False))
        print(f"guardado: {ruta}")

    ruta_por_ruta = SALIDA / f"metricas__comparacion_modelos__{freeze}__por_ruta.csv"
    consolidado["por_ruta"].round(4).to_csv(ruta_por_ruta, index=False)
    print("\n=== por_ruta ===")
    print(consolidado["por_ruta"].round(2).to_string(index=False))
    print(f"guardado: {ruta_por_ruta}")

    ruta_soporte = SALIDA / f"jornadas_comunes__{freeze}.csv"
    pd.DataFrame(sorted(comun_nuevo), columns=["route", "dia_op"]).to_csv(ruta_soporte, index=False)

    print(f"\n{'#' * 60}\nSoporte comun\n{'#' * 60}")
    print(f"Freeze anterior (freeze_20260823_203700): {len(comun_anterior)} jornadas comunes")
    print(f"Freeze nuevo ({freeze}): {len(comun_nuevo)} jornadas comunes")
    if comun_nuevo == comun_anterior:
        print("Sin cambios: el soporte comun es identico al del freeze anterior.")
    else:
        solo_antes = comun_anterior - comun_nuevo
        solo_ahora = comun_nuevo - comun_anterior
        print(
            f"Cambio detectado: {len(solo_antes)} jornadas salieron del soporte, "
            f"{len(solo_ahora)} jornadas nuevas entraron."
        )
        if solo_antes:
            print("Salieron:", sorted(solo_antes)[:20], "..." if len(solo_antes) > 20 else "")
        if solo_ahora:
            print("Entraron:", sorted(solo_ahora)[:20], "..." if len(solo_ahora) > 20 else "")

    resumen_ejecucion = {
        "freeze": freeze,
        "n_jornadas_comunes": len(comun_nuevo),
        "n_jornadas_comunes_freeze_anterior": len(comun_anterior),
        "artefactos": {
            metodo: {k: str(v) for k, v in paths.items()}
            for metodo, paths in resultado["artefactos"].items()
        },
    }
    ruta_manifiesto = SALIDA / f"manifiesto__reevaluacion__{freeze}.json"
    with ruta_manifiesto.open("w", encoding="utf-8") as f:
        json.dump(resumen_ejecucion, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nManifiesto: {ruta_manifiesto}")


if __name__ == "__main__":
    main()
