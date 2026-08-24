# Evaluacion de la LSTM con grilla horaria fija

## Correccion implementada

Las secuencias se reconstruyeron sobre 29 franjas de 30 minutos entre 04:00 y
18:00. Cada observacion conserva su hora real y los huecos internos permanecen
en su posicion temporal. La entrada recurrente tiene cuatro canales:

1. demanda estandarizada;
2. indicador de posicion observada;
3. seno de la hora;
4. coseno de la hora.

Los huecos toman el valor neutro cero despues de la estandarizacion y se
excluyen de la perdida mediante la mascara. Se comparo esta variante con la
LSTM ordinal enmascarada usando las mismas particiones temporales,
hiperparametros y semilla.

## Resultados ponderados

| Ruta | Jornadas | Observaciones | MAE ordinal | MAE grilla | MAE media | Grilla vs. ordinal | Grilla vs. media |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 66 | 1.483 | 29.016 | 29.578 | 27.943 | +1.94 % | +5.85 % |
| 3 | 68 | 1.555 | 32.771 | 31.658 | 31.138 | -3.39 % | +1.67 % |
| Global | 134 | 3.038 | 30.938 | 30.643 | 29.578 | -0.95 % | +3.60 % |

La grilla obtuvo menor MAE en 63 de 134 jornadas. La diferencia pareada frente
a la variante ordinal no fue significativa (Wilcoxon bilateral, p = 0.7805).
Al excluir las 16 jornadas cuya diferencia absoluta supera 10 pasajeros, la
grilla queda 0.04 pasajeros de MAE por jornada por detras de la ordinal. La
mejora agregada, por tanto, esta impulsada por pocos cambios extremos.

## Resultado por tipo de dia

| Tipo | Jornadas | MAE ordinal | MAE grilla | MAE media |
|---|---:|---:|---:|---:|
| Laboral | 85 | 33.444 | 32.471 | 32.985 |
| Sabado | 20 | 26.547 | 27.747 | 26.497 |
| Domingo | 19 | 11.711 | 15.040 | 11.115 |
| Festivo | 6 | 31.687 | 30.134 | 13.588 |
| Festivo puente | 4 | 42.378 | 45.269 | 10.440 |

La representacion alineada mejora los dias laborales y reduce algunos errores
extremos causados por la desalineacion. Sin embargo, es inestable en jornadas
raras y cortas. Esas categorias tienen pocos ejemplos y muchas posiciones sin
objetivo, mientras la capa final aprende una salida independiente para cada
franja.

## Conclusion

La grilla horaria es una correccion metodologica necesaria y debe conservarse,
pero no demuestra una mejora predictiva estable con la arquitectura actual. La
LSTM de grilla permanece 3.60 % por encima de la media historica en MAE global.

Antes de aceptar la LSTM se recomienda cambiar la salida densa de 29 valores
independientes por un decodificador que comparta parametros entre horas y
condicionar explicitamente por tipo de dia. Tambien conviene usar una estrategia
especifica para festivos y festivos puente, donde la media historica es mucho
mas robusta que ambas LSTM.
