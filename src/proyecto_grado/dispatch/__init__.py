"""Recomendacion de despachos por franja a partir de la demanda predicha.

Modulos:

- ``config``: contrato de configs/dispatch/recomendacion.yaml.
- ``parametros``: calibracion de cuantiles de pasajeros por despacho y capacidad.
- ``predictor_mixto``: XGBoost en regimen ordinario y referencia de 52 semanas en raro.
- ``reglas``: despachos por franja y ajuste de factibilidad.
- ``evaluacion``: comparacion con la operacion real.
"""

from proyecto_grado.dispatch.config import (
    ConfiguracionRecomendacion,
    ErrorConfiguracionRecomendacion,
    cargar_configuracion_recomendacion,
)

__all__ = [
    "ConfiguracionRecomendacion",
    "ErrorConfiguracionRecomendacion",
    "cargar_configuracion_recomendacion",
]
