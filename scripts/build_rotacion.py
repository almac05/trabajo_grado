"""Rotacion ociosa y ciclo de vehiculos por ruta.

Reconstruye el indicador de aprovechamiento de la flota reportado en la Tabla 10
del capitulo de caracterizacion operativa, cuyo calculo original no habia
quedado versionado.

Definicion adoptada, conforme al texto del documento: la rotacion ociosa es el
tiempo que transcurre en el patio entre el fin de un recorrido y el inicio del
siguiente de la misma placa. El ciclo con recorrido corresponde al tiempo entre
inicios consecutivos de la misma placa, de modo que comprende la rotacion mas
la duracion del recorrido intermedio.

Se calculan dos variantes que difieren en el tratamiento de los intervalos que
cruzan el cierre de la jornada. Un vehiculo detenido entre las 18:00 y las 04:30
del dia siguiente no se encuentra en rotacion ociosa en sentido operativo, pero
el calculo original podria haberlos incluido. Ambas versiones se reportan para
determinar cual reproduce las cifras publicadas y documentar el criterio.

Uso:
    python scripts/build_rotacion.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORIGEN = PROJECT_ROOT / "data" / "processed" / "model_ready" / "despachos_model_ready.parquet"
SALIDA = PROJECT_ROOT / "reports" / "tables" / "baseline" / "rotacion_vehiculos.csv"

RUTAS = (1, 3)

# El dia operativo se extiende de las 04:00 a las 04:00 del dia siguiente, de
# modo que las franjas de madrugada pertenecen a la jornada que comenzo la
# vispera.
INICIO_DIA_OPERATIVO_H = 4

# Rango horario empleado por el analizador de headway, que restringe los
# calculos a la franja de operacion efectiva.
HORA_OPERATIVA_INICIO = 4
HORA_OPERATIVA_FIN = 19

# Valores reportados en la Tabla 10, calculados sobre el conjunto de datos
# previo a la correccion del sesgo de conteo. Se emplean como contraste.
PUBLICADO = {
    1: {"mediana": 27.5, "p25": 15.3, "p75": 119.8, "ciclo": 347},
    3: {"mediana": 26.9, "p25": 13.9, "p75": 146.6, "ciclo": 337},
}


def calcular(d: pd.DataFrame) -> pd.DataFrame:
    """Anade rotacion, ciclo y el indicador de continuidad de jornada.

    El ordenamiento por placa y hora es imprescindible: un ordenamiento
    unicamente temporal mezclaria vehiculos distintos y el desplazamiento
    tomaria el recorrido de otra placa.
    """
    d = d.sort_values(["PLACA", "HORA_INICIAL_REAL"]).copy()
    d["dia_op"] = (d["HORA_INICIAL_REAL"] - pd.Timedelta(hours=INICIO_DIA_OPERATIVO_H)).dt.date

    g = d.groupby("PLACA", sort=False)

    # El desplazamiento se aplica dentro de cada placa: la primera fila de cada
    # vehiculo queda sin valor, dado que no existe recorrido previo.
    d["rotacion_min"] = (
        d["HORA_INICIAL_REAL"] - g["HORA_FIN_FINAL"].shift(1)
    ).dt.total_seconds() / 60

    d["ciclo_min"] = (
        d["HORA_INICIAL_REAL"] - g["HORA_INICIAL_REAL"].shift(1)
    ).dt.total_seconds() / 60

    d["misma_jornada"] = d["dia_op"] == g["dia_op"].shift(1)

    # Ambos extremos del intervalo deben caer en el horario operativo: el fin
    # del recorrido previo y el inicio del siguiente.
    fin_previo = g["HORA_FIN_FINAL"].shift(1)
    d["en_horario"] = fin_previo.dt.hour.between(HORA_OPERATIVA_INICIO, HORA_OPERATIVA_FIN) & d[
        "HORA_INICIAL_REAL"
    ].dt.hour.between(HORA_OPERATIVA_INICIO, HORA_OPERATIVA_FIN)

    return d


def resumir(d: pd.DataFrame, etiqueta: str) -> list[dict]:
    """Calcula los estadisticos por ruta sobre el subconjunto indicado."""
    filas = []
    for ruta, g in d.groupby("FK_RUTA"):
        rot = g["rotacion_min"].dropna()
        cic = g["ciclo_min"].dropna()

        # Los valores negativos indicarian solapamiento de recorridos de una
        # misma placa, situacion que no deberia producirse.
        negativos = int((rot < 0).sum())

        filas.append(
            {
                "variante": etiqueta,
                "route": ruta,
                "n_intervalos": len(rot),
                "rotacion_p25": rot.quantile(0.25),
                "rotacion_mediana": rot.median(),
                "rotacion_p75": rot.quantile(0.75),
                "rotacion_media": rot.mean(),
                "ciclo_mediana": cic.median(),
                "negativos": negativos,
            }
        )
    return filas


def main() -> None:
    if not ORIGEN.exists():
        raise FileNotFoundError(f"No se encontro el conjunto de datos: {ORIGEN}")

    df = pd.read_parquet(ORIGEN)
    df = df[df["FK_RUTA"].isin(RUTAS)]
    print(f"Despachos cargados: {len(df):,}")

    d = calcular(df)

    filas = []
    filas += resumir(d, "todos los intervalos")
    filas += resumir(d[d["misma_jornada"]], "misma jornada operativa")

    filas += resumir(d[d["en_horario"]], "horario operativo 4h-19h")

    filas += resumir(d[d["en_horario"] & d["misma_jornada"]], "horario y misma jornada")

    r = pd.DataFrame(filas).round(1)

    print("\n" + "=" * 78)
    print("ROTACION OCIOSA Y CICLO POR RUTA")
    print(r.to_string(index=False))

    # ---------------------------------------------------------------
    # Contraste con lo publicado
    # ---------------------------------------------------------------
    print("\n" + "=" * 78)
    print("CONTRASTE CON LA TABLA 10 DEL DOCUMENTO")
    print(f"{'variante':<26}{'ruta':>5}{'mediana':>10}{'p25':>8}{'p75':>9}{'ciclo':>9}")
    for _, f in r.iterrows():
        print(
            f"{f['variante']:<26}{int(f['route']):>5}"
            f"{f['rotacion_mediana']:>10.1f}{f['rotacion_p25']:>8.1f}"
            f"{f['rotacion_p75']:>9.1f}{f['ciclo_mediana']:>9.1f}"
        )
    for ruta, v in PUBLICADO.items():
        print(
            f"{'publicado':<26}{ruta:>5}{v['mediana']:>10.1f}"
            f"{v['p25']:>8.1f}{v['p75']:>9.1f}{v['ciclo']:>9.1f}"
        )

    # ---------------------------------------------------------------
    # Intervalos negativos: recorridos solapados de una misma placa
    # ---------------------------------------------------------------
    # Un valor negativo indica que un vehiculo inicia un recorrido antes de
    # haber concluido el anterior, situacion incompatible con la operacion.
    neg = d[d["rotacion_min"] < 0].copy()
    if len(neg):
        neg["solape_min"] = -neg["rotacion_min"]
        print("\n" + "=" * 78)
        print("INTERVALOS NEGATIVOS")
        print(f"Cantidad: {len(neg)} de {int(d['rotacion_min'].notna().sum()):,}")
        print(neg["solape_min"].describe(percentiles=[0.5, 0.9]).round(1).to_string())
        print(f"\nPlacas afectadas: {neg['PLACA'].nunique()}")
        print(neg["PLACA"].value_counts().head(8).to_string())
        print("\nDistribucion por anio:")
        print(pd.to_datetime(neg["HORA_INICIAL_REAL"]).dt.year.value_counts().to_string())
        print("\nPrimeros casos:")
        print(
            neg[
                [
                    "PLACA",
                    "FK_RUTA",
                    "HORA_INICIAL_REAL",
                    "HORA_FIN_FINAL",
                    "solape_min",
                    "DURACION_MIN_FINAL",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    # ---------------------------------------------------------------
    # Distribucion de los intervalos que cruzan el cierre de jornada
    # ---------------------------------------------------------------
    cruzan = d[d["rotacion_min"].notna() & ~d["misma_jornada"]]
    print("\n" + "=" * 78)
    print("INTERVALOS QUE CRUZAN EL CIERRE DE JORNADA")
    print(
        f"Cantidad: {len(cruzan):,} de {int(d['rotacion_min'].notna().sum()):,} "
        f"({100 * len(cruzan) / d['rotacion_min'].notna().sum():.1f} %)"
    )
    print(f"Mediana: {cruzan['rotacion_min'].median() / 60:.1f} horas")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    r.to_csv(SALIDA, index=False)
    print(f"\nResultado guardado en {SALIDA}")


if __name__ == "__main__":
    main()
