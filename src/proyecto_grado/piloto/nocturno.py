"""Orquestador nocturno de la prueba piloto.

Una sola corrida a las 00:30 (hora de Colombia) predice la jornada D+1 con la
jornada D completa y genera la recomendacion de despachos de las rutas 1 y 3.

Uso:
    python -m proyecto_grado.piloto.nocturno [--escribir-bd] [--subir-s3]
    python -m proyecto_grado.piloto.nocturno --fecha-objetivo 2026-10-01 --fuente local
    python -m proyecto_grado.piloto.nocturno --relleno 2026-10-04 2026-10-12

Codigos de salida: 0 = OK, 1 = ERROR, 2 = ya habia otra ejecucion en curso.

Requiere PILOTO_ENTORNO (EC2 o LOCAL). Con --fuente bd (por defecto) o
--escribir-bd no se conecta a la base entre las 04:00 y las 21:00 de Colombia,
salvo --forzar-horario. Solo corre desde un commit limpio (archivos versionados
sin cambios y sin archivos nuevos en src/, configs/ ni scripts/), salvo
--permitir-sucio; ambas excepciones quedan en el manifiesto y en el log.

Salidas en data/piloto/ (o --directorio-salidas):
    ejecuciones/<id>/       manifiesto.json, ejecucion.log, predicciones y recomendacion
    extracciones/<id>.parquet, almacen/, etl/<id>/, serie/<id>.parquet,
    historial/, planillas/, ESTADO_ULTIMA_EJECUCION.txt
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd

from proyecto_grado.modeling.config import (
    PROJECT_ROOT,
    load_scenario_definitions,
    load_target_config,
)
from proyecto_grado.piloto import config as cfg_mod
from proyecto_grado.piloto import correccion as corr
from proyecto_grado.piloto import extraccion as ext
from proyecto_grado.piloto import fechas, registro
from proyecto_grado.piloto import prediccion as pred_mod
from proyecto_grado.piloto import serie as serie_mod
from proyecto_grado.piloto.planilla import DatosPlanilla, escribir_planilla
from proyecto_grado.piloto.recomendacion import cargar_modulo, recomendar

logger = logging.getLogger("proyecto_grado.piloto.nocturno")

CODIGO_OK, CODIGO_ERROR, CODIGO_OCUPADO = 0, 1, 2
DIRECTORIOS_CODIGO = ("src/", "configs/", "scripts/")
BLOQUEO_VENCIDO_HORAS = 6
VERSION_PREDICCION = "definitiva"


class Estado(StrEnum):
    EN_CURSO = "EN_CURSO"
    OK = "OK"
    ADVERTENCIA = "ADVERTENCIA"  # fase 2
    CONTINGENCIA = "CONTINGENCIA"  # fase 2
    ERROR = "ERROR"


class ErrorEjecucion(RuntimeError):  # noqa: N818
    """La ejecucion no puede continuar (horario, commit, argumentos)."""


# --------------------------------------------------------------- dependencias


def _cargar_env() -> None:
    """Variables de .env sin reemplazar las ya definidas en el entorno."""
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)


def _git(args: list[str]) -> str:
    r = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True)
    return r.stdout


@dataclass
class Dependencias:
    """Puntos de inyeccion para pruebas: reloj, git, fuente, base y S3."""

    reloj: Callable[[], datetime] = fechas.ahora_bogota
    cargar_env: Callable[[], None] = _cargar_env
    git: Callable[[list[str]], str] = _git
    fuente: Callable[[cfg_mod.ConfigPiloto, str], ext.Fuente] | None = None
    escritor_bd: Callable[[], Any] | None = None
    cliente_s3: Callable[[], Any] | None = None
    cliente_sns: Callable[[], Any] | None = None


def fuente_predeterminada(cfg: cfg_mod.ConfigPiloto, nombre: str) -> ext.Fuente:
    if nombre == "local":
        return ext.FuenteLocal(cfg.entrada("semilla_crudo"))
    return ext.FuenteBD()


# --------------------------------------------------------------- bloqueo


class Ocupado(RuntimeError):  # noqa: N818
    pass


@contextmanager
def bloqueo(ruta: Path, ahora: datetime) -> Iterator[None]:
    """Archivo de bloqueo exclusivo; otra ejecucion activa lanza ``Ocupado``.

    Un bloqueo de mas de BLOQUEO_VENCIDO_HORAS horas se considera abandonado
    (proceso terminado sin limpiar) y se reemplaza, dejando constancia en el log.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps({"pid": os.getpid(), "inicio": ahora.isoformat()})
    for intento in range(2):
        try:
            fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            previo = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
            if intento == 0 and _bloqueo_vencido(previo, ahora):
                logger.warning("Bloqueo abandonado reemplazado: %s", previo)
                ruta.unlink(missing_ok=True)
                continue
            raise Ocupado(previo) from None
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenido)
        break
    try:
        yield
    finally:
        ruta.unlink(missing_ok=True)


def _bloqueo_vencido(contenido: str, ahora: datetime) -> bool:
    try:
        inicio = datetime.fromisoformat(json.loads(contenido)["inicio"])
    except (ValueError, KeyError, TypeError):
        return False
    return ahora - inicio > timedelta(hours=BLOQUEO_VENCIDO_HORAS)


# --------------------------------------------------------------- git


def estado_git(git: Callable[[list[str]], str]) -> dict:
    """Commit, salida completa de git status --porcelain y archivos que lo ensucian."""
    commit = git(["rev-parse", "HEAD"]).strip()
    porcelana = git(["status", "--porcelain", "--untracked-files=all"])
    return {
        "commit": commit,
        "status_porcelain": porcelana,
        "sucios": cambios_que_ensucian(porcelana),
    }


def cambios_que_ensucian(porcelana: str) -> list[str]:
    """Archivos versionados con cambios, o nuevos dentro de src/, configs/ o scripts/."""
    sucios = []
    for linea in porcelana.splitlines():
        if not linea.strip():
            continue
        codigo, ruta = linea[:2], linea[3:].strip().strip('"')
        if codigo == "??":
            if ruta.replace("\\", "/").startswith(DIRECTORIOS_CODIGO):
                sucios.append(linea)
        else:
            sucios.append(linea)
    return sucios


# --------------------------------------------------------------- manifiesto y pasos


@dataclass
class Ejecucion:
    id: str
    inicio: datetime
    carpeta: Path
    salidas: Path
    manifiesto: dict = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)
    estado: Estado = Estado.EN_CURSO

    @contextmanager
    def paso(self, nombre: str, reloj: Callable[[], datetime]) -> Iterator[None]:
        registro_paso = {"inicio": reloj().isoformat(timespec="seconds")}
        self.manifiesto.setdefault("pasos", {})[nombre] = registro_paso
        t0 = time.perf_counter()
        logger.info("Paso %s: inicio", nombre)
        try:
            yield
            registro_paso["estado"] = "OK"
        except BaseException:
            registro_paso["estado"] = "ERROR"
            raise
        finally:
            registro_paso["fin"] = reloj().isoformat(timespec="seconds")
            registro_paso["segundos"] = round(time.perf_counter() - t0, 2)
            logger.info(
                "Paso %s: %s (%.1f s)",
                nombre,
                registro_paso.get("estado"),
                registro_paso["segundos"],
            )

    def advertir(self, texto: str) -> None:
        logger.warning(texto)
        self.advertencias.append(texto)


def _sha_relativo(ruta: Path) -> dict:
    return {"ruta": _relativa(ruta), "sha256": cfg_mod.sha256_archivo(ruta)}


def _relativa(ruta: Path) -> str:
    try:
        return Path(ruta).resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return Path(ruta).as_posix()


def escribir_json(ruta: Path, datos: dict) -> None:
    texto = registro.ocultar(json.dumps(datos, ensure_ascii=False, indent=2, default=str))
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(texto, encoding="utf-8")
    os.replace(temporal, ruta)


def versiones() -> dict:
    import numpy
    import xgboost

    return {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": numpy.__version__,
        "xgboost": xgboost.__version__,
        "plataforma": platform.platform(),
    }


def evaluar_estado(e: Ejecucion) -> Estado:
    """Estado final de una ejecucion sin excepciones.

    Fase 1: siempre OK; las advertencias se informan sin cambiar el estado.
    Punto de extension de la fase 2 (ADVERTENCIA, CONTINGENCIA).
    """
    return Estado.OK


def escribir_estado_ultima(salidas: Path, e: Ejecucion) -> Path:
    """Resumen legible de la ultima ejecucion (se reemplaza en cada ejecucion)."""
    m = e.manifiesto
    obj = m.get("objetivo") or {}
    lineas = [
        f"Ejecucion: {e.id}",
        f"Estado: {e.estado}",
        f"Inicio: {m.get('inicio', '')}",
        f"Fin: {m.get('fin', '')}",
        f"Modo: {m.get('modo', '')}",
        f"Jornada objetivo: {obj.get('d_mas_1', '-')} (grupo {m.get('grupo', '-')})",
    ]
    if obj.get("anticipada"):
        lineas.append("Corrida anticipada: la jornada anterior estaba incompleta.")
    if obj.get("tardia"):
        lineas.append("Corrida tardia: empezo despues de las 04:00.")
    if m.get("salidas", {}).get("planilla"):
        lineas.append(f"Planilla: {m['salidas']['planilla']['ruta']}")
    lineas.append(f"Manifiesto: {_relativa(e.carpeta / 'manifiesto.json')}")
    lineas += [f"Advertencia: {a}" for a in e.advertencias] or ["Advertencias: ninguna"]
    if e.estado == Estado.ERROR:
        lineas += [
            f"Error: {m.get('error', {}).get('mensaje', '')}",
            "No hay recomendacion valida de esta ejecucion: operar como de costumbre.",
        ]
    ruta = salidas / "ESTADO_ULTIMA_EJECUCION.txt"
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(registro.ocultar("\n".join(lineas) + "\n"), encoding="utf-8")
    os.replace(temporal, ruta)
    return ruta


# --------------------------------------------------------------- argumentos


def _fecha(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Fecha invalida (AAAA-MM-DD): {valor}") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Orquestador nocturno de la prueba piloto.")
    p.add_argument(
        "--fecha-objetivo",
        type=_fecha,
        default=None,
        help="Jornada a predecir (ensayos con jornadas pasadas).",
    )
    p.add_argument(
        "--relleno",
        nargs=2,
        type=_fecha,
        metavar=("DESDE", "HASTA"),
        default=None,
        help="Predice las jornadas DESDE..HASTA para el historial (origen relleno).",
    )
    p.add_argument(
        "--fuente",
        choices=("bd", "local"),
        default="bd",
        help="bd: base real (por defecto); local: crudo de la semilla.",
    )
    p.add_argument(
        "--escribir-bd",
        action="store_true",
        help="Escribe la corrida en bd_montebello_recomendaciones.",
    )
    p.add_argument("--subir-s3", action="store_true", help="Sube la ejecucion a S3.")
    p.add_argument(
        "--permitir-sucio",
        action="store_true",
        help="Solo desarrollo: corre aunque el arbol de git tenga cambios.",
    )
    p.add_argument(
        "--forzar-horario",
        action="store_true",
        help="Permite consultar la base entre las 04:00 y las 21:00.",
    )
    p.add_argument(
        "--directorio-salidas",
        default=None,
        help="Raiz de salidas relativa al proyecto (por defecto data/piloto).",
    )
    p.add_argument("--config", default=None, help="Configuracion (por defecto piloto.yaml).")
    p.add_argument(
        "--sincronizar-estado",
        action="store_true",
        help="Solo descarga de S3 el estado mas reciente (preparar el plan B).",
    )
    p.add_argument(
        "--descargar-insumos",
        action="store_true",
        help="Solo descarga de s3://<bucket>/insumos/ las entradas congeladas y las verifica.",
    )
    args = p.parse_args(argv)
    if args.sincronizar_estado or args.descargar_insumos:
        otras = [
            args.sincronizar_estado and args.descargar_insumos,
            args.relleno,
            args.fecha_objetivo,
            args.escribir_bd,
            args.subir_s3,
        ]
        if any(otras):
            p.error(
                "--sincronizar-estado y --descargar-insumos son modos aparte: no se combinan "
                "entre si ni con --relleno, --fecha-objetivo, --escribir-bd o --subir-s3."
            )
    if args.relleno and args.fecha_objetivo:
        p.error("--relleno y --fecha-objetivo son excluyentes.")
    if args.relleno and args.escribir_bd:
        p.error("--relleno no escribe en la base.")
    if args.relleno and args.relleno[0] > args.relleno[1]:
        p.error("--relleno: DESDE debe ser anterior o igual a HASTA.")
    return args


# --------------------------------------------------------------- pasos de datos


@dataclass
class Datos:
    """Lo que producen extraccion y serie, compartido por la corrida y el relleno."""

    conjunto_apto: pd.DataFrame
    instantanea: Path
    version_dataset: str | None = None
    # Version del almacen escrita por esta ejecucion; el puntero se mueve al final,
    # solo si la ejecucion termina OK y la fuente es la base real.
    almacen_dir: Path | None = None
    almacen_rutas: dict = field(default_factory=dict)
    almacen_cubierto: date | None = None
    almacen_oficial: bool = False


def extraer_y_procesar(e: Ejecucion, cfg, objetivo, fuente, d: Dependencias) -> Datos:
    """Extraccion por ventana, bloques 4-8 y conjunto apto (secciones 1 y 2)."""
    m = e.manifiesto
    with e.paso("extraccion", d.reloj):
        alm_dir = e.salidas / "almacen"
        almacen = ext.leer_almacen(alm_dir)
        ventana = ext.calcular_ventana(
            objetivo,
            cfg.ventana_dias,
            cfg.ventana_dias_domingo,
            cfg.inicio_almacen,
            almacen.cubierto_hasta,
        )
        semilla_crudo = pd.read_csv(cfg.entrada("semilla_crudo"), usecols=[ext.PK, ext.FECHA])
        ancla = ext.calcular_pk_ancla([almacen.crudo, semilla_crudo], ventana.inicio, cfg.margen_pk)
        crudo = fuente.extraer(ventana, ancla)
        crudo, dedup = ext.deduplicar(crudo)
        instantanea = ext.guardar_instantanea(e.salidas / "extracciones", e.id, crudo)
        dif = ext.diferencias(almacen.crudo, crudo, ventana)
        m["extraccion"] = {
            "fuente": fuente.nombre,
            "ventana": ventana.como_dict(),
            "pk_ancla": ancla,
            "almacen_previo": almacen.id_ejecucion,
            "cubierto_hasta_previo": str(almacen.cubierto_hasta),
            "deduplicado": dedup,
            "diferencias": dif,
            "instantanea": _sha_relativo(instantanea),
        }
        if crudo.empty:
            raise ErrorEjecucion(f"La extraccion de {ventana.inicio} a {ventana.fin} esta vacia.")
        if dif["cambios_dia_mas_antiguo"]:
            e.advertir(
                f"Hubo cambios en el dia mas antiguo de la ventana ({ventana.inicio}): "
                "la ventana de reextraccion puede quedarse corta."
            )
    with e.paso("serie", d.reloj):
        gps = (
            serie_mod.GPSLocal.desde_archivo(cfg.entrada("semilla_fin_viaje"))
            if fuente.nombre == "local"
            else None
        )
        apto_ventana, info = serie_mod.procesar_ventana(crudo, e.salidas / "etl" / e.id, gps)
        crudo_alm = ext.reemplazar_ventana(almacen.crudo, crudo, ventana)
        apto_alm = ext.reemplazar_ventana(almacen.conjunto_apto, apto_ventana, ventana)
        cubierto = max(ventana.fin, almacen.cubierto_hasta or ventana.fin)
        rutas_alm = ext.guardar_almacen(
            alm_dir, e.id, crudo_alm, apto_alm, cubierto, mover_puntero=False
        )
        semilla_apto = pd.read_parquet(cfg.entrada("semilla_conjunto_apto"))
        conjunto = serie_mod.conjunto_apto_piloto(semilla_apto, apto_alm, cfg.inicio_almacen)
        m["procesamiento_ventana"] = info
        m["almacen"] = {
            "puntero_actualizado": False,
            "cubierto_hasta": str(cubierto),
            "archivos": {k: _sha_relativo(v) for k, v in rutas_alm.items()},
            "conjunto_apto_filas": len(conjunto),
        }
        if gps is not None and any(gps.consultas.values()):
            e.advertir(f"Modo local: consultas GPS sin resolver {gps.consultas}.")
    return Datos(
        conjunto_apto=conjunto,
        instantanea=instantanea,
        almacen_dir=alm_dir,
        almacen_rutas=rutas_alm,
        almacen_cubierto=cubierto,
        almacen_oficial=fuente.nombre == "bd",
    )


def consolidar_estado(e: Ejecucion, datos: Datos, filas_historial: pd.DataFrame | None) -> None:
    """Solo con la ejecucion en OK: agrega al historial y hace vigente el almacen."""
    if e.estado != Estado.OK:
        logger.warning("Estado %s: no se actualizan el historial ni el almacen.", e.estado)
        return
    if filas_historial is not None:
        e.manifiesto["historial"] = corr.agregar_al_historial(
            e.salidas / "historial", e.id, filas_historial
        )
    if datos.almacen_oficial:
        ext.mover_puntero_almacen(
            datos.almacen_dir, e.id, datos.almacen_rutas, datos.almacen_cubierto
        )
        e.manifiesto["almacen"]["puntero_actualizado"] = True


def serie_hasta(datos: Datos, dia: date, cfg, e: Ejecucion, guardar: bool) -> pd.DataFrame:
    """Serie con los despachos anteriores a las 04:00 de ``dia`` y las franjas de ``dia``."""
    corte = pred_mod.corte_de(dia)
    apto = datos.conjunto_apto
    apto = apto[pd.to_datetime(apto["HORA_INICIAL_REAL"]) < corte]
    objetivos = load_target_config(cfg.entrada("objetivos"))
    escenario = load_scenario_definitions(cfg.entrada("configuracion_escenarios"))["sin_oferta"]
    serie = serie_mod.construir_serie(apto, objetivos, escenario, dia, f"piloto_{e.id}", e.id)
    if guardar:
        ruta = serie_mod.guardar_serie(serie, e.salidas / "serie" / f"{e.id}.parquet")
        info = _sha_relativo(ruta)
        datos.version_dataset = info["sha256"]
        observadas = serie[serie["pasajeros_total"].notna()]
        e.manifiesto["serie"] = {
            **info,
            "filas": len(serie),
            "ultimo_dato": str(observadas["timestamp"].max()),
            "franjas_objetivo": int((serie["timestamp"] >= corte).sum()),
        }
    return serie


def historial_vigente(e: Ejecucion, cfg, p, escribir: bool) -> pd.DataFrame:
    """Historial de emisiones; si no existe, se arranca con el backtest."""
    directorio = e.salidas / "historial"
    hist = corr.leer_historial(directorio)
    if hist is None:
        filas = corr.filas_backtest(
            cfg.entrada("backtest_xgboost"),
            cfg.entrada("backtest_referencia_52s"),
            cfg.fin_backtest,
            p.tipos_raros,
        )
        if escribir:
            meta = corr.agregar_al_historial(directorio, "backtest_inicial", filas)
            e.manifiesto["historial_inicializado"] = meta
            hist = corr.leer_historial(directorio)
        else:
            hist = corr._normalizar(filas)
    return hist


def factores_de(e: Ejecucion, hist, serie, dia, cfg, p) -> dict[int, corr.Factor]:
    factores = {}
    for ruta in p.rutas:
        f = corr.calcular_factor(
            hist,
            serie,
            dia,
            ruta,
            cfg.ventana_correccion_dias,
            cfg.min_franjas_jornada,
            cfg.rango_factor,
        )
        for a in f.advertencias:
            e.advertir(a)
        factores[ruta] = f
    return factores


# --------------------------------------------------------------- corrida


def corrida(e: Ejecucion, args, cfg, d: Dependencias, ctx: dict) -> None:
    """Prediccion y recomendacion de una jornada (modo normal o --fecha-objetivo)."""
    m = e.manifiesto
    objetivo = ctx["objetivo"]
    dia = objetivo.d_mas_1
    oficial = args.fuente == "bd" and not objetivo.fijada  # escribe en el historial

    if args.escribir_bd:
        with e.paso("bd_abrir", d.reloj):
            ctx["escritor"] = (d.escritor_bd or _escritor_predeterminado)()
            ctx["escritor"].abrir_corrida(
                e.id, dia, e.inicio, ctx["entorno"], m["codigo"]["commit"]
            )
            m["bd"] = {"corrida_abierta": True}

    if args.subir_s3 and oficial:
        traer_estado(e, d)
    fuente = (d.fuente or fuente_predeterminada)(cfg, args.fuente)
    datos = extraer_y_procesar(e, cfg, objetivo, fuente, d)
    with e.paso("serie_objetivo", d.reloj):
        serie = serie_hasta(datos, dia, cfg, e, guardar=True)

    with e.paso("prediccion", d.reloj):
        p = pred_mod.cargar_parametros(
            cfg.entrada("configuracion_evaluacion"),
            cfg.entrada("hiperparametros_xgboost"),
            cfg.semanas_referencia_larga,
        )
        pred = pred_mod.predecir_jornada(serie, dia, p)
        m["prediccion"] = {
            **p.como_dict(),
            "franjas": pred.groupby("route").size().to_dict(),
            "ultimo_dato_entrenamiento": pred.groupby("route")["ultimo_dato"].first().to_dict(),
            "franjas_con_variables_nulas": int((pred["variables_nulas"] > 0).sum()),
        }

    with e.paso("correccion", d.reloj):
        hist = historial_vigente(e, cfg, p, escribir=oficial)
        factores = factores_de(e, hist, serie, dia, cfg, p)
        final = pred_mod.prediccion_final(pred, {r: f.valor for r, f in factores.items()})
        m["factor"] = {str(r): f.como_dict() for r, f in factores.items()}

    with e.paso("recomendacion", d.reloj):
        modulo = cargar_modulo(
            cfg.entrada("configuracion_recomendacion"),
            cfg.entrada("parametros_recomendacion"),
            cfg.entrada("manifiesto_recomendacion"),
        )
        rec, ajuste = recomendar(final, serie, pred_mod.corte_de(dia), modulo)
        m["recomendacion"] = {
            **modulo.como_dict(),
            "despachos_por_ruta": rec.groupby("route")["despachos_recomendados"].sum().to_dict(),
            "franjas_fuera_de_disponibilidad": int((~rec["en_disponibilidad"]).sum()),
            "ajuste_factibilidad": ajuste.to_dict("records"),
        }

    e.estado = evaluar_estado(e)
    with e.paso("salidas", d.reloj):
        salidas = {}
        for nombre, df in (("predicciones", final), ("recomendacion", rec), ("ajuste", ajuste)):
            ruta = e.carpeta / f"{nombre}.csv"
            df.to_csv(ruta, index=False)
            salidas[nombre] = ruta
        m["salidas"] = {k: _sha_relativo(v) for k, v in salidas.items()}
        ctx.update(rec=rec, factores=factores, datos=datos)

    # Orden de cierre (la planilla nunca contradice el estado de la corrida):
    # 1) S3 de la carpeta y la instantanea, para que ruta_s3 exista al cerrar;
    # 2) cierre en la base; 3) planilla con el estado final; 4) historial y
    # almacen solo si OK; 5) planilla, manifiesto y log a S3 al final de la ejecucion.
    if args.subir_s3:
        with e.paso("s3", d.reloj):
            # Un fallo de S3 no invalida la recomendacion: se avisa y se sigue.
            try:
                subir_s3(e, ctx, d)
            except Exception as exc:
                m["s3"] = {"ruta": None, "error": registro.ocultar(str(exc))}
                e.advertir(f"No se pudo subir la ejecucion a S3: {exc}")

    error_bd = None
    if args.escribir_bd:
        with e.paso("bd_cerrar", d.reloj):
            from proyecto_grado.piloto.salida_bd import CierreCorrida, filas_recomendaciones

            filas = filas_recomendaciones(rec, e.id, str(ctx["grupo"]))
            try:
                ctx["escritor"].cerrar_corrida(
                    e.id,
                    CierreCorrida(
                        fin=d.reloj(),
                        estado=str(e.estado),
                        advertencias=e.advertencias,
                        version_dataset=datos.version_dataset,
                        factores={r: f.valor for r, f in factores.items()},
                        filas=filas,
                        ruta_s3=m.get("s3", {}).get("ruta"),
                    ),
                )
                m["bd"] = {"corrida_abierta": True, "cerrada": True, "filas": len(filas)}
            except Exception as exc:
                # La corrida queda en ERROR en la base; la planilla se emite con ese estado.
                error_bd = exc
                e.estado = Estado.ERROR
                m["bd"] = {"corrida_abierta": True, "cerrada": False, "filas": 0}

    with e.paso("planilla", d.reloj):
        avisos = list(e.advertencias)
        if error_bd is not None:
            avisos.append(f"Error al escribir en la base: {registro.ocultar(str(error_bd))}")
        cfg_rec = modulo.config
        datos_planilla = DatosPlanilla(
            fecha=dia.isoformat(),
            estado=str(e.estado),
            grupo=str(ctx["grupo"]),
            id_ejecucion=e.id,
            tipo_dia=", ".join(sorted(set(final["tipo_dia"]))),
            regimen=", ".join(sorted(set(final["regimen"]))),
            factores={r: f.valor for r, f in factores.items()},
            ultimo_dato=m["serie"]["ultimo_dato"],
            anticipada=objetivo.anticipada,
            tardia=objetivo.tardia,
            advertencias=tuple(avisos),
        )
        planilla = escribir_planilla(
            e.salidas / "planillas",
            datos_planilla,
            rec,
            cfg_rec.bloques,
            cfg_rec.usar_tope_carga,
            cfg_rec.servicio_minimo,
        )
        ctx["planilla"] = planilla
        m["salidas"]["planilla"] = _sha_relativo(planilla)

    filas_hist = corr.filas_emitidas(final, e.id, "piloto", e.inicio) if oficial else None
    consolidar_estado(e, datos, filas_hist)
    if args.subir_s3 and oficial:
        publicar_estado(e, d, ctx)
    if error_bd is not None:
        raise error_bd


def relleno(e: Ejecucion, args, cfg, d: Dependencias, ctx: dict) -> None:
    """Predice DESDE..HASTA, cada jornada con datos anteriores a sus 04:00 (seccion 4)."""
    desde, hasta = args.relleno
    m = e.manifiesto
    if desde <= cfg.fin_backtest:
        raise ErrorEjecucion(
            f"--relleno debe empezar despues del backtest ({cfg.fin_backtest}): {desde}."
        )
    tope = ctx["objetivo_reloj"].d_mas_1
    if hasta > tope:
        raise ErrorEjecucion(f"--relleno: HASTA ({hasta}) es posterior a la jornada {tope}.")
    oficial = args.fuente == "bd"
    objetivo = fechas.objetivo_fijado(hasta)
    if args.subir_s3 and oficial:
        traer_estado(e, d)
    fuente = (d.fuente or fuente_predeterminada)(cfg, args.fuente)
    datos = extraer_y_procesar(e, cfg, objetivo, fuente, d)
    p = pred_mod.cargar_parametros(
        cfg.entrada("configuracion_evaluacion"),
        cfg.entrada("hiperparametros_xgboost"),
        cfg.semanas_referencia_larga,
    )
    hist = historial_vigente(e, cfg, p, escribir=oficial)
    nuevas, resumen = [], {}
    dia = desde
    while dia <= hasta:
        with e.paso(f"relleno_{dia}", d.reloj):
            serie = serie_hasta(datos, dia, cfg, e, guardar=False)
            pred = pred_mod.predecir_jornada(serie, dia, p)
            factores = factores_de(e, hist, serie, dia, cfg, p)
            final = pred_mod.prediccion_final(pred, {r: f.valor for r, f in factores.items()})
            filas = corr._normalizar(corr.filas_emitidas(final, e.id, "relleno", e.inicio))
            hist = pd.concat([hist, filas], ignore_index=True)  # las siguientes jornadas lo usan
            nuevas.append(filas)
            resumen[dia.isoformat()] = {
                "franjas": len(final),
                "factores": {str(r): f.valor for r, f in factores.items()},
            }
        dia += timedelta(days=1)
    todas = pd.concat(nuevas, ignore_index=True)
    ruta = e.carpeta / "relleno.csv"
    todas.to_csv(ruta, index=False)
    m["relleno"] = {
        "desde": str(desde),
        "hasta": str(hasta),
        "jornadas": resumen,
        "archivo": _sha_relativo(ruta),
        "escrito_en_historial": oficial,
    }
    e.estado = evaluar_estado(e)
    ctx["datos"] = datos
    consolidar_estado(e, datos, todas if oficial else None)
    if args.subir_s3:
        with e.paso("s3", d.reloj):
            try:
                subir_s3(e, ctx, d)
            except Exception as exc:
                m["s3"] = {"ruta": None, "error": registro.ocultar(str(exc))}
                e.advertir(f"No se pudo subir la ejecucion a S3: {exc}")
        if oficial:
            publicar_estado(e, d, ctx)


def subir_s3(e: Ejecucion, ctx: dict, d: Dependencias, solo_cierre: bool = False) -> None:
    from proyecto_grado.piloto import salida_s3

    destino = salida_s3.destino_desde_entorno()
    cliente = (d.cliente_s3 or salida_s3.cliente_s3)()
    if solo_cierre:
        # Al final: planilla (ya con su estado definitivo), manifiesto final y log.
        archivos = []
        if ctx.get("planilla") is not None:
            archivos.append((ctx["planilla"], ("planillas", ctx["planilla"].name)))
        archivos += [
            (e.carpeta / n, ("ejecuciones", e.id, n))
            for n in ("manifiesto.json", "ejecucion.log")
            if (e.carpeta / n).exists()
        ]
    else:
        escribir_json(e.carpeta / "manifiesto.json", e.manifiesto)  # version previa
        archivos = salida_s3.archivos_a_subir(e.carpeta, None, ctx["datos"].instantanea, e.id)
    uris = salida_s3.subir(archivos, destino, cliente)
    if not solo_cierre:
        e.manifiesto["s3"] = {"ruta": destino.uri("ejecuciones", e.id) + "/", "archivos": uris}


def _s3(d: Dependencias):
    from proyecto_grado.piloto import salida_s3

    return salida_s3.destino_desde_entorno(), (d.cliente_s3 or salida_s3.cliente_s3)()


def traer_estado(e: Ejecucion, d: Dependencias) -> None:
    """Al iniciar una corrida real con --subir-s3: estado remoto si es mas nuevo."""
    from proyecto_grado.piloto import estado_s3

    with e.paso("estado_descarga", d.reloj):
        try:
            destino, cliente = _s3(d)
            r = estado_s3.descargar_estado(e.salidas, destino, cliente)
        except Exception as exc:
            e.manifiesto.setdefault("estado_s3", {})["descarga"] = {"error": str(exc)}
            e.advertir(f"No se pudo consultar el estado en S3; se usa el local: {exc}")
            return
        e.manifiesto.setdefault("estado_s3", {})["descarga"] = r
        if r["accion"] == "local_mas_nuevo":
            e.advertir(
                f"El estado local ({r['local']}) es mas nuevo que el de S3 ({r['remoto']}): "
                "se usa el local y se publicara al terminar."
            )


def publicar_estado(e: Ejecucion, d: Dependencias, ctx: dict) -> None:
    """Al terminar en OK una corrida real con --subir-s3: publica el estado."""
    from proyecto_grado.piloto import estado_s3

    if e.estado != Estado.OK:
        return
    with e.paso("estado_publicacion", d.reloj):
        try:
            destino, cliente = _s3(d)
            r = estado_s3.publicar_estado(
                e.salidas,
                e.id,
                destino,
                cliente,
                {
                    "commit": e.manifiesto["codigo"]["commit"],
                    "entorno": ctx.get("entorno"),
                    "modo": e.manifiesto.get("modo"),
                    "creado": d.reloj().isoformat(timespec="seconds"),
                },
            )
            e.manifiesto.setdefault("estado_s3", {})["publicacion"] = r
        except Exception as exc:
            e.manifiesto.setdefault("estado_s3", {})["publicacion"] = {"error": str(exc)}
            e.advertir(f"No se pudo publicar el estado en S3 (queda solo local): {exc}")


def utilidad(e: Ejecucion, args, cfg, d: Dependencias) -> None:
    """--sincronizar-estado o --descargar-insumos: solo S3, sin base de datos."""
    from proyecto_grado.piloto import estado_s3

    destino, cliente = _s3(d)
    if args.sincronizar_estado:
        with e.paso("sincronizar_estado", d.reloj):
            e.manifiesto["estado_s3"] = {
                "descarga": estado_s3.descargar_estado(e.salidas, destino, cliente)
            }
    else:
        with e.paso("descargar_insumos", d.reloj):
            e.manifiesto["insumos"] = estado_s3.descargar_insumos(cfg, destino.bucket, cliente)
            e.manifiesto["entradas"] = cfg_mod.verificar_entradas(cfg, fuente_local=False)
    e.estado = Estado.OK


def _escritor_predeterminado():
    from proyecto_grado.piloto.salida_bd import EscritorBD

    return EscritorBD()


# --------------------------------------------------------------- main


def ejecutar(args: argparse.Namespace, d: Dependencias) -> int:
    d.cargar_env()
    ruta_config = PROJECT_ROOT / args.config if args.config else cfg_mod.RUTA_CONFIG_PREDETERMINADA
    cfg = cfg_mod.cargar_configuracion(ruta_config)
    registro.registrar_variables_sensibles(cfg.variables_sensibles)
    salidas = (
        PROJECT_ROOT / args.directorio_salidas
        if args.directorio_salidas
        else cfg.directorio_salidas
    )
    salidas.mkdir(parents=True, exist_ok=True)
    inicio = d.reloj()
    id_ejecucion = fechas.id_ejecucion(inicio)

    try:
        with bloqueo(salidas / "nocturno.lock", inicio):
            return _ejecutar_con_bloqueo(args, cfg, d, salidas, inicio, id_ejecucion, ruta_config)
    except Ocupado as previo:
        texto = (
            f"{inicio.isoformat(timespec='seconds')} ejecucion {id_ejecucion} no iniciada: "
            f"ya hay otra en curso ({previo})."
        )
        logging.getLogger(__name__).warning(texto)
        with (salidas / "ejecuciones_rechazadas.log").open("a", encoding="utf-8") as f:
            f.write(registro.ocultar(texto) + "\n")
        print(texto, file=sys.stderr)
        return CODIGO_OCUPADO


def _ejecutar_con_bloqueo(args, cfg, d, salidas, inicio, id_ejecucion, ruta_config) -> int:
    carpeta = salidas / "ejecuciones" / id_ejecucion
    carpeta.mkdir(parents=True, exist_ok=False)
    manejadores = registro.configurar_registro(carpeta / "ejecucion.log")
    e = Ejecucion(id=id_ejecucion, inicio=inicio, carpeta=carpeta, salidas=salidas)
    m = e.manifiesto
    m.update(
        {
            "id_ejecucion": id_ejecucion,
            "inicio": inicio.isoformat(timespec="seconds"),
            "zona_horaria": str(fechas.ZONA),
            "modo": modo_de(args),
            "version": VERSION_PREDICCION,
            "candidato": {"nombre": cfg.candidato, "nota": cfg.nota_candidato},
            "opciones": {
                k: (v if not isinstance(v, list | tuple) else [str(x) for x in v])
                for k, v in vars(args).items()
            },
            "estado": str(e.estado),
        }
    )
    ctx: dict = {}
    codigo = CODIGO_ERROR
    try:
        if args.sincronizar_estado or args.descargar_insumos:
            # Modos de solo S3: sin base de datos, sin prediccion y sin exigir commit limpio.
            with e.paso("preparacion", d.reloj):
                m["codigo"] = {**estado_git(d.git), **versiones()}
                ctx["entorno"] = str(cfg_mod.entorno())
                m["entorno"] = ctx["entorno"]
            utilidad(e, args, cfg, d)
            codigo = CODIGO_OK
            return codigo
        with e.paso("preparacion", d.reloj):
            m["codigo"] = {
                **estado_git(d.git),
                **versiones(),
                "permitir_sucio": bool(args.permitir_sucio),
            }
            ctx["entorno"] = str(cfg_mod.entorno())
            m["entorno"] = ctx["entorno"]
            if m["codigo"]["sucios"]:
                if not args.permitir_sucio:
                    raise ErrorEjecucion(
                        "El arbol de git tiene cambios; la piloto solo corre desde un commit "
                        f"limpio: {m['codigo']['sucios']}"
                    )
                e.advertir(
                    f"Ejecucion con --permitir-sucio: {len(m['codigo']['sucios'])} "
                    "cambios sin commit (solo desarrollo)."
                )
            usa_bd = args.fuente == "bd" or args.escribir_bd
            permitido = fechas.horario_bd_permitido(inicio, cfg.sin_bd_desde, cfg.sin_bd_hasta)
            m["horario"] = {
                "usa_bd": usa_bd,
                "horario_permitido": permitido,
                "forzar_horario": bool(args.forzar_horario),
            }
            if usa_bd and not permitido:
                if not args.forzar_horario:
                    raise ErrorEjecucion(
                        f"Son las {fechas.a_bogota(inicio):%H:%M} en Colombia: no se consulta la "
                        f"base entre las {cfg.sin_bd_desde:%H:%M} y las {cfg.sin_bd_hasta:%H:%M} "
                        "(use --forzar-horario para una excepcion autorizada)."
                    )
                e.advertir("Conexion a la base fuera de horario por --forzar-horario.")
            ctx["objetivo_reloj"] = fechas.jornada_objetivo(
                inicio, cfg.inicio_jornada, cfg.corte_objetivo
            )
            objetivo = (
                fechas.objetivo_fijado(args.fecha_objetivo)
                if args.fecha_objetivo
                else ctx["objetivo_reloj"]
            )
            if args.relleno:
                objetivo = fechas.objetivo_fijado(args.relleno[1])
            ctx["objetivo"] = objetivo
            m["objetivo"] = objetivo.como_dict()
            if objetivo.anticipada:
                e.advertir(
                    "Corrida anticipada: la jornada anterior aun no termina; sus datos "
                    "estan incompletos."
                )
            if objetivo.tardia:
                e.advertir("Corrida tardia: empezo despues del inicio del servicio (04:00).")
            ctx["grupo"] = cfg_mod.grupo_de(objetivo.d_mas_1, cfg.ruta_asignacion_grupos)
            m["grupo"] = str(ctx["grupo"])
            m["entradas"] = {
                "configuracion_piloto": _sha_relativo(ruta_config),
                "asignacion_grupos": _sha_relativo(cfg.ruta_asignacion_grupos),
                **cfg_mod.verificar_entradas(cfg, fuente_local=args.fuente == "local"),
            }
        if args.relleno:
            relleno(e, args, cfg, d, ctx)
        else:
            corrida(e, args, cfg, d, ctx)
        codigo = CODIGO_OK
    except Exception as exc:
        e.estado = Estado.ERROR
        mensaje = registro.ocultar(f"{type(exc).__name__}: {exc}")
        m["error"] = {"mensaje": mensaje, "traza": registro.ocultar(traceback.format_exc())}
        logger.error("Ejecucion en ERROR: %s", mensaje, exc_info=True)
        escritor = ctx.get("escritor")
        if escritor is not None:
            m.setdefault("bd", {})["marcada_error"] = escritor.marcar_error(
                e.id, d.reloj(), mensaje
            )
        codigo = CODIGO_ERROR
    finally:
        fin = d.reloj()
        m.update(
            {
                "estado": str(e.estado),
                "advertencias": e.advertencias,
                "fin": fin.isoformat(timespec="seconds"),
                "segundos": round((fin - inicio).total_seconds(), 1),
            }
        )
        escribir_json(carpeta / "manifiesto.json", m)
        escribir_estado_ultima(salidas, e)
        logger.info("Estado final: %s (codigo %d)", e.estado, codigo)
        if args.subir_s3 and m.get("s3", {}).get("ruta"):
            try:
                subir_s3(e, ctx, d, solo_cierre=True)
            except Exception as exc:  # el manifiesto local ya esta completo
                logger.error("No se pudo subir el manifiesto final a S3: %s", exc)
        if e.estado == Estado.OK and m["modo"] in MODOS_CON_AVISO:
            avisar_ok(m, d)
        if ctx.get("escritor") is not None:
            ctx["escritor"].cerrar()
        registro.cerrar_registro(manejadores)
    return codigo


MODOS_CON_AVISO = ("nocturno", "relleno", "ensayo")


def avisar_ok(m: dict, d: Dependencias) -> None:
    """Aviso corto por SNS si PILOTO_AVISAR_OK=1; un fallo solo se registra."""
    from proyecto_grado.piloto import avisos

    if not avisos.avisar_ok_activado():
        return
    try:
        asunto, cuerpo = avisos.mensaje_ok(m)
        cliente = d.cliente_sns() if d.cliente_sns else None
        avisos.publicar(asunto, cuerpo, cliente=cliente)
        logger.info("Aviso de exito enviado por SNS.")
    except Exception as exc:
        logger.error("No se pudo enviar el aviso de exito: %s", exc)


def modo_de(args: argparse.Namespace) -> str:
    if args.sincronizar_estado:
        return "sincronizar_estado"
    if args.descargar_insumos:
        return "descargar_insumos"
    if args.relleno:
        return "relleno"
    return "ensayo" if args.fecha_objetivo else "nocturno"


def main(argv: list[str] | None = None, dependencias: Dependencias | None = None) -> int:
    return ejecutar(parse_args(argv), dependencias or Dependencias())


if __name__ == "__main__":
    sys.exit(main())
