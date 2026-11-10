# Host monitoreado "FTP": vsftpd + Zabbix Agent 2 (supervisord)
FROM debian:12-slim
COPY common/install-agent.sh /tmp/install-agent.sh
RUN sh /tmp/install-agent.sh vsftpd && rm -f /tmp/install-agent.sh
COPY ftp/supervisord.conf /etc/supervisor/lab-supervisord.conf
COPY ftp/pre-start.sh /usr/local/bin/lab-pre-start.sh
COPY common/entrypoint.sh /lab-entrypoint.sh
RUN chmod +x /lab-entrypoint.sh
EXPOSE 21 30000-30009 10050
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD nc -z 127.0.0.1 21 || exit 1
ENTRYPOINT ["/lab-entrypoint.sh"]
