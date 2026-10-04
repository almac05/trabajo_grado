"""Figuras para la reunion: ventana de entrenamiento y referencias por regimen.

Solo lee salidas ya persistidas en analisis/salidas/; no reentrena ni recalcula
modelos. Las agregaciones del barrido son promedios ponderados por `n`
(observaciones de la jornada): sum(metrica * n) / sum(n).

  - Figura 1: sesgo ponderado segun la ventana de entrenamiento, una linea por
    tipo de dia y un panel por ruta (barrido_ventana_diario.csv).
  - Figura 2: MAE ponderado segun la ventana, por ruta y para ambas rutas
    combinadas (barrido_ventana_diario.csv).
  - Figura 3: MAE y sesgo de las referencias de 26 y 52 semanas en dias
    normales (regimen ordinario) y festivos (regimen raro)
    (metricas__comparacion_modelos__freeze_20260922_203820__regimen.csv).

Alcance del barrido: corresponde a XGBoost con su configuracion anterior a la
busqueda de hiperparametros (PARAMS_XGB de analisis/13_barrido_ventana_diario.py),
sobre 137 jornadas (68 de ruta 1 y 69 de ruta 3), no sobre las 134 jornadas
comunes del freeze de seis metodos.

Salidas:
  - reports/figures/reunion/fig4_sesgo_por_ventana.{png,pdf}
  - reports/figures/reunion/fig5_mae_por_ventana.{png,pdf}
  - reports/figures/reunion/fig6_referencias_por_regimen.{png,pdf}
  - analisis/salidas/tablas__reunion_ventana.md: tablas para verificar las
    figuras 1 y 2.

Uso:
    python analisis/30_figuras_reunion_ventana.py
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
RUTA_BARRIDO = ENTRADA / "barrido_ventana_diario.csv"
RUTA_REGIMEN = ENTRADA / f"metricas__comparacion_modelos__{FREEZE}__regimen.csv"

SALIDA = PROJECT_ROOT / "reports" / "figures" / "reunion"
SALIDA.mkdir(parents=True, exist_ok=True)
RUTA_TABLAS = ENTRADA / "tablas__reunion_ventana.md"

VENTANAS = [8, 13, 26, 52, 999]  # 999 = registro completo
ETIQUETA_VENTANA = {8: "8", 13: "13", 26: "26", 52: "52", 999: "Completo"}
TIPOS_DIA = ["LABORAL", "SABADO", "DOMINGO", "FESTIVO", "FESTIVO_PUENTE"]
ETIQUETA_TIPO = {
    "LABORAL": "Laboral",
    "SABADO": "Sábado",
    "DOMINGO": "Domingo",
    "FESTIVO": "Festivo",
    "FESTIVO_PUENTE": "Festivo puente",
}
REGIMENES = {"ordinario": "Días normales", "raro": "Festivos"}
REFERENCIAS = ["Referencia (26s)", "Referencia (52s)"]
ETIQUETA_REF = {"Referencia (26s)": "Referencia (26 semanas)", "Referencia (52s)": "Referencia (52 semanas)"}

# Paleta categorica validada (primeros cinco puestos, en orden fijo).
COLOR_TIPO = {
    "LABORAL": "#2a78d6",
    "SABADO": "#eb6834",
    "DOMINGO": "#1baf7a",
    "FESTIVO": "#eda100",
    "FESTIVO_PUENTE": "#e87ba4",
}
MARCADOR_TIPO = {"LABORAL": "o", "SABADO": "s", "DOMINGO": "^", "FESTIVO": "D", "FESTIVO_PUENTE": "v"}
COLOR_RUTA = {"Ruta 1": "#2a78d6", "Ruta 3": "#eb6834", "Ambas rutas": "#0b0b0b"}
MARCADOR_RUTA = {"Ruta 1": "o", "Ruta 3": "s", "Ambas rutas": "D"}
# Mismos colores de las referencias que en analisis/29_figuras_reunion.py.
COLOR_REF = {"Referencia (26s)": "#eb6834", "Referencia (52s)": "#1baf7a"}

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"
TAMANO_CARTA = (10.0, 7.0)  # pulgadas; cabe en carta horizontal con margenes
NOTA_BARRIDO = (
    "Barrido de XGBoost con su configuración anterior a la búsqueda de hiperparámetros, "
    "sobre 137 jornadas (68 de ruta 1 y 69 de ruta 3). Promedios ponderados por observaciones."
)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": TINTA_2,
        "axes.labelcolor": TINTA,
        "axes.titlesize": 12,
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


FORMATO_EJE = FuncFormatter(lambda v, _pos: coma(v, 0) if float(v).is_integer() else coma(v, 1))


def ponderado(df, claves):
    """MAE y sesgo ponderados por n, con conteo de jornadas y observaciones."""
    aux = df.assign(mae_n=df["mae"] * df["n"], sesgo_n=df["sesgo"] * df["n"])
    g = aux.groupby(claves).agg(
        jornadas=("dia_op", "size"), n=("n", "sum"), mae_n=("mae_n", "sum"), sesgo_n=("sesgo_n", "sum")
    )
    g["mae"] = g["mae_n"] / g["n"]
    g["sesgo"] = g["sesgo_n"] / g["n"]
    return g.drop(columns=["mae_n", "sesgo_n"]).reset_index()


def eje_ventanas(ax):
    ax.set_xticks(range(len(VENTANAS)))
    ax.set_xticklabels([ETIQUETA_VENTANA[v] for v in VENTANAS])
    ax.set_xlim(-0.4, len(VENTANAS) - 0.6)
    ax.set_xlabel("Ventana de entrenamiento (semanas)")


def nota_pie(fig, texto):
    fig.text(0.01, 0.01, texto, ha="left", va="bottom", fontsize=9, color=TINTA_2, wrap=True)


def guardar(fig, nombre_archivo):
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"{nombre_archivo}.{ext}", dpi=300)
    plt.close(fig)


def figura_1(barrido):
    tabla = ponderado(barrido, ["route", "semanas_entrenamiento", "tipo_dia"])
    fig, ejes = plt.subplots(1, 2, figsize=TAMANO_CARTA, sharey=True)
    for ax, ruta in zip(ejes, (1, 3)):
        ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
        ax.axhline(0, color=TINTA_2, linewidth=1, linestyle="--", zorder=1)
        for tipo in TIPOS_DIA:
            serie = (
                tabla.loc[(tabla["route"] == ruta) & (tabla["tipo_dia"] == tipo)]
                .set_index("semanas_entrenamiento")
                .reindex(VENTANAS)
            )
            jornadas = int(serie["jornadas"].iloc[0])
            ax.plot(
                range(len(VENTANAS)),
                serie["sesgo"].to_numpy(),
                color=COLOR_TIPO[tipo],
                marker=MARCADOR_TIPO[tipo],
                markersize=6,
                linewidth=2,
                label=f"{ETIQUETA_TIPO[tipo]} ({jornadas} jornadas)",
                zorder=3,
            )
        eje_ventanas(ax)
        ax.set_title(f"Ruta {ruta}", loc="left", fontweight="bold")
        ax.yaxis.set_major_formatter(FORMATO_EJE)
        ax.legend(loc="upper center", frameon=False, fontsize=9)
    ejes[0].set_ylabel("Sesgo medio (pasajeros por intervalo; > 0 sobreestima)")
    fig.suptitle(
        "Sesgo de XGBoost según la ventana de entrenamiento, por tipo de día",
        x=0.01, ha="left", fontsize=14, fontweight="bold",
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.17, wspace=0.08)
    nota_pie(fig, "Nota: " + NOTA_BARRIDO)
    guardar(fig, "fig4_sesgo_por_ventana")
    return tabla


def figura_2(barrido):
    por_ruta = ponderado(barrido, ["route", "semanas_entrenamiento"])
    por_ruta["serie"] = "Ruta " + por_ruta["route"].astype(str)
    ambas = ponderado(barrido, ["semanas_entrenamiento"]).assign(serie="Ambas rutas")
    tabla = pd.concat([por_ruta.drop(columns="route"), ambas], ignore_index=True)

    fig, ax = plt.subplots(figsize=TAMANO_CARTA)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
    desplaz = {"Ruta 1": -14, "Ruta 3": 8, "Ambas rutas": 8}
    for serie in COLOR_RUTA:
        datos = tabla.loc[tabla["serie"] == serie].set_index("semanas_entrenamiento").reindex(VENTANAS)
        x = range(len(VENTANAS))
        ax.plot(
            x,
            datos["mae"].to_numpy(),
            color=COLOR_RUTA[serie],
            marker=MARCADOR_RUTA[serie],
            markersize=7,
            linewidth=2.5 if serie == "Ambas rutas" else 2,
            linestyle="-" if serie == "Ambas rutas" else "--",
            label=f"{serie} ({int(datos['jornadas'].iloc[0])} jornadas)",
            zorder=3,
        )
        for xi, valor in zip(x, datos["mae"]):
            ax.annotate(
                coma(valor),
                (xi, valor),
                xytext=(0, desplaz[serie]),
                textcoords="offset points",
                ha="center",
                va="top" if desplaz[serie] < 0 else "bottom",
                fontsize=9,
                color=TINTA,
            )
    eje_ventanas(ax)
    ax.set_ylim(26, 40)
    ax.yaxis.set_major_formatter(FORMATO_EJE)
    ax.set_ylabel("MAE ponderado (pasajeros por intervalo)")
    ax.set_title("MAE de XGBoost según la ventana de entrenamiento", loc="left", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", frameon=False, ncols=3)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.15)
    nota_pie(fig, "Nota: " + NOTA_BARRIDO)
    guardar(fig, "fig5_mae_por_ventana")
    return tabla


def figura_3(reg):
    datos = reg.loc[reg["metodo"].isin(REFERENCIAS)].set_index(["metodo", "regimen"])
    fig, ejes = plt.subplots(1, 2, figsize=TAMANO_CARTA)
    ancho = 0.36
    filas = []
    for ax, (metrica, titulo, techo) in zip(
        ejes, (("mae", "MAE", 36), ("sesgo", "Sesgo (> 0 sobreestima)", 15))
    ):
        ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
        ax.axhline(0, color=TINTA_2, linewidth=1, zorder=2)
        for j, ref in enumerate(REFERENCIAS):
            for i, regimen in enumerate(REGIMENES):
                valor = datos.loc[(ref, regimen), metrica]
                x = i + (j - 0.5) * ancho
                ax.bar(x, valor, ancho, color=COLOR_REF[ref], edgecolor="white", linewidth=1.5, zorder=3)
                ax.text(x, valor + techo * 0.01, coma(valor), ha="center", va="bottom", fontsize=10)
                filas.append((ETIQUETA_REF[ref], REGIMENES[regimen], metrica, valor))
        ax.set_xticks(range(len(REGIMENES)))
        ax.set_xticklabels(list(REGIMENES.values()), color=TINTA)
        ax.set_ylim(0, techo)
        ax.yaxis.set_major_formatter(FORMATO_EJE)
        ax.set_title(titulo, loc="left", fontweight="bold")
        ax.set_ylabel("Pasajeros por intervalo")
    ejes[0].legend(
        handles=[Patch(facecolor=COLOR_REF[r], label=ETIQUETA_REF[r]) for r in REFERENCIAS],
        loc="upper right",
        frameon=False,
        fontsize=10,
    )
    n = reg.drop_duplicates("regimen").set_index("regimen")
    fig.suptitle(
        "Referencias de 26 y 52 semanas en días normales y festivos — evaluación",
        x=0.01, ha="left", fontsize=14, fontweight="bold",
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.14, wspace=0.28)
    nota_pie(
        fig,
        f"Nota: freeze 20260922_203820. Días normales: {int(n.loc['ordinario', 'n_jornadas'])} jornadas; "
        f"festivos: {int(n.loc['raro', 'n_jornadas'])} jornadas.",
    )
    guardar(fig, "fig6_referencias_por_regimen")
    return pd.DataFrame(filas, columns=["metodo", "regimen", "metrica", "valor"])


def escribir_tablas(t1, t2, t3):
    partes = [
        "# Tablas de verificación: barrido de ventana y referencias por régimen",
        "",
        "Generado por `analisis/30_figuras_reunion_ventana.py`. Figuras en `reports/figures/reunion/`.",
        "",
        "**Alcance del barrido (figuras 4 y 5):** XGBoost con su configuración anterior a la búsqueda de "
        "hiperparámetros (`PARAMS_XGB` de `analisis/13_barrido_ventana_diario.py`), reentrenamiento diario, "
        "sobre **137 jornadas** (68 de ruta 1 y 69 de ruta 3) entre el 2026-04-02 y el 2026-06-10. "
        "Objetivo del barrido: `pasajeros_total`, anterior a la adopción de `PASAJEROS_REALES`. "
        "No es comparable celda a celda con el freeze 20260922_203820 (134 jornadas comunes).",
        "",
        "Fuente: `analisis/salidas/barrido_ventana_diario.csv`. Operación: promedio ponderado por `n` "
        "(observaciones de la jornada), `sum(métrica × n) / sum(n)`. Ventana «Completo» = código 999.",
        "",
        "## MAE ponderado global por ventana y ruta (figura 5)",
        "",
    ]
    orden_series = ["Ruta 1", "Ruta 3", "Ambas rutas"]
    piv = t2.pivot(index="semanas_entrenamiento", columns="serie", values="mae")[orden_series]
    jornadas = t2.drop_duplicates("serie").set_index("serie")["jornadas"]
    partes.append(
        "| Ventana | " + " | ".join(f"{s} ({int(jornadas[s])} jornadas)" for s in orden_series) + " |"
    )
    partes.append("|---|---|---|---|")
    for v, fila in piv.iterrows():
        partes.append("| " + " | ".join([ETIQUETA_VENTANA[v]] + [coma(x) for x in fila]) + " |")

    for ruta in (1, 3):
        sub = t1.loc[t1["route"] == ruta]
        jor = sub.drop_duplicates("tipo_dia").set_index("tipo_dia")["jornadas"]
        piv = sub.pivot(index="semanas_entrenamiento", columns="tipo_dia", values="sesgo")[TIPOS_DIA]
        partes += [
            "",
            f"## Sesgo ponderado por ventana y tipo de día, ruta {ruta} (figura 4)",
            "",
            "| Ventana | " + " | ".join(f"{ETIQUETA_TIPO[t]} ({int(jor[t])})" for t in TIPOS_DIA) + " |",
            "|" + "---|" * (len(TIPOS_DIA) + 1),
        ]
        for v, fila in piv.iterrows():
            partes.append("| " + " | ".join([ETIQUETA_VENTANA[v]] + [coma(x) for x in fila]) + " |")

    partes += [
        "",
        "## Referencias por régimen, freeze 20260922_203820 (figura 6)",
        "",
        f"Fuente: `analisis/salidas/metricas__comparacion_modelos__{FREEZE}__regimen.csv`.",
        "",
        "| Método | Régimen | MAE | Sesgo |",
        "|---|---|---|---|",
    ]
    piv = t3.pivot_table(index=["metodo", "regimen"], columns="metrica", values="valor", sort=False)
    for (metodo, regimen), fila in piv.iterrows():
        partes.append(f"| {metodo} | {regimen} | {coma(fila['mae'])} | {coma(fila['sesgo'])} |")
    RUTA_TABLAS.write_text("\n".join(partes) + "\n", encoding="utf-8")


def main():
    barrido = pd.read_csv(RUTA_BARRIDO)
    reg = pd.read_csv(RUTA_REGIMEN)

    jornadas = barrido.groupby("semanas_entrenamiento").size()
    assert (jornadas == 137).all(), f"Se esperaban 137 jornadas por ventana: {jornadas.to_dict()}"
    assert sorted(barrido["semanas_entrenamiento"].unique()) == VENTANAS

    t1 = figura_1(barrido)
    t2 = figura_2(barrido)
    t3 = figura_3(reg)
    escribir_tablas(t1, t2, t3)
    print(RUTA_TABLAS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
