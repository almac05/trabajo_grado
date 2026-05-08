"""Validaciones de integridad y completitud de la serie temporal agregada."""

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

_OBJ_COLS = ["pasajeros_total", "despachos_count", "pasajeros_promedio", "ocupacion_p95"]


@dataclass
class ValidationReport:
    """Resultado de la validacion de una serie temporal.

    Attributes
    ----------
    ruta : int | None
        Identificador de ruta validada.
    n_filas : int
        Total de filas en la serie.
    fecha_inicio : str
        Fecha del primer timestamp (ISO).
    fecha_fin : str
        Fecha del ultimo timestamp (ISO).
    gaps_detectados : int
        Cantidad de franjas sin despachos reales.
    tiene_negativos : bool
        True si alguna variable objetivo tiene valores negativos.
    tiene_nulos_objetivo : bool
        True si alguna variable objetivo tiene NaN (estrategia mark).
    cobertura_dias : int
        Dias calendario que abarca la serie.
    cobertura_minima_dias : int
        Minimo requerido de cobertura.
    cobertura_ok : bool
        True si cobertura_dias >= cobertura_minima_dias.
    errores : list[str]
        Condiciones que invalidan la serie.
    advertencias : list[str]
        Condiciones que no invalidan pero merecen revision.
    """

    ruta: int | None
    n_filas: int
    fecha_inicio: str
    fecha_fin: str
    gaps_detectados: int
    tiene_negativos: bool
    tiene_nulos_objetivo: bool
    cobertura_dias: int
    cobertura_minima_dias: int
    cobertura_ok: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def valida(self) -> bool:
        """True si la serie no tiene errores criticos."""
        return len(self.errores) == 0


class TimeSeriesValidator:
    """Valida la integridad y completitud de una serie temporal agregada.

    Comprueba:
    - Continuidad temporal (sin saltos mayores a granularidad_min).
    - Ausencia de valores negativos en variables objetivo.
    - Cobertura minima de fechas requerida.
    - Reporte de gaps detectados.

    Parameters
    ----------
    granularidad_min : int
        Granularidad esperada entre timestamps consecutivos (minutos).
    cobertura_minima_dias : int
        Minimo de dias calendario que debe abarcar la serie.
    """

    def __init__(self, granularidad_min: int = 60, cobertura_minima_dias: int = 30) -> None:
        self.granularidad_min = granularidad_min
        self.cobertura_minima_dias = cobertura_minima_dias

    def validate(self, serie: pd.DataFrame, ruta: int | None = None) -> ValidationReport:
        """Valida una serie producida por TimeSeriesBuilder y retorna un reporte.

        Parameters
        ----------
        serie : pd.DataFrame
            Serie temporal con columna 'timestamp' y variables objetivo.
        ruta : int | None
            Identificador de ruta para incluir en el reporte.

        Returns
        -------
        ValidationReport
            Reporte con errores, advertencias y metricas de la serie.
        """
        errores: list[str] = []
        advertencias: list[str] = []

        if serie.empty:
            return ValidationReport(
                ruta=ruta,
                n_filas=0,
                fecha_inicio="",
                fecha_fin="",
                gaps_detectados=0,
                tiene_negativos=False,
                tiene_nulos_objetivo=False,
                cobertura_dias=0,
                cobertura_minima_dias=self.cobertura_minima_dias,
                cobertura_ok=False,
                errores=["Serie vacia"],
            )

        ts = pd.to_datetime(serie["timestamp"]).sort_values()
        n = len(serie)
        fecha_inicio = str(ts.min().date())
        fecha_fin = str(ts.max().date())
        cobertura_dias = (ts.max() - ts.min()).days + 1

        # Continuidad temporal
        esperado = pd.Timedelta(minutes=self.granularidad_min)
        diffs = ts.diff().dropna()
        saltos = diffs[diffs > esperado]
        if not saltos.empty:
            advertencias.append(
                f"{len(saltos)} saltos temporales mayores a {self.granularidad_min} min"
            )

        # Gaps detectados (columna is_gap si existe, sino saltos)
        gaps_detectados = int(serie["is_gap"].sum()) if "is_gap" in serie.columns else len(saltos)

        # Valores negativos en variables objetivo
        tiene_negativos = False
        for col in _OBJ_COLS:
            if col not in serie.columns:
                continue
            neg = int((serie[col].fillna(0) < 0).sum())
            if neg > 0:
                errores.append(f"'{col}' tiene {neg} valores negativos")
                tiene_negativos = True

        # Nulos en variables objetivo (solo relevante con imputacion_gaps=mark)
        tiene_nulos_objetivo = False
        for col in _OBJ_COLS:
            if col not in serie.columns:
                continue
            nulos = int(serie[col].isna().sum())
            if nulos > 0:
                advertencias.append(f"'{col}' tiene {nulos} NaN (gaps sin imputar)")
                tiene_nulos_objetivo = True

        # Cobertura minima
        cobertura_ok = cobertura_dias >= self.cobertura_minima_dias
        if not cobertura_ok:
            errores.append(
                f"Cobertura {cobertura_dias} dias < minimo requerido {self.cobertura_minima_dias}"
            )

        report = ValidationReport(
            ruta=ruta,
            n_filas=n,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            gaps_detectados=gaps_detectados,
            tiene_negativos=tiene_negativos,
            tiene_nulos_objetivo=tiene_nulos_objetivo,
            cobertura_dias=cobertura_dias,
            cobertura_minima_dias=self.cobertura_minima_dias,
            cobertura_ok=cobertura_ok,
            errores=errores,
            advertencias=advertencias,
        )

        if report.valida:
            logger.info(
                "Validacion ruta=%s OK: %d filas, %d dias, %d gaps",
                ruta,
                n,
                cobertura_dias,
                gaps_detectados,
            )
        else:
            logger.error("Validacion ruta=%s ERRORES: %s", ruta, errores)

        for adv in advertencias:
            logger.warning("Validacion ruta=%s: %s", ruta, adv)

        return report
