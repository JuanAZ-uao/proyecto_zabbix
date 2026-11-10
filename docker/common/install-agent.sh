#!/bin/sh
# Instala Zabbix Agent 2 (6.0 LTS, repo oficial para Debian 12) + supervisord + utilidades de prueba.
# Uso:  sh install-agent.sh [paquetes_extra_del_servicio...]
set -eu
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates curl wget supervisor procps iputils-ping stress-ng netcat-openbsd "$@"

wget -q -O /tmp/zabbix-release.deb \
  "https://repo.zabbix.com/zabbix/6.0/debian/pool/main/z/zabbix-release/zabbix-release_6.0-10+debian12_all.deb"
dpkg -i /tmp/zabbix-release.deb
apt-get update
apt-get install -y --no-install-recommends zabbix-agent2

rm -f /tmp/zabbix-release.deb
apt-get clean
rm -rf /var/lib/apt/lists/*
mkdir -p /run/zabbix && chown zabbix:zabbix /run/zabbix
