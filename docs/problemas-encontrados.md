# Problemas encontrados y cómo se resolvieron

Material directo para la sección *Discusión* del informe.

| # | Problema | Causa | Solución |
|---|---|---|---|
| 1 | Al estresar un contenedor subía la CPU de **todos** los hosts | Dentro de un contenedor `/proc/stat` y `/proc/meminfo` pertenecen al kernel compartido (VM de Docker), no al contenedor | Métricas propias desde **cgroup v2** (`config/agent/lab-cgroup.sh`) + límites `cpus`/`mem_limit`; el template *Linux by Zabbix agent* se mantiene para el resto |
| 2 | El disco raíz nunca llegaba al 90 % | `/` del contenedor refleja el disco de la VM (cientos de GB) | Partición `/data` tmpfs de 64 MB por host y triggers sobre `vfs.fs.size[/data,pused]` |
| 3 | `vsftpd`: *500 OOPS: failed to open vsftpd log file:/dev/stdout* → el puerto 21 abría pero el login fallaba y Zabbix marcaba FTP caído | vsftpd abre el log con `O_NOFOLLOW`; `/dev/stdout` es un enlace simbólico | `vsftpd_log_file=/var/log/vsftpd.log` + proceso `tail -F` en supervisord para ver el log en `docker logs`. Se detectó gracias al *external check* de login, que un simple `net.tcp.service` no habría revelado |
| 4b | **El trigger «Host caído» nunca disparaba al detener un contenedor** | Con interfaces por nombre DNS, al detener el contenedor Docker elimina su nombre → `fping` no puede resolverlo y el item `icmpping` queda *no soportado* (sin valor 0) | Interfaces por **IP fija** (172.28.0.10-13). Hallazgo importante: la primera prueba de caída detectó solo el servicio, no el host |
| 4 | Al detener un contenedor saltaba primero «Servicio HTTP caído» y luego «Host caído» (carrera de triggers; las dependencias no actúan si el trigger maestro aún no está en problema) | Intervalos y conteos similares (3 pings vs 2 chequeos) | «Host caído» = 2 pings (≈20 s); triggers de servicio = 3 chequeos (≈30 s) y declaran **dependencia** del host caído |
| 5 | Problemas «fantasma» al arrancar (Nginx *Failed to fetch stub status*, FTP) que se resuelven solos | Primeras evaluaciones antes de que existan datos | Normal en arranque en frío; `scripts/reset-mailhog.sh` limpia la bandeja antes de la demo. Los scripts de prueba ya la vacían al iniciar |
| 6 | Alerta permanente *MySQL: Buffer pool utilization is too low* | Con 64 MB de buffer pool y datos mínimos, < 50 % es lo normal | Macro `{$MYSQL.BUFF_UTIL.MIN.WARN}=1` en el host `lab-db` |
| 7 | Items *no soportados* en «Zabbix server» (IPMI, Java, VMware, SNMP trapper, report) | Esos pollers no se arrancan en el contenedor | El provisioner los deshabilita |
| 8 | `zabbix-web` no arrancaba: *port 8080 already allocated* | Otro proyecto usaba 8080 en el host | Puertos configurables por `.env` (`WEB_PORT`, `MAILHOG_UI_PORT`) |
| 9 | Host `Zabbix server` por defecto «no disponible» | Apunta a `127.0.0.1:10050` y el server no tiene agente propio en su contenedor | Contenedor `zabbix-agent` (oficial) y el provisioner redirige la interfaz del host |
| 10 | `fping` / ICMP | `fping` necesita `CAP_NET_RAW`; la imagen oficial lo trae con bit setuid | Sin cambios: se verificó que `icmpping` devuelve 1 desde `zabbix-server` |
| 11 | Scripts `.sh` con finales de línea CRLF fallarían en Linux | Clonado/edición en Windows | `.gitattributes` fuerza `eol=lf` en `*.sh`, `*.conf`, `Dockerfile`, etc.; los scripts se invocan con `sh` (no dependen del bit ejecutable salvo los `externalscripts`, que se marcan `chmod +x` al construir la imagen) |
| 13 | Items «no soportados» residuales: `system.sw.packages` en *Zabbix server* (Alpine no tiene dpkg/rpm) y `mysql.innodb_log_file_size` en `lab-db` | El primero no aplica a Alpine; el segundo necesita 1 h de histórico (`last(...,#1:now-1h)`) | El provisioner deshabilita el primero; el segundo se normaliza solo a la hora de arranque (es esperable en cualquier despliegue nuevo) |
| 12 | MySQL 8.0 está en fin de soporte (abril 2026) | — | Se mantiene `mysql:8.0-debian` por tener variante Debian (necesaria para el repo oficial de Zabbix Agent 2). Para producción: 8.4 LTS con agente en contenedor aparte |

## Lecciones
* Monitorear contenedores exige decidir **qué reloj/kernel** mide cada métrica: lo que reporta un agente dentro de un contenedor no siempre es «del contenedor».
* Combinar chequeos *desde el servidor* (red) y *desde el agente* (interno) permite distinguir «el host cayó» de «el servicio cayó».
* Las **dependencias de triggers** reducen la tormenta de alertas, pero hay que ajustar los tiempos para que el maestro dispare antes.
