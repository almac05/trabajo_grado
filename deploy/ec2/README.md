# Despliegue de la piloto en EC2

Orquestador nocturno de la prueba piloto (`python -m proyecto_grado.piloto.nocturno`) en la instancia EC2 Ubuntu 24.04 de us-east-2. Diseño: `docs/diseno_piloto_proceso_nocturno.md`.

## Piezas

| Archivo | Qué hace |
|---|---|
| `tunel-ionos.service` | Túnel SSH a MySQL de IONOS en 127.0.0.1:3306. No se habilita: lo arranca el nocturno y se detiene solo al terminar (`StopWhenUnneeded=yes`; ver «Cómo se abre y se cierra el túnel»). |
| `despacho-nocturno.service` / `.timer` | Corrida diaria a las 00:30 (America/Bogota) con `--escribir-bd --subir-s3`. Si falla, alerta por SNS. |
| `despacho-alerta@.service` | Alerta por SNS: unidad, hora, `ESTADO_ULTIMA_EJECUCION.txt` y las últimas 30 líneas del journal, sin secretos. |
| `despacho-verificacion.service` / `.timer` | Vigilante de las 05:00: alerta si no hay una corrida nocturna OK para la jornada de hoy y publica `JornadaCubierta`. |
| `env.ejemplo` | Plantilla de `/opt/despacho/.env` (credenciales; permisos 600). |
| `tunel.env.ejemplo` | Plantilla de `/opt/despacho/tunel.env` (destino del túnel; no versionado porque el repositorio es público). |
| `instalar.sh` | Instala o actualiza en un commit o etiqueta. Idempotente; los temporizadores solo con `--activar-timers`. |
| `../cloudwatch/tablero_despacho.json` | Tablero de CloudWatch (ver «Métricas y tablero CloudWatch»). |

Todo corre como el usuario `despacho` (sin sudo). Las credenciales de AWS vienen del rol de la instancia; nunca hay claves en archivos. Las unidades de servicio leen `/opt/despacho/.env` con `EnvironmentFile=`.

### Dos reglas para los comandos manuales

- **El `cd` va dentro de `sudo -u despacho -H bash -c '...'`.** La sesión de Session Manager es `ssm-user`, que no puede entrar a `/opt/despacho`: un `cd /opt/despacho/proyecto_grado` previo falla, y lo mismo un `cat` o `ls` de `data/piloto`. Todo comando que toque el repositorio o sus salidas se ejecuta como `despacho`.
- **Nada de CLI `aws` para el usuario `despacho`.** La CLI de Ubuntu instalada por snap no funciona para `despacho`, cuyo home (`/opt/despacho`) está fuera de `/home`. Para consultar AWS con el rol de la instancia se usa boto3 desde el entorno del proyecto:

  ```bash
  sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && ~/.local/bin/uv run --frozen python -c "
  import boto3
  r = boto3.client(\"s3\").list_objects_v2(Bucket=\"registel-montebello-despacho\", Prefix=\"piloto/planillas/\")
  print([o[\"Key\"] for o in r.get(\"Contents\", [])][-5:])"'
  ```

### Cómo se abre y se cierra el túnel

- **Se abre** con el nocturno: `despacho-nocturno.service` tiene `Requires=` y `After=tunel-ionos.service`, así que systemd arranca el túnel antes que la corrida, y `esperar_puerto.sh` espera hasta 60 s a que 127.0.0.1:3306 responda.
- **Se cierra** solo: `tunel-ionos.service` tiene `StopWhenUnneeded=yes` y systemd lo detiene cuando el nocturno termina (OK o con fallo), porque ya ninguna unidad activa lo requiere.
- **El nocturno no detiene el túnel por su cuenta.** Hasta la noche 1 (13-oct) tenía `ExecStopPost=+/bin/systemctl stop tunel-ionos.service`, y eso es un bloqueo mutuo: por `After=`, systemd detiene el túnel solo después de que el nocturno termina de detenerse, y el nocturno esperaba ese stop. La corrida terminó OK a las 00:30:42, el stop-post agotó los 90 s («State 'stop-post' timed out»), la unidad quedó en `failed` y `OnFailure=` mandó una alerta SNS falsa. El túnel se cerró ese mismo segundo por `StopWhenUnneeded=`. `tests/piloto/test_despliegue.py` falla si vuelve un `ExecStop=`/`ExecStopPost=` con `systemctl stop` síncrono de una dependencia.

## Instalación inicial

Todos los comandos se ejecutan en la instancia, por Session Manager.

1. Instalar el código en la etiqueta que se despliega (sin activar los temporizadores):

   ```bash
   curl -fsSL https://raw.githubusercontent.com/almac05/trabajo_grado/piloto-v1.1/deploy/ec2/instalar.sh -o /tmp/instalar.sh
   sudo bash /tmp/instalar.sh piloto-v1.1
   ```

   Si el repositorio ya está clonado, también sirve `sudo bash /opt/despacho/proyecto_grado/deploy/ec2/instalar.sh piloto-v1.1`.

2. Crear los archivos de entorno a partir de las plantillas:

   ```bash
   sudo install -o despacho -g despacho -m 600 /opt/despacho/proyecto_grado/deploy/ec2/env.ejemplo /opt/despacho/.env
   sudo -u despacho nano /opt/despacho/.env          # REGISTEL_DB_USER, REGISTEL_DB_PASSWORD, PILOTO_SNS_TOPIC
   sudo install -o despacho -g despacho -m 640 /opt/despacho/proyecto_grado/deploy/ec2/tunel.env.ejemplo /opt/despacho/tunel.env
   sudo -u despacho nano /opt/despacho/tunel.env     # PILOTO_TUNEL_DESTINO=usuario@host
   ```

3. Descargar los insumos congelados de `s3://registel-montebello-despacho/insumos/` y verificarlos contra `configs/piloto/piloto.yaml`:

   ```bash
   sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && set -a && . /opt/despacho/.env && set +a && \
     PILOTO_ENTORNO=EC2 ~/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno --descargar-insumos'
   ```

4. Ensayo manual con el túnel (ver «Ensayo manual»).

5. Activar los temporizadores:

   ```bash
   sudo bash /opt/despacho/proyecto_grado/deploy/ec2/instalar.sh piloto-v1.1 --activar-timers
   systemctl list-timers 'despacho-*'
   ```

## Actualizar a un nuevo commit

Desde el equipo de desarrollo: commit, etiqueta (por ejemplo `piloto-v1.1`) y push. En la instancia:

```bash
sudo bash /opt/despacho/proyecto_grado/deploy/ec2/instalar.sh piloto-v1.1 --activar-timers
```

El script rechaza nombres de rama, se detiene si hay cambios locales en archivos versionados y deja el repositorio en el commit exacto de la etiqueta (HEAD separado). El orquestador solo corre desde un árbol limpio.

Si la versión nueva agrega variables a `env.ejemplo` (v1.1: `PILOTO_METRICAS=1`), agregarlas a mano a `/opt/despacho/.env`:

```bash
sudo -u despacho -H bash -c 'grep -q "^PILOTO_METRICAS=" /opt/despacho/.env || echo "PILOTO_METRICAS=1" >> /opt/despacho/.env'
```

## Ver logs

```bash
systemctl list-timers 'despacho-*'                       # próxima y última ejecución
systemctl status despacho-nocturno.service
journalctl -u despacho-nocturno.service -n 200 --no-pager
journalctl -u tunel-ionos.service --since today
journalctl -u despacho-verificacion.service --since today
sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && cat data/piloto/ESTADO_ULTIMA_EJECUCION.txt'
sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && ls data/piloto/ejecuciones/'  # manifiesto.json y ejecucion.log de cada corrida
```

## Asignación del piloto

El grupo de cada jornada está en `configs/piloto/asignacion_grupos.yaml` (v1.4). La corrida de las 00:30 toma el grupo de la jornada que predice: la del lunes 19 a las 00:30 (domingo 18 en la noche) es la primera CONTROL.

| Grupo | Jornadas | Qué ve el despachador |
|---|---|---|
| MODULO | 22, 24, 26, 27, 28 y 30 de octubre | La recomendación, en Regisdata y en la planilla. |
| CONTROL | 19, 20, 21, 23, 25 y 29 de octubre | Nada. La recomendación se calcula y se guarda, pero él opera como siempre. |
| SOMBRA | Cualquier fecha sin asignar (13 al 18 y desde el 31 de octubre) | Nada. Es una ejecución de ensayo. |

La vista `v_recomendaciones_vigentes`, que es la que lee Regisdata, solo muestra MODULO. Está definida en `deploy/mysql/esquema_recomendaciones.sql` y `tests/piloto/test_esquema_sql.py` falla si deja de filtrar por MODULO. En CONTROL y SOMBRA las filas quedan en la base con su grupo y el despachador no ve nada. La asignación se hizo por sorteo en bloques por día de la semana (semilla 20261019, `scripts/piloto/sorteo_grupos.py`) y no se vuelve a sortear. El método está en `docs/diseno_piloto_proceso_nocturno.md`, sección 13.5.

**Cuidado con los ensayos manuales.** Un ensayo con `--escribir-bd` y `--fecha-objetivo` en una jornada MODULO escribe filas MODULO, y esas filas sí aparecen en la vista. Entre el 19 y el 30 de octubre, los ensayos con `--escribir-bd` se hacen solo con fechas SOMBRA.

## Ensayo manual

El ensayo usa la base real: hacerlo entre las 21:00 y las 04:00 (hora de Colombia). Fuera de ese horario el orquestador se niega, salvo `--forzar-horario`.

```bash
sudo systemctl start tunel-ionos.service
sudo -u despacho bash /opt/despacho/proyecto_grado/scripts/piloto/esperar_puerto.sh 127.0.0.1 3306 60
sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && set -a && . /opt/despacho/.env && set +a && \
  export PILOTO_ENTORNO=EC2 TZ=America/Bogota && \
  ~/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno \
  --fecha-objetivo 2026-10-08 --directorio-salidas data/piloto/ensayo_ec2; echo "codigo $?"'
sudo systemctl stop tunel-ionos.service
sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && cat data/piloto/ensayo_ec2/ESTADO_ULTIMA_EJECUCION.txt'
```

Para probar la escritura en la base sin que nadie la vea, agregar `--escribir-bd`: la jornada sin asignar es SOMBRA y la vista de Regisdata solo muestra MODULO.

Un ensayo con `--fecha-objetivo` no publica métricas en CloudWatch, salvo con `--publicar-metricas` (ver la advertencia en «Métricas y tablero CloudWatch»).

Para probar la unidad completa tal como la corre el temporizador (escribe en la base y en S3): `sudo systemctl start despacho-nocturno.service`.

## Métricas y tablero CloudWatch

Con `PILOTO_METRICAS=1` en `/opt/despacho/.env`, la corrida nocturna publica al cerrar (también en ERROR) y el vigilante de las 05:00 publica `JornadaCubierta`. Namespace `Montebello/Despacho`, región us-east-2 (`PILOTO_CW_NAMESPACE` y `PILOTO_AWS_REGION` los cambian). Un fallo de CloudWatch nunca cambia el estado ni el código de salida: queda una línea en el log y `"metricas": {"metricas_publicadas": false, "motivo": ...}` en el manifiesto. Cuando funciona, el manifiesto lleva `true` y la lista de métricas enviadas. En el plan B (Windows, sin rol) no se publica: dejar `PILOTO_METRICAS` sin definir.

| Métrica | Dimensiones | Unidad | Quién la publica |
|---|---|---|---|
| `EstadoCorrida` | — | None | nocturno: 0 OK, 1 ADVERTENCIA, 2 CONTINGENCIA, 3 ERROR |
| `DuracionTotal` | — | Seconds | nocturno |
| `DuracionExtraccion` | — | Seconds | nocturno (si llegó a extraer) |
| `RegistrosExtraidos` | — | Count | nocturno: filas deduplicadas de la ventana |
| `FilasRecomendaciones` | — | Count | nocturno: filas escritas en la base o generadas |
| `FactorCorreccion` | `Ruta` = 1, 3 | None | nocturno: factor de 14 días |
| `MemoriaPico` | — | Megabytes | nocturno: ru_maxrss del proceso y sus hijos |
| `JornadaCubierta` | — | Count | vigilante: 1 si hay corrida válida para hoy, 0 si no |
| `ErrorMAE`, `ErrorRMSE` | `Ruta` = 1, 3 | None | nocturno: error de la jornada anterior (pasajeros/franja) |
| `ErrorMAPE` | `Ruta` = 1, 3 | Percent | nocturno: MAPE parcial, franjas con real ≥ 10 |
| `SesgoPct` | `Ruta` = 1, 3 | Percent | nocturno: (Σpred − Σreal) / Σreal × 100 |

Son 17 combinaciones de nombre + dimensiones, la lista cerrada de `src/proyecto_grado/piloto/metricas.py` (una prueba falla si crece). El desempeño se calcula contra la predicción emitida la noche anterior; si no la hay (primera noche, o la noche anterior falló), se omite con el motivo en el bloque `desempeno` del manifiesto. El detalle por ruta queda en `data/piloto/indicadores/<D>.parquet` y, con `--subir-s3`, en `s3://registel-montebello-despacho/piloto/indicadores/`.

**Advertencia sobre ensayos.** Un ensayo con `--publicar-metricas` publica en las mismas métricas que la producción, con la hora del ensayo: el punto se mezcla con los de las corridas nocturnas (y un ensayo de una jornada pasada aparece como si fuera la de hoy). Usarlo solo para verificar la publicación, y tenerlo en cuenta al leer el tablero ese día.

### Permiso del rol de la instancia

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": {"StringEquals": {"cloudwatch:namespace": "Montebello/Despacho"}}
    }
  ]
}
```

El rol solo puede publicar: desde la instancia no se pueden listar ni leer las métricas (`ListMetrics` y `GetMetricData` dan AccessDenied). La verificación en la instancia es el bloque `metricas` del manifiesto; la consulta de los datos se hace en la consola.

### Tablero

1. En la consola de CloudWatch (us-east-2): Paneles → Crear panel (por ejemplo `Montebello-Despacho`).
2. Acciones → Ver/editar origen, pegar el contenido de `deploy/cloudwatch/tablero_despacho.json`.
3. Reemplazar `REEMPLAZAR_INSTANCE_ID` por el id de la instancia (solo en la consola; no se versiona). Guardar.

Rango por defecto de 30 días. Los widgets de `Montebello/Despacho` usan periodo de 3600 s: cada corrida aparece como un punto en la hora en que terminó, sin mezclarse con otra publicación del mismo día (por ejemplo, un ensayo). La CPU de la instancia (`AWS/EC2 CPUUtilization`) va con periodo de 300 s.

### Costo

Capa gratuita de CloudWatch: 10 métricas personalizadas, 3 tableros (hasta 50 métricas cada uno), 10 alarmas y 1 millón de llamadas a la API al mes. Fuera de ella, USD 0,30 por métrica al mes. AWS prorratea las métricas personalizadas por hora y solo cobra las horas en que se envían datos ([precios](https://aws.amazon.com/cloudwatch/pricing/)). Con una publicación diaria, cada métrica cuenta una hora al día:

- 17 métricas × 1 h/día × 30 días = 510 métrica-hora ≈ 510 / 730 = **0,70 métrica-mes**.
- Sin capa gratuita serían 0,70 × USD 0,30 ≈ **USD 0,21 al mes**; con ella, dentro de las 10 métricas gratuitas.
- Cada ensayo con `--publicar-metricas` suma a lo sumo una hora por métrica. Las llamadas (unas 60 `PutMetricData` al mes) quedan muy por debajo del millón.
- El tablero es 1 de los 3 gratuitos; no se crean alarmas.

Confirmarlo en Billing → Free Tier después del primer mes.

## Plan B: pasar al equipo Windows

1. En EC2, detener los temporizadores para que no corran ni alerten:

   ```bash
   sudo systemctl disable --now despacho-nocturno.timer despacho-verificacion.timer
   ```

2. En Windows (PowerShell, en la raíz del repositorio y en el mismo commit desplegado). El `.env` local lleva las credenciales de la base, `PILOTO_S3_BUCKET` y `PILOTO_S3_PREFIJO`. Las credenciales de AWS, limitadas a este bucket, van en un perfil de `%USERPROFILE%\.aws\credentials` (`aws configure`), nunca en `.env`. Sin rol de instancia no se publican métricas: no definir `PILOTO_METRICAS`.

   ```powershell
   git checkout piloto-v1.1
   $env:PILOTO_ENTORNO = "LOCAL"
   .venv\Scripts\python.exe -m proyecto_grado.piloto.nocturno --sincronizar-estado
   ```

   Esto descarga de S3 el último estado (almacén e historial) y lo verifica.

3. Cada noche, después de las 00:30:

   ```powershell
   .venv\Scripts\python.exe -m proyecto_grado.piloto.nocturno --escribir-bd --subir-s3
   ```

   Al terminar en OK publica el estado en S3, igual que EC2.

## Volver a EC2

1. En Windows, dejar de correr el proceso. La última corrida OK ya publicó su estado.
2. En EC2, sincronizar y reactivar:

   ```bash
   sudo -u despacho -H bash -c 'cd /opt/despacho/proyecto_grado && set -a && . /opt/despacho/.env && set +a && \
     PILOTO_ENTORNO=EC2 ~/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno --sincronizar-estado'
   sudo systemctl enable --now despacho-nocturno.timer despacho-verificacion.timer
   ```

Las corridas con `--subir-s3` también sincronizan al empezar: si el estado de S3 es más nuevo que el local, lo descargan antes de extraer.

**Nunca corran los dos equipos la misma noche.** El estado se compara por id y no hay bloqueo entre equipos.
