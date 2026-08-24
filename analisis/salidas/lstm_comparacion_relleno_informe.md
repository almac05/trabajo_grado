# Comparacion del tratamiento del relleno en la LSTM

## Protocolo

Se evaluaron 134 jornadas (66 de la ruta 1 y 68 de la ruta 3) con
reentrenamiento diario. En cada jornada se conservaron las mismas particiones
temporales, semilla, arquitectura base e hiperparametros. Se compararon:

1. **Original:** demanda como unico canal y MAE sobre las 28 posiciones,
   incluidas las rellenadas.
2. **Enmascarada:** demanda mas indicador de posicion observada y MAE calculado
   solo sobre observaciones reales.

El MAE de prueba siempre se calculo sobre observaciones reales. Los resultados
detallados estan en `lstm_comparacion_relleno.csv`.

## Resultados

| Ruta | Jornadas | MAE original | MAE enmascarada | Cambio | Gana enmascarada |
|---|---:|---:|---:|---:|---:|
| 1 | 66 | 27.376 | 29.016 | +5.99 % | 26 (39.4 %) |
| 3 | 68 | 32.041 | 33.118 | +3.36 % | 31 (45.6 %) |
| Global | 134 | 29.764 | 31.116 | +4.54 % | 57 (42.5 %) |

El signo positivo del cambio representa empeoramiento. En promedio, el relleno
constituyo 12.53 % de los objetivos de ajuste y 18.13 % de los objetivos de
parada temprana. En el modelo original produjo 8.24 % de la perdida de parada
temprana. La diferencia pareada global fue desfavorable a la variante
enmascarada (Wilcoxon bilateral, p = 0.0114).

Al excluir las 11 jornadas con una diferencia absoluta superior a 10, la
variante enmascarada conservo una desventaja media de 0.42 pasajeros de MAE por
jornada. Por tanto, el resultado agregado no se explica solamente por valores
atipicos.

La media historica obtuvo un MAE ponderado global de 29.578 sobre estas mismas
jornadas. El modelo original fue 0.63 % peor y el enmascarado 5.20 % peor que
esa referencia.

## Hallazgo estructural

El relleno final no es el unico problema. Las jornadas se copian por orden de
aparicion a las primeras posiciones del arreglo, aunque comienzan a horas
distintas y contienen huecos internos. En el periodo de prueba se observaron
saltos de 60 a 240 minutos. Por ejemplo, la primera posicion suele representar
04:00 o 04:30 en dias laborales, pero 07:00 en domingos. En consecuencia, una
misma posicion de la salida no representa necesariamente la misma franja
horaria entre jornadas.

## Decision

No se recomienda aceptar todavia los resultados de esta LSTM como evidencia de
mejora predictiva. Incluir el relleno en la perdida es conceptualmente
incorrecto, pero enmascararlo dentro de la representacion actual deja
posiciones con poca supervision y genera predicciones inestables, especialmente
en festivos, festivos puente y jornadas cortas.

El siguiente experimento debe construir una grilla fija por hora, conservar los
huecos en su posicion temporal real y proporcionar al modelo la hora de cada
paso. Despues debe repetirse la comparacion contra la media historica.
