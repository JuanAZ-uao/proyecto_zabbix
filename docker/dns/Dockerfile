# Host monitoreado "DNS": bind9 + Zabbix Agent 2 (supervisord)
FROM debian:12-slim
COPY common/install-agent.sh /tmp/install-agent.sh
RUN sh /tmp/install-agent.sh bind9 bind9-dnsutils && rm -f /tmp/install-agent.sh
COPY dns/supervisord.conf /etc/supervisor/lab-supervisord.conf
COPY common/entrypoint.sh /lab-entrypoint.sh
RUN chmod +x /lab-entrypoint.sh && mkdir -p /var/cache/bind /run/named && chown bind:bind /var/cache/bind /run/named
EXPOSE 53/udp 53/tcp 10050
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD dig +short +time=2 +tries=1 @127.0.0.1 web.lab.local | grep -q . || exit 1
ENTRYPOINT ["/lab-entrypoint.sh"]
