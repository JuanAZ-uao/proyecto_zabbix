# ==========================================================================
#  Imagen Zabbix Server personalizada (requisito del catalogo)
#  Sobre la imagen oficial 6.0 LTS agrega:
#    - herramientas de diagnostico (dig, nc, curl, fping ya viene)
#    - scripts de "External check" (ftp_login.sh)
#    - Include de /etc/zabbix/zabbix_server.conf.d/ para montar configuracion
# ==========================================================================
ARG ZABBIX_VERSION=6.0.49
FROM zabbix/zabbix-server-pgsql:alpine-${ZABBIX_VERSION}

LABEL org.opencontainers.image.title="zabbix-server-lab" \
      org.opencontainers.image.description="Zabbix Server 6.0 LTS personalizado para el proyecto de monitoreo" \
      org.opencontainers.image.version="${ZABBIX_VERSION}"

USER root
RUN apk add --no-cache bind-tools busybox-extras curl \
 && mkdir -p /etc/zabbix/zabbix_server.conf.d \
 && printf '\n# --- Laboratorio: configuracion extra montada como volumen ---\nInclude=/etc/zabbix/zabbix_server.conf.d/*.conf\n' >> /etc/zabbix/zabbix_server.conf

COPY --chmod=0755 externalscripts/ /usr/lib/zabbix/externalscripts/

USER 1997
