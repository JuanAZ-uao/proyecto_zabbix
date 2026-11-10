#!/usr/bin/env bash
# PRUEBA: umbral de disco.  Llena la particion /data (tmpfs de 64 MB) de un host para pasar el 80 % y el 90 %.
#   Uso: scripts/test-disk-fill.sh [web|db|dns|ftp] [limpiar]     (por defecto: web)
. "$(dirname "$0")/lib.sh"
SVC="${1:-web}"; C="$(container_of "$SVC")"

if [ "${2:-}" = "limpiar" ]; then
  docker exec "$C" sh -c 'rm -f /data/relleno*; df -h /data'
  exit 0
fi
clear_mailhog
banner "Llenando /data en $C al 85 % (alerta Warning) y despues al 95 % (alerta High)"
docker exec "$C" sh -c 'dd if=/dev/zero of=/data/relleno1 bs=1M count=54 status=none; df -h /data'
echo "Espera ~30 s para ver 'Disco /data casi lleno' (Warning)..."; sleep 30
docker exec "$C" sh -c 'dd if=/dev/zero of=/data/relleno2 bs=1M count=7 status=none; df -h /data'
echo "Espera ~30 s para ver 'Disco /data CRITICO' (High). Para limpiar:  scripts/test-disk-fill.sh $SVC limpiar"
