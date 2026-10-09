# Diseño del proceso nocturno de la prueba piloto

**Estado:** borrador para revisión, 2026-10-07. No hay código escrito. Ningún dato, freeze ni artefacto existente se modifica: todo lo nuevo vive en `data/piloto/`, `configs/piloto/` y un paquete nuevo `src/proyecto_grado/piloto/`.

**Objetivo:** cada noche, generar la recomendación de despachos de la jornada siguiente (D+1) para las rutas 1 y 3. Se usa el candidato C3 del preregistro (XGBoost en régimen ordinario con corrección multiplicativa de 14 días; referencia de 52 semanas en régimen raro) y el módulo de recomendación con los parámetros calibrados, sin tope.

> **Nota:** C3 fue el elegido en validación, pero no superó la confirmación preregistrada: su MAE en evaluación quedó 0,0025 por encima del candidato 1. La configuración de la piloto debe dejar constancia de que se usa por decisión explícita.

## 0. Hallazgo que condiciona el diseño: la hora de ejecución

El protocolo congelado supone que, al predecir la jornada *d*, la jornada *d* − 1 está **completa**. A las 21:00 del día D, la jornada D aún no lo está:

1. **Rezagos de XGBoost.** Las 15 variables de XGBoost incluyen `pasajeros_total_lag_48`, `_lag_96` y `_lag_336`, y sus equivalentes de pasajeros por despacho: la misma franja de hace 1, 2 y 7 días. Para predecir D+1, `lag_48` es la jornada D.
2. **Ventanas.** El entrenamiento (26 semanas), la parada temprana (2 semanas), la referencia de 52 semanas y la ventana de corrección [*d* − 14, *d* − 1] incluyen la jornada D.
3. **Datos de D a las 21:00.**
   - **Operación:** en la extensión, el último viaje del día termina a las 19:54 en la mediana, a las 20:23 en el percentil 90 y a las 21:55 como máximo. Operativamente, a las 21:00 casi todo terminó.
   - **Registros:** el **15 % de los despachos de cada día** (unos 14 por día, el 16 % de los pasajeros) no tiene hora de llegada registrada.
     - **La hora de llegada no es el problema.** El bloque 7 del ETL (`etl/trip_end.py`) la estima con el rastreo GPS. En la extensión, los 1.438 despachos sin llegada registrada son exactamente los 1.438 con `HORA_FIN_FUENTE = GPS_ESTIMADA`.
     - **El riesgo es el registro de registradora.** Ese registro contiene el conteo de pasajeros, y la extracción solo trae despachos que ya lo tienen. De los 37 despachos perdidos en abril, 34 no tenían llegada registrada; los del 22 y el 23 de abril tuvieron su registro creado a las **23:42**, en el cierre automático de la jornada. Mientras el registro no existe, el despacho no se extrae, y el bloque 7 no puede actuar sobre él.
     - **Aún no se sabe si es la regla.** El 22 de abril, 17 de los 28 despachos sin llegada sí estaban en la extracción anterior, así que su registro existía antes del cierre. Si el cierre automático fuera la regla para estos despachos, a las 21:00 faltaría hasta el 16 % de los pasajeros de D. Eso afectaría a `lag_48`, al entrenamiento, a la referencia y al factor.

**Opciones:**

| Opción | Datos de D | ¿Protocolo congelado? | Planilla disponible |
|---|---|---|---|
| A. Solo a las 21:00 | Incompletos (~16 % si se confirma el cierre a las 23:42) | No: rezagos y ventanas sesgados a la baja, y la ventana de corrección tiene que excluir D | 21:15 |
| **B. Solo a las 00:30** | Completos | **Sí**, exactamente | ~00:45, antes del inicio del servicio (04:00) |
| C. 21:00 preliminar + 00:30 definitiva | Preliminar incompleta y marcada; definitiva completa | La definitiva sí | Preliminar 21:15; definitiva ~00:45 |

**Recomendación:**
- **B**, si el despachador puede recibir la planilla al iniciar su turno.
- **C**, si necesita verla la noche anterior. La preliminar irá marcada como tal en el nombre y en la cabecera.
- La evaluación de la piloto usará siempre la definitiva.

**Verificación previa (requiere tu autorización).** Una consulta de solo lectura, fuera del horario de operación, sobre los últimos 30 días de `tbl_informacion_registradora`: qué fracción de los registros de cada día se crea después de las 21:00 y después de las 23:42. Decide entre A, B y C con evidencia en vez de con el caso de abril.

## 1. Extracción

### 1.1 Diagnóstico de los 37 despachos de abril

`etl/extract.py` es incremental por marca de agua: solo trae despachos con `PK_INTERVALO_DESPACHO` mayor que el máximo ya extraído (`max_pk`). Además, la consulta hace un `INNER JOIN` con `tbl_informacion_registradora`, así que **un despacho solo aparece cuando ya tiene registro de registradora**.

**Cómo se pierden:**
1. El ETL se ejecuta durante la operación.
2. El despacho 355970 ya tiene registro y entra; `max_pk` pasa a ser 355970.
3. Los despachos 355968 y 355969 tienen PK menor, pero sus registros se crean después (09:53–09:54; en el caso del 22 y el 23 de abril, a las 23:42 en el cierre automático).
4. En la siguiente ejecución, como su PK es menor que `max_pk`, quedan excluidos **para siempre**.

**Defectos latentes del mismo mecanismo:**
- **Cambios posteriores:** nunca se recogen los cambios de despachos ya extraídos, porque su PK ya es ≤ `max_pk`. Por ejemplo: hora real de llegada que llega tarde, cambios de `ESTADO_DESPACHO`, alarmas añadidas después.
- **Anulaciones:** si un intervalo pasa a `ESTADO` ≠ 1, sigue en el CSV.
- **Duplicados:** en los 44 despachos con dos registros de registradora, el que se queda depende del orden en que la base devuelve las filas (`drop_duplicates(keep="last")`), que no está garantizado.

En abril, los registros perdidos no se habían modificado después (`FECHA_MODIFICACION` = creación). El problema fue solo de ventana temporal, no de datos alterados.

### 1.2 Corrección: reextraer una ventana y reemplazarla por clave

En cada ejecución:
1. **Ventana:** las jornadas con `FECHA_INICIAL` en [D − 6, D], 7 días. Los domingos, la ventana se amplía a 35 días, como conciliación profunda.
2. **Consulta:** la misma de `extract.py`, en solo lectura. Para no recorrer la tabla completa (`FECHA_INICIAL` no tiene índice), se acota también por PK:
   - `PK_INTERVALO_DESPACHO >= pk_ancla`, donde `pk_ancla` es el menor PK local con `FECHA_INICIAL >= D − 6`, menos un margen de 5.000;
   - además, el filtro por fecha.
3. **Reemplazo por ventana:** en el almacén local se eliminan todos los despachos con `FECHA_INICIAL` dentro de la ventana y se insertan los recién extraídos. Así se recogen altas, cambios y anulaciones.
4. **Duplicados deterministas:** se ordena por `PK_INFORMACION_REGISTRADORA` antes de deduplicar. Hay que comprobar que reproduce lo que eligió la extracción del 4 de octubre en esos 44 casos; si no, se documenta la diferencia.
5. **Instantánea inmutable:** cada extracción se guarda tal cual en `data/piloto/extracciones/<id_ejecucion>.parquet`.
6. **Diferencias:** se registran por día y por campo (nuevos, cambiados y retirados). Si aparecen cambios en el **día más antiguo** de la ventana, se emite una advertencia: la ventana de 7 días se queda corta.

**Semilla:** el histórico hasta 2026-10-03 se lee, sin copiarlo ni modificarlo, de `data/actualizacion_20261004/`, que se extrajo completo después del cierre de ese día. La piloto guarda sus propios despachos desde el 2026-09-27; la superposición con la semilla sirve de control (sección 8).

## 2. Actualización de la serie de 30 minutos

- **Procesamiento por ventana:** a los despachos de la ventana se les aplican los bloques 4 a 8 del ETL, con las mismas funciones y `configs/etl.yaml` congelado:
  - transformaciones;
  - hora de salida por GPS;
  - control de calidad;
  - fin de viaje por GPS;
  - conjunto apto.

  Con unos 600 despachos, de los que unos 90 necesitan GPS en los bloques 5 y 7, debería tardar 2–3 minutos. El ETL completo tarda 3 h 37 min, casi todo en el bloque 7.
- **Conjunto apto de la piloto:** el de la semilla anterior a la ventana, unido al procesado de la ventana.
- **Serie:** se reconstruye completa con `TimeSeriesBuilder` y el horario operativo congelado (`data/processed/operational_hours.parquet`), y se versiona por ejecución. Reconstruir completo cuesta poco y evita inconsistencias de una actualización parcial.
- **Supuesto que hay que verificar:** que los bloques 4–8 sean fila a fila. Es decir, que procesar una ventana dé el mismo resultado que procesar todo. Los umbrales de percentil del control de calidad son globales, pero solo producen banderas blandas, que no excluyen. Lo comprueba el control 8.2. Si falla, la alternativa es ejecutar el ETL completo en `data/piloto/etl/` conservando el punto de control del bloque 7.

## 3. Predicción de la jornada siguiente

- **Tipo de día de D+1:** se toma del calendario de festivos de Colombia, con la misma regla de `TimeSeriesBuilder`, incluido `FESTIVO_PUENTE`. El régimen es raro si el tipo de día es `FESTIVO` o `FESTIVO_PUENTE`.
- **Franjas a predecir:** las del horario operativo congelado para la ruta y el tipo de día de D+1.

  > **Diferencia con el backtesting.** El backtesting solo predecía las franjas observadas (con despachos). Para un día futuro no hay franjas observadas, así que se predicen todas las del horario operativo. Esta diferencia es inevitable y debe declararse.
- **Variables de D+1:** se generan con el mismo código del constructor, añadiendo a la serie las franjas de D+1 sin demanda. **Control:** las variables generadas así para un día pasado deben coincidir con las del dataset (8.3).
- **XGBoost:** con las mismas funciones del freeze (`seleccionar_features`, `ajustar_predecir_xgboost`) y los mismos parámetros:
  - hiperparámetros de `analisis/salidas/busqueda_hiperparametros`;
  - entrenamiento con las 26 semanas anteriores a las 04:00 de D+1;
  - parada temprana con las 2 últimas;
  - `random_state = 42`.
- **Referencia de 52 semanas:** la fórmula del script 43.
- **Qué se calcula según el régimen:**
  - En régimen ordinario se calculan las dos predicciones.
  - En régimen raro, la final es la referencia, pero XGBoost también se calcula y se guarda en el historial.

## 4. Factor de corrección e historial de predicciones

- **Historial de predicciones emitidas** (`data/piloto/historial/predicciones_emitidas.parquet`): solo se añaden filas, nunca se reescriben.
  - **Por franja emitida:** ejecución, ruta, jornada, hora, tipo de día, régimen, `pred_xgboost` sin corregir, `ref52`, factor aplicado, predicción final, origen (`piloto`, `relleno` o `backtest`) y versión (preliminar o definitiva).
- **Factor para D+1, ruta *r*** (la regla del preregistro, k = 14):
  - **Franjas:** las ordinarias de la ruta con jornada en [D+1 − 14, D], que tengan `pred_xgboost` emitida **y** demanda real observada en la serie actual. Además, la jornada debe tener al menos 8 franjas observadas, como el soporte del backtesting.
  - **Valor:** factor = Σ real / Σ `pred_xgboost`.
  - **Demanda real:** sale siempre de la serie más reciente, así que una corrección tardía de la base se incorpora sola.
  - **Casos límite:** si la ventana queda vacía, o si Σ pred ≤ 0, el factor es 1 y se emite una advertencia (sección 6 del preregistro).
  - **Versión del historial:** si existen las dos (opción C), el factor usa siempre la definitiva.
- **Arranque del historial:**
  - **Hasta 2026-10-03:** las predicciones del script 43, con origen `backtest`.
  - **Del 2026-10-04 a la víspera del primer día de la piloto:** una ejecución de relleno que predice cada jornada con el mismo protocolo y los datos disponibles antes de las 04:00 de esa jornada, con origen `relleno`.
- **Avisos (no bloquean):**
  - jornadas de la ventana con menos de 10 franjas útiles;
  - factor fuera del rango observado en el backtesting, [0,68; 1,08].

## 5. Módulo de recomendación

`generar_recomendacion` sin cambios, con:
- **Parámetros:** los de `parametros__recomendacion_despacho__freeze_20260922_203820.csv` y la capacidad conjunta de 153 de su manifiesto;
- **Reglas:** política de festivos `divisor_propio`, servicio mínimo 1 y `usar_tope = false`.

**Entrada:** las franjas de D+1 de las dos rutas con la predicción final. La factibilidad se aplica por fecha a las dos rutas juntas, como en la evaluación. El resultado son los despachos por franja, el bloque horario y el ajuste de factibilidad.

## 6. Planilla

**Ubicación:** `data/piloto/planillas/planilla_<AAAA-MM-DD>_<estado>.xlsx`, una por jornada. Una nueva emisión crea otro archivo con sufijo `_v2`, con el motivo en el registro; nunca sobrescribe.

| Hoja | Contenido |
|---|---|
| Resumen | jornada, tipo de día y régimen; estado (OK / ADVERTENCIA / CONTINGENCIA / PRELIMINAR); advertencias en lenguaje llano; factor por ruta; fecha de los datos usados; identificador de la ejecución |
| Por bloque | ruta, bloque, horario del bloque, despachos recomendados; columnas para el despachador: **¿Siguió la recomendación?** (Sí / No / En parte, con lista desplegable), **Motivo** (lista desplegable más texto libre), despachos realizados |
| Por franja | ruta, franja de 30 min, bloque, despachos recomendados y las mismas columnas del despachador |

- **Lista de motivos inicial**, para ajustar con el despachador: falta de vehículo, falta de conductor, demanda distinta a la esperada, evento o tráfico, instrucción de la gerencia, otro.
- **La demanda predicha no se muestra** en las hojas del despachador, solo en el registro. Así se evita que el número de pasajeros sesgue su decisión. Se puede reconsiderar.
- **Dependencia:** `openpyxl` no está instalado y hace falta para las listas desplegables. Si prefieres no añadir la dependencia, la alternativa son dos CSV por jornada (UTF-8 con BOM, que Excel abre) sin listas desplegables.

## 7. Robustez

Cada ejecución avanza por pasos con comprobaciones. **Ninguna planilla sale sin un estado explícito en el nombre del archivo y en la cabecera.**

| Situación | Detección | Comportamiento |
|---|---|---|
| La base no responde o la extracción falla | Excepción o tiempo de espera | 3 reintentos con 10 min de espera. Si siguen fallando: planilla **CONTINGENCIA**, calculada con la última serie válida, indicando hasta qué fecha llegan los datos y que los rezagos y el factor no incluyen los días faltantes. Si no hay ninguna serie válida de las últimas 48 h: no se emite planilla, se deja `ESTADO_ULTIMA_EJECUCION.txt` con el error y la indicación de operar como de costumbre |
| Falta un día o el día D está incompleto | Despachos de D por ruta frente a la mediana de su tipo de día en las 8 semanas previas (< 80 % es incompleto). Intervalos de D con `ESTADO = 1` sin registro de registradora (lo habitual es ~1 %; > 5 % es incompleto). Días sin datos en la ventana de 14 días o en los rezagos (D, D − 1, D − 6) | **ADVERTENCIA**, con el día y la ruta afectados. En la opción C, la preliminar siempre lleva este aviso |
| Variables de D+1 con rezagos faltantes | Valores nulos en las variables de D+1 | **ADVERTENCIA** (XGBoost los admite, pero se sale del caso habitual) |
| Factor o predicciones fuera de rango | Factor fuera de [0,68; 1,08]; predicciones negativas o > 3 veces la máxima histórica de la franja | **ADVERTENCIA**; no bloquea |
| Fallo del modelo o del módulo | Excepción | No se emite planilla; estado de error |
| Ejecución tardía | Empieza después de las 03:30 | **ADVERTENCIA (TARDÍA)** |
| Dos ejecuciones a la vez | Archivo de bloqueo | La segunda termina sin hacer nada y lo registra |
| Código modificado | `git status` con cambios | No se ejecuta: la piloto solo corre desde un commit limpio, para poder reconstruir |

## 8. Controles antes de empezar (ensayo, sin entregar planillas)

1. **Extracción:** reextraer del 2026-09-20 al 2026-10-03 y comparar, por PK y campo, con el crudo de `data/actualizacion_20261004/`.
2. **Procesamiento por ventana:** el conjunto apto de esa ventana debe ser idéntico al de la actualización.
3. **Serie y variables:** la serie reconstruida hasta el 2026-10-03 debe ser idéntica al dataset de la actualización. Las variables de un día «futuro» simulado deben coincidir con las del dataset.
4. **Predicción y factor:** ejecutar el predictor como si fueran del 2026-09-01 al 2026-10-03. Debe reproducir `pred_xgboost` y la referencia de 52 s del script 43, el factor de 14 días de `serie_correccion` y la predicción de C3 de `observaciones__correccion_nivel_...`. Diferencia máxima < 10⁻⁴.
5. **Modo sombra:** una semana de ejecución programada sin entregar las planillas, revisando estados, tiempos y diferencias de la reextracción.

## 9. Registro y reconstrucción

**Carpeta por ejecución:** `data/piloto/ejecuciones/<id_ejecucion>/`, con `id_ejecucion` = `AAAAMMDD_HHMMSS`.

- `manifiesto.json`:
  - **Contexto:** jornada objetivo, versión (preliminar o definitiva), horas de inicio y fin de cada paso, estado y advertencias.
  - **Código y entorno:** commit de git, versiones de Python, pandas y xgboost.
  - **Entradas:** SHA-256 de las configuraciones, de los parámetros del módulo, de los hiperparámetros, de la instantánea de extracción, del conjunto apto y de la serie.
  - **Extracción:** ventana, `pk_ancla` y diferencias.
  - **Completitud:** las métricas de la sección 7.
  - **Factor por ruta:** valor, Σ real, Σ pred, franjas y jornadas de la ventana.
  - **Salidas:** archivos generados y su SHA-256.
- `ejecucion.log`: el registro completo. Los secretos de `.env` se ocultan, como ya hace el ETL.
- **Predicciones y recomendación** de la jornada, franja a franja.

Las instantáneas de extracción y la serie versionada se conservan. Un script `reconstruir --ejecucion <id>`, desde el mismo commit, vuelve a calcular la recomendación y comprueba que coincide byte a byte.

**Espacio:** la serie completa ocupa unos pocos MB por versión. Para no acumular, se conservan las de los últimos 30 días y la del primer día de cada mes; las instantáneas de extracción y los manifiestos se conservan siempre.

## 10. Programación en el Programador de tareas de Windows

- **Definición versionada** en `configs/piloto/tarea_nocturna.xml`; se registra con `schtasks /Create /TN "Piloto\RecomendacionNocturna" /XML ...`.
- **Acción:** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\regis\proyecto_grado\scripts\piloto\ejecutar_nocturno.ps1`. El script:
  - fija el directorio de trabajo y `PYTHONIOENCODING=utf-8`;
  - llama a `.venv\Scripts\python.exe -m proyecto_grado.piloto.nocturno --version definitiva`;
  - deja la salida estándar en el registro de la ejecución.
- **Para que no dependa de una sesión abierta:**
  - «Ejecutar tanto si el usuario inició sesión como si no»: guarda la contraseña de la cuenta y la tarea corre en segundo plano con tu usuario, así que tiene acceso a `.env` y al repositorio. Requiere el derecho «Iniciar sesión como proceso por lotes», que Windows concede al crear la tarea si eres administrador.
  - No ejecutar con privilegios elevados.
- **Desencadenador:** diario a las 00:30 (opción B). En la C, se añade otro a las 21:00 con `--version preliminar`.
- **Configuración:**
  - «Activar el equipo para ejecutar esta tarea», y los temporizadores de reactivación permitidos en el plan de energía;
  - «Ejecutar la tarea lo antes posible si no se inició a la hora programada»;
  - «Si la tarea ya se está ejecutando, no iniciar una nueva instancia»;
  - detener si dura más de 2 h;
  - reintentar 3 veces cada 15 min si falla;
  - desactivar «Iniciar solo si el equipo está conectado a la corriente alterna», si es un portátil.
- **Límites que no resuelve el programador:**
  - El equipo tiene que estar encendido o en suspensión, no apagado ni en hibernación.
  - Si el acceso a la base exige una VPN que se abre con la sesión del usuario, la tarea fallará sin sesión. Hay que confirmarlo.

## 11. Estructura de archivos nuevos

```
configs/piloto/piloto.yaml               candidato, ventanas, umbrales, rutas de entrada congeladas
configs/piloto/tarea_nocturna.xml        definición de la tarea
scripts/piloto/ejecutar_nocturno.ps1     envoltorio para el Programador de tareas
src/proyecto_grado/piloto/
    extraccion.py    ventana, reemplazo por clave, diferencias
    serie.py         bloques 4–8 por ventana y reconstrucción de la serie
    prediccion.py    franjas de D+1, XGBoost, referencia de 52 s
    correccion.py    historial y factor
    planilla.py      archivo de la jornada
    completitud.py   comprobaciones de la sección 7
    nocturno.py      orquestador, bloqueo, estados, manifiesto
    reconstruir.py
data/piloto/{extracciones, etl, serie, historial, ejecuciones, planillas}/
```

## 12. Decisiones pendientes

1. **Hora de ejecución:** A, B o C (sección 0). Recomiendo B, o C si el despachador necesita la planilla la noche anterior.
2. **Consulta de latencia:** autorización para la consulta de solo lectura de la sección 0, fuera del horario de operación.
3. **Formato de la planilla:** Excel con listas desplegables (añade `openpyxl`) o CSV.
4. **Entrega:** cómo llega la planilla al despachador (carpeta compartida, correo, impresión) y a qué hora empieza su turno.
5. **Equipo:** si queda encendido por la noche y si la base necesita VPN.
6. **Primer día de la piloto**, que fija el tramo de relleno del historial.
