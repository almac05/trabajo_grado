#!/usr/bin/env bash
# Instala o actualiza la piloto en la instancia EC2. Idempotente.
#
# Uso (como root, desde cualquier directorio):
#   sudo bash instalar.sh <commit|etiqueta> [--activar-timers]
#
# - Instala uv para el usuario despacho (si falta).
# - Clona o actualiza el repositorio en /opt/despacho/proyecto_grado y lo deja en
#   el commit o la etiqueta indicada (HEAD separado). Rechaza nombres de rama: la
#   piloto nunca corre desde una rama "viva".
# - uv sync --frozen sin extras (sin torch ni prophet).
# - Copia las unidades de systemd y hace daemon-reload.
# - Verifica /opt/despacho/.env (600, dueno despacho) y /opt/despacho/tunel.env.
# - Con --activar-timers, habilita y arranca los temporizadores.
# No crea el .env, no toca las llaves SSH y no corre el orquestador.
set -euo pipefail

USUARIO=despacho
CASA=/opt/despacho
REPO_DIR="$CASA/proyecto_grado"
REPO_URL="${REPO_URL:-https://github.com/almac05/trabajo_grado.git}"
UV="$CASA/.local/bin/uv"
UNIDADES=(tunel-ionos.service despacho-nocturno.service despacho-nocturno.timer
          despacho-alerta@.service despacho-verificacion.service despacho-verificacion.timer)
TIMERS=(despacho-nocturno.timer despacho-verificacion.timer)

morir() { echo "ERROR: $*" >&2; exit 1; }
paso() { echo; echo "==> $*"; }
como() { sudo -u "$USUARIO" -H -- "$@"; }

REF="${1:-}"
[[ -n "$REF" ]] || morir "Uso: sudo bash instalar.sh <commit|etiqueta> [--activar-timers]"
ACTIVAR=0
case "${2:-}" in
    "") ;;
    --activar-timers) ACTIVAR=1 ;;
    *) morir "Opcion desconocida: $2" ;;
esac
[[ $EUID -eq 0 ]] || morir "Ejecutar con sudo."
id "$USUARIO" >/dev/null 2>&1 || morir "No existe el usuario $USUARIO."
[[ -d "$CASA" ]] || morir "No existe $CASA."

paso "Paquetes del sistema (git, curl)"
faltan=()
for p in git curl ca-certificates; do
    dpkg -s "$p" >/dev/null 2>&1 || faltan+=("$p")
done
if ((${#faltan[@]})); then
    apt-get update -q && apt-get install -y -q "${faltan[@]}"
else
    echo "Ya instalados."
fi

paso "uv para $USUARIO"
if [[ ! -x "$UV" ]]; then
    como bash -c 'curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh'
fi
como "$UV" --version

paso "Repositorio en $REPO_DIR (ref $REF)"
if [[ ! -d "$REPO_DIR/.git" ]]; then
    como git clone --quiet "$REPO_URL" "$REPO_DIR"
fi
como git -C "$REPO_DIR" fetch --quiet --tags --prune origin
if como git -C "$REPO_DIR" show-ref --quiet --verify "refs/remotes/origin/$REF" ||
   como git -C "$REPO_DIR" show-ref --quiet --verify "refs/heads/$REF"; then
    morir "$REF es una rama. Indique un commit o una etiqueta (p. ej. piloto-v1.0)."
fi
COMMIT=$(como git -C "$REPO_DIR" rev-parse --verify --quiet "${REF}^{commit}") ||
    morir "No existe el commit o la etiqueta $REF."
if [[ -n "$(como git -C "$REPO_DIR" status --porcelain --untracked-files=no)" ]]; then
    morir "El repositorio tiene cambios locales en archivos versionados; no se toca."
fi
como git -C "$REPO_DIR" checkout --quiet --detach "$COMMIT"
echo "HEAD: $(como git -C "$REPO_DIR" log --oneline -1)"

paso "Entorno de Python (uv sync --frozen, sin extras)"
como bash -c "cd '$REPO_DIR' && '$UV' sync --frozen"
como bash -c "cd '$REPO_DIR' && '$UV' run --frozen python -c \
    'import proyecto_grado.piloto.nocturno, sys; print(\"Python\", sys.version.split()[0], \"- orquestador importable\")'"

paso "Unidades de systemd"
for u in "${UNIDADES[@]}"; do
    install -m 644 -o root -g root "$REPO_DIR/deploy/ec2/$u" "/etc/systemd/system/$u"
done
systemctl daemon-reload
systemd-analyze verify "${UNIDADES[@]/#//etc/systemd/system/}" 2>&1 | grep -v "^$" || true
# El tunel nunca queda habilitado: lo arranca el servicio nocturno.
systemctl disable tunel-ionos.service >/dev/null 2>&1 || true

paso "Archivos de entorno"
problemas=0
revisar() {  # ruta modos_permitidos
    local ruta="$1" permitidos="$2" modo dueno nombre
    if [[ ! -f "$ruta" ]]; then
        nombre=$(basename "$ruta")
        echo "FALTA $ruta (ver deploy/ec2/${nombre#.}.ejemplo)"; problemas=1; return
    fi
    modo=$(stat -c '%a' "$ruta"); dueno=$(stat -c '%U' "$ruta")
    if [[ " $permitidos " != *" $modo "* || "$dueno" != "$USUARIO" ]]; then
        echo "REVISAR $ruta: permisos $modo, dueno $dueno (se espera $permitidos y $USUARIO)"
        problemas=1
    else
        echo "OK $ruta ($modo, $dueno)"
    fi
}
revisar "$CASA/.env" "600"
revisar "$CASA/tunel.env" "600 640 644"

paso "Temporizadores"
if ((ACTIVAR)); then
    ((problemas == 0)) || morir "Corrija los archivos de entorno antes de activar los temporizadores."
    systemctl enable --now "${TIMERS[@]}"
else
    echo "No se activaron (use --activar-timers despues del ensayo manual)."
fi
systemctl list-timers --all 'despacho-*' --no-pager || true

paso "Resumen"
echo "Commit desplegado: $COMMIT"
echo "Ref: $REF"
echo "uv: $(como "$UV" --version)"
echo "Temporizadores activados: $([[ $ACTIVAR -eq 1 ]] && echo si || echo no)"
echo "Archivos de entorno: $([[ $problemas -eq 0 ]] && echo correctos || echo 'REVISAR (ver arriba)')"
