"""Construccion y justificacion de la referencia de comparacion (baseline honesto).

Este script documenta, con evidencia sobre los 38 folds de validacion, por que el
promedio movil calibrado sustituye al promedio historico completo como referencia
frente a la cual se evaluaran los modelos de la Fase 3.

Hallazgos que sostiene:
  H1. El promedio historico sobrepredice de forma sistematica en dias ordinarios.
      El sesgo es la mayor parte de su error, no la dispersion.
  H2. En dias ordinarios el sesgo crece de forma monotona con el tamano de ventana W,
      mientras el MAE presenta un minimo interior. Compromiso sesgo-varianza clasico.
  H3. En dias festivos el sesgo decrece de forma monotona con W, en sentido opuesto.
      Las dos fuentes de error se mueven en direcciones contrarias.
  H4. En dias festivos la historia completa es la mejor opcion entre los promedios,
      porque no sufre escasez muestral.
  H5. La eleccion de W se sostiene en comparacion pareada por fold, no en promedios.

Uso:
    python scripts/run_baseline_reference.py --run-id rolling_bias_20260720

Salidas en reports/tables/modeling/ y reports/figures/modeling/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

# --------------------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------------------

TARGET = "pasajeros_total"
ESCENARIO = "sin_oferta"

# Tipos de dia con pocas ocurrencias por ventana. La separacion de regimenes es el
# nucleo del analisis: promediarlos juntos oculta dos efectos de signo opuesto.
TIPOS_RAROS = ("FESTIVO", "FESTIVO_PUENTE")

VENTANAS = {
    "rolling_average_4w": 4,
    "rolling_average_8w": 8,
    "rolling_average_12w": 12,
    "rolling_average_26w": 26,
}
REFERENCIA_ACTUAL = "historical_average_route_day_type_slot"
MODELO_RECOMENDADO = "rolling_average_8w"

# Paleta apta para escala de grises: se combina color con marcador y estilo de linea,
# de modo que las series sigan siendo distinguibles al imprimir en blanco y negro.
ESTILOS = {
    1: {"color": "#1f3b57", "marker": "o", "linestyle": "-"},
    3: {"color": "#8a8580", "marker": "s", "linestyle": "--"},
}

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.labelsize": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.6,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    }
)


# --------------------------------------------------------------------------------------
# Carga y preparacion
# --------------------------------------------------------------------------------------


def cargar_predicciones(ruta: Path) -> pd.DataFrame:
    """Carga el parquet de predicciones y filtra a un unico target y escenario.

    El parquet contiene varias combinaciones de target y escenario apiladas. Mezclarlas
    produciria promedios sin sentido, porque las escalas no son comparables entre si.
    """
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro el parquet de predicciones: {ruta}")

    df = pd.read_parquet(ruta)
    faltantes = {"split", "target", "scenario", "target_observed", "error", "error_abs"} - set(
        df.columns
    )
    if faltantes:
        raise ValueError(f"Faltan columnas esperadas en el parquet: {sorted(faltantes)}")

    filtro = (
        (df["target"] == TARGET)
        & (df["scenario"] == ESCENARIO)
        & (df["target_observed"])  # excluye huecos operativos: y_real es nulo en ellos
    )
    return df.loc[filtro].copy()


def clasificar_regimen(df: pd.DataFrame) -> pd.DataFrame:
    """Anade la columna de regimen: dias ordinarios frente a tipos de dia raros."""
    df = df.copy()
    df["regimen"] = df["tipo_dia"].isin(TIPOS_RAROS).map({True: "raro", False: "ordinario"})
    return df


# --------------------------------------------------------------------------------------
# Metricas
# --------------------------------------------------------------------------------------


def metricas_por_fold(val: pd.DataFrame) -> pd.DataFrame:
    """Calcula MAE y sesgo por (modelo, ruta, regimen, fold).

    Trabajar por fold es lo que permite distinguir una diferencia real entre modelos
    de una fluctuacion del periodo evaluado.
    """
    return (
        val.groupby(["model", "route", "regimen", "fold"], observed=True)
        .agg(
            n=("error", "size"),
            demanda_media=("y_real", "mean"),
            mae=("error_abs", "mean"),
            sesgo=("error", "mean"),
        )
        .reset_index()
    )


def resumen_entre_folds(por_fold: pd.DataFrame) -> pd.DataFrame:
    """Agrega las metricas entre folds, reportando media y dispersion.

    La desviacion entre folds es tan informativa como la media: si supera las
    diferencias entre modelos, la comparacion de medias no discrimina nada.
    """
    resumen = (
        por_fold.groupby(["model", "route", "regimen"], observed=True)
        .agg(
            folds=("fold", "nunique"),
            n_total=("n", "sum"),
            demanda_media=("demanda_media", "mean"),
            mae_medio=("mae", "mean"),
            mae_std=("mae", "std"),
            sesgo_medio=("sesgo", "mean"),
            sesgo_std=("sesgo", "std"),
        )
        .reset_index()
    )
    # Metricas relativas: el MAE absoluto no es comparable entre regimenes, porque la
    # demanda media de un festivo es una fraccion de la de un dia ordinario.
    resumen["mae_pct"] = 100 * resumen["mae_medio"] / resumen["demanda_media"]
    resumen["sesgo_pct"] = 100 * resumen["sesgo_medio"] / resumen["demanda_media"]
    resumen["fraccion_sesgo"] = resumen["sesgo_medio"].abs() / resumen["mae_medio"]
    return resumen.round(3)


def comparaciones_pareadas(por_fold: pd.DataFrame, regimen: str = "ordinario") -> pd.DataFrame:
    """Compara cada par de ventanas fold a fold.

    La comparacion pareada elimina la variabilidad entre folds: en cada fold ambos
    modelos enfrentan exactamente los mismos datos, asi que la diferencia aisla el
    efecto del modelo. La proporcion de folds ganados es mas informativa que la
    diferencia media, porque no la dominan unos pocos folds atipicos.
    """
    sub = por_fold[por_fold["regimen"] == regimen]
    pivot = sub.pivot_table(index=["route", "fold"], columns="model", values=["mae", "sesgo"])

    modelos = list(VENTANAS)
    filas = []
    for metrica in ("mae", "sesgo"):
        tabla = pivot[metrica]
        for i, a in enumerate(modelos):
            for b in modelos[i + 1 :]:
                if a not in tabla or b not in tabla:
                    continue
                # En sesgo comparamos magnitudes: un sesgo de -8 no es mejor que uno de +3.
                serie_a = tabla[a].abs() if metrica == "sesgo" else tabla[a]
                serie_b = tabla[b].abs() if metrica == "sesgo" else tabla[b]
                dif = serie_a - serie_b
                for ruta, grupo in dif.groupby(level="route"):
                    filas.append(
                        {
                            "metrica": metrica,
                            "modelo_a": a,
                            "modelo_b": b,
                            "route": ruta,
                            "n_folds": int(grupo.size),
                            "dif_media": grupo.mean(),
                            "dif_std": grupo.std(),
                            "pct_folds_gana_a": 100 * (grupo < 0).mean(),
                        }
                    )
    return pd.DataFrame(filas).round(3)


def tabla_referencia(resumen: pd.DataFrame) -> pd.DataFrame:
    """Construye la tabla de referencia que los modelos de la Fase 3 deben superar.

    Contrasta la referencia ingenua (promedio historico) con la calibrada. La brecha
    entre ambas es la mejora que un modelo obtendria "gratis" si se comparara contra
    la referencia debil, y que por tanto no debe atribuirse al aprendizaje.
    """
    sel = resumen[resumen["model"].isin([REFERENCIA_ACTUAL, MODELO_RECOMENDADO])].copy()
    sel["rol"] = sel["model"].map(
        {REFERENCIA_ACTUAL: "referencia_debil", MODELO_RECOMENDADO: "referencia_honesta"}
    )
    cols = [
        "rol",
        "model",
        "route",
        "regimen",
        "folds",
        "n_total",
        "mae_medio",
        "mae_pct",
        "sesgo_medio",
        "fraccion_sesgo",
    ]
    return sel[cols].sort_values(["regimen", "route", "rol"])


# --------------------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------------------


def _serie_por_ventana(resumen: pd.DataFrame, regimen: str, ruta: int, col: str) -> list[float]:
    sub = resumen[(resumen["regimen"] == regimen) & (resumen["route"] == ruta)]
    idx = sub.set_index("model")[col]
    return [idx.get(m, float("nan")) for m in VENTANAS]


def fig_mae_vs_ventana(resumen: pd.DataFrame, destino: Path) -> None:
    """H2: minimo interior del MAE en dias ordinarios.

    Un minimo interior, y no una curva monotona, es la firma del compromiso
    sesgo-varianza: ventanas cortas pierden por varianza, largas por sesgo.
    """
    anchos = list(VENTANAS.values())
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, regimen, etiqueta in zip(
        axes, ("ordinario", "raro"), ("Dias ordinarios", "Dias festivos"), strict=True
    ):
        for ruta, estilo in ESTILOS.items():
            ax.plot(
                anchos,
                _serie_por_ventana(resumen, regimen, ruta, "mae_medio"),
                label=f"Ruta {ruta}",
                markersize=6,
                linewidth=1.8,
                **estilo,
            )
        ax.set_xlabel("Tamano de ventana W (semanas)")
        ax.set_ylabel("MAE medio entre folds (pasajeros)")
        ax.set_xticks(anchos)
        ax.annotate(
            etiqueta,
            xy=(0.03, 0.95),
            xycoords="axes fraction",
            va="top",
            fontsize=11,
            fontweight="bold",
        )
        ax.legend(frameon=False, loc="best")

    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def fig_sesgo_vs_ventana(resumen: pd.DataFrame, destino: Path) -> None:
    """H2 y H3: las dos fuentes de error se mueven en direcciones opuestas.

    Escala logaritmica en el eje vertical porque los dos regimenes difieren en un
    orden de magnitud; en escala lineal la curva de dias ordinarios queda plana.
    """
    anchos = list(VENTANAS.values())
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for regimen, relleno in (("ordinario", "full"), ("raro", "none")):
        for ruta, estilo in ESTILOS.items():
            etiqueta = "Ordinarios" if regimen == "ordinario" else "Festivos"
            ax.plot(
                anchos,
                _serie_por_ventana(resumen, regimen, ruta, "sesgo_medio"),
                label=f"{etiqueta} - Ruta {ruta}",
                markersize=6,
                linewidth=1.8,
                fillstyle=relleno,
                **estilo,
            )

    ax.set_yscale("log")
    ax.set_xlabel("Tamano de ventana W (semanas)")
    ax.set_ylabel("Sesgo medio entre folds (pasajeros, escala log)")
    ax.set_xticks(anchos)
    ax.legend(frameon=False, fontsize=9, loc="best")
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def fig_comparacion_pareada(por_fold: pd.DataFrame, destino: Path) -> None:
    """H5: la eleccion de W se sostiene fold a fold, no en promedios.

    Cada punto es un fold. La dispersion alrededor de cero muestra si la ventaja es
    consistente o si depende del periodo evaluado.
    """
    sub = por_fold[por_fold["regimen"] == "ordinario"]
    pivot = sub.pivot_table(index=["route", "fold"], columns="model", values="mae")

    pares = [
        ("rolling_average_4w", MODELO_RECOMENDADO),
        ("rolling_average_12w", MODELO_RECOMENDADO),
        ("rolling_average_26w", MODELO_RECOMENDADO),
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))

    posiciones, etiquetas = [], []
    for i, (a, b) in enumerate(pares):
        if a not in pivot or b not in pivot:
            continue
        for j, (ruta, estilo) in enumerate(ESTILOS.items()):
            pos = i + (j - 0.5) * 0.28
            dif = (pivot[a] - pivot[b]).xs(ruta, level="route").dropna()
            ax.scatter(
                [pos] * len(dif),
                dif,
                s=18,
                alpha=0.55,
                color=estilo["color"],
                marker=estilo["marker"],
                label=f"Ruta {ruta}" if i == 0 else None,
            )
            ax.hlines(dif.mean(), pos - 0.11, pos + 0.11, color=estilo["color"], linewidth=2.2)
            posiciones.append(pos)
        etiquetas.append(a.replace("rolling_average_", ""))

    ax.axhline(0, color="#444444", linewidth=1)
    ax.set_xticks(range(len(pares)))
    ax.set_xticklabels([f"{e} frente a 8w" for e in etiquetas])
    ax.set_ylabel("Diferencia de MAE por fold (pasajeros)")
    ax.set_xlabel("Comparacion (valores negativos favorecen al primer modelo)")
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def fig_plano_mae_sesgo(resumen: pd.DataFrame, destino: Path) -> None:
    """H1: el error del promedio historico es mayoritariamente calibracion.

    El plano MAE-sesgo separa los modelos que fallan por desnivel de los que fallan
    por dispersion. La esquina inferior izquierda es el objetivo de la Fase 3.
    """
    sub = resumen[resumen["regimen"] == "ordinario"]
    fig, ax = plt.subplots(figsize=(7.5, 5))

    for ruta, estilo in ESTILOS.items():
        datos = sub[sub["route"] == ruta]
        ax.scatter(
            datos["mae_medio"],
            datos["sesgo_medio"],
            s=60,
            color=estilo["color"],
            marker=estilo["marker"],
            label=f"Ruta {ruta}",
            zorder=3,
        )
        for _, fila in datos.iterrows():
            nombre = (
                fila["model"]
                .replace("rolling_average_", "")
                .replace("historical_average_route_day_type_slot", "prom. historico")
                .replace("seasonal_naive_", "est. ")
            )
            ax.annotate(
                nombre,
                xy=(fila["mae_medio"], fila["sesgo_medio"]),
                xytext=(5, 3),
                textcoords="offset points",
                fontsize=8,
            )

    ax.axhline(0, color="#888888", linewidth=0.8, linestyle=":")
    ax.set_xlabel("MAE medio entre folds (pasajeros)")
    ax.set_ylabel("Sesgo medio entre folds (pasajeros)")
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def fig_referencia_comparacion(resumen: pd.DataFrame, destino: Path) -> None:
    """Sintesis: cuanto de la "mejora" de un modelo vendria de una referencia debil.

    Compara el promedio historico con el promedio movil calibrado, por regimen. La
    brecha en dias ordinarios es margen que no debe atribuirse al aprendizaje; en
    festivos la relacion se invierte, y esa inversion es en si misma un hallazgo.
    """
    modelos = [REFERENCIA_ACTUAL, MODELO_RECOMENDADO]
    nombres = ["Promedio historico\n(referencia debil)", "Promedio movil 8w\n(referencia honesta)"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, regimen, etiqueta in zip(
        axes, ("ordinario", "raro"), ("Dias ordinarios", "Dias festivos"), strict=True
    ):
        sub = resumen[resumen["regimen"] == regimen]
        ancho = 0.35

        for j, (ruta, estilo) in enumerate(ESTILOS.items()):
            sub_ruta = sub[sub["route"] == ruta]  # <-- faltaba este filtro
            valores = []
            for m in modelos:
                fila = sub_ruta.loc[sub_ruta["model"] == m, "mae_medio"]
                valores.append(float(fila.iloc[0]) if len(fila) else float("nan"))

            pos = [k + (j - 0.5) * ancho for k in range(len(modelos))]
            ax.bar(
                pos,
                valores,
                width=ancho,
                color=estilo["color"],
                edgecolor="white",
                linewidth=0.8,
                label=f"Ruta {ruta}",
            )
            for x, v in zip(pos, valores, strict=True):
                if v == v:  # descarta NaN
                    ax.text(x, v + 0.4, f"{v:.1f}", ha="center", fontsize=9)

        ax.set_xticks(range(len(modelos)))
        ax.set_xticklabels(nombres, fontsize=9)
        ax.set_ylabel("MAE medio entre folds (pasajeros)")
        ax.annotate(
            etiqueta,
            xy=(0.03, 0.95),
            xycoords="axes fraction",
            va="top",
            fontsize=11,
            fontweight="bold",
        )
        ax.legend(frameon=False, loc="upper right", fontsize=9)

    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="rolling_bias_20260720")
    parser.add_argument("--raiz", default=".", help="Raiz del repositorio")
    args = parser.parse_args()

    raiz = Path(args.raiz).resolve()
    tablas = raiz / "reports" / "tables" / "modeling"
    figuras = raiz / "reports" / "figures" / "modeling"
    figuras.mkdir(parents=True, exist_ok=True)

    parquet = tablas / f"predictions_multitarget_{args.run_id}.parquet"
    df = clasificar_regimen(cargar_predicciones(parquet))

    val = df[df["split"] == "validation"]
    if val.empty:
        raise ValueError("No hay filas de validacion tras aplicar los filtros.")

    por_fold = metricas_por_fold(val)
    resumen = resumen_entre_folds(por_fold)
    pareadas = comparaciones_pareadas(por_fold)
    referencia = tabla_referencia(resumen)

    sufijo = args.run_id
    por_fold.round(4).to_csv(tablas / f"baseline_ref_por_fold_{sufijo}.csv", index=False)
    resumen.to_csv(tablas / f"baseline_ref_resumen_{sufijo}.csv", index=False)
    pareadas.to_csv(tablas / f"baseline_ref_pareadas_{sufijo}.csv", index=False)
    referencia.to_csv(tablas / f"baseline_ref_comparacion_{sufijo}.csv", index=False)

    fig_mae_vs_ventana(resumen, figuras / f"mae_vs_ventana_regimen_{sufijo}.png")
    fig_sesgo_vs_ventana(resumen, figuras / f"sesgo_vs_ventana_regimen_{sufijo}.png")
    fig_comparacion_pareada(por_fold, figuras / f"comparacion_pareada_folds_{sufijo}.png")
    fig_plano_mae_sesgo(resumen, figuras / f"plano_mae_sesgo_{sufijo}.png")
    fig_referencia_comparacion(resumen, figuras / f"referencia_comparacion_{sufijo}.png")

    # Resumen en consola: solo lo necesario para decidir, no un volcado de tablas.
    # Resumen en consola: solo lo necesario para decidir, no un volcado de tablas.
    n_ordinarios = int(por_fold.loc[por_fold["regimen"] == "ordinario", "n"].sum())
    n_raros = int(por_fold.loc[por_fold["regimen"] == "raro", "n"].sum())

    print(f"\nFolds de validacion procesados: {por_fold['fold'].nunique()}")
    print(f"Observaciones (ordinarios / raros): {n_ordinarios} / {n_raros}")

    print("\n--- Referencia de comparacion para la Fase 3 ---")
    print(referencia.to_string(index=False))

    print("\n--- Comparacion pareada en MAE, dias ordinarios ---")
    mae_par = pareadas[(pareadas["metrica"] == "mae")]
    print(
        mae_par[["modelo_a", "modelo_b", "route", "dif_media", "pct_folds_gana_a"]].to_string(
            index=False
        )
    )

    print(f"\nFiguras y tablas escritas con sufijo '{sufijo}'.")


if __name__ == "__main__":
    main()
