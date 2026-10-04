# Agregación de barrido de ventana de entrenamiento (XGBoost) por tipo de día

**Archivo fuente:** `analisis/salidas/barrido_ventana_diario.csv` (685 filas, una por jornada × ventana de entrenamiento; método = XGBoost, script `analisis/13_barrido_ventana_diario.py`).
**Operación aplicada:** promedio ponderado por `n` (número de observaciones de la jornada), agrupando por `route`, `semanas_entrenamiento` (renombrada aquí `ventana`, donde el código `999` = registro completo / todo el histórico) y `tipo_dia`. No se reentrenó ni se ejecutó nada: es agregación aritmética pura sobre valores ya persistidos.

**Advertencia de alcance (soporte de jornadas distinto al de las tablas del freeze de seis métodos):** este archivo cubre **68 jornadas en ruta 1 y 69 en ruta 3 (137 en total)** — el conjunto propio de XGBoost, sin restringir a la intersección con LSTM/GRU/CNN-LSTM. Las tablas del freeze de seis métodos (`tablas_capitulo_modelos.md`, Tablas 3–4) usan en cambio las **134 jornadas comunes** (66 ruta 1 + 68 ruta 3). La diferencia está en LABORAL: 44 jornadas aquí vs. 42 (ruta 1) / 43 (ruta 3) en las tablas de seis métodos. Por eso los valores de esta agregación **no son directamente comparables celda a celda** con las Tablas 3 y 4 de `tablas_capitulo_modelos.md`, aunque el criterio de agregación (promedio ponderado por `n`) es el mismo.

---

## Número de jornadas y observaciones por celda (constante entre ventanas)

El conjunto de jornadas y su `n` de observaciones no cambia con la ventana de entrenamiento (la ventana solo afecta cuántas semanas de historia usa el modelo, no qué jornadas se evalúan). Por eso esta tabla aplica igual a las cinco ventanas.

| Ruta | LABORAL | SABADO | DOMINGO | FESTIVO | FESTIVO_PUENTE |
|---|---|---|---|---|---|
| 1 — jornadas | 44 | 10 | 9 | 3 | 2 |
| 1 — observaciones | 1137 | 241 | 97 | 40 | 21 |
| 3 — jornadas | 44 | 10 | 10 | 3 | 2 |
| 3 — observaciones | 1157 | 244 | 110 | 48 | 22 |

---

## Tabla A — Sesgo medio (ponderado por n), ruta 1

| Ventana | LABORAL | SABADO | DOMINGO | FESTIVO | FESTIVO_PUENTE |
|---|---|---|---|---|---|
| 8 | -0,93 | 1,01 | 1,93 | 51,56 | 8,06 |
| 13 | 1,08 | 1,02 | 1,62 | 6,60 | 2,95 |
| 26 | 2,74 | 3,94 | 2,80 | 1,48 | 10,83 |
| 52 | 9,65 | 8,37 | 2,08 | 2,86 | 8,65 |
| completo | 16,95 | 13,12 | 2,41 | 2,20 | 3,05 |

## Tabla A — Sesgo medio (ponderado por n), ruta 3

| Ventana | LABORAL | SABADO | DOMINGO | FESTIVO | FESTIVO_PUENTE |
|---|---|---|---|---|---|
| 8 | -1,97 | 4,46 | 3,23 | 68,21 | 8,92 |
| 13 | 0,14 | 1,76 | 0,93 | 17,94 | 6,11 |
| 26 | 1,97 | 4,61 | 2,02 | 4,26 | 4,84 |
| 52 | 9,66 | 6,27 | 1,73 | 4,08 | 2,98 |
| completo | 17,35 | 12,43 | 2,71 | 5,24 | 2,76 |

---

## Tabla B — MAE medio (ponderado por n), ruta 1

| Ventana | LABORAL | SABADO | DOMINGO | FESTIVO | FESTIVO_PUENTE |
|---|---|---|---|---|---|
| 8 | 30,26 | 26,26 | 11,00 | 58,62 | 13,88 |
| 13 | 29,59 | 24,14 | 10,90 | 15,89 | 11,74 |
| 26 | 29,81 | 24,31 | 11,43 | 12,41 | 14,37 |
| 52 | 30,51 | 24,52 | 10,53 | 12,69 | 13,74 |
| completo | 33,21 | 26,29 | 10,90 | 13,35 | 11,27 |

## Tabla B — MAE medio (ponderado por n), ruta 3

| Ventana | LABORAL | SABADO | DOMINGO | FESTIVO | FESTIVO_PUENTE |
|---|---|---|---|---|---|
| 8 | 34,67 | 27,97 | 11,73 | 70,11 | 12,40 |
| 13 | 34,10 | 26,32 | 10,15 | 22,12 | 10,08 |
| 26 | 33,76 | 26,62 | 10,62 | 13,05 | 10,11 |
| 52 | 34,26 | 25,82 | 9,66 | 13,67 | 8,86 |
| completo | 37,32 | 26,73 | 10,25 | 13,84 | 8,98 |

---

## Desviación típica del sesgo entre jornadas, días ordinarios (LABORAL + SABADO + DOMINGO, `regimen = ordinario`)

**Operación:** desviación típica (muestral, `ddof=1`) del sesgo por jornada individual (no ponderada), agrupando por ruta y ventana, sobre las jornadas con `regimen = ordinario` en `barrido_ventana_diario.csv`.

| Ruta | Jornadas ordinarias (n) | Ventana 8 | Ventana 13 | Ventana 26 | Ventana 52 | Completo |
|---|---|---|---|---|---|---|
| 1 | 63 | 9,89 | 8,67 | 7,87 | 7,72 | 8,91 |
| 3 | 64 | 9,99 | 9,40 | 9,03 | 8,55 | 9,50 |

Lectura: la dispersión del sesgo entre jornadas ordinarias es mínima con ventana de 52 semanas en ambas rutas (7,72 y 8,55 respectivamente) y aumenta tanto con ventanas cortas (8 semanas) como con el registro completo, coherente con que el sesgo medio también crece de forma sostenida con la ventana completa (Tabla A).
