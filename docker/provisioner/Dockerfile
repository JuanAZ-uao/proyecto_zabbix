# Contenedor de automatizacion: configura Zabbix por API (hosts, templates, triggers, acciones, dashboards)
# Solo usa la libreria estandar de Python (sin pip install).
FROM python:3.12-alpine
WORKDIR /app
COPY provisioning/ /app/
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/provision.py"]
