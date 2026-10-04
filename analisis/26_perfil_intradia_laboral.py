"""Perfil intradia de la demanda en dia laboral, por franja de 30 minutos.

Una figura por ruta con la media y la banda entre los percentiles 25 y 75 de
`pasajeros_total` en cada franja. Reproduce la misma fuente y el mismo calculo
que `14_cuadros_mecanismos.py` usa para `cuadro_perfil_horario_laboral.csv`
(parquet de modelado, franjas con conteo no nulo, tipo_dia LABORAL, agrupacion
por la hora HH:MM de inicio de la franja), de modo que la media de cada franja
coincide con la del cuadro. El script lo verifica antes de escribir nada.

Sustituye, para el capitulo de caracterizacion, a
`reports/figures/eda/curva_intraday_{1,3}_laboral_g30min.png` de
`scripts/run_eda_temporal.py`, que agrupa por hora entera y lleva titulo
incrustado. Esta figura no lleva titulo: va en el pie de figura del documento.

Uso:
    python analisis/26_perfil_intradia_laboral.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: necesario para guardar sin mostrar

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from proyecto_grado.etl.config import PROJECT_ROOT  # noqa: E402

PARQUET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
)
CUADRO = PROJECT_ROOT / "analisis" / "salidas" / "cuadro_perfil_horario_laboral.csv"
TARGET = "pasajeros_total"
RUTAS = (1, 3)

SALIDA_TABLAS = PROJECT_ROOT / "analisis" / "salidas"
SALIDA_FIGURAS = PROJECT_ROOT / "reports" / "figures" / "eda"
SALIDA_TABLAS.mkdir(parents=True, exist_ok=True)
SALIDA_FIGURAS.mkdir(parents=True, exist_ok=True)

# Misma paleta que 24_acf_demanda_regiones.py y build_xgboost_figures.py.
ESTILOS = {
    1: {"color": "#1f3b57", "marker": "o"},
    3: {"color": "#8a8580", "marker": "s"},
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


def _version_dataset(df: pd.DataFrame) -> str:
    valores = df["dataset_version"].unique()
    if len(valores) != 1:
        raise ValueError(f"dataset_version no es unica en el parquet: {valores!r}")
    return str(valores[0])


def _perfil_laboral(df: pd.DataFrame, ruta: int) -> pd.DataFrame:
    """Mismo filtro y agrupacion que 14_cuadros_mecanismos.py, con p25 y p75."""
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")
    lab = d[d["tipo_dia"] == "LABORAL"]
    perfil = (
        lab.groupby("hora")[TARGET]
        .agg(
            media="mean",
            desv="std",
            n="count",
            p25=lambda s: s.quantile(0.25),
            p75=lambda s: s.quantile(0.75),
        )
        .reset_index()
    )
    perfil["route"] = ruta
    return perfil


def _verificar_contra_cuadro(perfil: pd.DataFrame) -> None:
    """Exige que media, desv y n coincidan con el cuadro redondeado a 1 decimal."""
    cuadro = pd.read_csv(CUADRO, dtype={"hora": str})
    propio = perfil[["hora", "media", "desv", "n", "route"]].round(1)
    j = cuadro.merge(propio, on=["route", "hora"], how="outer", suffixes=("_cuadro", "_fig"), indicator=True)
    if not (j["_merge"] == "both").all():
        raise ValueError(f"Las franjas no coinciden con el cuadro:\n{j[j['_merge'] != 'both']}")
    for col in ("media", "desv", "n"):
        if not np.allclose(j[f"{col}_cuadro"], j[f"{col}_fig"], atol=1e-9, equal_nan=True):
            raise ValueError(f"La columna {col} no coincide con {CUADRO.name}")


def _figura(perfil: pd.DataFrame, ruta: int, destino: Path) -> None:
    estilo = ESTILOS[ruta]
    p = perfil.sort_values("hora").reset_index(drop=True)
    x = np.arange(len(p))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.fill_between(
        x, p["p25"], p["p75"],
        color=estilo["color"], alpha=0.18, linewidth=0,
        label="Percentiles 25 a 75",
    )
    ax.plot(
        x, p["media"],
        color=estilo["color"], marker=estilo["marker"], markersize=3.5, linewidth=1.8,
        label="Media",
    )

    # Una etiqueta por hora en punto: las franjas HH:30 quedan como marcas menores.
    en_punto = [i for i, h in enumerate(p["hora"]) if h.endswith(":00")]
    ax.set_xticks(en_punto)
    ax.set_xticklabels([p["hora"][i] for i in en_punto], rotation=90)
    ax.set_xticks(x, minor=True)
    ax.set_xlim(-0.5, len(p) - 0.5)
    ax.set_xlabel("Franja de 30 minutos (hora de inicio)")
    ax.set_ylabel("Pasajeros por franja")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    ax.set_ylim(bottom=0)
    # Leyenda sobre el area de trazado: en ambas rutas la banda llega al borde
    # superior en alguna franja y cualquier esquina interior la taparia.
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
    fig.tight_layout()

    fig.savefig(destino)
    plt.close(fig)


def main() -> None:
    df = pd.read_parquet(PARQUET)
    version = _version_dataset(df)

    perfil = pd.concat([_perfil_laboral(df, r) for r in RUTAS], ignore_index=True)
    _verificar_contra_cuadro(perfil)

    figuras = {}
    for ruta in RUTAS:
        destino = SALIDA_FIGURAS / f"perfil_intradia_laboral_r{ruta}_g30min.png"
        _figura(perfil[perfil["route"] == ruta], ruta, destino)
        figuras[ruta] = destino

    ruta_tabla = SALIDA_TABLAS / "perfil_intradia_laboral_p25_p75.csv"
    perfil[["route", "hora", "media", "p25", "p75", "desv", "n"]].round(1).to_csv(ruta_tabla, index=False)

    # --- Reporte ---
    print(f"Parquet de origen: {PARQUET}")
    print(f"dataset_version: {version}")
    print(f"Verificacion contra {CUADRO.name}: media, desv y n coinciden en todas las franjas")
    print(f"Tabla: {ruta_tabla}")
    cuadro = pd.read_csv(CUADRO, dtype={"hora": str})
    for ruta in RUTAS:
        p = perfil[perfil["route"] == ruta]
        fila = p.loc[p["media"].idxmax()]
        c = cuadro[cuadro["route"] == ruta]
        fila_c = c.loc[c["media"].idxmax()]
        print(f"\n--- Ruta {ruta} ---")
        print(f"Figura: {figuras[ruta]}")
        print(f"Franjas: {len(p)} ({p['hora'].min()} a {p['hora'].max()}), n minimo {p['n'].min()}")
        print(f"Maximo de la media: {fila['media']:.1f} pasajeros en la franja {fila['hora']} "
              f"(p25={fila['p25']:.1f}, p75={fila['p75']:.1f}, n={fila['n']})")
        print(f"Maximo en el cuadro: {fila_c['media']:.1f} en {fila_c['hora']} -> "
              f"coincide: {'si' if (round(fila['media'], 1) == fila_c['media'] and fila['hora'] == fila_c['hora']) else 'no'}")


if __name__ == "__main__":
    main()
