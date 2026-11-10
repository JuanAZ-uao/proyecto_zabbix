#!/usr/bin/env bash
# PRUEBA: dashboard en tiempo real + alerta de umbral.  Genera carga de CPU y RAM con stress-ng
# DENTRO de un contenedor; las metricas por contenedor (cgroup) suben solo en ese host.
#   Uso: scripts/test-stress.sh [web|db|dns|ftp] [segundos]     (por defecto: web 240)
. "$(dirname "$0")/lib.sh"
SVC="${1:-web}"; SECS="${2:-240}"; C="$(container_of "$SVC")"

banner "Carga en $C durante ${SECS}s: 2 hilos de CPU + 100 MB de RAM (limite del contenedor: 1 CPU / 128 MB)"
clear_mailhog
echo "Abre el dashboard 'Lab - Visión general' > pagina 'Recursos en tiempo real' y observa $C."
docker exec "$C" stress-ng --cpu 2 --vm 1 --vm-bytes 100M --timeout "${SECS}s" --metrics-brief
echo "Carga terminada. En ~1-2 min los problemas 'CPU alta' y 'Memoria alta' se resuelven solos."
echo "Correos: http://localhost:${MAILHOG_UI_PORT}"
