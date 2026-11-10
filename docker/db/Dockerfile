# Host monitoreado "DB": MySQL 8.0 + Zabbix Agent 2 (supervisord)
FROM mysql:8.0-debian
COPY common/install-agent.sh /tmp/install-agent.sh
RUN sh /tmp/install-agent.sh && rm -f /tmp/install-agent.sh
COPY db/supervisord.conf /etc/supervisor/lab-supervisord.conf
COPY common/entrypoint.sh /lab-entrypoint.sh
RUN chmod +x /lab-entrypoint.sh
EXPOSE 3306 10050
HEALTHCHECK --interval=15s --timeout=5s --retries=10 --start-period=60s \
  CMD mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent || exit 1
ENTRYPOINT ["/lab-entrypoint.sh"]
