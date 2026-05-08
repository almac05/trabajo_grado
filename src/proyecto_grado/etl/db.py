"""Acceso a base de datos y utilidades de persistencia CSV."""

import contextlib
import logging
import os

import mysql.connector
import pandas as pd
from mysql.connector import Error

from .config import inicializar_entorno

logger = logging.getLogger(__name__)


def conectar_bd(database):
    """Crea una conexión a MySQL usando variables de entorno (ver .env).

    Las credenciales se leen de REGISTEL_DB_HOST/PORT/USER/PASSWORD.
    El nombre de la base de datos se pasa por argumento porque el ETL usa dos
    esquemas distintos: `bd_montebello_rdw` (operacional) y `bd_montebello_rdw_gps` (telemetría).
    """
    inicializar_entorno(crear_directorios=False, verbose=False)
    try:
        conexion = mysql.connector.connect(
            host=os.getenv("REGISTEL_DB_HOST", "localhost"),
            port=int(os.getenv("REGISTEL_DB_PORT", "3306")),
            user=os.getenv("REGISTEL_DB_USER", ""),
            password=os.getenv("REGISTEL_DB_PASSWORD", ""),
            database=database,
            connection_timeout=60,
            autocommit=True,
        )
        if conexion.is_connected():
            logger.info("Conexión a %s OK", database)
        return conexion
    except Error as e:
        logger.error("Error al conectar a MySQL (%s): %s", database, e)
        return None


def cerrar_conexion(conexion):
    try:
        if conexion and conexion.is_connected():
            conexion.close()
            logger.debug("Conexión cerrada.")
    except Exception:
        pass


def asegurar_conexion(conexion, database):
    try:
        if conexion is None:
            return conectar_bd(database)

        with contextlib.suppress(Exception):
            # Mantiene viva la sesion y fuerza reconexion si el servidor la cerro.
            conexion.ping(reconnect=True, attempts=3, delay=2)

        if conexion.is_connected():
            return conexion

        cerrar_conexion(conexion)
        return conectar_bd(database)
    except Exception:
        return conectar_bd(database)


def cargar_csv_si_existe(path):
    if os.path.exists(path):
        df = pd.read_csv(path, encoding="utf-8")
        logger.info("Cargado CSV: %s filas=%d", path, len(df))
        return df
    return None


def guardar_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Guardado CSV: %s filas=%d", path, len(df))
