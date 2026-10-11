"""Subida de la ejecucion a S3.

Usa solo la cadena de credenciales por defecto de boto3 (en EC2, el rol de la
instancia): nunca claves en el codigo, la configuracion o .env. El destino se
lee de PILOTO_S3_BUCKET y PILOTO_S3_PREFIJO.

Claves:
- ``<prefijo>/ejecuciones/<id>/<archivo>``: manifiesto, log y salidas de la ejecucion;
- ``<prefijo>/planillas/<planilla>.xlsx``;
- ``<prefijo>/extracciones/<id>.parquet``: instantanea de la extraccion;
- ``<prefijo>/indicadores/<D>.parquet``: desempeno del modelo en la jornada D.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VARIABLE_BUCKET = "PILOTO_S3_BUCKET"
VARIABLE_PREFIJO = "PILOTO_S3_PREFIJO"


class ErrorSalidaS3(RuntimeError):  # noqa: N818
    """Falta la configuracion de S3 o la subida fallo."""


@dataclass(frozen=True)
class DestinoS3:
    bucket: str
    prefijo: str

    def clave(self, *partes: str) -> str:
        return "/".join(p.strip("/") for p in (self.prefijo, *partes) if p and p.strip("/"))

    def uri(self, *partes: str) -> str:
        return f"s3://{self.bucket}/{self.clave(*partes)}"


def destino_desde_entorno() -> DestinoS3:
    bucket = os.environ.get(VARIABLE_BUCKET, "").strip()
    if not bucket:
        raise ErrorSalidaS3(f"Falta la variable de entorno {VARIABLE_BUCKET}.")
    return DestinoS3(bucket=bucket, prefijo=os.environ.get(VARIABLE_PREFIJO, "").strip())


def cliente_s3():
    """Cliente con la cadena de credenciales por defecto (sin claves explicitas)."""
    import boto3

    return boto3.client("s3")


def archivos_a_subir(
    carpeta_ejecucion: Path, planilla: Path | None, instantanea: Path | None, id_ejecucion: str
) -> list[tuple[Path, tuple[str, ...]]]:
    """(archivo local, partes de la clave) de todo lo que se sube."""
    archivos = [
        (p, ("ejecuciones", id_ejecucion, p.relative_to(carpeta_ejecucion).as_posix()))
        for p in sorted(Path(carpeta_ejecucion).rglob("*"))
        if p.is_file()
    ]
    if planilla is not None:
        archivos.append((Path(planilla), ("planillas", Path(planilla).name)))
    if instantanea is not None:
        archivos.append((Path(instantanea), ("extracciones", Path(instantanea).name)))
    return archivos


def subir(
    archivos: list[tuple[Path, tuple[str, ...]]], destino: DestinoS3, cliente=None
) -> list[str]:
    """Sube cada archivo con PutObject y devuelve sus URI."""
    cliente = cliente or cliente_s3()
    uris = []
    for ruta, partes in archivos:
        try:
            cliente.put_object(
                Bucket=destino.bucket, Key=destino.clave(*partes), Body=Path(ruta).read_bytes()
            )
        except Exception as exc:
            raise ErrorSalidaS3(f"No se pudo subir {Path(ruta).name}: {exc}") from exc
        uris.append(destino.uri(*partes))
    return uris
