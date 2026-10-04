# Regeneración de cuadro_perfil_horario_laboral.csv

Se ejecutó `python analisis/14_cuadros_mecanismos.py` (sin modificar su código) sobre el parquet vigente `data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet` (mtime 2026-08-23). Antes de ejecutar se respaldaron los cinco cuadros que el script puede escribir, para poder medir el efecto exacto de la regeneración.

---

## Máximos del perfil intradía en día laboral (valores regenerados)

| Ruta | Hora del máximo | Valor (media) | n (observaciones en esa franja) |
|---|---|---|---|
| Ruta 1 | **15:30** | **192.1** | 523 |
| Ruta 3 | **06:00** | **306.8** | 525 |

(Confirmado también por el resumen que imprime el propio script — "CUADRO 1b": `media_max` = 192.1 para ruta 1 y 306.8 para ruta 3.)

Nota: en la Ruta 1 la franja de 15:00 (191.1) es muy cercana al máximo pero **no** es el máximo — la franja 15:30 la supera por 1.0. Si el documento reporta "191.6 a las 15:00" como máximo, no coincide ni en franja ni en valor con esta regeneración.

## Perfil horario completo por franja (día laboral, `tipo_dia == "LABORAL"`)

### Ruta 1

| Hora | Media | Desv. std | n |
|---|---|---|---|
| 04:30 | 154.8 | 50.0 | 524 |
| 05:00 | 145.9 | 46.9 | 524 |
| 05:30 | 167.3 | 51.7 | 525 |
| 06:00 | 165.7 | 51.4 | 525 |
| 06:30 | 141.2 | 41.9 | 523 |
| 07:00 | 138.0 | 38.7 | 523 |
| 07:30 | 152.4 | 42.9 | 525 |
| 08:00 | 146.8 | 43.3 | 525 |
| 08:30 | 148.4 | 43.2 | 523 |
| 09:00 | 145.0 | 38.5 | 524 |
| 09:30 | 131.8 | 37.4 | 526 |
| 10:00 | 117.1 | 36.3 | 526 |
| 10:30 | 109.9 | 35.4 | 524 |
| 11:00 | 103.7 | 33.3 | 524 |
| 11:30 | 112.4 | 35.2 | 526 |
| 12:00 | 124.7 | 40.4 | 524 |
| 12:30 | 150.1 | 44.2 | 525 |
| 13:00 | 151.7 | 45.2 | 526 |
| 13:30 | 156.8 | 46.2 | 525 |
| 14:00 | 164.1 | 49.4 | 523 |
| 14:30 | 167.6 | 52.1 | 525 |
| **15:00** | **191.1** | 59.4 | 525 |
| **15:30** | **192.1** | 55.0 | 523 |
| 16:00 | 169.5 | 55.1 | 523 |
| 16:30 | 134.4 | 45.8 | 523 |
| 17:00 | 83.6 | 32.8 | 501 |
| 17:30 | 45.1 | 20.7 | 367 |
| 18:00 | 25.6 | 13.2 | 109 |

### Ruta 3

| Hora | Media | Desv. std | n |
|---|---|---|---|
| 04:00 | 51.3 | 14.2 | 448 |
| 04:30 | 151.8 | 45.3 | 523 |
| 05:00 | 246.3 | 68.0 | 524 |
| 05:30 | 291.6 | 71.4 | 524 |
| **06:00** | **306.8** | 69.4 | 525 |
| 06:30 | 249.4 | 67.9 | 526 |
| 07:00 | 185.1 | 50.3 | 526 |
| 07:30 | 173.3 | 48.6 | 524 |
| 08:00 | 169.3 | 51.2 | 522 |
| 08:30 | 167.9 | 50.8 | 525 |
| 09:00 | 156.8 | 45.9 | 524 |
| 09:30 | 136.2 | 40.3 | 523 |
| 10:00 | 139.0 | 37.1 | 524 |
| 10:30 | 129.6 | 40.4 | 523 |
| 11:00 | 122.1 | 36.4 | 525 |
| 11:30 | 135.0 | 38.6 | 524 |
| 12:00 | 171.5 | 44.5 | 524 |
| 12:30 | 156.6 | 46.8 | 524 |
| 13:00 | 158.0 | 45.8 | 524 |
| 13:30 | 152.4 | 47.2 | 522 |
| 14:00 | 143.9 | 46.1 | 521 |
| 14:30 | 165.9 | 52.8 | 522 |
| 15:00 | 176.3 | 62.4 | 523 |
| 15:30 | 166.0 | 58.2 | 519 |
| 16:00 | 135.7 | 49.8 | 518 |
| 16:30 | 100.4 | 39.3 | 514 |
| 17:00 | 63.3 | 28.4 | 461 |
| 17:30 | 35.3 | 18.5 | 265 |
| 18:00 | 21.1 | 10.7 | 57 |

---

## Efecto sobre otros cuadros generados por el mismo script

`analisis/14_cuadros_mecanismos.py` escribe potencialmente cinco archivos. Se compararon los cinco contra su versión previa (respaldada antes de ejecutar):

| Archivo | ¿Cambió? | Magnitud |
|---|---|---|
| `cuadro_perfil_horario_laboral.csv` | **Sí** (el pedido) | Ver tablas arriba — descensos de entre 0.2 y 2.6 puntos en la media por franja, `n` sin cambios |
| `cuadro_variabilidad_intradiaria.csv` | **Sí** | Ruta 1: demanda_media 116.1→115.4 (−0.7), desv_intradiaria_mediana 44.6→44.2 (−0.4). Ruta 3: demanda_media 131.0→130.1 (−0.9), desv_intradiaria_mediana 69.3→68.3 (−1.0). `jornadas` sin cambio (785 en ambas rutas) |
| `cuadro_amplitud_metodos.csv` | **Sí, con pérdida de datos — revertido** | Este cuadro depende de `sarima_multiples_dias.csv`, `prophet_multiples_dias.csv` y `xgboost_multiples_dias.csv` en `analisis/salidas/`. Ninguno de los tres existe actualmente en el repositorio, así que el script no pudo recalcular nada y sobrescribió el archivo (que antes tenía 6 filas con comparaciones SARIMA/Prophet/XGBoost por ruta) con una tabla **vacía**. Dado que esos tres CSV de origen no existen en ningún otro lugar del repositorio y por tanto esa información no es reproducible en este momento, **se restauró el archivo a su contenido previo** inmediatamente después de detectar la pérdida (ver contenido restaurado abajo). Esto es la única reversión aplicada. |
| `cuadro_sarima_por_dia_semana.csv` | No | El script solo lo regenera si existe `sarima_multiples_dias.csv`; al no existir, se omitió por completo y el archivo previo (mtime 2026-08-17) quedó intacto |
| `cuadro_jornadas_festivas.csv` | No | Ídem, condicionado a `xgboost_multiples_dias.csv`, que tampoco existe; archivo previo intacto |

### Contenido restaurado de `cuadro_amplitud_metodos.csv` (idéntico al existente antes de la ejecución)
```
metodo,route,amplitud_predicha,amplitud_observada,proporcion
SARIMA,1,26.811,136.118,0.197
SARIMA,3,83.956,220.232,0.381
Prophet,1,72.609,136.118,0.533
Prophet,3,171.755,220.232,0.78
XGBoost,1,69.172,136.118,0.508
XGBoost,3,170.714,220.232,0.775
```

**Nota metodológica**: el script tiene una asimetría — para los cuadros 3 y 4 comprueba `if ruta_sarima.exists()` / `if ruta_xgb.exists()` antes de escribir, pero para el cuadro 2 (`cuadro_amplitud_metodos.csv`) no aplica esa misma guarda: itera sobre los tres métodos, omite los que faltan (solo imprime un aviso), y **igual escribe el resultado**, aunque quede vacío. Si se vuelve a ejecutar este script sin antes regenerar `sarima_multiples_dias.csv`, `prophet_multiples_dias.csv` y `xgboost_multiples_dias.csv`, `cuadro_amplitud_metodos.csv` volverá a vaciarse.

---

## Conclusión sobre el máximo del perfil intradía

Con el dataset vigente (regenerado el 23-ago-2026), los máximos correctos son **192.1 en Ruta 1 (15:30)** y **306.8 en Ruta 3 (06:00)** — ambos distintos de los citados en el documento (191.6 a las 15:00 en Ruta 1; 278.1 a las 06:00 en Ruta 3) y también distintos de los que traía el `cuadro_perfil_horario_laboral.csv` desactualizado (193.9/15:30 y 309.4/06:00) reportado en la verificación anterior. La Ruta 3 muestra la mayor brecha frente al documento: 306.8 vs. 278.1 (+10.3%).
