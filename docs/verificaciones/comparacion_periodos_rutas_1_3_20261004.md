# Rutas 1 y 3: comparación entre el 1 de abril al 10 de junio y el 11 de junio al 3 de octubre de 2026

Consulta del 2026-10-04 sobre `bd_montebello_rdw`, solo con sentencias de lectura (`SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN`). Las consultas livianas (catálogos y tablas de configuración de pocas filas) se hicieron por la tarde. Las pesadas (planilla de despacho, unas 600 mil entradas de índice, y `tbl_registro_log`, que no tiene índice por fecha) se ejecutaron a las 21:37, fuera del horario de operación, y terminaron en 7 segundos. Los datos no pasaron por el ETL. No se modificó ningún archivo del repositorio ni ningún dato de la base.

**P1** = 2026-04-01 a 2026-06-10; **P2** = 2026-06-11 a 2026-10-03, por fecha programada del despacho (`FECHA_INICIAL`).

## Definiciones

- **Despacho.** `tbl_intervalo_despacho` con `ESTADO = 1`. La ruta sale de la registradora (`FK_RUTA`) o, si no hay registro de registradora, de `LISTA_RUTA`, que coincide con `FK_RUTA` cuando existen ambas.
  - Cuando un despacho tiene dos registros de registradora, se usa el último, como el ETL.
- **Duración.** Hora real de llegada (`tbl_planilla_despacho`, `TIPO_PUNTO = 3`) menos hora real de salida (`TIPO_PUNTO = 1`), cada una con su `FECHA`.
  - Solo cuentan los despachos que tienen las dos horas reales y una duración entre 5 y 480 minutos, el mismo rango que usa el ETL para el conjunto apto. Fuera de ese rango quedan entre 3 y 6 despachos por ruta y período.
  - Ningún despacho tiene más de una fila de salida o de llegada en la planilla.
- **Distancia.** `tbl_informacion_registradora.DISTANCIA_METROS`. Se excluyen las distancias en 0 (entre 134 y 267 por ruta y período); no hay nulos.
- **Pasajeros por despacho.** `DIFERENCIA_NUM`, el conteo crudo, sin descontar las alarmas de bloqueo; no hay nulos.
- **Despachos por franja en día laboral.**
  - Día laboral: lunes a viernes que no es festivo en Colombia.
  - Franja: hora real de salida truncada a 30 minutos o, si falta, la hora programada (650 de 17.584 despachos).
  - Para cada ruta, se promedia el número de despachos de cada franja sobre los días laborales del período, contando como 0 las franjas sin despachos. Se incluyen todas las franjas con algún despacho laboral de esa ruta en cualquiera de los dos períodos.
  - P1 tiene 45 días laborales y P2, 77.

## Resultados

| Ruta | Indicador | P1 | P2 | Variación |
|---|---|---|---|---|
| 1 | Despachos (con registradora) | 3.740 (3.692) | 4.635 (4.584) | — |
| 1 | Con hora real de salida y de llegada | 80,7 % | 83,0 % | — |
| 1 | Mediana de duración (min) | 153,7 | 152,6 | −0,7 % |
| 1 | P95 de duración (min) | 202,8 | 204,5 | +0,8 % |
| 1 | Mediana de distancia (km) | 37,60 | 37,45 | −0,4 % |
| 1 | Mediana de pasajeros por despacho | 43 | 44 | +2,3 % |
| 3 | Despachos (con registradora) | 4.064 (3.990) | 5.145 (5.081) | — |
| 3 | Con hora real de salida y de llegada | 79,2 % | 80,3 % | — |
| 3 | Mediana de duración (min) | 166,7 | 167,3 | +0,4 % |
| 3 | P95 de duración (min) | 212,4 | 212,4 | +0,0 % |
| 3 | Mediana de distancia (km) | 42,31 | 42,63 | +0,8 % |
| 3 | Mediana de pasajeros por despacho | 48 | 48 | +0,0 % |
| 1 | Despachos promedio por franja de 30 min, día laboral | 2,27 | 1,63 | −28,2 % |
| 1 | Despachos promedio por día laboral | 68,1 | 48,9 | −28,2 % |
| 3 | Despachos promedio por franja de 30 min, día laboral | 2,54 | 1,86 | −26,9 % |
| 3 | Despachos promedio por día laboral | 73,7 | 53,9 | −26,9 % |

### Despachos promedio por hora en día laboral (suma de las dos franjas de cada hora)

| Hora | Ruta 1 · P1 | Ruta 1 · P2 | Ruta 3 · P1 | Ruta 3 · P2 |
|---|---|---|---|---|
| 04:00–04:59 | 2,82 | 2,61 | 5,07 | 5,51 |
| 05:00–05:59 | 5,98 | 3,87 | 9,78 | 6,79 |
| 06:00–06:59 | 5,53 | 3,87 | 7,47 | 5,35 |
| 07:00–07:59 | 5,33 | 4,04 | 5,40 | 3,83 |
| 08:00–08:59 | 5,24 | 3,84 | 5,42 | 4,16 |
| 09:00–09:59 | 5,58 | 4,10 | 5,62 | 4,34 |
| 10:00–10:59 | 5,00 | 3,34 | 5,24 | 3,71 |
| 11:00–11:59 | 4,78 | 3,49 | 4,87 | 3,40 |
| 12:00–12:59 | 5,20 | 4,08 | 5,67 | 3,97 |
| 13:00–13:59 | 5,04 | 3,66 | 5,18 | 3,47 |
| 14:00–14:59 | 5,09 | 3,70 | 5,00 | 3,55 |
| 15:00–15:59 | 5,78 | 4,29 | 4,56 | 3,16 |
| 16:00–16:59 | 5,09 | 3,27 | 3,51 | 2,36 |
| 17:00–17:59 | 1,56 | 0,65 | 0,89 | 0,27 |
| 18:00–18:59 | 0,07 | 0,04 | 0,02 | 0,00 |
| 19:00–19:59 | 0,00 | 0,01 | — | — |

**Lectura.**
- **Viaje.** La duración, la distancia y los pasajeros por despacho prácticamente no cambian entre los dos períodos:
  - Las medianas varían menos del 1 % y el P95 de duración, menos del 1 %.
  - La mediana de pasajeros por despacho es de 43 frente a 44 en la ruta 1 e igual (48) en la ruta 3.
- **Despachos en día laboral.** Sí cambian: desde el 11 de junio hay entre un 27 % y un 28 % menos de despachos en las dos rutas (de 68 a 49 por día en la ruta 1 y de 74 a 54 en la ruta 3). La reducción se reparte a lo largo de todo el día, y es más marcada en el pico de la mañana de la ruta 3, que pasa de unos 10 a unos 7 despachos entre las 05:00 y las 05:59.
- **Alcance.** Esta consulta no explica la causa. Coincide con la caída semanal ya observada en el informe `consulta_bd_despachos_desde_20260601.md`.

## Condición para lanzar el ETL

El ETL hacia `data/actualizacion_20261004/` solo se lanzaba si, en las dos rutas, la mediana de duración variaba como mucho un 15 % y la mediana de distancia como mucho un 10 %, medido como |P2 − P1| / P1.

| Ruta | Mediana | P1 | P2 | Variación relativa | Umbral | ¿Supera? |
|---|---|---|---|---|---|---|
| 1 | duración | 153,73 | 152,63 | 0,72 % | 15 % | no |
| 1 | distancia | 37,60 | 37,45 | 0,42 % | 10 % | no |
| 3 | duración | 166,68 | 167,32 | 0,38 % | 15 % | no |
| 3 | distancia | 42,31 | 42,63 | 0,76 % | 10 % | no |

**Decisión: ninguna diferencia supera su umbral, por lo que el ETL se lanzó a las 21:38 sin esperar confirmación**, como se había pedido. Proceso desacoplado, con fecha fin 2026-10-03; se detiene a las 04:00 si no ha terminado. La condición no evalúa la reducción de despachos por día, que no afecta al recorrido.

## ¿Hubo cambios de recorrido, puntos de control o geometría en 2026?

No se encontró ningún registro de cambio de recorrido, de puntos de control ni de geometría de las rutas 1 y 3 en 2026.

| Fuente | Qué contiene | Resultado en 2026 |
|---|---|---|
| `tbl_auditoria_ruta` | Cambios en las rutas | Ningún evento. Los últimos de las rutas 1 y 3 son del 2025-12-02 y el 2025-11-27, cuando se crearon las geozonas `SIU_MOJICA` y `SIU_TEXACO3`. |
| `tbl_auditoria_punto`, `tbl_auditoria_punto_control`, `tbl_auditoria_ruta_punto` | Cambios de nombre o coordenadas de puntos | Ningún evento. El último es del 2025-12-31 (renombre de P35 y P39). Las dos últimas tablas están vacías. |
| `tbl_punto` | Puntos de control (40) | Ninguno modificado en 2026. |
| `tbl_ruta_punto` | Puntos asignados a cada ruta | Ninguno modificado en 2026. Los activos de la ruta 1 son del 2024-04-23 y los de la ruta 3, del 2025-01-21. |
| `tbl_ruta_trayectoria`, `tbl_ruta_trayectoria_puntos` | Geometría de las rutas | Sin cambios. Los trazados de las rutas 1 y 3 se cargaron por última vez el 2025-04-25. |
| `tbl_geozona` | Geozonas (11) | Ninguna creada ni modificada en 2026. |
| `tbl_ruta`, `tbl_ruta_modo` | Rutas y su modo | Sin cambios en 2026. |
| `tbl_configuracion_despacho` | Puntos y tiempos de cada configuración de despacho | No guarda fechas. Su uso real se comprobó en la planilla (fila siguiente). |
| `tbl_planilla_despacho` | Puntos efectivamente registrados por despacho | Sin cambios entre P1 y P2 (tabla siguiente). |
| `tbl_geozona_puntocontrol` | Envíos de puntos de control a los equipos GPS | Mismo conjunto en todo 2025 y 2026: 22 puntos para la ruta 1 y 20 para la ruta 3. |
| `tbl_gps_geozona_puntocontrol` | Configuración por equipo GPS | 104 registros creados y algunos modificados en 2026: configuración de equipos concretos (cuatro en febrero, uno en mayo), no cambios de ruta. |
| `tbl_registro_log` | Registro general del sistema | 2026-01: 32, 2026-02: 33, 2026-03: 7, 2026-04: 45, 2026-05: 50, 2026-06: 32, 2026-07: 27, 2026-08: 23, 2026-09: 36 entradas por mes en 2026. Ninguna menciona rutas, puntos, trayectorias, geozonas, configuración de despacho ni recorridos. |

**Puntos registrados en la planilla por despacho:**

| Ruta | Período | Configuración de despacho | Puntos intermedios | Puntos |
|---|---|---|---|---|
| 1 | P1 | 1 (3.740 despachos) | 13 | p1, p2, p22, p24, p26, p27, p3, p31, p38, p4, p5, p7, p9 |
| 1 | P2 | 1 (4.635 despachos) | 13 | p1, p2, p22, p24, p26, p27, p3, p31, p38, p4, p5, p7, p9 |
| 3 | P1 | 7 (4.064 despachos) | 11 | p1, p10, p14, p23, p29, p38, p5, p6, p7, p8, p9 |
| 3 | P2 | 7 (5.145 despachos) | 11 | p1, p10, p14, p23, p29, p38, p5, p6, p7, p8, p9 |

- **Configuración:** cada ruta usó una sola configuración en los dos períodos, la 1 en la ruta 1 y la 7 en la ruta 3, con los mismos puntos de salida (`p911`), llegada (`p910`) e intermedios.
- **Paso doble:** `p27` en la ruta 1 y `p9` en la ruta 3 aparecen dos veces por despacho, porque el recorrido pasa dos veces por ellos.
- **Dato aparte:** el punto `p38` (Mojica) tiene hora real en mucho menos despachos que los demás, en ambos períodos y rutas, y el `p9` de la ruta 1 también.

**Dato del sistema:** `tbl_punto`, `tbl_geozona` y `tbl_ruta_modo` se crearon de nuevo el 2026-05-07 a las 22:35, lo que sugiere una actualización del software. Ninguna fila de esas tablas cambió en 2026, y la planilla no muestra cambios de puntos entre P1 y P2.

## Consultas de la tanda nocturna

Todas en `bd_montebello_rdw`, a las 21:37:
- `tbl_informacion_registradora` unida a `tbl_intervalo_despacho`, filtrada por `FECHA_SALIDA_BASE_SALIDA` (con índice) entre 2026-03-31 y 2026-10-04 y rutas 1 y 3.
- `tbl_intervalo_despacho` por rango de clave primaria.
- `tbl_planilla_despacho`, con `TIPO_PUNTO` 1 y 3 por despacho y un agregado de puntos por ruta, configuración y período, por rango de `FK_INTERVALO_DESPACHO` (con índice).
- `tbl_registro_log` desde 2026-01-01: conteo mensual y búsqueda de menciones de tablas de ruta, punto, trayectoria, geozona, configuración de despacho y recorrido.
