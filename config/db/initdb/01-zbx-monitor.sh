#!/bin/bash
# Crea el usuario de monitoreo (privilegios minimos segun la documentacion del
# template "MySQL by Zabbix agent 2"). Se ejecuta solo la primera vez que se crea el volumen.
set -e
MONITOR_USER="${ZBX_MONITOR_USER:-zbx_monitor}"
MONITOR_PASS="${ZBX_MONITOR_PASSWORD:-zbx_monitor_pass}"
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
  CREATE USER IF NOT EXISTS '${MONITOR_USER}'@'%' IDENTIFIED WITH mysql_native_password BY '${MONITOR_PASS}';
  GRANT REPLICATION CLIENT, PROCESS, SHOW DATABASES, SHOW VIEW ON *.* TO '${MONITOR_USER}'@'%';
  FLUSH PRIVILEGES;
EOSQL
