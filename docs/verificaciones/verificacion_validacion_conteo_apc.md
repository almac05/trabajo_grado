# Verificación: validación del conteo automático de pasajeros (APC)

Verificación de solo lectura. No se modificó ningún script, configuración ni
artefacto del proyecto. Todos los conteos se recalcularon directamente contra
los parquet/CSV existentes con `.venv/Scripts/python.exe`.

## 1. Dónde se aplica la validación del conteo APC

La corrección vive en **`src/proyecto_grado/etl/transforms.py`**, función
`run_block4` (líneas 14-43), específicamente líneas 31-36:

```python
# PASAJEROS_REALES
despachos["ALARMAS"] = (
    pd.to_numeric(despachos["ALARMAS"], errors="coerce").fillna(0).astype(int)
)
despachos["PASAJEROS"] = pd.to_numeric(despachos["PASAJEROS"], errors="coerce")
despachos["PASAJEROS_REALES"] = (despachos["PASAJEROS"] - despachos["ALARMAS"]).clip(lower=0)
```

`ALARMAS` no es un umbral heurístico: es un conteo de eventos de alarma del
dispositivo, unido desde la base de origen en
**`src/proyecto_grado/etl/extract.py`**, líneas 63-70:

```sql
LEFT JOIN (
    SELECT FK_INFORMACION_REGISTRADORA, SUM(CANTIDAD_ALARMA) AS ALARMAS
    FROM tbl_alarma_info_regis
    WHERE FK_ALARMA IN ('5', '6')
    GROUP BY FK_INFORMACION_REGISTRADORA
) AS alarmas
ON ta.PK_INFORMACION_REGISTRADORA = alarmas.FK_INFORMACION_REGISTRADORA
```

**Criterio exacto:** los eventos con `FK_ALARMA IN ('5','6')` en
`tbl_alarma_info_regis` (apertura de puerta delantera/trasera, según
`models/metadata/correccion_sesgo_apc_20260823.json:4` — "eventos de puerta
delantera/trasera (FK_ALARMA 5 y 6...) contados erroneamente como abordajes")
se suman por despacho como `ALARMAS` y se restan del conteo crudo `PASAJEROS`,
con piso en 0, para producir `PASAJEROS_REALES` — la variable objetivo
adoptada (`configs/features.yaml:40` → `columna_pasajeros: PASAJEROS_REALES`;
`configs/modeling/targets.yaml`).

**Esto es una corrección de valor, no un filtro de exclusión de registros**:
ningún registro se descarta en este paso.

Existe además un mecanismo distinto y **blando** en
**`src/proyecto_grado/etl/qc.py`**, función
`validar_coherencia_operacional_avanzada` (líneas 173-203): la bandera
estadística `flag_pasajeros_absurdos`, calculada por ruta sobre el percentil
`pasajeros_pctl_soft` (por defecto **99.5**, `src/proyecto_grado/etl/config.py:80`,
sobreescribible en `configs/etl.yaml:69`), más un umbral duro opcional
`pasajeros_max_hard` (`config.py:81`) que actualmente está **desactivado**
(`null` en `configs/etl.yaml:72`). Esta bandera es blanda (`SOFT_FAILS`,
`qc.py:36-41`) y **no excluye** registros de `model_ready` ni del dataset de
modelado; solo las banderas `qc_hard_fail` (estructurales: PK nula, PK
duplicada, placa nula, horas nulas/invertidas, duración/distancia/pasajeros
negativos — `HARD_FAILS`, `qc.py:25-34`) excluyen registros, vía
`MODEL_READY_OK` en `src/proyecto_grado/etl/model_ready.py:77-79`.

**Umbrales relevantes:**

| Umbral | Valor | Fuente | Efecto |
|---|---|---|---|
| `pasajeros_pctl_soft` | 99.5 (percentil, por ruta) | `etl/config.py:80` | Bandera blanda `flag_pasajeros_absurdos`, no excluye |
| `pasajeros_max_hard` | `null` (desactivado) | `configs/etl.yaml:72` | Sin efecto actualmente |
| Criterio de alarma | `FK_ALARMA IN ('5','6')` | `extract.py:65-70` | Corrige `PASAJEROS_REALES`, no excluye |

## 2. Cuántos registros excluye / afecta ese criterio

**La corrección ALARMAS→PASAJEROS_REALES no excluye ningún registro; los
corrige.** Verificado contra
`data/processed/model_ready/despachos_model_ready_freeze_20260823_203700.parquet`
y contra `models/metadata/correccion_sesgo_apc_20260823.json` (líneas 12-16,
40-44):

- **8,938 de 109,559** despachos model-ready (8.16%) tienen
  `PASAJEROS_REALES ≠ PASAJEROS`.
- Se dividen 45.0% / 55.0% entre ruta 1 / ruta 3 (**4,025** / **4,913**
  registros respectivamente) — coincide exactamente con el metadato
  persistido.
- 3 registros quedan con `PASAJEROS_REALES == 0` tras el recorte en 0.

Ejemplos representativos (fecha, ruta, PASAJEROS → PASAJEROS_REALES, alarmas):

| Fecha | Ruta | PASAJEROS | ALARMAS | PASAJEROS_REALES |
|---|---|---|---|---|
| 2024-05-31 (PK 252998) | 3 | 868 | 874 | 0 (caso extremo, mayor magnitud) |
| 2024-05-17 | 1 | 261 | — | 43 |
| 2025-03-01 | 3 | 285 | — | 78 |
| 2024-05-20 | 1 | 247 | — | 51 |
| 2025-04-14 | 1 | 317 | — | 129 |

El caso PK 252998 (ruta 3, 2024-05-31) es señalado en el propio metadato como
"revisar si corresponde a un despacho con falla de dispositivo" (alarmas=874,
el máximo observado).

**Registros que sí se excluyen (mecanismo distinto, no es la corrección
ALARMAS):**

- `qc_hard_fail`: **14** registros (`reports/tables/qc/qc_resumen.csv`,
  fila `qc_hard_fail,14,0.01275...`) — excluidos vía `MODEL_READY_OK`.
- La caída total entre etapas `quality_checked`/`trip_end_resolved`
  (109,720 filas) y `model_ready` (109,559 filas) es de 161 filas, producto
  de `qc_hard_fail` más los filtros de completitud de duración/timestamp en
  `model_ready.py:71-79`.
- `flag_pasajeros_absurdos` (blanda, percentil 99.5): **521** registros
  marcados (`reports/tables/qc/qc_resumen.csv`), pero **no removidos** del
  pipeline.

## 3. Máximo de pasajeros por franja de 30 minutos

Calculado directamente sobre
`data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet`
(43,831 filas).

**(a) Serie completa, por ruta:**

| FK_RUTA | timestamp | pasajeros_total |
|---|---|---|
| 1 | 2024-08-28 15:00:00 | 464.0 |
| 3 | 2026-04-22 06:00:00 | 519.0 |

**(b) Período de evaluación del freeze (2026-04-02 a 2026-06-10 inclusive,
según `configs/modeling/evaluacion_comparativa.yaml:11-13`; 3,885 filas en la
ventana):**

| FK_RUTA | timestamp | pasajeros_total |
|---|---|---|
| 1 | 2026-06-05 13:30:00 | 270.0 |
| 3 | 2026-04-22 06:00:00 | 519.0 |

El máximo global y el máximo del período de evaluación de la ruta 3
coinciden (2026-04-22 06:00:00 cae dentro de la ventana de evaluación). Este
valor (519, ruta 3, 2026-04-22 06:00:00) coincide con la fila "corregida" de
`analisis/salidas/comparacion_atipico_apc.csv` (despachos=8, alarmas=6).

## 4. ¿El número de alarmas del dispositivo está disponible como variable?

**Sí, como columna `ALARMAS`** (entero, suma de `CANTIDAD_ALARMA` para
`FK_ALARMA IN ('5','6')` por despacho).

- **Aparece en:** el SQL de extracción (`extract.py:33,65-70`) y se conserva
  explícitamente en las etapas QC / resolución de fin de viaje / model-ready
  — retenida en `model_ready.py`, `cols_keep` (línea 97), "para
  trazabilidad" según el comentario en las líneas 89-94.
- **Se usa** en `transforms.py:32-36` para calcular `PASAJEROS_REALES`.
- **Se descarta antes del dataset de modelado**: `ALARMAS` **no** es columna
  de `modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (verificado
  contra la lista completa de columnas). Se pierde en la agregación a bins de
  30 minutos en `src/proyecto_grado/features/time_series_builder.py`, que
  agrega `columna_pasajeros = "PASAJEROS_REALES"` (línea 36) pero no tiene
  agregación equivalente para `ALARMAS`.

Es decir: `ALARMAS` sobrevive hasta `model_ready` pero se pierde en la etapa
de agregación a series de tiempo, y no llega a la tabla de modelado.

**Nota aparte:** el CSV crudo en disco
(`data/raw/despachos_raw_historico.csv`) contiene actualmente una columna
`PASAJEROS_REALES`, pero el SQL/`guardar_csv` de `extract.py` (línea 110) no
la calcula — solo une `ALARMAS`. Esa columna en el CSV crudo actual parece
residual de una escritura previa distinta y no la produce la ruta de código
de extracción vigente.

## 5. ¿Es esta validación una de las cuatro etapas de la tabla de registros conservados?

**No.** La tabla de cuatro etapas persistida es
**`reports/tables/eda/dataset_overview.csv`** (esquema
`stage,available,rows,columns`; generada por
`src/proyecto_grado/analytics/etl_diagnostics.py::dataset_overview`, líneas
45-64):

```
stage,available,rows,columns
raw,True,109720,17
quality_checked,True,109720,40
trip_end_resolved,True,109720,44
model_ready,True,109559,20
```

Las cuatro etapas nombradas son **raw → quality_checked →
trip_end_resolved → model_ready**, mapeadas a `DESPACHOS_CSV` (raw),
`despachos_qc.parquet` (quality_checked), `despachos_end.parquet`
(trip_end_resolved) y `despachos_model_ready.parquet` (model_ready) —
`DatasetPaths`, `etl_diagnostics.py:14-19`.

**La corrección ALARMAS/PASAJEROS_REALES (pregunta 1) no es una de esas
cuatro etapas** y no es un paso de retención de filas. Según el orquestador
**`src/proyecto_grado/etl/pipeline.py`** (líneas 67-75):

```python
despachos = run_block3()            # -> snapshot "raw" se escribe aquí
despachos = run_block4(despachos)   # <- correccion ALARMAS ocurre AQUI, en memoria
...
despachos = run_block5(despachos)
run_block6(despachos)               # -> etapa "quality_checked"
run_block7()                        # -> etapa "trip_end_resolved"
run_block8()                        # -> etapa "model_ready" (descarta solo qc_hard_fail)
run_block9()
```

`run_block4` se ejecuta estrictamente entre el snapshot `raw` persistido
(escrito dentro de `run_block3`/`extract.py:110`, antes de que exista
`PASAJEROS_REALES`) y la etapa `quality_checked` (`run_block6`). Es un paso
de transformación de valor que alimenta `quality_checked` y todo lo
posterior, no una etapa distinta del embudo, y no descarta ningún registro
— la exclusión de registros en el embudo la determina únicamente
`qc_hard_fail` (banderas estructurales), aplicado después en
`model_ready.py:77-79`.

## Archivos clave para trazabilidad

- `src/proyecto_grado/etl/transforms.py:14-43` (`run_block4`, fórmula de PASAJEROS_REALES)
- `src/proyecto_grado/etl/extract.py:26-73,110` (join SQL de ALARMAS, punto de escritura del CSV raw)
- `src/proyecto_grado/etl/qc.py:25-41,173-203,300-411` (banderas duras/blandas, pasajeros_absurdos)
- `src/proyecto_grado/etl/config.py:77-85` (umbrales de QC_CONFIG)
- `configs/etl.yaml:62-76` (overrides de qc, todos en null/default)
- `src/proyecto_grado/etl/model_ready.py:71-110` (filtro MODEL_READY_OK)
- `src/proyecto_grado/analytics/etl_diagnostics.py:14-64` (definición de la tabla de cuatro etapas)
- `reports/tables/eda/dataset_overview.csv`, `reports/tables/qc/qc_resumen.csv`
- `models/metadata/correccion_sesgo_apc_20260823.json`
- `analisis/salidas/comparacion_atipico_apc.csv`
- `configs/features.yaml:40`, `configs/modeling/targets.yaml`, `configs/modeling/evaluacion_comparativa.yaml:9-14`
- `data/processed/model_ready/despachos_model_ready_freeze_20260823_203700.parquet`,
  `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet`
  (cálculos verificados directamente con `.venv/Scripts/python.exe`)
