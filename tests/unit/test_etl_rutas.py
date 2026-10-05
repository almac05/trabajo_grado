"""Pruebas del directorio raiz alternativo del ETL.

Con el valor por defecto, las rutas y las llamadas de E/S deben ser las mismas de
siempre; con un directorio alternativo, ninguna lectura o escritura de datos puede
salir de el y el ETL debe detenerse si algun destino ya existe.
"""

import builtins
import json
import os
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import proyecto_grado.etl.config as cfg
import proyecto_grado.etl.extract as extract
import proyecto_grado.etl.gps as gps
import proyecto_grado.etl.model_ready as model_ready
import proyecto_grado.etl.pipeline as pipeline
import proyecto_grado.etl.qc as qc
import proyecto_grado.etl.trip_end as trip_end
from proyecto_grado.etl.transforms import run_block4

# ---------------------------------------------------------------------------
# Datos sinteticos
# ---------------------------------------------------------------------------


def _despachos_crudos(n: int = 12) -> pd.DataFrame:
    """Salida sintetica del Bloque 3: despachos completos de las rutas 1 y 3."""
    base = pd.Timestamp("2024-04-16 05:30:00")
    filas = []
    for i in range(n):
        t_ini = base + pd.Timedelta(minutes=30 * i)
        t_fin = t_ini + pd.Timedelta(minutes=90)
        filas.append(
            {
                "PK_INTERVALO_DESPACHO": i + 1,
                "FECHA_INICIAL": t_ini.date().isoformat(),
                "HORA_INICIAL_PLAN": t_ini.strftime("%H:%M:%S"),
                "HORA_INICIAL_REAL": t_ini.strftime("%H:%M:%S"),
                "HORA_INICIAL_AUX": None,
                "FECHA_FINAL": t_fin.date().isoformat(),
                "HORA_FINAL_PLAN": t_fin.strftime("%H:%M:%S"),
                "HORA_FINAL_REAL": t_fin.strftime("%H:%M:%S"),
                "HORA_FINAL_AUX": None,
                "FK_RUTA": 1 if i % 2 == 0 else 3,
                "PASAJEROS": 15 + i,
                "DISTANCIA": 8.5,
                "FK_VEHICULO": 100 + i % 3,
                "CONDUCTOR": 200,
                "ESTADO_DESPACHO": 1,
                "PK_INFORMACION_REGISTRADORA": 1000 + i,
                "PLACA": f"ABC{100 + i % 3}",
                "ALARMAS": 1,
            }
        )
    return pd.DataFrame(filas)


def _salida_bloque7() -> pd.DataFrame:
    """Salida sintetica del Bloque 7 para los Bloques 8 y 9."""
    return pd.DataFrame(
        {
            "PK_INTERVALO_DESPACHO": [1, 2],
            "PLACA": ["ABC123", "DEF456"],
            "FK_RUTA": [1, 3],
            "FECHA_INICIAL": ["2024-04-16", "2024-04-16"],
            "HORA_INICIAL_REAL": ["2024-04-16 08:00:00", "2024-04-16 09:00:00"],
            "HORA_FINAL_REAL": [pd.NaT, pd.NaT],
            "HORA_FIN_ESTIMADA": ["2024-04-16 09:00:00", "2024-04-16 10:00:00"],
            "PASAJEROS": [20, 30],
            "DISTANCIA": [12.0, 13.0],
            "RECORRIDO_COMPLETO": [0, 0],
            "FIN_TIPO": ["TRUNCADO_RETORNO", "TRUNCADO_RETORNO"],
            "HORA_FIN_FUENTE": ["GPS_ESTIMADA", "GPS_ESTIMADA"],
            "qc_hard_fail": [False, False],
        }
    )


# ---------------------------------------------------------------------------
# Captura de E/S
# ---------------------------------------------------------------------------


class _RegistroES:
    """Registra las rutas de lectura y escritura; opcionalmente no escribe nada."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, escribir: bool) -> None:
        self.lecturas: list[str] = []
        self.escrituras: list[str] = []
        self.directorios: list[str] = []
        to_parquet, to_csv = pd.DataFrame.to_parquet, pd.DataFrame.to_csv
        read_parquet, read_csv = pd.read_parquet, pd.read_csv
        makedirs, replace = os.makedirs, os.replace
        abrir = builtins.open

        def _escritura(original):
            def envoltura(df, ruta, *args, **kwargs):
                self.escrituras.append(str(ruta))
                if escribir:
                    return original(df, ruta, *args, **kwargs)
                return None

            return envoltura

        def _lectura(original):
            def envoltura(ruta, *args, **kwargs):
                self.lecturas.append(str(ruta))
                return original(ruta, *args, **kwargs)

            return envoltura

        def _makedirs(ruta, *args, **kwargs):
            self.directorios.append(str(ruta))
            if escribir:
                makedirs(ruta, *args, **kwargs)

        def _replace(origen, destino):
            self.escrituras.append(str(destino))
            if escribir:
                replace(origen, destino)

        def _open(ruta, modo="r", *args, **kwargs):
            (self.escrituras if any(c in modo for c in "wax+") else self.lecturas).append(str(ruta))
            return abrir(ruta, modo, *args, **kwargs)

        monkeypatch.setattr(pd.DataFrame, "to_parquet", _escritura(to_parquet))
        monkeypatch.setattr(pd.DataFrame, "to_csv", _escritura(to_csv))
        monkeypatch.setattr(pd, "read_parquet", _lectura(read_parquet))
        monkeypatch.setattr(pd, "read_csv", _lectura(read_csv))
        monkeypatch.setattr(os, "makedirs", _makedirs)
        monkeypatch.setattr(os, "replace", _replace)
        monkeypatch.setattr(model_ready, "open", _open, raising=False)

    def todas(self) -> list[str]:
        return [*self.lecturas, *self.escrituras, *self.directorios]


def _dentro(ruta: str, raiz: Path) -> bool:
    resuelta = Path(ruta).resolve()
    return resuelta == raiz.resolve() or raiz.resolve() in resuelta.parents


@pytest.fixture
def sin_efectos(monkeypatch):
    """Evita conexiones y salidas por pantalla en los bloques."""
    for modulo in (extract, gps, qc, trip_end, model_ready):
        if hasattr(modulo, "display"):
            monkeypatch.setattr(modulo, "display", lambda obj: None)
    monkeypatch.setattr(trip_end, "conectar_bd", lambda database: None)
    monkeypatch.setattr(trip_end, "cerrar_conexion", lambda con: None)
    monkeypatch.setattr(gps, "conectar_bd", lambda database: None)
    monkeypatch.setattr(gps, "cerrar_conexion", lambda con: None)


# ---------------------------------------------------------------------------
# Valor por defecto: rutas y comportamiento historicos
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rutas_por_defecto_coinciden_con_las_constantes_historicas() -> None:
    rutas = cfg.rutas_etl()
    assert rutas is cfg.RUTAS_PREDETERMINADAS
    assert not rutas.alternativa
    pares = {
        "data_dir": cfg.DATA_DIR,
        "raw_dir": cfg.RAW_DIR,
        "interim_dir": cfg.INTERIM_DIR,
        "processed_dir": cfg.PROCESSED_DIR,
        "reports_dir": cfg.REPORTS_DIR,
        "despachos_csv": cfg.DESPACHOS_CSV,
        "batch_dir": cfg.BATCH_DIR,
        "qc_dir": cfg.QC_DIR,
        "gps_dir": cfg.GPS_DIR,
        "progreso_file": cfg.PROGRESO_FILE,
        "model_ready_dir": cfg.MODEL_READY_DIR,
        "qc_reports_dir": cfg.QC_REPORTS_DIR,
        "etl_reports_dir": cfg.ETL_REPORTS_DIR,
        "qc_path": cfg.QC_PATH,
        "end_path": cfg.END_PATH,
    }
    for campo, constante in pares.items():
        valor = getattr(rutas, campo)
        assert valor == constante, campo
        assert type(valor) is type(constante), campo
    # Valores literales historicos, independientes de la implementacion.
    raiz = cfg.PROJECT_ROOT
    assert str(raiz / "data" / "raw" / "despachos_raw_historico.csv") == cfg.DESPACHOS_CSV
    assert (
        os.path.join(str(raiz / "data" / "interim" / "qc"), "despachos_qc.parquet") == cfg.QC_PATH
    )
    assert (
        os.path.join(str(raiz / "data" / "interim" / "gps"), "despachos_end.parquet")
        == cfg.END_PATH
    )
    assert str(raiz / "data" / "processed" / "model_ready") == cfg.MODEL_READY_DIR
    assert str(raiz / "reports" / "tables" / "etl") == cfg.ETL_REPORTS_DIR
    assert cfg._directorios_salida() == [
        cfg.RAW_DIR,
        cfg.INTERIM_DIR,
        cfg.PROCESSED_DIR,
        cfg.REPORTS_DIR,
        cfg.BATCH_DIR,
        cfg.QC_DIR,
        cfg.GPS_DIR,
        cfg.MODEL_READY_DIR,
        cfg.QC_REPORTS_DIR,
        cfg.ETL_REPORTS_DIR,
    ]
    # Sin restricciones: verificar devuelve la ruta tal cual, incluso fuera de data/.
    assert rutas.verificar("C:/otro/lugar.csv") == "C:/otro/lugar.csv"


@pytest.mark.unit
def test_bloque3_por_defecto_lee_y_escribe_el_csv_historico(monkeypatch) -> None:
    llamadas: dict = {}
    monkeypatch.setattr(extract, "inicializar_entorno", lambda **kwargs: None)
    monkeypatch.setattr(
        extract, "cargar_csv_si_existe", lambda ruta: llamadas.setdefault("lee", ruta) and None
    )
    monkeypatch.setattr(extract, "conectar_bd", lambda database: object())
    monkeypatch.setattr(extract, "cerrar_conexion", lambda con: None)

    def _obtener(con, fecha_ini, fecha_fin, max_pk):
        llamadas["consulta"] = (fecha_ini, fecha_fin, max_pk)
        return _despachos_crudos(2)

    monkeypatch.setattr(extract, "obtener_despachos", _obtener)
    monkeypatch.setattr(
        extract, "guardar_csv", lambda df, ruta: llamadas.setdefault("escribe", ruta)
    )

    extract.run_block3()

    assert llamadas["lee"] == cfg.DESPACHOS_CSV
    assert llamadas["escribe"] == cfg.DESPACHOS_CSV
    hoy = pd.to_datetime("today").strftime("%Y-%m-%d")
    assert llamadas["consulta"] == ("2024-04-16", hoy, 0)


@pytest.mark.unit
def test_bloques_5_a_9_por_defecto_usan_las_rutas_historicas(monkeypatch, sin_efectos) -> None:
    registro = _RegistroES(monkeypatch, escribir=False)
    for modulo in (gps, qc, trip_end, model_ready):
        monkeypatch.setattr(modulo, "inicializar_entorno", lambda **kwargs: None)
    escrituras_csv: list[str] = []
    monkeypatch.setattr(gps, "guardar_csv", lambda df, ruta: escrituras_csv.append(ruta))

    df4 = run_block4(_despachos_crudos())
    gps.run_block5(df4)
    assert escrituras_csv == [cfg.DESPACHOS_CSV]

    qc.run_block6(df4)
    assert registro.escrituras == [
        cfg.QC_PATH,
        os.path.join(cfg.QC_DIR, "despachos_gps_ready.parquet"),
        os.path.join(cfg.QC_DIR, "despachos_hard_excluded.parquet"),
        os.path.join(cfg.QC_REPORTS_DIR, "qc_resumen.csv"),
        os.path.join(cfg.QC_REPORTS_DIR, "qc_top_vehiculos.csv"),
        os.path.join(cfg.QC_REPORTS_DIR, "qc_top_rutas.csv"),
    ]

    # Bloques 7 a 9: lecturas historicas servidas desde memoria.
    end = _salida_bloque7()
    qc_df = qc.validar_coherencia_operacional_avanzada(
        df4,
        col_pk="PK_INTERVALO_DESPACHO",
        col_placa="PLACA",
        col_ruta="FK_RUTA",
        col_estado="ESTADO_DESPACHO",
        col_hi="HORA_INICIAL_REAL",
        col_hf="HORA_FINAL_REAL",
        col_pasaj="PASAJEROS_REALES",
        col_dist="DISTANCIA",
    )[0]
    fuentes = {cfg.QC_PATH: qc_df, cfg.END_PATH: end}
    model_ready_path = os.path.join(cfg.MODEL_READY_DIR, "despachos_model_ready.parquet")

    def _leer(ruta, *args, **kwargs):
        registro.lecturas.append(str(ruta))
        return fuentes.get(str(ruta), end).copy()

    # El Bloque 7 no encuentra una salida previa; los Bloques 8 y 9 si.
    existentes: set[str] = set()
    monkeypatch.setattr(pd, "read_parquet", _leer)
    for modulo in (trip_end, model_ready):
        monkeypatch.setattr(modulo.os.path, "exists", lambda ruta: str(ruta) in existentes)

    class _Archivo:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def write(self, texto):
            return len(texto)

    def _open(ruta, modo="r", *args, **kwargs):
        registro.escrituras.append(str(ruta))
        return _Archivo()

    monkeypatch.setattr(model_ready, "open", _open, raising=False)
    registro.escrituras.clear()
    registro.lecturas.clear()

    trip_end.run_block7()
    existentes.update({cfg.END_PATH, model_ready_path})
    model_ready.run_block8()
    model_ready.run_block9()

    assert registro.lecturas == [cfg.QC_PATH, cfg.END_PATH, model_ready_path]
    esperadas_fijas = [
        cfg.END_PATH,
        model_ready_path,
        os.path.join(cfg.MODEL_READY_DIR, "despachos_model_ready.csv"),
    ]
    assert registro.escrituras[:3] == esperadas_fijas
    versionadas = registro.escrituras[3:]
    assert len(versionadas) == 5
    nombres = sorted(Path(r).name.split("_2")[0] for r in versionadas)
    assert nombres == [
        "despachos_model_ready.parquet",
        "despachos_model_ready_freeze",
        "despachos_model_ready_freeze",
        "model_ready_metadata",
        "model_ready_qc",
    ]
    assert all(
        Path(r).parent in {Path(cfg.MODEL_READY_DIR), Path(cfg.ETL_REPORTS_DIR)}
        for r in versionadas
    )


@pytest.mark.unit
def test_main_por_defecto_ejecuta_los_bloques_con_las_rutas_historicas(monkeypatch) -> None:
    recibidas: list = []
    monkeypatch.setattr(pipeline, "inicializar_entorno", lambda **kw: recibidas.append(kw["rutas"]))
    monkeypatch.setattr(
        pipeline, "run_block3", lambda fecha_fin, rutas: recibidas.append((fecha_fin, rutas))
    )
    monkeypatch.setattr(pipeline, "run_block4", lambda d: d)
    monkeypatch.setattr(pipeline, "run_block5", lambda d, rutas: recibidas.append(rutas))
    monkeypatch.setattr(pipeline, "run_block6", lambda d, rutas: recibidas.append(rutas))
    for bloque in ("run_block7", "run_block8", "run_block9"):
        monkeypatch.setattr(pipeline, bloque, lambda rutas: recibidas.append(rutas))
    monkeypatch.setattr(cfg, "DIRECTORIO_SALIDA", None)
    preparadas: list = []
    monkeypatch.setattr(cfg, "preparar_raiz_alternativa", lambda *a, **k: preparadas.append(a))

    pipeline.main([])

    assert recibidas[1] == (None, cfg.RUTAS_PREDETERMINADAS)
    assert all(r is cfg.RUTAS_PREDETERMINADAS for r in [recibidas[0], *recibidas[2:]])
    assert len(recibidas) == 7
    assert preparadas == []


# ---------------------------------------------------------------------------
# Directorio alternativo
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rutas_alternativas_reproducen_la_estructura_bajo_la_raiz(tmp_path) -> None:
    rutas = cfg.rutas_etl(tmp_path / "actualizacion")
    raiz = (tmp_path / "actualizacion").resolve()
    assert rutas.alternativa and rutas.raiz == raiz
    assert rutas.despachos_csv == str(raiz / "raw" / "despachos_raw_historico.csv")
    assert rutas.qc_path == os.path.join(str(raiz / "interim" / "qc"), "despachos_qc.parquet")
    assert rutas.end_path == os.path.join(str(raiz / "interim" / "gps"), "despachos_end.parquet")
    assert rutas.model_ready_dir == str(raiz / "processed" / "model_ready")
    assert rutas.etl_reports_dir == str(raiz / "reports" / "tables" / "etl")
    assert all(_dentro(str(d), raiz) for d in rutas.directorios_salida())
    assert all(_dentro(d, raiz) for d in rutas.destinos_fijos())


@pytest.mark.unit
@pytest.mark.parametrize("raiz", ["data", "."])
def test_rechaza_una_raiz_que_contenga_data(raiz) -> None:
    with pytest.raises(cfg.ErrorRutaETL, match="no puede ser data"):
        cfg.rutas_etl(raiz)


@pytest.mark.unit
def test_verificar_rechaza_rutas_fuera_de_la_raiz(tmp_path) -> None:
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    dentro = str(tmp_path / "raiz" / "raw" / "x.csv")
    assert rutas.verificar(dentro) == dentro
    for fuera in (
        cfg.DESPACHOS_CSV,
        str(tmp_path / "otra" / "x.csv"),
        str(tmp_path / "raiz" / ".." / "x"),
    ):
        with pytest.raises(cfg.ErrorRutaETL, match="fuera de la raiz"):
            rutas.verificar(fuera)


@pytest.mark.unit
def test_cadena_b4_a_b9_no_lee_ni_escribe_fuera_de_la_raiz(
    tmp_path, monkeypatch, sin_efectos
) -> None:
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    cfg.preparar_raiz_alternativa(rutas, {"fecha_ini": "2024-04-16", "fecha_fin": "2026-10-03"})
    registro = _RegistroES(monkeypatch, escribir=True)
    monkeypatch.setattr(gps, "guardar_csv", lambda df, ruta: registro.escrituras.append(ruta))

    df4 = run_block4(_despachos_crudos())
    gps.run_block5(df4, rutas=rutas)
    qc.run_block6(df4, rutas=rutas)
    trip_end.run_block7(rutas=rutas)
    df8 = model_ready.run_block8(rutas=rutas)
    model_ready.run_block9(rutas=rutas)

    assert len(df8) > 0
    assert registro.lecturas and registro.escrituras
    fuera = [r for r in registro.todas() if not _dentro(r, rutas.raiz)]
    assert fuera == []
    assert list(Path(rutas.model_ready_dir).glob("despachos_model_ready_freeze_*.parquet"))
    assert list(Path(rutas.etl_reports_dir).glob("model_ready_metadata_*.json"))


@pytest.mark.unit
def test_bloque3_alternativo_usa_solo_el_csv_de_la_raiz_y_la_fecha_fin(
    tmp_path, monkeypatch
) -> None:
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    llamadas: dict = {}
    monkeypatch.setattr(extract, "inicializar_entorno", lambda **kwargs: None)
    monkeypatch.setattr(
        extract, "cargar_csv_si_existe", lambda ruta: llamadas.setdefault("lee", ruta) and None
    )
    monkeypatch.setattr(extract, "conectar_bd", lambda database: object())
    monkeypatch.setattr(extract, "cerrar_conexion", lambda con: None)
    monkeypatch.setattr(
        extract,
        "obtener_despachos",
        lambda con, fi, ff, pk: (
            llamadas.setdefault("consulta", (fi, ff, pk)) and _despachos_crudos(2)
        ),
    )
    monkeypatch.setattr(
        extract, "guardar_csv", lambda df, ruta: llamadas.setdefault("escribe", ruta)
    )

    extract.run_block3(fecha_fin="2026-10-03", rutas=rutas)

    assert llamadas["lee"] == rutas.despachos_csv
    assert llamadas["escribe"] == rutas.despachos_csv
    assert llamadas["consulta"] == ("2024-04-16", "2026-10-03", 0)


@pytest.mark.unit
def test_se_detiene_si_un_destino_ya_existe(tmp_path) -> None:
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    destino = Path(rutas.qc_path)
    destino.parent.mkdir(parents=True)
    destino.write_bytes(b"previo")

    with pytest.raises(cfg.ErrorRutaETL, match="Ya existen archivos de destino"):
        cfg.preparar_raiz_alternativa(rutas, {"fecha_ini": "2024-04-16", "fecha_fin": None})

    assert destino.read_bytes() == b"previo"
    assert sorted(p.relative_to(rutas.raiz).as_posix() for p in rutas.raiz.rglob("*")) == [
        "interim",
        "interim/qc",
        "interim/qc/despachos_qc.parquet",
    ]


@pytest.mark.unit
def test_bloque9_no_sobrescribe_un_archivo_versionado(tmp_path, monkeypatch, sin_efectos) -> None:
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    cfg.preparar_raiz_alternativa(rutas, {"fecha_ini": "2024-04-16", "fecha_fin": None})
    _salida_bloque7().to_parquet(rutas.end_path, index=False)

    class _Fija:
        @staticmethod
        def now():
            return pd.Timestamp("2026-10-04 22:00:00").to_pydatetime()

    monkeypatch.setattr(model_ready, "datetime", _Fija)
    ocupado = Path(rutas.etl_reports_dir) / "model_ready_qc_20261004_220000.csv"
    ocupado.write_text("previo", encoding="utf-8")

    with pytest.raises(cfg.ErrorRutaETL, match="ya existe"):
        model_ready.run_block9(rutas=rutas)
    assert ocupado.read_text(encoding="utf-8") == "previo"


@pytest.mark.unit
def test_copia_etl_yaml_y_no_registra_credenciales(tmp_path, monkeypatch) -> None:
    secreto = "clave-de-prueba-que-no-debe-aparecer"
    monkeypatch.setenv("REGISTEL_DB_PASSWORD", secreto)
    monkeypatch.setenv("REGISTEL_DB_USER", "usuario-de-prueba-no-registrar")
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    parametros = {"fecha_ini": "2024-04-16", "fecha_fin": "2026-10-03"}

    cfg.preparar_raiz_alternativa(rutas, parametros)

    copia = rutas.raiz / "etl.yaml"
    assert copia.read_bytes() == cfg.ETL_YAML_PATH.read_bytes()
    marcador = json.loads((rutas.raiz / cfg.MARCADOR_EJECUCION).read_text(encoding="utf-8"))
    assert set(marcador) == {"inicio", "parametros", "configuracion_copiada"}
    assert marcador["parametros"] == parametros
    for archivo in rutas.raiz.rglob("*"):
        if archivo.is_file():
            texto = archivo.read_text(encoding="utf-8", errors="ignore")
            assert secreto not in texto
            assert "usuario-de-prueba-no-registrar" not in texto


@pytest.mark.unit
def test_reanudar_exige_marcador_y_mismos_parametros(tmp_path) -> None:
    rutas = cfg.rutas_etl(tmp_path / "raiz")
    parametros = {"fecha_ini": "2024-04-16", "fecha_fin": "2026-10-03"}
    with pytest.raises(cfg.ErrorRutaETL, match="requiere el marcador"):
        cfg.preparar_raiz_alternativa(rutas, parametros, reanudar=True)

    cfg.preparar_raiz_alternativa(rutas, parametros)
    Path(rutas.end_path).write_bytes(b"punto de control")
    with pytest.raises(cfg.ErrorRutaETL, match="Ya existen"):
        cfg.preparar_raiz_alternativa(rutas, parametros)
    with pytest.raises(cfg.ErrorRutaETL, match="no coinciden"):
        cfg.preparar_raiz_alternativa(
            rutas, {**parametros, "fecha_fin": "2026-10-04"}, reanudar=True
        )

    cfg.preparar_raiz_alternativa(rutas, parametros, reanudar=True)
    marcador = json.loads((rutas.raiz / cfg.MARCADOR_EJECUCION).read_text(encoding="utf-8"))
    assert len(marcador["reanudaciones"]) == 1
    assert Path(rutas.end_path).read_bytes() == b"punto de control"


# ---------------------------------------------------------------------------
# Linea de comandos y clave de configuracion
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_el_argumento_prevalece_sobre_la_clave_de_configuracion(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cfg, "DIRECTORIO_SALIDA", str(tmp_path / "desde_yaml"))
    desde_yaml = pipeline.resolver_rutas(pipeline.parse_args([]))
    assert desde_yaml.raiz == (tmp_path / "desde_yaml").resolve()

    desde_argumento = pipeline.resolver_rutas(
        pipeline.parse_args(["--directorio-salida", str(tmp_path / "desde_argumento")])
    )
    assert desde_argumento.raiz == (tmp_path / "desde_argumento").resolve()

    monkeypatch.setattr(cfg, "DIRECTORIO_SALIDA", None)
    assert pipeline.resolver_rutas(pipeline.parse_args([])) is cfg.RUTAS_PREDETERMINADAS
    with pytest.raises(cfg.ErrorRutaETL, match="solo aplica"):
        pipeline.resolver_rutas(pipeline.parse_args(["--reanudar"]))


@pytest.mark.unit
def test_parse_args_valida_la_fecha_fin() -> None:
    assert pipeline.parse_args(["--fecha-fin", "2026-10-03"]).fecha_fin == "2026-10-03"
    assert pipeline.parse_args([]).fecha_fin is None
    with pytest.raises(SystemExit):
        pipeline.parse_args(["--fecha-fin", "03/10/2026"])


@pytest.mark.unit
def test_main_alternativo_prepara_la_raiz_y_pasa_sus_rutas(tmp_path, monkeypatch) -> None:
    recibidas: list = []
    monkeypatch.setattr(
        pipeline, "run_block3", lambda fecha_fin, rutas: recibidas.append((fecha_fin, rutas))
    )
    monkeypatch.setattr(pipeline, "run_block4", lambda d: d)
    monkeypatch.setattr(pipeline, "run_block5", lambda d, rutas: recibidas.append(rutas))
    monkeypatch.setattr(pipeline, "run_block6", lambda d, rutas: recibidas.append(rutas))
    for bloque in ("run_block7", "run_block8", "run_block9"):
        monkeypatch.setattr(pipeline, bloque, lambda rutas: recibidas.append(rutas))

    raiz = tmp_path / "actualizacion"
    pipeline.main(["--directorio-salida", str(raiz), "--fecha-fin", "2026-10-03"])

    fecha_fin, rutas = recibidas[0]
    assert fecha_fin == "2026-10-03"
    assert rutas.raiz == raiz.resolve()
    assert all(r == rutas for r in recibidas[1:])
    assert (raiz / cfg.MARCADOR_EJECUCION).exists()
    assert (raiz / "etl.yaml").exists()
    assert date.fromisoformat(
        json.loads((raiz / cfg.MARCADOR_EJECUCION).read_text(encoding="utf-8"))["inicio"][:10]
    )
    shutil.rmtree(raiz)
