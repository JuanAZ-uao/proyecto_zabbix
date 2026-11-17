#!/usr/bin/env bash
# PRUEBA: carga HTTP real contra lab-web con Artillery. A diferencia de test-stress.sh, que genera
# carga sintetica DENTRO del contenedor, aqui el trafico entra por el puerto 80 desde otro contenedor
# de la red lab-net, igual que lo haria un usuario externo.
#   Uso: scripts/test-artillery.sh        (fases y tasas en artillery/attack.yml)
. "$(dirname "$0")/lib.sh"
IMAGE="artilleryio/artillery:latest"

banner "Carga HTTP sobre lab-web: 20s de calentamiento + 40s de rampa + 60s de pico a 250 req/s"

docker image inspect "$IMAGE" >/dev/null 2>&1 || {
  echo "Descargando $IMAGE (solo la primera vez; la imagen es grande)..."
  docker pull "$IMAGE"
}

echo "Observa el dashboard 'Lab - Visión general' y Monitoring > Latest data > lab-web (filtro 'nginx')."
docker compose run --rm --no-deps artillery run /scripts/attack.yml

echo
echo "Ataque terminado. Compara el pico de peticiones por segundo de nginx con la CPU de lab-web."
echo "Para subir la carga, aumenta arrivalRate en artillery/attack.yml."
