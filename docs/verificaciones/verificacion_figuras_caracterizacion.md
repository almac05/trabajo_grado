# Verificación y regeneración de figuras del capítulo de caracterización

Fecha: 2026-09-27. Rama `consolidacion-evaluacion`, último commit `e504b29`. **No se hizo ningún commit.**
Continúa el inventario de [inventario_scripts_figuras.md](inventario_scripts_figuras.md).

## 0. Respaldo y archivos sobrescritos

Antes de ejecutar nada se copiaron fuera del repositorio `reports/figures/`, `analisis/salidas/` y `reports/tables/` (432 archivos, 105 MB):

- Respaldo: `C:\Users\regis\respaldos_proyecto_grado\respaldo_20260927_152128\`
- Manifiesto MD5: `C:\Users\regis\respaldos_proyecto_grado\manifiesto_20260927_152128.md5`

Al final se contrastaron los tres directorios contra el manifiesto.

| Situación | Archivo |
|---|---|
| **Sobrescrito** (único) | `reports/figures/baseline/contraccion_flota_mensual.png` (MD5 anterior `504e8939…`, nuevo `501bfd75…`; la versión anterior está en el respaldo, en `reports_figures/baseline/`) |
| Nuevo | `reports/figures/eda/perfil_intradia_laboral_r1_g30min.png` |
| Nuevo | `reports/figures/eda/perfil_intradia_laboral_r3_g30min.png` |
| Nuevo | `analisis/salidas/perfil_intradia_laboral_p25_p75.csv` |
| Nuevo | `analisis/salidas/rotacion_ociosa_p95_maximo.csv` |
| Scripts nuevos | `analisis/26_perfil_intradia_laboral.py`, `analisis/27_rotacion_p95_maximo.py` |

Ningún otro archivo de `reports/tables/` ni de `analisis/salidas/` cambió. No se modificó ningún script existente, ningún freeze ni ningún archivo de configuración. Las comparaciones del punto uno se hicieron con scripts temporales fuera del repositorio, en el scratchpad de la sesión.

## 1. Equivalencia de fuentes

Se comparó `pasajeros_total` de `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (`dataset_version = freeze_20260823_203700`) con `data/processed/time_series/ts_ruta{1,3}_g30min.parquet`, cruzando por ruta y `timestamp`.

Se usaron dos criterios de franja operativa, con resultado idéntico:

- **A**: en el parquet de modelado, `pasajeros_total` no nulo; en la serie temporal, `gap_tipo == 'operativo'`.
- **B**: `gap_tipo == 'operativo'` en ambos.

| Ruta | Franjas operativas (modelado) | Franjas operativas (time_series) | Franjas comparadas | Difieren | Diferencia máxima |
|---|---|---|---|---|---|
| 1 | 19.293 | 19.337 | 19.293 | **0** | **0** |
| 3 | 19.638 | 19.660 | 19.638 | **0** | **0** |

**Valores**: en las 38.931 franjas comunes el valor es idéntico.

**Cobertura**: la serie temporal tiene **66 franjas operativas que no están en el parquet de modelado** (44 en la Ruta 1 y 22 en la Ruta 3). Todas tienen un solo despacho, entre 3 y 58 pasajeros, y `dentro_horario_operativo == False`: son despachos aislados fuera del horario operativo estimado. El dataset de modelado las excluye por diseño (`src/proyecto_grado/modeling/dataset.py:190-193`, filtro `operational_only`). No hay franjas del parquet de modelado ausentes en la serie temporal.

- **Consecuencia**: las figuras de `run_eda_temporal.py`, que leen `time_series`, incluyen esas 66 franjas marginales. Las figuras nuevas no las incluyen.
- **Por qué se siguió adelante**: la condición de parada se refería a diferencias en los valores de `pasajeros_total`, y no las hay. La diferencia está en qué franjas cubre cada fuente, y se documenta aquí.

**Construcción a partir de `PASAJEROS_REALES`**: se contrastó el despacho del 31 de mayo de 2024 con 874 alarmas.

| Campo | Valor |
|---|---|
| Despacho | `PK_INTERVALO_DESPACHO = 252998`, Ruta 3, placa VEH025, salida 12:31:13 |
| `PASAJEROS` (crudo) | 868 |
| `ALARMAS` | 874 |
| `PASAJEROS_REALES` | 0 |
| Franja 12:30, Ruta 3, en `model_ready` | 5 despachos; suma `PASAJEROS` = 1.082; suma `PASAJEROS_REALES` = **208** |
| `time_series/ts_ruta3_g30min` | `pasajeros_total = 208`, `despachos_count = 5` |
| Parquet de modelado | `pasajeros_total = 208`, `despachos_count_real = 5` |

**Conclusión**: ambas fuentes se construyeron con `PASAJEROS_REALES`. Con el conteo crudo, la franja valdría 1.082.

## 2. Figura de flota

- **Ejecución**: `scripts/plot_contraccion_flota.py` sin modificarlo. El script no tiene cambios sin comprometer.
- **Fuente**: `reports/tables/baseline/diagnostico_flota_mensual.csv`, del 2026-08-31, generada por `scripts/diagnostico_reduccion_flota.py`. **Ese script tiene cambios sin comprometer (M)**: precisamente el paso de `PASAJEROS` a `PASAJEROS_REALES`.
- **Verificación contra `model_ready`**:
  - En los 27 meses del CSV, `pasajeros_total` es igual a la suma de `PASAJEROS_REALES`.
  - En ningún mes coincide con la suma de `PASAJEROS`.
  - `despachos_total` coincide con el conteo de despachos.
  - Ejemplo, mayo de 2024: 244.458 depurado frente a 247.688 crudo. Mayo de 2026: 145.287 frente a 145.868.
- **Comparación visual del panel «Pasajeros totales»**:
  - Figura anterior: primer punto en ~247,7 k (**conteo crudo**).
  - Figura nueva: primer punto en 244,5 k (**conteo depurado**).
  - Los paneles de vehículos y despachos no cambian.
- **Cambio de texto dentro de la imagen**: la anotación del panel de productividad pasó de «44-50, estable» a **«43-50, estable»**. Si el documento cita ese rango, hay que actualizarlo.
- **Títulos**: la figura conserva títulos por panel («Vehículos activos», «Despachos totales», etc.). No tiene título general incrustado. Quitar los títulos por panel exigiría modificar el script, y no se hizo.

## 3. Perfil intradía en día laboral

- **Script nuevo**: `analisis/26_perfil_intradia_laboral.py`.
- **Fuente y cálculo**: los mismos que `analisis/14_cuadros_mecanismos.py` usa para `cuadro_perfil_horario_laboral.csv`:
  - parquet de modelado;
  - `FK_RUTA == ruta` y `pasajeros_total` no nulo;
  - `tipo_dia == 'LABORAL'`;
  - agrupación por `timestamp.strftime('%H:%M')`, es decir, por franja de 30 minutos.
- **Verificación interna**: antes de escribir nada, el script comprueba que media, desviación y n coinciden con el cuadro en todas las franjas. Si no coinciden, aborta. Se cumplió en las 57 franjas.
- **Formato de la figura**: sin título incrustado; leyenda sobre el área de trazado.

| Ruta | Figura | Franjas | Máximo de la media | Franja | p25 – p75 en esa franja | n |
|---|---|---|---|---|---|---|
| 1 | `reports/figures/eda/perfil_intradia_laboral_r1_g30min.png` | 28 (04:30 a 18:00) | **192,1** pasajeros | **15:30** | 157,0 – 225,0 | 523 |
| 3 | `reports/figures/eda/perfil_intradia_laboral_r3_g30min.png` | 29 (04:00 a 18:00) | **306,8** pasajeros | **06:00** | 261,0 – 354,0 | 525 |

Los dos máximos coinciden exactamente con los del cuadro.

Notas:

- **Estado del cuadro en git**: `cuadro_perfil_horario_laboral.csv` **tiene cambios sin comprometer (M)**. Se regeneró el 2026-09-22 y la figura coincide con esa versión de trabajo, no con la comprometida. `14_cuadros_mecanismos.py` no tiene cambios.
- **Franja de menor n**: en la Ruta 3, la franja 04:00 tiene n = 57. El resumen del cuadro 1b excluye las franjas con n < 100, pero el CSV y la figura las incluyen. El máximo no cambia con ese filtro.
- **Proximidad del máximo en la Ruta 1**: la franja 15:00 está muy cerca del máximo (191 pasajeros aproximadamente).
- **Figuras que sustituyen**: estas figuras reemplazan a `curva_intraday_{1,3}_laboral_g30min.png` de `run_eda_temporal.py`, que agrupa por hora entera y tiene título. Esas figuras antiguas no se tocaron.

## 4. Disponibilidad de flota

**La medición por intervalo no existe.** No se calculó.

Qué hace `src/proyecto_grado/analytics/fleet_availability.py` (sin cambios sin comprometer):

- Reconstruye, con muestreo de 5 minutos, cuántos vehículos hay en patio en 30 días laborales.
- Resume **el porcentaje del tiempo con patio vacío en tres ventanas fijas**, no solo en el pico de la mañana:

  | Ventana | Tiempo con patio vacío |
  |---|---|
  | Pico mañana (05:00–09:00) | 34,1 % |
  | Pico tarde (14:00–16:00) | 0,0 % |
  | Cierre (16:30–17:30) | 5,6 % |

  Fuente: `reports/tables/baseline/fleet_availability_summary.csv`, del 2026-07-02.
- Por separado, **clasifica los intervalos largos (> 15 min) solo por la ventana horaria en que ocurren** (`_headways_largos_franjas`, líneas 133-157). No consulta la serie de ocupación del patio en ese instante. Las cifras 19,5 %, 15,7 %, 14,3 % y 50,6 % de los 447 intervalos largos son, por lo tanto, proporciones **por franja horaria**, no por estado del patio.

**Advertencia de redacción**: el docstring del módulo dice «Solo ~20 % de headways largos coinciden con patio vacío en pico mañana». En realidad, ese 19,5 % es la proporción de intervalos largos que cae **en el pico de la mañana**, sin verificar si el patio estaba vacío. Si el documento hace esa afirmación, no está respaldada por el cálculo.

Otros artefactos revisados:

- `reports/tables/baseline/diagnostico_disponibilidad_multidia.csv` (`scripts/diagnostico_disponibilidad_multidia.py`): la misma lógica por franja, sin cruce por intervalo.
- `scripts/diagnostico_disponibilidad_flota.py`: **sí** cruza cada intervalo largo con el patio. Para cada despacho con headway > 20 min, promedia los vehículos en patio unos 10 minutos antes de la salida. Pero lo hace para un único día (el quinto con más despachos) y **solo lo imprime en consola**. Su CSV (`diagnostico_disponibilidad_flota.csv`) guarda la serie de ocupación del patio de ese día, no el cruce. No es una medición persistida ni multidía.

## 5. Rotación ociosa dentro de la jornada

- **Fuentes existentes**: `scripts/build_rotacion.py` y `reports/tables/baseline/rotacion_vehiculos.csv` reportan p25, mediana, p75 y media, pero no el p95 ni el máximo.
- **Script nuevo**: `analisis/27_rotacion_p95_maximo.py` importa y reutiliza `calcular()` de `build_rotacion.py` sin modificarlo:
  - origen: `model_ready`;
  - rotación = inicio del recorrido menos fin del recorrido anterior de la misma placa;
  - variante «misma jornada operativa», con el día operativo de 04:00 a 04:00.
- **Control**: el script verifica que n y la mediana coincidan con `rotacion_vehiculos.csv`. Coinciden en ambas rutas.

Resultados (minutos, todos los intervalos, como en `build_rotacion.py`):

| Ruta | n intervalos | Mediana | p75 | **p95** | p99 | **Máximo** | Caso del máximo |
|---|---|---|---|---|---|---|---|
| 1 | 40.170 | 23,1 | 33,3 | **92,8** | 254,6 | **690,8** | placa VEH037, salida siguiente 2025-07-05 17:52 |
| 3 | 39.207 | 23,9 | 35,0 | **89,2** | 247,0 | **607,0** | placa VEH055, salida siguiente 2024-08-13 16:07 |

- **Intervalos negativos**: hay 54 en la Ruta 1 y 64 en la Ruta 3 (solapamiento de recorridos de la misma placa). Excluirlos no cambia el máximo y mueve el p95 a 92,9 y 89,5.
- **Interpretación de los máximos**: equivalen a 10–11,5 horas de detención dentro de una misma jornada. Con toda probabilidad son vehículos retirados a media mañana y reincorporados al final de la tarde, no rotación ociosa en sentido operativo. Conviene tenerlo en cuenta antes de citar el máximo.
- **Dependencia sin comprometer**: `scripts/build_rotacion.py`, del que depende `27_rotacion_p95_maximo.py`, **no está en git (??)**.

## 6. Script de origen de cada figura y estado en git

| Figura | Script que la generó | Cambios sin comprometer en el script | Estado |
|---|---|---|---|
| `reports/figures/baseline/contraccion_flota_mensual.png` | `scripts/plot_contraccion_flota.py` | No. Su productor de datos, `scripts/diagnostico_reduccion_flota.py`, **sí (M)** | **Regenerada** (sobrescrita) |
| `reports/figures/eda/perfil_intradia_laboral_r1_g30min.png` | `analisis/26_perfil_intradia_laboral.py` | **Sí: script nuevo, sin seguimiento (??)**. Su referencia, `cuadro_perfil_horario_laboral.csv`, tiene cambios (M) | **Nueva** |
| `reports/figures/eda/perfil_intradia_laboral_r3_g30min.png` | `analisis/26_perfil_intradia_laboral.py` | Ídem | **Nueva** |
| Tabla `analisis/salidas/rotacion_ociosa_p95_maximo.csv` (no es figura) | `analisis/27_rotacion_p95_maximo.py` | **Sí: nuevo (??)**; depende de `scripts/build_rotacion.py` (??) | **Nueva** |

Figuras del capítulo que no se tocaron en esta sesión:

- `heatmap_demanda_hora_dia_*`, `boxplot_tipo_dia_*` y `acf_pacf_*`, generadas por `run_eda_temporal.py`, sin cambios sin comprometer en el script.
- `acf_operativo_r*`, generada por `07_acf_operativo.py`, sin cambios.
- `acf_demanda_operativa_20260823.png`, generada por `24_acf_demanda_regiones.py`, **sin seguimiento (??)**.

Todas esas figuras llevan título incrustado, salvo `acf_operativo_r*`. Su regeneración sin título queda pendiente de decisión.
