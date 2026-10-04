"""Figuras de pasajeros por despacho a partir de los artefactos de
`36_pasajeros_por_despacho.py` (solo lectura; no modifica scripts, freezes ni
configuracion).

Figuras, sin titulo incrustado, con etiquetas en espanol y coma decimal:
  1. Pasajeros por despacho por bloque horario, un panel por ruta: mediana
     (punto) y rango Q1-Q3 (barra), validacion y evaluacion lado a lado.
  2. Clasificacion de franjas por bloque horario, un panel por ruta: barras
     apiladas (subutilizadas, normales, sobrecargadas), evaluacion y linea base
     de validacion lado a lado.
  3. Mapa de calor del periodo de evaluacion, un panel por ruta: franjas de
     30 minutos (horizontal) por jornada (vertical), coloreadas por clase; en
     blanco las franjas sin despachos.
  4. Despachos por jornada en evaluacion, por ruta y total, con una linea en el
     maximo observado.

Salidas en reports/figures/pasajeros_por_despacho/ (PNG a 300 dpi y PDF), y
manifiesto en analisis/salidas/manifiesto__figuras_pasajeros_por_despacho.json.

Uso:
    python analisis/37_figuras_pasajeros_por_despacho.py
"""

import json
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

from proyecto_grado.etl.config import PROJECT_ROOT

ENTRADA = PROJECT_ROOT / "analisis" / "salidas"
SUFIJO_36 = "pasajeros_por_despacho"
RUTA_DISTRIBUCION = ENTRADA / f"distribucion__{SUFIJO_36}.csv"
RUTA_CLASIFICACION = ENTRADA / f"clasificacion_franjas__{SUFIJO_36}.csv"
RUTA_FRANJAS = ENTRADA / f"franjas__{SUFIJO_36}.csv"
RUTA_CAPACIDAD = ENTRADA / f"capacidad_flota__{SUFIJO_36}.csv"

SALIDA = PROJECT_ROOT / "reports" / "figures" / "pasajeros_por_despacho"
RUTA_MANIFIESTO = ENTRADA / "manifiesto__figuras_pasajeros_por_despacho.json"

BLOQUES = [  # (clave en los artefactos, etiqueta en la figura)
    ("madrugada (04:00-04:59)", "Madrugada\n04:00–04:59"),
    ("pico manana (05:00-06:59)", "Pico mañana\n05:00–06:59"),
    ("manana (07:00-09:59)", "Mañana\n07:00–09:59"),
    ("valle (10:00-13:59)", "Valle\n10:00–13:59"),
    ("pico tarde (14:00-15:59)", "Pico tarde\n14:00–15:59"),
    ("cierre (16:00 en adelante)", "Cierre\n16:00 en adelante"),
]
RUTAS = [1, 3]
CLASES = ["subutilizada", "normal", "sobrecargada"]
NOMBRE_CLASE = {"subutilizada": "Subutilizada", "normal": "Normal",
                "sobrecargada": "Sobrecargada"}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Paleta validada (references/palette.md del skill de visualizacion, igual que
# analisis/29_figuras_reunion.py): azul y naranja para periodos y rutas. Las
# clases usan la escala divergente azul <-> rojo con punto medio gris neutro.
COLOR_PERIODO = {"validacion": "#2a78d6", "evaluacion": "#eb6834"}
NOMBRE_PERIODO = {"validacion": "Validación (25-dic-2025 a 1-abr-2026)",
                  "evaluacion": "Evaluación (2-abr a 10-jun-2026)"}
COLOR_RUTA = {"1": "#2a78d6", "3": "#eb6834", "ambas": "#0b0b0b"}
NOMBRE_RUTA = {"1": "Ruta 1", "3": "Ruta 3", "ambas": "Total (ambas rutas)"}
COLOR_CLASE = {"subutilizada": "#2a78d6", "normal": "#b8b7b2", "sobrecargada": "#e34948"}

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"
TAMANO_CARTA = (10.0, 7.0)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": TINTA_2,
    "axes.labelcolor": TINTA,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "text.color": TINTA,
    "savefig.facecolor": "white",
})


def coma(valor, decimales=1):
    return f"{valor:.{decimales}f}".replace(".", ",")


FORMATO_ENTERO = FuncFormatter(lambda v, _p: coma(v, 0))
FORMATO_PCT = FuncFormatter(lambda v, _p: f"{coma(v, 0)} %")


def fecha_corta(d):
    return f"{d.day:02d}-{MESES[d.month - 1]}"


def guardar(fig, nombre):
    archivos = []
    for ext in ("png", "pdf"):
        ruta = SALIDA / f"{nombre}.{ext}"
        fig.savefig(ruta, dpi=300, bbox_inches="tight")
        archivos.append(str(ruta.relative_to(PROJECT_ROOT)))
    plt.close(fig)
    return archivos


def etiqueta_panel(ax, ruta):
    ax.set_title(f"Ruta {ruta}", loc="left")


# ------------------------------------------------------------------------ figura 1


def figura_1(dist):
    d = dist[dist["corte"] == "bloque"]
    fig, ejes = plt.subplots(2, 1, figsize=TAMANO_CARTA, sharex=True, sharey=True)
    x = np.arange(len(BLOQUES))
    desplazamiento = {"validacion": -0.15, "evaluacion": 0.15}
    for ax, ruta in zip(ejes, RUTAS):
        ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
        for periodo, dx in desplazamiento.items():
            s = d[(d["route"] == ruta) & (d["periodo"] == periodo)].set_index("bloque")
            s = s.loc[[b for b, _ in BLOQUES]]
            ax.vlines(x + dx, s["q1"], s["q3"], color=COLOR_PERIODO[periodo], linewidth=6,
                      alpha=0.45, capstyle="round", zorder=2)
            ax.scatter(x + dx, s["mediana"], s=60, color=COLOR_PERIODO[periodo],
                       edgecolor="white", linewidth=1.5, zorder=3)
            for xi, med in zip(x + dx, s["mediana"]):
                ax.text(xi + (-0.07 if dx < 0 else 0.07), med, coma(med, 0),
                        ha="right" if dx < 0 else "left", va="center", fontsize=8, color=TINTA)
        etiqueta_panel(ax, ruta)
        ax.set_ylabel("Pasajeros por despacho")
        ax.yaxis.set_major_formatter(FORMATO_ENTERO)
    ejes[-1].set_xticks(x, [e for _, e in BLOQUES])
    ejes[-1].set_xlim(-0.5, len(BLOQUES) - 0.5)
    leyenda = [Line2D([0], [0], marker="o", color=COLOR_PERIODO[p], markersize=7, linewidth=6,
                      alpha=0.8, label=NOMBRE_PERIODO[p]) for p in ("validacion", "evaluacion")]
    fig.legend(handles=leyenda, loc="upper right", ncol=2, frameon=False,
               bbox_to_anchor=(1.0, 1.02))
    fig.text(0.01, -0.01, "Punto: mediana (con su valor). Barra: rango entre el primer y el tercer "
             "cuartil. Pasajeros reales por despacho, por hora de inicio del despacho.",
             fontsize=8.5, color=TINTA_2, ha="left", va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return guardar(fig, "figura_1_pasajeros_por_despacho_bloque")


# ------------------------------------------------------------------------ figura 2


def figura_2(clas):
    fig, ejes = plt.subplots(2, 1, figsize=TAMANO_CARTA, sharex=True, sharey=True)
    x = np.arange(len(BLOQUES))
    ancho = 0.36
    variantes = {"evaluacion": (-ancho / 2 - 0.01, None), "validacion": (ancho / 2 + 0.01, "///")}
    for ax, ruta in zip(ejes, RUTAS):
        for periodo, (dx, trama) in variantes.items():
            s = clas[(clas["route"] == ruta) & (clas["periodo"] == periodo)].set_index("bloque")
            s = s.loc[[b for b, _ in BLOQUES]]
            base = np.zeros(len(BLOQUES))
            for clase in CLASES:
                valores = s[f"pct_{clase}"].to_numpy()
                ax.bar(x + dx, valores, ancho, bottom=base, color=COLOR_CLASE[clase],
                       edgecolor="white", linewidth=1.5, hatch=trama,
                       alpha=0.6 if trama else 1.0, zorder=2)
                for xi, b, v in zip(x + dx, base, valores):
                    if v >= 8:
                        ax.text(xi, b + v / 2, coma(v, 0), ha="center", va="center", fontsize=7.5,
                                color="white" if clase != "normal" and not trama else TINTA,
                                zorder=3)
                base += valores
            for xi, n in zip(x + dx, s["n_franjas"]):
                ax.text(xi, 101.5, f"n={n}", ha="center", va="bottom", fontsize=7, color=TINTA_2)
        etiqueta_panel(ax, ruta)
        ax.set_ylim(0, 108)
        ax.set_ylabel("Franjas (%)")
        ax.yaxis.set_major_formatter(FORMATO_PCT)
        ax.set_yticks([0, 25, 50, 75, 100])
    ejes[-1].set_xticks(x, [e for _, e in BLOQUES])
    leyenda = [Patch(facecolor=COLOR_CLASE[c], label=NOMBRE_CLASE[c]) for c in reversed(CLASES)]
    leyenda += [Patch(facecolor="white", edgecolor=TINTA_2, label="Evaluación (barra izquierda)"),
                Patch(facecolor="white", edgecolor=TINTA_2, hatch="///",
                      label="Línea base de validación (barra derecha, rayada)")]
    fig.legend(handles=leyenda, loc="upper center", ncol=5, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, 1.03))
    fig.text(0.01, -0.01, "Clase de cada franja de 30 minutos según sus pasajeros por despacho "
             "frente al primer y tercer cuartil de validación de su ruta y bloque. Etiquetas: "
             "porcentaje de franjas (se omiten las menores de 8 %); n = franjas con despachos.",
             fontsize=8.5, color=TINTA_2, ha="left", va="top", wrap=True)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return guardar(fig, "figura_2_clasificacion_franjas_bloque")


# ------------------------------------------------------------------------ figura 3


def figura_3(franjas):
    ev = franjas[franjas["periodo"] == "evaluacion"].copy()
    ev["franja"] = pd.to_datetime(ev["franja"])
    ev["dia_op"] = pd.to_datetime(ev["dia_op"]).dt.date
    ev["hhmm"] = ev["franja"].dt.strftime("%H:%M")
    columnas = sorted(ev["hhmm"].unique())
    codigo = {c: i for i, c in enumerate(CLASES)}
    cmap = ListedColormap([COLOR_CLASE[c] for c in CLASES])
    cmap.set_bad("white")

    fig, ejes = plt.subplots(1, 2, figsize=(11, 9.5), sharey=False)
    for ax, ruta in zip(ejes, RUTAS):
        r = ev[ev["route"] == ruta]
        dias = sorted(r["dia_op"].unique())
        tipo = r.drop_duplicates("dia_op").set_index("dia_op")["tipo_dia"]
        matriz = (r.assign(c=r["clase"].map(codigo))
                  .pivot(index="dia_op", columns="hhmm", values="c")
                  .reindex(index=dias, columns=columnas))
        ax.imshow(np.ma.masked_invalid(matriz.to_numpy(dtype=float)), cmap=cmap, vmin=-0.5,
                  vmax=2.5, aspect="auto", interpolation="nearest")
        ax.set_xticks(range(0, len(columnas), 2), columnas[::2], rotation=90, fontsize=7.5)
        marcas = [i for i, d in enumerate(dias)
                  if d.weekday() == 0 or tipo[d] in ("FESTIVO", "FESTIVO_PUENTE")]
        ax.set_yticks(marcas, [fecha_corta(dias[i]) + (" (festivo)" if tipo[dias[i]] in
                                                       ("FESTIVO", "FESTIVO_PUENTE") else "")
                               for i in marcas], fontsize=7.5)
        ax.set_xlabel("Franja de 30 minutos (hora de inicio)")
        for lado in ax.spines.values():
            lado.set_visible(True)
            lado.set_color(REJILLA)
        ax.tick_params(length=2)
        ax.set_title(f"Ruta {ruta} ({len(dias)} jornadas)", loc="left")
    ejes[0].set_ylabel("Jornada (se rotulan los lunes y los festivos)")
    leyenda = [Patch(facecolor=COLOR_CLASE[c], label=NOMBRE_CLASE[c]) for c in reversed(CLASES)]
    leyenda.append(Patch(facecolor="white", edgecolor=TINTA_2, label="Sin despachos"))
    fig.legend(handles=leyenda, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.02))
    fig.text(0.01, -0.01, "Periodo de evaluación (2 de abril a 10 de junio de 2026). Clase según "
             "el primer y tercer cuartil de validación de pasajeros por despacho de la ruta y el "
             "bloque horario.", fontsize=8.5, color=TINTA_2, ha="left", va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return guardar(fig, "figura_3_mapa_calor_clases_evaluacion")


# ------------------------------------------------------------------------ figura 4


def figura_4(franjas, capacidad):
    ev = franjas[franjas["periodo"] == "evaluacion"].copy()
    ev["dia_op"] = pd.to_datetime(ev["dia_op"])
    por_ruta = ev.pivot_table(index="dia_op", columns="route", values="despachos",
                              aggfunc="sum").fillna(0)
    por_ruta.columns = [str(c) for c in por_ruta.columns]
    por_ruta["ambas"] = por_ruta.sum(axis=1)
    cap = capacidad.assign(route=capacidad["route"].astype(str)).set_index("route")
    for r in ("1", "3", "ambas"):  # coherencia con los artefactos del script 36
        assert por_ruta[r].max() == cap.loc[r, "max_despachos_jornada"], r
    maximo = int(cap.loc["ambas", "max_despachos_jornada"])
    dia_max = pd.Timestamp(cap.loc["ambas", "jornada_max_despachos"])
    tipo = ev.drop_duplicates("dia_op").set_index("dia_op")["tipo_dia"]

    fig, ax = plt.subplots(figsize=TAMANO_CARTA)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.8, zorder=0)
    for d, t in tipo.items():  # sombreado de festivos
        if t in ("FESTIVO", "FESTIVO_PUENTE"):
            ax.axvspan(d - pd.Timedelta(hours=12), d + pd.Timedelta(hours=12),
                       color=REJILLA, alpha=0.7, zorder=0, linewidth=0)
    ax.axhline(maximo, color=TINTA_2, linewidth=1.2, linestyle="--", zorder=1)
    ax.text(por_ruta.index.min(), maximo + 2,
            f"Máximo observado: {maximo} despachos ({fecha_corta(dia_max)})",
            ha="left", va="bottom", fontsize=9, color=TINTA_2)
    for r in ("ambas", "1", "3"):
        ax.plot(por_ruta.index, por_ruta[r], color=COLOR_RUTA[r], linewidth=2, marker="o",
                markersize=4, markeredgecolor="white", markeredgewidth=0.8, zorder=3,
                label=NOMBRE_RUTA[r])
    ax.set_ylim(0, maximo * 1.12)
    ax.set_xlim(por_ruta.index.min() - pd.Timedelta(days=1),
                por_ruta.index.max() + pd.Timedelta(days=1))
    semanas = pd.date_range(por_ruta.index.min(), por_ruta.index.max(), freq="W-MON")
    ax.set_xticks(semanas, [fecha_corta(d) for d in semanas], rotation=45, ha="right")
    ax.yaxis.set_major_formatter(FORMATO_ENTERO)
    ax.set_ylabel("Despachos por jornada")
    ax.set_xlabel("Jornada (marcas en los lunes)")
    leyenda = [Line2D([0], [0], color=COLOR_RUTA[r], linewidth=2, marker="o", markersize=4,
                      label=NOMBRE_RUTA[r]) for r in ("ambas", "1", "3")]
    leyenda.append(Patch(facecolor=REJILLA, label="Festivo"))
    ax.legend(handles=leyenda, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, frameon=False)
    fig.text(0.01, -0.01, "Periodo de evaluación (2 de abril a 10 de junio de 2026). Despachos "
             "aptos para modelado por jornada operativa.", fontsize=8.5, color=TINTA_2,
             ha="left", va="top")
    fig.tight_layout()
    return guardar(fig, "figura_4_despachos_por_jornada_evaluacion")


# ---------------------------------------------------------------------------- main


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    dist = pd.read_csv(RUTA_DISTRIBUCION)
    clas = pd.read_csv(RUTA_CLASIFICACION)
    franjas = pd.read_csv(RUTA_FRANJAS)
    capacidad = pd.read_csv(RUTA_CAPACIDAD)

    archivos = {
        "figura_1": figura_1(dist),
        "figura_2": figura_2(clas),
        "figura_3": figura_3(franjas),
        "figura_4": figura_4(franjas, capacidad),
    }
    manifiesto = {
        "script": "analisis/37_figuras_pasajeros_por_despacho.py",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "entradas": [str(r.relative_to(PROJECT_ROOT)) for r in
                     (RUTA_DISTRIBUCION, RUTA_CLASIFICACION, RUTA_FRANJAS, RUTA_CAPACIDAD)],
        "figuras": archivos,
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    for nombre, rutas in archivos.items():
        print(f"{nombre}: {rutas[0]}")


if __name__ == "__main__":
    main()
