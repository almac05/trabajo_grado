"""Control de calidad y coherencia operacional de despachos."""

import datetime as _dt
import logging
import os

import numpy as np
import pandas as pd

from .config import QC_CONFIG, QC_DIR, QC_PATH, QC_REPORTS_DIR, inicializar_entorno
from .utils import display

logger = logging.getLogger(__name__)

col_pk = "PK_INTERVALO_DESPACHO"
col_placa = "PLACA"
col_ruta = "FK_RUTA"
col_estado = "ESTADO_DESPACHO"
col_hi = "HORA_INICIAL_REAL"
col_hf = "HORA_FINAL_REAL"
col_pasaj = "PASAJEROS"
col_dist = "DISTANCIA"
col_fdesp = None

HARD_FAILS = [
    "flag_pk_nula",
    "flag_pk_duplicada",
    "flag_placa_nula",
    "flag_hi_nula",
    "flag_horas_invertidas",
    "flag_duracion_negativa",
    "flag_distancia_negativa",
    "flag_pasajeros_negativos",
]

SOFT_FAILS = [
    "flag_hf_nula",
    "flag_duracion_excesiva",
    "flag_pasajeros_absurdos",
    "flag_frecuencia_fuera_rango",
]

CFG: dict = QC_CONFIG.copy()


def _join_reasons(row, cols):
    """Concatena los nombres de flags activos en una fila."""
    return ",".join([c for c in cols if row.get(c, False)])


def _fix_object_dates_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Evita ArrowTypeError: convierte datetime.date en columnas object a datetime64."""
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == "object":
            s = out[c].dropna()
            if len(s) == 0:
                continue
            if s.map(lambda x: isinstance(x, _dt.date) and not isinstance(x, _dt.datetime)).any():
                out[c] = pd.to_datetime(out[c], errors="coerce")
    return out


def validar_coherencia_operacional_avanzada(
    df: pd.DataFrame,
    *,
    col_pk=None,
    col_placa=None,
    col_ruta=None,
    col_estado=None,
    col_hi=None,
    col_hf=None,
    col_pasaj=None,
    col_dist=None,
    col_fdesp=None,
    cfg=None,
    estados_validos=None,
):
    cfg = cfg or CFG
    out = df.copy()

    def _flag(name, cond):
        out[name] = cond.fillna(False) if hasattr(cond, "fillna") else bool(cond)
        return name

    # -------------------------
    # 6.1 Chequeos estructurales
    # -------------------------
    if col_pk is not None and col_pk in out.columns:
        _flag("flag_pk_nula", out[col_pk].isna())
        _flag("flag_pk_duplicada", out[col_pk].duplicated(keep=False))
    else:
        out["flag_pk_nula"] = False
        out["flag_pk_duplicada"] = False

    if col_placa is not None and col_placa in out.columns:
        placa_raw = out[col_placa]
        placa_str = placa_raw.astype(str).str.strip()
        _flag(
            "flag_placa_nula",
            placa_raw.isna()
            | placa_str.eq("")
            | placa_str.str.lower().isin(["nan", "none", "null"]),
        )
    else:
        out["flag_placa_nula"] = True  # sin placa no sirve para GPS

    if col_hi is not None and col_hi in out.columns:
        if not pd.api.types.is_datetime64_any_dtype(out[col_hi]):
            out[col_hi] = pd.to_datetime(out[col_hi], errors="coerce")
        _flag("flag_hi_nula", out[col_hi].isna())
    else:
        out["flag_hi_nula"] = True

    if col_hf is not None and col_hf in out.columns:
        if not pd.api.types.is_datetime64_any_dtype(out[col_hf]):
            out[col_hf] = pd.to_datetime(out[col_hf], errors="coerce")
        _flag("flag_hf_nula", out[col_hf].isna())
    else:
        out["flag_hf_nula"] = False

    # -------------------------
    # 6.2 Chequeos temporales
    # -------------------------
    out["duracion_min"] = np.nan
    out["duracion_seg"] = np.nan

    if col_hi in out.columns and col_hf in out.columns:
        mask_both = out[col_hi].notna() & out[col_hf].notna()
        _flag("flag_horas_invertidas", mask_both & (out[col_hf] < out[col_hi]))

        dur_sec = (out.loc[mask_both, col_hf] - out.loc[mask_both, col_hi]).dt.total_seconds()
        out.loc[mask_both, "duracion_seg"] = dur_sec
        out.loc[mask_both, "duracion_min"] = dur_sec / 60.0

        _flag("flag_duracion_negativa", mask_both & (out["duracion_min"] < 0))
    else:
        out["flag_horas_invertidas"] = False
        out["flag_duracion_negativa"] = False

    # duración excesiva (soft)
    out["flag_duracion_excesiva"] = False
    dur = out["duracion_min"]

    if dur.notna().any():
        pctl = cfg.get("duracion_pctl_soft", 99.0)

        if col_ruta is not None and col_ruta in out.columns:
            thresh = (
                out.loc[dur.notna() & (dur >= 0)]
                .groupby(col_ruta)["duracion_min"]
                .quantile(pctl / 100.0)
            )
            out["duracion_pctl_th"] = out[col_ruta].map(thresh)
            out["flag_duracion_excesiva"] = (
                dur.notna() & out["duracion_pctl_th"].notna() & (dur > out["duracion_pctl_th"])
            )
        else:
            global_th = np.nanpercentile(dur.dropna().values, pctl)
            out["duracion_pctl_th"] = global_th
            out["flag_duracion_excesiva"] = dur.notna() & np.isfinite(global_th) & (dur > global_th)

        max_hard = cfg.get("duracion_max_min_hard", None)
        if max_hard is not None:
            out["flag_duracion_excesiva"] = out["flag_duracion_excesiva"] | (
                dur.notna() & (dur > max_hard)
            )

    # -------------------------
    # 6.3 Chequeos operacionales
    # -------------------------
    # Pasajeros
    if col_pasaj is not None and col_pasaj in out.columns:
        out[col_pasaj] = pd.to_numeric(out[col_pasaj], errors="coerce")
        _flag("flag_pasajeros_negativos", out[col_pasaj].notna() & (out[col_pasaj] < 0))

        out["flag_pasajeros_absurdos"] = False
        pax = out[col_pasaj]
        pctl_pax = cfg.get("pasajeros_pctl_soft", 99.5)

        if pax.notna().any():
            if col_ruta is not None and col_ruta in out.columns:
                pax_th = (
                    out.loc[pax.notna() & (pax >= 0)]
                    .groupby(col_ruta)[col_pasaj]
                    .quantile(pctl_pax / 100.0)
                )
                out["pasajeros_pctl_th"] = out[col_ruta].map(pax_th)
                out["flag_pasajeros_absurdos"] = (
                    pax.notna()
                    & out["pasajeros_pctl_th"].notna()
                    & (pax > out["pasajeros_pctl_th"])
                )
            else:
                global_pax_th = np.nanpercentile(pax.dropna().values, pctl_pax)
                out["pasajeros_pctl_th"] = global_pax_th
                out["flag_pasajeros_absurdos"] = pax.notna() & (pax > global_pax_th)

        pax_hard = cfg.get("pasajeros_max_hard", None)
        if pax_hard is not None:
            out["flag_pasajeros_absurdos"] = out["flag_pasajeros_absurdos"] | (
                pax.notna() & (pax > pax_hard)
            )
    else:
        out["flag_pasajeros_negativos"] = False
        out["flag_pasajeros_absurdos"] = False

    # Distancia
    if col_dist is not None and col_dist in out.columns:
        out[col_dist] = pd.to_numeric(out[col_dist], errors="coerce")
        _flag("flag_distancia_negativa", out[col_dist].notna() & (out[col_dist] < 0))
    else:
        out["flag_distancia_negativa"] = False

    # Frecuencia fuera de rango (solo si existe col_fdesp)
    if col_fdesp is not None and col_fdesp in out.columns:
        out[col_fdesp] = pd.to_numeric(out[col_fdesp], errors="coerce")
        fmin = cfg.get("freq_min_soft")
        fmax = cfg.get("freq_max_soft")
        out["flag_frecuencia_fuera_rango"] = out[col_fdesp].notna() & (
            (out[col_fdesp] < fmin) | (out[col_fdesp] > fmax)
        )
    else:
        out["flag_frecuencia_fuera_rango"] = False

    # Estado inválido (solo si se define estados_validos)
    out["flag_estado_invalido"] = False
    if col_estado is not None and col_estado in out.columns and estados_validos is not None:
        # Soporta estados numéricos o string
        valid = set(estados_validos)
        out["flag_estado_invalido"] = out[col_estado].notna() & (~out[col_estado].isin(valid))

    # -------------------------
    # 6.4 Resumen QC + razones
    # -------------------------
    flag_cols = [c for c in out.columns if c.startswith("flag_")]
    out["qc_any_flag"] = out[flag_cols].any(axis=1) if flag_cols else False

    hard_cols = [c for c in HARD_FAILS if c in out.columns]
    soft_cols = [c for c in SOFT_FAILS if c in out.columns]

    out["qc_hard_fail"] = out[hard_cols].any(axis=1) if hard_cols else False
    out["qc_soft_fail"] = (~out["qc_hard_fail"]) & (
        out[soft_cols].any(axis=1) if soft_cols else False
    )

    # Razones (trazabilidad)
    out["qc_reason_hard"] = ""
    out["qc_reason_soft"] = ""

    if hard_cols:
        out.loc[out["qc_hard_fail"], "qc_reason_hard"] = out.loc[
            out["qc_hard_fail"], hard_cols
        ].apply(lambda r: _join_reasons(r, hard_cols), axis=1)

    if soft_cols:
        out.loc[out["qc_soft_fail"], "qc_reason_soft"] = out.loc[
            out["qc_soft_fail"], soft_cols
        ].apply(lambda r: _join_reasons(r, soft_cols), axis=1)

    # Score simple (hard pesa más)
    out["qc_score"] = 0
    if flag_cols:
        out["qc_score"] = out[flag_cols].sum(axis=1).astype(int)
    out["qc_score"] = out["qc_score"] + (out["qc_hard_fail"].astype(int) * 5)

    # Resumen global
    n = len(out)
    resumen = []
    for c in [*flag_cols, "qc_any_flag", "qc_hard_fail", "qc_soft_fail"]:
        cnt = int(out[c].sum()) if c in out.columns else 0
        resumen.append([c, cnt, (cnt / n * 100) if n else 0.0])

    qc_resumen = pd.DataFrame(resumen, columns=["regla_flag", "conteo", "porcentaje"]).sort_values(
        "porcentaje", ascending=False
    )

    # top offenders
    qc_top_vehiculos = None
    if col_placa is not None and col_placa in out.columns:
        qc_top_vehiculos = (
            out.groupby(col_placa)[["qc_any_flag", "qc_hard_fail", "qc_soft_fail"]]
            .sum()
            .sort_values(["qc_hard_fail", "qc_any_flag"], ascending=False)
            .head(15)
        )

    qc_top_rutas = None
    if col_ruta is not None and col_ruta in out.columns:
        qc_top_rutas = (
            out.groupby(col_ruta)[["qc_any_flag", "qc_hard_fail", "qc_soft_fail"]]
            .sum()
            .sort_values(["qc_hard_fail", "qc_any_flag"], ascending=False)
            .head(15)
        )

    return out, qc_resumen, qc_top_vehiculos, qc_top_rutas


def run_block6(despachos: pd.DataFrame) -> pd.DataFrame:
    """Bloque 6: QC de coherencia operacional, export de parquets y reportes."""
    inicializar_entorno(verbose=False)
    # Asegurar datetime
    despachos[col_hi] = pd.to_datetime(despachos[col_hi], errors="coerce")
    despachos[col_hf] = pd.to_datetime(despachos[col_hf], errors="coerce")

    logger.info(
        "BLOQUE 6 - columnas: pk=%s placa=%s ruta=%s hi=%s hf=%s pasajeros=%s distancia=%s",
        col_pk,
        col_placa,
        col_ruta,
        col_hi,
        col_hf,
        col_pasaj,
        col_dist,
    )

    estados_validos = None

    despachos_qc, qc_resumen, qc_top_vehiculos, qc_top_rutas = (
        validar_coherencia_operacional_avanzada(
            despachos,
            col_pk=col_pk,
            col_placa=col_placa,
            col_ruta=col_ruta,
            col_estado=col_estado,
            col_hi=col_hi,
            col_hf=col_hf,
            col_pasaj=col_pasaj,
            col_dist=col_dist,
            col_fdesp=col_fdesp,
            cfg=CFG,
            estados_validos=estados_validos,
        )
    )

    # dataset apto para GPS (Bloque 7)
    despachos_gps_ready = despachos_qc.loc[~despachos_qc["qc_hard_fail"]].copy()
    despachos_hard_excluded = despachos_qc.loc[despachos_qc["qc_hard_fail"]].copy()

    logger.info("BLOQUE 6 - QC Resumen (top 15):")
    display(qc_resumen.head(15))

    logger.info("BLOQUE 6 - filas totales: %d", len(despachos_qc))
    logger.info(
        "BLOQUE 6 - hard fail: %d (%.2f%%)",
        int(despachos_qc["qc_hard_fail"].sum()),
        despachos_qc["qc_hard_fail"].mean() * 100,
    )
    logger.info(
        "BLOQUE 6 - soft fail: %d (%.2f%%)",
        int(despachos_qc["qc_soft_fail"].sum()),
        despachos_qc["qc_soft_fail"].mean() * 100,
    )
    logger.info(
        "BLOQUE 6 - cualquier flag: %d (%.2f%%)",
        int(despachos_qc["qc_any_flag"].sum()),
        despachos_qc["qc_any_flag"].mean() * 100,
    )

    if qc_top_vehiculos is not None:
        logger.info("BLOQUE 6 - top vehículos con problemas (top 15):")
        display(qc_top_vehiculos)

    if qc_top_rutas is not None:
        logger.info("BLOQUE 6 - top rutas con problemas (top 15):")
        display(qc_top_rutas)

    if "duracion_min" in despachos_qc.columns and despachos_qc["duracion_min"].notna().any():
        desc = despachos_qc["duracion_min"].describe(percentiles=[0.5, 0.9, 0.95, 0.99])
        logger.info("BLOQUE 6 - duración (min):\n%s", desc)

    # Export (Parquet + CSV)
    despachos_qc = _fix_object_dates_for_parquet(despachos_qc)
    despachos_gps_ready = _fix_object_dates_for_parquet(despachos_gps_ready)
    despachos_hard_excluded = _fix_object_dates_for_parquet(despachos_hard_excluded)

    despachos_qc.to_parquet(QC_PATH, index=False)
    despachos_gps_ready.to_parquet(os.path.join(QC_DIR, "despachos_gps_ready.parquet"), index=False)
    despachos_hard_excluded.to_parquet(
        os.path.join(QC_DIR, "despachos_hard_excluded.parquet"), index=False
    )

    # Los CSV de resumen son reportes, no datos intermedios: van a reports/tables/qc
    qc_resumen.to_csv(os.path.join(QC_REPORTS_DIR, "qc_resumen.csv"), index=False)
    if qc_top_vehiculos is not None:
        qc_top_vehiculos.to_csv(os.path.join(QC_REPORTS_DIR, "qc_top_vehiculos.csv"), index=False)
    if qc_top_rutas is not None:
        qc_top_rutas.to_csv(os.path.join(QC_REPORTS_DIR, "qc_top_rutas.csv"), index=False)

    logger.info("BLOQUE 6 - QC parquets exportados en: %s", QC_DIR)
    logger.info("BLOQUE 6 - QC reportes exportados en: %s", QC_REPORTS_DIR)
    logger.info("BLOQUE 6 - QC_PATH (principal): %s", QC_PATH)

    neg = despachos_qc[despachos_qc["duracion_min"].notna() & (despachos_qc["duracion_min"] < 0)]
    logger.info("BLOQUE 6 - duraciones negativas reales: %d", len(neg))
    display(
        neg[
            [
                col_pk,
                col_placa,
                col_ruta,
                col_hi,
                col_hf,
                "duracion_min",
                "flag_horas_invertidas",
                "flag_duracion_negativa",
            ]
        ].head(20)
    )
    return despachos_qc
