"""Presentacion de la planilla de despacho por ruta y franja.

Solo da formato: la meta que se evalua es ``despachos_recomendados`` de
``reglas.generar_recomendacion``, que vale 0 fuera de la disponibilidad habitual.
En la planilla esas franjas muestran "Sin meta" y, como sugerencia si hay un
conductor disponible, lo que daria la regla normal (``despachos_regla_normal``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter

from proyecto_grado.dispatch.parametros import REGIMEN_RARO
from proyecto_grado.dispatch.reglas import intervalo_sugerido, redondeo_aritmetico

MARCA_FUERA = "Fuera de disponibilidad habitual"
SIN_META = "Sin meta"
NOTA_SIN_META = (
    "Sin meta: a esta hora normalmente no hay conductores. Si hay uno disponible, se "
    "sugiere despachar según la columna Si hay conductor disponible."
)
NOTA_SIN_CONDUCTOR = (
    "Si no hay conductores disponibles para cumplir la meta de una franja, registrar SIN CONDUCTOR."
)


def divisor_y_criterio(
    rec: pd.DataFrame, usar_tope: bool, minimo: int
) -> tuple[np.ndarray, np.ndarray]:
    """Divisor que determina los despachos de la regla en cada franja y su criterio.

    En las franjas fuera de la disponibilidad habitual (``en_disponibilidad`` en
    False) se informa el divisor que habria usado la regla normal, con el criterio
    precedido de la marca de fuera de disponibilidad.
    """
    d = np.clip(rec["demanda_predicha"].to_numpy(float), 0, None)
    raro = (rec["regimen"] == REGIMEN_RARO).to_numpy()
    por_mediana = redondeo_aritmetico(d / rec["divisor"].to_numpy(float))
    por_tope = np.ceil(d / rec["q3_ordinario"].to_numpy(float)) if usar_tope else np.zeros_like(d)
    usa_tope = ~raro & (por_tope > por_mediana)
    criterio = np.where(
        raro,
        "mediana del regimen raro",
        np.where(usa_tope, "Q3 (tope de carga)", "mediana del bloque"),
    )
    divisor = np.where(usa_tope, rec["q3_ordinario"], rec["divisor"])
    base = np.where(usa_tope, por_tope, por_mediana)
    criterio = np.where(base < minimo, "servicio minimo", criterio)
    if "en_disponibilidad" in rec:
        fuera = ~rec["en_disponibilidad"].astype(bool).to_numpy()
        criterio = np.where(fuera, np.char.add(f"{MARCA_FUERA}, ", criterio.astype(str)), criterio)
    return divisor, criterio


def texto_si_hay_conductor(despachos: int) -> str:
    """Despachos sugeridos y su intervalo, por ejemplo "1 (30 min)"."""
    minutos = intervalo_sugerido([despachos])[0]
    return f"{int(despachos)} ({int(minutos)} min)" if despachos > 0 else "0"


def tabla_planilla(rec: pd.DataFrame, usar_tope: bool, minimo: int) -> pd.DataFrame:
    """Filas de la planilla de una ruta, ordenadas por franja.

    ``rec`` es la salida de ``generar_recomendacion`` para esa ruta. Si trae
    ``en_disponibilidad``, la planilla agrega la columna "Si hay conductor
    disponible" y muestra "Sin meta" fuera de la disponibilidad habitual.
    """
    r = rec.sort_values("hora")
    divisor, criterio = divisor_y_criterio(r, usar_tope, minimo)
    meta = r["despachos_recomendados"].astype(int)
    columnas: dict[str, object] = {
        "Franja": r["hora"].to_numpy(),
        "Pasajeros predichos": r["demanda_predicha"].round(1).to_numpy(),
        "Divisor usado": np.round(divisor.astype(float), 2),
        "Criterio del divisor": criterio,
    }
    intervalo = pd.array(intervalo_sugerido(meta), dtype="Int64")
    if "en_disponibilidad" in r:
        fuera = ~r["en_disponibilidad"].astype(bool).to_numpy()
        # Fuera de la disponibilidad, "Sin meta"; dentro, la meta como numero.
        columnas["Meta de despachos"] = [
            SIN_META if f else int(m) for f, m in zip(fuera, meta, strict=True)
        ]
        columnas["Intervalo sugerido (min)"] = intervalo
        columnas["Si hay conductor disponible"] = [
            texto_si_hay_conductor(n) if f else ""
            for f, n in zip(fuera, r["despachos_regla_normal"], strict=True)
        ]
    else:
        columnas["Meta de despachos"] = meta.to_numpy()
        columnas["Intervalo sugerido (min)"] = intervalo
    columnas["Régimen"] = r["regimen"].to_numpy()
    return pd.DataFrame(columnas)


def escribir_hoja(xw: pd.ExcelWriter, hoja: str, tabla: pd.DataFrame, notas: list[str]) -> None:
    """Escribe la tabla con el encabezado fijo, el ancho ajustado al contenido y
    las notas al pie (una por linea, tras una fila en blanco)."""
    tabla.to_excel(xw, sheet_name=hoja, index=False)
    ws = xw.sheets[hoja]
    ws.freeze_panes = "A2"
    for i, col in enumerate(tabla.columns, start=1):
        valores = [str(col)] + ["" if pd.isna(v) else str(v) for v in tabla[col]]
        ws.column_dimensions[get_column_letter(i)].width = max(len(v) for v in valores) + 2
    for j, nota in enumerate(notas):
        ws.cell(row=len(tabla) + 3 + j, column=1, value=nota)
