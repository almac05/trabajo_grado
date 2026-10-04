# Verificación de artefactos vigentes vs. cifras del documento

Verificación de solo lectura sobre los CSV/artefactos actualmente presentes en el repositorio. Única excepción: se ejecutó `scripts/build_rotacion.py` (bloque 3) porque es un script de verificación que su propio docstring describe como reproductor de la Tabla 10 — no cambia datos de entrada y regeneró `rotacion_vehiculos.csv` con **valores idénticos** a los ya presentes (confirmado por lectura previa). Ningún otro archivo fue modificado ni regenerado.

---

## 1. Tabla de regularidad del intervalo de despacho (headway)

Fuente: `reports/tables/baseline/headway_summary.csv` — **mtime 2026-08-30 17:11**.
Módulo: [src/proyecto_grado/analytics/headway.py](src/proyecto_grado/analytics/headway.py)

| Métrica | Ruta 1 (vigente) | Ruta 1 (documento) | Ruta 3 (vigente) | Ruta 3 (documento) |
|---|---|---|---|---|
| media (min) | 11.07 | 10.97 | 10.65 | 10.56 |
| desviación std | 8.04 | 7.92 | 8.27 | 8.17 |
| cv (std/media) | 0.726 | 0.722 | 0.777 | 0.774 |
| mediana (p50) | 9.23 | 9.15 | 8.65 | 8.58 |
| p95 | **24.32** | **24.17** | **24.92** | **24.7** |
| bunching (%) | 3.84 | 3.82 | 4.75 | 4.71 |
| espera excesiva (%) | 2.86 | 2.79 | 3.18 | 3.09 |

**Ninguna de las ocho cifras por ruta coincide exactamente** con las del documento. La desviación es sistemática y pequeña (entre +0.10 y +0.22 en las métricas de tiempo, +0.003–0.004 en cv, +0.02–0.09 puntos porcentuales en bunching/espera), lo que indica que ambas tablas provienen del **mismo cálculo pero sobre universos de datos ligeramente distintos** (probablemente conteos de despachos distintos por una actualización posterior del dataset model-ready), no de una fórmula diferente.

### Criterio de bunching y espera excesiva
Definidos en [headway.py:32-35](src/proyecto_grado/analytics/headway.py) y aplicados en `_stats` (líneas 92-106):
- **Bunching** = % de intervalos (`headway_min`) con valor `< 3 min` (`BUNCHING_MIN = 3`).
- **Espera excesiva** = % de intervalos con valor `> 30 min` (`EXCESO_MIN = 30`).
- El universo de intervalos se restringe a despachos con `MODEL_READY_OK == True`, `HORA_INICIO_H` entre 4 y 19 (horario operativo 04h–19h), y `headway_min` en el rango `[0.1, 120]` minutos (se descartan valores fuera de ese rango antes de calcular las estadísticas, línea 83).

### Nota sobre el artefacto "sin_corregir"
Existe además `reports/tables/baseline_v1_sin_corregir/headway_summary.csv`, cuyos valores (Ruta 1: p95=24.17, cv=0.722, media=10.97; Ruta 3: p95=24.7, cv=0.774, media=10.56) **sí coinciden exactamente, cifra por cifra**, con las que hoy figuran en el documento. Es decir: **el documento cita la corrida "sin_corregir", no la vigente en `reports/tables/baseline/`.**

---

## 2. Disponibilidad de flota e intervalos largos

Fuente: `reports/tables/baseline/fleet_availability_summary.csv` — **mtime 2026-07-02 19:38**.
Módulo: [src/proyecto_grado/analytics/fleet_availability.py](src/proyecto_grado/analytics/fleet_availability.py), invocado por `scripts/build_fleet_availability.py`.

| Métrica | Vigente | Documento |
|---|---|---|
| n_dias_analizados | 30 | 30 |
| pct_largos_pico_manana | 19.5% | 19.5% |
| pct_largos_pico_tarde | 15.7% | 15.7% |
| pct_largos_cierre | 14.3% | 14.3% |
| pct_largos_otros | 50.6% | 50.6% |
| pct_vacio_pico_manana | 34.1% | 34.1% |

**Las seis cifras coinciden exactamente.** También se verificó la cobertura de meses: `fleet_availability_by_day.csv` contiene 30 fechas que caen en **21 meses calendario distintos** dentro de un rango total de **27 meses** (2024-04 a 2026-06 inclusive) — coincide con "21 de 27 meses" citado en el documento.

### Criterio de selección de los 30 días
`FleetAvailabilityAnalyzer._seleccionar_dias_laborales` (líneas 67-71): días laborales (`dia_semana < 5`) con al menos 150 despachos ese día. Sobre ese universo de días válidos, `run(n_dias=30)` (líneas 159-193) toma una **muestra espaciada uniformemente** con `np.linspace(0, len(dias)-1, n_dias)` redondeado a enteros — **no es una muestra aleatoria**. `scripts/build_fleet_availability.py` acepta `--n-dias` por línea de comandos (default 15); el archivo vigente corresponde a una corrida con `--n-dias 30`.

**Reproducibilidad**: sí, es determinista — `np.linspace` no usa semilla aleatoria. Dado el mismo `despachos_model_ready.parquet` y el mismo `--n-dias`, el resultado es idéntico en cualquier ejecución.

---

## 3. Rotación de vehículos

Fuente: `reports/tables/baseline/rotacion_vehiculos.csv` (regenerado en esta verificación, valores idénticos a los preexistentes).
Módulo/script: [scripts/build_rotacion.py](scripts/build_rotacion.py).

| Métrica | Ruta 1 (vigente) | Ruta 1 (documento) | Ruta 3 (vigente) | Ruta 3 (documento) |
|---|---|---|---|---|
| mediana rotación (min) | 23.1 | 23.1 | 23.9 | 23.9 |
| IQR (p25–p75) | 15.4–33.3 | 15.4–33.3 | 15.8–35.0 | 15.8–35.0 |
| ciclo mediana (min) | 181.9 | 181.9 | 177.3 | 177.3 |

Estas cifras corresponden a la variante **"misma jornada operativa"** del script (idéntica a la variante "horario y misma jornada"), no a "todos los intervalos" ni a "horario operativo 4h-19h" — el script calcula cuatro variantes y esta es la que reproduce el documento exactamente.

**Proporción de intervalos que cruzan el cierre de jornada**: al ejecutar el script se obtiene **27.5%** (30,115 de 109,492 intervalos con `rotacion_min` válido), calculado **de forma conjunta para ambas rutas** (el script no lo desglosa por ruta) — coincide con el "27.5% en ambas rutas" del documento, entendido como una única cifra global aplicable a ambas, no dos cifras independientes.

**Nota relevante encontrada en el propio script** (líneas 43-48): el script incluye un diccionario `PUBLICADO` con los valores que, según su comentario, fueron "reportados en la Tabla 10 [...] calculados sobre el conjunto de datos previo a la corrección del sesgo de conteo": mediana 27.5/26.9, p25 15.3/13.9, p75 119.8/146.6, ciclo 347/337 para rutas 1/3. **Estos valores no coinciden con los que el usuario cita como vigentes en el documento** (23.1/23.9, etc.), lo que indica que el texto del documento fue actualizado en algún punto para reflejar el dataset corregido (`PASAJEROS_REALES`) y ya no corresponde al valor `PUBLICADO` originalmente embebido como referencia de contraste en este script.

---

## 4. Contracción de la flota y productividad

### Comparación mayo 2024 vs. mayo 2026
Fuente: `reports/tables/baseline/diagnostico_flota_comparacion.csv` — **mtime 2026-08-31 09:07**.
Script: [scripts/diagnostico_reduccion_flota.py](scripts/diagnostico_reduccion_flota.py) (primer/último mes **completo** del dataset, excluyendo el primero y el último mes parciales — resultan ser mayo 2024 y mayo 2026).

| Indicador | Mayo 2024 | Mayo 2026 | Variación |
|---|---|---|---|
| Vehículos activos | 63 | 42 | −33.3% |
| Despachos totales | 5 266 | 3 179 | −39.6% |
| Pasajeros totales | 244 458 | 145 287 | −40.6% |
| Productividad (pas/despacho) | 46.42 | 45.70 | −1.6% |
| Despachos por vehículo | 83.59 | 75.69 | −9.5% |

### ⚠️ Base de cálculo: conteo depurado, no bruto — y con una discrepancia entre el script versionado y el vigente
Se verificó explícitamente ejecutando ambas variantes sobre `despachos_model_ready.parquet` (solo lectura, sin escribir salidas):

- Con `PASAJEROS_REALES` (depurado): pasajeros mayo 2024 = **244 458**, mayo 2026 = **145 287** → coincide exactamente con el CSV vigente.
- Con `PASAJEROS` (bruto): pasajeros mayo 2024 = 247 688, mayo 2026 = 145 868 → **no** coincide con el CSV.

Conclusión: **el archivo vigente fue calculado sobre el conteo depurado (`PASAJEROS_REALES`)**, no sobre el bruto.

Sin embargo, `git diff` sobre `scripts/diagnostico_reduccion_flota.py` muestra que este cambio **no está confirmado (commiteado)** — la versión en el último commit usa `PASAJEROS` (bruto):

```diff
-        despachos_total=("PASAJEROS", "count"),
-        pasajeros_total=("PASAJEROS", "sum"),
+        despachos_total=("PASAJEROS_REALES", "count"),
+        pasajeros_total=("PASAJEROS_REALES", "sum"),
```

Es decir: el CSV en disco refleja la versión **de árbol de trabajo (no comiteada)** del script, con la columna corregida. Dado que la corrección afecta al **8.16% de los despachos** (8 938 de 109 559, según `PASAJEROS_REALES ≠ PASAJEROS`, verificado en `verificacion_validacion_conteo_apc.md`), cualquier regeneración de este CSV a partir del script tal como está comiteado en git produciría cifras de pasajeros distintas (mayores) a las hoy presentes — riesgo de inconsistencia si alguien más regenera el artefacto sin aplicar antes este cambio.

### Productividad media por ruta (semanal, ajustada por tendencia OLS)
Fuente: `reports/tables/baseline/productivity_summary.csv` — **mtime 2026-08-30 16:18**. Módulo: [src/proyecto_grado/analytics/vehicle_productivity.py](src/proyecto_grado/analytics/vehicle_productivity.py), que usa `PASAJEROS_REALES` por defecto (línea 36, con fallback a `PASAJEROS` solo si la columna no existe).

| Métrica | Ruta 1 | Ruta 3 |
|---|---|---|
| n° semanas válidas | 111 | 111 |
| productividad media (bruta) | 44.14 pas/desp | 48.18 pas/desp |
| mediana (p50) | 44.15 | 48.28 |
| desviación estándar | 2.51 | 2.44 |
| pendiente OLS semanal | +0.006 | +0.007 |
| pendiente OLS mensual (≈) | +0.028 | +0.032 |
| variación total del período | +0.71 | +0.82 |

El cálculo se hace sobre **111 semanas** por ruta (se excluyen la primera y la última semana de cada ruta por ser parciales, línea 72-77 de `vehicle_productivity.py`).

---

## 5. Composición del conjunto y perfiles

### Distribución de `FIN_TIPO`
Fuente: `data/processed/model_ready/despachos_model_ready.parquet` — **mtime 2026-08-23 20:36** (109 559 filas, todas con `MODEL_READY_OK=True`).

| Categoría | n | % vigente | % documento |
|---|---|---|---|
| COMPLETO | 94 400 | 86.16% | 86.18% |
| TRUNCADO_RETORNO | 11 988 | 10.94% | 10.93% |
| TRUNCADO_INDETERMINADO | 1 994 | 1.82% | 1.82% |
| TRUNCADO_ABANDONO | 1 152 | 1.05% | 1.05% |
| SIN_GPS | 25 | 0.02% | 0.02% |

Las dos primeras categorías presentan una **discrepancia de 0.01–0.02 puntos porcentuales** (86.16 vs 86.18; 10.94 vs 10.93); las tres restantes coinciden. La diferencia es demasiado pequeña para deberse a un cambio de universo de datos grande; es compatible con redondeo o con una diferencia de un puñado de registros entre el freeze citado en el documento y el archivo `despachos_model_ready.parquet` vigente (que, según el histórico del repositorio, fue regenerado el 2026-08-23, posterior a la fecha del freeze `_20260610_192142` documentado en `docs/ESTADO_DEL_PROYECTO.md`).

### Duración del viaje por ruta
Calculado directamente sobre `DURACION_MIN_FINAL` del mismo parquet (solo lectura):

| Ruta | Media | Mediana | p95 |
|---|---|---|---|
| Ruta 1 | 160.57 min | **157.35 min** | 199.12 min |
| Ruta 3 | 161.53 min | **161.48 min** | 213.07 min |

Las medianas **coinciden exactamente** con las cifras del documento (157.35 y 161.48). El documento no aporta cifras de media ni p95 para contrastar; se reportan aquí como valores vigentes de referencia.

### Máximos del perfil intradía en día laboral
Fuente: `analisis/salidas/cuadro_perfil_horario_laboral.csv` — **mtime 2026-08-17 15:36**, generado por [analisis/14_cuadros_mecanismos.py](analisis/14_cuadros_mecanismos.py) a partir de `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (target `pasajeros_total`, construido con `PASAJEROS_REALES`), filtrando `tipo_dia == "LABORAL"` y franjas con `n >= 100` observaciones.

| Ruta | Hora del máximo (vigente) | Valor (vigente) | Hora (documento) | Valor (documento) |
|---|---|---|---|---|
| Ruta 1 | **15:30** | **193.9** | 15:00 | 191.6 |
| Ruta 3 | 06:00 | **309.4** | 06:00 | 278.1 |

**No coinciden.** Para la Ruta 1 incluso la franja del máximo difiere: el artefacto vigente ubica el pico en 15:30 (193.9), mientras que a las 15:00 el valor vigente es 193.0 — más cercano al 191.6 del documento, pero no exacto, y en cualquier caso 15:00 no es el máximo real de la serie vigente. Para la Ruta 3 la diferencia es mayor (309.4 vs 278.1, +11.3%).

**Causa probable**: `cuadro_perfil_horario_laboral.csv` (17-ago) es **anterior** a su propio archivo fuente `modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (23-ago) — es decir, el CSV está desactualizado respecto al parquet del que se calculó, y muy probablemente respecto a la versión del dataset que existía cuando se redactaron las cifras del documento. No se puede determinar sin regenerar el cuadro si la diferencia se debe únicamente a la actualización del dataset o también a un cambio de la corrección de sesgo APC entre versiones.

---

## 6. Procedencia, fechas y estado de depuración por bloque

| Bloque | Artefacto | mtime | ¿Antes o después de la corrección PASAJEROS→PASAJEROS_REALES? |
|---|---|---|---|
| 1. Headway | `reports/tables/baseline/headway_summary.csv` | 2026-08-30 17:11 | Después (usa `MODEL_READY_OK`/`HORA_INICIAL_REAL`, no depende de la columna de pasajeros — el headway es un cálculo de tiempos entre salidas, no de conteo de pasajeros; el dataset subyacente sí es posterior a la corrección) |
| 1b. Headway "sin_corregir" (coincide con el documento) | `reports/tables/baseline_v1_sin_corregir/headway_summary.csv` | (ver mtime del archivo; corresponde a una corrida anterior) | Corrida previa, con el dataset model-ready anterior a la regeneración de agosto 2026 |
| 2. Disponibilidad de flota | `reports/tables/baseline/fleet_availability_summary.csv` + `fleet_availability_by_day.csv` | 2026-07-02 19:38 | No depende de la columna de pasajeros (mide vehículos en patio) |
| 3. Rotación | `reports/tables/baseline/rotacion_vehiculos.csv` | regenerado hoy, contenido idéntico al preexistente | No depende de la columna de pasajeros (mide tiempos entre despachos por placa) |
| 4. Contracción de flota | `reports/tables/baseline/diagnostico_flota_comparacion.csv` | 2026-08-31 09:07 | **Después** — calculado con `PASAJEROS_REALES`, pero mediante una versión del script **no comiteada** (ver §4) |
| 4. Productividad | `reports/tables/baseline/productivity_summary.csv` | 2026-08-30 16:18 | Después — `ProductivityAnalyzer` usa `PASAJEROS_REALES` por defecto |
| 5. FIN_TIPO / duración | `data/processed/model_ready/despachos_model_ready.parquet` | 2026-08-23 20:36 | Después (freeze posterior al commit `e6115bf` "fix: adoptar PASAJEROS_REALES como variable objetivo") |
| 5. Perfil intradía | `analisis/salidas/cuadro_perfil_horario_laboral.csv` | 2026-08-17 15:36 | Después de la corrección conceptualmente (usa `pasajeros_total` del dataset de modelado, que ya usa `PASAJEROS_REALES`), pero **generado antes** de la última regeneración del parquet fuente (23-ago) — artefacto desactualizado respecto a su propia fuente |

### Cifras del documento que NO coinciden con el artefacto vigente

1. **Headway p95, ruta 1**: documento 24.17 vs. vigente 24.32 (coincide con `baseline_v1_sin_corregir`, no con `baseline`).
2. **Headway p95, ruta 3**: documento 24.7 vs. vigente 24.92 (ídem).
3. **Headway media, std, cv, mediana, bunching, espera excesiva — ambas rutas**: las ocho cifras del bloque 1 difieren ligeramente del artefacto vigente `baseline/headway_summary.csv`; todas coinciden en cambio con `baseline_v1_sin_corregir/headway_summary.csv`.
4. **FIN_TIPO=COMPLETO**: documento 86.18% vs. vigente 86.16%.
5. **FIN_TIPO=TRUNCADO_RETORNO**: documento 10.93% vs. vigente 10.94%.
6. **Máximo perfil intradía, Ruta 1**: documento 191.6 a las 15:00 vs. vigente 193.9 a las 15:30 (máximo real) / 193.0 a las 15:00.
7. **Máximo perfil intradía, Ruta 3**: documento 278.1 a las 06:00 vs. vigente 309.4 a las 06:00 (misma hora, magnitud distinta, +11.3%).
8. **Rotación de vehículos — Tabla 10 "publicada" embebida en `build_rotacion.py`** (27.5/26.9 min mediana, IQR 15.3–119.8 / 13.9–146.6, ciclo 347/337): no coincide con las cifras que el documento cita hoy (23.1/23.9, etc.) — evidencia de que el documento fue actualizado a la versión corregida y el comentario `PUBLICADO` del script quedó como referencia histórica, no como el valor vigente.

### Cifras que SÍ coinciden exactamente
- Disponibilidad de flota: las 6 cifras del bloque 2 (30 días, 19.5/15.7/14.3/50.6%, 34.1%) y la cobertura de 21/27 meses.
- Rotación: mediana 23.1/23.9, IQR 15.4–33.3/15.8–35.0, ciclo 181.9/177.3, y el 27.5% de intervalos que cruzan el cierre de jornada.
- FIN_TIPO: TRUNCADO_INDETERMINADO (1.82%), TRUNCADO_ABANDONO (1.05%), SIN_GPS (0.02%).
- Duración de viaje: medianas 157.35 (ruta 1) y 161.48 (ruta 3).
