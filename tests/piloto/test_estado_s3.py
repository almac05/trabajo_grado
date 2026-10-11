"""Estado de la piloto en S3 e insumos congelados (botocore.stub y S3 en memoria)."""

import hashlib
import io
import json
from datetime import date, datetime

import boto3
import pandas as pd
import pytest
import yaml
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.config import (
    RUTA_CONFIG_PREDETERMINADA,
    cargar_configuracion,
    sha256_archivo,
)
from proyecto_grado.piloto.correccion import agregar_al_historial
from proyecto_grado.piloto.estado_s3 import (
    ErrorEstadoS3,
    archivos_estado,
    descargar_estado,
    descargar_insumos,
    id_estado_local,
    publicar_estado,
)
from proyecto_grado.piloto.extraccion import guardar_almacen
from proyecto_grado.piloto.fechas import ZONA
from proyecto_grado.piloto.salida_s3 import DestinoS3

DESTINO = DestinoS3("bucket", "piloto")


@pytest.fixture
def cliente():
    return boto3.client(
        "s3", region_name="us-east-2", aws_access_key_id="x", aws_secret_access_key="x"
    )


def cuerpo(datos: bytes):
    return {"Body": StreamingBody(io.BytesIO(datos), len(datos))}


def sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def crear_estado(salidas, ident):
    """Almacen e historial vigentes con id ``ident``."""
    crudo = pd.DataFrame({"PK_INTERVALO_DESPACHO": [1], "FECHA_INICIAL": ["2026-10-12"]})
    guardar_almacen(salidas / "almacen", ident, crudo, crudo, date(2026, 10, 12), True)
    filas = pd.DataFrame(
        {
            "id_ejecucion": [ident],
            "origen": ["piloto"],
            "version": ["definitiva"],
            "emitido": [""],
            "route": [1],
            "dia_op": ["2026-10-13"],
            "hora": ["05:00"],
            "tipo_dia": ["LABORAL"],
            "regimen": ["ordinario"],
            "pred_xgboost": [1.0],
            "ref52": [1.0],
            "factor": [1.0],
            "pred_final": [1.0],
        }
    )
    agregar_al_historial(salidas / "historial", ident, filas)


class S3Memoria:
    """Cliente S3 minimo en memoria (get_object/put_object), sin DeleteObject."""

    def __init__(self):
        self.objetos: dict[tuple[str, str], bytes] = {}

    def put_object(self, Bucket, Key, Body):  # noqa: N803 - firma de boto3
        self.objetos[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.read()

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.objetos:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        datos = self.objetos[(Bucket, Key)]
        return {"Body": io.BytesIO(datos)}


# ------------------------------------------------------------------ estado local


@pytest.mark.unit
def test_archivos_e_id_del_estado_local(tmp_path):
    assert archivos_estado(tmp_path) == {} and id_estado_local(tmp_path) is None
    crear_estado(tmp_path, "20261013_003000")
    assert sorted(archivos_estado(tmp_path)) == [
        "almacen/ACTUAL.json",
        "almacen/conjunto_apto_20261013_003000.parquet",
        "almacen/crudo_20261013_003000.parquet",
        "historial/ACTUAL.json",
        "historial/predicciones_emitidas_20261013_003000.parquet",
    ]
    assert id_estado_local(tmp_path) == "20261013_003000"


# ------------------------------------------------------------------ publicar (Stubber)


@pytest.mark.unit
def test_publicar_sube_archivos_estado_y_puntero_al_final(tmp_path, cliente):
    crear_estado(tmp_path, "20261013_003000")
    archivos = archivos_estado(tmp_path)
    with Stubber(cliente) as st:
        for rel in sorted(archivos):
            st.add_response(
                "put_object",
                {},
                {"Bucket": "bucket", "Body": ANY, "Key": f"piloto/estado/20261013_003000/{rel}"},
            )
        st.add_response(
            "put_object",
            {},
            {"Bucket": "bucket", "Body": ANY, "Key": "piloto/estado/20261013_003000/estado.json"},
        )
        st.add_response(
            "put_object", {}, {"Bucket": "bucket", "Body": ANY, "Key": "piloto/estado/ACTUAL.json"}
        )
        r = publicar_estado(tmp_path, "20261013_003000", DESTINO, cliente, {"entorno": "EC2"})
        st.assert_no_pending_responses()
    assert r["archivos"] == 5 and r["uri"] == "s3://bucket/piloto/estado/20261013_003000/"
    registro = json.loads((tmp_path / "estado" / "ACTUAL.json").read_text())
    assert registro["id"] == "20261013_003000" and registro["origen"] == "publicado"


@pytest.mark.unit
def test_publicar_sin_estado_o_con_id_invalido(tmp_path, cliente):
    with pytest.raises(ErrorEstadoS3, match="No hay estado"):
        publicar_estado(tmp_path, "20261013_003000", DESTINO, cliente, {})
    crear_estado(tmp_path, "backtest_inicial")
    with pytest.raises(ErrorEstadoS3, match="invalido"):
        publicar_estado(tmp_path, "backtest_inicial", DESTINO, cliente, {})


# ------------------------------------------------------------------ descargar (Stubber)


def estado_remoto(origen, ident):
    """Publica en un S3 en memoria el estado de ``origen`` y devuelve sus objetos."""
    s3 = S3Memoria()
    publicar_estado(origen, ident, DESTINO, s3, {})
    return s3


@pytest.mark.unit
def test_descarga_si_el_remoto_es_mas_nuevo_y_verifica(tmp_path, cliente):
    origen, local = tmp_path / "ec2", tmp_path / "windows"
    crear_estado(origen, "20261014_003000")
    remoto = estado_remoto(origen, "20261014_003000")
    actual = remoto.objetos[("bucket", "piloto/estado/ACTUAL.json")]
    with Stubber(cliente) as st:
        st.add_response(
            "get_object", cuerpo(actual), {"Bucket": "bucket", "Key": "piloto/estado/ACTUAL.json"}
        )
        for rel in sorted(json.loads(actual)["archivos"]):
            clave = f"piloto/estado/20261014_003000/{rel}"
            st.add_response(
                "get_object",
                cuerpo(remoto.objetos[("bucket", clave)]),
                {"Bucket": "bucket", "Key": clave},
            )
        r = descargar_estado(local, DESTINO, cliente)
        st.assert_no_pending_responses()
    assert r["accion"] == "descargado" and r["archivos_nuevos"] == 3
    assert id_estado_local(local) == "20261014_003000"
    for rel in archivos_estado(origen):
        assert (local / rel).read_bytes() == (origen / rel).read_bytes()


@pytest.mark.unit
def test_no_descarga_si_el_local_esta_al_dia_o_es_mas_nuevo(tmp_path, cliente):
    origen, local = tmp_path / "ec2", tmp_path / "windows"
    crear_estado(origen, "20261014_003000")
    actual = estado_remoto(origen, "20261014_003000").objetos[
        ("bucket", "piloto/estado/ACTUAL.json")
    ]
    crear_estado(local, "20261015_003000")
    with Stubber(cliente) as st:
        st.add_response(
            "get_object", cuerpo(actual), {"Bucket": "bucket", "Key": "piloto/estado/ACTUAL.json"}
        )
        r = descargar_estado(local, DESTINO, cliente)
    assert r == {
        "accion": "local_mas_nuevo",
        "local": "20261015_003000",
        "remoto": "20261014_003000",
    }


@pytest.mark.unit
def test_sin_estado_remoto(tmp_path, cliente):
    with Stubber(cliente) as st:
        st.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
        assert descargar_estado(tmp_path, DESTINO, cliente)["accion"] == "sin_estado_remoto"


@pytest.mark.unit
def test_sha_alterado_no_deja_nada_a_medias(tmp_path, cliente):
    origen, local = tmp_path / "ec2", tmp_path / "windows"
    crear_estado(origen, "20261014_003000")
    remoto = estado_remoto(origen, "20261014_003000")
    actual = remoto.objetos[("bucket", "piloto/estado/ACTUAL.json")]
    primero = sorted(json.loads(actual)["archivos"])[0]  # almacen/ACTUAL.json
    with Stubber(cliente) as st:
        st.add_response(
            "get_object", cuerpo(actual), {"Bucket": "bucket", "Key": "piloto/estado/ACTUAL.json"}
        )
        st.add_response(
            "get_object",
            cuerpo(b"alterado"),
            {"Bucket": "bucket", "Key": f"piloto/estado/20261014_003000/{primero}"},
        )
        with pytest.raises(ErrorEstadoS3, match="SHA-256"):
            descargar_estado(local, DESTINO, cliente)
    assert not (local / "almacen" / "ACTUAL.json").exists()
    assert id_estado_local(local) is None


@pytest.mark.unit
def test_no_sobrescribe_un_archivo_local_distinto(tmp_path):
    origen, local = tmp_path / "ec2", tmp_path / "windows"
    crear_estado(origen, "20261014_003000")
    remoto = estado_remoto(origen, "20261014_003000")
    (local / "almacen").mkdir(parents=True)
    (local / "almacen" / "crudo_20261014_003000.parquet").write_bytes(b"otro")
    with pytest.raises(ErrorEstadoS3, match="no se sobrescribe"):
        descargar_estado(local, DESTINO, remoto)


# ------------------------------------------------------------------ insumos


def config_insumos(tmp_path, contenido: bytes):
    """piloto.yaml con una entrada de texto en .pytest_tmp (bajo la raiz del proyecto)."""
    ruta = tmp_path / "insumos" / "datos.csv"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(contenido)
    esperado = sha256_archivo(ruta)
    ruta.unlink()
    raw = yaml.safe_load(RUTA_CONFIG_PREDETERMINADA.read_text(encoding="utf-8"))
    rel = ruta.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    raw["entradas"] = {
        "datos": {"ruta": rel, "sha256": esperado},
        "solo_local": {"ruta": rel + ".local", "sha256": "0" * 64, "solo_fuente_local": True},
    }
    cfg_ruta = tmp_path / "piloto.yaml"
    cfg_ruta.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return cargar_configuracion(cfg_ruta), ruta, rel


@pytest.mark.unit
def test_descargar_insumos_verifica_y_omite_los_presentes(tmp_path, cliente):
    cfg, ruta, rel = config_insumos(tmp_path, b"a,b\r\n1,2\r\n")
    with Stubber(cliente) as st:
        st.add_response(
            "get_object", cuerpo(b"a,b\n1,2\n"), {"Bucket": "bucket", "Key": f"insumos/{rel}"}
        )
        assert descargar_insumos(cfg, "bucket", cliente) == {"datos": "descargado"}
        st.assert_no_pending_responses()
    assert ruta.read_bytes() == b"a,b\n1,2\n"  # CRLF/LF: mismo SHA-256 normalizado
    assert descargar_insumos(cfg, "bucket", cliente) == {"datos": "ya_estaba"}


@pytest.mark.unit
def test_insumo_con_sha_distinto_no_se_instala(tmp_path, cliente):
    cfg, ruta, rel = config_insumos(tmp_path, b"a,b\n1,2\n")
    with Stubber(cliente) as st:
        st.add_response(
            "get_object", cuerpo(b"a,b\n9,9\n"), {"Bucket": "bucket", "Key": f"insumos/{rel}"}
        )
        with pytest.raises(ErrorEstadoS3, match="no coincide"):
            descargar_insumos(cfg, "bucket", cliente)
    assert not ruta.exists() and not list(ruta.parent.glob("*.descarga"))
    ruta.write_bytes(b"otro")
    with pytest.raises(ErrorEstadoS3, match="no se sobrescribe"):
        descargar_insumos(cfg, "bucket", cliente)


# ------------------------------------------------------------------ orquestador


@pytest.mark.unit
def test_modos_del_orquestador(tmp_path, monkeypatch):
    from proyecto_grado.piloto.nocturno import CODIGO_OK, Dependencias, main

    monkeypatch.setenv("PILOTO_ENTORNO", "LOCAL")
    monkeypatch.setenv("PILOTO_S3_BUCKET", "bucket")
    monkeypatch.setenv("PILOTO_S3_PREFIJO", "piloto")
    origen = tmp_path / "ec2"
    crear_estado(origen, "20261014_003000")
    s3 = estado_remoto(origen, "20261014_003000")
    # Con el arbol "sucio" y a las 10:00: los modos de S3 no lo exigen ni usan la base.
    d = Dependencias(
        reloj=lambda: datetime(2026, 10, 14, 10, 0, tzinfo=ZONA),
        git=lambda a: "a" * 40 if a[0] == "rev-parse" else " M src/x.py\n",
        cargar_env=lambda: None,
        cliente_s3=lambda: s3,
    )
    salidas = tmp_path / "windows"
    assert main(["--sincronizar-estado", "--directorio-salidas", str(salidas)], d) == CODIGO_OK
    assert id_estado_local(salidas) == "20261014_003000"
    m = json.loads(next(salidas.glob("ejecuciones/*/manifiesto.json")).read_text("utf-8"))
    assert (
        m["modo"] == "sincronizar_estado" and m["estado_s3"]["descarga"]["accion"] == "descargado"
    )
    for prohibido in (
        ["--sincronizar-estado", "--descargar-insumos"],
        ["--sincronizar-estado", "--subir-s3"],
        ["--descargar-insumos", "--fecha-objetivo", "2026-10-01"],
    ):
        with pytest.raises(SystemExit):
            main(prohibido, d)


@pytest.mark.unit
def test_corrida_real_trae_el_estado_antes_de_extraer(tmp_path, monkeypatch):
    from proyecto_grado.piloto.nocturno import CODIGO_ERROR, Dependencias, main
    from tests.piloto.test_nocturno import FuenteQueFalla, config_minima, git_falso

    monkeypatch.setenv("PILOTO_ENTORNO", "EC2")
    monkeypatch.setenv("PILOTO_S3_BUCKET", "bucket")
    monkeypatch.setenv("PILOTO_S3_PREFIJO", "piloto")
    origen = tmp_path / "windows"
    crear_estado(origen, "20261014_003000")
    s3 = estado_remoto(origen, "20261014_003000")
    d = Dependencias(
        reloj=lambda: datetime(2026, 10, 15, 0, 30, tzinfo=ZONA),
        git=git_falso(),
        cargar_env=lambda: None,
        cliente_s3=lambda: s3,
        fuente=lambda cfg, n: FuenteQueFalla(),
    )
    salidas = tmp_path / "ec2"
    codigo = main(
        [
            "--subir-s3",
            "--directorio-salidas",
            str(salidas),
            "--config",
            str(config_minima(tmp_path)),
        ],
        d,
    )
    assert codigo == CODIGO_ERROR  # la fuente simulada falla al extraer
    m = json.loads(next(salidas.glob("ejecuciones/*/manifiesto.json")).read_text("utf-8"))
    pasos = list(m["pasos"])
    assert pasos.index("estado_descarga") < pasos.index("extraccion")
    assert m["estado_s3"]["descarga"]["accion"] == "descargado"
    assert id_estado_local(salidas) == "20261014_003000"
    # En ERROR no se publica estado.
    assert "publicacion" not in m["estado_s3"]


@pytest.mark.unit
def test_publicar_estado_del_orquestador_solo_con_ok(tmp_path, monkeypatch):
    from proyecto_grado.piloto.nocturno import Dependencias, Ejecucion, Estado, publicar_estado

    monkeypatch.setenv("PILOTO_S3_BUCKET", "bucket")
    monkeypatch.setenv("PILOTO_S3_PREFIJO", "piloto")
    crear_estado(tmp_path, "20261015_003000")
    s3 = S3Memoria()
    d = Dependencias(
        reloj=lambda: datetime(2026, 10, 15, 0, 45, tzinfo=ZONA), cliente_s3=lambda: s3
    )
    e = Ejecucion(
        id="20261015_003000",
        inicio=d.reloj(),
        carpeta=tmp_path,
        salidas=tmp_path,
        manifiesto={"codigo": {"commit": "a" * 40}, "modo": "nocturno"},
    )
    e.estado = Estado.ERROR
    publicar_estado(e, d, {"entorno": "EC2"})
    assert not s3.objetos
    e.estado = Estado.OK
    publicar_estado(e, d, {"entorno": "EC2"})
    actual = json.loads(s3.objetos[("bucket", "piloto/estado/ACTUAL.json")])
    assert actual["id"] == "20261015_003000" and actual["entorno"] == "EC2"
    assert actual["commit"] == "a" * 40 and len(actual["archivos"]) == 5
    assert e.manifiesto["estado_s3"]["publicacion"]["archivos"] == 5
