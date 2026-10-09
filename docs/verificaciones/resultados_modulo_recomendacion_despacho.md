# Módulo de recomendación de despacho: verificaciones, evaluación y controles de calidad

Generado el 2026-10-04 con `python scripts/run_recomendacion_despacho.py`. Las salidas están en `reports/tables/dispatch/` con el sufijo `__recomendacion_despacho__freeze_20260922_203820`. Ese directorio está ignorado por git (`reports/tables/*`), así que las cifras de este informe son la constancia versionable. No se modificó ningún módulo, script, freeze ni configuración existentes. Fuera del `__init__.py` de `dispatch/`, todos los archivos son nuevos.

## Archivos creados

| Archivo | Contenido |
|---|---|
| `configs/dispatch/recomendacion.yaml` | Rutas de entrada, período de calibración, bloques, política de festivos, tope y servicio mínimo |
| `src/proyecto_grado/dispatch/config.py` | `cargar_configuracion_recomendacion()`, `ConfiguracionRecomendacion`, `BloqueHorario`, `ErrorConfiguracionRecomendacion` |
| `src/proyecto_grado/dispatch/parametros.py` | Preparación de despachos, cuantiles, capacidad y verificación contra el script 36 |
| `src/proyecto_grado/dispatch/predictor_mixto.py` | Predictor por régimen, respaldo y verificación contra el script 25 |
| `src/proyecto_grado/dispatch/reglas.py` | Redondeo aritmético, reglas por régimen y ajuste de factibilidad |
| `src/proyecto_grado/dispatch/evaluacion.py` | Unión con la operación real, clasificación y las tres tablas |
| `src/proyecto_grado/dispatch/__init__.py` | Docstring y reexportación del cargador (único archivo existente modificado; estaba vacío) |
| `scripts/run_recomendacion_despacho.py` | Punto de entrada (`argparse`, `main()`, sin tocar `sys.path`) |
| `tests/unit/test_dispatch.py` | 17 pruebas `unit` con datos sintéticos |

## Decisiones de interpretación

El enunciado dejaba abiertos algunos puntos. Así se resolvieron; todos se pueden cambiar.

1. **Tipo de día de despachos fuera del horario operativo.** El dataset de modelado solo tiene franjas dentro del horario operativo. 66 despachos aislados del conjunto apto caen fuera, la mayoría a las 04:00 en la ruta 1. Siete de ellos son del período de calibración y diez del de evaluación. A esos despachos se les asigna el `tipo_dia` de las demás franjas de su ruta y jornada **en el mismo dataset**, sin aplicar ninguna regla de festivos propia. Antes se comprueba que cada jornada tenga un solo tipo de día en el dataset. Así se conservan, igual que en el script 36, y por eso los conteos coinciden con los suyos.
2. **Umbrales de clase (Q1 y Q3).** Se usan los del régimen de la franja: en régimen ordinario, los de la ruta y el bloque; en régimen raro, los de la ruta. Por eso la tabla de parámetros incluye también Q1 y, en régimen raro, Q3.
3. **Régimen raro.** Se aplica la demanda dividida por el divisor, con redondeo aritmético y el servicio mínimo. El tope de carga solo actúa en régimen ordinario, como dice la regla.
4. **Demanda negativa.** Se trata como 0. En las predicciones del freeze no hay valores negativos.
5. **Factibilidad.** Se aplica con la demanda **predicha**, que es la única disponible al recomendar. Los empates en pasajeros por despacho resultantes se resuelven por ruta y hora. Una jornada que siga sobre la capacidad con todas sus franjas en el mínimo se registra como no factible; en la ejecución no hubo ninguna.
6. **Jornadas con una sola ruta.** Dos de las 68 fechas solo tienen la ruta 3 entre las jornadas comunes. En ellas, el total conjunto incluye solo esa ruta.
7. **Franjas evaluadas.** Son las 3.038 franjas de las jornadas comunes, todas con despachos reales. Hay 10 franjas reales, con un despacho cada una, en esas jornadas pero fuera de la predicción. Son 10 despachos de la ruta 1 a las 04:00, los mismos fuera de horario del punto 1, y no entran en la evaluación.

## Verificaciones

### Calibración frente al script 36

Período de calibración: 2025-12-25 a 2026-04-01, con 11.178 despachos en 98 jornadas. La capacidad conjunta es de **153 despachos** (jornada 2026-03-13).

| Comparación con `distribucion__pasajeros_por_despacho.csv` (validación) | Celdas | Mediana y Q3 coinciden | Máx. dif. mediana | Máx. dif. Q3 |
|---|---|---|---|---|
| `corte = regimen_x_bloque`, régimen ordinario, frente a los parámetros ordinarios por ruta y bloque | 12 | 12 | 0 | 0 |
| `corte = regimen`, régimen raro, frente a los parámetros raros por ruta | 2 | 2 | 0 | 0 |
| `corte = bloque` (filas del clasificador del script 36, ambos regímenes juntos) frente a los parámetros ordinarios | 12 | 11 | 0 | 1 |

**Diferencia encontrada:** en la ruta 3, bloque mañana, el Q3 ordinario es 58 y el del script 36 es 57. No es un error de cálculo. Las filas `corte = bloque` del script 36 mezclan los dos regímenes (1.397 despachos frente a 1.377 ordinarios), mientras que el módulo calibra solo con el régimen ordinario, como pide el enunciado. Contra las filas del mismo régimen, todo coincide con exactitud, también el Q1 y los conteos. Varias de las demás celdas `bloque` difieren en Q1 (hasta 1 pasajero) y en número de despachos, pero ninguna en la mediana ni en el Q3.

| Ruta | Régimen | Bloque | Despachos | Jornadas | Q1 | Mediana | Q3 |
|---|---|---|---|---|---|---|---|
| 1 | ordinario | madrugada | 215 | 80 | 31 | 37 | 43,5 |
| 1 | ordinario | pico_manana | 887 | 81 | 35 | 42 | 48,5 |
| 1 | ordinario | manana | 1.344 | 94 | 36 | 43 | 52 |
| 1 | ordinario | valle | 1.581 | 94 | 34 | 43 | 51 |
| 1 | ordinario | pico_tarde | 794 | 94 | 45 | 54 | 65 |
| 1 | ordinario | cierre | 494 | 88 | 35,25 | 45 | 54 |
| 1 | raro | todos | 47 | 4 | 18 | 22 | 27 |
| 3 | ordinario | madrugada | 370 | 80 | 31 | 37 | 46 |
| 3 | ordinario | pico_manana | 1.357 | 82 | 39 | 52 | 67 |
| 3 | ordinario | manana | 1.377 | 94 | 38 | 48 | 58 |
| 3 | ordinario | valle | 1.595 | 94 | 40 | 48 | 57 |
| 3 | ordinario | pico_tarde | 727 | 93 | 44 | 52 | 60 |
| 3 | ordinario | cierre | 339 | 85 | 35 | 46 | 56 |
| 3 | raro | todos | 51 | 4 | 16,5 | 23 | 28 |

Los parámetros del régimen raro se apoyan en solo **4 jornadas por ruta** (47 y 51 despachos), así que conviene leerlos con cautela.

### Predictor mixto frente al script 25

`pred_combinada` del script 25 **no es** el predictor mixto: usa la referencia de 26 semanas en régimen ordinario y la de 52 en raro. Por eso la verificación se hizo por componente:

| Comprobación | Resultado |
|---|---|
| Franjas: módulo / script 25 / comunes | 3.038 / 3.038 / 3.038 (0 solo en uno de los dos) |
| Régimen distinto | 0 |
| Demanda real distinta | 0 (máx. dif. 0) |
| Régimen raro (131 franjas): predicción = `pred_combinada` y = `pred_ref52` | 0 distintas (máx. dif. 0) |
| Régimen ordinario (2.907 franjas): predicción = `pred_xgboost` del script 25 | 0 distintas (máx. dif. 0) |
| Referencia del módulo = `pred_ref52` en todas las franjas | 0 distintas |
| Diferencia con `pred_combinada` en régimen ordinario (informativa, esperada por diseño) | hasta 81,8 pasajeros |

Fuentes de la predicción: 2.907 franjas de XGBoost y 131 de la referencia en régimen raro. **El respaldo no se usó** porque no falta ninguna predicción de XGBoost en las jornadas comunes. El respaldo está cubierto por una prueba unitaria.

### Unión con la operación real (evaluación: 2026-04-02 a 2026-06-10)

Hay 7.483 despachos aptos en 69 jornadas del período, y 7.272 de ellos caen en las 3.038 franjas evaluadas. La demanda real reconstruida desde el conjunto apto coincide con la columna `real` de los artefactos: la diferencia máxima es 0. Ninguna franja evaluada carece de despachos reales.

**Contexto de la capacidad:** en 2 de las 68 fechas evaluadas la operación real superó la capacidad calibrada (máximo real: 154 frente a 153). Sin el ajuste, la recomendación llega a 163 despachos en una jornada con tope y a 160 sin él.

## Evaluación: resumen de las cuatro combinaciones

La política de festivos solo cambia las 131 franjas de régimen raro. Con el divisor propio (mediana rara de 22 o 23) se recomiendan 1 o 2 despachos por franja; con el divisor ordinario (42 a 54), siempre 1. El tope solo cambia las franjas ordinarias. Por eso el ajuste de factibilidad depende únicamente del tope: los festivos tienen poca demanda y nunca se acercan a la capacidad.

| Política de festivos | Tope | Despachos recomendados | Despachos reales | Diferencia % | Jornadas ajustadas | Despachos retirados | Jornadas no factibles |
|---|---|---|---|---|---|---|---|
| divisor_propio | sí | 7702 | 7272 | 5,9 | 18 de 68 | 91 | 0 |
| divisor_propio | no | 7400 | 7272 | 1,8 | 5 de 68 | 14 | 0 |
| divisor_ordinario | sí | 7660 | 7272 | 5,3 | 18 de 68 | 91 | 0 |
| divisor_ordinario | no | 7358 | 7272 | 1,2 | 5 de 68 | 14 | 0 |

Los totales cuentan los despachos de las 3.038 franjas evaluadas (7.272 reales).

## Evaluación por combinación

Cómo leer las tablas:

- **Tabla 1.** Por clase real, porcentaje de franjas en que la recomendación es **mayor / igual / menor** que lo real; entre paréntesis, el número de franjas.
- **Tabla 2.** Distribución de clases real frente a la que habrían tenido las franjas siguiendo la recomendación (demanda real entre despachos recomendados), con los mismos Q1 y Q3. «% misma clase» es la proporción de franjas cuya clase no cambia. El detalle cruzado está en `matriz_clasificacion__…csv`.
- **Tabla 3.** Totales por jornada, recomendados frente a reales. «Jornadas con ajuste» cuenta las jornadas de esa ruta y bloque en que se aplicó la factibilidad (sobre ambas rutas); «con retiro», aquellas en que el ajuste quitó despachos de esa ruta y bloque.

`todos` es el agregado de la ruta.

### Divisor propio, con tope (configuración por defecto)

**Tabla 1. Despachos recomendados frente a reales, por clase real**

| Ruta | Bloque | Todas | Sobrecargada | Normal | Subutilizada |
|---|---|---|---|---|---|
| 1 | todos | 31 / 49 / 21 (1483) | 55 / 35 / 10 (240) | 28 / 51 / 21 (901) | 21 / 52 / 27 (342) |
| 1 | madrugada | 29 / 60 / 12 (52) | 25 / 50 / 25 (8) | 31 / 61 / 8 (36) | 25 / 62 / 12 (8) |
| 1 | pico_manana | 25 / 54 / 21 (211) | 51 / 41 / 8 (37) | 19 / 58 / 24 (139) | 23 / 51 / 26 (35) |
| 1 | manana | 31 / 46 / 23 (367) | 58 / 31 / 12 (59) | 29 / 50 / 21 (222) | 19 / 47 / 35 (86) |
| 1 | valle | 29 / 48 / 23 (477) | 55 / 39 / 6 (93) | 26 / 50 / 24 (274) | 14 / 51 / 35 (110) |
| 1 | pico_tarde | 36 / 46 / 18 (223) | 59 / 30 / 11 (27) | 33 / 46 / 20 (138) | 33 / 52 / 16 (58) |
| 1 | cierre | 36 / 52 / 12 (153) | 62 / 25 / 12 (16) | 36 / 52 / 12 (92) | 27 / 62 / 11 (45) |
| 3 | todos | 35 / 46 / 19 (1555) | 58 / 38 / 4 (253) | 34 / 45 / 21 (951) | 23 / 54 / 23 (351) |
| 3 | madrugada | 34 / 40 / 26 (100) | 60 / 40 / 0 (20) | 29 / 46 / 25 (65) | 20 / 13 / 67 (15) |
| 3 | pico_manana | 39 / 28 / 33 (213) | 74 / 24 / 3 (38) | 35 / 27 / 38 (159) | 6 / 44 / 50 (16) |
| 3 | manana | 35 / 44 / 22 (385) | 71 / 23 / 6 (65) | 33 / 47 / 20 (223) | 14 / 51 / 35 (97) |
| 3 | valle | 35 / 52 / 13 (494) | 49 / 47 / 5 (88) | 33 / 51 / 16 (291) | 31 / 57 / 12 (115) |
| 3 | pico_tarde | 40 / 44 / 16 (234) | 46 / 46 / 8 (26) | 44 / 38 / 18 (135) | 30 / 55 / 15 (73) |
| 3 | cierre | 25 / 64 / 12 (129) | 38 / 62 / 0 (16) | 28 / 59 / 13 (78) | 11 / 74 / 14 (35) |

**Tabla 2. Clase real → clase con la recomendación (% de franjas)**

| Ruta | Bloque | Franjas | Sobrecargada real → rec. | Normal real → rec. | Subutilizada real → rec. | % misma clase |
|---|---|---|---|---|---|---|
| 1 | todos | 1483 | 16,2 → 20,8 | 60,8 → 41,8 | 23,1 → 37,4 | 56,5 |
| 1 | madrugada | 52 | 15,4 → 17,3 | 69,2 → 44,2 | 15,4 → 38,5 | 67,3 |
| 1 | pico_manana | 211 | 17,5 → 25,6 | 65,9 → 44,5 | 16,6 → 29,9 | 59,7 |
| 1 | manana | 367 | 16,1 → 19,3 | 60,5 → 43,6 | 23,4 → 37,1 | 54,8 |
| 1 | valle | 477 | 19,5 → 24,1 | 57,4 → 42,8 | 23,1 → 33,1 | 53,5 |
| 1 | pico_tarde | 223 | 12,1 → 19,3 | 61,9 → 36,3 | 26,0 → 44,4 | 56,1 |
| 1 | cierre | 153 | 10,5 → 10,5 | 60,1 → 37,9 | 29,4 → 51,6 | 62,7 |
| 3 | todos | 1555 | 16,3 → 18,8 | 61,2 → 41,5 | 22,6 → 39,6 | 56,6 |
| 3 | madrugada | 100 | 20,0 → 24,0 | 65,0 → 41,0 | 15,0 → 35,0 | 45,0 |
| 3 | pico_manana | 213 | 17,8 → 20,7 | 74,6 → 62,0 | 7,5 → 17,4 | 55,9 |
| 3 | manana | 385 | 16,9 → 16,4 | 57,9 → 47,0 | 25,2 → 36,6 | 51,4 |
| 3 | valle | 494 | 17,8 → 19,2 | 58,9 → 37,0 | 23,3 → 43,7 | 61,3 |
| 3 | pico_tarde | 234 | 11,1 → 19,2 | 57,7 → 24,8 | 31,2 → 56,0 | 55,1 |
| 3 | cierre | 129 | 12,4 → 17,1 | 60,5 → 39,5 | 27,1 → 43,4 | 66,7 |

**Tabla 3. Totales por jornada y ajuste de factibilidad**

| Ruta | Bloque | Jornadas | Total recomendado | Total real | Diferencia % | Media por jornada rec. / real | Jornadas rec. > / = / < real | Jornadas con ajuste | Jornadas con retiro (despachos) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | todos | 66 | 3610 | 3454 | 4,5 | 54,7 / 52,3 | 33 / 11 / 22 | 18 | 14 (53) |
| 1 | madrugada | 52 | 141 | 132 | 6,8 | 2,7 / 2,5 | 15 / 31 / 6 | 18 | 5 (5) |
| 1 | pico_manana | 55 | 587 | 580 | 1,2 | 10,7 / 10,5 | 23 / 16 / 16 | 18 | 3 (3) |
| 1 | manana | 66 | 935 | 897 | 4,2 | 14,2 / 13,6 | 32 / 16 / 18 | 18 | 4 (5) |
| 1 | valle | 66 | 1052 | 1040 | 1,2 | 15,9 / 15,8 | 27 / 16 / 23 | 18 | 14 (35) |
| 1 | pico_tarde | 65 | 557 | 507 | 9,9 | 8,6 / 7,8 | 33 / 20 / 12 | 18 | 0 (0) |
| 1 | cierre | 57 | 338 | 298 | 13,4 | 5,9 / 5,2 | 33 / 14 / 10 | 18 | 5 (5) |
| 3 | todos | 68 | 4092 | 3818 | 7,2 | 60,2 / 56,1 | 42 / 7 / 19 | 18 | 18 (38) |
| 3 | madrugada | 53 | 246 | 244 | 0,8 | 4,6 / 4,6 | 18 / 15 / 20 | 18 | 18 (28) |
| 3 | pico_manana | 54 | 916 | 911 | 0,5 | 17,0 / 16,9 | 24 / 9 / 21 | 18 | 1 (1) |
| 3 | manana | 68 | 975 | 910 | 7,1 | 14,3 / 13,4 | 35 / 15 / 18 | 18 | 3 (3) |
| 3 | valle | 68 | 1211 | 1089 | 11,2 | 17,8 / 16,0 | 44 / 15 / 9 | 18 | 3 (3) |
| 3 | pico_tarde | 68 | 529 | 466 | 13,5 | 7,8 / 6,9 | 38 / 22 / 8 | 18 | 0 (0) |
| 3 | cierre | 51 | 215 | 198 | 8,6 | 4,2 / 3,9 | 22 / 22 / 7 | 18 | 3 (3) |

### Divisor propio, sin tope

**Tabla 1. Despachos recomendados frente a reales, por clase real**

| Ruta | Bloque | Todas | Sobrecargada | Normal | Subutilizada |
|---|---|---|---|---|---|
| 1 | todos | 27 / 50 / 23 (1483) | 55 / 35 / 10 (240) | 25 / 52 / 23 (901) | 15 / 54 / 31 (342) |
| 1 | madrugada | 31 / 62 / 8 (52) | 25 / 75 / 0 (8) | 33 / 61 / 6 (36) | 25 / 50 / 25 (8) |
| 1 | pico_manana | 23 / 55 / 21 (211) | 51 / 41 / 8 (37) | 17 / 60 / 23 (139) | 20 / 51 / 29 (35) |
| 1 | manana | 31 / 47 / 22 (367) | 58 / 31 / 12 (59) | 28 / 52 / 20 (222) | 17 / 48 / 35 (86) |
| 1 | valle | 27 / 48 / 25 (477) | 56 / 35 / 9 (93) | 23 / 50 / 26 (274) | 12 / 52 / 36 (110) |
| 1 | pico_tarde | 27 / 47 / 26 (223) | 59 / 26 / 15 (27) | 28 / 45 / 28 (138) | 12 / 62 / 26 (58) |
| 1 | cierre | 25 / 54 / 20 (153) | 50 / 38 / 12 (16) | 26 / 53 / 21 (92) | 16 / 62 / 22 (45) |
| 3 | todos | 28 / 48 / 24 (1555) | 49 / 44 / 7 (253) | 27 / 47 / 26 (951) | 16 / 56 / 29 (351) |
| 3 | madrugada | 21 / 54 / 25 (100) | 25 / 75 / 0 (20) | 25 / 52 / 23 (65) | 0 / 33 / 67 (15) |
| 3 | pico_manana | 39 / 28 / 33 (213) | 74 / 24 / 3 (38) | 35 / 27 / 38 (159) | 6 / 44 / 50 (16) |
| 3 | manana | 33 / 43 / 24 (385) | 71 / 23 / 6 (65) | 30 / 47 / 23 (223) | 13 / 49 / 37 (97) |
| 3 | valle | 28 / 53 / 20 (494) | 39 / 53 / 8 (88) | 26 / 50 / 24 (291) | 23 / 59 / 18 (115) |
| 3 | pico_tarde | 18 / 54 / 27 (234) | 27 / 54 / 19 (26) | 19 / 52 / 30 (135) | 15 / 59 / 26 (73) |
| 3 | cierre | 19 / 65 / 16 (129) | 31 / 69 / 0 (16) | 21 / 63 / 17 (78) | 11 / 69 / 20 (35) |

**Tabla 2. Clase real → clase con la recomendación (% de franjas)**

| Ruta | Bloque | Franjas | Sobrecargada real → rec. | Normal real → rec. | Subutilizada real → rec. | % misma clase |
|---|---|---|---|---|---|---|
| 1 | todos | 1483 | 16,2 → 23,0 | 60,8 → 42,4 | 23,1 → 34,6 | 56,1 |
| 1 | madrugada | 52 | 15,4 → 17,3 | 69,2 → 44,2 | 15,4 → 38,5 | 65,4 |
| 1 | pico_manana | 211 | 17,5 → 25,1 | 65,9 → 46,9 | 16,6 → 28,0 | 61,1 |
| 1 | manana | 367 | 16,1 → 18,5 | 60,5 → 44,7 | 23,4 → 36,8 | 55,9 |
| 1 | valle | 477 | 19,5 → 24,9 | 57,4 → 43,4 | 23,1 → 31,7 | 53,2 |
| 1 | pico_tarde | 223 | 12,1 → 27,4 | 61,9 → 34,5 | 26,0 → 38,1 | 52,5 |
| 1 | cierre | 153 | 10,5 → 20,3 | 60,1 → 38,6 | 29,4 → 41,2 | 60,8 |
| 3 | todos | 1555 | 16,3 → 23,9 | 61,2 → 43,0 | 22,6 → 33,1 | 58,4 |
| 3 | madrugada | 100 | 20,0 → 29,0 | 65,0 → 47,0 | 15,0 → 24,0 | 58,0 |
| 3 | pico_manana | 213 | 17,8 → 20,7 | 74,6 → 62,0 | 7,5 → 17,4 | 55,9 |
| 3 | manana | 385 | 16,9 → 18,4 | 57,9 → 46,8 | 25,2 → 34,8 | 50,9 |
| 3 | valle | 494 | 17,8 → 25,9 | 58,9 → 36,2 | 23,3 → 37,9 | 60,9 |
| 3 | pico_tarde | 234 | 11,1 → 31,6 | 57,7 → 32,1 | 31,2 → 36,3 | 61,5 |
| 3 | cierre | 129 | 12,4 → 20,2 | 60,5 → 42,6 | 27,1 → 37,2 | 69,8 |

**Tabla 3. Totales por jornada y ajuste de factibilidad**

| Ruta | Bloque | Jornadas | Total recomendado | Total real | Diferencia % | Media por jornada rec. / real | Jornadas rec. > / = / < real | Jornadas con ajuste | Jornadas con retiro (despachos) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | todos | 66 | 3515 | 3454 | 1,8 | 53,3 / 52,3 | 28 / 5 / 33 | 5 | 2 (7) |
| 1 | madrugada | 52 | 143 | 132 | 8,3 | 2,8 / 2,5 | 16 / 32 / 4 | 5 | 1 (1) |
| 1 | pico_manana | 55 | 583 | 580 | 0,5 | 10,6 / 10,5 | 22 / 17 / 16 | 5 | 1 (1) |
| 1 | manana | 66 | 937 | 897 | 4,5 | 14,2 / 13,6 | 33 / 15 / 18 | 5 | 0 (0) |
| 1 | valle | 66 | 1035 | 1040 | −0,5 | 15,7 / 15,8 | 22 / 16 / 28 | 5 | 2 (5) |
| 1 | pico_tarde | 65 | 513 | 507 | 1,2 | 7,9 / 7,8 | 25 / 16 / 24 | 5 | 0 (0) |
| 1 | cierre | 57 | 304 | 298 | 2,0 | 5,3 / 5,2 | 23 / 16 / 18 | 5 | 0 (0) |
| 3 | todos | 68 | 3885 | 3818 | 1,8 | 57,1 / 56,1 | 32 / 12 / 24 | 5 | 5 (7) |
| 3 | madrugada | 53 | 238 | 244 | −2,5 | 4,5 / 4,6 | 15 / 20 / 18 | 5 | 5 (6) |
| 3 | pico_manana | 54 | 916 | 911 | 0,5 | 17,0 / 16,9 | 24 / 9 / 21 | 5 | 1 (1) |
| 3 | manana | 68 | 959 | 910 | 5,4 | 14,1 / 13,4 | 35 / 12 / 21 | 5 | 0 (0) |
| 3 | valle | 68 | 1132 | 1089 | 3,9 | 16,6 / 16,0 | 26 / 22 / 20 | 5 | 0 (0) |
| 3 | pico_tarde | 68 | 437 | 466 | −6,2 | 6,4 / 6,9 | 15 / 23 / 30 | 5 | 0 (0) |
| 3 | cierre | 51 | 203 | 198 | 2,5 | 4,0 / 3,9 | 14 / 26 / 11 | 5 | 0 (0) |

### Divisor ordinario, con tope

**Tabla 1. Despachos recomendados frente a reales, por clase real**

| Ruta | Bloque | Todas | Sobrecargada | Normal | Subutilizada |
|---|---|---|---|---|---|
| 1 | todos | 29 / 50 / 21 (1483) | 53 / 38 / 10 (240) | 27 / 52 / 21 (901) | 20 / 52 / 28 (342) |
| 1 | madrugada | 29 / 60 / 12 (52) | 25 / 50 / 25 (8) | 31 / 61 / 8 (36) | 25 / 62 / 12 (8) |
| 1 | pico_manana | 25 / 54 / 21 (211) | 49 / 43 / 8 (37) | 19 / 58 / 24 (139) | 23 / 51 / 26 (35) |
| 1 | manana | 29 / 47 / 24 (367) | 58 / 31 / 12 (59) | 27 / 51 / 22 (222) | 16 / 47 / 37 (86) |
| 1 | valle | 27 / 49 / 24 (477) | 54 / 40 / 6 (93) | 24 / 51 / 25 (274) | 12 / 53 / 35 (110) |
| 1 | pico_tarde | 35 / 48 / 18 (223) | 52 / 37 / 11 (27) | 32 / 48 / 20 (138) | 33 / 52 / 16 (58) |
| 1 | cierre | 35 / 53 / 12 (153) | 56 / 31 / 12 (16) | 36 / 52 / 12 (92) | 27 / 62 / 11 (45) |
| 3 | todos | 34 / 46 / 19 (1555) | 57 / 38 / 4 (253) | 33 / 45 / 22 (951) | 22 / 54 / 23 (351) |
| 3 | madrugada | 34 / 40 / 26 (100) | 60 / 40 / 0 (20) | 29 / 46 / 25 (65) | 20 / 13 / 67 (15) |
| 3 | pico_manana | 39 / 28 / 33 (213) | 74 / 24 / 3 (38) | 35 / 27 / 38 (159) | 6 / 44 / 50 (16) |
| 3 | manana | 33 / 45 / 22 (385) | 68 / 26 / 6 (65) | 31 / 48 / 21 (223) | 13 / 52 / 35 (97) |
| 3 | valle | 34 / 52 / 14 (494) | 49 / 47 / 5 (88) | 31 / 52 / 17 (291) | 30 / 57 / 12 (115) |
| 3 | pico_tarde | 38 / 46 / 16 (234) | 46 / 46 / 8 (26) | 41 / 41 / 18 (135) | 30 / 55 / 15 (73) |
| 3 | cierre | 25 / 64 / 12 (129) | 38 / 62 / 0 (16) | 28 / 59 / 13 (78) | 11 / 74 / 14 (35) |

**Tabla 2. Clase real → clase con la recomendación (% de franjas)**

| Ruta | Bloque | Franjas | Sobrecargada real → rec. | Normal real → rec. | Subutilizada real → rec. | % misma clase |
|---|---|---|---|---|---|---|
| 1 | todos | 1483 | 16,2 → 21,3 | 60,8 → 42,3 | 23,1 → 36,4 | 57,2 |
| 1 | madrugada | 52 | 15,4 → 17,3 | 69,2 → 44,2 | 15,4 → 38,5 | 67,3 |
| 1 | pico_manana | 211 | 17,5 → 26,1 | 65,9 → 44,5 | 16,6 → 29,4 | 60,2 |
| 1 | manana | 367 | 16,1 → 19,9 | 60,5 → 44,7 | 23,4 → 35,4 | 55,0 |
| 1 | valle | 477 | 19,5 → 24,5 | 57,4 → 43,2 | 23,1 → 32,3 | 54,3 |
| 1 | pico_tarde | 223 | 12,1 → 20,2 | 61,9 → 36,8 | 26,0 → 43,0 | 57,8 |
| 1 | cierre | 153 | 10,5 → 11,1 | 60,1 → 37,9 | 29,4 → 51,0 | 63,4 |
| 3 | todos | 1555 | 16,3 → 19,2 | 61,2 → 41,9 | 22,6 → 38,8 | 57,2 |
| 3 | madrugada | 100 | 20,0 → 24,0 | 65,0 → 41,0 | 15,0 → 35,0 | 45,0 |
| 3 | pico_manana | 213 | 17,8 → 20,7 | 74,6 → 62,0 | 7,5 → 17,4 | 55,9 |
| 3 | manana | 385 | 16,9 → 17,4 | 57,9 → 47,0 | 25,2 → 35,6 | 52,2 |
| 3 | valle | 494 | 17,8 → 19,6 | 58,9 → 37,4 | 23,3 → 42,9 | 61,7 |
| 3 | pico_tarde | 234 | 11,1 → 19,2 | 57,7 → 26,5 | 31,2 → 54,3 | 56,8 |
| 3 | cierre | 129 | 12,4 → 17,1 | 60,5 → 39,5 | 27,1 → 43,4 | 66,7 |

**Tabla 3. Totales por jornada y ajuste de factibilidad**

| Ruta | Bloque | Jornadas | Total recomendado | Total real | Diferencia % | Media por jornada rec. / real | Jornadas rec. > / = / < real | Jornadas con ajuste | Jornadas con retiro (despachos) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | todos | 66 | 3587 | 3454 | 3,9 | 54,3 / 52,3 | 30 / 10 / 26 | 18 | 14 (53) |
| 1 | madrugada | 52 | 141 | 132 | 6,8 | 2,7 / 2,5 | 15 / 31 / 6 | 18 | 5 (5) |
| 1 | pico_manana | 55 | 586 | 580 | 1,0 | 10,7 / 10,5 | 22 / 17 / 16 | 18 | 3 (3) |
| 1 | manana | 66 | 926 | 897 | 3,2 | 14,0 / 13,6 | 30 / 16 / 20 | 18 | 4 (5) |
| 1 | valle | 66 | 1044 | 1040 | 0,4 | 15,8 / 15,8 | 25 / 16 / 25 | 18 | 14 (35) |
| 1 | pico_tarde | 65 | 553 | 507 | 9,1 | 8,5 / 7,8 | 30 / 22 / 13 | 18 | 0 (0) |
| 1 | cierre | 57 | 337 | 298 | 13,1 | 5,9 / 5,2 | 32 / 15 / 10 | 18 | 5 (5) |
| 3 | todos | 68 | 4073 | 3818 | 6,7 | 59,9 / 56,1 | 40 / 6 / 22 | 18 | 18 (38) |
| 3 | madrugada | 53 | 246 | 244 | 0,8 | 4,6 / 4,6 | 18 / 15 / 20 | 18 | 18 (28) |
| 3 | pico_manana | 54 | 916 | 911 | 0,5 | 17,0 / 16,9 | 24 / 9 / 21 | 18 | 1 (1) |
| 3 | manana | 68 | 967 | 910 | 6,3 | 14,2 / 13,4 | 34 / 14 / 20 | 18 | 3 (3) |
| 3 | valle | 68 | 1204 | 1089 | 10,6 | 17,7 / 16,0 | 43 / 15 / 10 | 18 | 3 (3) |
| 3 | pico_tarde | 68 | 525 | 466 | 12,7 | 7,7 / 6,9 | 35 / 25 / 8 | 18 | 0 (0) |
| 3 | cierre | 51 | 215 | 198 | 8,6 | 4,2 / 3,9 | 22 / 22 / 7 | 18 | 3 (3) |

### Divisor ordinario, sin tope

**Tabla 1. Despachos recomendados frente a reales, por clase real**

| Ruta | Bloque | Todas | Sobrecargada | Normal | Subutilizada |
|---|---|---|---|---|---|
| 1 | todos | 26 / 51 / 23 (1483) | 52 / 38 / 10 (240) | 24 / 53 / 23 (901) | 14 / 54 / 32 (342) |
| 1 | madrugada | 31 / 62 / 8 (52) | 25 / 75 / 0 (8) | 33 / 61 / 6 (36) | 25 / 50 / 25 (8) |
| 1 | pico_manana | 23 / 56 / 21 (211) | 49 / 43 / 8 (37) | 17 / 60 / 23 (139) | 20 / 51 / 29 (35) |
| 1 | manana | 29 / 48 / 23 (367) | 58 / 31 / 12 (59) | 27 / 53 / 20 (222) | 15 / 48 / 37 (86) |
| 1 | valle | 26 / 49 / 25 (477) | 55 / 37 / 9 (93) | 22 / 51 / 27 (274) | 10 / 54 / 36 (110) |
| 1 | pico_tarde | 26 / 49 / 26 (223) | 52 / 33 / 15 (27) | 26 / 46 / 28 (138) | 12 / 62 / 26 (58) |
| 1 | cierre | 25 / 55 / 20 (153) | 44 / 44 / 12 (16) | 26 / 53 / 21 (92) | 16 / 62 / 22 (45) |
| 3 | todos | 27 / 49 / 24 (1555) | 49 / 45 / 7 (253) | 26 / 48 / 27 (951) | 15 / 56 / 29 (351) |
| 3 | madrugada | 21 / 54 / 25 (100) | 25 / 75 / 0 (20) | 25 / 52 / 23 (65) | 0 / 33 / 67 (15) |
| 3 | pico_manana | 39 / 28 / 33 (213) | 74 / 24 / 3 (38) | 35 / 27 / 38 (159) | 6 / 44 / 50 (16) |
| 3 | manana | 31 / 44 / 24 (385) | 68 / 26 / 6 (65) | 29 / 47 / 24 (223) | 12 / 51 / 37 (97) |
| 3 | valle | 27 / 53 / 20 (494) | 39 / 53 / 8 (88) | 25 / 51 / 24 (291) | 22 / 60 / 18 (115) |
| 3 | pico_tarde | 17 / 56 / 27 (234) | 27 / 54 / 19 (26) | 16 / 55 / 30 (135) | 15 / 59 / 26 (73) |
| 3 | cierre | 19 / 65 / 16 (129) | 31 / 69 / 0 (16) | 21 / 63 / 17 (78) | 11 / 69 / 20 (35) |

**Tabla 2. Clase real → clase con la recomendación (% de franjas)**

| Ruta | Bloque | Franjas | Sobrecargada real → rec. | Normal real → rec. | Subutilizada real → rec. | % misma clase |
|---|---|---|---|---|---|---|
| 1 | todos | 1483 | 16,2 → 23,5 | 60,8 → 42,9 | 23,1 → 33,6 | 56,8 |
| 1 | madrugada | 52 | 15,4 → 17,3 | 69,2 → 44,2 | 15,4 → 38,5 | 65,4 |
| 1 | pico_manana | 211 | 17,5 → 25,6 | 65,9 → 46,9 | 16,6 → 27,5 | 61,6 |
| 1 | manana | 367 | 16,1 → 19,1 | 60,5 → 45,8 | 23,4 → 35,1 | 56,1 |
| 1 | valle | 477 | 19,5 → 25,4 | 57,4 → 43,8 | 23,1 → 30,8 | 54,1 |
| 1 | pico_tarde | 223 | 12,1 → 28,3 | 61,9 → 35,0 | 26,0 → 36,8 | 54,3 |
| 1 | cierre | 153 | 10,5 → 20,9 | 60,1 → 38,6 | 29,4 → 40,5 | 61,4 |
| 3 | todos | 1555 | 16,3 → 24,3 | 61,2 → 43,3 | 22,6 → 32,3 | 59,0 |
| 3 | madrugada | 100 | 20,0 → 29,0 | 65,0 → 47,0 | 15,0 → 24,0 | 58,0 |
| 3 | pico_manana | 213 | 17,8 → 20,7 | 74,6 → 62,0 | 7,5 → 17,4 | 55,9 |
| 3 | manana | 385 | 16,9 → 19,5 | 57,9 → 46,8 | 25,2 → 33,8 | 51,7 |
| 3 | valle | 494 | 17,8 → 26,3 | 58,9 → 36,6 | 23,3 → 37,0 | 61,3 |
| 3 | pico_tarde | 234 | 11,1 → 31,6 | 57,7 → 33,8 | 31,2 → 34,6 | 63,2 |
| 3 | cierre | 129 | 12,4 → 20,2 | 60,5 → 42,6 | 27,1 → 37,2 | 69,8 |

**Tabla 3. Totales por jornada y ajuste de factibilidad**

| Ruta | Bloque | Jornadas | Total recomendado | Total real | Diferencia % | Media por jornada rec. / real | Jornadas rec. > / = / < real | Jornadas con ajuste | Jornadas con retiro (despachos) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | todos | 66 | 3492 | 3454 | 1,1 | 52,9 / 52,3 | 25 / 4 / 37 | 5 | 2 (7) |
| 1 | madrugada | 52 | 143 | 132 | 8,3 | 2,8 / 2,5 | 16 / 32 / 4 | 5 | 1 (1) |
| 1 | pico_manana | 55 | 582 | 580 | 0,3 | 10,6 / 10,5 | 21 / 18 / 16 | 5 | 1 (1) |
| 1 | manana | 66 | 928 | 897 | 3,5 | 14,1 / 13,6 | 31 / 15 / 20 | 5 | 0 (0) |
| 1 | valle | 66 | 1027 | 1040 | −1,2 | 15,6 / 15,8 | 20 / 16 / 30 | 5 | 2 (5) |
| 1 | pico_tarde | 65 | 509 | 507 | 0,4 | 7,8 / 7,8 | 22 / 18 / 25 | 5 | 0 (0) |
| 1 | cierre | 57 | 303 | 298 | 1,7 | 5,3 / 5,2 | 22 / 17 / 18 | 5 | 0 (0) |
| 3 | todos | 68 | 3866 | 3818 | 1,3 | 56,9 / 56,1 | 30 / 11 / 27 | 5 | 5 (7) |
| 3 | madrugada | 53 | 238 | 244 | −2,5 | 4,5 / 4,6 | 15 / 20 / 18 | 5 | 5 (6) |
| 3 | pico_manana | 54 | 916 | 911 | 0,5 | 17,0 / 16,9 | 24 / 9 / 21 | 5 | 1 (1) |
| 3 | manana | 68 | 951 | 910 | 4,5 | 14,0 / 13,4 | 34 / 11 / 23 | 5 | 0 (0) |
| 3 | valle | 68 | 1125 | 1089 | 3,3 | 16,5 / 16,0 | 25 / 22 / 21 | 5 | 0 (0) |
| 3 | pico_tarde | 68 | 433 | 466 | −7,1 | 6,4 / 6,9 | 12 / 26 / 30 | 5 | 0 (0) |
| 3 | cierre | 51 | 203 | 198 | 2,5 | 4,0 / 3,9 | 14 / 26 / 11 | 5 | 0 (0) |

## Controles de calidad

Antes de escribir el módulo se ejecutaron los tres comandos sobre la rama `consolidacion-evaluacion` como línea base. **`make lint` y `make typecheck` ya fallaban antes de este cambio**, por errores en módulos que el enunciado no permite modificar. El módulo nuevo no agrega ninguno: ruff y mypy pasan sin errores sobre `dispatch/`, el script y la prueba.

| Comando | Línea base (antes) | Después | Errores en archivos nuevos |
|---|---|---|---|
| `make lint` | 4 errores (`RUF059` en `analytics/plots.py`) | los mismos 4 | 0 |
| `make typecheck` | 41 errores en 18 archivos (63 revisados) | los mismos 41 (salida idéntica); 68 revisados | 0 |
| `make test` | 155 pasan | **172 pasan** (155 + 17 nuevas), 0 fallan | — |

Los 6 errores de `import-untyped` de mypy que hay entre los 41 vienen de que `types-PyYAML` no está declarado ni instalado. Para que `dispatch/config.py` no sume uno más, se importa con `# type: ignore[import-untyped, unused-ignore]`. Esa forma no dispara `warn_unused_ignores` si las stubs se instalan más adelante.

Verificación aislada de los archivos nuevos:

```
$ ruff check src/proyecto_grado/dispatch tests/unit/test_dispatch.py scripts/run_recomendacion_despacho.py
All checks passed!
$ mypy src/proyecto_grado/dispatch scripts/run_recomendacion_despacho.py
Success: no issues found in 7 source files
$ python -m pytest tests/unit/test_dispatch.py -p no:cacheprovider -q
.................                                                        [100%]
17 passed
```

Salida de `make lint`:

```
ruff check src/proyecto_grado tests
RUF059 Unpacked variable `fig` is never used
   --> src\proyecto_grado\analytics\plots.py:119:5
    |
117 |         }
118 |     )
119 |     fig, ax = plt.subplots(figsize=(8.2, 4.4))
    |     ^^^
120 |     sns.barplot(data=data, x="stage_label", y="rows", color=PALETTE["primary"], ax=ax)
121 |     ax.set_ylabel("Filas")
    |
help: Prefix it with an underscore or any other dummy variable pattern
RUF059 Unpacked variable `fig` is never used
   --> src\proyecto_grado\analytics\plots.py:139:5
    |
137 |         return
138 |     data = data.sort_values("count", ascending=True)
139 |     fig, ax = plt.subplots(figsize=(9.4, 5.6))
    |     ^^^
140 |     sns.barplot(data=data, x="count", y="flag", color=PALETTE["accent"], ax=ax)
141 |     ax.set_xlabel("Registros")
    |
help: Prefix it with an underscore or any other dummy variable pattern
RUF059 Unpacked variable `fig` is never used
   --> src\proyecto_grado\analytics\plots.py:158:5
    |
156 |         return
157 |     data["ruta"] = data["FK_RUTA"].astype(str)
158 |     fig, ax = plt.subplots(figsize=(7.2, 4.4))
    |     ^^^
159 |     sns.barplot(data=data, x="ruta", y="pasajeros_total", color=PALETTE["secondary"], ax=ax)
160 |     ax.set_xlabel("Ruta")
    |
help: Prefix it with an underscore or any other dummy variable pattern
RUF059 Unpacked variable `fig` is never used
   --> src\proyecto_grado\analytics\plots.py:195:5
    |
193 |     pivot.index = [weekday_labels.get(int(i), str(i)) for i in pivot.index]
194 |
195 |     fig, ax = plt.subplots(figsize=(10.8, 5.3))
    |     ^^^
196 |     sns.heatmap(
197 |         pivot,
    |
help: Prefix it with an underscore or any other dummy variable pattern
Found 4 errors.
No fixes available (4 hidden fixes can be enabled with the `--unsafe-fixes` option).
make: *** [Makefile:92: lint] Error 1
```

Salida de `make typecheck`:

```
mypy src/proyecto_grado
src\proyecto_grado\modeling\baselines.py:176: error: Returning Any from function declared to return "str"  [no-any-return]
src\proyecto_grado\modeling\baselines.py:310: error: Item "None" of "Any | None" has no attribute "rename"  [union-attr]
src\proyecto_grado\modeling\baselines.py:315: error: Item "None" of "Any | None" has no attribute "rename"  [union-attr]
src\proyecto_grado\modeling\baselines.py:320: error: Item "None" of "Any | None" has no attribute "rename"  [union-attr]
src\proyecto_grado\modeling\baselines.py:325: error: Item "None" of "Any | None" has no attribute "rename"  [union-attr]
src\proyecto_grado\modeling\baselines.py:410: error: Incompatible types in assignment (expression has type "HistoricalAverageBaseline", variable has type "RollingAverageBaseline")  [assignment]
src\proyecto_grado\modeling\splits.py:65: error: Returning Any from function declared to return "time"  [no-any-return]
src\proyecto_grado\modeling\config.py:13: error: Library stubs not installed for "yaml"  [import-untyped]
src\proyecto_grado\modeling\evaluation_config.py:11: error: Library stubs not installed for "yaml"  [import-untyped]
src\proyecto_grado\modeling\evaluation_config.py:350: error: Argument 1 to "float" has incompatible type "Any | None"; expected "str | Buffer | SupportsFloat | SupportsIndex"  [arg-type]
src\proyecto_grado\modeling\hparam_search\search_config.py:15: error: Library stubs not installed for "yaml"  [import-untyped]
src\proyecto_grado\etl\config.py:7: error: Library stubs not installed for "yaml"  [import-untyped]
src\proyecto_grado\etl\config.py:7: note: Hint: "python3 -m pip install types-PyYAML"
src\proyecto_grado\etl\config.py:7: note: (or run "mypy --install-types" to install all missing stub packages)
src\proyecto_grado\etl\config.py:7: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
src\proyecto_grado\analytics\etl_diagnostics.py:108: error: Incompatible types in assignment (expression has type "None", target has type "str")  [assignment]
src\proyecto_grado\analytics\etl_diagnostics.py:109: error: Incompatible types in assignment (expression has type "None", target has type "str")  [assignment]
src\proyecto_grado\analytics\etl_diagnostics.py:112: error: Incompatible types in assignment (expression has type "int", target has type "str")  [assignment]
src\proyecto_grado\analytics\etl_diagnostics.py:113: error: Incompatible types in assignment (expression has type "float", target has type "str")  [assignment]
src\proyecto_grado\features\time_series_builder.py:11: error: Library stubs not installed for "yaml"  [import-untyped]
src\proyecto_grado\features\time_series_builder.py:95: error: Module has no attribute "Colombia"  [attr-defined]
src\proyecto_grado\analytics\fleet_availability.py:175: error: Incompatible types in assignment (expression has type "list[Any]", variable has type "ndarray[tuple[Any, ...], dtype[Any]]")  [assignment]
src\proyecto_grado\etl\utils.py:4: error: Unused "type: ignore" comment  [unused-ignore]
src\proyecto_grado\modeling\xgboost_models.py:144: error: Unsupported operand types for - ("None" and "int")  [operator]
src\proyecto_grado\modeling\xgboost_models.py:144: note: Left operand is of type "int | None"
src\proyecto_grado\modeling\xgboost_models.py:152: error: Argument 1 to "dict" has incompatible type "dict[str, float | list[float]]"; expected "SupportsKeysAndGetItem[str, float]"  [arg-type]
src\proyecto_grado\modeling\error_analysis.py:163: error: Argument "label" to "hlines" of "Axes" has incompatible type "str | None"; expected "str"  [arg-type]
src\proyecto_grado\modeling\error_analysis.py:167: error: Argument "label" to "hlines" of "Axes" has incompatible type "str | None"; expected "str"  [arg-type]
src\proyecto_grado\features\operational_hours.py:14: error: Library stubs not installed for "yaml"  [import-untyped]
src\proyecto_grado\features\operational_hours.py:42: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
src\proyecto_grado\analytics\plots.py:231: error: Cannot call function of unknown type  [operator]
src\proyecto_grado\modeling\hparam_search\fits.py:84: error: Returning Any from function declared to return "ndarray[tuple[Any, ...], dtype[Any]]"  [no-any-return]
src\proyecto_grado\modeling\hparam_search\fits.py:178: error: Argument "out_channels" to "Conv1d" has incompatible type "int | None"; expected "int"  [arg-type]
src\proyecto_grado\modeling\hparam_search\fits.py:178: error: Argument "kernel_size" to "Conv1d" has incompatible type "int | None"; expected "int | tuple[int]"  [arg-type]
src\proyecto_grado\modeling\hparam_search\fits.py:178: error: Unsupported operand types for // ("None" and "int")  [operator]
src\proyecto_grado\modeling\hparam_search\fits.py:178: note: Left operand is of type "int | None"
src\proyecto_grado\modeling\hparam_search\fits.py:269: error: Argument 1 to "load_state_dict" of "Module" has incompatible type "dict[str, Any] | None"; expected "Mapping[str, Any]"  [arg-type]
src\proyecto_grado\dashboard\app.py:81: error: Argument 1 to "float" has incompatible type "object"; expected "str | Buffer | SupportsFloat | SupportsIndex"  [arg-type]
src\proyecto_grado\dashboard\app.py:90: error: Argument 1 to "float" has incompatible type "object"; expected "str | Buffer | SupportsFloat | SupportsIndex"  [arg-type]
src\proyecto_grado\dashboard\app.py:104: error: Returning Any from function declared to return "bytes"  [no-any-return]
src\proyecto_grado\dashboard\app.py:339: error: Need type annotation for "candidates" (hint: "candidates: list[<type>] = ...")  [var-annotated]
src\proyecto_grado\dashboard\app.py:346: error: Returning Any from function declared to return "str"  [no-any-return]
src\proyecto_grado\dashboard\app.py:1457: error: Incompatible types in assignment (expression has type "tuple[()] | tuple[date]", variable has type "date")  [assignment]
src\proyecto_grado\modeling\hparam_search\runner.py:136: error: Argument 4 to "ajustar_predecir_xgboost" has incompatible type "list[str] | None"; expected "list[str]"  [arg-type]
src\proyecto_grado\modeling\hparam_search\reevaluacion.py:113: error: "object" has no attribute "items"  [attr-defined]
src\proyecto_grado\modeling\hparam_search\reevaluacion.py:189: error: Argument 4 to "ajustar_predecir_xgboost" has incompatible type "list[str] | None"; expected "list[str]"  [arg-type]
Found 41 errors in 18 files (checked 68 source files)
make: *** [Makefile:99: typecheck] Error 1
```

Salida de `make test` (resumen):

```
============================= test session starts =============================
tests\integration\test_etl_pipeline.py .......                           [  4%]
tests\unit\test_analytics.py ........                                    [  8%]
tests\unit\test_config.py .                                              [  9%]
tests\unit\test_db.py ..........                                         [ 15%]
tests\unit\test_dispatch.py .................                            [ 25%]
tests\unit\test_evaluation_aggregation.py ....                           [ 27%]
tests\unit\test_evaluation_config.py ...                                 [ 29%]
tests\unit\test_extract.py ........                                      [ 33%]
tests\unit\test_gps.py ..                                                [ 34%]
tests\unit\test_model_ready.py .                                         [ 35%]
tests\unit\test_modeling.py ..................................           [ 55%]
tests\unit\test_operational_hours.py ........................            [ 69%]
tests\unit\test_pipeline.py .                                            [ 69%]
tests\unit\test_qc.py ..                                                 [ 70%]
tests\unit\test_temporal_eda.py ............                             [ 77%]
tests\unit\test_time_series_builder.py ...........................       [ 93%]
tests\unit\test_transforms.py ..                                         [ 94%]
tests\unit\test_trip_end.py ......                                       [ 98%]
tests\unit\test_utils.py ...                                             [100%]
============================== warnings summary ===============================
tests/unit/test_temporal_eda.py::TestAutocorrelacion::test_adf_retorna_columnas_esperadas
tests/unit/test_temporal_eda.py::TestAutocorrelacion::test_adf_is_stationary_es_bool
tests/unit/test_temporal_eda.py::TestPersistencia::test_artefactos_guardados_en_disco
tests/unit/test_temporal_eda.py::TestPersistencia::test_run_all_retorna_dict_con_seis_claves
tests/unit/test_temporal_eda.py::TestAutocorrelacion::test_adf_retorna_columnas_esperadas
tests/unit/test_temporal_eda.py::TestAutocorrelacion::test_adf_is_stationary_es_bool
tests/unit/test_temporal_eda.py::TestPersistencia::test_artefactos_guardados_en_disco
tests/unit/test_temporal_eda.py::TestPersistencia::test_run_all_retorna_dict_con_seis_claves
====================== 172 passed, 8 warnings in 16.40s =======================
```

Las 8 advertencias de `make test` vienen de `tests/unit/test_temporal_eda.py` (statsmodels) y ya estaban en la línea base.

### Pruebas de `tests/unit/test_dispatch.py`

| Prueba | Qué comprueba |
|---|---|
| `test_150_pasajeros_con_mediana_54_y_q3_65_dan_3_despachos` | 150 pasajeros con mediana 54 y Q3 65 dan 3 despachos, con y sin tope |
| `test_70_pasajeros_dan_2_con_tope_y_1_sin_tope` | 70 pasajeros: 2 con tope y 1 sin él |
| `test_redondeo_aritmetico_sube_los_medios` | 2,5 → 3 (y `round(2.5)` daría 2); 0,5, 1,5, 3,5 y 4,5 suben; 135/54 = 2,5 da 3 |
| `test_nunca_menos_despachos_que_el_minimo` (mínimo 1 y 2) | Demanda 0, negativa o pequeña en ambos regímenes, y factibilidad con capacidad 0 |
| `test_regimen_raro_usa_el_divisor_de_la_politica` | 50 pasajeros: 2 con divisor propio (22) y 1 con divisor ordinario (54); el tope no actúa en régimen raro |
| `test_factibilidad_retira_primero_de_la_franja_menos_cargada` | Retira de la franja con menor pasajeros por despacho resultante, reevalúa tras cada retiro y desempata por orden |
| `test_factibilidad_no_toca_jornadas_dentro_de_la_capacidad` | Sin exceso de capacidad, no hay cambios |
| `test_respaldo_con_la_referencia_cuando_falta_xgboost` | Falta XGBoost → referencia, `fuente = respaldo_referencia` y aviso en el registro; régimen raro → referencia; filtro de jornadas comunes |
| `test_asignar_bloque_por_hora_de_inicio` | Límites de los seis bloques y horas anteriores al primero |
| `test_preparar_despachos_toma_el_tipo_de_dia_del_dataset` | Jornada = salida − 4 h, franja de 30 min, tipo de día de la franja y, si falta, de la jornada |
| `test_tabla_de_parametros_y_capacidad` | Cuantiles lineales por ruta y bloque, mediana rara por ruta y capacidad conjunta |
| `test_clasificacion_y_comparacion_con_lo_real` | Clases, comparación mayor/igual/menor y clase con la recomendación |
| `test_carga_configuracion_de_recomendacion` | Valores del YAML y período de evaluación tomado del contrato comparativo |
| `test_rechaza_reglas_invalidas` (3 casos) | Política desconocida, servicio mínimo 0 y tope no booleano |

## Reproducción

```
python scripts/run_recomendacion_despacho.py
```

El manifiesto `manifiesto__recomendacion_despacho__freeze_20260922_203820.json` registra la ruta y el SHA-256 de cada entrada, los parámetros, la tabla calibrada, las verificaciones y el resumen de cada combinación.
