# Integración de un módulo de recomendación de despacho: convenciones del proyecto

Relevamiento de solo lectura, 2026-10-04. No se modificó ni ejecutó ningún script, freeze ni configuración: solo se leyeron archivos y se consultó el estado de git. Las columnas del Parquet apto para modelado provienen de una lectura hecha en esta misma sesión, antes del relevamiento; el resto, de la cabecera de cada CSV.

**Puntos que condicionan el diseño (detallados abajo):**

1. Ya existe un subpaquete vacío `src/proyecto_grado/dispatch/`, el lugar natural para el módulo.
2. Las tres piezas que pide el módulo (pasajeros por despacho individual, cuartiles por bloque y asignación a los seis bloques) **solo existen en scripts de `analisis/`**, no en `src/`. Hay además **tres definiciones de bloque horario distintas** en el código, y una clasificación de carga ya existente con otro criterio (`analytics/demand_supply.py`).
3. El paquete `modeling/hparam_search/` (del que dependen los scripts 25 y 31–35, y la carga de los hiperparámetros seleccionados) y `configs/modeling/busqueda_hiperparametros.yaml` **no están versionados en git**.
4. Los artefactos del freeze `freeze_20260922_203820` no están declarados en ningún YAML: `evaluacion_comparativa.yaml` sigue apuntando a los de `freeze_20260823_203700`.

---

## 1. Paquete

```
src/proyecto_grado/
├── __init__.py
├── analytics/        Análisis posteriores al ETL: KPI, diagnósticos, productividad, oferta-demanda, flota
│   ├── demand_supply.py          DemandSupplyAnalyzer: factor de carga por franja (capacidad fija)
│   ├── etl_diagnostics.py        comparación de etapas del ETL
│   ├── fleet_availability.py     FleetAvailabilityAnalyzer: vehículos en ruta/en patio por instante
│   ├── headway.py                HeadwayAnalyzer: intervalo entre despachos e irregularidad
│   ├── kpis.py                   KPI operativos (usa PASAJEROS_REALES)
│   ├── plots.py, report.py       figuras y reporte posteriores al ETL
│   └── vehicle_productivity.py   ProductivityAnalyzer: pasajeros/despacho semanal por ruta
├── dashboard/app.py  Tablero Streamlit (punto de entrada `dashboard` en pyproject)
├── data/             vacío
├── dispatch/         vacío (solo __init__.py sin contenido)
├── eda/temporal_analysis.py      EDA temporal de las series
├── etl/              Pipeline ETL: extracción MySQL, QC, GPS, fin de recorrido, model-ready
│   ├── config.py                 rutas del ETL y constantes de etl.yaml
│   ├── db.py, extract.py, gps.py, qc.py, transforms.py, trip_end.py, utils.py
│   ├── model_ready.py            construcción del conjunto apto para modelado
│   └── pipeline.py               orquestador (bloques 1–9)
├── evaluation/       vacío
├── features/         Serie temporal agregada desde model-ready
│   ├── time_series_builder.py    TimeSeriesBuilder: agregación por franja, festivos, tipo_dia
│   ├── operational_hours.py      horario operativo real por tipo_dia × ruta
│   └── validators.py             validaciones de la serie
├── modeling/         Modelado reproducible y evaluación comparativa
│   ├── config.py                 PROJECT_ROOT, ModelingPaths, cargadores de YAML de modelado
│   ├── dataset.py, features.py   dataset de modelado sin fuga, rezagos y codificaciones cíclicas
│   ├── evaluation_config.py      contrato de la evaluación comparativa (YAML → dataclass)
│   ├── evaluation_aggregation.py métricas sobre predicciones persistidas (calcular_metricas)
│   ├── experimentos.py           seleccionar_features, particiones, entrenamiento compartido
│   ├── baselines.py, backtesting.py, splits.py, evaluate.py, error_analysis.py, bias_analysis.py
│   ├── xgboost_models.py, xgboost_report.py
│   └── hparam_search/            búsqueda de hiperparámetros y reevaluación del freeze (SIN VERSIONAR)
│       ├── fits.py               ajustar_predecir_<metodo> (XGBoost, SARIMA, Prophet, redes)
│       ├── runner.py             walk-forward; _preparar_ruta, _dias_candidatos
│       ├── reevaluacion.py       genera freeze_20260922_203820; cargar_configuraciones_seleccionadas
│       ├── search.py, search_config.py, spaces.py, metrics.py, persist.py
│       └── consolidacion_freeze_nuevo.py
├── models/{baselines,dl,ml}/  vacíos
└── utils/pruebas.py  borrador: lee un Parquet e imprime al importarse; no importar
```

### Funciones reutilizables para el módulo

| Necesidad | Qué existe | Dónde | Observación |
|---|---|---|---|
| Pasajeros por despacho **por franja** | `ensure_modeling_target_columns` crea `pasajeros_por_despacho_real = pasajeros_total / despachos_count_real` (NaN si no hay despachos) | [modeling/features.py:49](src/proyecto_grado/modeling/features.py#L49) | Sobre la serie de 30 min, no por despacho individual. La columna ya está en el dataset de modelado. |
| Pasajeros por despacho **semanal** | `ProductivityAnalyzer` (`productividad_bruta`, ajustada por tendencia) | [analytics/vehicle_productivity.py:30](src/proyecto_grado/analytics/vehicle_productivity.py#L30) | Agregado semana × ruta. |
| Pasajeros por despacho **por despacho** y sus cuartiles | Solo en `analisis/36_pasajeros_por_despacho.py` (`distribucion`, `bootstrap`, `clasificar_franjas`) | [analisis/36_pasajeros_por_despacho.py](analisis/36_pasajeros_por_despacho.py) | No hay equivalente en `src/`. |
| Clasificación de carga por franja | `DemandSupplyAnalyzer`: factor de carga = pasajeros / (despachos × 80); `SOBRECARGA` > 0,85, `SUBCARGA` < 0,40, `OPTIMO` | [analytics/demand_supply.py:31](src/proyecto_grado/analytics/demand_supply.py#L31) | **Criterio distinto** del de cuartiles del script 36 (capacidad supuesta, «debe validarse con Montebello»). Conviene decidir cuál usa el módulo y nombrarlos distinto. |
| Asignación a los seis bloques horarios | Solo en `analisis/32_…` y `analisis/36_…` (`BLOQUES`, `bloque_de`), duplicada | [analisis/36_pasajeros_por_despacho.py:106](analisis/36_pasajeros_por_despacho.py#L106) | Ver «bloques» abajo. |
| Franjas horarias del builder | `TimeSeriesBuilder._franja_horaria` con `franjas_horarias` de `configs/features.yaml` | [features/time_series_builder.py:98](src/proyecto_grado/features/time_series_builder.py#L98) | **Otra definición**: MADRUGADA 0–5, MANANA 6–11, MEDIODIA 12–13, TARDE 14–18, NOCHE 19–23. |
| Picos de flota | `PICO_MANANA = (5, 9)`, `PICO_TARDE = (14, 16)`, `CIERRE = (16.5, 17.5)` | [analytics/fleet_availability.py:30](src/proyecto_grado/analytics/fleet_availability.py#L30) | **Tercera definición**. |
| Tipo de día y festivos | `TimeSeriesBuilder._get_colombia_holidays` y `_enriquecer` (regla FESTIVO_PUENTE = lunes festivo) | [features/time_series_builder.py:92](src/proyecto_grado/features/time_series_builder.py#L92), [:184](src/proyecto_grado/features/time_series_builder.py#L184) | Métodos privados de la clase; el script 36 replica la regla en `tipo_dia_de`. |
| Régimen (ordinario / raro) | `tipos_baja_frecuencia` de `evaluacion_comparativa.yaml` (`FESTIVO`, `FESTIVO_PUENTE`) | [modeling/evaluation_config.py:71](src/proyecto_grado/modeling/evaluation_config.py#L71) | La función `_regimen` está en [analisis/25:55](analisis/25_referencia_combinada_regimen.py#L55); la agregación la recalcula en línea. |
| Jornada operativa | `dia_op = (timestamp − 4 h).date`, `hora = timestamp.strftime("%H:%M")` | [modeling/hparam_search/runner.py:38](src/proyecto_grado/modeling/hparam_search/runner.py#L38) (`_preparar_ruta`) | Privada y sin versionar; la misma regla se repite en los scripts. |
| Métricas | `calcular_metricas(real, pred, umbral_mape)` → n, demanda_media, mae, rmse, wape, sesgo, mape_parcial, n_mape | [modeling/evaluation_aggregation.py:221](src/proyecto_grado/modeling/evaluation_aggregation.py#L221) | Sin MedAE. |
| Referencia histórica | `_media_historica`: media de train por (tipo_dia, hora), con la media global como respaldo | [analisis/25:59](analisis/25_referencia_combinada_regimen.py#L59) | Misma regla que el `pred_media` de los productores. |
| Ajuste diario de XGBoost | `ajustar_predecir_xgboost(fit_df, stop_df, test_df, features, target, params)`; `seleccionar_features(d)` | [hparam_search/fits.py:90](src/proyecto_grado/modeling/hparam_search/fits.py#L90), [experimentos.py:97](src/proyecto_grado/modeling/experimentos.py#L97) | `fits.py` sin versionar. |
| Hiperparámetros seleccionados | `cargar_configuraciones_seleccionadas(directorio)` lee `seleccion__<metodo>.json` | [hparam_search/reevaluacion.py:106](src/proyecto_grado/modeling/hparam_search/reevaluacion.py#L106) | Directorio: `analisis/salidas/busqueda_hiperparametros/`. |

**Bloques horarios del diagnóstico** (scripts 32 y 36, por hora entera de inicio): madrugada [4, 5), pico mañana [5, 7), mañana [7, 10), valle [10, 14), pico tarde [14, 16), cierre [16, 24). Si el módulo los usa, conviene trasladarlos a `src/` (o a un YAML) como única definición.

---

## 2. Configuración

**Archivos** (YAML plano, mapas anidados, comentarios en español, rutas siempre relativas a la raíz del proyecto):

| Archivo | Contenido | Cargador |
|---|---|---|
| `configs/etl.yaml` | rutas operativas, parámetros de GPS, fin de recorrido, QC | constantes de módulo en [etl/config.py](src/proyecto_grado/etl/config.py) (`{**defaults, **yaml}`) |
| `configs/features.yaml` | granularidades, `franjas_horarias`, `imputacion_gaps`, `columna_pasajeros: PASAJEROS_REALES`, horario operativo | `_load_features_yaml` en `TimeSeriesBuilder` |
| `configs/modeling/targets.yaml` | `dataset_version`, `source_path` (model-ready), objetivos | `load_target_config` ([modeling/config.py:161](src/proyecto_grado/modeling/config.py#L161)) |
| `configs/modeling/backtesting.yaml`, `models.yaml` | backtesting y modelos de la fase inicial | `load_backtesting_config`, `load_model_names` |
| `configs/modeling/evaluacion_comparativa.yaml` | contrato canónico: dataset, período 2026-04-02 a 2026-06-10, rutas, objetivo, `tipos_baja_frecuencia`, métodos y referencias con sus artefactos, salidas | **`cargar_configuracion_evaluacion`** |
| `configs/modeling/busqueda_hiperparametros.yaml` (sin versionar) | período de validación 2025-12-25 a 2026-04-01, presupuesto de la búsqueda, directorio de salidas | `cargar_configuracion_busqueda` ([hparam_search/search_config.py:56](src/proyecto_grado/modeling/hparam_search/search_config.py#L56)), que reutiliza el contrato anterior |

**Cargador de la evaluación comparativa** — [modeling/evaluation_config.py:272](src/proyecto_grado/modeling/evaluation_config.py#L272):

- `cargar_configuracion_evaluacion(ruta=None)`. Sin argumento usa `RUTA_CONFIG_PREDETERMINADA`; una ruta relativa se resuelve contra `PROJECT_ROOT`. Lee con `yaml.safe_load` y valida cada campo.
- Ante un valor faltante o incoherente lanza `ErrorConfiguracionEvaluacion` (subclase de `ValueError`). Las rutas absolutas dentro del YAML se rechazan (`_ruta_proyecto`).
- Devuelve el dataclass inmutable `ConfiguracionEvaluacionComparativa`. Campos: `dataset_version`, `inicio`/`fin` (`date`), `paso_muestreo`, `min_franjas`, `rutas` (tupla), `objetivo`, `tipos_baja_frecuencia`, `umbral_mape`, `metodos`, `referencias`, `directorio_salida`, entre otros.
- Accesos: `ruta_dataset` (propiedad) y `metodo(nombre)`, que devuelve `MetodoEvaluacion` con `semanas_entrenamiento` y `semanas_parada_temprana`.

**Ejemplo de lectura** ([scripts/run_xgboost_comparative_evaluation.py](scripts/run_xgboost_comparative_evaluation.py), líneas 23–36):

```python
from proyecto_grado.modeling.evaluation_config import cargar_configuracion_evaluacion

CONFIG = cargar_configuracion_evaluacion()
METODO = CONFIG.metodo("XGBoost")
PARQUET = CONFIG.ruta_dataset
INICIO_TEST = pd.Timestamp(CONFIG.inicio)
FIN_TEST = pd.Timestamp(CONFIG.fin)
SEMANAS_ENTRENAMIENTO = METODO.semanas_entrenamiento
MIN_FRANJAS = CONFIG.min_franjas
```

Para un módulo nuevo, el patrón establecido es: un YAML propio en `configs/` con rutas relativas, y un cargador `cargar_configuracion_<x>()` que valide y devuelva un `@dataclass(frozen=True)`, con una excepción propia. Puede reutilizar `cargar_configuracion_evaluacion`, como hace `search_config.py`.

---

## 3. Rutas

Hay un mecanismo centralizado, aunque duplicado:

- **`PROJECT_ROOT`** se define como `Path(__file__).resolve().parents[3]` en dos lugares: [modeling/config.py:15](src/proyecto_grado/modeling/config.py#L15) y [etl/config.py:13](src/proyecto_grado/etl/config.py#L13). Los módulos de modelado y los scripts de `analisis/` lo importan de `proyecto_grado.modeling.config`; algunos, de `proyecto_grado.etl.config`.
- **`ModelingPaths`** (dataclass, [modeling/config.py:29](src/proyecto_grado/modeling/config.py#L29)): `source_path` (model-ready), `dataset_path`, `time_series_dir`, `tables_dir` (`reports/tables/modeling`), `figures_dir` (`reports/figures/modeling`), `metadata_dir` (`models/metadata`). `ensure_modeling_dirs()` los crea. `DEFAULT_SOURCE_PATH` apunta a `data/processed/model_ready/despachos_model_ready_freeze_20260823_203700.parquet`.
- **ETL**: constantes `DATA_DIR`, `PROCESSED_DIR`, `MODEL_READY_DIR`, `REPORTS_DIR`… en `etl/config.py`. Los directorios solo se crean al llamar a `inicializar_entorno()`, nunca al importar.
- **Evaluación comparativa**: todas las rutas de artefactos están en `evaluacion_comparativa.yaml` y se exponen ya resueltas en el dataclass (`config.ruta_dataset`, `config.directorio_salida`, `config.metodo(...).artefacto_predicciones`).
- **Scripts de `analisis/`**: construyen `SALIDA = PROJECT_ROOT / "analisis" / "salidas"` y nombran los archivos como `<tipo>__<sufijo>[__<freeze>].csv`, con un `manifiesto__<sufijo>.json` (entradas, parámetros, verificaciones, salidas). Las figuras van a `reports/figures/<tema>/`, en PNG a 300 dpi y PDF.
- **Git ignora** `data/processed/*` y `reports/figures/*`. Los artefactos de `analisis/salidas/` sí pueden versionarse (hay archivos modificados ahí).

---

## 4. Scripts de entrada (`scripts/`)

Conviven tres estilos:

1. **Con `argparse`** ([scripts/build_modeling_dataset.py](scripts/build_modeling_dataset.py)):
   - Docstring de módulo con sección `Usage:`.
   - Inserta `src/` en `sys.path` antes de importar (`# noqa: E402`).
   - Usa `parse_args()` con valores por defecto relativos a la raíz, que `_resolve_project_path` resuelve contra `PROJECT_ROOT`.
   - Configura el registro con `logging.basicConfig` y una función `main()`.

   Los scripts de `scripts/hparam_search/` usan `argparse.ArgumentParser(description=__doc__)`.
2. **Sin argumentos, con `main()`** ([scripts/aggregate_comparative_metrics.py](scripts/aggregate_comparative_metrics.py)): docstring con `Uso:`, importaciones directas desde `proyecto_grado` y `main()`, que carga la configuración, llama a una función de `src/` e imprime.
3. **Sin argumentos ni `main()`** (los seis `run_*_comparative_evaluation.py`): la configuración se lee como constantes de módulo y el cálculo corre en el nivel superior. Están excluidos de ruff para no alterar artefactos verificados; no es un patrón a imitar.

**Importación desde `src`:** el paquete está instalado en modo editable en `.venv` (`_editable_impl_proyecto_grado.pth`), así que `from proyecto_grado.<subpaquete>.<modulo> import …` funciona sin tocar `sys.path`. El ajuste de `sys.path` que hacen algunos scripts es redundante con esa instalación.

**Fechas y períodos:**
- Se leen del YAML como `date` (`config.inicio`, `config.fin`; validación con `cargar_configuracion_busqueda().inicio_validacion` y `fin_validacion`), con extremos inclusivos, y se convierten a `pd.Timestamp`.
- La jornada se define como `inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)` y `fin_dia = inicio_dia + 1 día`. La ventana de entrenamiento es `inicio_dia − semanas` y la de parada temprana, las últimas `semanas_parada_temprana`.
- Los scripts de `analisis/` declaran los períodos como constantes (`PERIODOS`, `VALIDACION_INICIO`).

---

## 5. Pruebas

- **Marco:** pytest ≥ 8 (pytest-cov opcional). Configuración en `pyproject.toml`: `testpaths = ["tests"]`, `addopts = "-ra --strict-markers --basetemp=.pytest_tmp"`, marcadores `unit`, `integration` y `slow`. Con `--strict-markers`, todo marcador debe estar declarado.
- **Organización:**
  - `tests/unit/test_<modulo>.py`: 17 archivos, unas 148 funciones `test_`.
  - `tests/integration/test_etl_pipeline.py`.
  - No hay `conftest.py`; los fixtures se definen en cada archivo.
  - Los datos son `DataFrame` sintéticos pequeños. Algunas pruebas leen YAML reales con rutas relativas a la raíz, así que hay que ejecutarlas desde la raíz.
  - **Ningún test cubre `hparam_search/`.**
- **Ejemplo** ([tests/unit/test_evaluation_config.py](tests/unit/test_evaluation_config.py)):

```python
@pytest.mark.unit
def test_rechaza_metodo_obligatorio_faltante(tmp_path: Path) -> None:
    ruta_origen = Path("configs/modeling/evaluacion_comparativa.yaml")
    raw = yaml.safe_load(ruta_origen.read_text(encoding="utf-8"))
    raw["metodos_obligatorios"].pop("GRU")
    ruta = tmp_path / "evaluacion_incompleta.yaml"
    ruta.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ErrorConfiguracionEvaluacion, match="metodos_obligatorios"):
        cargar_configuracion_evaluacion(ruta)
```

  El estilo con fixture de datos sintéticos está en [tests/unit/test_analytics.py](tests/unit/test_analytics.py) (`@pytest.fixture def analytics_datasets()`).
- **Comandos:**
  - `make test` ejecuta `python -m pytest tests -p no:cacheprovider` con el Python de `.venv`.
  - `make test-cov` añade cobertura sobre `src/proyecto_grado`.
  - Solo unitarias: `python -m pytest tests -m unit`.

---

## 6. Artefactos de entrada

Claves comunes: **ruta** = `route` (int 1 o 3), **jornada** = `dia_op` (texto `YYYY-MM-DD`; jornada operativa que empieza a las 04:00), **franja** = `hora` (texto `HH:MM`, inicio de la franja de 30 min), **tipo de día** = `tipo_dia` (`LABORAL`, `SABADO`, `DOMINGO`, `FESTIVO`, `FESTIVO_PUENTE`). El régimen se deriva: raro si `tipo_dia` ∈ {FESTIVO, FESTIVO_PUENTE}.

| Artefacto | Ruta | Filas | Columnas | Ruta / jornada / franja / tipo de día |
|---|---|---|---|---|
| Predicciones de XGBoost del freeze | `analisis/salidas/predicciones__xgboost__freeze_20260922_203820.csv` | 3.117 (137 jornadas; **filtrar con las jornadas comunes**) | `route, dia_op, tipo_dia, hora, real, pred_xgboost, pred_media` | `route` / `dia_op` / `hora` / `tipo_dia`. `pred_media` = **referencia de 26 semanas**. |
| Referencia de 52 semanas | `analisis/salidas/predicciones__gru__freeze_20260922_203820.csv`, columna **`pred_media`** (así lo declara `evaluacion_comparativa.yaml` → `referencias.Referencia (52s)`) | 3.038 (las 134 jornadas comunes) | `route, dia_op, tipo_dia, hora, real, pred_gru, pred_media` | `route` / `dia_op` / `hora` / `tipo_dia`. **No confundir** `pred_media` (52 s) con `pred_gru`. |
| Alternativa ya unida (evaluación) | `analisis/salidas/observaciones__referencia_combinada_regimen__freeze_20260922_203820.csv` (script 25) | 3.038 | `route, dia_op, tipo_dia, regimen, hora, real, pred_combinada, pred_xgboost, pred_ref26, pred_ref52` | Incluye `regimen`; `pred_ref52` coincide con el `pred_media` del artefacto de GRU. |
| Alternativa ya unida (validación) | `analisis/salidas/observaciones__referencia_combinada_regimen__validacion.csv` (script 25) | 4.637 (192 jornadas) | mismas columnas | Única fuente de las referencias en validación. |
| Jornadas comunes | `analisis/salidas/jornadas_comunes__freeze_20260922_203820.csv` | 134 (66 de la ruta 1 y 68 de la ruta 3) | `route, dia_op` | Pares (ruta, jornada). |
| Script 36: distribución | `analisis/salidas/distribucion__pasajeros_por_despacho.csv` | 76 | `periodo, corte, route, regimen, bloque, n_despachos, n_jornadas, media, q1, q1_ic_inf, q1_ic_sup, mediana, mediana_ic_inf, mediana_ic_sup, q3, q3_ic_inf, q3_ic_sup, p90, p90_ic_inf, p90_ic_sup` | `route`; sin jornada ni franja; `bloque` (texto, p. ej. `pico manana (05:00-06:59)`); `regimen`; `corte` ∈ {ruta, regimen, bloque, regimen_x_bloque}, con `todos` como comodín. Los umbrales del clasificador son las filas `periodo == "validacion"`, `corte == "bloque"`. |
| Script 36: franjas | `analisis/salidas/franjas__pasajeros_por_despacho.csv` | 7.797 | `periodo, route, dia_op, tipo_dia, regimen, franja, bloque, pasajeros, despachos, pasajeros_por_despacho, q1_val, q3_val, clase` | `route` / `dia_op` / **`franja`** (marca de tiempo completa `YYYY-MM-DD HH:MM:SS`, no `HH:MM`) / `tipo_dia`. |
| Script 36: clasificación | `analisis/salidas/clasificacion_franjas__pasajeros_por_despacho.csv` | 28 | `periodo, route, bloque, n_franjas, despachos_por_franja_mediana, n_sobrecargada, pct_sobrecargada, n_normal, pct_normal, n_subutilizada, pct_subutilizada` | `route`, `bloque` (incluye `todos`). |
| Script 36: comparación de períodos | `analisis/salidas/comparacion_periodos__pasajeros_por_despacho.csv` | 38 | `corte, route, regimen, bloque, n_despachos_val, n_despachos_eval, n_jornadas_val, n_jornadas_eval`, y por cada cuantil `{q1, mediana, q3, p90}`: `_val, _eval, _dif, _dif_pct, _dif_ic_inf, _dif_ic_sup, _ic_excluye_0, _apreciable`; `cuantiles_apreciables` | `route`, `regimen`, `bloque`. |
| Script 36: variación entre bloques | `analisis/salidas/variacion_bloques__pasajeros_por_despacho.csv` | 16 | `periodo, route, cuantil, valor_ruta, minimo, bloque_minimo, maximo, bloque_maximo, rango, rango_pct_ruta, apreciable` | `route`. |
| Script 36: capacidad | `analisis/salidas/capacidad_flota__pasajeros_por_despacho.csv` | 3 | `route, jornadas, max_despachos_jornada, jornada_max_despachos, tipo_dia_jornada_max, mediana_despachos_jornada_laboral, vehiculos_activos_periodo, max_vehiculos_jornada, mediana_vehiculos_jornada_laboral, vehiculos_en_jornada_max_despachos` | `route` ∈ {1, 3, `ambas`}: columna mixta, **leer como texto**. |
| Script 36: otros | `resumen__pasajeros_por_despacho.md`, `manifiesto__pasajeros_por_despacho.json` | — | — | — |
| Conjunto apto para modelado | `data/processed/model_ready/despachos_model_ready_freeze_20260823_203700.parquet` (también en `.csv`, con las mismas columnas) | 109.559 despachos (2024-04-16 a 2026-06-10), todos con `MODEL_READY_OK` | `PK_INTERVALO_DESPACHO, PLACA, FK_RUTA, FECHA_INICIAL, HORA_INICIAL_REAL, HORA_FIN_FINAL, DURACION_MIN_FINAL, PASAJEROS, PASAJEROS_REALES, ALARMAS, DISTANCIA, RECORRIDO_COMPLETO, FIN_TIPO, HORA_FIN_FUENTE, HORA_INICIO_H, HORA_FIN_H, DIA_SEMANA, MES, DIA, MODEL_READY_OK` | Ruta = **`FK_RUTA`**; jornada = `(HORA_INICIAL_REAL − 4 h).date` (no viene precalculada); franja = `HORA_INICIAL_REAL.floor("30min")`; **no hay `tipo_dia`**: se deriva con los festivos de Colombia (`DIA_SEMANA` es float, 0 = lunes). Pasajeros: **`PASAJEROS_REALES`** (no `PASAJEROS`, que es el conteo crudo). Vehículo: `PLACA`. |

---

## 7. Estilo

- **Idioma de los identificadores: mixto.**
  - En inglés: los módulos más antiguos (`modeling/config.py`, `dataset.py`, `features.py`, `baselines.py`, `backtesting.py`, `splits.py`, `xgboost_*.py`, `analytics/kpis.py`, `etl_diagnostics.py`, `dashboard/`).
  - En español sin tildes: los recientes y todo el flujo comparativo (`evaluation_config.py`, `evaluation_aggregation.py`, `experimentos.py`, `hparam_search/`, `etl/`, `features/`), por ejemplo `cargar_configuracion_evaluacion`, `calcular_metricas` o `ErrorConfiguracionEvaluacion`. Algunos nombres de archivo siguen en inglés aunque el contenido esté en español.
  - Para un módulo de despacho en `dispatch/`, lo coherente con el flujo vigente es el español sin tildes.
- **Anotaciones de tipo:**
  - 33 de 47 módulos usan `from __future__ import annotations`.
  - Las funciones públicas de `src/` van anotadas, con estilo moderno (`str | Path | None`, `tuple[int, ...]`, `dict[str, X]`).
  - Las configuraciones son `@dataclass(frozen=True)`.
  - Las excepciones propias heredan de `ValueError` o `RuntimeError` y llevan `# noqa: N818`.
  - Los scripts de `analisis/` casi no anotan.
- **Docstrings:**
  - Triple comilla. Una línea de resumen y, si hace falta, párrafos explicativos del porqué.
  - Los módulos llevan docstring de módulo; los scripts, la sección `Uso:`/`Usage:` con el comando.
  - Cinco módulos usan el formato numpy (`Parameters`/`Returns` con subrayado): `features/*`, `eda/temporal_analysis.py`, `analytics/fleet_availability.py`. El resto usa prosa libre.
- **Registro:** `logger = logging.getLogger(__name__)` en `src/` (17 usos); los scripts de análisis usan `print`.
- **Herramientas** (`pyproject.toml`):
  - **Ruff**: `line-length = 100`, `target-version = "py311"`, reglas `E, F, W, I, N, UP, B, C4, SIM, RUF`, ignora `RUF001–003` y `E501`, formato con comillas dobles. Excluye `analisis/`, `notebooks`, `data`, `reports`, `backups`, `revision_modelado` y los seis `run_*_comparative_evaluation.py`.
  - **Mypy**: `python_version = "3.11"`, `strict_optional`, `warn_unused_ignores`, `warn_return_any`, `ignore_missing_imports`; excluye `tests` y `notebooks`.
  - **Pre-commit** (`.pre-commit-config.yaml`): `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-merge-conflict`, `debug-statements`, `ruff --fix` y `ruff-format` (v0.11.9).
  - **Makefile**: `make lint` (`ruff check src tests`), `make format`, `make typecheck` (`mypy src`), `make test`.

---

## 8. Git

- **Rama actual:** `consolidacion-evaluacion` (la principal es `master`).
- **Último commit:** `e504b29` (2026-08-30), «Corrige constantes desfasadas en los reportes de caracterizacion».
- **En el índice (preparado):** `scripts/build_xgboost_figures.py`, que tiene además cambios sin preparar.
- **Modificados sin preparar (11):** cinco `analisis/salidas/cuadro_*.csv`, `scripts/diagnostico_reduccion_flota.py`, `src/proyecto_grado/analytics/{etl_diagnostics,kpis,report}.py`, `src/proyecto_grado/eda/temporal_analysis.py`, `tests/unit/test_analytics.py`.
- **Sin seguimiento:**
  - **`src/proyecto_grado/modeling/hparam_search/`** (10 módulos) y **`configs/modeling/busqueda_hiperparametros.yaml`**.
  - `scripts/hparam_search/` (3 scripts) y `scripts/build_rotacion.py`.
  - `analisis/24_…` a `analisis/37_…` (14 scripts) y 94 archivos en `analisis/salidas/`, entre ellos los artefactos del freeze `freeze_20260922_203820`, la selección de hiperparámetros y los del script 36.
  - `comprobaciones.py`, diez `verificacion_*.md` y otros informes en la raíz, `reports/figures_v1_sin_corregir/` y `models/metadata/` (respaldos multitarget).

**Implicación:** un módulo nuevo que importe de `hparam_search` o lea los artefactos del freeze nuevo dependería de código y datos que todavía no están en el historial. Conviene versionarlos antes, o en el mismo cambio que el módulo.
