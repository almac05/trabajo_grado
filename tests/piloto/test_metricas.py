"""Metricas de CloudWatch: catalogo cerrado, datos, publicacion y tolerancia a fallos."""

import ast
import json
import re
import sys
import types
from datetime import UTC, datetime

import boto3
import pytest
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError
from botocore.stub import Stubber

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto import metricas
from proyecto_grado.piloto.fechas import ZONA

LIMITE_CATALOGO = 17
FIN = datetime(2026, 10, 13, 0, 41, 7, tzinfo=ZONA)
FIN_UTC = datetime(2026, 10, 13, 5, 41, 7, tzinfo=UTC)
TABLERO = PROJECT_ROOT / "deploy" / "cloudwatch" / "tablero_despacho.json"


def manifiesto_ok(**cambios):
    m = {
        "estado": "OK",
        "segundos": 312.4,
        "pasos": {"extraccion": {"segundos": 41.5}},
        "extraccion": {"deduplicado": {"filas": 1210, "despachos": 1200}},
        "recomendacion": {"filas": 57},
        "bd": {"corrida_abierta": True, "cerrada": True, "filas": 57},
        "factor": {"1": {"valor": 0.87}, "3": {"valor": 0.91}},
        "desempeno": {
            "jornada": "2026-10-12",
            "por_ruta": {
                "1": {"mae": 4.5, "rmse": 6.1, "mape_u10": 21.3, "sesgo_pct": -3.2},
                "3": {"mae": 3.1, "rmse": 4.0, "mape_u10": None, "sesgo_pct": 1.5},
            },
        },
    }
    m.update(cambios)
    return m


def cw_stub():
    return boto3.client(
        "cloudwatch", region_name="us-east-2", aws_access_key_id="x", aws_secret_access_key="x"
    )


class CWFalso:
    def __init__(self, error=None):
        self.llamadas = []
        self.error = error

    def put_metric_data(self, Namespace, MetricData):  # noqa: N803 - firma de boto3
        if self.error is not None:
            raise self.error
        self.llamadas.append({"Namespace": Namespace, "MetricData": MetricData})
        return {}


@pytest.fixture
def activadas(monkeypatch):
    monkeypatch.setenv("PILOTO_METRICAS", "1")
    monkeypatch.delenv("PILOTO_CW_NAMESPACE", raising=False)


# ------------------------------------------------------------------ catalogo


def _claves(datos):
    return {metricas._clave_de(d) for d in datos}


@pytest.mark.unit
def test_catalogo_cerrado_de_17_combinaciones():
    claves = [d.clave for d in metricas.CATALOGO]
    assert len(claves) == len(set(claves)) <= LIMITE_CATALOGO
    # Todas las combinaciones que el codigo puede generar, en todos los escenarios.
    escenarios = [
        manifiesto_ok(),
        manifiesto_ok(estado="ERROR", pasos={}, extraccion={}, factor={}, desempeno={}),
        {"estado": "EN_CURSO"},
        manifiesto_ok(factor={"1": {"valor": 1}, "2": {"valor": 1}}),  # ruta 2: fuera
    ]
    generadas = set()
    for m in escenarios:
        generadas |= _claves(metricas.datos_de_corrida(m, memoria_mb=512.0))
    generadas |= _claves([metricas.dato_jornada_cubierta(True)])
    assert generadas <= set(claves)
    assert len(generadas) <= LIMITE_CATALOGO
    assert "FactorCorreccion[Ruta=2]" not in generadas


@pytest.mark.unit
def test_todo_metricname_del_codigo_esta_en_el_catalogo():
    """Ningun modulo de la piloto llama a put_metric_data fuera de metricas.py, y todo
    nombre que se pasa a ``dato(...)`` es del catalogo."""
    nombres = {d.nombre for d in metricas.CATALOGO}
    piloto = PROJECT_ROOT / "src" / "proyecto_grado" / "piloto"
    for ruta in piloto.glob("*.py"):
        codigo = ruta.read_text(encoding="utf-8")
        if ruta.name != "metricas.py":
            assert "put_metric_data" not in codigo, ruta.name
        for nodo in ast.walk(ast.parse(codigo)):
            if (
                isinstance(nodo, ast.Call)
                and getattr(nodo.func, "attr", getattr(nodo.func, "id", None)) == "dato"
                and nodo.args
                and isinstance(nodo.args[0], ast.Constant)
            ):
                assert nodo.args[0].value in nombres, (ruta.name, nodo.args[0].value)
    assert set(metricas.METRICAS_DESEMPENO.values()) <= nombres


# ------------------------------------------------------------------ datos


@pytest.mark.unit
def test_datos_de_una_corrida_completa():
    datos = {metricas._clave_de(d): d for d in metricas.datos_de_corrida(manifiesto_ok(), 300.0)}
    assert datos["EstadoCorrida"]["Value"] == 0
    assert datos["DuracionTotal"] == {
        "MetricName": "DuracionTotal",
        "Value": 312.4,
        "Unit": "Seconds",
    }
    assert datos["RegistrosExtraidos"]["Value"] == 1200  # deduplicadas
    assert datos["FilasRecomendaciones"]["Value"] == 57
    assert datos["FactorCorreccion[Ruta=3]"] == {
        "MetricName": "FactorCorreccion",
        "Value": 0.91,
        "Unit": "None",
        "Dimensions": [{"Name": "Ruta", "Value": "3"}],
    }
    assert datos["MemoriaPico"]["Unit"] == "Megabytes"
    assert datos["ErrorMAPE[Ruta=1]"]["Unit"] == "Percent"
    assert datos["SesgoPct[Ruta=1]"]["Value"] == -3.2
    assert "ErrorMAPE[Ruta=3]" not in datos  # None: no se envia
    assert len(datos) == 15


@pytest.mark.unit
@pytest.mark.parametrize(
    ("estado", "codigo"),
    [("OK", 0), ("ADVERTENCIA", 1), ("CONTINGENCIA", 2), ("ERROR", 3), ("EN_CURSO", 3)],
)
def test_codigo_de_estado(estado, codigo):
    d = metricas.datos_de_corrida({"estado": estado, "segundos": 1})
    assert d[0] == {"MetricName": "EstadoCorrida", "Value": codigo, "Unit": "None"}


@pytest.mark.unit
def test_error_temprano_envia_solo_estado_y_duracion():
    m = {"estado": "ERROR", "segundos": 2.0, "pasos": {"preparacion": {"segundos": 1.0}}}
    assert _claves(metricas.datos_de_corrida(m)) == {"EstadoCorrida", "DuracionTotal"}


@pytest.mark.unit
def test_filas_generadas_si_no_se_escribio_en_la_base():
    m = manifiesto_ok(bd={})
    d = {metricas._clave_de(x): x for x in metricas.datos_de_corrida(m)}
    assert d["FilasRecomendaciones"]["Value"] == 57


@pytest.mark.unit
def test_memoria_pico_suma_self_y_children_en_mb(monkeypatch):
    falso = types.SimpleNamespace(
        RUSAGE_SELF=0,
        RUSAGE_CHILDREN=-1,
        getrusage=lambda q: types.SimpleNamespace(ru_maxrss=1024 * (300 if q == 0 else 100)),
    )
    monkeypatch.setitem(sys.modules, "resource", falso)
    assert metricas.memoria_pico_mb() == 400.0
    monkeypatch.setitem(sys.modules, "resource", None)  # Windows: ImportError
    assert metricas.memoria_pico_mb() is None


# ------------------------------------------------------------------ publicacion


@pytest.mark.unit
def test_publicacion_con_stubber_namespace_nombres_unidades_y_dimensiones(activadas):
    cliente = cw_stub()
    datos = [
        metricas.dato("EstadoCorrida", 0),
        metricas.dato("FactorCorreccion", 0.87, 1),
        metricas.dato("SesgoPct", -3.2, "3"),
    ]
    esperado = {
        "Namespace": "Montebello/Despacho",
        "MetricData": [
            {"MetricName": "EstadoCorrida", "Value": 0.0, "Unit": "None", "Timestamp": FIN_UTC},
            {
                "MetricName": "FactorCorreccion",
                "Value": 0.87,
                "Unit": "None",
                "Dimensions": [{"Name": "Ruta", "Value": "1"}],
                "Timestamp": FIN_UTC,
            },
            {
                "MetricName": "SesgoPct",
                "Value": -3.2,
                "Unit": "Percent",
                "Dimensions": [{"Name": "Ruta", "Value": "3"}],
                "Timestamp": FIN_UTC,
            },
        ],
    }
    with Stubber(cliente) as st:
        st.add_response("put_metric_data", {}, esperado)
        r = metricas.publicar_metricas(datos, FIN, lambda: cliente)
        st.assert_no_pending_responses()
    assert r["metricas_publicadas"] is True
    assert r["metricas"] == ["EstadoCorrida", "FactorCorreccion[Ruta=1]", "SesgoPct[Ruta=3]"]
    assert r["timestamp"] == "2026-10-13T05:41:07+00:00"


@pytest.mark.unit
def test_timestamp_utc_con_zona(activadas):
    cw = CWFalso()
    metricas.publicar_metricas([metricas.dato("DuracionTotal", 1)], FIN, lambda: cw)
    ts = cw.llamadas[0]["MetricData"][0]["Timestamp"]
    assert ts.tzinfo is not None and ts.utcoffset().total_seconds() == 0 and ts == FIN
    # Una hora sin zona no se publica (y no lanza).
    r = metricas.publicar_metricas([metricas.dato("DuracionTotal", 1)], datetime(2026, 10, 13))
    assert r["metricas_publicadas"] is False


@pytest.mark.unit
def test_namespace_desde_el_entorno(activadas, monkeypatch):
    monkeypatch.setenv("PILOTO_CW_NAMESPACE", "Otro/Espacio")
    cw = CWFalso()
    metricas.publicar_metricas([metricas.dato("DuracionTotal", 1)], FIN, lambda: cw)
    assert cw.llamadas[0]["Namespace"] == "Otro/Espacio"


@pytest.mark.unit
def test_sin_piloto_metricas_no_se_crea_cliente(monkeypatch):
    creados = []
    for valor in (None, "0", "si"):
        if valor is None:
            monkeypatch.delenv("PILOTO_METRICAS", raising=False)
        else:
            monkeypatch.setenv("PILOTO_METRICAS", valor)
        r = metricas.publicar_metricas(
            [metricas.dato("DuracionTotal", 1)], FIN, lambda: creados.append(1)
        )
        assert r["metricas_publicadas"] is False and r["motivo"].startswith("desactivadas")
    assert creados == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "error",
    [
        ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "no autorizado"}}, "PutMetricData"
        ),
        ReadTimeoutError(endpoint_url="https://monitoring.us-east-2.amazonaws.com"),
        ConnectTimeoutError(endpoint_url="https://monitoring.us-east-2.amazonaws.com"),
    ],
    ids=["client_error", "read_timeout", "connect_timeout"],
)
def test_fallo_de_cloudwatch_no_lanza(activadas, monkeypatch, error):
    monkeypatch.setenv("REGISTEL_DB_PASSWORD", "no autorizado")
    r = metricas.publicar_metricas([metricas.dato("DuracionTotal", 1)], FIN, lambda: CWFalso(error))
    assert r["metricas_publicadas"] is False
    assert type(error).__name__ in r["motivo"] and "no autorizado" not in r["motivo"]


@pytest.mark.unit
def test_cliente_con_tiempos_cortos_y_dos_intentos(monkeypatch):
    monkeypatch.delenv("PILOTO_AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    c = metricas.cliente_cloudwatch()
    assert c.meta.region_name == "us-east-2"
    assert c.meta.config.connect_timeout == 5 and c.meta.config.read_timeout == 5
    assert c.meta.config.retries["total_max_attempts"] == 2
    monkeypatch.setenv("PILOTO_AWS_REGION", "us-west-2")
    assert metricas.cliente_cloudwatch().meta.region_name == "us-west-2"


@pytest.mark.unit
def test_fuera_del_catalogo_y_no_finitos_se_descartan():
    assert metricas.dato("MetricaNueva", 1) is None
    assert metricas.dato("FactorCorreccion", 1.0) is None  # sin dimension Ruta
    assert metricas.dato("FactorCorreccion", 1.0, 2) is None
    assert metricas.dato("EstadoCorrida", float("nan")) is None
    assert metricas.dato("EstadoCorrida", None) is None


# ------------------------------------------------------------------ tablero


@pytest.mark.unit
def test_tablero_valido_y_sin_datos_de_la_cuenta():
    texto = TABLERO.read_text(encoding="utf-8")
    t = json.loads(texto)
    assert t["start"] == "-P30D"
    assert "REEMPLAZAR_INSTANCE_ID" in texto
    assert "arn:" not in texto and not re.search(r"\b\d{12}\b", texto)
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", texto)
    catalogo = {d.clave for d in metricas.CATALOGO}
    usadas = set()
    for w in t["widgets"]:
        p = w["properties"]
        if w["type"] != "metric":
            continue
        assert p["region"] == "us-east-2"
        assert p["period"] == 3600
        for fila in p["metrics"]:
            if fila[0] != "Montebello/Despacho":
                assert fila[:4] == [
                    "AWS/EC2",
                    "CPUUtilization",
                    "InstanceId",
                    "REEMPLAZAR_INSTANCE_ID",
                ]
                assert fila[4]["period"] == 300 and p["stat"] == "Maximum"
                continue
            valores = [x for x in fila[1:] if not isinstance(x, dict)]
            dims = tuple(zip(valores[1::2], valores[2::2], strict=True))
            clave = metricas.DefinicionMetrica(valores[0], "", dims).clave
            assert clave in catalogo, clave
            usadas.add(clave)
    assert usadas == catalogo  # el tablero muestra todas las metricas publicadas
    titulos = [w["properties"].get("title", "") for w in t["widgets"]]
    assert "MAPE parcial (real ≥ 10) por ruta (%)" in titulos
