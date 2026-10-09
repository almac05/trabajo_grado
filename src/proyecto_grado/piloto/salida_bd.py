"""Escritura de la corrida y sus recomendaciones en bd_montebello_recomendaciones.

Es el unico modulo de la piloto que escribe en una base de datos, y solo en el
esquema ``bd_montebello_recomendaciones`` (creado por el responsable de la base;
este modulo no crea ni altera tablas). Nunca escribe en bd_montebello_rdw ni en
bd_montebello_rdw_gps.

Orden:
1. Al inicio, ``abrir_corrida``: INSERT de la corrida en EN_CURSO (y COMMIT).
2. Al final, ``cerrar_corrida``: en UNA transaccion, INSERT de todas las
   recomendaciones y UPDATE de la corrida a su estado final; COMMIT. La vista
   de Regisdata nunca ve una corrida a medias.
3. Si el cierre falla: ROLLBACK, se intenta dejar la corrida en ERROR y se
   propaga la excepcion (la planilla y el manifiesto locales se conservan).

Todas las fechas y horas en hora de Colombia, sin zona (columnas DATETIME/TIME).
Consultas siempre parametrizadas.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from proyecto_grado.dispatch.reglas import intervalo_sugerido
from proyecto_grado.piloto.fechas import a_bogota
from proyecto_grado.piloto.registro import ocultar

logger = logging.getLogger(__name__)

ESQUEMA = "bd_montebello_recomendaciones"
LARGO_ADVERTENCIAS = 2000
LARGO_MENSAJE = 1000

SQL_ABRIR = (
    "INSERT INTO bd_montebello_recomendaciones.corridas "
    "(id_corrida, fecha_operacion, inicio, estado, entorno, commit_hash) "
    "VALUES (%s, %s, %s, 'EN_CURSO', %s, %s)"
)
SQL_RECOMENDACION = (
    "INSERT INTO bd_montebello_recomendaciones.recomendaciones "
    "(id_corrida, fecha, ruta, franja_inicio, franja_fin, bloque, tipo_dia, regimen, "
    "pasajeros_predichos, divisor, meta_despachos, despachos_si_conductor, "
    "intervalo_sugerido_min, dentro_disponibilidad, grupo) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
SQL_CERRAR = (
    "UPDATE bd_montebello_recomendaciones.corridas SET "
    "fin = %s, estado = %s, advertencias = %s, version_dataset = %s, "
    "factor_ruta_1 = %s, factor_ruta_3 = %s, filas_recomendaciones = %s, ruta_s3 = %s, "
    "mensaje_error = %s "
    "WHERE id_corrida = %s AND estado = 'EN_CURSO'"
)
SQL_ERROR = (
    "UPDATE bd_montebello_recomendaciones.corridas SET "
    "fin = %s, estado = 'ERROR', mensaje_error = %s "
    "WHERE id_corrida = %s AND estado = 'EN_CURSO'"
)


class ErrorSalidaBD(RuntimeError):  # noqa: N818
    """La escritura en bd_montebello_recomendaciones fallo."""


def hora_local(instante: datetime) -> datetime:
    """Instante con zona a hora de Colombia sin zona (para DATETIME)."""
    return a_bogota(instante).replace(tzinfo=None, microsecond=0)


def _recortar(texto: str | None, largo: int) -> str | None:
    if not texto:
        return None
    texto = ocultar(texto)
    return texto if len(texto) <= largo else texto[: largo - 3] + "..."


def _o_nulo(valor, redondeo: int | None = None):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)) or pd.isna(valor):
        return None
    return round(float(valor), redondeo) if redondeo is not None else valor


def filas_recomendaciones(rec: pd.DataFrame, id_corrida: str, grupo: str) -> list[tuple]:
    """Filas de la tabla recomendaciones, en el orden de SQL_RECOMENDACION.

    - meta_despachos = despachos_recomendados;
    - despachos_si_conductor = despachos_regla_normal fuera de la disponibilidad
      habitual, NULL dentro (columna "Si hay conductor disponible");
    - intervalo_sugerido_min, de la meta (NULL si la meta es 0).
    """
    r = rec.sort_values(["route", "hora"]).reset_index(drop=True)
    dentro = r["en_disponibilidad"].astype(bool).to_numpy()
    intervalos = intervalo_sugerido(r["despachos_recomendados"].to_numpy())
    regla_normal = r.get("despachos_regla_normal")
    filas = []
    for i, f in r.iterrows():
        inicio = datetime.strptime(f["hora"], "%H:%M")
        fin = inicio + timedelta(minutes=30)
        si_conductor = None if dentro[i] or regla_normal is None else int(regla_normal.iloc[i])
        filas.append(
            (
                id_corrida,
                date.fromisoformat(str(f["dia_op"])[:10]),
                int(f["route"]),
                inicio.strftime("%H:%M:%S"),
                fin.strftime("%H:%M:%S"),
                str(f["bloque"]),
                str(f["tipo_dia"]),
                str(f["regimen"]),
                round(float(f["demanda_predicha"]), 2),
                _o_nulo(f.get("divisor_usado"), 2),
                int(f["despachos_recomendados"]),
                si_conductor,
                _o_nulo(intervalos[i], 1),
                int(bool(dentro[i])),
                grupo,
            )
        )
    return filas


@dataclass(frozen=True)
class CierreCorrida:
    fin: datetime
    estado: str
    advertencias: Sequence[str]
    version_dataset: str | None
    factores: dict[int, float]
    filas: list[tuple]
    ruta_s3: str | None = None
    mensaje_error: str | None = None


def conectar_recomendaciones():
    """Conexion transaccional al esquema de la piloto con REGISTEL_DB_*."""
    import mysql.connector

    from proyecto_grado.etl.config import inicializar_entorno

    inicializar_entorno(crear_directorios=False, verbose=False)  # carga .env
    return mysql.connector.connect(
        host=os.getenv("REGISTEL_DB_HOST", "localhost"),
        port=int(os.getenv("REGISTEL_DB_PORT", "3306")),
        user=os.getenv("REGISTEL_DB_USER", ""),
        password=os.getenv("REGISTEL_DB_PASSWORD", ""),
        database=ESQUEMA,
        connection_timeout=60,
        autocommit=False,
    )


class EscritorBD:
    """Escritura de una corrida; ``conectar`` es inyectable para las pruebas."""

    def __init__(self, conectar: Callable | None = None, esquema: str = ESQUEMA):
        if esquema != ESQUEMA:
            raise ErrorSalidaBD(f"La piloto solo escribe en {ESQUEMA}, no en {esquema}.")
        self._conectar = conectar or conectar_recomendaciones
        self._conexion = None

    def _con(self):
        if self._conexion is None:
            self._conexion = self._conectar()
        return self._conexion

    def abrir_corrida(
        self, id_corrida: str, fecha: date, inicio: datetime, entorno: str, commit: str
    ) -> None:
        con = self._con()
        cursor = con.cursor()
        try:
            cursor.execute(SQL_ABRIR, (id_corrida, fecha, hora_local(inicio), entorno, commit))
            con.commit()
        except Exception as exc:
            con.rollback()
            raise ErrorSalidaBD(ocultar(f"No se pudo abrir la corrida: {exc}")) from exc
        finally:
            cursor.close()

    def cerrar_corrida(self, id_corrida: str, c: CierreCorrida) -> None:
        con = self._con()
        cursor = con.cursor()
        try:
            if c.filas:
                cursor.executemany(SQL_RECOMENDACION, c.filas)
            cursor.execute(
                SQL_CERRAR,
                (
                    hora_local(c.fin),
                    c.estado,
                    _recortar(" | ".join(c.advertencias), LARGO_ADVERTENCIAS),
                    c.version_dataset,
                    _o_nulo(c.factores.get(1), 5),
                    _o_nulo(c.factores.get(3), 5),
                    len(c.filas),
                    c.ruta_s3,
                    _recortar(c.mensaje_error, LARGO_MENSAJE),
                    id_corrida,
                ),
            )
            if cursor.rowcount != 1:
                raise ErrorSalidaBD(f"La corrida {id_corrida} no estaba EN_CURSO.")
            con.commit()
        except Exception as exc:
            con.rollback()
            mensaje = ocultar(f"Fallo al cerrar la corrida: {exc}")
            self.marcar_error(id_corrida, c.fin, mensaje)
            raise ErrorSalidaBD(mensaje) from exc
        finally:
            cursor.close()

    def marcar_error(self, id_corrida: str, fin: datetime, mensaje: str) -> bool:
        """Deja la corrida en ERROR; no lanza excepciones (se usa al fallar)."""
        try:
            con = self._con()
            cursor = con.cursor()
            try:
                cursor.execute(
                    SQL_ERROR, (hora_local(fin), _recortar(mensaje, LARGO_MENSAJE), id_corrida)
                )
                con.commit()
            finally:
                cursor.close()
            return True
        except Exception as exc:  # pragma: no cover - solo registro
            logger.error("No se pudo marcar la corrida %s en ERROR: %s", id_corrida, exc)
            return False

    def cerrar(self) -> None:
        if self._conexion is not None:
            try:
                self._conexion.close()
            finally:
                self._conexion = None
