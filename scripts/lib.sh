#!/usr/bin/env bash
# Funciones comunes de los scripts de prueba. Solo requieren Docker (sin instalar nada en el host).
set -euo pipefail
export MSYS_NO_PATHCONV=1                      # evita que Git Bash en Windows reescriba rutas /app/...
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Carga .env si existe (para puertos personalizados)
if [ -f .env ]; then set -a; . ./.env; set +a; fi
WEB_PORT="${WEB_PORT:-8080}"
MAILHOG_UI_PORT="${MAILHOG_UI_PORT:-8025}"

# contenedor de cada servicio y nombre del proceso en supervisord
container_of() { case "$1" in web) echo lab-web;; db) echo lab-db;; dns) echo lab-dns;; ftp) echo lab-ftp;; *) echo "$1";; esac; }
program_of()   { case "$1" in web) echo nginx;;  db) echo mysqld;;  dns) echo named;;  ftp) echo vsftpd;;  *) echo "$1";; esac; }

# Ejecuta measure.py dentro de la red del laboratorio (sin levantar dependencias)
measure() { docker compose run --rm --no-deps -T provisioner python /app/measure.py "$@"; }

# Vacia la bandeja de Mailhog para que la evidencia sea limpia
clear_mailhog() {
  curl -s -X DELETE "http://localhost:${MAILHOG_UI_PORT}/api/v1/messages" >/dev/null && echo "Mailhog vaciado."
}

banner() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
