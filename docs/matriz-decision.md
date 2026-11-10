# Evaluación y selección de alternativas

Problema: una infraestructura de servicios (web, base de datos, DNS, FTP) sin monitoreo centralizado detecta las fallas tarde, cuando el usuario ya las sufrió.
Restricciones del catálogo: **todo en Docker Compose, nada instalado en el host**, ≥ 4 hosts monitoreados, dashboards, alertas por correo (Mailhog), servicios HTTP/MySQL/ping.

## 1. Alternativas evaluadas

| | Alternativa | Arquitectura en Docker Compose |
|---|---|---|
| **A** | **Zabbix 6.0 LTS** | server + PostgreSQL + frontend + Agent 2 en cada host. Alertas por *media type* de correo |
| **B** | **Prometheus + Grafana + Alertmanager** | Prometheus (pull) + node_exporter, mysqld_exporter, blackbox_exporter y exporter FTP + Grafana + Alertmanager (≥ 8 contenedores) |
| **C** | **Nagios Core + NRPE + PNP4Nagios** | Nagios Core + NRPE en cada host + plugins; gráficos con PNP4Nagios/Grafana |
| **D** | **Datadog** (SaaS) | Agente Datadog en cada host; servidor, dashboards y alertas en la nube (requiere cuenta y API key) |

## 2. Criterios, pesos y cómo se mide cada uno

Escala **1–5** (1 = no cumple / muy deficiente · 3 = cumple con esfuerzo · 5 = cumple de forma nativa y completa).

| # | Criterio | Peso | Cómo se mide (evidencia) |
|---|---|---|---|
| C1 | Cumplimiento de los requisitos del catálogo | 25 % | Se desglosan los 14 requisitos del Proyecto 7 (4 hosts, agente, servidor+BD+frontend, hosts/grupos/templates, triggers, dashboards, correo a Mailhog, HTTP/MySQL/ping, imagen propia, config montada, README) y se cuenta cuáles se logran **con una sola herramienta, sin servicios externos y dentro de Compose** |
| C2 | Facilidad de despliegue en Docker | 15 % | Nº de contenedores/archivos a integrar, disponibilidad de imágenes **oficiales**, y si el arranque es reproducible con `docker compose up` |
| C3 | Agentes, templates y autodescubrimiento | 15 % | Existencia de agente propio, plantillas oficiales listas para Linux/Nginx/MySQL/DNS/FTP/ICMP y creación de hosts por API |
| C4 | Dashboards e históricos nativos | 15 % | ¿Gráficos históricos, dashboards editables y retención sin componentes extra? |
| C5 | Alertas y notificaciones | 10 % | Triggers con severidades, dependencias, recuperación, escalado y envío SMTP nativo |
| C6 | Curva de aprendizaje y documentación | 10 % | Nº de lenguajes/formatos a dominar (PromQL, YAML, config de texto…), calidad de la documentación oficial |
| C7 | Consumo de recursos | 5 % | RAM del stack en reposo (**medida** para Zabbix; para las demás, valores de referencia de la documentación oficial) |
| C8 | Costo / licencia | 5 % | Licencia open source vs. suscripción de pago |

### Evidencia medida para Zabbix (stack en reposo, `docker stats`)

| Contenedor | RAM |
|---|---|
| zabbix-db (PostgreSQL) | ≈ 163 MiB |
| zabbix-server | ≈ 54 MiB |
| zabbix-web | ≈ 118 MiB |
| zabbix-agent + mailhog | ≈ 13 MiB |
| **Plataforma** | **≈ 350 MiB** |
| 4 hosts monitoreados (nginx, MySQL, bind9, vsftpd con su agente) | ≈ 280 MiB |

Tiempos de primer arranque medidos: construcción de las imágenes de los hosts (descarga de paquetes, depende de la red; unos minutos), creación del esquema de la BD de Zabbix ≈ 1,5 min y **provisionamiento por API ≈ 25 s**.

## 3. Matriz de decisión

| Criterio (peso) | **Zabbix** | Prometheus + Grafana | Nagios Core | Datadog |
|---|:--:|:--:|:--:|:--:|
| C1 Requisitos del catálogo (25 %) | **5** | 4 | 3 | 2 |
| C2 Despliegue en Docker (15 %) | **4** | 3 | 2 | 3 |
| C3 Agentes y templates (15 %) | **5** | 3 | 3 | 5 |
| C4 Dashboards e históricos (15 %) | **4** | 5 | 2 | 5 |
| C5 Alertas (10 %) | **5** | 4 | 4 | 5 |
| C6 Curva de aprendizaje (10 %) | **3** | 2 | 2 | 4 |
| C7 Recursos (5 %) | **3** | 5 | 4 | 4 |
| C8 Costo / licencia (5 %) | **5** | 5 | 5 | 1 |
| **Puntaje ponderado (sobre 5)** | **4,40** | 3,75 | 2,85 | 3,60 |

Fórmula: `Puntaje = Σ (peso_i × calificación_i)`, con pesos en fracción (p. ej. Zabbix: 0,25·5 + 0,15·4 + 0,15·5 + 0,15·4 + 0,10·5 + 0,10·3 + 0,05·3 + 0,05·5 = **4,40**).

### Justificación de las calificaciones

**C1 — Requisitos.** Zabbix cubre los 14 requisitos con una sola herramienta (5). Prometheus+Grafana los cubre todos, pero la gestión de hosts, el estado «host caído» y el inventario se resuelven con archivos YAML y reglas manuales, sin una entidad *host/template* equivalente (4). Nagios no trae dashboards ni históricos nativos (3). Datadog incumple la restricción «sin dependencias externas / todo en Compose»: solo el agente corre local y exige cuenta y API key (2).
**C2 — Despliegue.** Zabbix: imágenes oficiales versionadas (server, web, agent2) + PostgreSQL; 4 servicios de plataforma (4). Prometheus: ≥ 8 contenedores (Prometheus, Alertmanager, Grafana, 3-4 exporters) con configuración enlazada a mano (3). Nagios: no hay imagen oficial mantenida; se usan imágenes de comunidad (2). Datadog: un contenedor de agente, pero depende de credenciales y de Internet (3).
**C3 — Agentes/templates.** Zabbix: Agent 2 oficial con plugins (MySQL, etc.) y cientos de templates oficiales (*Linux*, *Nginx*, *MySQL*, *ICMP*…) (5). Prometheus: un exporter por servicio y dashboards de comunidad, no hay plantillas oficiales integradas (3). Nagios: gran biblioteca de plugins, pero la asociación host↔servicio es manual (3). Datadog: integraciones listas (5).
**C4 — Dashboards/históricos.** Grafana es el referente visual (5); Datadog también (5). Zabbix los trae integrados y editables, aunque con estética más sobria (4). Nagios Core solo muestra estado; históricos requieren PNP4Nagios (2).
**C5 — Alertas.** Zabbix: severidades, dependencias, acciones con escalado, recuperación y SMTP nativo (5). Prometheus: Alertmanager potente (agrupación, silencios) pero aparte (4). Nagios: notificaciones maduras pero configuración de texto (4). Datadog: monitores y notificaciones completas (5).
**C6 — Aprendizaje.** Zabbix: frontend guiado + API, curva media (3). Prometheus: PromQL + YAML + varios componentes (2). Nagios: archivos de configuración de texto propensos a errores (2). Datadog: interfaz guiada (4).
**C7 — Recursos.** Zabbix (≈ 350 MiB de plataforma medidos) usa BD relacional y varios procesos (3). Prometheus y Nagios son más ligeros (5 y 4); el agente Datadog es ligero (4). *Estas tres calificaciones provienen de la documentación oficial y de valores de referencia, no de una medición propia; el equipo puede validarlas desplegando cada alternativa y comparando `docker stats`.*
**C8 — Costo.** Zabbix 6.0 (GPL), Prometheus (Apache-2.0), Grafana (AGPL) y Nagios Core (GPL) son gratuitos (5). Datadog es de pago por host tras la prueba (1).

## 4. Análisis de sensibilidad

¿La decisión cambia si cambian los pesos?

| Escenario | Zabbix | Prometheus + Grafana | Nagios | Datadog |
|---|:--:|:--:|:--:|:--:|
| Pesos del informe (tabla anterior) | **4,40** | 3,75 | 2,85 | 3,60 |
| Pesos iguales (12,5 % cada criterio) | **4,25** | 3,88 | 3,12 | 3,62 |
| Prioriza visualización (C4 = 40 %, resto proporcional) | **4,28** | 4,12 | 2,60 | 4,01 |
| Prioriza facilidad de operación (C2 + C6 = 50 %) | **4,13** | 3,37 | 2,57 | 3,53 |

Zabbix queda primero en los cuatro escenarios. Solo si «dashboards» (C4) recibiera un peso de ≈ 50 % o más, Prometheus + Grafana igualaría/superaría a Zabbix (4,26 vs 4,24 con C4 = 50 %), lo cual no corresponde a los requisitos del catálogo (que piden además agentes, triggers, hosts, templates y alertas).

## 5. Decisión

**Se selecciona Zabbix 6.0 LTS.** Razones: (1) es la única alternativa que cubre *todos* los requisitos del catálogo con una sola herramienta open source, dentro de Compose y sin dependencias externas; (2) trae agentes, templates, triggers con dependencias, acciones y dashboards nativos, lo que reduce las piezas a integrar y el riesgo de fallo en la sustentación; (3) su API permitió automatizar toda la configuración (`provisioning/`), de modo que otra persona reproduce el sistema con `docker compose up`.

**Compromisos asumidos:** mayor consumo de RAM que Prometheus, gráficos más sobrios que Grafana y curva de aprendizaje media. Como mejora futura, Grafana puede consumir los datos de Zabbix mediante su plugin oficial.

**Descartes:** Datadog por ser SaaS de pago y depender de una cuenta externa; Nagios por falta de dashboards/históricos nativos y configuración manual; Prometheus + Grafana queda como la alternativa técnica más cercana (mejor para métricas de contenedores y Kubernetes, menos para inventario de hosts y estado de disponibilidad).
