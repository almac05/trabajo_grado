"""Metricas operativas y de desempeno en Amazon CloudWatch.

Usa boto3 con la cadena de credenciales por defecto (en EC2, el rol de la
instancia, con cloudwatch:PutMetricData limitado al namespace
Montebello/Despacho); nunca claves en el codigo ni en .env.

- Solo publica si PILOTO_METRICAS=1; si no, no crea cliente y lo registra.
- Region: PILOTO_AWS_REGION (por defecto us-east-2); namespace:
  PILOTO_CW_NAMESPACE (por defecto Montebello/Despacho).
- Nunca lanza excepciones: un fallo queda en una linea del log (enmascarada) y
  en el resultado ``{"metricas_publicadas": False, "motivo": ...}``.
- La lista de metricas es cerrada (``CATALOGO``): cada combinacion nombre +
  dimensiones es una metrica facturable, asi que todo dato fuera del catalogo
  se descarta.
"""

from __future__ import annotations

import logging
import math
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from proyecto_grado.piloto.registro import ocultar

logger = logging.getLogger("proyecto_grado.piloto.metricas")

VARIABLE_ACTIVAR = "PILOTO_METRICAS"
VARIABLE_REGION = "PILOTO_AWS_REGION"
VARIABLE_NAMESPACE = "PILOTO_CW_NAMESPACE"
REGION_PREDETERMINADA = "us-east-2"
NAMESPACE_PREDETERMINADO = "Montebello/Despacho"
RUTAS = ("1", "3")
CODIGOS_ESTADO = {"OK": 0, "ADVERTENCIA": 1, "CONTINGENCIA": 2, "ERROR": 3}
CODIGO_ESTADO_DESCONOCIDO = 3


@dataclass(frozen=True)
class DefinicionMetrica:
    nombre: str
    unidad: str
    dimensiones: tuple[tuple[str, str], ...] = ()

    @property
    def clave(self) -> str:
        dims = ",".join(f"{k}={v}" for k, v in self.dimensiones)
        return f"{self.nombre}[{dims}]" if dims else self.nombre


def _por_ruta(nombre: str, unidad: str) -> tuple[DefinicionMetrica, ...]:
    return tuple(DefinicionMetrica(nombre, unidad, (("Ruta", r),)) for r in RUTAS)


# 9 operativas + 8 de desempeno. Agregar una combinacion aqui es una decision de
# costo: la prueba de test_metricas falla si el catalogo pasa de 17.
CATALOGO: tuple[DefinicionMetrica, ...] = (
    DefinicionMetrica("EstadoCorrida", "None"),
    DefinicionMetrica("DuracionTotal", "Seconds"),
    DefinicionMetrica("DuracionExtraccion", "Seconds"),
    DefinicionMetrica("RegistrosExtraidos", "Count"),
    DefinicionMetrica("FilasRecomendaciones", "Count"),
    *_por_ruta("FactorCorreccion", "None"),
    DefinicionMetrica("MemoriaPico", "Megabytes"),
    DefinicionMetrica("JornadaCubierta", "Count"),
    *_por_ruta("ErrorMAE", "None"),
    *_por_ruta("ErrorRMSE", "None"),
    *_por_ruta("ErrorMAPE", "Percent"),
    *_por_ruta("SesgoPct", "Percent"),
)
_POR_CLAVE = {d.clave: d for d in CATALOGO}

# Campo del bloque "desempeno" del manifiesto -> metrica de CloudWatch.
METRICAS_DESEMPENO = {
    "mae": "ErrorMAE",
    "rmse": "ErrorRMSE",
    "mape_u10": "ErrorMAPE",
    "sesgo_pct": "SesgoPct",
}


# --------------------------------------------------------------- datos


def dato(nombre: str, valor: Any, ruta: str | int | None = None) -> dict | None:
    """Un dato de PutMetricData (sin Timestamp), o None si no esta en el catalogo
    o el valor no es un numero finito."""
    dimensiones = (("Ruta", str(ruta)),) if ruta is not None else ()
    definicion = _POR_CLAVE.get(DefinicionMetrica(nombre, "", dimensiones).clave)
    if definicion is None:
        logger.warning("Metrica fuera del catalogo, no se publica: %s %s", nombre, dimensiones)
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(valor):
        return None
    salida = {"MetricName": nombre, "Value": valor, "Unit": definicion.unidad}
    if dimensiones:
        salida["Dimensions"] = [{"Name": k, "Value": v} for k, v in dimensiones]
    return salida


def memoria_pico_mb() -> float | None:
    """ru_maxrss de RUSAGE_SELF + RUSAGE_CHILDREN en MB (Linux, KB); None sin ``resource``."""
    try:
        import resource
    except ImportError:
        return None
    kb = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        + resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    )
    return kb / 1024


def datos_de_corrida(m: dict, memoria_mb: float | None = None) -> list[dict]:
    """Datos de una corrida a partir de su manifiesto final.

    EstadoCorrida y DuracionTotal van siempre; las demas, solo si la corrida
    llego al paso que las produce.
    """
    pasos = m.get("pasos") or {}
    bd = m.get("bd") or {}
    filas = bd.get("filas") if bd.get("cerrada") else (m.get("recomendacion") or {}).get("filas")
    candidatos = [
        dato("EstadoCorrida", CODIGOS_ESTADO.get(m.get("estado"), CODIGO_ESTADO_DESCONOCIDO)),
        dato("DuracionTotal", m.get("segundos", 0)),
        dato("DuracionExtraccion", (pasos.get("extraccion") or {}).get("segundos")),
        dato(
            "RegistrosExtraidos",
            ((m.get("extraccion") or {}).get("deduplicado") or {}).get("despachos"),
        ),
        dato("FilasRecomendaciones", filas),
        dato("MemoriaPico", memoria_mb),
    ]
    for ruta, f in (m.get("factor") or {}).items():
        candidatos.append(dato("FactorCorreccion", (f or {}).get("valor"), ruta))
    for ruta, r in ((m.get("desempeno") or {}).get("por_ruta") or {}).items():
        for campo, nombre in METRICAS_DESEMPENO.items():
            candidatos.append(dato(nombre, (r or {}).get(campo), ruta))
    return [c for c in candidatos if c is not None]


def dato_jornada_cubierta(cubierta: bool) -> dict:
    return dato("JornadaCubierta", 1 if cubierta else 0)


# --------------------------------------------------------------- publicacion


def metricas_activadas() -> bool:
    return os.environ.get(VARIABLE_ACTIVAR, "").strip() == "1"


def namespace() -> str:
    return os.environ.get(VARIABLE_NAMESPACE, "").strip() or NAMESPACE_PREDETERMINADO


def cliente_cloudwatch():
    """Cliente con la cadena de credenciales por defecto y tiempos cortos."""
    import boto3
    from botocore.config import Config

    region = os.environ.get(VARIABLE_REGION, "").strip() or REGION_PREDETERMINADA
    config = Config(
        connect_timeout=5,
        read_timeout=5,
        retries={"total_max_attempts": 2, "mode": "standard"},
    )
    return boto3.client("cloudwatch", region_name=region, config=config)


def no_aplica(motivo: str) -> dict:
    return {"metricas_publicadas": False, "motivo": f"no_aplica: {motivo}"}


def publicar_metricas(
    datos: list[dict],
    momento: datetime,
    fabrica_cliente: Callable[[], Any] | None = None,
) -> dict:
    """Publica ``datos`` con el instante ``momento`` (UTC). Nunca lanza excepciones."""
    try:
        if not metricas_activadas():
            logger.info("Metricas de CloudWatch desactivadas (%s distinto de 1).", VARIABLE_ACTIVAR)
            return {
                "metricas_publicadas": False,
                "motivo": f"desactivadas: {VARIABLE_ACTIVAR} distinto de 1",
            }
        datos = [d for d in datos if d is not None]
        if not datos:
            return {"metricas_publicadas": False, "motivo": "sin datos"}
        if momento.tzinfo is None or momento.utcoffset() is None:
            raise ValueError("El instante de las metricas debe tener zona horaria.")
        instante = momento.astimezone(UTC)
        ns = namespace()
        cliente = (fabrica_cliente or cliente_cloudwatch)()
        cliente.put_metric_data(
            Namespace=ns, MetricData=[{**d, "Timestamp": instante} for d in datos]
        )
        enviadas = [_clave_de(d) for d in datos]
        logger.info("Metricas publicadas en CloudWatch (%s): %s", ns, ", ".join(enviadas))
        return {
            "metricas_publicadas": True,
            "namespace": ns,
            "timestamp": instante.isoformat(timespec="seconds"),
            "metricas": enviadas,
        }
    except Exception as exc:
        motivo = ocultar(f"{type(exc).__name__}: {exc}")
        logger.error("No se pudieron publicar las metricas en CloudWatch: %s", motivo)
        return {"metricas_publicadas": False, "motivo": motivo}


def _clave_de(d: dict) -> str:
    dims = tuple((x["Name"], x["Value"]) for x in d.get("Dimensions", []))
    return DefinicionMetrica(d["MetricName"], d["Unit"], dims).clave
