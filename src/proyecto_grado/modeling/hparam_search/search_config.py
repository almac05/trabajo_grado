"""Carga la configuracion de la busqueda de hiperparametros.

Reutiliza el contrato de evaluacion comparativa (dataset, rutas, objetivo,
min_franjas, paso_muestreo, umbral_mape, tipos_baja_frecuencia) y le suma el
periodo de validacion y el presupuesto de configuraciones, propios de la
busqueda.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.modeling.evaluation_config import (
    ConfiguracionEvaluacionComparativa,
    cargar_configuracion_evaluacion,
)

RUTA_CONFIG_PREDETERMINADA = PROJECT_ROOT / "configs" / "modeling" / "busqueda_hiperparametros.yaml"


class ErrorConfiguracionBusqueda(ValueError):  # noqa: N818
    """Indica que la configuracion de busqueda no satisface el contrato."""


@dataclass(frozen=True)
class ConfiguracionBusquedaHiperparametros:
    """Contrato de la busqueda: periodo de validacion y presupuesto."""

    evaluacion: ConfiguracionEvaluacionComparativa
    inicio_validacion: date
    fin_validacion: date
    n_iter: int
    semilla: int
    directorio_salida: Path

    def __post_init__(self) -> None:
        if self.inicio_validacion > self.fin_validacion:
            raise ErrorConfiguracionBusqueda(
                "El inicio del periodo de validacion es posterior al fin."
            )
        if self.fin_validacion >= self.evaluacion.inicio:
            raise ErrorConfiguracionBusqueda(
                "El periodo de validacion debe terminar antes del inicio del "
                f"periodo de evaluacion ({self.evaluacion.inicio}); "
                f"fin_validacion={self.fin_validacion}."
            )
        if self.n_iter <= 0:
            raise ErrorConfiguracionBusqueda("n_iter debe ser un entero positivo.")


def cargar_configuracion_busqueda(
    ruta: str | Path | None = None,
) -> ConfiguracionBusquedaHiperparametros:
    """Carga configs/modeling/busqueda_hiperparametros.yaml y valida el contrato."""
    ruta_config = Path(ruta) if ruta is not None else RUTA_CONFIG_PREDETERMINADA
    if not ruta_config.is_absolute():
        ruta_config = PROJECT_ROOT / ruta_config
    if not ruta_config.is_file():
        raise FileNotFoundError(f"No existe la configuracion de busqueda: {ruta_config}.")
    with ruta_config.open(encoding="utf-8") as archivo:
        raw = yaml.safe_load(archivo)
    if not isinstance(raw, dict):
        raise ErrorConfiguracionBusqueda("La raiz de la configuracion debe ser un mapa.")

    validacion = raw.get("validacion")
    if not isinstance(validacion, dict) or not isinstance(validacion.get("periodo"), dict):
        raise ErrorConfiguracionBusqueda("Falta el bloque validacion.periodo.")
    periodo = validacion["periodo"]
    if periodo.get("extremos_inclusivos") is not True:
        raise ErrorConfiguracionBusqueda(
            "El periodo de validacion debe declarar ambos extremos inclusivos."
        )
    inicio_validacion = date.fromisoformat(str(periodo.get("inicio")))
    fin_validacion = date.fromisoformat(str(periodo.get("fin")))

    busqueda = raw.get("busqueda")
    if not isinstance(busqueda, dict):
        raise ErrorConfiguracionBusqueda("Falta el bloque busqueda.")
    n_iter = int(busqueda.get("n_iter", 10))
    semilla = int(busqueda.get("semilla", 42))

    salidas = raw.get("salidas")
    if not isinstance(salidas, dict) or not salidas.get("directorio"):
        raise ErrorConfiguracionBusqueda("Falta salidas.directorio.")
    directorio_salida = PROJECT_ROOT / str(salidas["directorio"])

    return ConfiguracionBusquedaHiperparametros(
        evaluacion=cargar_configuracion_evaluacion(),
        inicio_validacion=inicio_validacion,
        fin_validacion=fin_validacion,
        n_iter=n_iter,
        semilla=semilla,
        directorio_salida=directorio_salida,
    )
