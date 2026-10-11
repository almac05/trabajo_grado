#!/usr/bin/env bash
# Envia por SNS la alerta del fallo de una unidad de systemd.
# Uso: alerta.sh <unidad>   (lo invoca despacho-alerta@.service con %i)
# El mensaje pasa por el filtro de secretos de proyecto_grado.piloto.registro.
set -euo pipefail

unidad="${1:?Uso: alerta.sh <unidad>}"
uv="${UV:-/opt/despacho/.local/bin/uv}"
cd "$(dirname "$0")/../.."
exec "$uv" run --frozen python -m proyecto_grado.piloto.alerta --unidad "$unidad"
