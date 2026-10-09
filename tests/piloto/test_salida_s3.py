"""Subida a S3 con botocore.stub (sin AWS real)."""

import boto3
import pytest
from botocore.stub import ANY, Stubber

from proyecto_grado.piloto.salida_s3 import (
    DestinoS3,
    ErrorSalidaS3,
    archivos_a_subir,
    destino_desde_entorno,
    subir,
)


@pytest.fixture
def cliente():
    # Credenciales ficticias solo para construir el cliente; Stubber no envia nada.
    return boto3.client(
        "s3", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x"
    )


@pytest.mark.unit
def test_destino_desde_entorno(monkeypatch):
    monkeypatch.delenv("PILOTO_S3_BUCKET", raising=False)
    with pytest.raises(ErrorSalidaS3, match="PILOTO_S3_BUCKET"):
        destino_desde_entorno()
    monkeypatch.setenv("PILOTO_S3_BUCKET", "mi-bucket")
    monkeypatch.setenv("PILOTO_S3_PREFIJO", "/piloto/")
    d = destino_desde_entorno()
    assert d.clave("planillas", "p.xlsx") == "piloto/planillas/p.xlsx"
    assert d.uri("ejecuciones", "id") == "s3://mi-bucket/piloto/ejecuciones/id"


@pytest.mark.unit
def test_sube_carpeta_planilla_e_instantanea(tmp_path, cliente):
    carpeta = tmp_path / "ejecuciones" / "20261013_003000"
    carpeta.mkdir(parents=True)
    (carpeta / "manifiesto.json").write_text("{}", encoding="utf-8")
    (carpeta / "ejecucion.log").write_text("log", encoding="utf-8")
    planilla = tmp_path / "planilla_2026-10-13_OK_SOMBRA.xlsx"
    planilla.write_bytes(b"x")
    inst = tmp_path / "20261013_003000.parquet"
    inst.write_bytes(b"p")
    archivos = archivos_a_subir(carpeta, planilla, inst, "20261013_003000")
    destino = DestinoS3("b", "piloto")
    claves = [
        "piloto/ejecuciones/20261013_003000/ejecucion.log",
        "piloto/ejecuciones/20261013_003000/manifiesto.json",
        "piloto/planillas/planilla_2026-10-13_OK_SOMBRA.xlsx",
        "piloto/extracciones/20261013_003000.parquet",
    ]
    with Stubber(cliente) as st:
        for k in claves:
            st.add_response("put_object", {}, {"Bucket": "b", "Key": k, "Body": ANY})
        uris = subir(archivos, destino, cliente)
        st.assert_no_pending_responses()
    assert uris == [f"s3://b/{k}" for k in claves]


@pytest.mark.unit
def test_fallo_de_subida(tmp_path, cliente):
    f = tmp_path / "a.json"
    f.write_text("{}", encoding="utf-8")
    with Stubber(cliente) as st:
        st.add_client_error("put_object", service_error_code="AccessDenied")
        with pytest.raises(ErrorSalidaS3, match=r"a.json"):
            subir([(f, ("ejecuciones", "id", "a.json"))], DestinoS3("b", ""), cliente)
