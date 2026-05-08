"""Clasificacion del fin de recorrido usando senales GPS."""

import logging
import os
from datetime import timedelta

import pandas as pd
from mysql.connector import Error

from .config import END_PATH, QC_PATH, TRIP_END_CONFIG, inicializar_entorno
from .db import asegurar_conexion, cerrar_conexion, conectar_bd
from .utils import display

logger = logging.getLogger(__name__)

PK_COL = "PK_INTERVALO_DESPACHO"
COL_PLACA = "PLACA"
COL_HI = "HORA_INICIAL_REAL"
COL_HF = "HORA_FINAL_REAL"
TABLA_GPS: str = TRIP_END_CONFIG["tabla_gps"]

BUFFER_MIN: int = TRIP_END_CONFIG["buffer_min"]
VENTANA_MIN: int = TRIP_END_CONFIG["ventana_min"]

VEL_BAJA: float = TRIP_END_CONFIG["vel_baja_kmh"]
VEL_RETORNO: float = TRIP_END_CONFIG["vel_retorno_kmh"]
COLA_EVAL_MIN: int = TRIP_END_CONFIG["cola_eval_min"]
PCT_BAJA: float = TRIP_END_CONFIG["pct_baja"]
USAR_MSG_APAGADO: bool = TRIP_END_CONFIG["usar_msg_apagado"]
W_MSG: float = TRIP_END_CONFIG["w_msg"]
MSG_APAGADO: str = TRIP_END_CONFIG["msg_apagado"]


def fetch_gps_events_by_time_window(con_gps, placa, t_ini, t_fin, tabla=TABLA_GPS):
    con_gps = asegurar_conexion(con_gps, "bd_montebello_rdw_gps")
    if con_gps is None:
        logger.warning("Sin conexión GPS para placa=%s. Ventana %s - %s", placa, t_ini, t_fin)
        return pd.DataFrame()

    try:
        cursor = con_gps.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT fecha_gps, velocidad, rumbo_radianes, msg, latitud, longitud
            FROM {tabla}
            WHERE placa=%s AND fecha_gps BETWEEN %s AND %s
            ORDER BY fecha_gps
        """,
            (placa, t_ini, t_fin),
        )
        rows = cursor.fetchall()
        cursor.close()
    except Error as e:
        logger.warning("Consulta GPS falló para placa=%s: %s", placa, e)
        return pd.DataFrame()

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if df.empty:
        return df

    df["fecha_gps"] = pd.to_datetime(df["fecha_gps"], errors="coerce")
    df = df[df["fecha_gps"].notna()].sort_values("fecha_gps")

    if "velocidad" in df.columns:
        df["velocidad"] = pd.to_numeric(df["velocidad"], errors="coerce")

    if "rumbo_radianes" in df.columns:
        df["rumbo_radianes"] = pd.to_numeric(df["rumbo_radianes"], errors="coerce")

    if "msg" in df.columns:
        df["msg"] = df["msg"].astype(str)

    return df


def classify_trip_end_from_gps_signals(
    dispatch_df,
    vel_baja=VEL_BAJA,
    vel_retorno=VEL_RETORNO,
    cola_eval_min=COLA_EVAL_MIN,
    pct_baja=PCT_BAJA,
    usar_msg_apagado=USAR_MSG_APAGADO,
    w_msg=W_MSG,
):
    """
    dispatch_df: eventos GPS posteriores al inicio (fecha_gps >= HI)
    Retorna: (hora_fin_estimada, fin_tipo)
    """
    if dispatch_df is None or dispatch_df.empty:
        return None, "SIN_GPS_POST_INICIO"

    fin = dispatch_df.iloc[-1]["fecha_gps"]

    # Si no hay velocidad usable, no inventamos:
    if "velocidad" not in dispatch_df.columns:
        return fin, "TRUNCADO_INDETERMINADO"

    dvel = dispatch_df[dispatch_df["velocidad"].notna()].copy()
    if dvel.empty:
        return fin, "TRUNCADO_INDETERMINADO"

    t0 = fin - pd.Timedelta(minutes=cola_eval_min)
    cola = dvel[dvel["fecha_gps"] >= t0]
    if cola.empty:
        cola = dvel.tail(10)

    frac_baja = float((cola["velocidad"] <= vel_baja).mean())
    med_vel = float(cola["velocidad"].median())

    score_abandono = frac_baja

    # FIX: aquí era "df", debe ser dispatch_df
    if usar_msg_apagado and "msg" in dispatch_df.columns:
        cola_msg = dispatch_df[dispatch_df["fecha_gps"] >= t0]
        apagado = cola_msg["msg"].str.contains(MSG_APAGADO, na=False).any()
        if apagado:
            score_abandono = min(1.0, (1 - w_msg) * score_abandono + w_msg * 1.0)

    if score_abandono >= pct_baja:
        return fin, "TRUNCADO_ABANDONO"

    if med_vel >= vel_retorno:
        return fin, "TRUNCADO_RETORNO"

    return fin, "TRUNCADO_INDETERMINADO"


def apply_final_postprocessing_adjustments(df, col_hf=COL_HF):
    """
    Asegura que los completos siempre queden consistentes,
    incluso si por accidente algo los tocó.
    """
    df = df.copy()
    mask_completo = df[col_hf].notna()
    df.loc[mask_completo, "RECORRIDO_COMPLETO"] = 1
    df.loc[mask_completo, "HORA_FIN_ESTIMADA"] = df.loc[mask_completo, col_hf]
    df.loc[mask_completo, "FIN_TIPO"] = "COMPLETO"
    df.loc[mask_completo, "HORA_FIN_FUENTE"] = "REAL"
    return df


def merge_block7_results(
    base: pd.DataFrame, updates: pd.DataFrame, *, pk_col=PK_COL, col_hf=COL_HF
) -> pd.DataFrame:
    """
    Mezcla resultados parciales/finales del Bloque 7 sobre la base actual
    sin sobrescribir valores ya existentes no nulos.
    """
    merged = base.copy()

    if updates is None or updates.empty:
        return apply_final_postprocessing_adjustments(merged, col_hf=col_hf)

    updates = updates.drop_duplicates(subset=[pk_col]).copy()
    merged = merged.merge(updates, on=pk_col, how="left", suffixes=("", "_gps"))

    for col in ["RECORRIDO_COMPLETO", "HORA_FIN_ESTIMADA", "FIN_TIPO", "HORA_FIN_FUENTE"]:
        gps_col = col + "_gps"
        if gps_col in merged.columns:
            merged[col] = merged[col].combine_first(merged[gps_col])
            merged.drop(columns=[gps_col], inplace=True)

    return apply_final_postprocessing_adjustments(merged, col_hf=col_hf)


def save_block7_checkpoint(
    base: pd.DataFrame,
    updates: pd.DataFrame,
    checkpoint_path: str,
    *,
    pk_col=PK_COL,
    col_hf=COL_HF,
    debug: bool = True,
) -> None:
    """
    Guarda un checkpoint consistente del Bloque 7 para reanudar sin perder avance.
    """
    if not checkpoint_path:
        return

    checkpoint_df = merge_block7_results(base, updates, pk_col=pk_col, col_hf=col_hf)
    tmp_path = checkpoint_path + ".tmp"
    checkpoint_df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, checkpoint_path)

    if debug:
        done = int(updates["FIN_TIPO"].notna().sum()) if "FIN_TIPO" in updates.columns else 0
        logger.info(
            "BLOQUE 7 - checkpoint guardado en %s con %d truncados resueltos", checkpoint_path, done
        )


def resolve_trip_end_using_gps_window(
    df_trunc,
    con_gps,
    *,
    pk_col=PK_COL,
    col_placa=COL_PLACA,
    col_hi=COL_HI,
    tabla_gps=TABLA_GPS,
    buffer_min=BUFFER_MIN,
    ventana_min=VENTANA_MIN,
    vel_baja=VEL_BAJA,
    vel_retorno=VEL_RETORNO,
    cola_eval_min=COLA_EVAL_MIN,
    pct_baja=PCT_BAJA,
    usar_msg_apagado=USAR_MSG_APAGADO,
    w_msg=W_MSG,
    checkpoint_base: pd.DataFrame | None = None,
    checkpoint_path: str | None = None,
    checkpoint_every: int = 500,
    checkpoint_col_hf=COL_HF,
    debug=True,
):
    """
    Procesa truncados con 1 consulta por despacho (ventana acotada).
    """
    out = df_trunc[[pk_col, col_placa, col_hi]].copy()
    out = out.drop_duplicates(subset=[pk_col])
    out[col_hi] = pd.to_datetime(out[col_hi], errors="coerce")

    out["RECORRIDO_COMPLETO"] = 0
    out["HORA_FIN_ESTIMADA"] = pd.NaT
    out["FIN_TIPO"] = None
    out["HORA_FIN_FUENTE"] = None

    n = len(out)
    processed = 0

    def _record_result(idx, *, fin_tipo, fuente, hora_fin=pd.NaT):
        nonlocal processed

        out.loc[idx, "HORA_FIN_ESTIMADA"] = hora_fin if hora_fin is not None else pd.NaT
        out.loc[idx, "FIN_TIPO"] = fin_tipo
        out.loc[idx, "HORA_FIN_FUENTE"] = fuente

        processed += 1

        if debug and processed % 500 == 0:
            logger.info("… procesados %d/%d truncados", processed, n)

        if (
            checkpoint_base is not None
            and checkpoint_path
            and checkpoint_every > 0
            and processed % checkpoint_every == 0
        ):
            updates_done = out.loc[
                out["FIN_TIPO"].notna(),
                [pk_col, "RECORRIDO_COMPLETO", "HORA_FIN_ESTIMADA", "FIN_TIPO", "HORA_FIN_FUENTE"],
            ].copy()
            save_block7_checkpoint(
                checkpoint_base,
                updates_done,
                checkpoint_path,
                pk_col=pk_col,
                col_hf=checkpoint_col_hf,
                debug=debug,
            )

    for i, r in out.iterrows():
        # Si existe asegurar_conexion, úsala. Si no, sigue normal.
        if "asegurar_conexion" in globals():
            con_gps = asegurar_conexion(con_gps, "bd_montebello_rdw_gps")

        placa = r[col_placa]
        hi = r[col_hi]

        if pd.isna(placa) or str(placa).strip() == "" or pd.isna(hi):
            _record_result(i, fin_tipo="SIN_PLACA_O_INICIO", fuente="SIN_INFO")
            continue

        t_ini = hi - timedelta(minutes=buffer_min)
        t_fin = hi + timedelta(minutes=ventana_min)

        df_gps = fetch_gps_events_by_time_window(con_gps, placa, t_ini, t_fin, tabla=tabla_gps)

        if df_gps.empty:
            _record_result(i, fin_tipo="SIN_GPS", fuente="SIN_INFO")
            continue

        df_post = df_gps[df_gps["fecha_gps"] >= hi].copy()

        if df_post.empty:
            _record_result(i, fin_tipo="SIN_GPS_POST_INICIO", fuente="SIN_INFO")
            continue

        hora_fin, fin_tipo = classify_trip_end_from_gps_signals(
            df_post,
            vel_baja=vel_baja,
            vel_retorno=vel_retorno,
            cola_eval_min=cola_eval_min,
            pct_baja=pct_baja,
            usar_msg_apagado=usar_msg_apagado,
            w_msg=w_msg,
        )

        _record_result(
            i,
            fin_tipo=fin_tipo,
            fuente="GPS_ESTIMADA" if hora_fin is not None else "SIN_INFO",
            hora_fin=hora_fin,
        )

    if debug:
        logger.info(
            "BLOQUE 7 - FIN_TIPO (truncados): %s",
            out["FIN_TIPO"].value_counts(dropna=False).to_dict(),
        )

    return out[
        [pk_col, "RECORRIDO_COMPLETO", "HORA_FIN_ESTIMADA", "FIN_TIPO", "HORA_FIN_FUENTE"]
    ].drop_duplicates(subset=[pk_col])


def classify_trip_end_block7(
    despachos: pd.DataFrame,
    con_gps,
    *,
    pk_col=PK_COL,
    col_placa=COL_PLACA,
    col_hi=COL_HI,
    col_hf=COL_HF,
    tabla_gps=TABLA_GPS,
    buffer_min=BUFFER_MIN,
    ventana_min=VENTANA_MIN,
    checkpoint_path: str | None = None,
    checkpoint_every: int = 500,
    debug=True,
    recompute_estimated: bool = False,
):
    base = despachos.copy()

    # normaliza tipos
    base[col_hi] = pd.to_datetime(base[col_hi], errors="coerce")
    base[col_hf] = pd.to_datetime(base[col_hf], errors="coerce")

    # 1) Asegurar columnas del Bloque 7 SIN borrar lo existente
    if "RECORRIDO_COMPLETO" not in base.columns:
        base["RECORRIDO_COMPLETO"] = 0
    if "HORA_FIN_ESTIMADA" not in base.columns:
        base["HORA_FIN_ESTIMADA"] = pd.NaT
    if "FIN_TIPO" not in base.columns:
        base["FIN_TIPO"] = None
    if "HORA_FIN_FUENTE" not in base.columns:
        base["HORA_FIN_FUENTE"] = None

    # 2) Completos siempre mandan (si hay HF real, no hay discusión)
    m_ok = base[col_hf].notna()
    base.loc[m_ok, "RECORRIDO_COMPLETO"] = 1
    base.loc[m_ok, "HORA_FIN_ESTIMADA"] = base.loc[m_ok, col_hf]
    base.loc[m_ok, "FIN_TIPO"] = "COMPLETO"
    base.loc[m_ok, "HORA_FIN_FUENTE"] = "REAL"

    # 3) Truncados (HF real nula)
    m_trunc = base[col_hf].isna() & base[col_hi].notna()

    # 4) Pendientes: truncados sin estimación previa (a menos que se fuerce recompute)
    if recompute_estimated:
        m_pend = m_trunc
    else:
        m_pend = m_trunc & (base["HORA_FIN_ESTIMADA"].isna() | base["FIN_TIPO"].isna())

    trunc = base.loc[m_pend, [pk_col, col_placa, col_hi]].copy()

    if debug:
        logger.info("BLOQUE 7 - truncados totales: %d", int(m_trunc.sum()))
        logger.info("BLOQUE 7 - truncados pendientes a procesar: %d", len(trunc))

    # 5) Resolver solo pendientes
    if len(trunc) > 0:
        res_trunc = resolve_trip_end_using_gps_window(
            trunc,
            con_gps,
            pk_col=pk_col,
            col_placa=col_placa,
            col_hi=col_hi,
            tabla_gps=tabla_gps,
            buffer_min=buffer_min,
            ventana_min=ventana_min,
            checkpoint_base=base,
            checkpoint_path=checkpoint_path,
            checkpoint_every=checkpoint_every,
            checkpoint_col_hf=col_hf,
            debug=debug,
        )

        base = merge_block7_results(base, res_trunc, pk_col=pk_col, col_hf=col_hf)

    # 6) Consistencia final: completos siempre consistentes
    return base


def run_block7() -> pd.DataFrame:
    """Bloque 7: Inferencia del fin del recorrido via telemetria GPS. Lee QC_PATH, escribe END_PATH."""
    inicializar_entorno(verbose=False)
    con_gps = conectar_bd("bd_montebello_rdw_gps")

    base = pd.read_parquet(QC_PATH)
    logger.info("BLOQUE 7 - base desde QC: %s filas=%d", QC_PATH, len(base))

    if os.path.exists(END_PATH):
        logger.info("BLOQUE 7 - cargando estimaciones previas desde: %s", END_PATH)
        prev = pd.read_parquet(END_PATH)[
            [PK_COL, "RECORRIDO_COMPLETO", "HORA_FIN_ESTIMADA", "FIN_TIPO", "HORA_FIN_FUENTE"]
        ].drop_duplicates(subset=[PK_COL])

        base = base.merge(prev, on=PK_COL, how="left", suffixes=("", "_prev"))

        # Traer lo previo solo si en QC no esta
        cols_b7 = ["RECORRIDO_COMPLETO", "HORA_FIN_ESTIMADA", "FIN_TIPO", "HORA_FIN_FUENTE"]
        for c in cols_b7:
            cprev = c + "_prev"
            if cprev in base.columns:
                base[c] = base[c].combine_first(base[cprev])
                base.drop(columns=[cprev], inplace=True)

    despachos_end = classify_trip_end_block7(
        base, con_gps, checkpoint_path=END_PATH, checkpoint_every=500, debug=True
    )
    despachos_end.to_parquet(END_PATH, index=False)

    display(
        despachos_end[
            [
                "PK_INTERVALO_DESPACHO",
                "PLACA",
                "HORA_INICIAL_REAL",
                "HORA_FINAL_REAL",
                "HORA_FIN_ESTIMADA",
                "FIN_TIPO",
                "HORA_FIN_FUENTE",
            ]
        ].head()
    )
    cerrar_conexion(con_gps)
    return despachos_end
