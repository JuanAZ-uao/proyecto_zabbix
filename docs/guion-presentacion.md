# Guion de la presentación (20 min en total, incluida la sustentación)

| Min | Diapositiva / acción | Qué decir |
|---|---|---|
| 0:00-1:30 | **1. Problema y objetivos** | Fallas detectadas tarde; objetivo: plataforma Zabbix 100 % en contenedores con alertas y dashboards |
| 1:30-4:00 | **2. Alternativas y matriz de decisión** | Zabbix vs Prometheus+Grafana vs Nagios vs Datadog; criterios y pesos; puntajes 4,40 / 3,75 / 3,60 / 2,85; sensibilidad; por qué ganó Zabbix y cómo se midió cada criterio (RAM medida con `docker stats`) |
| 4:00-7:30 | **3. Arquitectura** (diagrama del README) | Red `lab-net`, 11 servicios, único puerto 8080 (+8025 Mailhog); imagen propia del server; configs montadas; agente + servicio con supervisord (vs sidecar); IPs fijas |
| 7:30-9:30 | **4. Qué se monitorea** | Inventario de hosts, templates jerárquicos, triggers y severidades, cgroup v2 por contenedor, dos puntos de vista (agente y servidor) |
| 9:30-10:30 | **5. Automatización por API** | `docker compose up` → provisioner → 25 s; idempotente; configuración como código |
| 10:30-16:00 | **6. DEMO EN VIVO** | (a) Dashboard *Recursos en tiempo real* abierto → `scripts/test-stress.sh web 120` (sube solo `lab-web`). (b) `scripts/test-host-down.sh ftp` → mostrar *Problems* y la bandeja de Mailhog; leer el tiempo de detección. (c) Historial: gráfico de CPU con el pico |
| 16:00-17:30 | **7. Resultados y problemas** | Tabla de tiempos (13,3 s / 19,0 s), caída de servicio vs host; problemas: DNS de contenedores detenidos, vsftpd `/dev/stdout`, métricas de VM vs contenedor |
| 17:30-18:30 | **8. Conclusiones y trabajo futuro** | Reproducible con un comando; limitaciones; proxy / Grafana / plugin Docker |
| 18:30-20:00 | **Preguntas** | Ver banco de preguntas abajo |

## Preparación de la demo (antes de empezar)
1. `docker compose up -d` y esperar *Provisionamiento completo SIN avisos* (`docker logs zabbix-provisioner`).
2. `scripts/reset-mailhog.sh` (bandeja vacía) y esperar ≈ 3 min para que se disipen las alertas del arranque en frío.
3. Pestañas abiertas: Dashboard página 2, *Problems*, Mailhog. Terminal con los comandos listos.
4. Plan B: capturas de `docs/evidencias/` y el video de la demo.

## Banco de preguntas probables
* **¿Por qué Zabbix y no Prometheus?** Cubre todos los requisitos con una herramienta (agentes, hosts, templates, triggers con dependencias, acciones); Prometheus es mejor en métricas cloud-native pero exige integrar ≥ 8 componentes y no tiene inventario de hosts. La matriz lo cuantifica.
* **¿Cómo medimos los criterios?** Escala 1-5 con definición; RAM de Zabbix medida con `docker stats`; el resto según documentación oficial (se declara).
* **¿Por qué no sidecar?** Un host = un contenedor; `docker stop` literal; agente ve el mismo cgroup/PID.
* **¿Por qué las métricas de CPU no salen del template Linux?** `/proc/stat` en un contenedor es de la VM completa; usamos cgroup v2.
* **¿Cómo escala?** Zabbix proxy, particionado de BD, intervalos más largos; aquí intervalos de 10 s solo por la demo.
* **¿Seguridad?** Agentes pasivos limitados a la subred, usuario MySQL con privilegios mínimos, secretos en `.env`; limitaciones: sin TLS, `Admin/zabbix`.
* **¿Qué pasa si cae el propio Zabbix?** Hoy es punto único de falla; mitigación: HA nativa de Zabbix 6.0 / monitoreo externo (trabajo futuro).
* **¿Qué cambió entre detección de servicio y de host?** Dependencias de triggers y conteos distintos (host 2 pings, servicio 3 chequeos).
