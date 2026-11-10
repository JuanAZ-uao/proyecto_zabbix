# Host monitoreado "WEB": nginx + Zabbix Agent 2 (supervisord)
FROM nginx:1.27-bookworm
COPY common/install-agent.sh /tmp/install-agent.sh
RUN sh /tmp/install-agent.sh && rm -f /tmp/install-agent.sh
COPY web/supervisord.conf /etc/supervisor/lab-supervisord.conf
COPY common/entrypoint.sh /lab-entrypoint.sh
RUN chmod +x /lab-entrypoint.sh
EXPOSE 80 10050
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD curl -fsS -o /dev/null http://127.0.0.1/ || exit 1
ENTRYPOINT ["/lab-entrypoint.sh"]
