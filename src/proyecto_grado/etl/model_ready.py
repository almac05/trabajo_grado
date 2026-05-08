"""Construccion, exportacion y trazabilidad del dataset model-ready.

Este modulo contiene las etapas finales del ETL: prepara el dataset que sera
usado por los modelos predictivos, genera controles de calidad finales y guarda
versiones trazables de la salida procesada.
"""

import json
import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd

from .config import END_PATH, ETL_REPORTS_DIR, MODEL_READY_DIR, inicializar_entorno
from .utils import display

logger = logging.getLogger(__name__)


def run_block8() -> pd.DataFrame:
    """Construye el dataset model-ready a partir de la salida del Bloque 7.

    La funcion carga el parquet definido por ``END_PATH``, normaliza columnas
    temporales y numericas, calcula la hora final consolidada del recorrido,
    deriva variables temporales y operacionales, aplica reglas basicas de
    consistencia y conserva solo los registros aptos para modelado.

    Como salida operativa, guarda el dataset model-ready en formato parquet y
    CSV dentro de ``MODEL_READY_DIR``. Tambien retorna el DataFrame filtrado para
    facilitar pruebas, inspeccion o ejecuciones interactivas.

    Returns:
        pd.DataFrame: Dataset final filtrado con los registros aptos para
        modelado.

    Raises:
        FileNotFoundError: Si no existe la salida del Bloque 7 requerida en
        ``END_PATH``.
    """
    inicializar_entorno(verbose=False)
    if not os.path.exists(END_PATH):
        raise FileNotFoundError(f"No existe END_PATH. Ejecuta Bloque 7 primero: {END_PATH}")

    df = pd.read_parquet(END_PATH)
    logger.info("BLOQUE 8 - cargado despachos_end: %s filas=%d", END_PATH, len(df))

    # Normalizar datetimes y numericos
    for c in ["HORA_INICIAL_REAL", "HORA_FINAL_REAL", "HORA_FIN_ESTIMADA", "FECHA_INICIAL"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["PASAJEROS", "DISTANCIA", "FK_RUTA"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Hora fin final (real o estimada)
    df["HORA_FIN_FINAL"] = df["HORA_FINAL_REAL"].combine_first(df["HORA_FIN_ESTIMADA"])

    # Variables temporales y operacionales
    df["DURACION_MIN_FINAL"] = (
        df["HORA_FIN_FINAL"] - df["HORA_INICIAL_REAL"]
    ).dt.total_seconds() / 60.0
    df["HORA_INICIO_H"] = df["HORA_INICIAL_REAL"].dt.hour
    df["HORA_FIN_H"] = df["HORA_FIN_FINAL"].dt.hour
    df["DIA_SEMANA"] = df["HORA_INICIAL_REAL"].dt.dayofweek  # 0=lunes
    df["MES"] = df["HORA_INICIAL_REAL"].dt.month
    df["DIA"] = df["HORA_INICIAL_REAL"].dt.day

    # Reglas basicas de consistencia
    m_inicio_ok = df["HORA_INICIAL_REAL"].notna()
    m_fin_ok = df["HORA_FIN_FINAL"].notna()
    dur_min = 5
    dur_max = 8 * 60
    m_dur_ok = df["DURACION_MIN_FINAL"].between(dur_min, dur_max, inclusive="both")

    m_qc_ok = ~df["qc_hard_fail"].fillna(False) if "qc_hard_fail" in df.columns else True

    df["MODEL_READY_OK"] = m_inicio_ok & m_fin_ok & m_dur_ok & m_qc_ok

    cols_keep = [
        "PK_INTERVALO_DESPACHO",
        "PLACA",
        "FK_RUTA",
        "FECHA_INICIAL",
        "HORA_INICIAL_REAL",
        "HORA_FIN_FINAL",
        "DURACION_MIN_FINAL",
        "PASAJEROS",
        "DISTANCIA",
        "RECORRIDO_COMPLETO",
        "FIN_TIPO",
        "HORA_FIN_FUENTE",
        "HORA_INICIO_H",
        "HORA_FIN_H",
        "DIA_SEMANA",
        "MES",
        "DIA",
        "MODEL_READY_OK",
    ]
    cols_keep = [c for c in cols_keep if c in df.columns]
    df_model = df.loc[df["MODEL_READY_OK"], cols_keep].copy()

    logger.info("BLOQUE 8 - model_ready filas: %d de %d", len(df_model), len(df))

    os.makedirs(MODEL_READY_DIR, exist_ok=True)
    out_parquet = os.path.join(MODEL_READY_DIR, "despachos_model_ready.parquet")
    out_csv = os.path.join(MODEL_READY_DIR, "despachos_model_ready.csv")

    df_model.to_parquet(out_parquet, index=False)
    df_model.to_csv(out_csv, index=False)

    logger.info("BLOQUE 8 - exportado model-ready parquet=%s csv=%s", out_parquet, out_csv)

    display(df_model.head(10))
    return df_model


def run_block9() -> None:
    """Consolida, versiona y documenta el dataset model-ready final.

    La funcion toma como fuente principal el dataset generado por el Bloque 8.
    Si este archivo no existe, usa como respaldo la salida del Bloque 7. Luego
    aplica filtros minimos de integridad, elimina duplicados por identificador de
    despacho cuando la columna existe y calcula un reporte final de calidad.

    Finalmente, sobrescribe la version estable del dataset model-ready, genera
    una copia congelada con timestamp en parquet y CSV, y registra metadatos en
    JSON para trazabilidad del proceso, reproducibilidad y soporte documental.

    Returns:
        None: La funcion no retorna datos; sus resultados se materializan en
        archivos dentro de ``MODEL_READY_DIR`` y ``ETL_REPORTS_DIR``.

    Raises:
        FileNotFoundError: Si no existe ni el dataset model-ready del Bloque 8 ni
        la salida del Bloque 7.
    """
    inicializar_entorno(verbose=False)
    os.makedirs(MODEL_READY_DIR, exist_ok=True)

    report_dir = ETL_REPORTS_DIR
    os.makedirs(report_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_ready_path = os.path.join(MODEL_READY_DIR, "despachos_model_ready.parquet")
    freeze_path = os.path.join(MODEL_READY_DIR, f"despachos_model_ready_freeze_{stamp}.parquet")
    freeze_csv = os.path.join(MODEL_READY_DIR, f"despachos_model_ready_freeze_{stamp}.csv")
    meta_path = os.path.join(report_dir, f"model_ready_metadata_{stamp}.json")
    qc_report_path = os.path.join(report_dir, f"model_ready_qc_{stamp}.csv")

    logger.info("BLOQUE 9 - END_PATH=%s", END_PATH)
    logger.info("BLOQUE 9 - MODEL_READY_PATH=%s", model_ready_path)
    logger.info("BLOQUE 9 - REPORT_DIR=%s", report_dir)

    # Cargar base
    if os.path.exists(model_ready_path):
        df = pd.read_parquet(model_ready_path)
        fuente = "MODEL_READY_PATH (Bloque 8)"
    elif os.path.exists(END_PATH):
        df = pd.read_parquet(END_PATH)
        fuente = "END_PATH (Bloque 7)"
    else:
        raise FileNotFoundError(
            "No existe ni el dataset model-ready del Bloque 8 ni la salida del Bloque 7.\n"
            f"- Esperado Bloque 8: {model_ready_path}\n"
            f"- Esperado Bloque 7: {END_PATH}"
        )

    logger.info(
        "BLOQUE 9 - dataset cargado desde: %s filas=%d cols=%d", fuente, len(df), df.shape[1]
    )

    # Normalizaciones minimas
    for c in ["HORA_INICIAL_REAL", "HORA_FINAL_REAL", "HORA_FIN_ESTIMADA"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    if (
        "DURACION_MIN_FINAL" not in df.columns
        and ("HORA_INICIAL_REAL" in df.columns)
        and ("HORA_FIN_ESTIMADA" in df.columns)
    ):
        mask = df["HORA_INICIAL_REAL"].notna() & df["HORA_FIN_ESTIMADA"].notna()
        dur = pd.Series(np.nan, index=df.index)
        dur.loc[mask] = (
            df.loc[mask, "HORA_FIN_ESTIMADA"] - df.loc[mask, "HORA_INICIAL_REAL"]
        ).dt.total_seconds() / 60.0
        df["DURACION_MIN_FINAL"] = dur

    min_cols = [
        "PK_INTERVALO_DESPACHO",
        "PLACA",
        "FK_RUTA",
        "HORA_INICIAL_REAL",
        "HORA_FIN_ESTIMADA",
    ]
    missing = [c for c in min_cols if c not in df.columns]
    if missing:
        logger.warning("BLOQUE 9 - faltan columnas mínimas para model-ready: %s", missing)

    base = df.copy()
    if "PK_INTERVALO_DESPACHO" in base.columns:
        base = base[base["PK_INTERVALO_DESPACHO"].notna()]
    if "HORA_INICIAL_REAL" in base.columns:
        base = base[base["HORA_INICIAL_REAL"].notna()]
    if "HORA_FIN_ESTIMADA" in base.columns:
        base = base[base["HORA_FIN_ESTIMADA"].notna()]
    if "DURACION_MIN_FINAL" in base.columns:
        base = base[base["DURACION_MIN_FINAL"].isna() | (base["DURACION_MIN_FINAL"] > 0)]
    if "PK_INTERVALO_DESPACHO" in base.columns:
        base = base.drop_duplicates(subset=["PK_INTERVALO_DESPACHO"])

    logger.info("BLOQUE 9 - filas luego de filtros mínimos: %d", len(base))

    # QC final
    qc_rows = []

    def _pct(x, n):
        """Calcula el porcentaje que representa ``x`` sobre ``n``.

        Se usa en el reporte de calidad final para expresar cada conteo como
        porcentaje del total de filas evaluadas. Si el denominador es cero,
        retorna ``0.0`` para evitar divisiones invalidas.
        """
        return float(x / n * 100) if n else 0.0

    n_rows = len(base)

    if "PK_INTERVALO_DESPACHO" in base.columns:
        dup = base["PK_INTERVALO_DESPACHO"].duplicated(keep=False)
        qc_rows.append(["pk_duplicada", int(dup.sum()), _pct(int(dup.sum()), n_rows)])
    else:
        qc_rows.append(["pk_duplicada", None, None])

    if "PLACA" in base.columns:
        placa = base["PLACA"].astype(str).str.strip()
        bad = placa.isna() | placa.eq("") | placa.str.lower().isin(["nan", "none", "null"])
        qc_rows.append(["placa_vacia", int(bad.sum()), _pct(int(bad.sum()), n_rows)])
    else:
        qc_rows.append(["placa_vacia", None, None])

    if "DURACION_MIN_FINAL" in base.columns:
        bad = base["DURACION_MIN_FINAL"].notna() & (base["DURACION_MIN_FINAL"] <= 0)
        qc_rows.append(["duracion_no_positiva", int(bad.sum()), _pct(int(bad.sum()), n_rows)])
    else:
        qc_rows.append(["duracion_no_positiva", None, None])

    fin_counts = None
    if "FIN_TIPO" in base.columns:
        fin_counts = base["FIN_TIPO"].astype(str).value_counts(dropna=False).to_dict()

    qc_final = pd.DataFrame(qc_rows, columns=["regla", "conteo", "pct"])
    qc_final.to_csv(qc_report_path, index=False)

    logger.info("BLOQUE 9 - QC final:")
    display(qc_final)
    logger.info("BLOQUE 9 - QC guardado en: %s", qc_report_path)

    # Export: model-ready "ultimo" + freeze versionado
    base.to_parquet(model_ready_path, index=False)
    base.to_parquet(freeze_path, index=False)
    base.to_csv(freeze_csv, index=False)

    logger.info("BLOQUE 9 - export final: model_ready=%s freeze=%s", model_ready_path, freeze_path)

    # Metadata para tesis / trazabilidad
    meta = {
        "timestamp": stamp,
        "fuente_carga": fuente,
        "ruta_fuente": model_ready_path if fuente.startswith("MODEL_READY") else END_PATH,
        "rows_final": len(base),
        "cols_final": int(base.shape[1]),
        "columns": list(base.columns),
        "fin_tipo_counts": fin_counts,
    }

    if "DURACION_MIN_FINAL" in base.columns and base["DURACION_MIN_FINAL"].notna().any():
        desc = base["DURACION_MIN_FINAL"].describe(percentiles=[0.5, 0.9, 0.95, 0.99]).to_dict()
        meta["duracion_min_final_describe"] = {
            k: (float(v) if pd.notna(v) else None) for k, v in desc.items()
        }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("BLOQUE 9 - metadata guardada en: %s", meta_path)
    logger.info("BLOQUE 9 - dataset listo para modelado.")
