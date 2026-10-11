# Despliegue de la piloto en EC2

Orquestador nocturno de la prueba piloto (`python -m proyecto_grado.piloto.nocturno`) en la instancia EC2 Ubuntu 24.04 de us-east-2. Diseño: `docs/diseno_piloto_proceso_nocturno.md`.

## Piezas

| Archivo | Qué hace |
|---|---|
| `tunel-ionos.service` | Túnel SSH a MySQL de IONOS en 127.0.0.1:3306. No se habilita: lo arranca el nocturno y se detiene al terminar. |
| `despacho-nocturno.service` / `.timer` | Corrida diaria a las 00:30 (America/Bogota) con `--escribir-bd --subir-s3`. Si falla, alerta por SNS. |
| `despacho-alerta@.service` | Alerta por SNS: unidad, hora, `ESTADO_ULTIMA_EJECUCION.txt` y las últimas 30 líneas del journal, sin secretos. |
| `despacho-verificacion.service` / `.timer` | Vigilante de las 05:00: alerta si no hay una corrida nocturna OK para la jornada de hoy. |
| `env.ejemplo` | Plantilla de `/opt/despacho/.env` (credenciales; permisos 600). |
| `tunel.env.ejemplo` | Plantilla de `/opt/despacho/tunel.env` (destino del túnel; no versionado porque el repositorio es público). |
| `instalar.sh` | Instala o actualiza en un commit o etiqueta. Idempotente; los temporizadores solo con `--activar-timers`. |

Todo corre como el usuario `despacho` (sin sudo). Las credenciales de AWS vienen del rol de la instancia; nunca hay claves en archivos.

## Instalación inicial

Todos los comandos se ejecutan en la instancia, por Session Manager.

1. Instalar el código en la etiqueta que se despliega (sin activar los temporizadores):

   ```bash
   curl -fsSL https://raw.githubusercontent.com/almac05/trabajo_grado/piloto-v1.0/deploy/ec2/instalar.sh -o /tmp/instalar.sh
   sudo bash /tmp/instalar.sh piloto-v1.0
   ```

   Si el repositorio ya está clonado, también sirve `sudo bash /opt/despacho/proyecto_grado/deploy/ec2/instalar.sh piloto-v1.0`.

2. Crear los archivos de entorno a partir de las plantillas:

   ```bash
   sudo install -o despacho -g despacho -m 600 /opt/despacho/proyecto_grado/deploy/ec2/env.ejemplo /opt/despacho/.env
   sudo -u despacho nano /opt/despacho/.env          # REGISTEL_DB_USER, REGISTEL_DB_PASSWORD, PILOTO_SNS_TOPIC
   sudo install -o despacho -g despacho -m 640 /opt/despacho/proyecto_grado/deploy/ec2/tunel.env.ejemplo /opt/despacho/tunel.env
   sudo -u despacho nano /opt/despacho/tunel.env     # PILOTO_TUNEL_DESTINO=usuario@host
   ```

3. Descargar los insumos congelados de `s3://registel-montebello-despacho/insumos/` y verificarlos contra `configs/piloto/piloto.yaml`:

   ```bash
   cd /opt/despacho/proyecto_grado
   sudo -u despacho -H bash -c 'set -a; . /opt/despacho/.env; set +a; PILOTO_ENTORNO=EC2 ~/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno --descargar-insumos'
   ```

4. Ensayo manual con el túnel (ver «Ensayo manual»).

5. Activar los temporizadores:

   ```bash
   sudo bash /opt/despacho/proyecto_grado/deploy/ec2/instalar.sh piloto-v1.0 --activar-timers
   systemctl list-timers 'despacho-*'
   ```

## Actualizar a un nuevo commit

Desde el equipo de desarrollo: commit, etiqueta (por ejemplo `piloto-v1.1`) y push. En la instancia:

```bash
sudo bash /opt/despacho/proyecto_grado/deploy/ec2/instalar.sh piloto-v1.1 --activar-timers
```

El script rechaza nombres de rama, se detiene si hay cambios locales en archivos versionados y deja el repositorio en el commit exacto de la etiqueta (HEAD separado). El orquestador solo corre desde un árbol limpio.

## Ver logs

```bash
systemctl list-timers 'despacho-*'                       # próxima y última ejecución
systemctl status despacho-nocturno.service
journalctl -u despacho-nocturno.service -n 200 --no-pager
journalctl -u tunel-ionos.service --since today
journalctl -u despacho-verificacion.service --since today
cat /opt/despacho/proyecto_grado/data/piloto/ESTADO_ULTIMA_EJECUCION.txt
ls /opt/despacho/proyecto_grado/data/piloto/ejecuciones/  # manifiesto.json y ejecucion.log de cada corrida
```

## Ensayo manual

El ensayo usa la base real: hacerlo entre las 21:00 y las 04:00 (hora de Colombia). Fuera de ese horario el orquestador se niega, salvo `--forzar-horario`.

```bash
sudo systemctl start tunel-ionos.service
sudo -u despacho bash /opt/despacho/proyecto_grado/scripts/piloto/esperar_puerto.sh 127.0.0.1 3306 60
cd /opt/despacho/proyecto_grado
sudo -u despacho -H bash -c 'set -a; . /opt/despacho/.env; set +a; export PILOTO_ENTORNO=EC2 TZ=America/Bogota; \
  ~/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno \
  --fecha-objetivo 2026-10-08 --directorio-salidas data/piloto/ensayo_ec2'
echo "codigo $?"
sudo systemctl stop tunel-ionos.service
cat data/piloto/ensayo_ec2/ESTADO_ULTIMA_EJECUCION.txt
```

Para probar la escritura en la base sin que nadie la vea, agregar `--escribir-bd`: la jornada sin asignar es SOMBRA y la vista de Regisdata solo muestra MODULO.

Para probar la unidad completa tal como la corre el temporizador (escribe en la base y en S3): `sudo systemctl start despacho-nocturno.service`.

## Plan B: pasar al equipo Windows

1. En EC2, detener los temporizadores para que no corran ni alerten:

   ```bash
   sudo systemctl disable --now despacho-nocturno.timer despacho-verificacion.timer
   ```

2. En Windows (PowerShell, en la raíz del repositorio y en el mismo commit desplegado). El `.env` local lleva las credenciales de la base, `PILOTO_S3_BUCKET` y `PILOTO_S3_PREFIJO`. Las credenciales de AWS, limitadas a este bucket, van en un perfil de `%USERPROFILE%\.aws\credentials` (`aws configure`), nunca en `.env`:

   ```powershell
   git checkout piloto-v1.0
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
   cd /opt/despacho/proyecto_grado
   sudo -u despacho -H bash -c 'set -a; . /opt/despacho/.env; set +a; PILOTO_ENTORNO=EC2 ~/.local/bin/uv run --frozen python -m proyecto_grado.piloto.nocturno --sincronizar-estado'
   sudo systemctl enable --now despacho-nocturno.timer despacho-verificacion.timer
   ```

Las corridas con `--subir-s3` también sincronizan al empezar: si el estado de S3 es más nuevo que el local, lo descargan antes de extraer.

**Nunca corran los dos equipos la misma noche.** El estado se compara por id y no hay bloqueo entre equipos.
