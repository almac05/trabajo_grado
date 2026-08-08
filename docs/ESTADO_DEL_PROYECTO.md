# Estado del proyecto — 2026-07-20

## 0. Resumen ejecutivo

El proyecto (predicción de demanda de pasajeros para Transportes Montebello, rutas 1 y 3, UAO) tiene la Fase 1 (ETL + EDA + diagnóstico operativo) completamente implementada y persistida, y la Fase 3 (modelado) **con código y una primera corrida de baselines ya ejecutada hoy mismo (2026-07-20)**, aunque el `README.md` versionado sigue marcando "Modelado: 🔲 Pendiente" — desactualizado frente al estado real del working tree. El pipeline ETL corrió por última vez el 2026-06-10 (`freeze_20260610_192142`, 109 559 filas / 18 columnas), y ese freeze es el dataset base de todo el modelado vigente. Existen 4 baselines temporales implementados y evaluados (naive, seasonal_naive_daily, seasonal_naive_weekly, historical_average_route_day_type_slot) sobre 3 escenarios/targets, con backtesting de ventana expansiva (38 folds de validación + test final de 10 semanas), corregido hoy para alinear los cortes a días operativos completos (04:00–04:00). No hay SARIMA, Prophet, XGBoost, LSTM, GRU ni CNN-LSTM implementados — únicamente baselines estadísticos simples. No existe MLflow ni `mlruns/`; la trazabilidad de corridas se hace por convención de nombres de archivo con timestamp. La suite de pytest completa pasa (134 passed, 0 failed) al momento de esta auditoría. Hay conflictos documentados entre artefactos (ver sección 7): el README declara ~150 000 despachos model-ready vs. 109 559 reales del freeze vigente; `docs/project_summary_for_claude.md` (2026-06-08) afirma que headway y demand-supply "NO existen", pero esos módulos ya están implementados (aunque no comprometidos a git); y hay dos versiones del inventario diagnóstico (`inventario_diagnostico.md` vs `_v2.md`) con alcance distinto. El directorio `revision_modelado/` es un paquete de auditoría externa fechado 2026-07-18 18:11, **anterior** a la corrida de "días operativos completos" de hoy a las 15:30 — por tanto sus cifras de métricas están una iteración desactualizadas frente al estado actual. Lo que sigue: (1) decidir y congelar la versión de partición temporal (día operativo completo) como definitiva; (2) comprometer a git el módulo `modeling/` y los `analytics/` nuevos; (3) implementar modelos ML/DL más allá de baselines; (4) resolver los conflictos de la sección 7 antes de redactar el capítulo de resultados de la tesis.

## 1. Inventario estructural

### Árbol (3 niveles, excluyendo .venv, __pycache__, .git, mlruns, .pytest_cache, .pytest_tmp, .ruff_cache, build)

```
proyecto_grado/
├── .agents/ .claude/ .vscode/                  (config de tooling, no relevantes al proyecto)
├── Anteproyecto Carlos Macias V4.pdf            (documento de anteproyecto)
├── Dockerfile, docker-compose.yml, .dockerignore
├── Makefile, pyproject.toml, uv.lock, README.md
├── .env / .env.example / .pre-commit-config.yaml
├── backups/
│   ├── modeling_full_days_20260720_152008/{configs,scripts,src,tests}
│   └── modeling_refactor_20260720_141525/{configs,scripts,src,tests}
├── configs/
│   ├── etl.yaml, features.yaml
│   └── modeling/{backtesting.yaml, models.yaml, targets.yaml}
├── data/
│   ├── external/  (vacío según muestreo)
│   ├── interim/{batches_parquet, gps, qc}
│   ├── processed/{eda, model_ready, modeling, time_series, operational_hours.parquet}
│   └── raw/despachos_raw_historico.csv (.gitkeep)
├── docs/
│   ├── project_summary_for_claude.md (2026-06-08, desactualizado — ver §7)
│   └── taller_final_plan_entrega.html
├── models/
│   └── metadata/ (JSON de corridas de dataset y baselines, con backups/ internos)
├── notebooks/{01_eda,02_preprocessing,03_modeling,04_evaluation}  — vacíos (solo estructura)
├── reports/
│   ├── figures/{baseline, eda, modeling, operational_heatmap_*.png}
│   └── tables/{baseline, eda, etl, modeling, qc, gaps_horario_operativo.csv, operational_hours_summary.csv, time_series_summary.csv}
├── revision_modelado/  (+ revision_modelado.zip)      — paquete de auditoría externa, ver §7
├── scripts/            (18 scripts .py, ETL/EDA/diagnóstico/modelado)
├── src/proyecto_grado/
│   ├── analytics/  (etl_diagnostics, kpis, plots, report + headway, demand_supply, fleet_availability, vehicle_productivity — estos 4 últimos sin comprometer a git)
│   ├── dashboard/app.py
│   ├── data/, dispatch/ (vacío), eda/, etl/, evaluation/ (vacío)
│   ├── features/, models/{baselines,ml,dl} (vacíos — solo __init__.py)
│   ├── modeling/  (backtesting, baselines, config, dataset, error_analysis, evaluate, features, splits — sin comprometer a git)
│   └── utils/ (+ pruebas.py, sin comprometer)
└── tests/{unit (15 módulos), integration (1 módulo)}
```

### Propósito y estado por carpeta de primer nivel

| Carpeta | Propósito inferido | Estado |
|---|---|---|
| `configs/` | Parámetros declarativos ETL/features/modelado | Activo |
| `data/` | Datos crudos, intermedios y procesados | Activo, con múltiples freezes históricos coexistiendo |
| `docs/` | Documentación técnica | Activo pero con documentos desactualizados (ver §7) |
| `models/` | Metadatos de corridas de modelado (no artefactos de modelo serializados) | Activo (actividad de hoy) |
| `notebooks/` | Notebooks por fase | Vacío/placeholder — el proyecto es script-based, no notebook-based |
| `reports/` | Figuras y tablas de salida | Activo |
| `scripts/` | Entry points CLI del pipeline y diagnósticos | Activo |
| `src/proyecto_grado/` | Código fuente del paquete | Activo; `dispatch/`, `evaluation/`, `models/{baselines,ml,dl}` son stubs vacíos |
| `tests/` | Suite pytest | Activo, 134 tests pasan |
| `backups/` | Snapshots manuales del autor durante el refactor de hoy | No versionado, tratar como bitácora informal, no fuente de verdad |
| `revision_modelado/` + `.zip` | Paquete empaquetado para revisión externa ("codex") de la fase de modelado | Snapshot fechado 2026-07-18, ya desactualizado frente al código vigente (ver §7) |

### README, pyproject.toml, .gitignore, Makefile, docker-compose.yml

- **README.md**: declara ETL, ETL Analytics, Features, EDA temporal y Dashboard como "✅ Implementado"; Modelado, Evaluación y Despacho como "🔲 Pendiente". Esta tabla está desactualizada: hay código de modelado funcional y ejecutado hoy (ver §4), aunque no comprometido a git. El README también reporta "~150 000 despachos tras filtros QC" para el dataset model-ready, cifra que no coincide con el freeze vigente (109 559 filas, ver §7).
- **pyproject.toml**: Python ≥3.11; dependencias productivas: pandas≥2.1, numpy≥1.26, pyarrow≥15.0, sqlalchemy≥2.0, pymysql≥1.1, mysql-connector-python==9.6.0, matplotlib≥3.8, seaborn≥0.13, streamlit≥1.36, altair≥5.0, scikit-learn≥1.4, statsmodels≥0.14, xgboost≥2.0, prophet≥1.1, pyyaml≥6.0, tqdm≥4.66, holidays≥0.46. Extra `dl` = torch≥2.2 (no instalado por defecto). Extra `aws` = boto3/s3fs/sagemaker. Extra `dev` = pytest≥8.0, pytest-cov, ruff≥0.3, mypy≥1.8, pre-commit, ipykernel, jupyter, nbconvert. Ruff configurado con reglas E/F/W/I/N/UP/B/C4/SIM/RUF, línea 100, ignora E501. Mypy strict_optional=true, excluye notebooks y tests. Pytest con `--basetemp=.pytest_tmp` y markers `unit/integration/slow`.
- **.gitignore**: excluye `__pycache__/`, `.venv/`, `.env`, `.ipynb_checkpoints/`, artefactos de build. No excluye explícitamente `data/`, `models/`, `reports/` ni `backups/` en la porción revisada (primeras 30 líneas); esto explica por qué `models/`, `backups/`, `revision_modelado/` aparecen como *untracked* en vez de ignorados.
- **Makefile**: define targets `venv/install/dev`, `lint/format/typecheck`, `test/test-eda/test-cov`, `etl/etl-dry-run/etl-clean`, `build-ts*/estimate-op-hours`, `eda-temporal/eda-clean`, `docker-*`, `post-etl-report`, `dashboard`. Sección "Fase 3-4: Entrenamiento y evaluación" está comentada como "pendiente de implementación" — **desactualizada**: ya existen scripts de modelado operativos (`run_backtesting.py`, `evaluate_models.py`, `build_modeling_report.py`) sin targets de Makefile asociados. Cambio no comprometido detectado en `git diff`: el target `dashboard` pasó de invocar `main()` por import a invocar `streamlit run ... --server.port 8502` directamente.
- **docker-compose.yml**: servicio `app` (build desde `Dockerfile`, Python 3.11-slim declarado), monta `data/`, `reports/`, `configs/` (ro) y `src/` (ro); comando por defecto `python -m proyecto_grado.etl.pipeline`. Existe también un servicio `db` opcional (no leído en detalle, truncado a 40 líneas en la inspección).

### Commits y cambios no comprometidos

Últimos 3 commits (git log completo del repo — solo hay 3):
1. `9345b1e` — docs: actualizar README con estado real del proyecto
2. `674d1f6` — fix: corregir símbolo multiplicación ambiguo en docstrings y linting
3. `10cf2ed` — Proyecto trabajo de grado

⚠️ No verificable: se solicitaron los últimos 20 commits, pero el repositorio solo tiene 3 en su historial completo (`git log --oneline` no devuelve más).

Rama activa: `master`, sincronizada con `origin/master` (`git status` → "up to date").

`git diff --stat` (cambios no comprometidos en archivos trackeados):
```
 Makefile                                 | 2 +-
 src/proyecto_grado/analytics/__init__.py | 5 +++++
 src/proyecto_grado/etl/config.py         | 2 +-
 tests/unit/test_config.py                | 6 +++++-
 uv.lock                                  | 4 ++++
```
Detalle: `src/proyecto_grado/analytics/__init__.py` ahora importa `HeadwayAnalyzer`, `DemandSupplyAnalyzer`, `FleetAvailabilityAnalyzer`, `ProductivityAnalyzer` desde módulos nuevos aún no comprometidos (`headway.py`, `demand_supply.py`, `fleet_availability.py`, `vehicle_productivity.py`). `etl/config.py` cambió `load_dotenv(PROJECT_ROOT / ".env")` a `load_dotenv(PROJECT_ROOT / ".env", override=True)`. `Makefile` cambió el target `dashboard`. `tests/unit/test_config.py` fue ajustado para aceptar la nueva firma de `load_dotenv`.

Archivos *untracked* relevantes (lista completa en el `git status` provisto): `backups/`, `configs/modeling/`, `docs/project_summary_for_claude.md`, `docs/taller_final_plan_entrega.html`, `models/`, `reports/inventario_diagnostico.md`, `reports/inventario_diagnostico_v2.md`, `revision_modelado.zip`, `revision_modelado/`, 12 scripts nuevos en `scripts/`, 4 módulos nuevos en `src/proyecto_grado/analytics/`, todo `src/proyecto_grado/modeling/`, `src/proyecto_grado/utils/pruebas.py`, `tests/unit/test_modeling.py`.

**Conclusión de la sección 1**: el trabajo de modelado y de analítica avanzada (headway, disponibilidad de flota, productividad) existe y funciona, pero vive enteramente fuera del control de versiones — un riesgo de pérdida de trabajo y de reproducibilidad para la tesis.

## 2. Pipeline ETL y datos procesados

### Scripts y transformaciones (Bloques 1–9, según `src/proyecto_grado/etl/`)

| Bloque | Módulo | Entrada | Salida | Transformaciones |
|---|---|---|---|---|
| 3 | `extract.py` | MySQL `tbl_intervalo_despacho` (Registel) o CSV crudo | `data/raw/despachos_raw_historico.csv` | Extracción incremental |
| 4 | `transforms.py` | raw | normalizado | Normalización temporal, cálculo de duraciones, filtrado de rutas 1 y 3 |
| 5 | `gps.py` | normalizado + `tbl_forwarding_wtch` | `data/interim/gps/` | Geocerca radio 700 m (`configs/etl.yaml:gps.radio_geocerca_m`), imputación de `HORA_INICIAL_REAL` con ventanas escalonadas [30, 90, 180] min |
| 6 | `qc.py` | post-GPS | `data/interim/qc/` | QC hard/soft: percentil 99.0 duración, percentil 99.5 pasajeros, frecuencia de despacho 1–60 min (`configs/etl.yaml:qc.*`) |
| 7 | `trip_end.py` | post-QC + GPS | clasificación FIN_TIPO | Ventana GPS de 180 min con buffer de 20 min antes de `HORA_INICIAL_REAL`; umbral 3 km/h para "detenido", 12 km/h para "retorno activo"; score de abandono con señal "Móvil Apagado" (peso 0.35) |
| 8 | `model_ready.py` | post-trip_end | `data/processed/model_ready/despachos_model_ready*.{csv,parquet}` | Construcción del dataset final con flag `MODEL_READY_OK` |
| 9 | `pipeline.py` | orquestador | exportación + metadatos JSON | Ejecuta Bloques 3–9 secuencialmente |

Configuración leída de `configs/etl.yaml`: rutas operativas `[1, 3]`; puntos GPS `MOJICA` (3.416218, -76.490574) y `MORICHAL` (3.398863, -76.508078); `checkpoint_every: 500`.

`configs/features.yaml`: granularidades `[15, 30, 60]` min; franjas horarias MADRUGADA(0-5)/MAÑANA(6-11)/MEDIODÍA(12-13)/TARDE(14-18)/NOCHE(19-23); `imputacion_gaps: zero`; `cobertura_minima_dias: 30`; horario operativo con `umbral_actividad=0.10`, `umbral_anomalia=0.30`, `min_dias_muestra=10`, `incluir_festivo_puente=true`.

### Inventario de archivos procesados (verificado con `pandas.read_parquet`/`read_csv`, `uv run python`)

| Archivo | Tamaño | mtime | Filas × Cols | Rango temporal |
|---|---|---|---|---|
| `data/raw/despachos_raw_historico.csv` | 15 992 430 B (15.25 MB) | 2026-06-10 19:21 | 109 720 × 17 | `FECHA_INICIAL`/`FECHA_FINAL`: 2024-04-16 → 2026-06-10 |
| `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.parquet` (= dataset activo, referenciado por `configs/modeling/targets.yaml`) | 3 451 428 B | 2026-06-10 19:21 | 109 559 × 18 | `FECHA_INICIAL`: 2024-04-16 → 2026-06-10 |
| `data/processed/model_ready/despachos_model_ready_freeze_20260610_191955.parquet` | 3 451 428 B | 2026-06-10 19:19 | (freeze previo, 2 min antes del vigente) | idéntico rango |
| `data/processed/model_ready/despachos_model_ready_freeze_20260503_114750.parquet` | 3 320 481 B | 2026-05-03 11:47 | (freeze anterior) | — |
| `data/processed/model_ready/despachos_model_ready.parquet` (alias "actual", sin timestamp) | 3 451 428 B | 2026-06-10 19:21 | igual al freeze `_192142` | — |
| `data/processed/time_series/ts_ruta1_g30min.parquet` | 426 403 B | 2026-05-03 18:02 | 35 864 × 19 | 2024-04-16 04:30 → 2026-05-03 08:00 |
| `data/processed/time_series/ts_ruta3_g30min.parquet` | 431 815 B | 2026-05-03 18:02 | 35 867 × 19 | 2024-04-16 04:00 → 2026-05-03 09:00 |
| `data/processed/modeling/modeling_dataset_g30min.parquet` | — | 2026-07-18/20 | 43 831 × 34 | 2024-04-16 04:00 → 2026-06-10 16:00 |
| `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` | — | — | 43 831 × 76 | 2024-04-16 04:00 → 2026-06-10 16:00 |
| `data/processed/modeling/modeling_dataset_pasajeros_total_oferta_historica_rezagada_g30min.parquet` | — | — | 43 831 × 76 | ídem |
| `data/processed/modeling/modeling_dataset_pasajeros_por_despacho_productividad_por_despacho_g30min.parquet` | — | — | 43 831 × 76 | ídem |
| `data/processed/operational_hours.parquet` | — | — | 30 × 14 | — |

**⚠️ Conflicto — "total de registros modelables"**: las `data/processed/time_series/ts_ruta{1,3}_g30min.parquet` (generadas 2026-05-03) tienen rango hasta **2026-05-03**, mientras que los datasets en `data/processed/modeling/` (generados 2026-07-18/20, a partir del freeze de junio) llegan hasta **2026-06-10**. Es decir, las series temporales "clásicas" de `features/` están desactualizadas respecto del dataset de modelado vigente y no deben usarse como fuente de EDA final sin regenerar.

**Retención vs. crudo — dos versiones no reconciliadas**:
- `reports/tables/eda/retention_summary.csv` (sin fecha de generación explícita en el CSV, pero corresponde a un freeze anterior): `raw_rows=104803, model_ready_rows=104650, retention_pct=99.85%`.
- `reports/tables/etl/model_ready_metadata_20260610_192142.json` (freeze vigente, 2026-06-10 19:21): `rows_final=109559, cols_final=18`.
- `data/raw/despachos_raw_historico.csv` actual: 109 720 filas.
- Retención implícita del freeze vigente: 109 559 / 109 720 ≈ 99.85% (consistente en magnitud con el CSV de retención, pero **el CSV de retención no corresponde al freeze vigente** — sus totales absolutos, 104 803/104 650, no coinciden con ninguno de los freezes inventariados). Se reporta como conflicto sin resolver: la tabla `retention_summary.csv` debe regenerarse contra el freeze `_20260610_192142` antes de citarla en la tesis.

**Esquema del dataset model-ready vigente** (`reports/tables/etl/model_ready_metadata_20260610_192142.json`): `PK_INTERVALO_DESPACHO, PLACA, FK_RUTA, FECHA_INICIAL, HORA_INICIAL_REAL, HORA_FIN_FINAL, DURACION_MIN_FINAL, PASAJEROS, DISTANCIA, RECORRIDO_COMPLETO, FIN_TIPO, HORA_FIN_FUENTE, HORA_INICIO_H, HORA_FIN_H, DIA_SEMANA, MES, DIA, MODEL_READY_OK` (18 columnas). Distribución `FIN_TIPO` en este freeze: COMPLETO=94 400, TRUNCADO_RETORNO=11 988, TRUNCADO_INDETERMINADO=1 994, TRUNCADO_ABANDONO=1 152, SIN_GPS=25 (suma=109 559).

**Exclusión de mayo 2026 como mes incompleto**: ⚠️ No verificable. Se buscó en `src/`, `scripts/` y `configs/` cualquier lógica de exclusión de "2026-05" o "mayo" como mes incompleto (`grep -rniE "2026-05|mayo"`) y no se encontró ningún filtro de ese tipo; las únicas coincidencias son menciones textuales en reportes ("Abril 2024 – Mayo 2026" como rango descriptivo) y la palabra "mayor" en variables no relacionadas. El dataset de modelado sí excluye el **último día parcial** (2026-06-10, desde las 04:00) mediante la lógica de "días operativos completos" (ver §4), pero esto es distinto de excluir un mes calendario completo.

**Gaps operativos** (`reports/tables/gaps_horario_operativo.csv`, columnas `granularidad_min,ruta,tipo_dia,n_franjas_op,n_gaps_op,pct_gaps_op,n_franjas_24h,n_gaps_24h,pct_gaps_24h`): ejemplo a 15 min, ruta 1: LABORAL `pct_gaps_op=8.21%` (vs. `pct_gaps_24h=47.27%`); DOMINGO `pct_gaps_op=58.81%` (vs. `79.32%` en vista 24h). La columna `_op` (dentro de horario operativo) es la métrica correcta para eficiencia según nota metodológica en `docs/project_summary_for_claude.md`.

`data/processed/operational_hours.parquet` (30×14) resumido en `reports/tables/operational_hours_summary.csv`: ejemplo ruta 1, 15 min, LABORAL: horario 04:30–18:00 (13.75 h), 501 días de muestra, 1 franja anómala, cobertura 100%.

## 3. Diagnóstico operativo y marco de KPIs

Esta sección se apoya en `reports/inventario_diagnostico_v2.md` (generado 2026-07-05 11:21, alcance más amplio y con verificación cruzada explícita frente al freeze) como fuente primaria, contrastada puntualmente contra los CSV originales. Se cita como "según `reports/inventario_diagnostico_v2.md`" cuando el valor proviene de ese inventario y fue confirmado por lectura directa del CSV fuente.

### Tabla consolidada de indicadores

| Indicador | Valor por ruta | Archivo fuente | Fecha (mtime) | Clasificación |
|---|---|---|---|---|
| CV headway | Ruta 1: cv=0.722, media=10.97 min, p95=24.17 min; Ruta 3: cv=0.774, media=10.56 min, p95=24.70 min | `reports/tables/baseline/headway_summary.csv` (confirmado por lectura directa) | 2026-06-08 17:28 | Hallazgo diagnóstico (no es un objetivo de predicción de demanda; describe regularidad de despacho) |
| Bunching (agrupamiento) | Ruta 1: 3.82%; Ruta 3: 4.71% | `headway_summary.csv` | 2026-06-08 17:28 | Hallazgo diagnóstico |
| Espera excesiva | Ruta 1: 2.79%; Ruta 3: 3.09% | `headway_summary.csv` | 2026-06-08 17:28 | Hallazgo diagnóstico |
| Disponibilidad de flota / patio vacío | `n_dias_analizados=30`; `pct_vacio_pico_manana=34.1%`; `pct_vacio_pico_tarde=0.0%`; `pct_vacio_cierre=5.6%`; `disp_promedio_pico_manana=2.67` | `reports/tables/baseline/fleet_availability_summary.csv` (confirmado) | 2026-07-02 19:38 | Hallazgo diagnóstico |
| Intervalos largos por franja | `total_headways_largos=447`; pico mañana 19.5%, pico tarde 15.7%, cierre 14.3%, otros 50.6% | `fleet_availability_summary.csv` | 2026-07-02 19:38 | Hallazgo diagnóstico |
| Contracción de flota | Vehículos activos: 63.0 → 42.0 (−33.3%); Despachos: 5266 → 3179 (−39.6%); Pasajeros: 247 688 → 145 868 (−41.1%) | `reports/tables/baseline/diagnostico_flota_comparacion.csv` (confirmado) | 2026-06-23 10:49 | Hallazgo diagnóstico (magnitud de la contracción de oferta, no mejorable directamente por el modelo de demanda) |
| Productividad por despacho | Ruta 1: media bruta=44.4, p50=44.51; Ruta 3: media bruta=48.5, p50=48.65; global 47.04 → 45.88 pas/desp (−2.5%) | `reports/tables/baseline/productivity_summary.csv` y `diagnostico_flota_comparacion.csv` (confirmados) | 2026-06-23 10:40 / 10:49 | KPI retenido (target `pasajeros_por_despacho` en `configs/modeling/targets.yaml`) |
| Intensidad de uso (despachos/vehículo) | 83.59 → 75.69 (−9.5%) | `diagnostico_flota_comparacion.csv` | 2026-06-23 10:49 | Hallazgo diagnóstico |
| Rotación entre despachos por placa | Sin CSV/figura persistida; solo salida de consola | `scripts/diagnostico_rotacion.py` (mtime 2026-06-22 20:20) | — | Hallazgo diagnóstico no persistido — hueco pendiente |
| Ajuste oferta-demanda (load factor) | Ruta 1: load_factor_mean=1.544, sobrecarga=96.34%; Ruta 3: load_factor_mean=1.642, sobrecarga=96.24% — **metodológicamente inválido** | `reports/tables/baseline/demand_supply_summary.csv` | 2026-06-08 16:01 | Descartado — advertencia explícita en `inventario_diagnostico_v2.md`: `PASAJEROS` son abordajes acumulados por recorrido, no ocupación simultánea; `load_factor` no debe usarse como KPI de ajuste oferta-demanda |
| Demanda recuperable | Solo fórmula conceptual: `demanda_recuperable = (despachos_recomendados − despachos_reales) × productividad_estable (~46 pas/desp)`; sin cálculo persistido | `reports/tables/baseline/BASELINE_REPORT.txt` | 2026-06-29 11:51 | Hallazgo diagnóstico no calculado — hueco pendiente |

### Desactualización frente al freeze de referencia

Según `reports/inventario_diagnostico_v2.md` §2, los siguientes artefactos de `reports/tables/baseline/` son anteriores al freeze `_20260610_192142` (2026-06-10 19:21) y por tanto recalculables con el dataset más reciente: `demand_supply_by_franja.csv`, `demand_supply_summary.csv`, `load_factor_distribution.csv`, `headway_by_franja.csv`, `headway_by_hour.csv`, `headway_summary.csv` (todos con mtime 2026-06-08). Los artefactos de disponibilidad de flota, contracción de flota y productividad (mtime 2026-06-22/23, julio 02) son posteriores al freeze de junio y por tanto consistentes con él.

**Advertencia adicional de `inventario_diagnostico_v2.md` §3**: `reports/tables/baseline/fleet_availability_report.txt` y `reports/tables/baseline/BASELINE_REPORT.txt` conservan texto narrativo de una corrida anterior de 15 días, desalineado con los CSV actuales de 30 días (`fleet_availability_summary.csv`, `fleet_availability_by_day.csv`).

**Artefactos solo-consola sin persistencia** (según `inventario_diagnostico_v2.md` §4, verificado por ausencia de `to_csv/to_parquet/savefig` en el código): `scripts/build_baseline.py`, `scripts/build_baseline_consolidado.py`, `scripts/build_fleet_availability.py`, `scripts/build_productivity.py`, `scripts/diagnostico_rotacion.py`, entre otros.

## 4. Estado del modelado (Fase 3)

### Modelos: implementado / esbozado / inexistente

| Modelo | Estado | Archivo |
|---|---|---|
| `naive` (último valor, `lag_1`) | Implementado y evaluado | `src/proyecto_grado/modeling/baselines.py` |
| `seasonal_naive_daily` (`lag_48` a 30 min) | Implementado y evaluado | `src/proyecto_grado/modeling/baselines.py` |
| `seasonal_naive_weekly` (`lag_336` a 30 min) | Implementado y evaluado | `src/proyecto_grado/modeling/baselines.py` |
| `historical_average_route_day_type_slot` (promedio histórico por ruta×tipo_día×franja_30min, con fallback) | Implementado y evaluado | `src/proyecto_grado/modeling/baselines.py` |
| SARIMA | Inexistente | No se encontró `train_statistical.py` ni referencia a SARIMA en `src/proyecto_grado/modeling/` |
| Prophet | Inexistente | Sin archivo dedicado; dependencia declarada en `pyproject.toml` pero no usada en `modeling/` |
| XGBoost | Inexistente | Ídem — dependencia declarada, no usada |
| Random Forest / scikit-learn ML | Inexistente | `src/proyecto_grado/models/ml/__init__.py` vacío |
| LSTM / GRU | Inexistente | `src/proyecto_grado/models/dl/__init__.py` vacío; extra `dl` (torch) no instalado por defecto |
| Híbrido CNN-LSTM | Inexistente | Sin rastro en el repositorio |

`src/proyecto_grado/models/{baselines,ml,dl}/` (paquete antiguo) siguen siendo stubs vacíos; toda la implementación real vive en el paquete nuevo `src/proyecto_grado/modeling/` (no comprometido a git): `backtesting.py`, `baselines.py`, `config.py`, `dataset.py`, `error_analysis.py`, `evaluate.py`, `features.py`, `splits.py`.

### Configuración efectiva verificada

- **Granularidad de trabajo**: 30 minutos (`configs/modeling/targets.yaml:granularity_min`, confirmado en metadatos de corrida).
- **Horizonte**: 1 franja adelante (`horizon: 1`).
- **Rutas**: [1, 3].
- **Targets**: `pasajeros_total` (columna `pasajeros_total`) y `pasajeros_por_despacho` (columna `pasajeros_por_despacho_real`), definidos en `configs/modeling/targets.yaml`.
- **Escenarios/feature sets** (`configs/modeling/backtesting.yaml`): `sin_oferta` (calendario+ruta+lags de demanda), `oferta_historica_rezagada` (+ lags de despachos), `productividad_por_despacho` (+ lags de productividad).
- **Variables de fuga excluidas explícitamente**: `pasajeros_promedio, ocupacion_p95, HORA_FIN_FINAL, DURACION_MIN_FINAL, FIN_TIPO, HORA_FIN_FUENTE, RECORRIDO_COMPLETO` (`configs/modeling/targets.yaml:exclude_predictors`).
- **Features de lag/rolling** (según `revision_modelado/informe_codex.txt`, sección D, no re-verificado línea por línea en el código vivo pero consistente con `src/proyecto_grado/modeling/features.py`): `lag_1, lag_2, lag_3, lag_48, lag_96, lag_336`; `rolling_mean_{3,6,12}`, `rolling_std_{6,12}` calculados con `shift(1)` para evitar fuga; variables cíclicas `hora_sin/cos`, `dia_semana_sin/cos`.
- **Esquema de partición temporal**: ventana expansiva (`configs/modeling/backtesting.yaml`: `seed=42, test_weeks=10, validation_weeks=2, step_weeks=2, min_train_weeks=26`), con **38 folds de validación** + 1 test final. Desde la corrida de hoy 15:30 (`full_days_20260720_1530`), la partición se alinea a **días operativos completos** `[D 04:00, D+1 04:00)` (`operational_day_start="04:00:00"`, `require_full_operational_days=true`, `drop_partial_boundary_days=true` en `configs/modeling/backtesting.yaml`).
- **Métricas de evaluación**: MAE, RMSE, sMAPE, WAPE, bias_mean (confirmado en `models/metadata/*.json` y en los CSV `metrics_comparison_multitarget*.csv`).
- **Semilla/reproducibilidad**: `seed: 42` (`configs/modeling/backtesting.yaml`), `shuffle=False` por construcción de ventanas temporales ordenadas (sin uso de `shuffle` detectado en el pipeline de backtesting, según `revision_modelado/informe_codex.txt` §E).

### Resultado de la corrida más reciente (`full_days_20260720_1530`, 2026-07-20 15:30–15:37)

Según `reports/tables/modeling/reporte_alineacion_dias_completos.md` y `comparacion_splits_dias_completos.md` (ambos generados 2026-07-20 15:37, los más recientes del repositorio):

- Se corrigió la partición temporal para excluir días operativos parciales en los bordes de validación/test. Targets, features, escenarios y modelos baseline **no cambiaron**; solo el soporte temporal.
- Test final corregido: `2026-04-02 04:00:00 → 2026-06-10 04:00:00` (antes: `2026-04-01 16:00:00 → 2026-06-10 16:30:00`), quedando **69 días operativos completos**. Filas de test por ruta: Ruta 1 = 1890, Ruta 3 = 1948 (antes de exclusión: se descartaron 5+24 filas en ruta 1 y 5+23 en ruta 3, en los bordes inicial/final).
- Folds de validación: 38 antes y después (sin cambio en el conteo, sí hubo cambio menor en encuadre horario que ya coincidía con 04:00 en la mayoría de folds).
- Cambios en métricas principales (tabla completa en `comparacion_splits_dias_completos.md` §J): por ejemplo, para `pasajeros_total`/escenario `sin_oferta`/modelo `historical_average_route_day_type_slot`/ruta 1: MAE 36.082 → 35.643 (Δ=−0.438), RMSE 45.146 → 44.461, WAPE 35.684 → 35.193, bias_mean 27.860 → 27.294, n=1544→1518.
- Resultado de pruebas reportado en el propio informe de refactor: `ruff check` → "All checks passed!"; `compileall` → código de salida 0; `pytest tests/unit/test_modeling.py` → 23 passed; `pytest tests/unit/test_config.py` → 1 passed; suite completa → **134 passed, 0 failed, 8 warnings**.
- **Verificación independiente de esta auditoría**: se ejecutó `uv run python -m pytest tests -q` sobre el working tree actual (no el backup) y se confirmó **134 passed, 8 warnings, 0 failed**, consistente con lo reportado en el informe de refactor de hoy.

### Métricas de referencia previas (corrida `baselines_full_20260718`, snapshot documentado por `revision_modelado/informe_codex.txt`, generado 2026-07-18 18:11 — **anterior** al refactor de días completos de hoy)

Test final (`pasajeros_total`, target legado, sin distinción de escenario), extracto:

| Modelo | Ruta | MAE | RMSE | sMAPE | WAPE | bias_mean |
|---|---|---|---|---|---|---|
| historical_average_route_day_type_slot | 1 | 36.082 | 45.146 | 35.929 | 35.684 | 27.860 |
| historical_average_route_day_type_slot | 3 | 38.414 | 49.957 | 34.150 | 32.581 | 27.098 |
| naive | 1 | 43.560 | 55.867 | 42.672 | 41.198 | 1.247 |
| naive | 3 | 55.279 | 73.231 | 46.058 | 44.314 | 0.299 |
| seasonal_naive_daily | 1 | 47.505 | 60.917 | 50.796 | 46.850 | 4.766 |
| seasonal_naive_daily | 3 | 53.069 | 68.102 | 51.101 | 45.501 | 6.352 |
| seasonal_naive_weekly | 1 | 42.846 | 55.666 | 44.939 | 41.290 | 1.518 |
| seasonal_naive_weekly | 3 | 47.451 | 62.552 | 44.095 | 39.230 | 1.545 |

⚠️ Estas cifras (del 18 de julio, empaquetadas en `revision_modelado/`) están **una iteración desactualizadas** frente a los resultados corregidos del 20 de julio (sección anterior). Se citan porque son las que efectivamente fueron enviadas para revisión externa ("codex") y por tanto son las que un revisor externo pudo haber visto — deben reconciliarse antes de redactar resultados finales.

### MLflow / mlruns

No existe directorio `mlruns/` en el repositorio ni se encontró configuración de tracking URI de MLflow en el código inspeccionado. La trazabilidad de corridas se implementa manualmente mediante metadatos JSON en `models/metadata/*.json` con convención de nombre `<tipo>_<run_id>_<timestamp>.json` y CSV versionados con sufijo `_<run_id>` en `reports/tables/modeling/`. **No hay MLflow registrado; declarado explícitamente ausente.**

### Suite de pruebas

15 módulos en `tests/unit/` + 1 en `tests/integration/`. `tests/unit/test_modeling.py` contiene 23 funciones `test_*` (cubre splits, baselines, anti-fuga según nombre del archivo y confirmación en `informe_codex.txt`). Ejecución de `uv run python -m pytest tests -q` por esta auditoría: **134 passed, 0 failed, 8 warnings** (los 8 warnings son `RuntimeWarning`/`ValueWarning` de `statsmodels` en `test_temporal_eda.py`, no relacionados con modelado). No se requirió acceso a base de datos ni red para esta corrida.

## 5. Figuras y salidas para la tesis

Este inventario se apoya en `reports/inventario_diagnostico_v2.md` (verificado 2026-07-05) para las figuras EDA/operativas, y en inspección directa del sistema de archivos para las figuras de modelado (posteriores a esa fecha).

### Figuras de modelado (`reports/figures/modeling/`, no cubiertas por el inventario de julio 5 por ser posteriores)

| Archivo | Script productor (inferido por convención de nombre/CLI) |
|---|---|
| `backtesting_folds.png` | `scripts/build_modeling_report.py` |
| `error_by_hour_baselines.png` | `scripts/build_modeling_report.py` |
| `metrics_comparison_baselines.png` | `scripts/build_modeling_report.py` |
| `observed_vs_predicted_baselines.png` | `scripts/build_modeling_report.py` |
| `residuals_baselines.png` | `scripts/build_modeling_report.py` |

⚠️ No verificable con precisión de línea de código: no se abrió el contenido completo de `scripts/build_modeling_report.py` (12 204 bytes, modificado 2026-07-20 15:24) para confirmar el mapeo exacto de cada figura a su función; la atribución anterior es por convención de nombres y por ser el único script de reporte de modelado presente. **Nota**: estas 5 figuras corresponden a la corrida de baselines sin sufijo de `run_id` versionado en el nombre de archivo — no queda explícito en el nombre si corresponden a la corrida `baselines_full_20260718` o a una posterior; los CSV versionados más recientes (`*_full_days_20260720_1530.csv`) no tienen figuras homónimas versionadas — **posible desactualización de figuras respecto a las tablas más recientes**.

### Figuras EDA/operativas (según `inventario_diagnostico_v2.md`, 61 PNG persistidas)

Resumen por familia (detalle completo en el inventario v2 citado):
- `reports/figures/eda/acf_pacf_{1,3}_g{15,30,60}min.png` (6 figuras) — `scripts/run_eda_temporal.py`, mtime 2026-05-07.
- `reports/figures/eda/boxplot_tipo_dia_{1,3}_g{15,30,60}min.png` (6 figuras) — ídem.
- `reports/figures/eda/curva_intraday_{1,3}_{tipo_dia}_g{15,30,60}min.png` (30 figuras) — ídem.
- `reports/figures/eda/heatmap_demanda_hora_dia_{1,3}_g{15,30,60}min.png` (6 figuras) — ídem.
- `reports/figures/eda/tendencia_mensual_{1,3}.png` (2 figuras) — ídem.
- `reports/figures/eda/demand_by_route.png`, `demand_by_hour_weekday.png`, `qc_flags_top.png`, `etl_rows_by_stage.png` — `src/proyecto_grado/analytics/plots.py`, mtime 2026-04-25.
- `reports/figures/operational_heatmap_{1,3}_{15,30,60}min.png` (6 figuras) — `src/proyecto_grado/features/operational_hours.py:354-372`, mtime 2026-05-03.
- `reports/figures/baseline/contraccion_flota_mensual.png` — `scripts/plot_contraccion_flota.py:124-216`, mtime 2026-06-29 20:18.

Todas las figuras EDA/operativas listadas arriba son **anteriores** al freeze `_20260610_192142` (según `inventario_diagnostico_v2.md` §2) y por tanto "recalculables" con el dataset más reciente si se desea que el capítulo de EDA de la tesis cite exactamente el freeze vigente.

### Figuras solo en código (no persistidas como archivo, ~20 según inventario v2)

Todas viven en `src/proyecto_grado/dashboard/app.py` (Streamlit + matplotlib/seaborn/Altair) y en `src/proyecto_grado/etl/gps.py:84` (`plt.show`, no persistida). Ver listado línea por línea en `reports/inventario_diagnostico_v2.md` líneas 249-268 (26 entradas con función y número de línea).

### Figuras huérfanas / scripts sin salida verificada

⚠️ No verificable de forma exhaustiva en esta auditoría: no se re-ejecutó cada script para confirmar que su salida declarada exista actualmente en disco más allá de lo ya cruzado en `inventario_diagnostico_v2.md` §2 y §4. Ese inventario no reporta figuras huérfanas (todas las PNG encontradas tienen un productor identificado en código).

## 6. Brechas, deuda técnica y plan propuesto

### Brechas concretas (ordenadas por dependencia)

1. **Nada del trabajo de modelado y analítica avanzada está comprometido a git** (`src/proyecto_grado/modeling/`, `src/proyecto_grado/analytics/{headway,demand_supply,fleet_availability,vehicle_productivity}.py`, `configs/modeling/`, 12 scripts nuevos, `tests/unit/test_modeling.py`). Riesgo de pérdida de trabajo — es la brecha más urgente y bloquea cualquier otra, porque sin un commit no hay una versión "oficial" citable en la tesis.
2. **Conflicto de partición temporal sin cerrar**: existen dos versiones de resultados de backtesting (pre y post alineación a días operativos completos) del mismo día. Debe decidirse cuál es la definitiva antes de generar cualquier figura/tabla para el capítulo de resultados.
3. **README y Makefile desactualizados** respecto al estado real del modelado (tabla de estado y sección de targets de Fase 3-4).
4. **Retention_summary.csv y las series temporales `data/processed/time_series/*_g30min.parquet` desincronizadas** del freeze vigente — deben regenerarse antes de citarlas.
5. **No hay modelos más allá de baselines estadísticos** — SARIMA, Prophet, XGBoost, LSTM/GRU y el híbrido CNN-LSTM planteados en el anteproyecto siguen sin implementar.
6. **Rotación de vehículos y "demanda recuperable" sin persistir** — solo salida de consola / fórmula conceptual, sin tabla ni figura.
7. **Sin MLflow** — la trazabilidad manual por nombre de archivo es funcional pero fragil a errores de nomenclatura (ya se observan runs con y sin sufijo de `run_id`).

### Deuda técnica detectada

- Rutas absolutas hardcodeadas de tipo `C:\Users\regis\proyecto_grado\...` dentro de metadatos JSON (`models/metadata/*.json`) y en `revision_modelado/informe_codex.txt` — no portables entre máquinas/colaboradores.
- Múltiples "freezes" del dataset model-ready coexistiendo en `data/processed/model_ready/` (4 versiones con y sin sufijo de timestamp) sin un mecanismo declarativo de cuál es la vigente más allá de que `configs/modeling/targets.yaml` la referencia explícitamente — buena práctica parcial, pero el README y otros documentos citan cifras de freezes distintos.
- Scripts exploratorios y de producción mezclados en `scripts/` sin separación (p. ej. `diagnostico_rotacion.py` solo imprime a consola, sin persistencia, al lado de scripts que sí exportan artefactos).
- Ausencia de logging estructurado: según `inventario_diagnostico_v2.md` §4, gran parte de `etl/` y `analytics/` usa `print`/`logging` básico mezclado con persistencia, sin un logger configurado centralizadamente verificado en esta auditoría.
- Convención de nombres de archivo inconsistente entre corridas versionadas (`*_full_20260718` vs `*_full_days_20260720_1530` vs sin sufijo) dificulta automatizar "cuál es la última corrida válida".
- Carpeta `backups/` con snapshots manuales duplicando código fuente completo (dos veces en el mismo día) — indica ausencia de una disciplina de commits incrementales durante el refactor de hoy.

### Plan propuesto — próximas 5 tareas

1. **Comprometer a git el estado actual de modelado y analítica.** Archivos: `src/proyecto_grado/modeling/**`, `src/proyecto_grado/analytics/{headway,demand_supply,fleet_availability,vehicle_productivity}.py`, `configs/modeling/**`, `scripts/{build_modeling_dataset,build_modeling_report,evaluate_models,run_backtesting,run_baselines,build_baseline*,build_desajuste_od,build_fleet_availability,build_productivity,diagnostico_*}.py`, `tests/unit/test_modeling.py`. Criterio de aceptación: `git status` muestra árbol limpio salvo `.venv`, datos y artefactos generados; `git log` refleja el commit. Esfuerzo estimado: 0.5 día (incluye decidir qué excluir vía `.gitignore`, p. ej. `backups/`, `revision_modelado.zip`, `models/metadata/backups/`).
2. **Congelar la versión de partición temporal.** Decidir si `full_days_20260720_1530` reemplaza definitivamente a `baselines_full_20260718`/`multitarget_20260720_1435`, documentar la decisión en un único README de `reports/tables/modeling/`, y eliminar o archivar explícitamente las corridas obsoletas. Criterio de aceptación: un solo conjunto de métricas por escenario/target citable sin ambigüedad. Esfuerzo: 0.5 día.
3. **Regenerar `retention_summary.csv` y las series temporales de `features/` contra el freeze `_20260610_192142`.** Archivos: `scripts/build_time_series.py`, `src/proyecto_grado/analytics/report.py` (`make post-etl-report`, `make build-ts`). Criterio de aceptación: `raw_rows`/`model_ready_rows` en `retention_summary.csv` coinciden con 109 720/109 559. Esfuerzo: 0.5 día (cómputo) + revisión.
4. **Actualizar README.md y Makefile** para reflejar el estado real de Fase 3 (baselines implementados, modelos avanzados pendientes) y agregar targets `train-*`/`evaluate`/`backtest` al Makefile apuntando a los scripts ya existentes. Criterio de aceptación: tabla de estado del README coincide con el inventario de esta auditoría. Esfuerzo: 0.25 día.
5. **Implementar al menos un modelo más allá de baselines** (candidato natural: XGBoost sobre el escenario `oferta_historica_rezagada`, dado que ya existen features de lag/rolling y el pipeline de backtesting). Archivos a crear: `src/proyecto_grado/modeling/models/xgboost_model.py` (o similar), integración con `evaluate.py`/`backtesting.py` existentes. Criterio de aceptación: métricas de XGBoost persistidas en `reports/tables/modeling/metrics_comparison_*.csv` junto a los baselines, comparables fold a fold. Esfuerzo: 2-3 días.

## 7. Conflictos detectados y decisiones pendientes del autor

1. **Tamaño del dataset model-ready**: `README.md` declara "~150 000 despachos tras filtros QC" (línea 35). El freeze vigente (`despachos_model_ready_freeze_20260610_192142.parquet`, referenciado por `configs/modeling/targets.yaml`, mtime 2026-06-10 19:21) tiene **109 559 filas**, confirmado por lectura directa con pandas y por `reports/tables/etl/model_ready_metadata_20260610_192142.json`. Diferencia de ~40 000 registros. Decisión pendiente: corregir el README o aclarar a qué corte temporal/versión corresponde la cifra de ~150 000.

2. **`docs/project_summary_for_claude.md` (generado 2026-06-08) vs. estado real del código**: ese documento afirma explícitamente "NO existe" cálculo de headway/CV headway, ni módulo de desajuste demanda-oferta, ni scripts de evaluación de modelos, y lista `src/proyecto_grado/models/{baselines,ml,dl}/` como completamente vacíos. Al momento de esta auditoría existen `src/proyecto_grado/analytics/headway.py`, `demand_supply.py`, `fleet_availability.py`, `vehicle_productivity.py` y todo `src/proyecto_grado/modeling/` con baselines evaluados. Ninguno de estos archivos está comprometido a git, lo que explica en parte por qué un resumen fechado después en apariencia (2026-06-08 es anterior a las corridas de junio-julio) no los refleja — pero el documento en sí no fue regenerado desde entonces pese a llamarse "generado automáticamente". Decisión pendiente: regenerar o retirar este documento antes de usarlo como referencia de estado.

3. **`reports/inventario_diagnostico.md` (2026-06-29 14:29) vs. `reports/inventario_diagnostico_v2.md` (2026-07-05 11:21)**: la v1 es un inventario simple de figuras/tablas sin verificación cruzada de KPIs; la v2 añade explícitamente un "Mapa KPI → fuente", detección de desactualización frente al freeze, verificación puntual de disponibilidad de flota, y la advertencia metodológica sobre `load_factor`. La v2 es estrictamente más completa y más reciente. Decisión pendiente: archivar o eliminar la v1 para evitar que se cite por error una versión sin las advertencias metodológicas de la v2 (en particular, la v1 no contiene la advertencia de que `load_factor` es inválido como KPI).

4. **`revision_modelado/` (paquete de auditoría externa, creado 2026-07-18 18:11) vs. estado vigente del código y métricas (2026-07-20 15:30)**: el paquete enviado a revisión ("codex") documenta la corrida `baselines_full_20260718` con partición temporal *sin* alinear a días operativos completos. El código vivo en `src/proyecto_grado/modeling/` ya difiere línea por línea de `revision_modelado/src/proyecto_grado/modeling/*` (confirmado con `diff -rq`: los 8 módulos .py difieren) y las métricas de test final cambiaron (ver §4, ej. MAE de `historical_average_route_day_type_slot` ruta 1: 36.082 → 35.643). Decisión pendiente: si la revisión externa ya fue entregada con las cifras del 18 de julio, el autor debe decidir si reenvía una versión actualizada o aclara explícitamente en la tesis cuál conjunto de cifras es el definitivo.

5. **Series temporales de `features/` (`data/processed/time_series/ts_ruta{1,3}_g30min.parquet`, hasta 2026-05-03) vs. datasets de modelado (`data/processed/modeling/*.parquet`, hasta 2026-06-10)**: ambos se derivan en última instancia del mismo pipeline pero fueron generados en momentos distintos con datos de distinto alcance temporal. No deben mezclarse en el mismo capítulo de la tesis sin aclarar la fecha de corte de cada uno.

6. **Backups duplicados del mismo día** (`backups/modeling_refactor_20260720_141525/` a las 14:15 y `backups/modeling_full_days_20260720_152008/` a las 15:20): ambos son snapshots completos de `configs/scripts/src/tests` hechos por el autor en la misma sesión de trabajo, separados por ~1 hora. Sugieren al menos dos iteraciones de refactor no comprometidas a git en el mismo día. Decisión pendiente: cuál (si alguna) de las dos versiones intermedias debe conservarse fuera de git, o si ambas pueden descartarse una vez comprometido el estado final a git (tarea 1 de §6).

## 8. Anexo: tabla de trazabilidad

| Indicador | Valor | Archivo fuente | Fecha (mtime) |
|---|---|---|---|
| Filas raw históricas | 109 720 | `data/raw/despachos_raw_historico.csv` | 2026-06-10 19:21 |
| Filas model-ready (freeze vigente) | 109 559 | `data/processed/model_ready/despachos_model_ready_freeze_20260610_192142.parquet` | 2026-06-10 19:21 |
| Columnas model-ready | 18 | `reports/tables/etl/model_ready_metadata_20260610_192142.json` | 2026-06-10 19:21 |
| FIN_TIPO=COMPLETO | 94 400 (86.2%) | `model_ready_metadata_20260610_192142.json` | 2026-06-10 19:21 |
| Retención raw→model_ready (versión desactualizada) | 99.85% (104 803→104 650) | `reports/tables/eda/retention_summary.csv` | sin fecha explícita en el CSV; anterior al freeze vigente |
| CV headway ruta 1 / ruta 3 | 0.722 / 0.774 | `reports/tables/baseline/headway_summary.csv` | 2026-06-08 17:28 |
| Bunching ruta 1 / ruta 3 | 3.82% / 4.71% | `headway_summary.csv` | 2026-06-08 17:28 |
| % patio vacío pico mañana | 34.1% | `reports/tables/baseline/fleet_availability_summary.csv` | 2026-07-02 19:38 |
| Contracción vehículos activos | 63.0 → 42.0 (−33.3%) | `reports/tables/baseline/diagnostico_flota_comparacion.csv` | 2026-06-23 10:49 |
| Contracción pasajeros totales | 247 688 → 145 868 (−41.1%) | `diagnostico_flota_comparacion.csv` | 2026-06-23 10:49 |
| Productividad media ruta 1 / ruta 3 | 44.4 / 48.5 pas/desp | `reports/tables/baseline/productivity_summary.csv` | 2026-06-23 10:40 |
| Granularidad de modelado | 30 min | `configs/modeling/targets.yaml` | untracked, presente en working tree al 2026-07-20 |
| Folds de validación | 38 | `models/metadata/modeling_multitarget_full_days_20260720_1530.json` | 2026-07-20 15:30 |
| Test final (corregido, días completos) | 2026-04-02 04:00 → 2026-06-10 04:00 (69 días) | `reports/tables/modeling/reporte_alineacion_dias_completos.md` | 2026-07-20 15:37 |
| MAE test final, historical_average, ruta 1 (corregido) | 35.643 | `reports/tables/modeling/comparacion_splits_dias_completos.md` §J | 2026-07-20 15:37 |
| MAE test final, historical_average, ruta 1 (previo, pre-alineación) | 36.082 | `revision_modelado/informe_codex.txt` §G | 2026-07-18 18:11 |
| Tests pytest suite completa | 134 passed, 0 failed, 8 warnings | Ejecución directa `uv run python -m pytest tests -q` (esta auditoría) | 2026-07-20 (hora de la auditoría) |
| Modelos de modelado avanzado (XGBoost, LSTM, etc.) | 0 implementados | `src/proyecto_grado/modeling/`, `src/proyecto_grado/models/{ml,dl}/__init__.py` (vacíos) | 2026-07-20 |
| Figuras PNG persistidas (EDA/operativas) | 61 | `reports/inventario_diagnostico_v2.md` | 2026-07-05 11:21 |
| Figuras PNG de modelado | 5 | Listado directo `reports/figures/modeling/` | 2026-07-20 (mtimes de la corrida `baselines_full_20260718`, sin re-verificar contra `full_days_20260720_1530`) |
