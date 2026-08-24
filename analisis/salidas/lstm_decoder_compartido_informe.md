# LSTM con decodificador horario compartido

## Cambios evaluados

El encoder procesa la jornada anterior sobre la grilla fija de 29 franjas. El
decoder aplica la misma red neuronal a cada hora objetivo usando:

- el contexto producido por la LSTM;
- la hora objetivo en representacion seno/coseno;
- variables de calendario;
- indicadores separados para laboral, sabado, domingo, festivo y festivo
  puente.

La perdida calcula primero el MAE de cada jornada y luego promedia las jornadas,
por lo que un dia corto recibe el mismo peso que uno largo. La variante hibrida
reemplaza la prediccion neuronal por la media historica hora-tipo en `FESTIVO` y
`FESTIVO_PUENTE`.

## Resultados ponderados

| Ruta | MAE densa | MAE decoder | MAE hibrido | MAE media | Hibrido vs. densa |
|---|---:|---:|---:|---:|---:|
| 1 | 29.578 | 28.009 | 27.699 | 27.943 | -6.35 % |
| 3 | 31.658 | 35.110 | 35.122 | 31.138 | +10.94 % |
| Global | 30.643 | 31.644 | 31.498 | 29.578 | +2.79 % |

En la ruta 1 el hibrido mejora significativamente frente a la salida densa
(Wilcoxon bilateral, p = 0.0113), aunque no frente a la media historica
(p = 0.4274). En la ruta 3 el hibrido empeora significativamente frente a la
salida densa (p < 0.0001). Globalmente no mejora a la salida densa (p = 0.1203)
y es peor que la media historica (p = 0.0009).

## Resultado por tipo de dia

| Tipo | MAE densa | MAE decoder | MAE hibrido | MAE media |
|---|---:|---:|---:|---:|
| Laboral | 32.471 | 35.532 | 35.532 | 32.985 |
| Sabado | 27.747 | 26.738 | 26.738 | 26.497 |
| Domingo | 15.040 | 11.482 | 11.482 | 11.115 |
| Festivo | 30.134 | 12.444 | 13.588 | 13.588 |
| Festivo puente | 45.269 | 23.054 | 10.440 | 10.440 |

El decoder compartido transfiere informacion de manera efectiva hacia jornadas
cortas y horas con poca supervision. El fallback elimina los errores extremos
de los festivos puente. Sin embargo, la comparticion total reduce demasiado la
capacidad de representar el perfil laboral de la ruta 3: en esa ruta, el MAE
laboral pasa de 34.29 con la salida densa a 40.39 con el decoder.

## Decision

El fallback para `FESTIVO` y `FESTIVO_PUENTE` queda justificado y debe
conservarse. El decoder totalmente compartido no debe sustituir todavia la
salida densa para todas las rutas y tipos de dia.

El siguiente diseño debe mantener la red compartida, pero incorporar un
embedding o residual entrenable por franja horaria. Esto permite transferir
informacion entre horas sin obligarlas a compartir exactamente la misma curva.
La seleccion entre arquitecturas debe hacerse en validacion dentro de cada
ventana, no a partir de los resultados finales de prueba.
