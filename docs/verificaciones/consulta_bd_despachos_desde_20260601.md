# Despachos de Montebello desde el 1 de junio de 2026 en `bd_montebello_rdw`

Consulta del 2026-10-04. La extracción terminó a las 16:11, hora del servidor. Solo se ejecutaron sentencias `SELECT`, `SHOW TABLES` y `DESCRIBE`, mediante un ayudante que rechaza cualquier otra sentencia. No se escribió en la base ni se modificó ningún archivo del repositorio: este informe es el único archivo nuevo, y los datos extraídos quedaron fuera del repositorio.

## Definiciones

- **Montebello.** `tbl_empresa` tiene una sola empresa, Montebello (`PK_EMPRESA = 11`), y todas las rutas de `tbl_ruta` son suyas.
- **Despacho.** Un registro de `tbl_intervalo_despacho` con `ESTADO = 1` y `FECHA_INICIAL` igual o posterior al 2026-06-01, con el mismo filtro de estado que la extracción del ETL (`etl/extract.py`). Desde esa fecha todos los intervalos tienen `ESTADO = 1`: son 11.100.
- **Ruta y vehículo.** Se toman de `tbl_informacion_registradora` (`FK_RUTA`, `FK_VEHICULO`), unida por `FK_INTERVALO_DESPACHO`, como en el ETL.
  - 131 despachos no tienen registro de registradora (57 de la ruta 1 y 74 de la ruta 3). A esos se les asigna la ruta de `tbl_intervalo_despacho.LISTA_RUTA`, que coincide con `FK_RUTA` en todos los despachos que tienen ambas. Esos 131 no tienen vehículo, conteo ni alarmas.
  - 44 despachos tienen dos registros de registradora, siempre con la misma ruta y el mismo vehículo. Se cuentan una sola vez. Se considera que tienen conteo o alarma si cualquiera de los dos registros lo tiene.
- **Fechas y horas.** Son las programadas: `FECHA_INICIAL` y `HORA_INICIAL`. La hora real de salida está en `tbl_planilla_despacho` y no se consultó.
- **Jornada.** Día calendario (`FECHA_INICIAL`) con al menos un despacho de la ruta. Es distinta de la jornada operativa del proyecto (salida real − 4 h), que necesita la hora real; como el servicio empieza hacia las 04:00, la diferencia es mínima.
- **Semana.** Semana ISO, de lunes a domingo. El 2026-06-01 fue lunes, así que la primera semana está completa. La última (S40) incluye el 2026-10-04, que estaba en curso al consultar: tenía 13 despachos registrados, con el último programado a las 15:00.
- **Conteo de pasajeros.** `tbl_informacion_registradora.DIFERENCIA_NUM`, la columna que el ETL guarda como `PASAJEROS`.
- **Alarmas de bloqueo.** `tbl_alarma_info_regis`, unida por `FK_INFORMACION_REGISTRADORA`.
  - Criterio principal: `FK_ALARMA` 5 y 6, «Sensor Bloqueado BQ1» y «BQ2» en `tbl_alarma`, los mismos que suma el ETL en `ALARMAS`.
  - También se reporta `FK_ALARMA` 7, «Sensor Bloqueado BQ3», que el ETL no usa.
  - Se consideran las alarmas con `FECHA_ALARMA` desde el 2026-05-25, para no recorrer la tabla completa.

## 1. Rutas con despachos desde el 1 de junio de 2026

| Ruta | Nombre | Despachos | Primer despacho | Último despacho | Días con despachos |
|---|---|---|---|---|---|
| 1 | Ruta1S Mojica | 5.154 | 2026-06-01 04:43 | 2026-10-04 15:00 | 126 |
| 3 | Ruta3 Texaco | 5.714 | 2026-06-01 04:27 | 2026-10-04 15:00 | 126 |
| 5 | Ruta5 Texaco-Montebello | 232 | 2026-06-01 04:11 | 2026-10-03 04:52 | 101 |

Rutas de Montebello sin ningún despacho en el período:

| Ruta | Nombre | Estado |
|---|---|---|
| 2 | Ruta3S Vallado | 0 |
| 6 | Ruta5A Montebello-Mojica | 0 |
| 7 | RUTA REGISTEL | 0 |
| 8 | REGISTEL | 0 |
| 9 | Montebello- Mojica | 1 |
| 10 | Texaco retorno 80 | 1 |

`Estado` es `tbl_ruta.ESTADO`. Las rutas 9 y 10 están activas en el catálogo, pero no tuvieron despachos.

## 2. Despachos y jornadas por ruta y semana

Cada celda indica despachos / jornadas (días con despachos de la ruta en la semana). En la columna Total, las jornadas son los días con despachos de cualquier ruta.

| Semana ISO | Lunes a domingo | Ruta 1 | Ruta 3 | Ruta 5 | Total |
|---|---|---|---|---|---|
| 2026-S23 | 2026-06-01 a 2026-06-07 | 388 / 7 | 421 / 7 | 16 / 6 | 825 / 7 |
| 2026-S24 | 2026-06-08 a 2026-06-14 | 318 / 7 | 347 / 7 | 12 / 5 | 677 / 7 |
| 2026-S25 | 2026-06-15 a 2026-06-21 | 307 / 7 | 337 / 7 | 14 / 5 | 658 / 7 |
| 2026-S26 | 2026-06-22 a 2026-06-28 | 335 / 7 | 372 / 7 | 16 / 6 | 723 / 7 |
| 2026-S27 | 2026-06-29 a 2026-07-05 | 290 / 7 | 320 / 7 | 13 / 5 | 623 / 7 |
| 2026-S28 | 2026-07-06 a 2026-07-12 | 311 / 7 | 348 / 7 | 11 / 6 | 670 / 7 |
| 2026-S29 | 2026-07-13 a 2026-07-19 | 273 / 7 | 294 / 7 | 9 / 5 | 576 / 7 |
| 2026-S30 | 2026-07-20 a 2026-07-26 | 255 / 7 | 278 / 7 | 11 / 5 | 544 / 7 |
| 2026-S31 | 2026-07-27 a 2026-08-02 | 284 / 7 | 316 / 7 | 15 / 6 | 615 / 7 |
| 2026-S32 | 2026-08-03 a 2026-08-09 | 250 / 7 | 276 / 7 | 13 / 5 | 539 / 7 |
| 2026-S33 | 2026-08-10 a 2026-08-16 | 260 / 7 | 291 / 7 | 12 / 6 | 563 / 7 |
| 2026-S34 | 2026-08-17 a 2026-08-23 | 251 / 7 | 281 / 7 | 14 / 5 | 546 / 7 |
| 2026-S35 | 2026-08-24 a 2026-08-30 | 277 / 7 | 310 / 7 | 15 / 6 | 602 / 7 |
| 2026-S36 | 2026-08-31 a 2026-09-06 | 270 / 7 | 307 / 7 | 16 / 6 | 593 / 7 |
| 2026-S37 | 2026-09-07 a 2026-09-13 | 264 / 7 | 297 / 7 | 15 / 6 | 576 / 7 |
| 2026-S38 | 2026-09-14 a 2026-09-20 | 266 / 7 | 301 / 7 | 9 / 6 | 576 / 7 |
| 2026-S39 | 2026-09-21 a 2026-09-27 | 286 / 7 | 320 / 7 | 10 / 6 | 616 / 7 |
| 2026-S40 | 2026-09-28 a 2026-10-04 | 269 / 7 | 298 / 7 | 11 / 6 | 578 / 7 |

Las rutas 1 y 3 operan los 7 días de cada semana, y la 5, entre 5 y 6 días con 9 a 16 despachos por semana. La semana S40 incluye el día en curso.

## 3. Conteo de pasajeros y alarmas de bloqueo

| Ruta | Despachos | Con registro de registradora | Con conteo de pasajeros | Con conteo > 0 | Con alarma BQ1/BQ2 | Alarmas BQ1/BQ2 (suma) | Con alarma BQ3 |
|---|---|---|---|---|---|---|---|
| 1 | 5.154 | 5.097 | 5.097 (98,9 %) | 5.097 (98,9 %) | 287 (5,6 %) | 629 | 0 (0,0 %) |
| 3 | 5.714 | 5.640 | 5.640 (98,7 %) | 5.640 (98,7 %) | 398 (7,0 %) | 1.193 | 0 (0,0 %) |
| 5 | 232 | 232 | 232 (100,0 %) | 232 (100,0 %) | 8 (3,4 %) | 25 | 0 (0,0 %) |
| Total | 11.100 | 10.969 | 10.969 (98,8 %) | 10.969 (98,8 %) | 693 (6,2 %) | 1.847 | 0 (0,0 %) |

- **Conteo de pasajeros.** Todos los despachos con registro de registradora tienen conteo, y en todos es mayor que 0: no hay nulos ni ceros. El 1,2 % sin conteo son exactamente los 131 despachos sin registro de registradora.
- **Alarmas de bloqueo.** El 6,2 % de los despachos tiene al menos una alarma BQ1/BQ2, con un total de 1.847 alarmas. Ninguno tiene BQ3.
- **Ninguna alarma de bloqueo.** Que un despacho no tenga alarmas BQ1/BQ2 no significa que el conteo esté libre de error; solo que el sensor no reportó un bloqueo.

Evolución mensual:

| Mes | Ruta | Despachos | % con conteo | % con alarma BQ1/BQ2 |
|---|---|---|---|---|
| 2026-06 | 1 | 1.417 | 99,2 | 6,0 |
| 2026-06 | 3 | 1.549 | 98,5 | 7,1 |
| 2026-06 | 5 | 61 | 100,0 | 1,6 |
| 2026-07 | 1 | 1.302 | 98,8 | 5,9 |
| 2026-07 | 3 | 1.431 | 98,9 | 7,3 |
| 2026-07 | 5 | 55 | 100,0 | 5,5 |
| 2026-08 | 1 | 1.126 | 98,8 | 5,0 |
| 2026-08 | 3 | 1.262 | 99,0 | 7,2 |
| 2026-08 | 5 | 58 | 100,0 | 3,4 |
| 2026-09 | 1 | 1.177 | 98,6 | 5,0 |
| 2026-09 | 3 | 1.320 | 98,7 | 6,4 |
| 2026-09 | 5 | 52 | 100,0 | 1,9 |
| 2026-10 | 1 | 132 | 99,2 | 7,6 |
| 2026-10 | 3 | 152 | 96,7 | 5,3 |
| 2026-10 | 5 | 6 | 100,0 | 16,7 |

Octubre solo incluye del 1 al 4.

## 4. Vehículos que operan cada ruta

Vehículos distintos (`FK_VEHICULO`, con su `PLACA` de `tbl_vehiculo`) en los despachos con registro de registradora:

| Ruta | Vehículos distintos | Placas distintas | Exclusivos de la ruta | Mediana por día | Máximo en un día |
|---|---|---|---|---|---|
| 1 | 37 | 37 | 0 | 24 | 35 |
| 3 | 37 | 37 | 0 | 25 | 36 |
| 5 | 7 | 7 | 0 | 2 | 3 |
| Todas | 37 | 37 | — | 25 | 36 |

«Exclusivos de la ruta» son los vehículos que no operaron ninguna otra ruta en el período. La mediana y el máximo cuentan vehículos distintos por día con despachos.

Ningún vehículo opera una sola ruta. Combinaciones de rutas por vehículo:

| Rutas que opera el vehículo | Vehículos |
|---|---|
| 1, 3 | 30 |
| 1, 3, 5 | 7 |

La flota es una sola, de 37 vehículos: los mismos 37 operan las rutas 1 y 3, y 7 de ellos también la ruta 5.

## Consultas ejecutadas

Exploración del esquema y de los catálogos:

```sql
SHOW TABLES LIKE 'tbl_ruta%';
DESCRIBE tbl_ruta;
SHOW TABLES LIKE 'tbl_alarma%';
SHOW TABLES LIKE 'tbl_empresa%';
SELECT PK_EMPRESA, NOMBRE FROM tbl_empresa;
SELECT PK_RUTA, FK_EMPRESA, NOMBRE, TIPO_RUTA, ESTADO FROM tbl_ruta ORDER BY PK_RUTA;
DESCRIBE tbl_alarma;
DESCRIBE tbl_alarma_info_regis;
DESCRIBE tbl_informacion_registradora;
DESCRIBE tbl_intervalo_despacho;
SELECT PK_ALARMA, CODIGO_ALARMA, NOMBRE, TIPO, ESTADO FROM tbl_alarma ORDER BY PK_ALARMA;
```

Conteos de control:

```sql
SELECT COUNT(*) AS filas, COUNT(DISTINCT d.PK_INTERVALO_DESPACHO) AS despachos,
       COUNT(DISTINCT r.PK_INFORMACION_REGISTRADORA) AS registros,
       MIN(d.FECHA_INICIAL) AS min_fecha, MAX(d.FECHA_INICIAL) AS max_fecha,
       SUM(r.FECHA_SALIDA_BASE_SALIDA >= '2026-06-01') AS salida_en_rango
FROM tbl_intervalo_despacho d
INNER JOIN tbl_informacion_registradora r ON d.PK_INTERVALO_DESPACHO = r.FK_INTERVALO_DESPACHO
WHERE d.FECHA_INICIAL >= '2026-06-01' AND d.ESTADO = 1;

SELECT d.ESTADO, COUNT(*) AS n FROM tbl_intervalo_despacho d
WHERE d.FECHA_INICIAL >= '2026-06-01' GROUP BY d.ESTADO;

SELECT COUNT(*) AS intervalos_sin_registradora
FROM tbl_intervalo_despacho d
LEFT JOIN tbl_informacion_registradora r ON d.PK_INTERVALO_DESPACHO = r.FK_INTERVALO_DESPACHO
WHERE d.FECHA_INICIAL >= '2026-06-01' AND d.ESTADO = 1 AND r.PK_INFORMACION_REGISTRADORA IS NULL;
```

Extracción a nivel de despacho (11.144 filas; los cuatro apartados se agregaron a partir de ella):

```sql
SELECT d.PK_INTERVALO_DESPACHO, d.FECHA_INICIAL, d.HORA_INICIAL, d.LISTA_RUTA,
       r.PK_INFORMACION_REGISTRADORA, r.FK_RUTA, r.FK_VEHICULO, v.PLACA,
       r.DIFERENCIA_NUM, r.FECHA_SALIDA_BASE_SALIDA, r.HORA_SALIDA_BASE_SALIDA,
       a.BLOQUEO_BQ1_BQ2, a.REGISTROS_BQ1_BQ2, a.BLOQUEO_BQ3
FROM tbl_intervalo_despacho d
LEFT JOIN tbl_informacion_registradora r ON d.PK_INTERVALO_DESPACHO = r.FK_INTERVALO_DESPACHO
LEFT JOIN tbl_vehiculo v ON r.FK_VEHICULO = v.PK_VEHICULO
LEFT JOIN (
    SELECT FK_INFORMACION_REGISTRADORA,
           SUM(CASE WHEN FK_ALARMA IN (5, 6) THEN CANTIDAD_ALARMA ELSE 0 END) AS BLOQUEO_BQ1_BQ2,
           SUM(CASE WHEN FK_ALARMA IN (5, 6) THEN 1 ELSE 0 END) AS REGISTROS_BQ1_BQ2,
           SUM(CASE WHEN FK_ALARMA = 7 THEN CANTIDAD_ALARMA ELSE 0 END) AS BLOQUEO_BQ3
    FROM tbl_alarma_info_regis
    WHERE FK_ALARMA IN (5, 6, 7) AND FECHA_ALARMA >= '2026-05-25'
    GROUP BY FK_INFORMACION_REGISTRADORA
) a ON r.PK_INFORMACION_REGISTRADORA = a.FK_INFORMACION_REGISTRADORA
WHERE d.FECHA_INICIAL >= '2026-06-01' AND d.ESTADO = 1;

SELECT PK_RUTA, FK_EMPRESA, NOMBRE, ESTADO FROM tbl_ruta;
SELECT NOW() AS ahora_servidor;
```

`tbl_intervalo_despacho.FECHA_INICIAL` no tiene índice, así que las consultas filtradas por esa columna recorren la tabla completa (la extracción tardó unos 8 minutos). Para repetir la consulta conviene hacerlo fuera del horario de operación.
