"""Avisos por SNS: fallos, vigilancia y exito de la corrida nocturna.

Usa boto3 con la cadena de credenciales por defecto (en EC2, el rol de la
instancia con sns:Publish); el tema se lee de PILOTO_SNS_TOPIC. Todo texto pasa
por ``registro.ocultar`` antes de salir. La region se toma del ARN del tema, asi
que no hace falta configurarla.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from proyecto_grado.piloto.registro import ocultar

VARIABLE_TEMA = "PILOTO_SNS_TOPIC"
VARIABLE_AVISAR_OK = "PILOTO_AVISAR_OK"
LARGO_ASUNTO = 100  # limite de SNS para el asunto de correo
LARGO_MENSAJE = 200_000  # por debajo del limite de 256 KB de SNS


class ErrorAviso(RuntimeError):  # noqa: N818
    """Falta el tema de SNS o la publicacion fallo."""


def tema() -> str:
    valor = os.environ.get(VARIABLE_TEMA, "").strip()
    if not valor:
        raise ErrorAviso(f"Falta la variable de entorno {VARIABLE_TEMA}.")
    return valor


def avisar_ok_activado() -> bool:
    return os.environ.get(VARIABLE_AVISAR_OK, "").strip() == "1"


def region_de(arn: str) -> str | None:
    """Region de un ARN de SNS (arn:aws:sns:<region>:<cuenta>:<tema>)."""
    partes = arn.split(":")
    return partes[3] if len(partes) >= 6 and partes[2] == "sns" and partes[3] else None


def cliente_sns(arn: str):
    import boto3

    return boto3.client("sns", region_name=region_de(arn))


def publicar(asunto: str, mensaje: str, cliente=None, arn: str | None = None) -> str:
    """Publica en el tema; devuelve el MessageId. Asunto y mensaje van enmascarados."""
    arn = arn or tema()
    cliente = cliente or cliente_sns(arn)
    asunto = " ".join(ocultar(asunto).split())[:LARGO_ASUNTO]
    mensaje = ocultar(mensaje)[:LARGO_MENSAJE]
    try:
        r = cliente.publish(TopicArn=arn, Subject=asunto, Message=mensaje)
    except Exception as exc:
        raise ErrorAviso(f"No se pudo publicar en SNS: {ocultar(str(exc))}") from exc
    return r.get("MessageId", "")


def texto_estado_ultima(salidas: Path) -> str:
    ruta = Path(salidas) / "ESTADO_ULTIMA_EJECUCION.txt"
    if not ruta.exists():
        return "(no existe ESTADO_ULTIMA_EJECUCION.txt)"
    return ruta.read_text(encoding="utf-8").strip()


def mensaje_ok(m: dict) -> tuple[str, str]:
    """Asunto y texto corto del aviso de exito a partir del manifiesto."""
    obj = m.get("objetivo") or {}
    jornada = obj.get("d_mas_1", "?")
    filas = (m.get("bd") or {}).get("filas")
    factores = {r: round(v.get("valor", 0), 4) for r, v in (m.get("factor") or {}).items()}
    lineas = [
        f"Jornada: {jornada} (grupo {m.get('grupo', '-')})",
        f"Estado: {m.get('estado')}",
        f"Duracion: {m.get('segundos', '?')} s",
        f"Filas escritas en la base: {filas if filas is not None else 'no se escribio'}",
        f"Factores: {json.dumps(factores)}",
        f"Advertencias: {len(m.get('advertencias') or [])}",
        f"Ejecucion: {m.get('id_ejecucion')} ({m.get('modo')}, {m.get('entorno', '-')})",
    ]
    for a in (m.get("advertencias") or [])[:5]:
        lineas.append(f"- {a}")
    return f"Piloto despacho: {m.get('estado')} jornada {jornada}", "\n".join(lineas)
