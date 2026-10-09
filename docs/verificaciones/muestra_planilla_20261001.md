# Planilla de muestra: jornada del jueves 1 de octubre de 2026

Simulación de la recomendación emitida la víspera, con información hasta el cierre de la jornada del 30 de septiembre. La jornada operativa del 1 de octubre empieza a las 04:00, que es el corte.

- **Script:** `scripts/muestra_planilla_20261001.py`.
- **Salidas** en `data/muestra_planilla/`, ignorada por git con un `.gitignore` propio:
  - `planilla_2026-10-01.xlsx`;
  - `comparacion_2026-10-01.xlsx`;
  - `verificaciones_2026-10-01.json`.
- **Sin cambios externos:** no se consultó la base ni se modificó ningún archivo existente.

## Montaje

- **Datos:** solo `data/actualizacion_20261004/`, con el dataset de modelado y el conjunto apto.
- **Hiperparámetros:** XGBoost, los de la búsqueda congelada.
- **Predictor:** C3 del preregistro. En régimen ordinario, XGBoost con el protocolo congelado (26 semanas de entrenamiento y 2 de parada temprana) multiplicado por el factor de 14 días; en régimen raro, la referencia de 52 semanas. El 1 de octubre es `LABORAL`, así que las 57 franjas son de régimen ordinario.
- **Franjas:** se predicen todas las del horario operativo del 1 de octubre: 28 en la ruta 1 y 29 en la ruta 3, con o sin despachos ese día.
- **Módulo:** las reglas de `configs/dispatch/recomendacion.yaml` tal como están, que **incluyen el tope de carga** (`usar_tope_carga: true`): política `divisor_propio` y servicio mínimo 1. Los parámetros calibrados son los de `freeze_20260922_203820`, con capacidad 153; no hizo falta ajuste de factibilidad.

## Verificación de que no se usan datos del 1 de octubre

| Comprobación | Resultado |
|---|---|
| Último instante de los datos de entrenamiento y referencia | 2026-09-30 18:00 |
| Despachos del conjunto apto con salida desde el corte | 268, ignorados |
| Las 15 variables de XGBoost de las 57 franjas, recalculadas solo con el conjunto apto anterior al corte y el calendario | Iguales en las 15. Los rezagos de 48, 96 y 336 franjas apuntan como máximo al 30 de septiembre a las 18:00 |
| Conjunto de franjas del 1 de octubre | Igual al del 30 de septiembre (`LABORAL`), por ruta: viene del horario operativo congelado, no de lo observado el 1 de octubre |
| Objetivos de entrenamiento de las 52 semanas previas (16.761 franjas) | Iguales a los del conjunto apto truncado en el corte |
| Ventana del factor | Jornadas del 17 al 30 de septiembre, cada una predicha solo con datos anteriores a ella |

**Contraste con los scripts 43 y 44** (mismo dataset y protocolo):

| Elemento | Diferencia máxima |
|---|---|
| XGBoost del 1 de octubre, en las 51 franjas con despachos | 4·10⁻⁶ |
| XGBoost de la ventana, 602 franjas | 7·10⁻⁶ |
| Factor de 14 días | 3·10⁻⁸ |

**Límite de la simulación:** el dataset se extrajo el 4 de octubre. Sin consultar la base no se puede comprobar si algún registro del 30 de septiembre se creó después de las 04:00 del 1 de octubre. En abril, los registros tardíos se crearon a las 23:42 del mismo día, antes del corte.

## Factor de corrección (14 días)

| Ruta | Jornadas | Franjas | Σ real | Σ XGBoost | Factor |
|---|---|---|---|---|---|
| 1 | 13 | 302 | 23.608 | 27.136 | 0,870 |
| 3 | 13 | 300 | 28.862 | 31.660 | 0,912 |

En las dos rutas falta el domingo 20 de septiembre: tuvo menos de 8 franjas observadas, así que no se predijo y queda fuera de la ventana, como en el preregistro.

## Totales por ruta

| Ruta | Pasajeros predichos | Pasajeros reales | Despachos recomendados | Despachos reales |
|---|---|---|---|---|
| 1 | 2.150 | 2.119 | 54 | 45 |
| 3 | 2.669 | 2.599 | 61 | 52 |

- **Pasajeros:** la predicción total queda un 1,4 % y un 2,7 % por encima de la real.
- **Despachos:** la recomendación propone 18 más que la práctica real (115 frente a 97). Se explican así:
  - **Franjas sin servicio ese día:** 6 despachos van a las franjas de 17:00, 17:30 y 18:00 de las dos rutas. Están en el horario operativo, pero el 1 de octubre no tuvieron despachos. El 1 que se recomienda en cada una no lo impone el servicio mínimo, sino el redondeo: la demanda predicha es de 27 a 39 pasajeros, más de la mitad del divisor (45 en la ruta 1 y 46 en la ruta 3), y por eso se redondea a 1. *(Corregido el 2026-10-07; la primera versión lo atribuía al servicio mínimo).*
  - **Tope de carga:** 4 despachos, en la ruta 1 (08:30, 10:00, 12:00 y 16:30), donde dividir por Q3 da un despacho más que dividir por la mediana.
  - **Redondeo:** el resto sale de redondear franja a franja.

**Clase de las franjas con despachos reales:**

| Ruta | Práctica real (baja / normal / alta) | Con la recomendación (baja / normal / alta) |
|---|---|---|
| 1 (25 franjas) | 3 / 15 / 7 | 10 / 10 / 5 |
| 3 (26 franjas) | 3 / 21 / 2 | 8 / 14 / 4 |

La clase con la recomendación divide los pasajeros reales entre los despachos recomendados.

## Franjas con mayor diferencia

**Despachos (recomendados − reales):**

| Ruta | Franja | Recomendados | Reales | Diferencia |
|---|---|---|---|---|
| 1 | 08:30 | 3 | 1 | +2 |
| 3 | 12:00 | 3 | 1 | +2 |
| 1 | 04:30 | 2 | 3 | −1 |
| 1 | 08:00 | 2 | 3 | −1 |

Las demás diferencias son de ±1, incluidas las 6 franjas de 17:00–18:00 sin despachos reales.

**Pasajeros (predichos − reales):**

| Ruta | Franja | Predichos | Reales | Diferencia |
|---|---|---|---|---|
| 1 | 08:00 | 81,5 | 161 | −79,5 |
| 3 | 15:00 | 86,1 | 156 | −69,9 |
| 3 | 07:30 | 113,2 | 58 | +55,2 |
| 3 | 05:30 | 136,0 | 190 | −54,0 |
| 3 | 12:00 | 121,5 | 68 | +53,5 |
| 3 | 07:00 | 107,4 | 158 | −50,6 |

En el total del día se compensan, pero franja a franja hay desvíos grandes en los dos sentidos. La mayor parte coincide con franjas en las que la práctica real concentró o espació los despachos: por ejemplo, la ruta 1 a las 08:00 tuvo 3 despachos con 161 pasajeros, y a las 08:30, 1 despacho.
