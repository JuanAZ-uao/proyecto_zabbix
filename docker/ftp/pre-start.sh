#!/bin/sh
# Crea (o actualiza) el usuario FTP a partir de las variables FTP_USER / FTP_PASS
set -e
FTP_USER="${FTP_USER:-ftpuser}"
FTP_PASS="${FTP_PASS:-ftp_lab_pass}"
id "$FTP_USER" >/dev/null 2>&1 || useradd -m -d "/home/$FTP_USER" -s /bin/bash "$FTP_USER"
echo "$FTP_USER:$FTP_PASS" | chpasswd
mkdir -p /var/run/vsftpd/empty "/home/$FTP_USER"
touch /var/log/vsftpd.log
chown "$FTP_USER:$FTP_USER" "/home/$FTP_USER"
[ -f "/home/$FTP_USER/bienvenida.txt" ] || echo "Servidor FTP del laboratorio Zabbix" > "/home/$FTP_USER/bienvenida.txt"
