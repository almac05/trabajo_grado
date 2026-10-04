"""Funcion de autocorrelacion de la demanda operativa, con regiones de rezago
senaladas.

Extiende a `07_acf_operativo.py` (que solo genera el diagnostico exploratorio
ACF/PACF con rezagos 1-60) con una figura enfocada en los rezagos citados en
el capitulo de modelado (12-16 y 26-29, este ultimo el que sustenta s=27 en
SARIMA), bandas de confianza al 95%, y una tabla CSV trazable de los valores
de ACF por rezago.

No depende de ningun artefacto de prediccion ni de ningun freeze de
evaluacion: opera directamente sobre la serie de demanda del parquet de
modelado. Los artefactos se nombran con la fecha del freeze del dataset de
origen (embebida en su columna `dataset_version`), no con el freeze de una
corrida de evaluacion.

Uso:
    python analisis/24_acf_demanda_regiones.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: necesario para guardar sin mostrar

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.graphics.tsaplots import plot_acf  # noqa: E402
from statsmodels.tsa.stattools import acf  # noqa: E402

from proyecto_grado.etl.config import PROJECT_ROOT  # noqa: E402

PARQUET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
)
TARGET = "pasajeros_total"
LAGS = 35
RUTAS = (1, 3)
REGION_ONDULACION = (12, 16)
REGION_ESTACIONAL = (26, 29)

SALIDA_TABLAS = PROJECT_ROOT / "analisis" / "salidas"
SALIDA_FIGURAS = PROJECT_ROOT / "reports" / "figures" / "modeling"
SALIDA_TABLAS.mkdir(parents=True, exist_ok=True)
SALIDA_FIGURAS.mkdir(parents=True, exist_ok=True)

# Misma paleta que scripts/build_xgboost_figures.py: apta para escala de
# grises, color combinado con marcador para distinguir series.
ESTILOS = {
    1: {"color": "#1f3b57", "marker": "o"},
    3: {"color": "#8a8580", "marker": "s"},
}
COLOR_REGION_ONDULACION = "#c9a227"
COLOR_REGION_ESTACIONAL = "#2e7d5b"

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    }
)


def _version_dataset(df: pd.DataFrame) -> str:
    valores = df["dataset_version"].unique()
    if len(valores) != 1:
        raise ValueError(f"dataset_version no es unica en el parquet: {valores!r}")
    return str(valores[0])


def _restringir_operativo(df: pd.DataFrame, ruta: int) -> pd.DataFrame:
    """Mismo criterio que 07_acf_operativo.py y los scripts de evaluacion
    comparativa: solo observaciones de la ruta con conteo de pasajeros no
    nulo, es decir, franjas con operacion registrada."""
    return df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].sort_values("timestamp")


def main() -> None:
    df = pd.read_parquet(PARQUET)
    version = _version_dataset(df)
    fecha_parquet = version.replace("freeze_", "").split("_")[0]  # AAAAMMDD

    tabla_filas = []
    resumen_reporte = []

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)

    for ax, ruta in zip(axes, RUTAS, strict=False):
        d = _restringir_operativo(df, ruta)
        s = d[TARGET]
        estilo = ESTILOS[ruta]

        mediana_franjas = (
            d.groupby((d["timestamp"] - pd.Timedelta(hours=4)).dt.date).size().median()
        )

        valores, confint = acf(s, nlags=LAGS, alpha=0.05, fft=False)
        for k in range(1, LAGS + 1):
            tabla_filas.append({
                "route": ruta,
                "lag": k,
                "acf": valores[k],
                "ic95_inferior": confint[k, 0] - valores[k],
                "ic95_superior": confint[k, 1] - valores[k],
            })

        region_2629 = {k: valores[k] for k in range(REGION_ESTACIONAL[0], REGION_ESTACIONAL[1] + 1)}
        lag_max_2629 = max(region_2629, key=region_2629.get)
        max_2629 = region_2629[lag_max_2629]

        region_1216 = {k: valores[k] for k in range(REGION_ONDULACION[0], REGION_ONDULACION[1] + 1)}

        resumen_reporte.append({
            "route": ruta,
            "mediana_franjas_por_jornada": mediana_franjas,
            "lag_max_26_29": lag_max_2629,
            "max_26_29": max_2629,
            "region_12_16": region_1216,
        })

        plot_acf(
            s,
            ax=ax,
            lags=LAGS,
            alpha=0.05,
            fft=False,
            title=None,
            color=estilo["color"],
            vlines_kwargs={"colors": estilo["color"], "linewidth": 1.3},
        )
        for line in ax.lines:
            line.set_color(estilo["color"])
        for coll in ax.collections:
            coll.set_facecolor(estilo["color"])
            coll.set_alpha(0.15)

        ax.axvspan(
            REGION_ONDULACION[0] - 0.5, REGION_ONDULACION[1] + 0.5,
            color=COLOR_REGION_ONDULACION, alpha=0.15, zorder=0,
            label="Rezagos 12-16" if ruta == RUTAS[0] else None,
        )
        ax.axvspan(
            REGION_ESTACIONAL[0] - 0.5, REGION_ESTACIONAL[1] + 0.5,
            color=COLOR_REGION_ESTACIONAL, alpha=0.15, zorder=0,
            label="Rezagos 26-29" if ruta == RUTAS[0] else None,
        )

        ax.annotate(
            f"max={max_2629:.3f}\n(rezago {lag_max_2629})",
            xy=(lag_max_2629, max_2629),
            xytext=(lag_max_2629 - 1, max_2629 + 0.09),
            fontsize=9.5,
            color=COLOR_REGION_ESTACIONAL,
            arrowprops={"arrowstyle": "->", "color": COLOR_REGION_ESTACIONAL, "lw": 1.0},
        )

        ax.set_title(f"Ruta {ruta}")
        ax.set_xlabel("Rezago (franjas de 30 min)")
        ax.set_xlim(0, LAGS + 1)

    axes[0].set_ylabel("ACF")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04), frameon=False)
    fig.suptitle(
        "Autocorrelación de la demanda operativa (franjas de 30 min)",
        y=1.12, fontsize=12,
    )
    fig.tight_layout()

    ruta_figura = SALIDA_FIGURAS / f"acf_demanda_operativa_{fecha_parquet}.png"
    fig.savefig(ruta_figura)
    plt.close(fig)

    tabla = pd.DataFrame(tabla_filas)
    ruta_tabla = SALIDA_TABLAS / f"acf_demanda_operativa_{fecha_parquet}.csv"
    tabla.round(6).to_csv(ruta_tabla, index=False)

    # --- Reporte ---
    print(f"Parquet de origen: {PARQUET}")
    print(f"dataset_version: {version}")
    print(f"Criterio de restriccion a franjas operativas: FK_RUTA == ruta y "
          f"{TARGET}.notna() (excluye franjas sin operacion registrada)")
    print(f"Figura: {ruta_figura}")
    print(f"Tabla: {ruta_tabla}\n")

    citados = {1: 0.243, 3: 0.358}
    for fila in resumen_reporte:
        ruta = fila["route"]
        print(f"--- Ruta {ruta} ---")
        print(f"Mediana de franjas operativas por jornada: {fila['mediana_franjas_por_jornada']:.1f}")
        print(f"Max ACF en rezagos 26-29: {fila['max_26_29']:.4f} en rezago {fila['lag_max_26_29']}")
        cita = citados[ruta]
        diferencia = fila["max_26_29"] - cita
        coincide = "si" if abs(diferencia) < 1e-3 else "no"
        print(f"  Cifra citada en el borrador: {cita} -> coincide: {coincide} "
              f"(diferencia {diferencia:+.4f})")
        print(f"Region rezagos 12-16: "
              + ", ".join(f"{k}={v:.3f}" for k, v in fila["region_12_16"].items()))
        valores_1216 = list(fila["region_12_16"].values())
        hay_ondulacion = (
            max(valores_1216) > valores_1216[0] and max(valores_1216) > valores_1216[-1]
        )
        print(f"  Ondulacion local (maximo interior a la region): {'si' if hay_ondulacion else 'no'}")
        print()


if __name__ == "__main__":
    main()
