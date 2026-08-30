"""Metricas comparativas sobre seis metodos y dos referencias auxiliares.

Recalcula los indicadores sobre predicciones ya almacenadas, sin reentrenar
ningun modelo. Las seis fuentes obligatorias son SARIMA, Prophet, XGBoost,
LSTM, GRU y CNN-LSTM.

Todos los productores implementan el mismo estimador auxiliar: la media
historica por tipo de dia y franja, con respaldo en la media global cuando no
existe la combinacion. El resultado depende de la profundidad del historico,
por lo cual se publican dos lineas base distintas: Referencia (26s), tomada
del artefacto de XGBoost, y Referencia (52s), tomada del artefacto de GRU.
Estas referencias no se consideran metodos.

La comparacion se restringe a la interseccion de jornadas y calcula las
metricas sobre observaciones, no promediando por jornada. Antes de calcular,
se validan de forma estricta nombres, versiones, columnas, claves unicas,
frescura registrada y procedencia del dataset.

Uso:
    python scripts/aggregate_comparative_metrics.py
"""

from __future__ import annotations

import pandas as pd

from proyecto_grado.modeling.evaluation_aggregation import ejecutar_agregacion
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion

pd.set_option("display.width", 250)


def _mostrar_tablas(resultado, umbral_mape: float) -> None:
    """Imprime tablas completas y evidencia de las verificaciones."""
    glob = resultado.global_sin_redondear.round(2)
    reg = resultado.regimen_sin_redondear.round(2)
    tip = resultado.tipo_dia_sin_redondear.round(2)
    cols = [
        "metodo",
        "route",
        "n",
        "demanda_media",
        "mae",
        "rmse",
        "wape",
        "sesgo",
        "mape_parcial",
    ]

    print("Metodos obligatorios: SARIMA, Prophet, XGBoost, LSTM, GRU, CNN-LSTM")
    print("Lineas base auxiliares: Referencia (26s), Referencia (52s)")
    print(f"Jornadas comunes a las ocho fuentes: {len(resultado.jornadas_comunes)}")
    print(f"Jornadas de la interseccion anterior: {len(resultado.jornadas_anteriores)}")

    entran = sorted(resultado.jornadas_comunes - resultado.jornadas_anteriores)
    salen = sorted(resultado.jornadas_anteriores - resultado.jornadas_comunes)
    print(f"Jornadas que entran: {entran}")
    print(f"Jornadas que salen: {salen}")
    if entran or salen:
        metodos = ["SARIMA", "Prophet", "XGBoost", "LSTM", "GRU", "CNN-LSTM"]
        anterior = resultado.global_interseccion_anterior
        anterior = anterior[anterior["metodo"].isin(metodos)]
        nueva = resultado.global_sin_redondear
        nueva = nueva[nueva["metodo"].isin(metodos)]
        efecto = anterior.merge(
            nueva,
            on=["metodo", "route"],
            suffixes=("_interseccion_anterior", "_interseccion_seis"),
        )
        print("Efecto del cambio de interseccion sobre cada metodo:")
        print(
            efecto[
                [
                    "metodo",
                    "route",
                    "n_interseccion_anterior",
                    "n_interseccion_seis",
                    "mae_interseccion_anterior",
                    "mae_interseccion_seis",
                    "rmse_interseccion_anterior",
                    "rmse_interseccion_seis",
                    "wape_interseccion_anterior",
                    "wape_interseccion_seis",
                ]
            ].to_string(index=False)
        )
    print("Jornadas comunes:")
    print(
        pd.DataFrame(sorted(resultado.jornadas_comunes), columns=["route", "dia_op"]).to_string(
            index=False
        )
    )

    print("\n" + "=" * 110)
    print("METRICAS GLOBALES")
    print(glob[cols].sort_values(["route", "mae"]).to_string(index=False))

    print("\n" + "=" * 110)
    print("POR REGIMEN DE DIA")
    print(
        reg[
            [
                "metodo",
                "route",
                "regimen",
                "n",
                "demanda_media",
                "mae",
                "rmse",
                "wape",
                "sesgo",
            ]
        ]
        .sort_values(["regimen", "route", "mae"])
        .to_string(index=False)
    )

    print("\n" + "=" * 110)
    print("MAE POR TIPO DE DIA")
    print(
        tip.pivot_table(index="metodo", columns=["route", "tipo_dia"], values="mae")
        .round(2)
        .to_string()
    )
    print("\nSESGO POR TIPO DE DIA")
    print(
        tip.pivot_table(index="metodo", columns=["route", "tipo_dia"], values="sesgo")
        .round(2)
        .to_string()
    )

    print("\nREFERENCIAS EN TIPOS DE DIA DE BAJA FRECUENCIA")
    columnas_referencia = [
        "metodo",
        "route",
        "tipo_dia",
        "n",
        "mae",
        "rmse",
        "wape",
        "sesgo",
        "celdas_sin_media",
    ]
    print(
        resultado.comparacion_referencias[columnas_referencia]
        .sort_values(["route", "tipo_dia", "metodo"])
        .round(10)
        .to_string(index=False)
    )

    print(
        f"\nCOBERTURA DEL MAPE (franjas con demanda igual o superior a {umbral_mape:g} pasajeros)"
    )
    cobertura = glob.drop_duplicates(subset=["route"])[["route", "n", "n_mape"]].copy()
    cobertura["pct_cubierto"] = (100 * cobertura["n_mape"] / cobertura["n"]).round(1)
    print(cobertura.to_string(index=False))
    print(
        "\nDiferencia absoluta maxima frente a la captura preconsolidacion: "
        f"{resultado.max_diferencia_equivalencia:.3e}"
    )


def main() -> None:
    """Ejecuta la agregacion; cualquier defecto produce codigo distinto de cero."""
    config = cargar_configuracion_evaluacion()
    resultado = ejecutar_agregacion(config)
    _mostrar_tablas(resultado, config.umbral_mape)
    print(f"\nMetricas guardadas en {config.directorio_salida}")
    print(f"Manifiesto guardado en {config.manifiesto}")


if __name__ == "__main__":
    main()
