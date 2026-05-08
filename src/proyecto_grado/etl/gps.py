"""Funciones geoespaciales, GPS e imputacion de hora inicial."""

import logging
import os
from datetime import timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm

from .config import DESPACHOS_CSV, GPS_CONFIG, RUTAS_OPERATIVAS, inicializar_entorno
from .db import asegurar_conexion, cerrar_conexion, conectar_bd, guardar_csv
from .utils import display

logger = logging.getLogger(__name__)

RUN_VALIDATION = False

PUNTOS: dict = GPS_CONFIG["puntos"]
RADIO_GEOCERCA_M: int = GPS_CONFIG["radio_geocerca_m"]
RADIO_VALIDACION_M: int = GPS_CONFIG["radio_validacion_m"]


def haversine_m_local(lat1, lon1, lat2, lon2):
    r = 6371000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2.0) ** 2
    return 2 * r * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def normalizar_latlon_local(df, col_lat="latitud", col_lon="longitud"):
    df = df.copy()
    df[col_lat] = df[col_lat].astype(str).str.strip().str.replace(",", ".", regex=False)
    df[col_lon] = df[col_lon].astype(str).str.strip().str.replace(",", ".", regex=False)
    df[col_lat] = pd.to_numeric(df[col_lat], errors="coerce")
    df[col_lon] = pd.to_numeric(df[col_lon], errors="coerce")
    df = df[df[col_lat].notna() & df[col_lon].notna()]
    df = df[(df[col_lat].between(-90, 90)) & (df[col_lon].between(-180, 180))]
    return df


def obtener_placa_local(conexion, pk_vehiculo):
    cursor = conexion.cursor()
    cursor.execute("SELECT PLACA FROM tbl_vehiculo WHERE PK_VEHICULO = %s", (pk_vehiculo,))
    r = cursor.fetchone()
    cursor.close()
    return r[0] if r else None


def obtener_detalle_rastreo_local(conexion, fecha_ini, fecha_fin, placa):
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT fecha_gps, msg, latitud, longitud
        FROM tbl_forwarding_wtch
        WHERE placa=%s AND fecha_gps BETWEEN %s AND %s
        ORDER BY fecha_gps
    """,
        (placa, fecha_ini, fecha_fin),
    )
    rows = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _cargar_despachos_para_validacion():
    logger.warning("Variable 'despachos' no definida. Cargando CSV...")
    _path = globals().get(
        "DESPACHOS_CSV", "/content/drive/MyDrive/proyecto_grado/datos/despachos_raw_historico.csv"
    )
    if os.path.exists(_path):
        df = pd.read_csv(_path)
        df["HORA_INICIAL_REAL"] = pd.to_datetime(df["HORA_INICIAL_REAL"], errors="coerce")
        df["HORA_INICIAL_PLAN"] = pd.to_datetime(df["HORA_INICIAL_PLAN"], errors="coerce")
        logger.info("Datos cargados: %d", len(df))
        return df
    return pd.DataFrame()


def validar_radio_con_nulos(df, n_muestras=200):
    logger.info("Analizando registros NULOS (sin hora real)...")

    # FILTRO: Solo los que NO tienen hora real (Nulos)
    # Usamos HORA_INICIAL_PLAN como proxy
    df_nulos = df[
        (df["HORA_INICIAL_REAL"].isna())
        & (df["HORA_INICIAL_PLAN"].notna())
        & (df["FK_VEHICULO"].notna())
        & (df["FK_RUTA"].isin(RUTAS_OPERATIVAS))
    ].copy()

    total_nulos = len(df_nulos)
    logger.info("Total registros nulos disponibles: %d", total_nulos)

    if total_nulos == 0:
        logger.warning("No hay registros nulos para analizar en el dataset actual.")
        return

    if total_nulos < n_muestras:
        muestra = df_nulos
    else:
        muestra = df_nulos.sample(n=n_muestras, random_state=42)

    distancias_proxy = []

    try:
        con_gps = conectar_bd("bd_montebello_rdw_gps")
        con_pri = conectar_bd("bd_montebello_rdw")
    except NameError:
        logger.error("Conexión DB no disponible.")
        return

    for _, row in tqdm(muestra.iterrows(), total=len(muestra)):
        placa = row.get("PLACA")
        if pd.isna(placa):
            placa = obtener_placa_local(con_pri, row["FK_VEHICULO"])
        if not placa:
            continue

        # PROXY: Usamos la hora PLANIFICADA
        hora_ref = pd.to_datetime(row["HORA_INICIAL_PLAN"])
        ruta = row["FK_RUTA"]
        nombre_punto = "MORICHAL" if ruta == 3 else "MOJICA"
        coords_teoricas = PUNTOS.get(nombre_punto)

        # Ventana amplia (+- 10 min) alrededor de la hora planificada
        t0 = hora_ref - timedelta(minutes=10)
        t1 = hora_ref + timedelta(minutes=10)

        gps_data = obtener_detalle_rastreo_local(con_gps, t0, t1, placa)

        if gps_data is not None and not gps_data.empty:
            gps_data = normalizar_latlon_local(gps_data)
            if gps_data.empty:
                continue

            gps_data["dist_ref"] = haversine_m_local(
                gps_data["latitud"].values,
                gps_data["longitud"].values,
                coords_teoricas["lat"],
                coords_teoricas["lon"],
            )

            # Mínima distancia en esa ventana (el momento más cercano al patio)
            min_dist = gps_data["dist_ref"].min()
            distancias_proxy.append(min_dist)

    cerrar_conexion(con_gps)
    cerrar_conexion(con_pri)

    if distancias_proxy:
        s = pd.Series(distancias_proxy)
        logger.info(
            "RESULTADOS (Muestra Nulos usando Hora Plan):\n%s",
            s.describe(percentiles=[0.5, 0.75, 0.90, 0.95, 0.99]),
        )

        plt.figure(figsize=(10, 4))
        plt.hist(s, bins=30, color="salmon", edgecolor="black", alpha=0.7)
        plt.axvline(
            s.quantile(0.95), color="red", linestyle="--", label=f"P95: {s.quantile(0.95):.1f}m"
        )
        plt.axvline(700, color="green", linewidth=2, label="Radio (700m)")
        plt.title("Distancia mínima al patio (Hora Planificada) en registros Nulos")
        plt.xlabel("Distancia (metros)")
        plt.ylabel("Frecuencia")
        plt.legend()
        plt.show()
    else:
        logger.warning("No se encontró GPS para la muestra de nulos.")


def run_radio_validation(df=None, n_muestras=100):
    """Ejecuta la validacion metodologica de radio solo cuando se solicita."""
    if df is None:
        df = globals().get("despachos")
    if df is None:
        df = _cargar_despachos_para_validacion()
    if df is None or df.empty:
        print("⚠️ No hay despachos disponibles para validar radio.")
        return None
    return validar_radio_con_nulos(df, n_muestras=n_muestras)


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2.0) ** 2
    return 2 * r * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def normalizar_latlon(df, col_lat="latitud", col_lon="longitud"):
    df = df.copy()
    df[col_lat] = df[col_lat].astype(str).str.strip().str.replace(",", ".", regex=False)
    df[col_lon] = df[col_lon].astype(str).str.strip().str.replace(",", ".", regex=False)
    df[col_lat] = pd.to_numeric(df[col_lat], errors="coerce")
    df[col_lon] = pd.to_numeric(df[col_lon], errors="coerce")
    df = df[df[col_lat].notna() & df[col_lon].notna()]
    df = df[(df[col_lat].between(-90, 90)) & (df[col_lon].between(-180, 180))]
    return df


def encontrar_hora_salida_por_geocerca(
    hora_plan_dt,
    datos_rastreo,
    lat_punto,
    lon_punto,
    radio_m=RADIO_VALIDACION_M,
    col_lat="latitud",
    col_lon="longitud",
):
    if datos_rastreo is None or datos_rastreo.empty or pd.isna(hora_plan_dt):
        return None

    df = datos_rastreo.copy()
    df["fecha_gps"] = pd.to_datetime(df["fecha_gps"], errors="coerce")
    df = df[df["fecha_gps"].notna()]
    if df.empty:
        return None

    if col_lat not in df.columns or col_lon not in df.columns:
        return None

    df = normalizar_latlon(df, col_lat=col_lat, col_lon=col_lon)
    if df.empty:
        return None

    df["dist_m"] = haversine_m(df[col_lat].values, df[col_lon].values, lat_punto, lon_punto)
    dentro = df[df["dist_m"] <= radio_m].sort_values("fecha_gps")

    return dentro.iloc[0]["fecha_gps"] if not dentro.empty else None


def obtener_placa(conexion, pk_vehiculo):
    cursor = conexion.cursor()
    cursor.execute("SELECT PLACA FROM tbl_vehiculo WHERE PK_VEHICULO = %s", (pk_vehiculo,))
    r = cursor.fetchone()
    cursor.close()
    return r[0] if r else None


def obtener_detalle_rastreo(conexion, fecha_ini, fecha_fin, placa):
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT fecha_gps, msg, latitud, longitud
        FROM tbl_forwarding_wtch
        WHERE placa=%s AND fecha_gps BETWEEN %s AND %s
        ORDER BY fecha_gps
    """,
        (placa, fecha_ini, fecha_fin),
    )
    rows = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def encontrar_hora_salida(hora_plan_dt, datos_rastreo, nombre_punto, radio_m=RADIO_GEOCERCA_M):
    if datos_rastreo is None or datos_rastreo.empty or pd.isna(hora_plan_dt):
        return None

    df = datos_rastreo.copy()
    df["fecha_gps"] = pd.to_datetime(df["fecha_gps"], errors="coerce")
    df = df[df["fecha_gps"].notna()]
    if df.empty:
        return None

    # 1) Buscar por texto (normalizado)
    if "msg" in df.columns:
        msg = df["msg"].astype(str).str.upper()
        nom = str(nombre_punto).upper()
        filtro = df[msg.str.contains(nom, na=False)].sort_values("fecha_gps")
        if not filtro.empty:
            return filtro.iloc[0]["fecha_gps"]

    # 2) Fallback: geocerca
    p = PUNTOS.get(nombre_punto)
    if not p:
        return None

    return encontrar_hora_salida_por_geocerca(
        hora_plan_dt, df, lat_punto=p["lat"], lon_punto=p["lon"], radio_m=radio_m
    )


def run_block5(despachos: pd.DataFrame) -> pd.DataFrame:
    """Bloque 5: Imputacion de HORA_INICIAL_REAL via telemetria GPS (Haversine + geocerca)."""
    inicializar_entorno(verbose=False)
    con_pri = conectar_bd("bd_montebello_rdw")
    con_gps = conectar_bd("bd_montebello_rdw_gps")

    filtro = (
        despachos["HORA_INICIAL_REAL"].isna()
        | (despachos["HORA_INICIAL_REAL"].astype(str).str.strip() == "")
    ) & (despachos["FK_RUTA"].isin(RUTAS_OPERATIVAS))
    faltantes = despachos.loc[filtro].copy()

    logger.info("BLOQUE 5 - despachos con HORA_INICIAL_REAL faltante: %d", len(faltantes))

    ventanas_min = GPS_CONFIG["ventanas_busqueda_min"]

    updates = []  # (pk_intervalo, hora_salida)
    audit = []  # (pk_intervalo, placa, ruta, ventana_usada, resultado) opcional para tesis

    for _, row in tqdm(faltantes.iterrows(), total=len(faltantes)):
        con_pri = asegurar_conexion(con_pri, "bd_montebello_rdw")
        con_gps = asegurar_conexion(con_gps, "bd_montebello_rdw_gps")

        pk = row.get("PK_INTERVALO_DESPACHO")
        placa = row.get("PLACA")
        ruta = row.get("FK_RUTA")

        if pd.isna(pk):
            continue

        if pd.isna(placa) or str(placa).strip() == "":
            placa = obtener_placa(con_pri, row.get("FK_VEHICULO"))
            if placa is None:
                audit.append((pk, None, ruta, None, "SIN_PLACA"))
                continue

        hora_plan = pd.to_datetime(row.get("HORA_INICIAL_PLAN"), errors="coerce")
        if pd.isna(hora_plan):
            audit.append((pk, placa, ruta, None, "SIN_HORA_PLAN"))
            continue

        nombre_punto = "MORICHAL" if ruta == 3 else "MOJICA"

        hora_salida = None
        ventana_usada = None

        # Intentos escalonados
        for mins in ventanas_min:
            t0 = hora_plan - timedelta(minutes=mins)
            t1 = hora_plan + timedelta(minutes=mins)

            detalle = obtener_detalle_rastreo(con_gps, t0, t1, placa)
            if detalle is None or detalle.empty:
                continue

            hora_salida = encontrar_hora_salida(hora_plan, detalle, nombre_punto)
            if hora_salida is not None:
                ventana_usada = mins
                break

        if hora_salida is not None:
            updates.append((pk, hora_salida))
            audit.append((pk, placa, ruta, ventana_usada, "OK"))
        else:
            audit.append((pk, placa, ruta, None, "NO_ENCONTRADO"))

    # Aplicar updates por PK
    if updates:
        upd_df = pd.DataFrame(updates, columns=["PK_INTERVALO_DESPACHO", "HORA_INICIAL_REAL_EST"])
        despachos = despachos.merge(upd_df, on="PK_INTERVALO_DESPACHO", how="left")

        m = despachos["HORA_INICIAL_REAL"].isna() & despachos["HORA_INICIAL_REAL_EST"].notna()
        despachos.loc[m, "HORA_INICIAL_REAL"] = despachos.loc[m, "HORA_INICIAL_REAL_EST"]

        despachos.drop(columns=["HORA_INICIAL_REAL_EST"], inplace=True)

    # (Opcional) Auditoria: util para tesis y debug
    audit_df = pd.DataFrame(
        audit,
        columns=["PK_INTERVALO_DESPACHO", "PLACA", "FK_RUTA", "VENTANA_MIN_USADA", "RESULTADO"],
    )
    display(audit_df["RESULTADO"].value_counts(dropna=False))
    display(audit_df.head(10))

    cerrar_conexion(con_pri)
    cerrar_conexion(con_gps)

    logger.info("BLOQUE 5 - actualizaciones HORA_INICIAL_REAL: %d", len(updates))
    guardar_csv(despachos, DESPACHOS_CSV)

    desp = despachos.copy()

    desp["HORA_INICIAL_REAL"] = pd.to_datetime(desp["HORA_INICIAL_REAL"], errors="coerce")
    desp["HORA_FINAL_REAL"] = pd.to_datetime(desp["HORA_FINAL_REAL"], errors="coerce")
    desp["HORA_FINAL_PLAN"] = pd.to_datetime(desp["HORA_FINAL_PLAN"], errors="coerce")

    # Etiquetas
    desp["RECORRIDO_COMPLETO"] = np.where(desp["HORA_FINAL_REAL"].notna(), 1, 0)
    desp["HORA_FINAL_FUENTE"] = np.where(desp["HORA_FINAL_REAL"].notna(), "REAL", "SIN_FIN")
    desp["MOTIVO_FIN"] = np.where(desp["HORA_FINAL_REAL"].notna(), "COMPLETO", "TRUNCADO_SIN_FIN")

    # Orden temporal solo si ambas horas existen
    mask_ambas = desp["HORA_INICIAL_REAL"].notna() & desp["HORA_FINAL_REAL"].notna()
    desp["FLAG_ORDEN_TEMPORAL_INVALIDO"] = False
    desp.loc[mask_ambas, "FLAG_ORDEN_TEMPORAL_INVALIDO"] = ~(
        desp.loc[mask_ambas, "HORA_FINAL_REAL"] > desp.loc[mask_ambas, "HORA_INICIAL_REAL"]
    )

    # Dataset para demanda/zonas
    desp_demanda = desp[(desp["ESTADO_DESPACHO"] != 4) & (desp["HORA_INICIAL_REAL"].notna())].copy()

    # Dataset para analisis de duracion/tiempos
    desp_tiempos = desp[
        (desp["ESTADO_DESPACHO"] != 4)
        & (desp["RECORRIDO_COMPLETO"] == 1)
        & ~desp["FLAG_ORDEN_TEMPORAL_INVALIDO"]
    ].copy()

    logger.info("BLOQUE 5 - despachos demanda/zonas: %d", len(desp_demanda))
    logger.info("BLOQUE 5 - despachos completos para tiempos: %d", len(desp_tiempos))
    return despachos
