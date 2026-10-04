# Disponibilidad de vehículos en patio en los intervalos largos entre despachos

Fecha: 2026-09-27. Rama `consolidacion-evaluacion`, último commit `e504b29`. Sin commits.

## Qué se hizo

- **Script nuevo**: `analisis/28_disponibilidad_patio_intervalos_largos.py`. No está en git (`??`).
- **Reutilización**: el script importa, sin modificarlas, las funciones y constantes de `src/proyecto_grado/analytics/fleet_availability.py`, que no tiene cambios sin comprometer:
  - `FleetAvailabilityAnalyzer._preparar` y `_reconstruir_timeline`;
  - `PICO_MANANA`, `PICO_TARDE` y `CIERRE`.
- **Archivos**: solo se crearon archivos nuevos; no se sobrescribió ninguno existente.
- **Artefactos persistidos** en `analisis/salidas/`:
  - `intervalos_largos_patio__detalle.csv`: un registro por intervalo largo y umbral (20.384 registros). Incluye fecha, ruta, salidas que abren y cierran el intervalo, instante evaluado, vehículos en patio y los indicadores de sensibilidad.
  - `intervalos_largos_patio__resumen.csv`: agregado por umbral, ruta y franja, con dos agrupaciones: las ventanas de `fleet_availability.py` y la hora entera.
  - `manifiesto__intervalos_largos_patio.json`: origen, criterios, conteos y resultado del contraste.

## Criterio exacto

**Universo**
- Despachos de `data/processed/model_ready/despachos_model_ready.parquet` de las rutas 1 y 3, con `MODEL_READY_OK` y `HORA_FIN_FINAL` no nula: 109.559 despachos.
- Jornadas: las 785 fechas con conteo de pasajeros en el parquet de modelado (`freeze_20260823_203700`). Coinciden con todas las fechas de `model_ready`.

**Ocupación del patio** (idéntica a `fleet_availability.py`)
- Por día calendario (`FECHA_INICIAL`) y por placa, un vehículo está EN_PATIO desde la `HORA_FIN_FINAL` de un recorrido hasta la `HORA_INICIAL_REAL` de su siguiente recorrido del mismo día.
- Se descartan los tramos con inicio ≥ fin.
- Un vehículo cuenta en el instante t si `inicio ≤ t < fin`.
- El patio es común a ambas rutas. Las 67 placas operan las dos rutas, y en 27.068 de las 30.182 combinaciones placa-día alternan de ruta dentro de la jornada.
- `fleet_availability.py` muestrea la ocupación cada 5 minutos para sus promedios. Aquí se evalúa de forma exacta en el instante requerido, con la misma regla de pertenencia.

**Intervalo largo** (idéntico a `fleet_availability.py::_headways_largos_franjas`)
- Por día calendario y ruta, es la diferencia entre salidas consecutivas (`HORA_INICIAL_REAL` ordenada) estrictamente mayor que el umbral: 15 o 30 minutos.
- Restricción añadida en este análisis: la salida que abre el intervalo y la que lo cierra deben estar ambas en [04:00, 19:00).
- Franja: la de la hora de la salida que **cierra** el intervalo, como en `fleet_availability.py`. Las ventanas son:
  - pico mañana [05:00, 09:00);
  - pico tarde [14:00, 16:00);
  - cierre [16:30, 17:30);
  - otras: el resto.

**Disponibilidad (criterio principal)**
- Instante evaluado: t* = salida que abre el intervalo + umbral. Es el momento en que el intervalo pasa a ser largo; desde ahí hasta la salida siguiente había un despacho pendiente.
- **Patio vacío**: ningún vehículo EN_PATIO en t*.
- **Con vehículos disponibles**: al menos uno en t*.

**Sensibilidad** (tramo excedente = [t*, salida siguiente))
- `vacio_todo_tramo`: el patio estuvo vacío durante todo el tramo.
- `algun_instante_vacio`: el patio estuvo vacío en algún instante del tramo.
- `placa_siguiente_en_patio`: la placa que finalmente sale ya estaba en patio en t*.

**Validaciones**
- Sin la restricción horaria, con umbral de 15 minutos y sobre los mismos 30 días, el script reproduce exactamente los **447** intervalos largos de `reports/tables/baseline/fleet_availability_by_day.csv`.
- Una verificación independiente de la ocupación en t*, recalculada desde `model_ready` sobre 400 intervalos aleatorios, dio 0 discrepancias.

## Resultados por ruta y franja (criterio principal)

| Umbral | Ruta | Franja | Intervalos largos | % patio vacío | % con vehículos disponibles | Mediana de vehículos en patio en t* |
|---|---|---|---|---|---|---|
| 15 min | 1 | Pico mañana | 2.175 | 37,1 | 62,9 | 2 |
| 15 min | 1 | Pico tarde | 1.581 | 4,0 | 96,0 | 5 |
| 15 min | 1 | Cierre | 760 | 9,5 | 90,5 | 2 |
| 15 min | 1 | Otras | 4.741 | 7,9 | 92,1 | 4 |
| 15 min | 1 | **Total** | **9.257** | **14,2** | **85,8** | 3 |
| 15 min | 3 | Pico mañana | 1.601 | 39,0 | 61,0 | 2 |
| 15 min | 3 | Pico tarde | 1.569 | 3,6 | 96,4 | 4 |
| 15 min | 3 | Cierre | 974 | 5,6 | 94,4 | 2 |
| 15 min | 3 | Otras | 4.685 | 11,5 | 88,5 | 4 |
| 15 min | 3 | **Total** | **8.829** | **14,4** | **85,6** | 3 |
| 30 min | 1 | Pico mañana | 246 | 47,6 | 52,4 | 1 |
| 30 min | 1 | Pico tarde | 299 | 9,0 | 91,0 | 2 |
| 30 min | 1 | Cierre | 129 | 27,1 | 72,9 | 1 |
| 30 min | 1 | Otras | 847 | 15,8 | 84,2 | 2 |
| 30 min | 1 | **Total** | **1.521** | **20,6** | **79,4** | 2 |
| 30 min | 3 | Pico mañana | 198 | 51,5 | 48,5 | 0 |
| 30 min | 3 | Pico tarde | 326 | 11,7 | 88,3 | 2 |
| 30 min | 3 | Cierre | 171 | 22,8 | 77,2 | 1 |
| 30 min | 3 | Otras | 1.082 | 33,4 | 66,6 | 1 |
| 30 min | 3 | **Total** | **1.777** | **30,4** | **69,6** | 1 |

Sensibilidad, sobre el total:

| Umbral | Ruta | % vacío en todo el tramo excedente | % vacío en algún instante del tramo | % con la placa que sale ya en patio en t* |
|---|---|---|---|---|
| 15 min | 1 | 8,9 | 15,8 | 72,7 |
| 15 min | 3 | 10,5 | 16,6 | 71,3 |
| 30 min | 1 | 7,7 | 24,1 | 61,2 |
| 30 min | 3 | 19,1 | 33,6 | 54,2 |

La tabla por hora entera y el desglose de sensibilidad por franja están en `intervalos_largos_patio__resumen.csv`.

## Advertencia: artefacto de madrugada heredado del criterio

El criterio de `fleet_availability.py` no cuenta a un vehículo como disponible antes de su primer recorrido del día. Los recorridos duran unos 161 minutos: el primer vehículo del día regresa a patio, en mediana, a las **06:05** (percentil 10: 05:54; percentil 90: 08:24). Por lo tanto, en las primeras horas el patio figura vacío **por construcción**, aunque haya vehículos esperando su primera salida.

| Hora de la salida que cierra | Ruta 1, 15 min | Ruta 3, 15 min | Ruta 1, 30 min | Ruta 3, 30 min |
|---|---|---|---|---|
| 04:00 | 100 % vacío (n = 102) | 100 % (n = 335) | 100 % (n = 1) | 100 % (n = 233) |
| 05:00 | 98,9 % (n = 370) | 98,4 % (n = 243) | 100 % (n = 19) | 100 % (n = 16) |
| 06:00 | 37,3 % | 48,2 % | 46,5 % | 55,9 % |

Consecuencias:

- **Pico mañana**: las cifras de la ventana 05:00–09:00 están infladas por la hora 05:00. Restringiendo a **07:00–09:00**, la proporción con patio vacío es:

  | Umbral | Ruta 1 | Ruta 3 |
  |---|---|---|
  | 15 min | 20,2 % | 23,9 % |
  | 30 min | 42,4 % | 45,3 % |

- **Ruta 3, umbral 30, franja «otras»** (33,4 %): se explica sobre todo por 233 intervalos que cierran a las 04:00, todos con patio vacío por construcción.
- **Totales desde las 07:00 en adelante**:

  | Umbral | Ruta 1 | Ruta 3 |
  |---|---|---|
  | 15 min | 8,2 % (685 de 8.340) | 7,3 % (582 de 8.004) |
  | 30 min | 18,7 % (273 de 1.458) | 18,2 % (272 de 1.494) |

  Estas cifras se derivan del resumen por hora entera, sumando `n_patio_vacio` y `n_intervalos_largos` de las horas 07 a 18.

Para medir disponibilidad real en la madrugada haría falta modelar la presencia en patio antes del primer despacho, por ejemplo desde el fin del último recorrido de la víspera o desde el registro de GPS. Eso cambiaría el criterio de `fleet_availability.py` y no se hizo.

## Lectura

- **Fuera de la madrugada, la mayoría de los intervalos largos ocurre con vehículos en patio**:
  - con umbral de 15 minutos, más del 90 % desde las 07:00;
  - con umbral de 30 minutos, alrededor del 81 %.
- **La placa que finalmente sale ya estaba en patio en t\*** en el 71–73 % de los intervalos de 15 minutos. Esto indica que el retraso no se debe, en esos casos, a falta de vehículo.
- **El patio vacío pesa más en el pico de la mañana y en el cierre**. También pesa más cuanto más largo es el intervalo.
- **Límites del criterio**:
  - no considera un tiempo mínimo de alistamiento o descanso del conductor, así que un vehículo recién llegado cuenta como disponible;
  - no distingue vehículos fuera de servicio que permanecen en patio entre dos recorridos del mismo día.

## Estado en git

| Archivo | Estado |
|---|---|
| `analisis/28_disponibilidad_patio_intervalos_largos.py` | Nuevo, sin seguimiento (`??`) |
| `src/proyecto_grado/analytics/fleet_availability.py` (dependencia) | Sin cambios |
| Los tres artefactos de `analisis/salidas/` | Nuevos, sin seguimiento |
