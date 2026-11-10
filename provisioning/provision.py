# -*- coding: utf-8 -*-
"""
Automatizacion de Zabbix 6.0 por API JSON-RPC (solo libreria estandar).

Crea de forma IDEMPOTENTE:
  grupos -> templates (items, triggers, dependencias, web scenarios) -> hosts + macros
  -> media type de correo (Mailhog) -> correo del usuario Admin -> accion de alertas
  -> dashboards.

Se ejecuta solo con `docker compose up` (servicio "provisioner") y se puede repetir con
`docker compose run --rm provisioner` sin duplicar nada.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

import lab_config as cfg

URL = os.environ.get("ZBX_URL", "http://zabbix-web:8080/api_jsonrpc.php")
ADMIN_USER = os.environ.get("ZBX_ADMIN_USER", "Admin")
ADMIN_PASS = os.environ.get("ZBX_ADMIN_PASSWORD", "zabbix")
MAILHOG_API = os.environ.get("MAILHOG_API", "http://mailhog:8025")

TOKEN = None
WARNINGS = []


class ApiError(Exception):
    pass


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def rpc(method, params=None, auth=True, retries=1):
    body = {"jsonrpc": "2.0", "method": method, "params": {} if params is None else params, "id": 1}
    if auth and TOKEN:
        body["auth"] = TOKEN
    data = json.dumps(body).encode("utf-8")
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json-rpc"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                out = json.load(resp)
            if "error" in out:
                e = out["error"]
                raise ApiError("%s -> %s %s" % (method, e.get("message"), e.get("data")))
            return out["result"]
        except (urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(3)
    raise ApiError("%s -> sin conexion: %s" % (method, last))


def warn(msg):
    WARNINGS.append(msg)
    log("  [AVISO] " + msg)


# ----------------------------------------------------------------------------- espera + login
def wait_and_login():
    global TOKEN
    log("Esperando a la API de Zabbix en %s ..." % URL)
    deadline = time.time() + 600
    last_err = None
    while time.time() < deadline:
        try:
            ver = rpc("apiinfo.version", auth=False)
            TOKEN = rpc("user.login", {"username": ADMIN_USER, "password": ADMIN_PASS}, auth=False)
            log("API lista (Zabbix %s). Sesion iniciada como %s." % (ver, ADMIN_USER))
            return
        except ApiError as exc:
            last_err = exc
            time.sleep(5)
    log("ERROR: la API no estuvo disponible a tiempo: %s" % last_err)
    sys.exit(1)


# ----------------------------------------------------------------------------- utilidades
GROUP_IDS = {}
TEMPLATE_IDS = {}


def ensure_group(key):
    name = cfg.GROUPS[key]
    if key in GROUP_IDS:
        return GROUP_IDS[key]
    res = rpc("hostgroup.get", {"filter": {"name": [name]}, "output": ["groupid"]})
    if res:
        gid = res[0]["groupid"]
    else:
        gid = rpc("hostgroup.create", {"name": name})["groupids"][0]
        log("  + grupo '%s'" % name)
    GROUP_IDS[key] = gid
    return gid


def template_id(host):
    if host in TEMPLATE_IDS:
        return TEMPLATE_IDS[host]
    res = rpc("template.get", {"filter": {"host": [host]}, "output": ["templateid"]})
    if not res:
        raise ApiError("No existe el template '%s'" % host)
    TEMPLATE_IDS[host] = res[0]["templateid"]
    return TEMPLATE_IDS[host]


def macros_payload(macros):
    out = []
    for m in macros:
        macro, value = m[0], m[1]
        item = {"macro": macro, "value": value}
        if len(m) > 2 and isinstance(m[2], int):          # (macro, valor, tipo)  tipo 0/1
            item["type"] = m[2]
        elif len(m) > 2:                                   # (macro, valor, descripcion)
            item["description"] = m[2]
        out.append(item)
    return out


# ----------------------------------------------------------------------------- templates
def ensure_template(spec):
    host = spec["host"]
    gid = ensure_group(spec["group"])
    links = [{"templateid": template_id(t)} for t in spec.get("link", [])]
    existing = rpc("template.get", {"filter": {"host": [host]}, "output": ["templateid"]})
    payload = {"name": spec["name"], "description": spec.get("description", ""),
               "groups": [{"groupid": gid}], "templates": links}
    if spec.get("macros"):
        payload["macros"] = macros_payload(spec["macros"])
    if existing:
        tid = existing[0]["templateid"]
        rpc("template.update", dict(payload, templateid=tid))
        log("= template '%s' (actualizado)" % host)
    else:
        tid = rpc("template.create", dict(payload, host=host))["templateids"][0]
        log("+ template '%s'" % host)
    TEMPLATE_IDS[host] = tid

    for it in spec.get("items", []):
        upsert_item(tid, it)
    for ws in spec.get("webscenarios", []):
        upsert_webscenario(tid, ws)
    return tid


def upsert_item(tid, it):
    found = rpc("item.get", {"hostids": [tid], "filter": {"key_": it["key_"]}, "output": ["itemid"]})
    body = dict(it)
    body["hostid"] = tid
    try:
        if found:
            body.pop("key_"), body.pop("type"), body.pop("hostid")
            rpc("item.update", dict(body, itemid=found[0]["itemid"]))
        else:
            rpc("item.create", body)
            log("    + item %s" % it["key_"])
    except ApiError as exc:
        warn("item %s: %s" % (it["key_"], exc))


def upsert_webscenario(tid, ws):
    found = rpc("httptest.get", {"hostids": [tid], "filter": {"name": ws["name"]}, "output": ["httptestid"]})
    steps = [dict(s, no=i + 1) for i, s in enumerate(ws["steps"])]
    body = {"name": ws["name"], "hostid": tid, "delay": ws.get("delay", "1m"),
            "retries": ws.get("retries", 1), "steps": steps}
    try:
        if found:
            rpc("httptest.update", {"httptestid": found[0]["httptestid"], "delay": body["delay"],
                                    "retries": body["retries"], "steps": steps})
        else:
            rpc("httptest.create", body)
            log("    + web scenario '%s'" % ws["name"])
    except ApiError as exc:
        warn("web scenario %s: %s" % (ws["name"], exc))


def trigger_id_by_name(tid, name):
    res = rpc("trigger.get", {"hostids": [tid], "filter": {"description": [name]}, "output": ["triggerid"]})
    return res[0]["triggerid"] if res else None


def ensure_triggers(spec):
    tid = TEMPLATE_IDS[spec["host"]]
    base_tid = TEMPLATE_IDS["Lab Base"]
    for tr in spec.get("triggers", []):
        deps = []
        for dep in tr["deps"]:
            did = trigger_id_by_name(tid, dep) or trigger_id_by_name(base_tid, dep)
            if did:
                deps.append({"triggerid": did})
        body = {"description": tr["description"], "expression": tr["expression"], "priority": tr["priority"],
                "comments": tr["comments"], "tags": tr["tags"], "dependencies": deps, "manual_close": 1}
        try:
            existing = trigger_id_by_name(tid, tr["description"])
            if existing:
                rpc("trigger.update", dict(body, triggerid=existing))
            else:
                rpc("trigger.create", body)
                log("    + trigger [%d] %s" % (tr["priority"], tr["description"]))
        except ApiError as exc:
            warn("trigger '%s': %s" % (tr["description"], exc))


# ----------------------------------------------------------------------------- hosts
def ensure_host(spec):
    host = spec["host"]
    gids = [{"groupid": ensure_group("all")}, {"groupid": ensure_group(spec["group"])}]
    tpls = [{"templateid": template_id(t)} for t in spec["templates"]]
    # Interfaz por IP: si el contenedor se detiene Docker elimina su nombre DNS y fping no podria resolverlo
    # (el item ICMP quedaria "no soportado" en vez de devolver 0 y el trigger de host caido nunca dispararia).
    iface = {"type": 1, "main": 1, "useip": 1, "ip": spec["ip"], "dns": spec["dns"], "port": "10050"}
    tags = [{"tag": k, "value": v} for k, v in spec.get("tags", {}).items()]
    macros = macros_payload(spec.get("macros", []))
    existing = rpc("host.get", {"filter": {"host": [host]}, "output": ["hostid"],
                                "selectInterfaces": ["interfaceid", "type", "main"]})
    if existing:
        hid = existing[0]["hostid"]
        for itf in existing[0]["interfaces"]:
            if itf["type"] == "1" and itf["main"] == "1":
                rpc("hostinterface.update", dict(iface, interfaceid=itf["interfaceid"]))
        rpc("host.update", {"hostid": hid, "groups": gids, "templates": tpls, "tags": tags, "macros": macros,
                            "description": spec.get("description", "")})
        log("= host '%s' (actualizado)" % host)
    else:
        rpc("host.create", {"host": host, "name": host, "interfaces": [iface], "groups": gids, "templates": tpls,
                            "tags": tags, "macros": macros, "description": spec.get("description", "")})
        log("+ host '%s' -> %s" % (host, spec["dns"]))


def fix_zabbix_server_host():
    """El host por defecto 'Zabbix server' apuntaba a 127.0.0.1; ahora lo atiende el contenedor zabbix-agent."""
    res = rpc("host.get", {"filter": {"host": ["Zabbix server"]}, "output": ["hostid"],
                           "selectInterfaces": ["interfaceid", "type", "main"]})
    if not res:
        return
    hid = res[0]["hostid"]
    for itf in res[0]["interfaces"]:
        if itf["type"] == "1":
            rpc("hostinterface.update", {"interfaceid": itf["interfaceid"], "useip": 0, "ip": "",
                                         "dns": "zabbix-agent", "port": "10050"})
    rpc("host.update", {"hostid": hid, "groups": [{"groupid": g["groupid"]} for g in rpc(
        "hostgroup.get", {"hostids": [hid], "output": ["groupid"]})] + [{"groupid": ensure_group("all")}]})
    log("= host 'Zabbix server' apunta al contenedor zabbix-agent")

    # Los pollers IPMI/Java/SNMP-trapper/VMware/report no se arrancan en este laboratorio:
    # se deshabilitan sus items para que no aparezcan como "no soportados".
    patterns = ["ipmi", "java poller", "snmp trapper", "vmware", "report writer", "report manager"]
    items = rpc("item.get", {"hostids": [hid], "output": ["itemid", "key_"], "search": {"key_": patterns},
                             "searchByAny": True, "filter": {"status": 0}})
    items = [it for it in items if it["key_"].startswith("zabbix[")]
    # system.sw.packages no es soportado por la imagen Alpine (no hay dpkg/rpm)
    items += rpc("item.get", {"hostids": [hid], "output": ["itemid", "key_"],
                              "filter": {"key_": ["system.sw.packages"], "status": 0}})
    for it in items:
        rpc("item.update", {"itemid": it["itemid"], "status": 1})
    if items:
        log("  - %d items de pollers no usados deshabilitados en 'Zabbix server'" % len(items))


# ----------------------------------------------------------------------------- correo / acciones
SUBJ_PROBLEM = "[{EVENT.SEVERITY}] PROBLEMA: {EVENT.NAME}"
SUBJ_RECOVERY = "[RESUELTO] {EVENT.RECOVERY.NAME}"
BODY_PROBLEM = (
    "<h3 style=\"color:#c0392b;font-family:sans-serif\">PROBLEMA detectado</h3>"
    "<table cellpadding=\"4\" style=\"font-family:sans-serif;font-size:14px\">"
    "<tr><td><b>Evento</b></td><td>{EVENT.NAME}</td></tr>"
    "<tr><td><b>Host</b></td><td>{HOST.NAME} ({HOST.CONN})</td></tr>"
    "<tr><td><b>Severidad</b></td><td>{EVENT.SEVERITY}</td></tr>"
    "<tr><td><b>Inicio</b></td><td>{EVENT.DATE} {EVENT.TIME}</td></tr>"
    "<tr><td><b>Dato</b></td><td>{ITEM.NAME1}: {ITEM.VALUE1}</td></tr>"
    "<tr><td><b>ID del evento</b></td><td>{EVENT.ID}</td></tr>"
    "</table>")
BODY_RECOVERY = (
    "<h3 style=\"color:#27ae60;font-family:sans-serif\">Problema RESUELTO</h3>"
    "<table cellpadding=\"4\" style=\"font-family:sans-serif;font-size:14px\">"
    "<tr><td><b>Evento</b></td><td>{EVENT.RECOVERY.NAME}</td></tr>"
    "<tr><td><b>Host</b></td><td>{HOST.NAME} ({HOST.CONN})</td></tr>"
    "<tr><td><b>Resuelto</b></td><td>{EVENT.RECOVERY.DATE} {EVENT.RECOVERY.TIME}</td></tr>"
    "<tr><td><b>Duracion</b></td><td>{EVENT.DURATION}</td></tr>"
    "</table>")


def ensure_mediatype():
    name = "Correo (Mailhog)"
    body = {
        "name": name, "type": 0, "status": 0, "smtp_server": "mailhog", "smtp_port": "1025",
        "smtp_helo": "zabbix.lab.local", "smtp_email": "zabbix@lab.local", "smtp_security": 0,
        "smtp_verify_peer": 0, "smtp_verify_host": 0, "smtp_authentication": 0, "content_type": 1,
        "maxsessions": "1", "maxattempts": "3", "attempt_interval": "10s",
        "description": "Envia las alertas por SMTP sin autenticacion al contenedor Mailhog (mailhog:1025)",
        "message_templates": [
            {"eventsource": "0", "recovery": "0", "subject": SUBJ_PROBLEM, "message": BODY_PROBLEM},
            {"eventsource": "0", "recovery": "1", "subject": SUBJ_RECOVERY, "message": BODY_RECOVERY},
        ],
    }
    res = rpc("mediatype.get", {"filter": {"name": [name]}, "output": ["mediatypeid"]})
    if res:
        mid = res[0]["mediatypeid"]
        rpc("mediatype.update", dict(body, mediatypeid=mid))
        log("= media type '%s' (actualizado)" % name)
    else:
        mid = rpc("mediatype.create", body)["mediatypeids"][0]
        log("+ media type '%s' -> mailhog:1025" % name)
    return mid


def ensure_admin_media(mediatypeid):
    users = rpc("user.get", {"filter": {"username": [ADMIN_USER]}, "output": ["userid"]})
    uid = users[0]["userid"]
    rpc("user.update", {"userid": uid, "medias": [{
        "mediatypeid": mediatypeid, "sendto": [cfg.ALERT_EMAIL], "active": 0, "severity": 63,
        "period": "1-7,00:00-24:00"}]})
    log("= usuario %s recibe alertas en %s" % (ADMIN_USER, cfg.ALERT_EMAIL))
    return uid


def ensure_action(mediatypeid, userid):
    name = "Notificar problemas por correo (Mailhog)"
    msg = {"mediatypeid": mediatypeid, "default_msg": 1}
    body = {
        "name": name, "eventsource": 0, "status": 0, "esc_period": "1m",
        "filter": {"evaltype": 0, "conditions": [
            {"conditiontype": 4, "operator": 5, "value": "2"}]},          # severidad >= Warning
        "operations": [{"operationtype": 0, "esc_period": "0", "esc_step_from": 1, "esc_step_to": 1,
                        "evaltype": 0, "opmessage": msg, "opmessage_usr": [{"userid": userid}]}],
        "recovery_operations": [{"operationtype": 0, "opmessage": msg, "opmessage_usr": [{"userid": userid}]}],
    }
    res = rpc("action.get", {"filter": {"name": [name]}, "output": ["actionid"]})
    if res:
        body.pop("eventsource")
        rpc("action.update", dict(body, actionid=res[0]["actionid"]))
        log("= accion '%s' (actualizada)" % name)
    else:
        rpc("action.create", body)
        log("+ accion '%s' (severidad >= Warning)" % name)


# ----------------------------------------------------------------------------- dashboards
def resolve_fields(fields):
    out = []
    for f in fields:
        if f["type"] == "group":
            out.append({"type": 2, "name": f["name"], "value": ensure_group(f["value"])})
        else:
            out.append(dict(f, value=f["value"]))
    return out


def ensure_dashboard(spec, userid):
    pages = []
    for p in spec["pages"]:
        widgets = []
        for w in p["widgets"]:
            widgets.append({"type": w["type"], "name": w.get("name", ""), "x": w["x"], "y": w["y"],
                            "width": w["width"], "height": w["height"], "view_mode": 0,
                            "fields": resolve_fields(w.get("fields", []))})
        pages.append({"name": p["name"], "display_period": 30, "widgets": widgets})
    body = {"name": spec["name"], "userid": userid, "private": 0, "display_period": 30, "auto_start": 0,
            "pages": pages}
    res = rpc("dashboard.get", {"filter": {"name": [spec["name"]]}, "output": ["dashboardid"]})
    try:
        if res:
            rpc("dashboard.update", dict(body, dashboardid=res[0]["dashboardid"]))
            log("= dashboard '%s' (actualizado)" % spec["name"])
        else:
            rpc("dashboard.create", body)
            log("+ dashboard '%s'" % spec["name"])
    except ApiError as exc:
        warn("dashboard %s: %s" % (spec["name"], exc))


# ----------------------------------------------------------------------------- principal
def main():
    wait_and_login()

    log("--- Grupos")
    for key in cfg.GROUPS:
        ensure_group(key)

    log("--- Templates")
    for spec in cfg.TEMPLATES:
        ensure_template(spec)
    for spec in cfg.TEMPLATES:           # los triggers van despues: las dependencias referencian otros triggers
        ensure_triggers(spec)

    log("--- Hosts")
    for spec in cfg.HOSTS:
        ensure_host(spec)
    fix_zabbix_server_host()

    log("--- Alertas por correo")
    mid = ensure_mediatype()
    uid = ensure_admin_media(mid)
    ensure_action(mid, uid)

    log("--- Dashboards")
    for spec in cfg.DASHBOARDS:
        ensure_dashboard(spec, uid)

    hosts = rpc("host.get", {"output": ["host"], "selectTriggers": "count", "selectItems": "count",
                             "filter": {"status": 0}})
    log("--- Resumen")
    for h in sorted(hosts, key=lambda x: x["host"]):
        log("   %-14s items=%-4s triggers=%s" % (h["host"], h["items"], h["triggers"]))
    if WARNINGS:
        log("Terminado con %d aviso(s):" % len(WARNINGS))
        for w in WARNINGS:
            log("   - " + w)
    else:
        log("Provisionamiento completo SIN avisos.")
    log("Frontend: http://localhost:8080  |  Mailhog: http://localhost:8025")


if __name__ == "__main__":
    main()
