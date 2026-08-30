"""Carga y validacion de la configuracion de evaluacion comparativa."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from proyecto_grado.modeling.config import PROJECT_ROOT

RUTA_CONFIG_PREDETERMINADA = PROJECT_ROOT / "configs" / "modeling" / "evaluacion_comparativa.yaml"
METODOS_ESPERADOS = ("SARIMA", "Prophet", "XGBoost", "LSTM", "GRU", "CNN-LSTM")
REFERENCIAS_ESPERADAS = ("Referencia (26s)", "Referencia (52s)")
PATRON_VERSION = re.compile(r"^freeze_\d{8}_\d{6}$")
PATRON_PREDICCIONES = re.compile(
    r"^predicciones__(?P<metodo>[a-z0-9_]+)__(?P<version>freeze_\d{8}_\d{6})\.csv$"
)
PATRON_RESUMEN = re.compile(
    r"^resumen__(?P<metodo>[a-z0-9_]+)__(?P<version>freeze_\d{8}_\d{6})\.csv$"
)


class ErrorConfiguracionEvaluacion(ValueError):  # noqa: N818
    """Indica que la configuracion comparativa no satisface el contrato."""


@dataclass(frozen=True)
class MetodoEvaluacion:
    """Procedencia y ventana efectiva de un metodo obligatorio."""

    nombre: str
    identificador: str
    columna_prediccion: str
    artefacto_predicciones: Path
    artefacto_resumen: Path
    artefacto_original: Path
    semanas_entrenamiento: int
    semanas_parada_temprana: int | None


@dataclass(frozen=True)
class ReferenciaEvaluacion:
    """Serie de referencia ya almacenada y su profundidad historica."""

    nombre: str
    metodo_fuente: str
    columna_prediccion: str
    artefacto: Path
    artefacto_original: Path
    ventana_semanas: int


@dataclass(frozen=True)
class ConfiguracionEvaluacionComparativa:
    """Contrato inmutable del flujo comparativo canonico."""

    dataset_version: str
    escenario: str
    dataset_por_escenario: dict[str, Path]
    inicio: date
    fin: date
    extremos_inclusivos: bool
    paso_muestreo: int
    min_franjas: int
    rutas: tuple[int, ...]
    objetivo: str
    tipos_baja_frecuencia: tuple[str, ...]
    umbral_mape: float
    metodos: dict[str, MetodoEvaluacion]
    referencias: dict[str, ReferenciaEvaluacion]
    directorio_salida: Path
    registro_fechas_originales: Path
    jornadas_pre_consolidacion: Path
    metricas_pre_consolidacion: Path
    manifiesto: Path

    @property
    def ruta_dataset(self) -> Path:
        """Devuelve el dataset correspondiente al escenario seleccionado."""
        return self.dataset_por_escenario[self.escenario]

    def metodo(self, nombre: str) -> MetodoEvaluacion:
        """Obtiene un metodo obligatorio o falla con un mensaje explicito."""
        try:
            return self.metodos[nombre]
        except KeyError as exc:
            raise ErrorConfiguracionEvaluacion(
                f"El metodo obligatorio {nombre!r} no esta configurado."
            ) from exc

    def ruta_metricas(self, desagregacion: str) -> Path:
        """Construye el nombre canonico de una tabla de metricas."""
        if desagregacion not in {"global", "regimen", "tipo_dia"}:
            raise ErrorConfiguracionEvaluacion(f"Desagregacion no soportada: {desagregacion}.")
        return self.directorio_salida / (
            f"metricas__comparacion_modelos__{self.dataset_version}__{desagregacion}.csv"
        )


def _ruta_proyecto(valor: Any, campo: str) -> Path:
    ruta = Path(str(valor))
    if ruta.is_absolute():
        raise ErrorConfiguracionEvaluacion(
            f"{campo} debe ser una ruta relativa al proyecto: {ruta}."
        )
    return PROJECT_ROOT / ruta


def _entero_positivo(valor: Any, campo: str) -> int:
    try:
        resultado = int(valor)
    except (TypeError, ValueError) as exc:
        raise ErrorConfiguracionEvaluacion(f"{campo} debe ser un entero positivo.") from exc
    if resultado <= 0:
        raise ErrorConfiguracionEvaluacion(f"{campo} debe ser un entero positivo.")
    return resultado


def _fecha(valor: Any, campo: str) -> date:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as exc:
        raise ErrorConfiguracionEvaluacion(f"{campo} debe usar el formato AAAA-MM-DD.") from exc


def _validar_nombre_artefacto(
    ruta: Path,
    patron: re.Pattern[str],
    identificador: str,
    version: str,
) -> None:
    coincidencia = patron.fullmatch(ruta.name)
    if coincidencia is None:
        raise ErrorConfiguracionEvaluacion(
            f"El artefacto no cumple el patron canonico: {ruta.name}."
        )
    if coincidencia.group("metodo") != identificador:
        raise ErrorConfiguracionEvaluacion(
            f"El metodo del nombre {ruta.name} no coincide con {identificador}."
        )
    if coincidencia.group("version") != version:
        raise ErrorConfiguracionEvaluacion(
            f"La version del nombre {ruta.name} no coincide con {version}."
        )


def validar_nombre_predicciones(ruta: str | Path, identificador: str, dataset_version: str) -> None:
    """Valida patron, metodo y version de un artefacto de predicciones."""
    _validar_nombre_artefacto(Path(ruta), PATRON_PREDICCIONES, identificador, dataset_version)


def _cargar_metodos(raw: Any, dataset_version: str) -> dict[str, MetodoEvaluacion]:
    if not isinstance(raw, dict) or tuple(raw) != METODOS_ESPERADOS:
        raise ErrorConfiguracionEvaluacion(
            "metodos_obligatorios debe declarar, en orden, SARIMA, Prophet, "
            "XGBoost, LSTM, GRU y CNN-LSTM."
        )

    metodos: dict[str, MetodoEvaluacion] = {}
    identificadores: set[str] = set()
    for nombre, payload in raw.items():
        if not isinstance(payload, dict):
            raise ErrorConfiguracionEvaluacion(f"La entrada de {nombre} debe ser un mapa.")
        identificador = str(payload.get("identificador", ""))
        if not re.fullmatch(r"[a-z0-9_]+", identificador):
            raise ErrorConfiguracionEvaluacion(
                f"Identificador invalido para {nombre}: {identificador!r}."
            )
        if identificador in identificadores:
            raise ErrorConfiguracionEvaluacion(
                f"Identificador de metodo duplicado: {identificador}."
            )
        identificadores.add(identificador)

        predicciones = _ruta_proyecto(
            payload.get("artefacto_predicciones"),
            f"metodos_obligatorios.{nombre}.artefacto_predicciones",
        )
        resumen = _ruta_proyecto(
            payload.get("artefacto_resumen"),
            f"metodos_obligatorios.{nombre}.artefacto_resumen",
        )
        _validar_nombre_artefacto(predicciones, PATRON_PREDICCIONES, identificador, dataset_version)
        _validar_nombre_artefacto(resumen, PATRON_RESUMEN, identificador, dataset_version)

        parada_raw = payload.get("semanas_parada_temprana")
        parada = (
            None
            if parada_raw is None
            else _entero_positivo(
                parada_raw,
                f"metodos_obligatorios.{nombre}.semanas_parada_temprana",
            )
        )
        columna = str(payload.get("columna_prediccion", ""))
        if not columna:
            raise ErrorConfiguracionEvaluacion(f"Falta columna_prediccion para el metodo {nombre}.")
        metodos[nombre] = MetodoEvaluacion(
            nombre=nombre,
            identificador=identificador,
            columna_prediccion=columna,
            artefacto_predicciones=predicciones,
            artefacto_resumen=resumen,
            artefacto_original=_ruta_proyecto(
                payload.get("artefacto_original"),
                f"metodos_obligatorios.{nombre}.artefacto_original",
            ),
            semanas_entrenamiento=_entero_positivo(
                payload.get("semanas_entrenamiento"),
                f"metodos_obligatorios.{nombre}.semanas_entrenamiento",
            ),
            semanas_parada_temprana=parada,
        )
    return metodos


def _cargar_referencias(
    raw: Any,
    metodos: dict[str, MetodoEvaluacion],
    dataset_version: str,
) -> dict[str, ReferenciaEvaluacion]:
    if not isinstance(raw, dict) or tuple(raw) != REFERENCIAS_ESPERADAS:
        raise ErrorConfiguracionEvaluacion(
            "referencias debe declarar Referencia (26s) y Referencia (52s)."
        )
    por_identificador = {metodo.identificador: metodo for metodo in metodos.values()}
    referencias: dict[str, ReferenciaEvaluacion] = {}
    for nombre, payload in raw.items():
        if not isinstance(payload, dict):
            raise ErrorConfiguracionEvaluacion(f"La entrada de {nombre} debe ser un mapa.")
        metodo_fuente = str(payload.get("metodo_fuente", ""))
        if metodo_fuente not in por_identificador:
            raise ErrorConfiguracionEvaluacion(
                f"La fuente de {nombre} no es un metodo obligatorio: {metodo_fuente}."
            )
        artefacto = _ruta_proyecto(payload.get("artefacto"), f"referencias.{nombre}.artefacto")
        _validar_nombre_artefacto(artefacto, PATRON_PREDICCIONES, metodo_fuente, dataset_version)
        metodo = por_identificador[metodo_fuente]
        ventana = _entero_positivo(
            payload.get("ventana_semanas"), f"referencias.{nombre}.ventana_semanas"
        )
        if artefacto != metodo.artefacto_predicciones:
            raise ErrorConfiguracionEvaluacion(
                f"{nombre} no apunta al artefacto canonico de {metodo_fuente}."
            )
        if ventana != metodo.semanas_entrenamiento:
            raise ErrorConfiguracionEvaluacion(
                f"La ventana de {nombre} no coincide con la de {metodo_fuente}."
            )
        referencias[nombre] = ReferenciaEvaluacion(
            nombre=nombre,
            metodo_fuente=metodo_fuente,
            columna_prediccion=str(payload.get("columna_prediccion", "")),
            artefacto=artefacto,
            artefacto_original=_ruta_proyecto(
                payload.get("artefacto_original"),
                f"referencias.{nombre}.artefacto_original",
            ),
            ventana_semanas=ventana,
        )
        if not referencias[nombre].columna_prediccion:
            raise ErrorConfiguracionEvaluacion(f"Falta columna_prediccion para {nombre}.")
    return referencias


def cargar_configuracion_evaluacion(
    ruta: str | Path | None = None,
) -> ConfiguracionEvaluacionComparativa:
    """Carga el YAML comparativo y rechaza valores incompletos o incoherentes."""
    ruta_config = Path(ruta) if ruta is not None else RUTA_CONFIG_PREDETERMINADA
    if not ruta_config.is_absolute():
        ruta_config = PROJECT_ROOT / ruta_config
    if not ruta_config.is_file():
        raise FileNotFoundError(f"No existe la configuracion comparativa: {ruta_config}.")
    with ruta_config.open(encoding="utf-8") as archivo:
        raw = yaml.safe_load(archivo)
    if not isinstance(raw, dict):
        raise ErrorConfiguracionEvaluacion("La raiz de la configuracion debe ser un mapa.")

    dataset_version = str(raw.get("dataset_version", ""))
    if PATRON_VERSION.fullmatch(dataset_version) is None:
        raise ErrorConfiguracionEvaluacion(
            f"dataset_version no cumple el patron esperado: {dataset_version!r}."
        )

    dataset_raw = raw.get("dataset")
    if not isinstance(dataset_raw, dict):
        raise ErrorConfiguracionEvaluacion("Falta el bloque dataset.")
    escenario = str(dataset_raw.get("escenario_utilizado", ""))
    rutas_raw = dataset_raw.get("rutas_por_escenario")
    if not isinstance(rutas_raw, dict) or escenario not in rutas_raw:
        raise ErrorConfiguracionEvaluacion(
            "El escenario utilizado no tiene una ruta de dataset declarada."
        )
    dataset_por_escenario = {
        str(nombre): _ruta_proyecto(ruta_dataset, f"dataset.rutas_por_escenario.{nombre}")
        for nombre, ruta_dataset in rutas_raw.items()
    }

    evaluacion = raw.get("evaluacion")
    if not isinstance(evaluacion, dict):
        raise ErrorConfiguracionEvaluacion("Falta el bloque evaluacion.")
    periodo = evaluacion.get("periodo")
    if not isinstance(periodo, dict):
        raise ErrorConfiguracionEvaluacion("Falta evaluacion.periodo.")
    extremos_inclusivos = periodo.get("extremos_inclusivos")
    if extremos_inclusivos is not True:
        raise ErrorConfiguracionEvaluacion(
            "El periodo comparativo debe declarar ambos extremos inclusivos."
        )
    inicio = _fecha(periodo.get("inicio"), "evaluacion.periodo.inicio")
    fin = _fecha(periodo.get("fin"), "evaluacion.periodo.fin")
    if inicio > fin:
        raise ErrorConfiguracionEvaluacion("El inicio del periodo es posterior al fin.")

    metodos = _cargar_metodos(raw.get("metodos_obligatorios"), dataset_version)
    referencias = _cargar_referencias(raw.get("referencias"), metodos, dataset_version)
    salidas = raw.get("salidas")
    if not isinstance(salidas, dict):
        raise ErrorConfiguracionEvaluacion("Falta el bloque salidas.")

    rutas = tuple(int(valor) for valor in evaluacion.get("rutas", []))
    tipos = tuple(str(valor) for valor in evaluacion.get("tipos_baja_frecuencia", []))
    objetivo = str(evaluacion.get("objetivo", ""))
    if not rutas or len(set(rutas)) != len(rutas):
        raise ErrorConfiguracionEvaluacion("evaluacion.rutas debe contener rutas unicas.")
    if not tipos:
        raise ErrorConfiguracionEvaluacion("evaluacion.tipos_baja_frecuencia no puede estar vacio.")
    if not objetivo:
        raise ErrorConfiguracionEvaluacion("evaluacion.objetivo no puede estar vacio.")

    return ConfiguracionEvaluacionComparativa(
        dataset_version=dataset_version,
        escenario=escenario,
        dataset_por_escenario=dataset_por_escenario,
        inicio=inicio,
        fin=fin,
        extremos_inclusivos=True,
        paso_muestreo=_entero_positivo(evaluacion.get("paso_muestreo"), "evaluacion.paso_muestreo"),
        min_franjas=_entero_positivo(evaluacion.get("min_franjas"), "evaluacion.min_franjas"),
        rutas=rutas,
        objetivo=objetivo,
        tipos_baja_frecuencia=tipos,
        umbral_mape=float(evaluacion.get("umbral_mape")),
        metodos=metodos,
        referencias=referencias,
        directorio_salida=_ruta_proyecto(salidas.get("directorio"), "salidas.directorio"),
        registro_fechas_originales=_ruta_proyecto(
            salidas.get("registro_fechas_originales"),
            "salidas.registro_fechas_originales",
        ),
        jornadas_pre_consolidacion=_ruta_proyecto(
            salidas.get("jornadas_pre_consolidacion"),
            "salidas.jornadas_pre_consolidacion",
        ),
        metricas_pre_consolidacion=_ruta_proyecto(
            salidas.get("metricas_pre_consolidacion"),
            "salidas.metricas_pre_consolidacion",
        ),
        manifiesto=_ruta_proyecto(salidas.get("manifiesto"), "salidas.manifiesto"),
    )
