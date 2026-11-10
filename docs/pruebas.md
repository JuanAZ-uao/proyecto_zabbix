# Pruebas y resultados

Entorno de medición: Docker Desktop (WSL2, 4 vCPU, 7,7 GB RAM), Zabbix 6.0.49, 10-nov-2026.
Todas las pruebas se ejecutan con los scripts de `scripts/` (solo requieren Docker). Las capturas están en [`docs/evidencias/`](evidencias/).

## P1 — Dashboard en tiempo real (CPU, memoria, disco, servicios)

`scripts/test-stress.sh web 180` ejecuta `stress-ng --cpu 2 --vm 1 --vm-bytes 100M` dentro de `lab-web` (límites del contenedor: 1 CPU, 128 MB).

| Observación | Resultado |
|---|---|
| CPU de `lab-web` (cgroup) | **≈ 100 %** del límite durante la carga; el resto de hosts permanece < 5 % |
| Memoria de `lab-web` | **≈ 92 %** del límite |
| Triggers | *CPU alta* (>85 %, Warning) y *Memoria alta* (>90 %, Warning) activos tras ≈ 1 min de carga sostenida (promedio de 1 min) y resueltos solos al terminar |
| Correos | Un correo de problema por trigger y otro de recuperación |

Evidencia: `02_dashboard_carga.png` (dashboard, página *Recursos en tiempo real*), `02b_problemas_carga.png`, `05_historico_cpu_lab-web.png` (histórico con la línea del umbral 85 %).

## P2 — Caída de host y tiempo de detección

`scripts/test-host-down.sh <host>` hace `docker stop`, toma T0 de `docker inspect … FinishedAt` (mismo reloj que Zabbix y Mailhog) y mide hasta el evento *Host caído* y hasta el correo. Después hace `docker start` y mide la recuperación.

| Host detenido | Evento «Host caído» (Disaster) | Correo en Mailhog | Recuperación (evento) | Correo de recuperación |
|---|---:|---:|---:|---:|
| lab-web | 13,1 s | 19,3 s | 4,0 s | 8,3 s |
| lab-db | 14,7 s | 20,1 s | 5,3 s | 11,9 s |
| lab-dns | 11,5 s | 17,1 s | 5,7 s | 9,4 s |
| lab-ftp | 13,7 s | 19,4 s | 4,4 s | 11,2 s |
| **Promedio** | **13,3 s** | **19,0 s** | **4,9 s** | **10,2 s** |

*Una corrida por host (n = 1 cada uno); la resolución de los eventos de Zabbix es de 1 s.*

**Análisis.** El detector (2 pings fallidos con intervalo de 10 s) dispara entre 10 y 20 s después de la caída; el correo llega ≈ 5-6 s después del evento (cola de alertas + SMTP). Con intervalos de 60 s, típicos en producción, la detección sería de ≈ 2 min: el compromiso es **velocidad de detección vs. carga de polling**.

Evidencia: `03_host_caido_hosts.png`, `03b_host_caido_problemas.png`, `04c_mailhog_bandeja_con_recuperacion.png`, `04d_mailhog_correo_recuperacion.png`.

## P3 — Alerta en Mailhog

Cada prueba anterior termina en correos visibles en <http://localhost:8025>: asunto `[Severidad] PROBLEMA: <evento>` y `[RESUELTO] <evento>`, remitente `zabbix@lab.local`, destinatario `admin@lab.local`, cuerpo HTML con host, severidad, hora, dato y duración.

## P4 — Caída de servicio (el host sigue vivo)

`scripts/test-service-down.sh <web|db|dns|ftp>` detiene solo el proceso con `supervisorctl stop`.

| Servicio | Trigger de proceso (agente) | Trigger de servicio (visto desde el servidor) | Correo del primer evento |
|---|---:|---:|---:|
| FTP (vsftpd) | 8,0 s | 24,0 s | 10,9 s |
| DNS (named) | 4,0 s | 25,0 s | 8,1 s |
| Web (nginx) | 10,0 s | 27,0 s | 14,3 s |
| DB (mysqld) | 14,0 s | 26,0 s | 17,7 s |

No se dispara «Host caído» (el contenedor responde a ICMP), lo que permite **distinguir fallo de host de fallo de servicio**. El chequeo desde el agente (proceso) detecta primero; el del servidor (puerto/banner, 3 chequeos × 10 s) confirma desde la perspectiva del cliente. Todas las alertas se resuelven al reiniciar el servicio (1-12 s).

## P5 — Umbral de disco

`scripts/test-disk-fill.sh web`: `/data` (tmpfs 64 MB) al 85 % → *Disco /data casi lleno* (**Warning**); al 96 % → *Disco /data CRITICO* (**High**) y se resuelve el Warning. Correos recibidos: Warning, High y resolución del Warning. Evidencia: `08_disco_lleno_problemas.png`.

## P6 — Métricas históricas y su utilidad

En los items propios del laboratorio Zabbix guarda cada valor 7 días (*history*) y agregados por hora 90 días (*trends*) (los templates oficiales usan sus propios valores, p. ej. 31 d / 365 d). En *Monitoring → Latest data → Graph* (ver `05_historico_cpu_lab-web.png`) se distinguen la línea base (≈ 0,4 % de CPU), el pico de la prueba de carga (≈ 100 % durante 3 min) y el umbral del trigger. Sirven para:

1. **Análisis post-incidente:** cuándo empezó el problema y qué métrica cambió primero.
2. **Planificación de capacidad:** tendencia de uso de memoria/disco para anticipar saturación.
3. **Ajuste de umbrales:** línea base real para evitar falsos positivos (p. ej. el buffer pool de MySQL).
4. **SLA:** disponibilidad calculada a partir de los eventos de host caído.

## Reproducibilidad

* `docker compose down -v && docker compose up -d --build` desde cero deja el sistema operativo sin intervención manual; el contenedor `provisioner` termina con «Provisionamiento completo SIN avisos».
* Se verificó que `docker compose run --rm provisioner` es **idempotente** (segunda ejecución solo muestra `=` actualizado, sin duplicados).
* **Clon limpio:** se clonó el repositorio en otra carpeta (sin `.env` ni volúmenes), `docker compose up -d --build` dejó todo operativo en ≈ 1 min 5 s (con imágenes base en caché; el primer arranque en frío tarda más por las descargas) y el provisioner terminó sin avisos. La prueba de caída de host repetida desde el clon dio **14,1 s** (evento) y **20,3 s** (correo), consistente con la tabla de P2.
