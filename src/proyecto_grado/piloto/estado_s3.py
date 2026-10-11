"""Estado de la piloto en S3 e insumos congelados.

Estado: lo que una corrida necesita de la anterior. Es la version vigente del
almacen (``almacen/ACTUAL.json`` y sus dos parquet) y del historial de
predicciones (``historial/ACTUAL.json`` y su parquet). La serie se reconstruye en
cada corrida y no forma parte del estado.

En S3 (``s3://<bucket>/<prefijo>/estado/``):
    estado/<id>/almacen/...      estado/<id>/historial/...
    estado/<id>/estado.json      id, commit, entorno y SHA-256 de cada archivo
    estado/ACTUAL.json           copia del estado.json vigente
Nunca se borra nada (el rol no tiene DeleteObject); el unico objeto que se
reescribe es estado/ACTUAL.json, y el bucket lo versiona.

Localmente, ``<salidas>/estado/ACTUAL.json`` guarda el id del ultimo estado
publicado o descargado. Los ids son AAAAMMDD_HHMMSS y se comparan como texto.
Los archivos de datos llevan el id en el nombre, asi que nunca se sobrescriben;
solo se reemplazan los punteros ACTUAL.json, despues de verificar todo.

Insumos: ``s3://<bucket>/insumos/<ruta relativa a la raiz del proyecto>`` para
cada entrada congelada de piloto.yaml, verificados contra su SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.config import ConfigPiloto, sha256_archivo
from proyecto_grado.piloto.salida_s3 import DestinoS3

logger = logging.getLogger(__name__)

PREFIJO_ESTADO = "estado"
PREFIJO_INSUMOS = "insumos"
PATRON_ID = re.compile(r"^\d{8}_\d{6}$")
COMPONENTES = ("almacen", "historial")


class ErrorEstadoS3(RuntimeError):  # noqa: N818
    """El estado o un insumo no se pudo publicar, descargar o verificar."""


def _sha_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _sha_crudo(ruta: Path) -> str:
    return _sha_bytes(Path(ruta).read_bytes())


def _escribir_atomico(ruta: Path, datos: bytes) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_bytes(datos)
    os.replace(temporal, ruta)


def _leer_objeto(cliente, bucket: str, clave: str) -> bytes | None:
    """Contenido de un objeto; None si no existe."""
    try:
        respuesta = cliente.get_object(Bucket=bucket, Key=clave)
    except Exception as exc:
        codigo = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if codigo in ("NoSuchKey", "404"):
            return None
        raise ErrorEstadoS3(f"No se pudo leer s3://{bucket}/{clave}: {exc}") from exc
    return respuesta["Body"].read()


# --------------------------------------------------------------- estado local


def archivos_estado(salidas: Path) -> dict[str, Path]:
    """Archivos del estado vigente: punteros y los archivos a los que apuntan."""
    salidas = Path(salidas)
    archivos: dict[str, Path] = {}
    alm = salidas / "almacen" / "ACTUAL.json"
    if alm.exists():
        meta = json.loads(alm.read_text(encoding="utf-8"))
        archivos["almacen/ACTUAL.json"] = alm
        for clave in ("crudo", "conjunto_apto"):
            archivos[f"almacen/{meta[clave]}"] = alm.parent / meta[clave]
    his = salidas / "historial" / "ACTUAL.json"
    if his.exists():
        meta = json.loads(his.read_text(encoding="utf-8"))
        archivos["historial/ACTUAL.json"] = his
        archivos[f"historial/{meta['archivo']}"] = his.parent / meta["archivo"]
    faltan = [r for r, p in archivos.items() if not p.exists()]
    if faltan:
        raise ErrorEstadoS3(f"El estado local apunta a archivos que no existen: {faltan}")
    return archivos


def id_estado_local(salidas: Path) -> str | None:
    """Id del estado local: el registrado al publicar o descargar.

    Si no hay registro (estado anterior a esta funcion), el mayor id con forma
    AAAAMMDD_HHMMSS de los punteros del almacen y del historial.
    """
    salidas = Path(salidas)
    registro = salidas / PREFIJO_ESTADO / "ACTUAL.json"
    if registro.exists():
        return json.loads(registro.read_text(encoding="utf-8"))["id"]
    ids = []
    for componente in COMPONENTES:
        puntero = salidas / componente / "ACTUAL.json"
        if puntero.exists():
            ident = json.loads(puntero.read_text(encoding="utf-8")).get("id_ejecucion", "")
            if PATRON_ID.match(ident):
                ids.append(ident)
    return max(ids) if ids else None


def _registrar_local(salidas: Path, id_estado: str, origen: str) -> None:
    datos = {
        "id": id_estado,
        "origen": origen,
        "registrado": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    _escribir_atomico(
        Path(salidas) / PREFIJO_ESTADO / "ACTUAL.json", json.dumps(datos, indent=2).encode("utf-8")
    )


# --------------------------------------------------------------- publicar y descargar


def publicar_estado(
    salidas: Path, id_estado: str, destino: DestinoS3, cliente, contexto: dict
) -> dict:
    """Sube el estado vigente a estado/<id>/ y actualiza estado/ACTUAL.json."""
    if not PATRON_ID.match(id_estado):
        raise ErrorEstadoS3(f"Id de estado invalido: {id_estado!r}.")
    archivos = archivos_estado(salidas)
    if not archivos:
        raise ErrorEstadoS3("No hay estado local que publicar.")
    shas = {}
    for relativa, ruta in sorted(archivos.items()):
        datos = ruta.read_bytes()
        shas[relativa] = _sha_bytes(datos)
        cliente.put_object(
            Bucket=destino.bucket,
            Key=destino.clave(PREFIJO_ESTADO, id_estado, relativa),
            Body=datos,
        )
    estado = {
        "id": id_estado,
        "prefijo": destino.clave(PREFIJO_ESTADO, id_estado) + "/",
        "archivos": shas,
        **contexto,
    }
    cuerpo = json.dumps(estado, ensure_ascii=False, indent=2).encode("utf-8")
    cliente.put_object(
        Bucket=destino.bucket,
        Key=destino.clave(PREFIJO_ESTADO, id_estado, "estado.json"),
        Body=cuerpo,
    )
    # El puntero se reescribe al final: si algo falla antes, sigue apuntando al anterior.
    cliente.put_object(
        Bucket=destino.bucket, Key=destino.clave(PREFIJO_ESTADO, "ACTUAL.json"), Body=cuerpo
    )
    _registrar_local(salidas, id_estado, "publicado")
    return {
        "id": id_estado,
        "uri": destino.uri(PREFIJO_ESTADO, id_estado) + "/",
        "archivos": len(shas),
    }


def leer_estado_remoto(destino: DestinoS3, cliente) -> dict | None:
    datos = _leer_objeto(cliente, destino.bucket, destino.clave(PREFIJO_ESTADO, "ACTUAL.json"))
    return None if datos is None else json.loads(datos)


def descargar_estado(salidas: Path, destino: DestinoS3, cliente) -> dict:
    """Descarga el estado remoto si es mas nuevo que el local (por id) y lo verifica.

    Devuelve {"accion": ...}: ``sin_estado_remoto``, ``local_al_dia``,
    ``local_mas_nuevo`` o ``descargado``.
    """
    salidas = Path(salidas)
    remoto = leer_estado_remoto(destino, cliente)
    local = id_estado_local(salidas)
    if remoto is None:
        return {"accion": "sin_estado_remoto", "local": local}
    if local is not None and remoto["id"] <= local:
        accion = "local_al_dia" if remoto["id"] == local else "local_mas_nuevo"
        return {"accion": accion, "local": local, "remoto": remoto["id"]}

    punteros: dict[Path, bytes] = {}
    nuevos = 0
    for relativa, sha in sorted(remoto["archivos"].items()):
        if Path(relativa).parts[0] not in COMPONENTES or ".." in Path(relativa).parts:
            raise ErrorEstadoS3(f"Ruta inesperada en el estado remoto: {relativa}")
        destino_local = salidas / relativa
        es_puntero = destino_local.name == "ACTUAL.json"
        if not es_puntero and destino_local.exists():
            if _sha_crudo(destino_local) != sha:
                raise ErrorEstadoS3(
                    f"{relativa} ya existe localmente con otro contenido; no se sobrescribe."
                )
            continue
        datos = _leer_objeto(
            cliente, destino.bucket, destino.clave(PREFIJO_ESTADO, remoto["id"], relativa)
        )
        if datos is None or _sha_bytes(datos) != sha:
            raise ErrorEstadoS3(f"{relativa}: falta en S3 o su SHA-256 no coincide.")
        if es_puntero:
            punteros[destino_local] = datos  # se escriben al final
        else:
            _escribir_atomico(destino_local, datos)
            nuevos += 1
    for ruta, datos in punteros.items():
        _escribir_atomico(ruta, datos)
    _registrar_local(salidas, remoto["id"], "descargado")
    return {
        "accion": "descargado",
        "local_previo": local,
        "remoto": remoto["id"],
        "archivos_nuevos": nuevos,
    }


# --------------------------------------------------------------- insumos


def descargar_insumos(cfg: ConfigPiloto, bucket: str, cliente, incluir_solo_local=False) -> dict:
    """Baja cada entrada congelada de s3://<bucket>/insumos/<ruta> y verifica su SHA-256.

    Una entrada local que ya coincide se omite; una que no coincide es un error
    (nunca se sobrescribe).
    """
    destino = DestinoS3(bucket=bucket, prefijo="")
    resultado = {}
    for nombre, e in sorted(cfg.entradas.items()):
        if e.solo_fuente_local and not incluir_solo_local:
            continue
        relativa = Path(e.ruta).resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        if e.ruta.exists():
            if sha256_archivo(e.ruta) != e.sha256:
                raise ErrorEstadoS3(f"{relativa} ya existe con otro SHA-256; no se sobrescribe.")
            resultado[nombre] = "ya_estaba"
            continue
        datos = _leer_objeto(cliente, bucket, destino.clave(PREFIJO_INSUMOS, relativa))
        if datos is None:
            raise ErrorEstadoS3(f"Falta s3://{bucket}/{PREFIJO_INSUMOS}/{relativa}.")
        temporal = e.ruta.with_name(e.ruta.name + ".descarga")
        e.ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal.write_bytes(datos)
        sha = _sha_insumo(temporal, e.ruta.suffix)
        if sha != e.sha256:
            temporal.unlink()
            raise ErrorEstadoS3(f"{relativa}: el SHA-256 descargado no coincide con piloto.yaml.")
        os.replace(temporal, e.ruta)
        resultado[nombre] = "descargado"
    return resultado


def _sha_insumo(ruta: Path, extension: str) -> str:
    """SHA-256 con la misma regla de piloto.yaml (texto normalizado segun la extension)."""
    from proyecto_grado.piloto.config import EXTENSIONES_TEXTO

    datos = Path(ruta).read_bytes()
    if extension.lower() in EXTENSIONES_TEXTO:
        datos = datos.replace(b"\r\n", b"\n")
    return _sha_bytes(datos)
