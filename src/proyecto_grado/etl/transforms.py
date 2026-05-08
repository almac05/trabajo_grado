"""Transformaciones deterministicas de despachos."""

import pandas as pd

from .config import RUTAS_OPERATIVAS


def combinar_fecha_hora(df, col_fecha, col_hora, out_col):
    h = df[col_hora].astype(str).str.extract(r"(\d{2}:\d{2}:\d{2})")[0]
    df[out_col] = pd.to_datetime(df[col_fecha].astype(str) + " " + h.astype(str), errors="coerce")
    return df


def run_block4(despachos: pd.DataFrame) -> pd.DataFrame:
    """Bloque 4: Normalizacion temporal, PASAJEROS_REALES y filtrado rutas 1 y 3."""
    despachos = despachos.copy()

    despachos = combinar_fecha_hora(
        despachos, "FECHA_INICIAL", "HORA_INICIAL_PLAN", "HORA_INICIAL_PLAN"
    )
    despachos = combinar_fecha_hora(
        despachos, "FECHA_INICIAL", "HORA_INICIAL_REAL", "HORA_INICIAL_REAL"
    )
    despachos = combinar_fecha_hora(despachos, "FECHA_FINAL", "HORA_FINAL_PLAN", "HORA_FINAL_PLAN")
    despachos = combinar_fecha_hora(despachos, "FECHA_FINAL", "HORA_FINAL_REAL", "HORA_FINAL_REAL")

    for c in ["HORA_INICIAL_AUX", "HORA_FINAL_AUX"]:
        if c in despachos.columns:
            despachos.drop(columns=[c], inplace=True)

    # PASAJEROS_REALES
    despachos["ALARMAS"] = (
        pd.to_numeric(despachos["ALARMAS"], errors="coerce").fillna(0).astype(int)
    )
    despachos["PASAJEROS"] = pd.to_numeric(despachos["PASAJEROS"], errors="coerce")
    despachos["PASAJEROS_REALES"] = (despachos["PASAJEROS"] - despachos["ALARMAS"]).clip(lower=0)

    despachos = despachos[despachos["FK_RUTA"].isin(RUTAS_OPERATIVAS)]

    # % faltantes correcto
    porcentaje_faltantes = (despachos.isnull().sum() / len(despachos)) * 100
    print(porcentaje_faltantes.sort_values(ascending=False).head(10))
    return despachos
