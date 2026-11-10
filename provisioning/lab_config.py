# -*- coding: utf-8 -*-
"""
Definicion declarativa de TODO lo que se configura en Zabbix:
grupos, templates (items + triggers + web scenarios), hosts, macros, dashboards.

El motor (provision.py) lee este archivo y lo aplica por la API de Zabbix de forma idempotente.
Para agregar un host o un trigger basta con editar este archivo y volver a ejecutar:
    docker compose run --rm provisioner
"""
import os

FTP_USER = os.environ.get("FTP_USER", "ftpuser")
FTP_PASS = os.environ.get("FTP_PASS", "ftp_lab_pass")
MON_USER = os.environ.get("ZBX_MONITOR_USER", "zbx_monitor")
MON_PASS = os.environ.get("ZBX_MONITOR_PASSWORD", "zbx_monitor_pass")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "admin@lab.local")

# Severidades de Zabbix
INFO, WARN, AVG, HIGH, DISASTER = 1, 2, 3, 4, 5

# Tipos de item
T_AGENT, T_SIMPLE, T_INTERNAL, T_EXTERNAL = 0, 3, 5, 10
# Tipos de dato
V_FLOAT, V_CHAR, V_LOG, V_UINT, V_TEXT = 0, 1, 2, 3, 4

GROUPS = {
    "all": "Lab - Todos los hosts",
    "web": "Lab - Servidores web",
    "db": "Lab - Bases de datos",
    "dns": "Lab - DNS",
    "ftp": "Lab - FTP",
    "tpl": "Lab - Plantillas",
}

HOST_DOWN = "Host caído: {HOST.NAME} no responde a ICMP"


def item(name, key, type=T_AGENT, vt=V_UINT, delay="15s", units="", descr="", tags=None,
         history="7d", trends="90d"):
    return {
        "name": name, "key_": key, "type": type, "value_type": vt, "delay": delay,
        "units": units, "description": descr, "history": history,
        "trends": trends if vt in (V_FLOAT, V_UINT) else "0",
        "tags": [{"tag": k, "value": v} for k, v in (tags or {}).items()],
    }


def trig(name, expr, prio, descr="", deps=None, tags=None):
    return {
        "description": name, "expression": expr, "priority": prio, "comments": descr,
        "deps": deps or [],
        "tags": [{"tag": k, "value": v} for k, v in (tags or {}).items()],
    }


TEMPLATES = [
    # ------------------------------------------------------------------ BASE
    {
        "host": "Lab Base",
        "name": "Lab Base - Contenedor Linux",
        "description": "Plantilla base de todos los hosts del laboratorio: ICMP, agente, recursos "
                       "por contenedor (cgroup v2), disco /data y triggers de host caido / CPU / RAM / disco.",
        "group": "tpl",
        "link": ["Linux by Zabbix agent"],
        "macros": [
            ("{$LAB.CPU.MAX}", "85", "Umbral de CPU (%) del contenedor"),
            ("{$LAB.MEM.MAX}", "90", "Umbral de memoria (%) del contenedor"),
            ("{$LAB.DISK.WARN}", "80", "Umbral de aviso del disco /data (%)"),
            ("{$LAB.DISK.CRIT}", "90", "Umbral critico del disco /data (%)"),
        ],
        "items": [
            item("ICMP: host responde a ping", "icmpping", T_SIMPLE, V_UINT, "10s",
                 descr="1 = responde, 0 = sin respuesta (fping desde el Zabbix Server)",
                 tags={"component": "network"}),
            item("ICMP: perdida de paquetes", "icmppingloss", T_SIMPLE, V_FLOAT, "30s", "%",
                 tags={"component": "network"}),
            item("ICMP: tiempo de respuesta", "icmppingsec", T_SIMPLE, V_FLOAT, "30s", "s",
                 tags={"component": "network"}),
            item("Contenedor: uso de CPU (% del limite)", "lab.cg[cpu_pct]", T_AGENT, V_FLOAT, "15s", "%",
                 "Leido del cgroup v2 del contenedor (no de la VM completa)", {"component": "cpu"}),
            item("Contenedor: uso de memoria (% del limite)", "lab.cg[mem_pct]", T_AGENT, V_FLOAT, "15s", "%",
                 tags={"component": "memory"}),
            item("Contenedor: memoria usada", "lab.cg[mem_used]", T_AGENT, V_UINT, "30s", "B",
                 tags={"component": "memory"}),
            item("Contenedor: limite de memoria", "lab.cg[mem_limit]", T_AGENT, V_UINT, "5m", "B",
                 tags={"component": "memory"}),
            item("Contenedor: numero de procesos", "lab.cg[pids]", T_AGENT, V_UINT, "15s", "",
                 "Tambien sirve como latido del agente (nodata)", {"component": "os"}),
            item("Disco /data: espacio usado (%)", "vfs.fs.size[/data,pused]", T_AGENT, V_FLOAT, "15s", "%",
                 "Particion tmpfs de 64 MB para simular saturacion de disco", {"component": "storage"}),
            item("Disco /data: espacio libre", "vfs.fs.size[/data,free]", T_AGENT, V_UINT, "30s", "B",
                 tags={"component": "storage"}),
        ],
        "triggers": [
            trig(HOST_DOWN, "max(/Lab Base/icmpping,#2)=0", DISASTER,
                 "El host no contesta 2 pings consecutivos (~20 s). Probable contenedor detenido.",
                 tags={"scope": "host", "type": "availability"}),
            trig("Agente Zabbix sin datos en {HOST.NAME} (60 s)", "nodata(/Lab Base/lab.cg[pids],60s)=1", AVG,
                 "El agente dejo de entregar datos.", deps=[HOST_DOWN],
                 tags={"scope": "host", "type": "availability"}),
            trig("CPU alta: {HOST.NAME} supera {$LAB.CPU.MAX}% de CPU (promedio 1 min)",
                 "avg(/Lab Base/lab.cg[cpu_pct],1m)>{$LAB.CPU.MAX}", WARN,
                 "Uso de CPU del contenedor por encima del umbral.", tags={"scope": "resource", "type": "cpu"}),
            trig("Memoria alta: {HOST.NAME} supera {$LAB.MEM.MAX}% de RAM (promedio 1 min)",
                 "avg(/Lab Base/lab.cg[mem_pct],1m)>{$LAB.MEM.MAX}", WARN,
                 "Uso de memoria del contenedor por encima del umbral.", tags={"scope": "resource", "type": "memory"}),
            trig("Disco /data casi lleno en {HOST.NAME} (>{$LAB.DISK.WARN}%)",
                 "last(/Lab Base/vfs.fs.size[/data,pused])>{$LAB.DISK.WARN} and "
                 "last(/Lab Base/vfs.fs.size[/data,pused])<={$LAB.DISK.CRIT}", WARN,
                 tags={"scope": "resource", "type": "disk"}),
            trig("Disco /data CRITICO en {HOST.NAME} (>{$LAB.DISK.CRIT}%)",
                 "last(/Lab Base/vfs.fs.size[/data,pused])>{$LAB.DISK.CRIT}", HIGH,
                 tags={"scope": "resource", "type": "disk"}),
            trig("Latencia ICMP alta en {HOST.NAME} (>150 ms durante 5 min)",
                 "avg(/Lab Base/icmppingsec,5m)>0.15", WARN, deps=[HOST_DOWN],
                 tags={"scope": "network", "type": "latency"}),
        ],
    },
    # ------------------------------------------------------------------ WEB
    {
        "host": "Lab Web",
        "name": "Lab Web - nginx",
        "description": "Servicio web: puerto HTTP, proceso nginx, escenario web y template oficial Nginx by Zabbix agent.",
        "group": "tpl",
        "link": ["Lab Base", "Nginx by Zabbix agent"],
        "items": [
            item("HTTP: puerto 80 responde (visto desde el servidor)", "net.tcp.service[http,,80]", T_SIMPLE,
                 V_UINT, "10s", tags={"service": "http"}),
            item("nginx: procesos en ejecucion", "proc.num[nginx]", T_AGENT, V_UINT, "15s",
                 tags={"service": "http"}),
        ],
        "webscenarios": [
            {"name": "Sitio web", "delay": "30s", "retries": 1,
             "steps": [{"name": "Portada", "url": "http://{HOST.CONN}/", "status_codes": "200",
                        "required": "Laboratorio Zabbix", "timeout": "10s", "follow_redirects": 1}]},
        ],
        "triggers": [
            trig("Servicio HTTP caído en {HOST.NAME}", "max(/Lab Web/net.tcp.service[http,,80],#3)=0", HIGH,
                 "El puerto 80 no responde desde el Zabbix Server.", deps=[HOST_DOWN],
                 tags={"scope": "service", "service": "http"}),
            trig("Escenario web 'Sitio web' falló en {HOST.NAME}", "last(/Lab Web/web.test.fail[Sitio web])<>0", HIGH,
                 "La portada no devolvio HTTP 200 o no contiene el texto esperado.", deps=[HOST_DOWN],
                 tags={"scope": "service", "service": "http"}),
            trig("Proceso nginx ausente en {HOST.NAME}", "last(/Lab Web/proc.num[nginx])=0", HIGH,
                 deps=[HOST_DOWN], tags={"scope": "service", "service": "http"}),
        ],
    },
    # ------------------------------------------------------------------ DB
    {
        "host": "Lab DB",
        "name": "Lab DB - MySQL",
        "description": "Base de datos: puerto 3306, proceso mysqld y template oficial MySQL by Zabbix agent 2.",
        "group": "tpl",
        "link": ["Lab Base", "MySQL by Zabbix agent 2"],
        "items": [
            item("MySQL: puerto 3306 responde (visto desde el servidor)", "net.tcp.service[tcp,,3306]", T_SIMPLE,
                 V_UINT, "10s", tags={"service": "mysql"}),
            item("mysqld: procesos en ejecucion", "proc.num[mysqld]", T_AGENT, V_UINT, "15s",
                 tags={"service": "mysql"}),
        ],
        "triggers": [
            trig("MySQL no acepta conexiones (TCP 3306) en {HOST.NAME}",
                 "max(/Lab DB/net.tcp.service[tcp,,3306],#3)=0", HIGH, deps=[HOST_DOWN],
                 tags={"scope": "service", "service": "mysql"}),
            trig("Proceso mysqld ausente en {HOST.NAME}", "last(/Lab DB/proc.num[mysqld])=0", HIGH,
                 deps=[HOST_DOWN], tags={"scope": "service", "service": "mysql"}),
        ],
    },
    # ------------------------------------------------------------------ DNS
    {
        "host": "Lab DNS",
        "name": "Lab DNS - bind9",
        "description": "DNS autoritativo de lab.local: resolucion (net.dns), respuesta correcta y proceso named.",
        "group": "tpl",
        "link": ["Lab Base"],
        "items": [
            item("DNS: resuelve web.lab.local (1 = OK)", "net.dns[127.0.0.1,web.lab.local,A,2,1]", T_AGENT,
                 V_UINT, "10s", descr="net.dns contra el propio bind9", tags={"service": "dns"}),
            item("DNS: respuesta del registro A de web.lab.local", "net.dns.record[127.0.0.1,web.lab.local,A,2,1]",
                 T_AGENT, V_TEXT, "30s", tags={"service": "dns"}),
            item("named: procesos en ejecucion", "proc.num[named]", T_AGENT, V_UINT, "15s",
                 tags={"service": "dns"}),
            item("DNS: escuchando en UDP 53", "net.udp.listen[53]", T_AGENT, V_UINT, "30s",
                 tags={"service": "dns"}),
        ],
        "triggers": [
            trig("DNS no resuelve web.lab.local en {HOST.NAME}",
                 "max(/Lab DNS/net.dns[127.0.0.1,web.lab.local,A,2,1],#3)=0", HIGH, deps=[HOST_DOWN],
                 tags={"scope": "service", "service": "dns"}),
            trig("Proceso named ausente en {HOST.NAME}", "last(/Lab DNS/proc.num[named])=0", HIGH,
                 deps=[HOST_DOWN], tags={"scope": "service", "service": "dns"}),
            trig("DNS devuelve una IP inesperada para web.lab.local en {HOST.NAME}",
                 'find(/Lab DNS/net.dns.record[127.0.0.1,web.lab.local,A,2,1],#1,"like","172.28.0.10")=0', AVG,
                 "La zona lab.local fue alterada o esta corrupta.", deps=[HOST_DOWN],
                 tags={"scope": "service", "service": "dns"}),
        ],
    },
    # ------------------------------------------------------------------ FTP
    {
        "host": "Lab FTP",
        "name": "Lab FTP - vsftpd",
        "description": "FTP: puerto 21 (net.tcp.service), login real por External check y proceso vsftpd.",
        "group": "tpl",
        "link": ["Lab Base"],
        "macros": [
            ("{$FTP.USER}", FTP_USER, "Usuario FTP de prueba"),
            ("{$FTP.PASSWORD}", FTP_PASS, "Clave FTP de prueba"),
        ],
        "items": [
            item("FTP: puerto 21 responde (visto desde el servidor)", "net.tcp.service[ftp,,21]", T_SIMPLE,
                 V_UINT, "10s", tags={"service": "ftp"}),
            item("FTP: login y listado correctos (1 = OK)", "ftp_login.sh[{HOST.CONN},{$FTP.USER},{$FTP.PASSWORD}]",
                 T_EXTERNAL, V_UINT, "30s", descr="External check: curl ftp:// con usuario y clave",
                 tags={"service": "ftp"}),
            item("vsftpd: procesos en ejecucion", "proc.num[vsftpd]", T_AGENT, V_UINT, "15s",
                 tags={"service": "ftp"}),
        ],
        "triggers": [
            trig("Servicio FTP caído (TCP 21) en {HOST.NAME}", "max(/Lab FTP/net.tcp.service[ftp,,21],#3)=0", HIGH,
                 deps=[HOST_DOWN], tags={"scope": "service", "service": "ftp"}),
            trig("Login FTP falla en {HOST.NAME}",
                 "max(/Lab FTP/ftp_login.sh[{HOST.CONN},{$FTP.USER},{$FTP.PASSWORD}],#2)=0", AVG,
                 "El puerto responde pero no se puede autenticar/listar.", deps=[HOST_DOWN],
                 tags={"scope": "service", "service": "ftp"}),
            trig("Proceso vsftpd ausente en {HOST.NAME}", "last(/Lab FTP/proc.num[vsftpd])=0", HIGH,
                 deps=[HOST_DOWN], tags={"scope": "service", "service": "ftp"}),
        ],
    },
]

# --------------------------------------------------------------------------- HOSTS
HOSTS = [
    {"host": "lab-web", "dns": "lab-web", "ip": "172.28.0.10", "group": "web", "templates": ["Lab Web"],
     "description": "Servidor web nginx 1.27 + Zabbix Agent 2 (172.28.0.10)",
     "tags": {"rol": "web", "entorno": "laboratorio"}, "macros": []},
    {"host": "lab-db", "dns": "lab-db", "ip": "172.28.0.11", "group": "db", "templates": ["Lab DB"],
     "description": "Base de datos MySQL 8.0 + Zabbix Agent 2 (172.28.0.11)",
     "tags": {"rol": "db", "entorno": "laboratorio"},
     "macros": [("{$MYSQL.DSN}", "tcp://127.0.0.1:3306", 0), ("{$MYSQL.USER}", MON_USER, 0),
                ("{$MYSQL.PASSWORD}", MON_PASS, 1),
                # Con 64 MB de buffer pool y datos de ejemplo minimos, "utilizacion < 50 %" es normal:
                # se baja el umbral para no generar un falso positivo permanente.
                ("{$MYSQL.BUFF_UTIL.MIN.WARN}", "1", 0)]},
    {"host": "lab-dns", "dns": "lab-dns", "ip": "172.28.0.12", "group": "dns", "templates": ["Lab DNS"],
     "description": "DNS bind9 (zona lab.local) + Zabbix Agent 2 (172.28.0.12)",
     "tags": {"rol": "dns", "entorno": "laboratorio"}, "macros": []},
    {"host": "lab-ftp", "dns": "lab-ftp", "ip": "172.28.0.13", "group": "ftp", "templates": ["Lab FTP"],
     "description": "FTP vsftpd + Zabbix Agent 2 (172.28.0.13)",
     "tags": {"rol": "ftp", "entorno": "laboratorio"}, "macros": []},
]

# --------------------------------------------------------------------------- DASHBOARDS
HOST_COLORS = [("lab-web", "1976D2"), ("lab-db", "F57C00"), ("lab-dns", "388E3C"), ("lab-ftp", "8E24AA")]


def graph(title, item_pattern, x, y, w, h, hosts=HOST_COLORS, left_min=None, left_max=None, unit_hint=None):
    """Widget 'Grafico' (svggraph) con una serie por host."""
    fields = []
    for i, (host, color) in enumerate(hosts):
        fields += [
            {"type": 1, "name": "ds.hosts.%d.0" % i, "value": host},
            {"type": 1, "name": "ds.items.%d.0" % i, "value": item_pattern},
            {"type": 1, "name": "ds.color.%d" % i, "value": color},
            {"type": 0, "name": "ds.fill.%d" % i, "value": 0},      # solo linea, sin relleno
            {"type": 0, "name": "ds.width.%d" % i, "value": 2},
        ]
    # Ventana de tiempo propia del grafico: ultimos 15 minutos (se ve el cambio en tiempo real)
    fields += [
        {"type": 0, "name": "graph_time", "value": 1},
        {"type": 1, "name": "time_period.from", "value": "now-15m"},
        {"type": 1, "name": "time_period.to", "value": "now"},
        {"type": 0, "name": "legend_columns", "value": 2},
    ]
    if left_min is not None:
        fields.append({"type": 0, "name": "lefty_min", "value": left_min})
    if left_max is not None:
        fields.append({"type": 0, "name": "lefty_max", "value": left_max})
    return {"type": "svggraph", "name": title, "x": x, "y": y, "width": w, "height": h, "fields": fields}


DASHBOARDS = [
    {
        "name": "Lab - Visión general",
        "pages": [
            {
                "name": "Estado",
                "widgets": [
                    {"type": "hostavail", "name": "Disponibilidad de hosts", "x": 0, "y": 0, "width": 8, "height": 4,
                     "fields": [{"type": "group", "name": "groupids.0", "value": "all"}]},
                    {"type": "problemsbysv", "name": "Problemas por severidad", "x": 8, "y": 0, "width": 8, "height": 4,
                     "fields": [{"type": "group", "name": "groupids.0", "value": "all"}]},
                    {"type": "systeminfo", "name": "Información del sistema", "x": 16, "y": 0, "width": 8, "height": 4,
                     "fields": []},
                    {"type": "problems", "name": "Problemas activos", "x": 0, "y": 4, "width": 24, "height": 6,
                     "fields": [{"type": 0, "name": "show_lines", "value": 15}]},
                    {"type": "trigover", "name": "Servicios y triggers por host", "x": 0, "y": 10, "width": 24,
                     "height": 6, "fields": [{"type": "group", "name": "groupids.0", "value": "all"}]},
                ],
            },
            {
                "name": "Recursos en tiempo real",
                "widgets": [
                    graph("CPU del contenedor (%)", "Contenedor: uso de CPU*", 0, 0, 12, 6, left_min=0, left_max=100),
                    graph("Memoria del contenedor (%)", "Contenedor: uso de memoria (%*", 12, 0, 12, 6,
                          left_min=0, left_max=100),
                    graph("Disco /data usado (%)", "Disco /data: espacio usado*", 0, 6, 12, 6, left_min=0, left_max=100),
                    graph("Tiempo de respuesta ICMP (s)", "ICMP: tiempo de respuesta", 12, 6, 12, 6),
                ],
            },
            {
                "name": "Servicios",
                "widgets": [
                    graph("HTTP (lab-web) - 1 = OK", "HTTP: puerto 80*", 0, 0, 8, 5, [("lab-web", "1976D2")],
                          left_min=0, left_max=1),
                    graph("MySQL (lab-db) - 1 = OK", "MySQL: puerto 3306*", 8, 0, 8, 5, [("lab-db", "F57C00")],
                          left_min=0, left_max=1),
                    graph("DNS (lab-dns) - 1 = OK", "DNS: resuelve*", 16, 0, 8, 5, [("lab-dns", "388E3C")],
                          left_min=0, left_max=1),
                    graph("FTP (lab-ftp) - 1 = OK", "FTP: puerto 21*", 0, 5, 8, 5, [("lab-ftp", "8E24AA")],
                          left_min=0, left_max=1),
                    graph("Login FTP (lab-ftp) - 1 = OK", "FTP: login*", 8, 5, 8, 5, [("lab-ftp", "8E24AA")],
                          left_min=0, left_max=1),
                    {"type": "web", "name": "Escenarios web", "x": 16, "y": 5, "width": 8, "height": 5,
                     "fields": [{"type": "group", "name": "groupids.0", "value": "all"}]},
                ],
            },
        ],
    },
]
