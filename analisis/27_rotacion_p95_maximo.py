"""Percentil 95 y maximo de la rotacion ociosa dentro de la jornada, por ruta.

`scripts/build_rotacion.py` reporta p25, mediana, p75 y media de la rotacion
ociosa, pero no la cola de la distribucion. Este script reutiliza su funcion
`calcular` sin modificarla (mismo origen, misma definicion de rotacion y de
jornada operativa) y agrega el percentil 95 y el maximo sobre la variante
"misma jornada operativa", que excluye los intervalos que cruzan el cierre.

Se reportan dos versiones: con todos los intervalos, como build_rotacion.py, y
sin los intervalos negativos (solapamiento de recorridos de una misma placa),
que no pueden afectar al maximo pero si, marginalmente, al percentil 95.

Uso:
    python analisis/27_rotacion_p95_maximo.py
"""

import importlib.util

import pandas as pd

from proyecto_grado.etl.config import PROJECT_ROOT

SCRIPT_ROTACION = PROJECT_ROOT / "scripts" / "build_rotacion.py"
SALIDA = PROJECT_ROOT / "analisis" / "salidas" / "rotacion_ociosa_p95_maximo.csv"


def _cargar_build_rotacion():
    """Importa scripts/build_rotacion.py como modulo (scripts/ no es paquete)."""
    spec = importlib.util.spec_from_file_location("build_rotacion", SCRIPT_ROTACION)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main() -> None:
    br = _cargar_build_rotacion()
    df = pd.read_parquet(br.ORIGEN)
    df = df[df["FK_RUTA"].isin(br.RUTAS)]
    d = br.calcular(df)
    jornada = d[d["misma_jornada"] & d["rotacion_min"].notna()]

    filas = []
    for version, sub in (
        ("todos los intervalos", jornada),
        ("sin negativos", jornada[jornada["rotacion_min"] >= 0]),
    ):
        for ruta, g in sub.groupby("FK_RUTA"):
            rot = g["rotacion_min"]
            fila_max = g.loc[rot.idxmax()]
            filas.append({
                "variante": "misma jornada operativa",
                "version": version,
                "route": ruta,
                "n_intervalos": len(rot),
                "rotacion_mediana": rot.median(),
                "rotacion_p75": rot.quantile(0.75),
                "rotacion_p95": rot.quantile(0.95),
                "rotacion_p99": rot.quantile(0.99),
                "rotacion_max": rot.max(),
                "max_placa": fila_max["PLACA"],
                "max_inicio_siguiente": fila_max["HORA_INICIAL_REAL"].strftime("%Y-%m-%d %H:%M:%S"),
            })

    r = pd.DataFrame(filas)
    r.round(1).to_csv(SALIDA, index=False)

    print(f"Origen: {br.ORIGEN}")
    print(f"Definicion: {SCRIPT_ROTACION.name}::calcular, variante misma jornada operativa")
    print(f"Tabla: {SALIDA}\n")
    print(r.round(1).to_string(index=False))

    # Contraste con la tabla de build_rotacion.py: n y mediana deben coincidir.
    ref = pd.read_csv(br.SALIDA)
    ref = ref[ref["variante"] == "misma jornada operativa"].set_index("route")
    propio = r[r["version"] == "todos los intervalos"].set_index("route")
    for ruta in br.RUTAS:
        ok = (
            int(propio.loc[ruta, "n_intervalos"]) == int(ref.loc[ruta, "n_intervalos"])
            and round(propio.loc[ruta, "rotacion_mediana"], 1) == ref.loc[ruta, "rotacion_mediana"]
        )
        print(f"Ruta {ruta}: n y mediana coinciden con {br.SALIDA.name}: {'si' if ok else 'no'}")


if __name__ == "__main__":
    main()
