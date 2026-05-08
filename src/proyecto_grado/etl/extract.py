"""Extraccion incremental de despachos operacionales."""

import logging

import numpy as np
import pandas as pd
from mysql.connector import Error

from .config import DESPACHOS_CSV, inicializar_entorno
from .db import cargar_csv_si_existe, cerrar_conexion, conectar_bd, guardar_csv

logger = logging.getLogger(__name__)


def obtener_despachos(conexion, fecha_ini, fecha_fin, max_pk):
    """
    Trae solo despachos con PK_INTERVALO_DESPACHO > max_pk
    y fechas entre fecha_ini y fecha_fin.
    """
    if not conexion:
        logger.error("No hay conexión a bd_montebello_rdw.")
        return None

    try:
        cursor = conexion.cursor(dictionary=True)
        query = """
            SELECT
                ta.FECHA_INICIAL, ta.HORA_INICIAL_PLAN, ta.HORA_INICIAL_REAL, ta.HORA_INICIAL_AUX, ta.FECHA_FINAL,
                ta.HORA_FINAL_PLAN, ta.HORA_FINAL_REAL, ta.HORA_FINAL_AUX, ta.FK_RUTA, ta.PASAJEROS, ta.DISTANCIA,
                ta.FK_VEHICULO, ta.FK_CONDUCTOR AS CONDUCTOR,
                ta.ESTADO_DESPACHO, ta.PK_INTERVALO_DESPACHO, ta.PK_INFORMACION_REGISTRADORA,
                veh.PLACA,
                COALESCE(alarmas.ALARMAS, 0) AS ALARMAS
            FROM (
                SELECT
                    tbl_intervalo_despacho.PK_INTERVALO_DESPACHO, FECHA_INICIAL,
                    HORA_INICIAL AS HORA_INICIAL_PLAN,
                    (SELECT HORA_REAL
                    FROM tbl_planilla_despacho
                    WHERE FK_INTERVALO_DESPACHO = tbl_intervalo_despacho.PK_INTERVALO_DESPACHO AND TIPO_PUNTO = 1) AS HORA_INICIAL_REAL,
                    FECHA_FINAL, HORA_FINAL AS HORA_FINAL_PLAN,
                    (SELECT HORA_REAL
                    FROM tbl_planilla_despacho
                    WHERE FK_INTERVALO_DESPACHO = tbl_intervalo_despacho.PK_INTERVALO_DESPACHO AND TIPO_PUNTO = 3) AS HORA_FINAL_REAL,
                    (SELECT ESTADO_DESPACHO
                    FROM tbl_planilla_despacho
                    WHERE FK_INTERVALO_DESPACHO = tbl_intervalo_despacho.PK_INTERVALO_DESPACHO AND TIPO_PUNTO = 3) AS ESTADO_DESPACHO,
                    HORA_SALIDA_BASE_SALIDA AS HORA_INICIAL_AUX,
                    HORA_INGRESO AS HORA_FINAL_AUX,
                    FK_RUTA, DIFERENCIA_NUM AS PASAJEROS,
                    DISTANCIA_METROS AS DISTANCIA,
                    FK_VEHICULO,
                    tbl_intervalo_despacho.FK_CONDUCTOR,
                    PK_INFORMACION_REGISTRADORA
                FROM tbl_intervalo_despacho
                INNER JOIN tbl_informacion_registradora
                    ON tbl_intervalo_despacho.PK_INTERVALO_DESPACHO = tbl_informacion_registradora.FK_INTERVALO_DESPACHO
                WHERE tbl_intervalo_despacho.FECHA_INICIAL BETWEEN %s AND %s
                    AND tbl_intervalo_despacho.ESTADO = 1
                    AND tbl_intervalo_despacho.PK_INTERVALO_DESPACHO > %s
                    AND tbl_informacion_registradora.FECHA_SALIDA_BASE_SALIDA BETWEEN %s AND %s
            ) AS ta
            LEFT JOIN (
                SELECT
                    FK_INFORMACION_REGISTRADORA, SUM(CANTIDAD_ALARMA) AS ALARMAS
                FROM tbl_alarma_info_regis
                WHERE FK_ALARMA IN ('5', '6')
                GROUP BY FK_INFORMACION_REGISTRADORA
            ) AS alarmas
            ON ta.PK_INFORMACION_REGISTRADORA = alarmas.FK_INFORMACION_REGISTRADORA
            LEFT JOIN tbl_vehiculo AS veh
            ON ta.FK_VEHICULO = veh.PK_VEHICULO
        """
        cursor.execute(query, (fecha_ini, fecha_fin, max_pk, fecha_ini, fecha_fin))
        rows = cursor.fetchall()
        cursor.close()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Error as e:
        logger.error("Error al obtener despachos: %s", e)
        return None


def actualizar_despachos_desde_bd(fecha_ini="2024-04-16"):
    # cargar existentes para max_pk
    df_exist = cargar_csv_si_existe(DESPACHOS_CSV)
    if df_exist is not None and "PK_INTERVALO_DESPACHO" in df_exist.columns:
        max_pk = int(pd.to_numeric(df_exist["PK_INTERVALO_DESPACHO"], errors="coerce").max())
        max_pk = 0 if np.isnan(max_pk) else max_pk
    else:
        max_pk = 0

    fecha_fin = pd.to_datetime("today").strftime("%Y-%m-%d")

    con = conectar_bd("bd_montebello_rdw")
    nuevos = obtener_despachos(con, fecha_ini, fecha_fin, max_pk)
    cerrar_conexion(con)

    if nuevos is None:
        raise RuntimeError("No se pudo consultar despachos en BD.")

    df_total = nuevos if df_exist is None else pd.concat([df_exist, nuevos], ignore_index=True)

    # eliminar duplicados por PK
    if not df_total.empty:
        df_total["PK_INTERVALO_DESPACHO"] = pd.to_numeric(
            df_total["PK_INTERVALO_DESPACHO"], errors="coerce"
        )
        df_total = df_total.drop_duplicates(subset=["PK_INTERVALO_DESPACHO"], keep="last")

    guardar_csv(df_total, DESPACHOS_CSV)
    logger.info("Nuevos despachos traídos: %d", len(nuevos))
    return df_total


def run_block3() -> pd.DataFrame:
    """Bloque 3: Extraccion incremental de despachos desde Registel MySQL."""
    inicializar_entorno(verbose=False)
    despachos = actualizar_despachos_desde_bd(fecha_ini="2024-04-16")
    logger.info("BLOQUE 3 - total despachos: %d", len(despachos))
    return despachos
