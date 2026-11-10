# Plataforma de monitoreo de infraestructura contenerizada con Zabbix 6.0 LTS

**Autores:** Juan Esteban Panesso, Samuel Rios Calderon, Sebastian Castillo — Universidad Autónoma de Occidente, Servicios Telemáticos 2026-02 · _correos_

> **Borrador para pasar a la plantilla IEEE de 2 columnas (máx. 7 páginas).** Las secciones siguen la estructura del catálogo. Los números provienen de las pruebas reales de `docs/pruebas.md`; las figuras sugeridas están en `docs/evidencias/` y el diagrama en `README.md` / `docs/arquitectura.md`. Reemplazar los autores, revisar el estilo y recortar según el espacio.

---

## Resumen
Se implementó una plataforma de monitoreo basada en Zabbix 6.0 LTS, íntegramente contenerizada con Docker Compose, que supervisa la disponibilidad, los recursos y los servicios de cuatro hosts (web, base de datos, DNS y FTP), genera alertas por correo (Mailhog) y presenta dashboards en tiempo real. La configuración completa se automatiza mediante la API de Zabbix, por lo que `docker compose up` deja el sistema operativo sin intervención manual. En las pruebas, la caída de un host se detectó en **13,3 s** en promedio y el correo llegó en **19,0 s**; las fallas de servicio se distinguieron de las de host. **Palabras clave:** Zabbix, monitoreo, Docker Compose, alertas, observabilidad.

## I. Introducción
En una infraestructura de servicios sin monitoreo centralizado, las fallas se descubren cuando el usuario ya las sufrió. **Objetivo general:** implementar una plataforma de monitoreo con Zabbix, totalmente contenerizada, que supervise disponibilidad, recursos y servicios de una red de contenedores y genere alertas. **Objetivos específicos:** (1) desplegar ≥ 4 hosts monitoreados con Zabbix Agent; (2) desplegar Zabbix Server, base de datos y frontend; (3) definir hosts, grupos, templates y triggers; (4) crear dashboards; (5) enviar alertas por correo a Mailhog; (6) validar con pruebas de falla.

## II. Contexto
El monitoreo de infraestructura mide estados (disponible/no disponible) y métricas (CPU, memoria, disco, latencia) para alertar antes de que el usuario perciba el fallo. Zabbix combina recolección por agente (pasiva/activa), chequeos sin agente (ICMP, TCP, HTTP), *templates*, *triggers* con severidades y dependencias, *acciones* y *dashboards* [1]. Las restricciones del proyecto son: todo en contenedores, nada instalado en el host, imagen del servidor personalizada y configuración montada como volúmenes.

## III. Evaluación y selección de alternativas
Se compararon cuatro alternativas con una matriz multicriterio (detalle en `docs/matriz-decision.md`): **Zabbix**, **Prometheus + Grafana + Alertmanager** [2], **Nagios Core + NRPE** [3] y **Datadog** (SaaS). Criterios y pesos: cumplimiento de requisitos (25 %), despliegue en Docker (15 %), agentes y templates (15 %), dashboards e históricos (15 %), alertas (10 %), curva de aprendizaje (10 %), recursos (5 %) y costo/licencia (5 %). Cada criterio se calificó de 1 a 5 con una escala definida; para Zabbix los recursos se midieron (`docker stats`: ≈ 350 MiB la plataforma) y el resto se basó en la documentación oficial.

| Alternativa | Puntaje (0–5) |
|---|:--:|
| **Zabbix 6.0 LTS** | **4,40** |
| Prometheus + Grafana | 3,75 |
| Datadog | 3,60 |
| Nagios Core | 2,85 |

*(Insertar la tabla completa de la matriz si el espacio lo permite.)* Zabbix ganó también en el análisis de sensibilidad (pesos iguales: 4,25 vs 3,88; priorizando visualización: 4,28 vs 4,12). Se eligió porque es la única alternativa que cubre todos los requisitos con una sola herramienta open source dentro de Compose; Datadog se descartó por ser SaaS de pago y depender de una cuenta externa, y Nagios por carecer de dashboards e históricos nativos.

## IV. Diseño de la solución
**Arquitectura** (Fig. 1 = diagrama Mermaid del README): una red Docker `lab-net` (172.28.0.0/24) con 11 servicios. *Plataforma:* `zabbix-db` (PostgreSQL 15, volumen persistente), `zabbix-server` (imagen propia con Dockerfile y configuración montada), `zabbix-web` (nginx + PHP, único puerto publicado: 8080), `zabbix-agent` (auto-monitoreo), `mailhog` (SMTP 1025, UI 8025) y `provisioner` (automatización). *Hosts monitoreados:* `lab-web` (nginx), `lab-db` (MySQL 8.0), `lab-dns` (bind9) y `lab-ftp` (vsftpd), cada uno con **Zabbix Agent 2**.

**Decisiones clave.**
1. *Agente en la misma imagen (supervisord) en lugar de sidecar:* un «host» es un contenedor; `docker stop` apaga servicio y agente (coincide con la prueba del catálogo), y el agente comparte PID, cgroup y sistema de archivos con el servicio.
2. *Métricas por contenedor desde cgroup v2:* dentro de un contenedor `/proc` refleja el kernel compartido; sin esta decisión, estresar un host elevaría la CPU de los cuatro. Se calcula CPU y memoria respecto al límite del contenedor.
3. *Dos puntos de vista:* agente (interno: procesos, `net.dns`, MySQL) y servidor (externo: ICMP, TCP, *web scenario*, *external check* de login FTP).
4. *Plantillas jerárquicas:* `Lab Base` (ICMP, recursos, disco, host caído) enlaza *Linux by Zabbix agent*; `Lab Web/DB/DNS/FTP` enlazan `Lab Base` y los templates oficiales de Nginx y MySQL.
5. *Triggers con severidades y dependencias:* Disaster (host caído), High (servicio caído, disco > 90 %), Average, Warning (CPU > 85 %, memoria > 90 %, disco > 80 %). Los de servicio dependen del de host para evitar tormentas de alertas.
6. *Automatización por API:* `provisioning/lab_config.py` describe de forma declarativa grupos, templates, items, triggers, hosts, acción de correo y dashboards; `provision.py` lo aplica de forma idempotente en ≈ 25 s.

## V. Implementación
Se fijaron versiones (Zabbix 6.0.49, PostgreSQL 15, MySQL 8.0, nginx 1.27, Mailhog v1.0.1) y se parametrizó con `.env.example`. Cada host se construye con un Dockerfile que instala el repositorio oficial de Zabbix 6.0 (Debian 12), supervisord y el servicio; la configuración (agente, nginx, bind, vsftpd, usuario `zbx_monitor` con privilegios mínimos) se monta como volúmenes de solo lectura. El *media type* SMTP apunta a `mailhog:1025` y la acción envía a `admin@lab.local` los problemas de severidad ≥ Warning y sus recuperaciones. El dashboard *Lab - Visión general* tiene tres páginas: estado, recursos en tiempo real y servicios. Los intervalos son cortos (10 s) para facilitar la detección y la demostración.

## VI. Pruebas y resultados
**Dashboard en tiempo real:** con `stress-ng` en `lab-web`, su CPU llegó a ≈ 100 % y la memoria a ≈ 92 % del límite sin afectar a los demás hosts; se dispararon *CPU alta* y *Memoria alta* y se resolvieron al terminar (Fig. 2). **Caída de host:** tabla de tiempos —

| Host | Detección | Correo | Recuperación |
|---|---:|---:|---:|
| lab-web | 13,1 s | 19,3 s | 4,0 s |
| lab-db | 14,7 s | 20,1 s | 5,3 s |
| lab-dns | 11,5 s | 17,1 s | 5,7 s |
| lab-ftp | 13,7 s | 19,4 s | 4,4 s |
| **Prom.** | **13,3 s** | **19,0 s** | **4,9 s** |

**Falla de servicio:** el proceso se detectó en 4-14 s y el puerto/servicio desde el servidor en 24-27 s, sin disparar *Host caído*. **Disco:** `/data` al 85 % generó Warning y al 96 % High. **Alertas:** correos HTML en Mailhog (Fig. 3). **Históricos:** gráficos con línea base, pico de carga y umbral (Fig. 4), útiles para análisis post-incidente, capacidad y ajuste de umbrales.

## VII. Discusión
*Problemas hallados* (detalle en `docs/problemas-encontrados.md`): (a) métricas de contenedor vs. VM (solución cgroup v2); (b) al detener un contenedor Docker elimina su nombre DNS y `fping` no resolvía el host, dejando el item ICMP *no soportado* y el trigger de host caído sin disparar → se usan **IP fijas** en las interfaces; (c) *vsftpd* fallaba con «500 OOPS» al usar `/dev/stdout` como log (abre con `O_NOFOLLOW`), problema que solo reveló el chequeo de login y no el de puerto; (d) carrera entre triggers de host y de servicio, resuelta ajustando conteos y dependencias; (e) falsos positivos en el arranque en frío.
*Limitaciones:* sin TLS entre componentes, credenciales de laboratorio, intervalos agresivos (en producción 30-60 s alargarían la detección a ≈ 1-2 min), un solo servidor Zabbix (sin alta disponibilidad), una corrida por host en las mediciones. *Trabajo futuro:* Zabbix proxy, plugin de Grafana, descubrimiento automático de contenedores con el plugin Docker de Agent 2, SLA y mapas de red.

## VIII. Conclusiones
Se logró una plataforma de monitoreo reproducible con un solo comando, que detecta la caída de un host en ≈ 13 s y notifica por correo en ≈ 19 s, distingue fallas de host y de servicio y presenta métricas por contenedor en dashboards en tiempo real. La automatización por API y la matriz de decisión sustentan la elección de Zabbix frente a Prometheus + Grafana, Nagios y Datadog. La principal lección técnica es que monitorear contenedores exige decidir qué kernel, red y reloj mide cada métrica.

## Referencias
[1] Zabbix SIA, «Zabbix 6.0 Documentation», https://www.zabbix.com/documentation/6.0/ (consultado nov. 2026).
[2] Prometheus Authors, «Prometheus Documentation», https://prometheus.io/docs/ ; Grafana Labs, «Grafana Documentation», https://grafana.com/docs/.
[3] Nagios Enterprises, «Nagios Core Documentation», https://www.nagios.org/documentation/.
[4] Docker Inc., «Docker Compose specification», https://docs.docker.com/compose/.
[5] Linux kernel, «Control Group v2», https://docs.kernel.org/admin-guide/cgroup-v2.html.
[6] M. Wright, «MailHog», https://github.com/mailhog/MailHog.
[7] Datadog, «Datadog Documentation», https://docs.datadoghq.com/.

## Figuras sugeridas
Fig. 1 Arquitectura (README) · Fig. 2 `02_dashboard_carga.png` · Fig. 3 `04c_mailhog_bandeja_con_recuperacion.png` · Fig. 4 `05_historico_cpu_lab-web.png` · opcional `03b_host_caido_problemas.png`.
