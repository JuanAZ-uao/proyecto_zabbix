#!/usr/bin/env bash
# PRUEBA: caida de host.  Detiene un contenedor, mide cuanto tarda Zabbix en detectarlo y
# cuanto tarda en llegar el correo a Mailhog; despues lo levanta y mide la recuperacion.
#   Uso: scripts/test-host-down.sh [web|db|dns|ftp]     (por defecto: web)
. "$(dirname "$0")/lib.sh"
SVC="${1:-web}"; C="$(container_of "$SVC")"

banner "1/3 Preparacion"
clear_mailhog
sleep 3

banner "2/3 Caida: docker stop $C"
docker stop "$C" >/dev/null
T0="$(docker inspect -f '{{.State.FinishedAt}}' "$C")"
echo "Contenedor detenido (T0 = $T0)"
measure --host "$C" --since "$T0" --wait 240 --expect "Host caído"

banner "3/3 Recuperacion: docker start $C"
docker start "$C" >/dev/null
T1="$(docker inspect -f '{{.State.StartedAt}}' "$C")"
measure --host "$C" --since "$T1" --wait 240 --recovery --expect "Host caído"
echo; echo "Revisa http://localhost:${MAILHOG_UI_PORT} (correos) y http://localhost:${WEB_PORT} (Monitoring > Problems)."
