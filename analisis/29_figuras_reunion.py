"""Figuras para la reunion: MAE y sesgo de los metodos sobre el freeze 20260922_203820.

Genera tres figuras pensadas para imprimir en tamano carta (horizontal), con
etiquetas en espanol y coma decimal. Solo lee salidas ya persistidas en
analisis/salidas/; no reentrena ni recalcula metricas.

  - Figura 1: dispersion MAE frente a sesgo, un punto por metodo
    (metricas__comparacion_modelos__freeze_20260922_203820__global.csv).
  - Figura 2: MAE por metodo en dias normales (regimen ordinario) y festivos
    (regimen raro), ordenado por MAE en dias normales
    (metricas__comparacion_modelos__freeze_20260922_203820__regimen.csv).
  - Figura 3: sesgo global en validacion y en evaluacion del promedio combinado,
    XGBoost y las dos referencias simples
    (metricas__referencia_combinada_regimen__validacion.csv y
    metricas__referencia_combinada_regimen__freeze_20260922_203820.csv).

SARIMA se excluye del area principal de las figuras 1 y 2 porque su error
(MAE global ~48) comprime la escala del resto; sus valores se citan en una nota
al pie. Cada metodo conserva el mismo color en las tres figuras: XGBoost y las
referencias en color saturado, Prophet y las redes en grises.

Salidas en reports/figures/reunion/ (PNG a 300 dpi y PDF):
  - fig1_mae_vs_sesgo
  - fig2_mae_por_regimen
  - fig3_sesgo_validacion_evaluacion

Uso:
    python analisis/29_figuras_reunion.py
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

from proyecto_grado.etl.config import PROJECT_ROOT

FREEZE = "freeze_20260922_203820"
ENTRADA = PROJECT_ROOT / "analisis" / "salidas"
RUTA_GLOBAL = ENTRADA / f"metricas__comparacion_modelos__{FREEZE}__global.csv"
RUTA_REGIMEN = ENTRADA / f"metricas__comparacion_modelos__{FREEZE}__regimen.csv"
RUTA_COMB_VAL = ENTRADA / "metricas__referencia_combinada_regimen__validacion.csv"
RUTA_COMB_EVAL = ENTRADA / f"metricas__referencia_combinada_regimen__{FREEZE}.csv"

SALIDA = PROJECT_ROOT / "reports" / "figures" / "reunion"
SALIDA.mkdir(parents=True, exist_ok=True)

COMBINADA = "Combinada (26s/52s por regimen)"
EXCLUIDO = "SARIMA"

# Color fijo por metodo en todas las figuras. Destacados: paleta categorica
# validada (azul, naranja, aguamarina, violeta; pasa CVD en todos los pares).
# Prophet y redes: grises, para que queden en segundo plano.
COLORES = {
    "XGBoost": "#2a78d6",
    "Referencia (26s)": "#eb6834",
    "Referencia (52s)": "#1baf7a",
    COMBINADA: "#4a3aa7",
    "Prophet": "#7a7a78",
    "LSTM": "#9c9b98",
    "GRU": "#b3b2ae",
    "CNN-LSTM": "#c9c8c4",
}
DESTACADOS = {"XGBoost", "Referencia (26s)", "Referencia (52s)", COMBINADA}
NOMBRES = {
    COMBINADA: "Promedio combinado\n(26s/52s por régimen)",
    "Referencia (26s)": "Referencia\n(26 semanas)",
    "Referencia (52s)": "Referencia\n(52 semanas)",
}
NOMBRES_UNA_LINEA = {
    COMBINADA: "Promedio combinado (26s/52s por régimen)",
    "Referencia (26s)": "Referencia (26 semanas)",
    "Referencia (52s)": "Referencia (52 semanas)",
}

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"
TAMANO_CARTA = (10.0, 7.0)  # pulgadas; cabe en carta horizontal con margenes

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": TINTA_2,
        "axes.labelcolor": TINTA,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": TINTA_2,
        "ytick.color": TINTA_2,
        "text.color": TINTA,
        "savefig.facecolor": "white",
    }
)


def coma(valor, decimales=2):
    """Formatea un numero con coma decimal."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def miles(valor):
    """Entero con punto como separador de miles."""
    return f"{int(valor):,}".replace(",", ".")


FORMATO_EJE =FuncFormatter(lambda v, _pos: coma(v, 0) if float(v).is_integer() else coma(v, 1))


def nombre(metodo, una_linea=False):
    tabla = NOMBRES_UNA_LINEA if una_linea else NOMBRES
    return tabla.get(metodo, metodo)


def estilo_barra(metodo, variante):
    """Relleno por metodo; la variante secundaria va aclarada y rayada."""
    base = dict(color=COLORES[metodo], edgecolor="white", linewidth=1.5)
    if variante == "secundaria":
        base.update(alpha=0.55, hatch="///", edgecolor="white")
    if metodo in DESTACADOS:
        base["zorder"] = 3
    return base


def rotular_barras(ax, barras, valores, desplazamiento):
    for barra, valor in zip(barras, valores):
        x = barra.get_x() + barra.get_width() / 2
        y = barra.get_height()
        va = "bottom" if y >= 0 else "top"
        dy = desplazamiento if y >= 0 else -desplazamiento
        ax.text(x, y + dy, coma(valor), ha="center", va=va, fontsize=9, color=TINTA)


def nota_pie(fig, texto):
    fig.text(0.01, 0.01, texto, ha="left", va="bottom", fontsize=9, color=TINTA_2, wrap=True)


def guardar(fig, nombre_archivo):
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"{nombre_archivo}.{ext}", dpi=300)
    plt.close(fig)


def figura_1(glob):
    sarima = glob.loc[glob["metodo"] == EXCLUIDO].iloc[0]
    datos = glob.loc[glob["metodo"] != EXCLUIDO].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=TAMANO_CARTA)
    ax.axhline(0, color=TINTA_2, linewidth=1, linestyle="--", zorder=1)
    ax.grid(True, color=REJILLA, linewidth=0.8, zorder=0)

    # Desplazamientos manuales (puntos tipograficos) para evitar solapes.
    desplaz = {
        "XGBoost": (-12, -6, "right", "top"),
        "Referencia (26s)": (-12, 0, "right", "center"),
        "Referencia (52s)": (12, 0, "left", "center"),
        "Prophet": (-12, 8, "right", "bottom"),
        "LSTM": (-12, 6, "right", "bottom"),
        "GRU": (0, -14, "center", "top"),
        "CNN-LSTM": (12, 6, "left", "bottom"),
    }
    for _, fila in datos.iterrows():
        m = fila["metodo"]
        destacado = m in DESTACADOS
        ax.scatter(
            fila["mae"],
            fila["sesgo"],
            s=140 if destacado else 90,
            color=COLORES[m],
            edgecolor="white" if destacado else TINTA_2,
            linewidth=1.5 if destacado else 0.6,
            zorder=4 if destacado else 3,
        )
        dx, dy, ha, va = desplaz[m]
        ax.annotate(
            f"{nombre(m, una_linea=True)}\nMAE {coma(fila['mae'])} · sesgo {coma(fila['sesgo'])}",
            (fila["mae"], fila["sesgo"]),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=9.5,
            fontweight="bold" if destacado else "normal",
            color=TINTA if destacado else TINTA_2,
        )

    ax.set_xlim(26.6, 31.6)
    ax.set_ylim(-2, 14)
    ax.xaxis.set_major_formatter(FORMATO_EJE)
    ax.yaxis.set_major_formatter(FORMATO_EJE)
    ax.set_xlabel("MAE (pasajeros por intervalo)")
    ax.set_ylabel("Sesgo (pasajeros por intervalo; > 0 sobreestima)")
    ax.set_title("Error absoluto medio frente a sesgo por método — evaluación", loc="left")
    fig.subplots_adjust(left=0.09, right=0.97, top=0.92, bottom=0.15)
    nota_pie(
        fig,
        f"Nota: SARIMA se excluye del área principal por su error muy superior "
        f"(MAE {coma(sarima['mae'])}; sesgo {coma(sarima['sesgo'])}). "
        f"Periodo de evaluación del freeze 20260922_203820: {int(sarima['n_jornadas'])} jornadas, "
        f"{miles(sarima['n'])} intervalos.",
    )
    guardar(fig, "fig1_mae_vs_sesgo")

    return [
        ("Fig. 1", r["metodo"], "global", "MAE", r["mae"]) for _, r in datos.iterrows()
    ] + [("Fig. 1", r["metodo"], "global", "sesgo", r["sesgo"]) for _, r in datos.iterrows()] + [
        ("Fig. 1 (nota)", EXCLUIDO, "global", "MAE", sarima["mae"]),
        ("Fig. 1 (nota)", EXCLUIDO, "global", "sesgo", sarima["sesgo"]),
    ]


def figura_2(reg):
    tabla = reg.pivot(index="metodo", columns="regimen", values="mae")
    sarima = tabla.loc[EXCLUIDO]
    tabla = tabla.drop(index=EXCLUIDO).sort_values("ordinario")

    fig, ax = plt.subplots(figsize=TAMANO_CARTA)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
    ancho = 0.38
    posiciones = range(len(tabla))
    for i, (metodo, fila) in enumerate(tabla.iterrows()):
        b1 = ax.bar(i - ancho / 2, fila["ordinario"], ancho, **estilo_barra(metodo, "principal"))
        b2 = ax.bar(i + ancho / 2, fila["raro"], ancho, **estilo_barra(metodo, "secundaria"))
        rotular_barras(ax, b1, [fila["ordinario"]], 0.3)
        rotular_barras(ax, b2, [fila["raro"]], 0.3)

    ax.set_xticks(list(posiciones))
    etiquetas = ax.set_xticklabels([nombre(m) for m in tabla.index], fontsize=10)
    for etiqueta, metodo in zip(etiquetas, tabla.index):
        if metodo in DESTACADOS:
            etiqueta.set_fontweight("bold")
            etiqueta.set_color(TINTA)
    ax.set_ylim(0, 35)
    ax.yaxis.set_major_formatter(FORMATO_EJE)
    ax.set_ylabel("MAE (pasajeros por intervalo)")
    ax.set_title("MAE por método en días normales y festivos — evaluación", loc="left")
    ax.legend(
        handles=[
            Patch(facecolor="#8a8986", edgecolor="white", label="Días normales"),
            Patch(facecolor="#8a8986", alpha=0.55, hatch="///", edgecolor="white", label="Festivos"),
        ],
        loc="upper right",
        frameon=False,
        ncols=2,
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.18)
    n = reg.drop_duplicates("regimen").set_index("regimen")
    nota_pie(
        fig,
        f"Nota: SARIMA se excluye del área principal por su error muy superior "
        f"(MAE {coma(sarima['ordinario'])} en días normales; {coma(sarima['raro'])} en festivos). "
        f"Días normales: {int(n.loc['ordinario', 'n_jornadas'])} jornadas; "
        f"festivos: {int(n.loc['raro', 'n_jornadas'])} jornadas. Métodos ordenados por MAE en días normales.",
    )
    guardar(fig, "fig2_mae_por_regimen")

    filas = []
    for metodo, fila in tabla.iterrows():
        filas.append(("Fig. 2", metodo, "Días normales", "MAE", fila["ordinario"]))
        filas.append(("Fig. 2", metodo, "Festivos", "MAE", fila["raro"]))
    filas.append(("Fig. 2 (nota)", EXCLUIDO, "Días normales", "MAE", sarima["ordinario"]))
    filas.append(("Fig. 2 (nota)", EXCLUIDO, "Festivos", "MAE", sarima["raro"]))
    return filas


def figura_3(val, ev):
    orden = [COMBINADA, "XGBoost", "Referencia (26s)", "Referencia (52s)"]
    sesgo_val = val.loc[val["desagregacion"] == "global"].set_index("metodo")["sesgo"]
    sesgo_ev = ev.loc[ev["desagregacion"] == "global"].set_index("metodo")["sesgo"]
    n_val = int(val.loc[val["desagregacion"] == "global", "n_jornadas"].iloc[0])
    n_ev = int(ev.loc[ev["desagregacion"] == "global", "n_jornadas"].iloc[0])

    fig, ax = plt.subplots(figsize=TAMANO_CARTA)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
    ax.axhline(0, color=TINTA_2, linewidth=1, zorder=2)
    ancho = 0.36
    for i, metodo in enumerate(orden):
        b1 = ax.bar(i - ancho / 2, sesgo_val[metodo], ancho, **estilo_barra(metodo, "secundaria"))
        b2 = ax.bar(i + ancho / 2, sesgo_ev[metodo], ancho, **estilo_barra(metodo, "principal"))
        rotular_barras(ax, b1, [sesgo_val[metodo]], 0.15)
        rotular_barras(ax, b2, [sesgo_ev[metodo]], 0.15)

    ax.set_xticks(range(len(orden)))
    ax.set_xticklabels([nombre(m) for m in orden], fontsize=10.5, fontweight="bold", color=TINTA)
    ax.set_ylim(0, 17)
    ax.yaxis.set_major_formatter(FORMATO_EJE)
    ax.set_ylabel("Sesgo (pasajeros por intervalo; > 0 sobreestima)")
    ax.set_title("Sesgo en validación y en evaluación", loc="left")
    ax.legend(
        handles=[
            Patch(facecolor="#8a8986", alpha=0.55, hatch="///", edgecolor="white", label="Validación"),
            Patch(facecolor="#8a8986", edgecolor="white", label="Evaluación"),
        ],
        loc="upper left",
        frameon=False,
        ncols=2,
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.16)
    nota_pie(
        fig,
        f"Nota: sesgo global. Validación: {n_val} jornadas; evaluación (freeze 20260922_203820): "
        f"{n_ev} jornadas. El promedio combinado usa la referencia de 26 semanas en días normales "
        f"y la de 52 semanas en festivos.",
    )
    guardar(fig, "fig3_sesgo_validacion_evaluacion")

    filas = []
    for metodo in orden:
        filas.append(("Fig. 3", metodo, "Validación", "sesgo", sesgo_val[metodo]))
        filas.append(("Fig. 3", metodo, "Evaluación", "sesgo", sesgo_ev[metodo]))
    return filas


def main():
    glob = pd.read_csv(RUTA_GLOBAL)
    reg = pd.read_csv(RUTA_REGIMEN)
    val = pd.read_csv(RUTA_COMB_VAL)
    ev = pd.read_csv(RUTA_COMB_EVAL)

    filas = figura_1(glob) + figura_2(reg) + figura_3(val, ev)
    resumen = pd.DataFrame(filas, columns=["figura", "metodo", "grupo", "metrica", "valor"])
    resumen["rotulo"] = resumen["valor"].map(coma)
    with pd.option_context("display.width", 140, "display.max_rows", 200):
        print(resumen.to_string(index=False))
    print(f"\nFiguras en {SALIDA}")


if __name__ == "__main__":
    main()
