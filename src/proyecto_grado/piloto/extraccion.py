"""Extraccion por ventana con reemplazo por clave (seccion 1.2 del diseno).

Cada ejecucion reextrae las jornadas de la ventana [D - 6, D] (35 dias si la
jornada objetivo es domingo), ampliada hacia atras hasta cubrir los dias que el
almacen de la piloto aun no tiene desde ``inicio_almacen``. La consulta es la de
``etl.extract.obtener_despachos`` sin cambios, en solo lectura y acotada por
``pk_ancla``. Los despachos de la ventana reemplazan a los del almacen, asi se
recogen altas, cambios y anulaciones.

El almacen (``<salidas>/almacen/``) guarda una version por ejecucion del crudo y
del conjunto apto, y un puntero ``ACTUAL.json`` a la ultima valida. Nada se
sobrescribe: cada ejecucion escribe archivos nuevos y solo mueve el puntero.
"""

from __future__ import annotations

import io
import json
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from proyecto_grado.piloto.fechas import Objetivo

logger = logging.getLogger(__name__)

PK = "PK_INTERVALO_DESPACHO"
PK_REGISTRADORA = "PK_INFORMACION_REGISTRADORA"
FECHA = "FECHA_INICIAL"
BD_OPERACIONAL = "bd_montebello_rdw"


class ErrorExtraccion(RuntimeError):  # noqa: N818
    """La extraccion fallo o su resultado no es utilizable."""


# --------------------------------------------------------------- ventana


@dataclass(frozen=True)
class Ventana:
    inicio: date
    fin: date
    motivo: str

    @property
    def dias(self) -> int:
        return (self.fin - self.inicio).days + 1

    def contiene(self, fechas: pd.Series) -> pd.Series:
        return (fechas >= self.inicio) & (fechas <= self.fin)

    def como_dict(self) -> dict:
        return {
            "inicio": self.inicio.isoformat(),
            "fin": self.fin.isoformat(),
            "dias": self.dias,
            "motivo": self.motivo,
        }


def calcular_ventana(
    objetivo: Objetivo,
    ventana_dias: int,
    ventana_dias_domingo: int,
    inicio_almacen: date,
    cubierto_hasta: date | None,
) -> Ventana:
    """Ventana de reextraccion para la jornada objetivo.

    Termina en D. Empieza ``ventana_dias - 1`` dias antes (o
    ``ventana_dias_domingo - 1`` si la jornada objetivo es domingo: conciliacion
    profunda), y antes aun si el almacen no cubre los dias previos desde
    ``inicio_almacen`` (primera ejecucion o ejecuciones perdidas). Nunca empieza
    antes de ``inicio_almacen``.
    """
    fin = objetivo.d
    domingo = objetivo.d_mas_1.weekday() == 6
    n = ventana_dias_domingo if domingo else ventana_dias
    inicio = fin - timedelta(days=n - 1)
    motivo = "domingo" if domingo else "ordinaria"
    primero_sin_cubrir = inicio_almacen if cubierto_hasta is None else cubierto_hasta + timedelta(1)
    if primero_sin_cubrir < inicio:
        inicio, motivo = primero_sin_cubrir, f"{motivo}, ampliada hasta el primer dia sin cubrir"
    if inicio < inicio_almacen:
        inicio = inicio_almacen
    if inicio > fin:
        raise ErrorExtraccion(f"Ventana vacia: {inicio} > {fin}.")
    return Ventana(inicio=inicio, fin=fin, motivo=motivo)


def fechas_de(df: pd.DataFrame) -> pd.Series:
    """FECHA_INICIAL como fecha (sin hora)."""
    return pd.to_datetime(df[FECHA], errors="coerce").dt.date


def calcular_pk_ancla(locales: list[pd.DataFrame], inicio: date, margen: int) -> int:
    """Menor PK local con FECHA_INICIAL >= inicio, menos ``margen``.

    Si ningun despacho local es de la ventana, se usa el mayor PK local. Sin
    datos locales, 0 (recorre la tabla completa, solo con el filtro de fecha).
    """
    con_datos = [d for d in locales if d is not None and len(d)]
    if not con_datos:
        return 0
    todos = pd.concat([d[[PK, FECHA]] for d in con_datos], ignore_index=True)
    pks = pd.to_numeric(todos[PK], errors="coerce")
    en_ventana = pks[fechas_de(todos) >= inicio]
    base = en_ventana.min() if en_ventana.notna().any() else pks.max()
    return max(int(base) - int(margen), 0)


# --------------------------------------------------------------- fuentes


class Fuente(Protocol):
    nombre: str

    def extraer(self, ventana: Ventana, pk_ancla: int) -> pd.DataFrame: ...


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Representacion canonica del crudo: ida y vuelta por CSV.

    Es la representacion con la que el ETL siempre leyo el crudo
    (``despachos_raw_historico.csv``), asi las fechas y horas de MySQL
    (``date``, ``timedelta``, ``datetime``) quedan como texto igual que en la
    semilla, y la instantanea en parquet tiene tipos estables.
    """
    if df.empty:
        return df.copy()
    return pd.read_csv(io.StringIO(df.to_csv(index=False)))


class FuenteBD:
    """Consulta de ``etl.extract.obtener_despachos`` en sesion de solo lectura."""

    nombre = "bd"

    def __init__(self, conectar=None, consultar=None):
        # Inyectables para las pruebas; por defecto, las funciones del ETL.
        if conectar is None:
            from proyecto_grado.etl.db import conectar_bd as conectar
        if consultar is None:
            from proyecto_grado.etl.extract import obtener_despachos as consultar
        self._conectar = conectar
        self._consultar = consultar

    def extraer(self, ventana: Ventana, pk_ancla: int) -> pd.DataFrame:
        from proyecto_grado.etl.db import cerrar_conexion

        conexion = self._conectar(BD_OPERACIONAL)
        if conexion is None:
            raise ErrorExtraccion(f"No se pudo conectar a {BD_OPERACIONAL}.")
        try:
            cursor = conexion.cursor()
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.close()
            # obtener_despachos filtra PK > max_pk: con pk_ancla - 1 equivale a
            # PK >= pk_ancla. La fecha final lleva 23:59:59 para que el BETWEEN
            # incluya todo el dia D tambien si la columna es DATETIME.
            filas = self._consultar(
                conexion, ventana.inicio.isoformat(), f"{ventana.fin} 23:59:59", pk_ancla - 1
            )
        finally:
            cerrar_conexion(conexion)
        if filas is None:
            raise ErrorExtraccion("La consulta de despachos fallo (ver el log).")
        return normalizar(filas)


class FuenteLocal:
    """Crudo de una extraccion anterior (la semilla), como si fuera la base.

    Para pruebas y ensayos sin base de datos: aplica a ese archivo los mismos
    filtros que la consulta (fecha de la ventana y PK >= pk_ancla).
    """

    nombre = "local"

    def __init__(self, ruta_crudo: Path):
        self.ruta = Path(ruta_crudo)

    def extraer(self, ventana: Ventana, pk_ancla: int) -> pd.DataFrame:
        crudo = pd.read_csv(self.ruta)
        f = fechas_de(crudo)
        sel = ventana.contiene(f) & (pd.to_numeric(crudo[PK]) >= pk_ancla)
        return normalizar(crudo[sel].reset_index(drop=True))


# --------------------------------------------------------------- deduplicado y diferencias


def deduplicar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Un registro por despacho, de forma determinista.

    Ordena de forma estable por (PK_INTERVALO_DESPACHO,
    PK_INFORMACION_REGISTRADORA) y conserva el ultimo: el registro de
    registradora de mayor PK. No depende del orden en que la base devuelve las
    filas.
    """
    if df.empty:
        return df.copy(), {"filas": 0, "despachos": 0, "duplicados": []}
    orden = df.sort_values([PK, PK_REGISTRADORA], kind="mergesort")
    dup = orden[orden.duplicated(PK, keep=False)]
    detalle = [
        {
            "pk": int(pk),
            "registros": [int(x) for x in g[PK_REGISTRADORA]],
            "conservado": int(g[PK_REGISTRADORA].iloc[-1]),
        }
        for pk, g in dup.groupby(PK, sort=True)
    ]
    salida = orden.drop_duplicates(PK, keep="last").reset_index(drop=True)
    return salida, {"filas": len(df), "despachos": len(salida), "duplicados": detalle}


def _iguales(a: pd.Series, b: pd.Series) -> np.ndarray:
    na, nb = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
    numericas = (na.notna() | a.isna()) & (nb.notna() | b.isna())
    if numericas.all():
        return np.asarray((na.isna() & nb.isna()) | np.isclose(na, nb, equal_nan=False))
    sa, sb = a.astype("string").fillna("<NA>"), b.astype("string").fillna("<NA>")
    return np.asarray(sa == sb)


def diferencias(previo: pd.DataFrame, nuevo: pd.DataFrame, ventana: Ventana) -> dict:
    """Nuevos, cambiados (por campo) y retirados, por dia de la ventana.

    ``previo`` es el crudo del almacen (solo cuentan sus despachos de la
    ventana); ``nuevo``, la extraccion deduplicada. Un dia sin despachos previos
    en el almacen se marca ``sin_previo``. Si hay cambios o retiros en el dia
    mas antiguo de la ventana, ``cambios_dia_mas_antiguo`` es True: la ventana
    puede quedarse corta.
    """
    prev = previo[ventana.contiene(fechas_de(previo))] if len(previo) else previo
    columnas = [c for c in nuevo.columns if c in prev.columns and c != PK]
    por_dia: dict[str, dict] = {}
    dias = [ventana.inicio + timedelta(i) for i in range(ventana.dias)]
    f_nuevo = fechas_de(nuevo) if len(nuevo) else pd.Series(dtype=object)
    f_prev = fechas_de(prev) if len(prev) else pd.Series(dtype=object)
    for dia in dias:
        n = nuevo[f_nuevo == dia] if len(nuevo) else nuevo
        p = prev[f_prev == dia] if len(prev) else prev
        pk_n = set(pd.to_numeric(n[PK]).astype(int)) if len(n) else set()
        pk_p = set(pd.to_numeric(p[PK]).astype(int)) if len(p) else set()
        cambiados, campos = 0, {}
        comunes = sorted(pk_n & pk_p)
        if comunes:
            a = n.assign(_pk=pd.to_numeric(n[PK]).astype(int)).set_index("_pk").loc[comunes]
            b = p.assign(_pk=pd.to_numeric(p[PK]).astype(int)).set_index("_pk").loc[comunes]
            distinto = np.zeros(len(comunes), dtype=bool)
            for c in columnas:
                d = ~_iguales(a[c].reset_index(drop=True), b[c].reset_index(drop=True))
                if d.any():
                    campos[c] = int(d.sum())
                    distinto |= d
            cambiados = int(distinto.sum())
        por_dia[dia.isoformat()] = {
            "despachos": len(pk_n),
            "nuevos": len(pk_n - pk_p),
            "cambiados": cambiados,
            "retirados": len(pk_p - pk_n),
            "campos_cambiados": campos,
            "sin_previo": not pk_p,
        }
    mas_antiguo = por_dia[dias[0].isoformat()]
    return {
        "por_dia": por_dia,
        "totales": {
            k: int(sum(v[k] for v in por_dia.values()))
            for k in ("despachos", "nuevos", "cambiados", "retirados")
        },
        "cambios_dia_mas_antiguo": bool(
            not mas_antiguo["sin_previo"] and (mas_antiguo["cambiados"] or mas_antiguo["retirados"])
        ),
    }


def reemplazar_ventana(base: pd.DataFrame, nuevo: pd.DataFrame, ventana: Ventana) -> pd.DataFrame:
    """``base`` sin sus despachos de la ventana, mas ``nuevo``, ordenado por PK."""
    fuera = base[~ventana.contiene(fechas_de(base))] if len(base) else base
    partes = [d for d in (fuera, nuevo) if len(d)]
    if not partes:
        return nuevo.iloc[0:0].copy()
    junto = pd.concat(partes, ignore_index=True)
    junto["_pk"] = pd.to_numeric(junto[PK])
    if junto["_pk"].duplicated().any():
        raise ErrorExtraccion("Despachos repetidos al reemplazar la ventana.")
    return junto.sort_values("_pk", kind="mergesort").drop(columns="_pk").reset_index(drop=True)


# --------------------------------------------------------------- almacen e instantaneas


@dataclass(frozen=True)
class Almacen:
    crudo: pd.DataFrame
    conjunto_apto: pd.DataFrame
    cubierto_hasta: date | None
    id_ejecucion: str | None


def _escribir_nuevo(ruta: Path, escribir) -> Path:
    """Escribe un archivo que no debe existir (nunca sobrescribe)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        raise FileExistsError(f"No se sobrescribe: {ruta}")
    temporal = ruta.with_name(ruta.name + ".tmp")
    escribir(temporal)
    os.replace(temporal, ruta)
    return ruta


def guardar_instantanea(directorio: Path, id_ejecucion: str, crudo: pd.DataFrame) -> Path:
    """Extraccion tal cual (normalizada) en ``extracciones/<id>.parquet``."""
    return _escribir_nuevo(
        Path(directorio) / f"{id_ejecucion}.parquet", lambda r: crudo.to_parquet(r, index=False)
    )


def leer_almacen(directorio: Path) -> Almacen:
    """Ultima version valida del almacen; vacio si no hay puntero."""
    puntero = Path(directorio) / "ACTUAL.json"
    if not puntero.exists():
        return Almacen(pd.DataFrame(), pd.DataFrame(), None, None)
    meta = json.loads(puntero.read_text(encoding="utf-8"))
    return Almacen(
        crudo=pd.read_parquet(Path(directorio) / meta["crudo"]),
        conjunto_apto=pd.read_parquet(Path(directorio) / meta["conjunto_apto"]),
        cubierto_hasta=date.fromisoformat(meta["cubierto_hasta"]),
        id_ejecucion=meta["id_ejecucion"],
    )


def guardar_almacen(
    directorio: Path,
    id_ejecucion: str,
    crudo: pd.DataFrame,
    conjunto_apto: pd.DataFrame,
    cubierto_hasta: date,
    mover_puntero: bool,
) -> dict[str, Path]:
    """Escribe la version de esta ejecucion y, si se indica, mueve el puntero."""
    directorio = Path(directorio)
    rutas = {
        "crudo": _escribir_nuevo(
            directorio / f"crudo_{id_ejecucion}.parquet",
            lambda r: crudo.to_parquet(r, index=False),
        ),
        "conjunto_apto": _escribir_nuevo(
            directorio / f"conjunto_apto_{id_ejecucion}.parquet",
            lambda r: conjunto_apto.to_parquet(r, index=False),
        ),
    }
    if mover_puntero:
        mover_puntero_almacen(directorio, id_ejecucion, rutas, cubierto_hasta)
    return rutas


def mover_puntero_almacen(
    directorio: Path, id_ejecucion: str, rutas: dict[str, Path], cubierto_hasta: date
) -> None:
    """Hace vigente la version ``id_ejecucion`` del almacen (escritura atomica)."""
    directorio = Path(directorio)
    meta = {
        "id_ejecucion": id_ejecucion,
        "crudo": Path(rutas["crudo"]).name,
        "conjunto_apto": Path(rutas["conjunto_apto"]).name,
        "cubierto_hasta": cubierto_hasta.isoformat(),
    }
    temporal = directorio / "ACTUAL.json.tmp"
    temporal.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    os.replace(temporal, directorio / "ACTUAL.json")
