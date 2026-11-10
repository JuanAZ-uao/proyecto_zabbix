#!/bin/sh
# Chequeo externo de Zabbix: valida login + listado FTP real (no solo el puerto abierto).
# Uso (item "External check"):  ftp_login.sh[{HOST.CONN},{$FTP.USER},{$FTP.PASSWORD}]
# Devuelve 1 si el login y el listado funcionan, 0 en caso contrario.
HOST="$1"; USER="$2"; PASS="$3"
if curl -s --max-time 5 --user "${USER}:${PASS}" "ftp://${HOST}/" --list-only >/dev/null 2>&1; then
  echo 1
else
  echo 0
fi
