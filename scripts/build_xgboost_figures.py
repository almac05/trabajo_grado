"""Figuras del capitulo de modelado XGBoost.

Lee artefactos ya generados; no entrena ningun modelo. Esta separacion permite
ajustar las figuras sin recomputar resultados y garantiza que las cifras de las
graficas coincidan con las del texto.

Uso:
    python scripts/build_xgboost_figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: necesario para guardar sin mostrar

import matplotlib.pyplot as plt
import pandas as pd

ENTRADA = Path("analisis/salidas")
SALIDA = Path("reports/figures/modeling")

# Paleta apta para impresion en escala de grises: se combina color con marcador
# y estilo de linea, de modo que las series sigan siendo distinguibles.
ESTILOS = {
    1: {"color": "#1f3b57", "marker": "o", "linestyle": "-"},
    3: {"color": "#8a8580", "marker": "s", "linestyle": "--"},
}

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    }
)


def figura_cruce_ventanas(destino: Path) -> None:
    """Sesgo frente a ventana de entrenamiento, por regimen de dia.

    Muestra el hallazgo central: en dias ordinarios el sesgo crece con la
    ventana (deriva de nivel por contraccion de flota), mientras que en dias
    festivos decrece (escasez muestral). Dos mecanismos de sentido opuesto.
    """
    datos = []
    for ruta in (1, 3):
        d = pd.read_csv(ENTRADA / f"barrido_disponibilidad_real_r{ruta}.csv")
        d["route"] = ruta
        datos.append(d)
    r = pd.concat(datos, ignore_index=True)

    # La ventana de 78 semanas solo existe en 3 de los 6 cortes, porque en los
    # mas antiguos excede el inicio del dataset. Se excluye por no ser
    # comparable con el resto.
    r = r[r["semanas_entrenamiento"] != 78]

    # 999 codifica "todo el historico". Se ubica en 78 para que la escala del
    # eje no quede dominada por ese valor.
    posicion_todo = 78
    r["x"] = r["semanas_entrenamiento"].replace({999: posicion_todo})

    agg = r.groupby(["regimen", "route", "x"])["sesgo"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    for regimen, relleno in (("ordinario", "full"), ("raro", "none")):
        for ruta, estilo in ESTILOS.items():
            s = agg[(agg["regimen"] == regimen) & (agg["route"] == ruta)].sort_values("x")
            etiqueta = "Ordinarios" if regimen == "ordinario" else "Festivos"
            ax.plot(
                s["x"],
                s["sesgo"],
                label=f"{etiqueta} · Ruta {ruta}",
                markersize=6,
                linewidth=1.8,
                fillstyle=relleno,
                **estilo,
            )

    ax.axhline(0, color="#666666", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Ventana de entrenamiento (semanas)")
    ax.set_ylabel("Sesgo medio (pasajeros por franja)")
    ax.set_xticks([8, 10, 13, 26, 52, posicion_todo])
    ax.set_xticklabels(["8", "10", "13", "26", "52", "Todo"])
    ax.legend(frameon=False, fontsize=9)

    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)
    print(f"Figura escrita: {destino}")


def figura_sesgo_por_hora(destino: Path) -> None:
    """Sesgo por hora del dia sobre el conjunto de prueba final.

    Verifica que el sesgo agregado no oculte cancelacion de errores de signo
    opuesto, y revela la concentracion del error en las horas de cierre de la
    operacion.
    """
    p = pd.read_csv(ENTRADA / "test_final_predicciones.csv")

    agg = (
        p.groupby(["route", "hora_del_dia"])
        .agg(sesgo=("error", "mean"), n=("error", "size"))
        .reset_index()
    )

    # Las horas con muy pocas observaciones son los bordes de la jornada, donde
    # el promedio es inestable. Se excluyen para no inducir lectura erronea.
    agg = agg[agg["n"] >= 60]

    # Ambas rutas deben cubrir el mismo rango horario para que la comparacion
    # visual sea legitima: la Ruta 3 arranca antes que la Ruta 1.
    horas_comunes = set.intersection(*(set(g["hora_del_dia"]) for _, g in agg.groupby("route")))
    agg = agg[agg["hora_del_dia"].isin(horas_comunes)]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    for ruta, estilo in ESTILOS.items():
        s = agg[agg["route"] == ruta].sort_values("hora_del_dia")
        ax.plot(
            s["hora_del_dia"],
            s["sesgo"],
            label=f"Ruta {ruta}",
            markersize=6,
            linewidth=1.8,
            **estilo,
        )

    ax.axhline(0, color="#666666", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Hora del día")
    ax.set_ylabel("Sesgo medio (pasajeros por franja)")
    ax.set_xticks(range(5, 19, 2))
    ax.legend(frameon=False, fontsize=9)

    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)
    print(f"Figura escrita: {destino}")


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    figura_cruce_ventanas(SALIDA / "xgb_cruce_ventanas.png")
    figura_sesgo_por_hora(SALIDA / "xgb_sesgo_por_hora.png")
