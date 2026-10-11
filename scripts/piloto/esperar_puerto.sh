#!/usr/bin/env bash
# Espera a que host:puerto acepte conexiones TCP, hasta un maximo de segundos.
# Uso: esperar_puerto.sh <host> <puerto> [segundos=60]
# Sale con 0 en cuanto responde y con 1 si se agota el tiempo.
set -euo pipefail

host="${1:?Uso: esperar_puerto.sh <host> <puerto> [segundos]}"
puerto="${2:?Uso: esperar_puerto.sh <host> <puerto> [segundos]}"
maximo="${3:-60}"

for ((i = 0; i < maximo; i++)); do
    if (exec 3<>"/dev/tcp/${host}/${puerto}") 2>/dev/null; then
        echo "Puerto ${host}:${puerto} disponible tras ${i} s."
        exit 0
    fi
    sleep 1
done
echo "El puerto ${host}:${puerto} no respondio en ${maximo} s." >&2
exit 1
