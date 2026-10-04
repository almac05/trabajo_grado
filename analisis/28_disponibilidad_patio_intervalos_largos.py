"""Disponibilidad de vehiculos en patio en cada intervalo largo entre despachos.

`src/proyecto_grado/analytics/fleet_availability.py` mide el porcentaje del
tiempo con patio vacio en tres ventanas fijas y, por separado, cuenta los
intervalos largos por ventana horaria, pero no determina si en cada intervalo
largo habia vehiculos en patio. Este script hace ese cruce, intervalo por
intervalo, sobre todas las jornadas del conjunto de modelado y con los umbrales
de 15 y 30 minutos.

Criterio de ocupacion del patio (identico a fleet_availability.py, cuyas
funciones se reutilizan sin modificarlas):
  - Despachos de model_ready con MODEL_READY_OK y HORA_FIN_FINAL no nula
    (FleetAvailabilityAnalyzer._preparar).
  - Por dia calendario (FECHA_INICIAL) y por placa, un vehiculo esta EN_PATIO
    desde la HORA_FIN_FINAL de un recorrido hasta la HORA_INICIAL_REAL de su
    siguiente recorrido del mismo dia; se descartan los tramos con inicio >= fin
    (FleetAvailabilityAnalyzer._reconstruir_timeline).
  - Un vehiculo cuenta en el instante t si inicio <= t < fin. El patio es comun
    a ambas rutas: las 67 placas operan las dos rutas y alternan de ruta dentro
    de una misma jornada.
  - Consecuencia heredada: antes de su primer recorrido del dia y despues del
    ultimo, un vehiculo no cuenta como disponible.

Criterio de intervalo largo (el de fleet_availability.py::_headways_largos_franjas):
  - Por dia calendario y por ruta, diferencia entre HORA_INICIAL_REAL de
    despachos consecutivos ordenados; largo si es estrictamente mayor que el
    umbral (15 o 30 min).
  - Se asigna a la franja por la hora del despacho que cierra el intervalo.
    Franjas: pico manana [05:00, 09:00), pico tarde [14:00, 16:00), cierre
    [16:30, 17:30) y otras; ademas, por hora entera.
  - Restriccion horaria de este analisis: ambos despachos del intervalo deben
    salir en [04:00, 19:00).

Criterio de disponibilidad en el intervalo (principal):
  - Instante evaluado t* = salida del despacho que abre el intervalo + umbral,
    es decir, el momento en que el intervalo pasa a ser largo: desde t* hasta
    la salida siguiente hubo un despacho pendiente que no se hizo.
  - Patio vacio si ningun vehiculo esta EN_PATIO en t*; con vehiculos
    disponibles si hay al menos uno.

Medidas de sensibilidad (persistidas, no sustituyen al criterio principal),
sobre el tramo excedente [t*, salida siguiente):
  - vacio_todo_tramo: ningun tramo EN_PATIO se solapa con el tramo excedente.
  - algun_instante_vacio: el patio estuvo vacio en algun instante del tramo.
  - placa_siguiente_en_patio: la placa que cierra el intervalo ya estaba en
    patio en t*.

Salidas en analisis/salidas/:
  - intervalos_largos_patio__detalle.csv: un registro por intervalo y umbral.
  - intervalos_largos_patio__resumen.csv: por umbral, ruta y franja (ventanas
    de fleet_availability y hora entera).
  - manifiesto__intervalos_largos_patio.json: origen, criterios y conteos.

Uso:
    python analisis/28_disponibilidad_patio_intervalos_largos.py
"""

import json

import numpy as np
import pandas as pd

from proyecto_grado.analytics.fleet_availability import (
    CIERRE,
    PICO_MANANA,
    PICO_TARDE,
    FleetAvailabilityAnalyzer,
)
from proyecto_grado.etl.config import PROJECT_ROOT

MODEL_READY = PROJECT_ROOT / "data" / "processed" / "model_ready" / "despachos_model_ready.parquet"
MODELADO = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "modeling"
    / "modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
)
FLEET_POR_DIA = PROJECT_ROOT / "reports" / "tables" / "baseline" / "fleet_availability_by_day.csv"

UMBRALES_MIN = (15, 30)
RUTAS = (1, 3)
HORA_INICIO, HORA_FIN = 4, 19  # [04:00, 19:00)
ORDEN_FRANJAS = ["pico_manana", "pico_tarde", "cierre", "otras"]

SALIDA = PROJECT_ROOT / "analisis" / "salidas"
SALIDA.mkdir(parents=True, exist_ok=True)
RUTA_DETALLE = SALIDA / "intervalos_largos_patio__detalle.csv"
RUTA_RESUMEN = SALIDA / "intervalos_largos_patio__resumen.csv"
RUTA_MANIFIESTO = SALIDA / "manifiesto__intervalos_largos_patio.json"


def _franja(hora: float) -> str:
    """Mismo orden de asignacion que _headways_largos_franjas."""
    if PICO_MANANA[0] <= hora < PICO_MANANA[1]:
        return "pico_manana"
    if PICO_TARDE[0] <= hora < PICO_TARDE[1]:
        return "pico_tarde"
    if CIERRE[0] <= hora < CIERRE[1]:
        return "cierre"
    return "otras"


def _intervalos_dia(dia_df: pd.DataFrame, umbral: float, horario: bool) -> pd.DataFrame:
    """Intervalos largos de un dia, por ruta, como en _headways_largos_franjas."""
    filas = []
    for ruta, r in dia_df.groupby("FK_RUTA"):
        r = r.sort_values("HORA_INICIAL_REAL")
        t_prev = r["HORA_INICIAL_REAL"].shift(1)
        headway = (r["HORA_INICIAL_REAL"] - t_prev).dt.total_seconds() / 60
        largos = r.assign(t_prev=t_prev, headway_min=headway)
        largos = largos[largos["headway_min"] > umbral]
        if horario:
            en_horario = (
                (largos["t_prev"].dt.hour >= HORA_INICIO)
                & (largos["HORA_INICIAL_REAL"].dt.hour < HORA_FIN)
            )
            largos = largos[en_horario]
        for _, row in largos.iterrows():
            filas.append({
                "route": ruta,
                "t_prev": row["t_prev"],
                "t_next": row["HORA_INICIAL_REAL"],
                "placa_siguiente": row["PLACA"],
                "headway_min": row["headway_min"],
            })
    return pd.DataFrame(filas)


def _evaluar_patio(intervalos: pd.DataFrame, patio: pd.DataFrame, umbral: float) -> pd.DataFrame:
    """Ocupacion del patio en t* y en el tramo excedente [t*, t_next)."""
    t_eval = intervalos["t_prev"] + pd.Timedelta(minutes=umbral)
    ini = patio["inicio"].to_numpy()[None, :]
    fin = patio["fin"].to_numpy()[None, :]
    te = t_eval.to_numpy()[:, None]
    tn = intervalos["t_next"].to_numpy()[:, None]

    en_patio_t = (ini <= te) & (fin > te)
    solapa_tramo = (ini < tn) & (fin > te)

    # Patio vacio en algun instante del tramo: se evalua en t* y en cada fin de
    # estancia en patio dentro del tramo, que es donde la ocupacion puede bajar.
    algun_vacio = []
    for i in range(len(intervalos)):
        puntos = np.concatenate([[te[i, 0]], fin[0][(fin[0] > te[i, 0]) & (fin[0] < tn[i, 0])]])
        ocup = ((ini <= puntos[:, None]) & (fin > puntos[:, None])).sum(axis=1)
        algun_vacio.append(bool((ocup == 0).any()))

    placas = patio["PLACA"].to_numpy()
    siguiente_en_patio = [
        bool((en_patio_t[i] & (placas == p)).any())
        for i, p in enumerate(intervalos["placa_siguiente"])
    ]

    out = intervalos.copy()
    out["t_eval"] = t_eval
    out["vehiculos_patio_t_eval"] = en_patio_t.sum(axis=1)
    out["patio_vacio"] = out["vehiculos_patio_t_eval"] == 0
    out["vacio_todo_tramo"] = ~solapa_tramo.any(axis=1)
    out["algun_instante_vacio"] = algun_vacio
    out["placa_siguiente_en_patio"] = siguiente_en_patio
    return out


def _resumir(det: pd.DataFrame, agrupacion: str, columna: str) -> pd.DataFrame:
    grupos = []
    for (umbral, ruta, valor), g in det.groupby(["umbral_min", "route", columna]):
        grupos.append((umbral, ruta, valor, g))
    for (umbral, ruta), g in det.groupby(["umbral_min", "route"]):
        grupos.append((umbral, ruta, "total", g))

    filas = []
    for umbral, ruta, valor, g in grupos:
        n = len(g)
        filas.append({
            "umbral_min": umbral,
            "route": ruta,
            "agrupacion": agrupacion,
            "franja": valor,
            "n_intervalos_largos": n,
            "n_patio_vacio": int(g["patio_vacio"].sum()),
            "n_con_disponibles": int((~g["patio_vacio"]).sum()),
            "pct_patio_vacio": 100 * g["patio_vacio"].mean(),
            "pct_con_disponibles": 100 * (~g["patio_vacio"]).mean(),
            "mediana_vehiculos_patio_t_eval": g["vehiculos_patio_t_eval"].median(),
            "pct_vacio_todo_tramo": 100 * g["vacio_todo_tramo"].mean(),
            "pct_algun_instante_vacio": 100 * g["algun_instante_vacio"].mean(),
            "pct_placa_siguiente_en_patio": 100 * g["placa_siguiente_en_patio"].mean(),
        })
    return pd.DataFrame(filas)


def _contraste_fleet(analizador: FleetAvailabilityAnalyzer) -> dict:
    """Reproduce el conteo de intervalos largos de fleet_availability_by_day.csv.

    Sin restriccion horaria y con umbral 15, sobre los mismos dias, el conteo
    debe coincidir si el CSV se genero con el model_ready vigente.
    """
    if not FLEET_POR_DIA.exists():
        return {"disponible": False}
    ref = pd.read_csv(FLEET_POR_DIA, parse_dates=["fecha"])
    cols = ["headways_largos_pico_manana", "headways_largos_pico_tarde",
            "headways_largos_cierre", "headways_largos_otros"]
    ref_total = int(ref[cols].to_numpy().sum())
    propio = 0
    for fecha in ref["fecha"].dt.date:
        dia_df = analizador._df[analizador._df["fecha_dia"] == fecha]
        propio += len(_intervalos_dia(dia_df, 15.0, horario=False))
    return {"disponible": True, "dias": len(ref), "total_csv": ref_total,
            "total_reproducido": propio, "coincide": ref_total == propio}


def main() -> None:
    df = pd.read_parquet(MODEL_READY)
    df = df[df["FK_RUTA"].isin(RUTAS)]
    analizador = FleetAvailabilityAnalyzer(df)
    datos = analizador._df

    # Jornadas del conjunto de modelado: fechas con conteo de pasajeros.
    modelado = pd.read_parquet(MODELADO, columns=["timestamp", "pasajeros_total", "dataset_version"])
    version = str(modelado["dataset_version"].unique()[0])
    jornadas = sorted(modelado.loc[modelado["pasajeros_total"].notna(), "timestamp"].dt.date.unique())
    datos = datos[datos["fecha_dia"].isin(set(jornadas))]

    detalle = []
    for fecha, dia_df in datos.groupby("fecha_dia"):
        timeline = analizador._reconstruir_timeline(dia_df.copy())
        patio = timeline[timeline["estado"] == "EN_PATIO"].reset_index(drop=True)
        for umbral in UMBRALES_MIN:
            intervalos = _intervalos_dia(dia_df, float(umbral), horario=True)
            if intervalos.empty:
                continue
            ev = _evaluar_patio(intervalos, patio, float(umbral))
            ev.insert(0, "fecha", fecha)
            ev.insert(0, "umbral_min", umbral)
            detalle.append(ev)

    det = pd.concat(detalle, ignore_index=True)
    hora_cierre = det["t_next"].dt.hour + det["t_next"].dt.minute / 60
    det["franja"] = [_franja(h) for h in hora_cierre]
    det["hora"] = det["t_next"].dt.hour
    det = det.sort_values(["umbral_min", "route", "t_prev"]).reset_index(drop=True)

    resumen = pd.concat([
        _resumir(det, "ventana_fleet_availability", "franja"),
        _resumir(det, "hora_entera", "hora"),
    ], ignore_index=True)
    resumen["orden"] = resumen["franja"].map(
        {f: i for i, f in enumerate(ORDEN_FRANJAS + ["total"])}
    )
    resumen = (
        resumen.sort_values(["umbral_min", "route", "agrupacion", "orden", "franja"],
                            key=lambda s: s.astype(str) if s.name == "franja" else s)
        .drop(columns="orden")
    )

    det.round({"headway_min": 2}).to_csv(RUTA_DETALLE, index=False)
    resumen.round(1).to_csv(RUTA_RESUMEN, index=False)

    contraste = _contraste_fleet(analizador)
    manifiesto = {
        "origen_despachos": str(MODEL_READY),
        "origen_jornadas": str(MODELADO),
        "dataset_version_modelado": version,
        "n_jornadas": len(jornadas),
        "n_jornadas_con_despachos": int(datos["fecha_dia"].nunique()),
        "n_despachos": len(datos),
        "criterio_ocupacion": (
            "fleet_availability.py: EN_PATIO desde HORA_FIN_FINAL hasta la siguiente "
            "HORA_INICIAL_REAL de la misma placa y dia calendario; cuenta en t si "
            "inicio <= t < fin; patio comun a ambas rutas"
        ),
        "criterio_intervalo_largo": (
            "por dia calendario y ruta, diferencia entre salidas consecutivas > umbral; "
            "ambas salidas en [04:00, 19:00); franja por la hora de la salida que cierra"
        ),
        "criterio_disponibilidad": (
            "patio vacio si ningun vehiculo esta EN_PATIO en t* = salida que abre + umbral"
        ),
        "umbrales_min": list(UMBRALES_MIN),
        "n_intervalos_por_umbral": det.groupby("umbral_min").size().to_dict(),
        "contraste_fleet_availability_by_day": contraste,
        "artefactos": {"detalle": str(RUTA_DETALLE), "resumen": str(RUTA_RESUMEN)},
    }
    with RUTA_MANIFIESTO.open("w", encoding="utf-8") as f:
        json.dump(manifiesto, f, indent=2, ensure_ascii=False, default=str)

    # --- Reporte ---
    print(f"Despachos: {MODEL_READY} ({len(datos):,} despachos)")
    print(f"Jornadas del conjunto de modelado ({version}): {len(jornadas)}")
    print(f"Contraste con {FLEET_POR_DIA.name}: {contraste}")
    vista = resumen[resumen["agrupacion"] == "ventana_fleet_availability"]
    cols = ["umbral_min", "route", "franja", "n_intervalos_largos", "pct_patio_vacio",
            "pct_con_disponibles", "mediana_vehiculos_patio_t_eval", "pct_vacio_todo_tramo",
            "pct_algun_instante_vacio", "pct_placa_siguiente_en_patio"]
    print(vista[cols].round(1).to_string(index=False))
    print(f"\nDetalle: {RUTA_DETALLE}\nResumen: {RUTA_RESUMEN}\nManifiesto: {RUTA_MANIFIESTO}")


if __name__ == "__main__":
    main()
