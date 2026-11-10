#!/usr/bin/env bash
# PRUEBA: caida de SERVICIO (el contenedor sigue vivo; solo se detiene el proceso del servicio).
#   Uso: scripts/test-service-down.sh [web|db|dns|ftp]     (por defecto: ftp)
. "$(dirname "$0")/lib.sh"
SVC="${1:-ftp}"; C="$(container_of "$SVC")"; P="$(program_of "$SVC")"
EXPECT="$(case "$SVC" in web) echo "Servicio HTTP";; db) echo "MySQL no acepta";; dns) echo "DNS no resuelve";; ftp) echo "Servicio FTP";; esac)"
CTL="supervisorctl -c /etc/supervisor/lab-supervisord.conf"

banner "1/3 Preparacion"
clear_mailhog

banner "2/3 Caida del servicio: supervisorctl stop $P  (en $C)"
docker exec "$C" $CTL stop "$P"
T0="$(docker exec zabbix-server date -u +%Y-%m-%dT%H:%M:%S.000Z)"   # reloj de Docker (el mismo de Zabbix)
echo "T0 = $T0"
measure --host "$C" --since "$T0" --wait 240 --expect "$EXPECT"

banner "3/3 Recuperacion: supervisorctl start $P"
docker exec "$C" $CTL start "$P"
T1="$(docker exec zabbix-server date -u +%Y-%m-%dT%H:%M:%S.000Z)"
measure --host "$C" --since "$T1" --wait 240 --recovery --expect "$EXPECT"
