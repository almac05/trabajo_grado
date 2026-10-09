"""Historial de predicciones emitidas y factor de 14 dias (seccion 4 del diseno).

Historial (``<salidas>/historial/``): una fila por franja emitida. Solo se
agregan filas: cada escritura crea ``predicciones_emitidas_<id>.parquet`` con el
historial anterior mas las filas nuevas y mueve el puntero ``ACTUAL.json``, que
guarda el SHA-256 y el numero de filas de la version vigente; al leer se
verifica el SHA-256 y, al escribir, que la version anterior sea un prefijo
intacto de la nueva.

Arranque: hasta ``fin_backtest`` (2026-10-03) el historial son las predicciones
del script 43 (origen ``backtest``); desde el 2026-10-04 hasta la vispera de la
piloto, el relleno (origen ``relleno``); despues, las ejecuciones nocturnas
(origen ``piloto``).

Factor de la ruta r para la jornada D+1 (regla del preregistro, k = 14):
franjas ordinarias con jornada en [D+1 - 14, D] que tengan ``pred_xgboost``
emitida y demanda real observada en la serie actual, de jornadas con al menos
``min_franjas_jornada`` franjas observadas; factor = suma real / suma pred.
Ventana vacia o suma pred <= 0: factor 1 con advertencia.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from proyecto_grado.piloto.config import sha256_archivo
from proyecto_grado.piloto.prediccion import REGIMEN_ORDINARIO, regimen

ORIGENES = ("backtest", "relleno", "piloto")
PRIORIDAD_ORIGEN = {"piloto": 3, "relleno": 2, "backtest": 1}
COLUMNAS = [
    "id_ejecucion",
    "origen",
    "version",
    "emitido",
    "route",
    "dia_op",
    "hora",
    "tipo_dia",
    "regimen",
    "pred_xgboost",
    "ref52",
    "factor",
    "pred_final",
]


class ErrorHistorial(RuntimeError):  # noqa: N818
    """El historial no existe, fue alterado o la escritura no es de solo agregar."""


# --------------------------------------------------------------- historial


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    out = df[COLUMNAS].copy()
    out["route"] = out["route"].astype(int)
    out["dia_op"] = pd.to_datetime(out["dia_op"]).dt.strftime("%Y-%m-%d")
    out["hora"] = out["hora"].astype(str)
    for c in ("pred_xgboost", "ref52", "factor", "pred_final"):
        out[c] = out[c].astype(float)
    for c in ("id_ejecucion", "origen", "version", "emitido", "tipo_dia", "regimen"):
        out[c] = out[c].astype(str)
    return out.reset_index(drop=True)


def leer_historial(directorio: Path) -> pd.DataFrame | None:
    """Version vigente del historial (verificada), o None si no existe."""
    puntero = Path(directorio) / "ACTUAL.json"
    if not puntero.exists():
        return None
    meta = json.loads(puntero.read_text(encoding="utf-8"))
    ruta = Path(directorio) / meta["archivo"]
    if sha256_archivo(ruta) != meta["sha256"]:
        raise ErrorHistorial(f"El historial {ruta.name} no coincide con su SHA-256.")
    df = pd.read_parquet(ruta)
    if len(df) != meta["filas"]:
        raise ErrorHistorial(f"El historial {ruta.name} no tiene las filas registradas.")
    return df


def agregar_al_historial(directorio: Path, id_ejecucion: str, filas: pd.DataFrame) -> dict:
    """Escribe una version nueva con las filas agregadas al final y mueve el puntero."""
    directorio = Path(directorio)
    previo = leer_historial(directorio)
    nuevas = _normalizar(filas)
    if (nuevas["origen"] == "").any() or not nuevas["origen"].isin(ORIGENES).all():
        raise ErrorHistorial(f"Origen invalido; se esperaba uno de {ORIGENES}.")
    junto = nuevas if previo is None else pd.concat([previo, nuevas], ignore_index=True)
    if previo is not None:
        pd.testing.assert_frame_equal(junto.iloc[: len(previo)], previo, check_dtype=False)
    ruta = directorio / f"predicciones_emitidas_{id_ejecucion}.parquet"
    if ruta.exists():
        raise ErrorHistorial(f"No se sobrescribe: {ruta}")
    directorio.mkdir(parents=True, exist_ok=True)
    junto.to_parquet(ruta, index=False)
    meta = {
        "archivo": ruta.name,
        "sha256": sha256_archivo(ruta),
        "filas": len(junto),
        "filas_agregadas": len(nuevas),
        "id_ejecucion": id_ejecucion,
    }
    temporal = directorio / "ACTUAL.json.tmp"
    temporal.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    os.replace(temporal, directorio / "ACTUAL.json")
    return meta


def filas_backtest(
    ruta_xgboost: Path, ruta_ref52: Path, fin_backtest: date, tipos_raros: tuple[str, ...]
) -> pd.DataFrame:
    """Predicciones del script 43 hasta ``fin_backtest`` con origen ``backtest``."""
    xgb = pd.read_csv(ruta_xgboost)
    ref = pd.read_csv(ruta_ref52)
    claves = ["route", "dia_op", "hora"]
    for d in (xgb, ref):
        d["route"] = d["route"].astype(int)
        d["dia_op"] = pd.to_datetime(d["dia_op"]).dt.strftime("%Y-%m-%d")
        d["hora"] = d["hora"].astype(str)
    df = xgb.merge(ref[[*claves, "pred_media_52s"]], on=claves, how="left", validate="1:1")
    if df["pred_media_52s"].isna().any():
        raise ErrorHistorial("Franjas del script 43 sin referencia de 52 semanas.")
    df = df[pd.to_datetime(df["dia_op"]).dt.date <= fin_backtest]
    return pd.DataFrame(
        {
            "id_ejecucion": "backtest_" + Path(ruta_xgboost).stem.split("__")[-1],
            "origen": "backtest",
            "version": "definitiva",
            "emitido": "",
            "route": df["route"],
            "dia_op": df["dia_op"],
            "hora": df["hora"],
            "tipo_dia": df["tipo_dia"],
            "regimen": regimen(df["tipo_dia"], tipos_raros),
            "pred_xgboost": df["pred_xgboost"],
            "ref52": df["pred_media_52s"],
            "factor": np.nan,
            "pred_final": np.nan,
        }
    )


def filas_emitidas(pred: pd.DataFrame, id_ejecucion: str, origen: str, emitido: datetime):
    """Filas del historial para las predicciones de una jornada."""
    return pd.DataFrame(
        {
            "id_ejecucion": id_ejecucion,
            "origen": origen,
            "version": "definitiva",
            "emitido": emitido.isoformat(timespec="seconds"),
            "route": pred["route"],
            "dia_op": pred["dia_op"],
            "hora": pred["hora"],
            "tipo_dia": pred["tipo_dia"],
            "regimen": pred["regimen"],
            "pred_xgboost": pred["pred_xgboost"],
            "ref52": pred["ref52"],
            "factor": pred["factor"],
            "pred_final": pred["pred_final"],
        }
    )


# --------------------------------------------------------------- factor


@dataclass
class Factor:
    ruta: int
    valor: float
    aplicado: bool
    suma_real: float
    suma_pred: float
    franjas: int
    jornadas: int
    ventana: tuple[str, str]
    jornadas_pocas_franjas: list[str] = field(default_factory=list)
    origenes: dict[str, int] = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "valor": self.valor,
            "aplicado": self.aplicado,
            "suma_real": self.suma_real,
            "suma_pred": self.suma_pred,
            "franjas": self.franjas,
            "jornadas": self.jornadas,
            "ventana": list(self.ventana),
            "jornadas_menos_de_10_franjas": self.jornadas_pocas_franjas,
            "origenes": self.origenes,
            "advertencias": self.advertencias,
        }


def demanda_observada(serie: pd.DataFrame, objetivo: str = "pasajeros_total") -> pd.DataFrame:
    """route, dia_op, hora y real de las franjas con demanda observada."""
    s = serie[serie[objetivo].notna()]
    return pd.DataFrame(
        {
            "route": s["FK_RUTA"].astype(int).to_numpy(),
            "dia_op": (s["timestamp"] - pd.Timedelta(hours=4)).dt.strftime("%Y-%m-%d").to_numpy(),
            "hora": s["timestamp"].dt.strftime("%H:%M").to_numpy(),
            "real": s[objetivo].astype(float).to_numpy(),
        }
    )


def emision_vigente(historial: pd.DataFrame) -> pd.DataFrame:
    """Una emision por ruta y jornada: la del origen de mayor prioridad y, entre
    ellas, la mas reciente (por orden en el historial, que solo crece)."""
    h = historial.reset_index(drop=True).assign(_orden=lambda x: np.arange(len(x)))
    h["_prioridad"] = h["origen"].map(PRIORIDAD_ORIGEN)
    # La ejecucion elegida es la de la ultima fila de mayor prioridad de cada jornada.
    mejor = (
        h.sort_values(["_prioridad", "_orden"])
        .groupby(["route", "dia_op"])
        .tail(1)[["route", "dia_op", "id_ejecucion", "origen"]]
    )
    claves = ["route", "dia_op", "id_ejecucion", "origen"]
    return h.merge(mejor, on=claves).drop(columns=["_orden", "_prioridad"])


def calcular_factor(
    historial: pd.DataFrame,
    serie: pd.DataFrame,
    dia: date,
    ruta: int,
    ventana_dias: int,
    min_franjas_jornada: int,
    rango: tuple[float, float],
) -> Factor:
    """Factor multiplicativo de la ruta para la jornada ``dia`` (D+1)."""
    ini, fin = dia - timedelta(days=ventana_dias), dia - timedelta(days=1)
    ventana = (ini.isoformat(), fin.isoformat())
    h = historial[(historial["route"] == ruta) & (historial["regimen"] == REGIMEN_ORDINARIO)]
    fechas = pd.to_datetime(h["dia_op"]).dt.date
    h = emision_vigente(h[(fechas >= ini) & (fechas <= fin)])
    obs = demanda_observada(serie)
    obs = obs[obs["route"] == ruta]
    por_jornada = obs.groupby("dia_op").size()
    u = h.merge(obs, on=["route", "dia_op", "hora"], how="inner", validate="1:1")
    u = u[u["dia_op"].map(por_jornada).fillna(0) >= min_franjas_jornada]
    assert (pd.to_datetime(u["dia_op"]).dt.date < dia).all()  # causalidad

    s_real, s_pred = float(u["real"].sum()), float(u["pred_xgboost"].sum())
    franjas_jornada = u.groupby("dia_op").size()
    f = Factor(
        ruta=ruta,
        valor=1.0,
        aplicado=False,
        suma_real=s_real,
        suma_pred=s_pred,
        franjas=len(u),
        jornadas=int(u["dia_op"].nunique()),
        ventana=ventana,
        jornadas_pocas_franjas=sorted(franjas_jornada[franjas_jornada < 10].index),
        origenes={
            k: int(v) for k, v in u.drop_duplicates("dia_op")["origen"].value_counts().items()
        },
    )
    if len(u) and s_pred > 0:
        f.valor, f.aplicado = s_real / s_pred, True
    else:
        f.advertencias.append(
            f"Ruta {ruta}: sin franjas utilizables en {ini} a {fin}; factor 1 (sin corregir)."
        )
    if f.jornadas_pocas_franjas:
        f.advertencias.append(
            f"Ruta {ruta}: jornadas de la ventana con menos de 10 franjas utiles: "
            f"{', '.join(f.jornadas_pocas_franjas)}."
        )
    if f.aplicado and not rango[0] <= f.valor <= rango[1]:
        f.advertencias.append(
            f"Ruta {ruta}: factor {f.valor:.3f} fuera del rango del backtesting "
            f"[{rango[0]:.2f}; {rango[1]:.2f}]."
        )
    return f
