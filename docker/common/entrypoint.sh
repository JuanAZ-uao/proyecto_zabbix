#!/bin/sh
# Entrypoint comun de los hosts monitoreados: prepara el entorno y lanza supervisord,
# que mantiene vivos el servicio (nginx/mysqld/named/vsftpd) y el Zabbix Agent 2.
set -e
mkdir -p /run/zabbix && chown zabbix:zabbix /run/zabbix
if [ -f /usr/local/bin/lab-pre-start.sh ]; then
  sh /usr/local/bin/lab-pre-start.sh
fi
exec /usr/bin/supervisord -n -c /etc/supervisor/lab-supervisord.conf
