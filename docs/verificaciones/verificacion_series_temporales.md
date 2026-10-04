# Verificación: construcción de series temporales, jornada operativa, tipo_dia y regularidad de despacho

Verificación de solo lectura (no se modificó código). Fuentes citadas con ruta y número de línea.

---

## 1. Columna temporal usada para asignar cada despacho a una franja de 30 min, e imputación de pasajeros

Archivo: [src/proyecto_grado/features/time_series_builder.py](src/proyecto_grado/features/time_series_builder.py)

- La columna usada es `HORA_INICIAL_REAL` (hora de salida real del despacho), no `HORA_FIN_FINAL` ni la hora de llegada.
- La asignación a la franja se hace con un truncamiento hacia abajo (floor), no con redondeo ni con una regla de reparto:

```python
# líneas 122-125
freq = f"{granularidad_min}min"
col = self.columna_pasajeros
df = df.copy()
df["_ts_bin"] = df["HORA_INICIAL_REAL"].dt.floor(freq)
```

- Los pasajeros del viaje completo **se imputan íntegramente a una sola franja** — la franja de 30 min en la que cae la hora de salida (`HORA_INICIAL_REAL`) truncada hacia abajo. No hay distribución/prorrateo del volumen de pasajeros entre franjas según duración del recorrido:

```python
# líneas 127-137
agg = (
    df.groupby("_ts_bin", sort=True)
    .agg(
        pasajeros_total=(col, "sum"),
        despachos_count=("PK_INTERVALO_DESPACHO", "count"),
        pasajeros_promedio=(col, "mean"),
        ocupacion_p95=(col, lambda x: float(np.percentile(x.to_numpy(), 95))),
    )
    ...
)
```

- Implicación: un despacho que sale a las 07:58 y termina su recorrido a las 08:40 aporta la totalidad de sus pasajeros (columna `PASAJEROS_REALES` por defecto, ver `_DEFAULTS["columna_pasajeros"]`, línea 36) a la franja `07:30–08:00`, no a la franja en que ocurre la mayor parte del recorrido ni distribuido entre ambas.

---

## 2. Definición de "jornada operativa" en el código y coincidencia con 04:00–04:00

Hay **dos conceptos distintos** en el código que conviene no confundir:

### 2a. Horario operativo empírico (`operational_hours.py`)

Archivo: [src/proyecto_grado/features/operational_hours.py](src/proyecto_grado/features/operational_hours.py)

`OperationalHoursEstimator` **no asume** un horario fijo 04:00–04:00. Estima, por cada combinación `tipo_dia x ruta x granularidad_min`, el rango horario real de operación a partir de la franja con actividad histórica (umbral `umbral_actividad`, por defecto 0.10; líneas 28-33, 196-230). El resultado (`hora_inicio_op`, `hora_fin_op`) varía por ruta y tipo de día — no está anclado a 04:00.

Este horario estimado es el que consume `time_series_builder.py::_enriquecer_con_horario_operativo` (líneas 229-290) para marcar `dentro_horario_operativo` y clasificar gaps como `gap_anomalo` vs `fuera_operacion`. Es decir: en la construcción de la serie temporal, la "jornada operativa" es empírica y variable, no un intervalo fijo de 24h desplazado.

### 2b. Día operativo fijo 04:00–04:00 (`splits.py`)

Archivo: [src/proyecto_grado/modeling/splits.py](src/proyecto_grado/modeling/splits.py)

Aquí sí existe un límite de día operativo **fijo y configurable, con default 04:00:00**:

```python
# línea 10
DEFAULT_OPERATIONAL_DAY_START = "04:00:00"
```

Se usa exclusivamente para alinear los límites de train/validation/test a días operativos completos (`align_start_to_operational_day`, `align_end_to_operational_day`, `operational_day_label`, `align_to_full_operational_days`, líneas 74-194) — es decir, para que un split no corte un día por la mitad. Un "día operativo" aquí va de 04:00 de un día calendario a 04:00 del día siguiente (04:00 → 04:00), confirmado por el uso documentado en `docs/ESTADO_DEL_PROYECTO.md:215`: *"Test final corregido: 2026-04-02 04:00:00 → 2026-06-10 04:00:00"*.

**Conclusión punto 2**: el intervalo fijo 04:00–04:00 sí existe en el código, pero **solo en `splits.py`**, como convención para no partir días en los folds de evaluación — no es la definición de jornada operativa que usa `time_series_builder.py`/`operational_hours.py` para calcular franjas activas o gaps, que es empírica y varía por ruta/tipo de día.

---

## 3. Construcción de `tipo_dia`, fuente del calendario y criterio de `FESTIVO_PUENTE`

Archivo: [src/proyecto_grado/features/time_series_builder.py](src/proyecto_grado/features/time_series_builder.py), método `_enriquecer` (líneas 184-227).

### Fuente de calendario
Usa la librería de terceros `holidays` (import línea 8), específicamente `holidays.Colombia(years=year)` (línea 95), cacheada por año en `self._colombia_holidays`. No hay un archivo propio de festivos en el repo para esto — depende de esa librería externa.

### Construcción de `tipo_dia`

```python
# líneas 216-225
conditions = [
    agg["es_festivo"] & (agg["dia_semana"] == 0),
    agg["es_festivo"],
    agg["dia_semana"] == 5,
    agg["dia_semana"] == 6,
]
choices = ["FESTIVO_PUENTE", "FESTIVO", "SABADO", "DOMINGO"]
agg["tipo_dia"] = np.select(conditions, choices, default="LABORAL")
```

Prioridad: `FESTIVO_PUENTE` > `FESTIVO` > `SABADO` > `DOMINGO` > `LABORAL`.

### Criterio exacto de `FESTIVO_PUENTE`
`es_festivo AND dia_semana == 0` (lunes), donde `es_festivo` proviene de `holidays.Colombia`.

**Verificación adicional (ejecución de la librería, no solo lectura de código)**: se instanció `holidays.Colombia(years=2024)` para confirmar el comportamiento real. La librería **ya aplica internamente** la Ley Emiliani (traslado de festivos no inamovibles al lunes siguiente) y marca esos casos como "(observado)". Para 2024, 11 de 18 festivos caen en lunes, incluyendo el 1 de enero de 2024 (que cae en lunes por coincidencia calendario, no por traslado de ley).

Consecuencia importante: el código **no distingue** entre "festivo trasladado al lunes por la Ley Emiliani" y "festivo que simplemente cae en lunes" (como el Año Nuevo en años en que el 1 de enero coincide con lunes). El criterio `FESTIVO_PUENTE` del código es puramente "festivo (según la librería) que cae en lunes", sin importar el motivo. El comentario en el código (línea 217: `# FESTIVO_PUENTE: lunes festivo colombiano (Ley Emiliani)`) sugiere que la intención es capturar los puentes por Ley Emiliani, pero la implementación real captura cualquier festivo en lunes.

---

## 4. Reproducibilidad de los percentiles 95 de 24.17 y 24.7 min en la tabla de regularidad del intervalo de despacho

**Sí se localizó el artefacto exacto, pero corresponde a una versión anterior/no corregida, no a la tabla vigente citada.**

### Módulo que calcula el indicador
Archivo: [src/proyecto_grado/analytics/headway.py](src/proyecto_grado/analytics/headway.py), clase `HeadwayAnalyzer`, método `_stats` (líneas 92-106):

```python
"headway_p95": round(series.quantile(0.95), 2),
```

`headway_min` se calcula como la diferencia en minutos entre salidas consecutivas de la misma ruta y mismo día (`HORA_INICIAL_REAL`, líneas 76-81), filtrando despachos con `HORA_INICIO_H` entre 4 y 19 (`HORA_OP_INICIO=4`, `HORA_OP_FIN=19`, líneas 32-33) y con `headway_min` entre 0.1 y 120 minutos (línea 83).

### Dónde aparecen los valores citados
`docs/ESTADO_DEL_PROYECTO.md:158` cita textualmente:
> Ruta 1: cv=0.722, media=10.97 min, p95=24.17 min; Ruta 3: cv=0.774, media=10.56 min, p95=24.70 min — fuente `reports/tables/baseline/headway_summary.csv`, fecha (mtime) 2026-06-08 17:28.

Al leer los dos artefactos `headway_summary.csv` presentes en el repo:

| Archivo | Ruta 1 p95 | Ruta 3 p95 | cv Ruta 1 | cv Ruta 3 |
|---|---|---|---|---|
| `reports/tables/baseline_v1_sin_corregir/headway_summary.csv` | **24.17** | **24.7** | 0.722 | 0.774 |
| `reports/tables/baseline/headway_summary.csv` (vigente) | 24.32 | 24.92 | 0.726 | 0.777 |

**Hallazgo**: los valores 24.17/24.7 (y el resto de cifras citadas: cv=0.722/0.774, media=10.97/10.56) coinciden exactamente con `reports/tables/baseline_v1_sin_corregir/headway_summary.csv`, **no** con el archivo vigente en `reports/tables/baseline/headway_summary.csv` (que hoy contiene 24.32/24.92). Esto indica que:

1. El cálculo **sí es reproducible** desde código (`HeadwayAnalyzer` en `headway.py`) y los números no están inventados.
2. Pero la cita en `docs/ESTADO_DEL_PROYECTO.md` quedó **desactualizada**: el archivo `reports/tables/baseline/headway_summary.csv` fue regenerado después del 2026-06-08 (probablemente por el cambio de variable objetivo a `PASAJEROS_REALES`, commit `e6115bf`, u otro ajuste posterior en el pipeline de extracción/model-ready) y ya no reproduce esas cifras. La tabla "sin_corregir" (nombre que sugiere una versión pre-corrección) es la que efectivamente contiene 24.17/24.7.
3. Cualquier texto del informe que cite "p95=24.17 min (ruta 1) / 24.7 min (ruta 3)" como cifra vigente debe verificarse contra `reports/tables/baseline/headway_summary.csv` actual (24.32/24.92) o aclarar explícitamente que corresponde a la corrida `baseline_v1_sin_corregir`.

---

## Resumen de hallazgos accionables

1. **Sin distribución de pasajeros entre franjas**: confirmado, la imputación es 100% a la franja de salida (floor de `HORA_INICIAL_REAL`).
2. **04:00–04:00 no es la "jornada operativa" de la serie temporal**: es un límite de alineación de splits en `splits.py`; el horario operativo real usado en `time_series_builder.py` es empírico y variable por ruta/tipo_dia (`operational_hours.py`).
3. **`FESTIVO_PUENTE` = festivo (librería `holidays`) que cae en lunes**, sin distinguir si el festivo fue trasladado por Ley Emiliani o coincide con lunes de forma natural — posible discrepancia entre el comentario del código y su comportamiento real.
4. **Los percentiles 24.17/24.7 son reproducibles pero desde un artefacto distinto al vigente** (`baseline_v1_sin_corregir` vs `baseline`); la documentación que los cita como estado actual está desactualizada.
