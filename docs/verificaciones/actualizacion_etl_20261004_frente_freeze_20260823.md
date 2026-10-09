# Actualización del ETL al 2026-10-03 y comparación con `freeze_20260823_203700`

Ejecución nocturna del 4 al 5 de octubre de 2026. El ETL corrió con directorio alternativo hacia `data/actualizacion_20261004/` (commit `b1434d1`), y después se construyó el dataset de modelado de 30 minutos en ese mismo directorio. La comparación se hizo con `analisis/39_comparacion_actualizacion_freeze.py`, cuyas salidas están en `data/actualizacion_20261004/comparacion/`.

No se modificó ningún archivo existente de `data/`, `analisis/salidas/` ni del freeze. Se comprobó que, desde el inicio de la ejecución, ningún archivo fuera de `data/actualizacion_20261004/` cambió.

## Conclusión

**Hasta el 2026-06-09 no hay ningún registro histórico modificado en la base después del freeze.**

- **Despachos comunes:** en los 109.617 despachos presentes en ambas extracciones, los 15 campos que vienen de la base son idénticos. Entre ellos están `PASAJEROS`, `ALARMAS`, `DISTANCIA`, `ESTADO_DESPACHO`, las horas reales y la placa.
- **Despachos nuevos:** la extracción nueva trae 37 despachos que el freeze no tenía, de las tardes del 22 y el 23 de abril y de la mañana del 24 de abril de 2026. No son registros añadidos después del freeze:
  - Sus registros de registradora se crearon el mismo día del viaje y no se han modificado desde entonces.
  - El freeze los perdió por la forma incremental de la extracción, explicada más abajo.
- **Efecto en el dataset de modelado:**
  - 23 franjas laborales tienen más despachos y pasajeros (37 despachos y 1.871 pasajeros depurados en total).
  - Ninguna franja cambia de tipo de día.
  - No aparecen ni desaparecen franjas.
- **2026-06-10:** el freeze tiene la jornada incompleta (se extrajo ese día por la tarde), así que la comparación de ese día se presenta aparte.

## 1. Ejecución del ETL

| Bloque | Inicio–fin | Resultado |
|---|---|---|
| Preparación | 21:38:37 | Raíz vacía; copia de `configs/etl.yaml` y marcador `.etl_ejecucion.json` (parámetros `fecha_ini` 2024-04-16 y `fecha_fin` 2026-10-03; sin credenciales) |
| 3. Extracción | 21:38–21:39 | 123.909 filas; 123.085 despachos únicos (las 824 filas repetidas son despachos con dos registros de registradora) |
| 4. Transformaciones | 21:39 | 119.443 despachos de las rutas 1 y 3 |
| 5. Hora de salida por GPS | 21:39–22:01 | 1.906 despachos sin hora real de salida; 1.895 imputados |
| 6. Control de calidad | 22:01 | 14 excluidos por banderas duras (0,01 %); 18.074 con banderas blandas (15,1 %), que no excluyen |
| 7. Fin de viaje por GPS | 22:01–01:15 | 16.651 despachos truncados resueltos, con puntos de control cada 500 |
| 8. Conjunto apto | 01:15 | 119.279 de 119.443 despachos |
| 9. Versión congelada | 01:15 | `despachos_model_ready_freeze_20261005_011520`; control final sin PK duplicadas, sin placas vacías y sin duraciones no positivas |

- **Resultado:** terminó con código 0 a las 01:15:34, antes del corte de las 04:00.
- **Tipo de fin de viaje:**

  | Tipo | Despachos |
  |---|---|
  | `COMPLETO` | 102.628 |
  | `TRUNCADO_RETORNO` | 13.226 |
  | `TRUNCADO_INDETERMINADO` | 2.193 |
  | `TRUNCADO_ABANDONO` | 1.232 |

- **Aviso del bloque 9:** registra que falta `HORA_FIN_ESTIMADA` entre las columnas mínimas. Es lo esperado, porque el bloque 8 la reemplaza por `HORA_FIN_FINAL`.
- **Registro (`etl_20261004_213834.log`):** los valores de `.env` se sustituyen por `[OCULTO]`. Eso oculta también el nombre de la base, porque coincide con un valor de `.env`. El registro no contiene contraseñas.

## 2. Dataset de modelado de 30 minutos

- **Comando:** `scripts/build_modeling_dataset.py --multitarget`, ejecutado a las 04:07.
- **Configuración:** `data/actualizacion_20261004/targets.yaml`, una copia de `configs/modeling/targets.yaml` en la que solo cambian `dataset_version` (`freeze_20261005_011520`) y `source_path` (el conjunto apto nuevo).
- **Horario operativo:** se reutilizó en solo lectura el del freeze (`data/processed/operational_hours.parquet`).
- **Resultado:**
  - 50.251 franjas: 43.946 observadas y 6.305 huecos.
  - Período: del 2024-04-16 04:00 al 2026-10-03 16:00.
  - Tres escenarios (`sin_oferta`, `oferta_historica_rezagada` y `productividad_por_despacho`) en `processed/modeling/`.
  - Series en `processed/modeling/time_series/` y metadatos en `metadata/`.

## 3. Comparación con el freeze hasta el 2026-06-10

### Despachos en bruto: cambios en la base

Se comparan, por `PK_INTERVALO_DESPACHO`, el CSV crudo del freeze (`data/raw/despachos_raw_historico.csv`, extraído el 2026-06-10) y el crudo nuevo.

| Tramo | Solo en el freeze | Solo en el nuevo | Comunes | Comunes con algún campo distinto |
|---|---|---|---|---|
| Hasta 2026-06-09 | 0 | 37 | 109.617 | **0** |
| 2026-06-10 | 0 | 21 | 103 | 0 |

Campos comparados: `FECHA_INICIAL`, `HORA_INICIAL_PLAN`, `FECHA_FINAL`, `HORA_FINAL_PLAN`, `HORA_FINAL_REAL`, `FK_RUTA`, `PASAJEROS`, `ALARMAS`, `DISTANCIA`, `FK_VEHICULO`, `CONDUCTOR`, `ESTADO_DESPACHO`, `PK_INFORMACION_REGISTRADORA`, `PLACA` y `HORA_INICIAL_REAL`. Esta última también coincide en los despachos cuya hora de salida se imputó por GPS, lo que indica que la telemetría GPS de esos viajes tampoco cambió.

**Origen de los 37 despachos nuevos.** Son 18 de la ruta 1 y 19 de la ruta 3: 11 del 22 de abril, 24 del 23 de abril y 2 del 24 de abril.

- **Cuándo se crearon:** se consultaron en solo lectura sus registros de `tbl_informacion_registradora`.
  - Los del 22 y el 23 de abril se crearon a las 23:42–23:43 de ese mismo día, en el cierre automático de la jornada (`HORA_INGRESO` 23:59:59).
  - Los del 24 de abril, a las 09:53–09:54.
  - En ambos casos, `FECHA_MODIFICACION` coincide con la creación: no se han tocado desde entonces.
- **Por qué no estaban en el freeze:** la extracción incremental (`etl/extract.py`) solo trae despachos con `PK_INTERVALO_DESPACHO` mayor que el máximo ya extraído y que ya tengan registro de registradora. Si se ejecuta durante la operación, un despacho cuyo registro de registradora aparece más tarde, cuando ya se extrajeron despachos de PK mayor, queda fuera para siempre.
  - **Ejemplo del 24 de abril:** los registros de los despachos 355962, 355964, 355965 y 355970 se crearon entre las 09:36 y las 09:48 y están en el freeze. Los de 355968 y 355969, de PK menor que 355970, aparecieron a las 09:53–09:54 y quedaron fuera.
  - **Fechas del ETL:** los directorios intermedios del ETL se crearon el 22 de abril, coherente con ejecuciones en esos días.
- **Riesgo de repetición:** el mecanismo puede volver a perder despachos si el ETL se ejecuta en modo incremental durante la operación. La extracción completa en una raíz vacía, como esta, no tiene ese problema.

### Conjunto apto

| Tramo | Despachos freeze → nuevo | Pasajeros depurados freeze → nuevo | Comunes con valores distintos |
|---|---|---|---|
| Hasta 2026-06-09 | 109.457 → 109.494 (+37) | 5.062.910 → 5.064.781 (+1.871) | 25, solo en la etiqueta del tipo de fin |
| 2026-06-10 | 102 → 123 (+21) | 4.918 → 6.118 (+1.200) | 0 |

- **Valores comunes:** en los despachos comunes coinciden `PASAJEROS`, `ALARMAS`, `PASAJEROS_REALES`, `DISTANCIA`, `HORA_INICIAL_REAL`, `HORA_FIN_FINAL`, la ruta y la placa.
- **Las 25 diferencias son del proceso, no de la base:**
  - Son despachos con `FIN_TIPO = SIN_GPS` y `HORA_FIN_FUENTE = SIN_INFO` en el freeze, que ahora el bloque 7 clasifica como `TRUNCADO_RETORNO` (23), `TRUNCADO_ABANDONO` (1) y `TRUNCADO_INDETERMINADO` (1), con `GPS_ESTIMADA`.
  - Su hora de fin final y su duración son las mismas, así que no afectan a ninguna variable del dataset de modelado.
- **Despachos excluidos:** ningún despacho del freeze sale del conjunto apto. La imputación GPS y los filtros de duración dan el mismo resultado en los despachos comunes.

### Dataset de modelado por franja y tipo de día (escenario `sin_oferta`)

| Tramo | Franjas freeze / nuevo | Solo en uno | Despachos o pasajeros distintos | Tipo de día distinto | Diferencia de pasajeros |
|---|---|---|---|---|---|
| Hasta 2026-06-09 | 43.784 / 43.784 | 0 | 23 (máx. 126 pasajeros) | **0** | +1.871 |
| 2026-06-10 | 47 / 49 | 2, solo en el nuevo | 11 (máx. 131) | 0 | +808 |

- **Las 23 franjas** son del 22 (7), el 23 (15) y el 24 de abril (1), y las explican exactamente los 37 despachos nuevos.
- **Por tipo de día:** hasta el 2026-06-09 solo cambia `LABORAL`, porque esos tres días fueron de miércoles a viernes.
  - **Ruta 1:** +18 despachos y +923 pasajeros depurados.
  - **Ruta 3:** +19 despachos y +948 pasajeros depurados.
  - **Franjas laborales observadas:** pasan de 14.062 a 14.066 en la ruta 1 y de 14.282 a 14.287 en la ruta 3. Son franjas que en el freeze eran huecos.
  - **Demás tipos de día:** `SABADO`, `DOMINGO`, `FESTIVO` y `FESTIVO_PUENTE` son idénticos en franjas, despachos y pasajeros.

## 4. Franjas del 2026-06-11 al 2026-10-03 fuera del horario operativo del freeze

Se cuentan sobre las series completas de la actualización, antes del filtro `operational_only` del dataset de modelado. Como referencia se incluye el período del 2026-04-01 al 2026-06-10.

| Ruta | Período | Franjas con despachos | Fuera del horario | Despachos / pasajeros fuera | Hora de esas franjas |
|---|---|---|---|---|---|
| 1 | 2026-04-01 a 2026-06-10 | 1.582 | 10 (0,6 %) | 10 / 416 | 04:00 (10) |
| 1 | **2026-06-11 a 2026-10-03** | 2.526 | **26 (1,0 %)** | 26 / 1.112 | 04:00 (25), 19:00 (1) |
| 3 | 2026-04-01 a 2026-06-10 | 1.615 | 0 | 0 / 0 | — |
| 3 | **2026-06-11 a 2026-10-03** | 2.502 | **1 (0,04 %)** | 1 / 5 | 03:30 (1) |

- **Total del 11 de junio al 3 de octubre:** 27 de 5.028 franjas con despachos (0,5 %) quedan fuera del horario del freeze y, por tanto, fuera del dataset de modelado.
- **Ruta 1:** casi todas son despachos aislados a las 04:00, antes del inicio de su horario operativo. Ya ocurría antes del 11 de junio, aunque con algo más de frecuencia: 0,23 por día frente a 0,14.
- **Franjas sin despachos dentro del horario:** aumentan ligeramente por día, de 5,3 a 5,7 en la ruta 1 y de 5,5 a 6,6 en la ruta 3. Es coherente con la reducción de despachos en día laboral desde el 11 de junio, descrita en `comparacion_periodos_rutas_1_3_20261004.md`.

## Archivos

- **ETL:**
  - `data/actualizacion_20261004/` contiene `raw/`, `interim/`, `processed/model_ready/` y `reports/tables/{qc,etl}/`, el registro `etl_20261004_213834.log`, `etl.yaml` y `.etl_ejecucion.json`.
  - El directorio está ignorado por git.
- **Dataset de modelado:**
  - `data/actualizacion_20261004/targets.yaml`
  - `data/actualizacion_20261004/processed/modeling/`
  - `data/actualizacion_20261004/metadata/modeling_multitarget_dataset_actualizacion_20261004.json`
- **Comparación:** `analisis/39_comparacion_actualizacion_freeze.py` (sin versionar). Sus salidas están en `data/actualizacion_20261004/comparacion/`:
  - `resumen.json`
  - `diferencias_crudo_por_pk.csv`, `crudo_solo_nuevo.csv`
  - `diferencias_model_ready_por_pk.csv`, `atribucion_model_ready.csv`
  - `franjas_distintas.csv`, `franjas_solo_en_uno.csv`
  - `por_tipo_dia.csv`
