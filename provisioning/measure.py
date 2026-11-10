# -*- coding: utf-8 -*-
"""
Mide el TIEMPO DE DETECCION: desde el instante de la falla (T0) hasta que
  (a) Zabbix genera el problema y (b) llega el correo a Mailhog.

Uso (lo invocan los scripts de /scripts):
    python measure.py --host lab-web --since 2026-11-10T09:08:33.456Z [--wait 240] [--recovery]

T0 se toma de `docker inspect -f '{{.State.FinishedAt}}'` (o StartedAt para recuperacion), que usa el
mismo reloj que Zabbix y Mailhog (todos corren en el mismo kernel/VM de Docker).
"""
import argparse
import email.header
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

URL = os.environ.get("ZBX_URL", "http://zabbix-web:8080/api_jsonrpc.php")
MAILHOG = os.environ.get("MAILHOG_API", "http://mailhog:8025")
USER = os.environ.get("ZBX_ADMIN_USER", "Admin")
PASS = os.environ.get("ZBX_ADMIN_PASSWORD", "zabbix")


def parse_ts(s):
    s = s.strip().replace("Z", "+00:00")
    if "." in s:                                   # recorta nanosegundos -> microsegundos
        head, rest = s.split(".", 1)
        frac = ""
        tz = ""
        for i, ch in enumerate(rest):
            if not ch.isdigit():
                frac, tz = rest[:i], rest[i:]
                break
        else:
            frac = rest
        s = "%s.%s%s" % (head, frac[:6].ljust(6, "0"), tz)
    return datetime.fromisoformat(s).astimezone(timezone.utc).timestamp()


def rpc(method, params, token=None):
    body = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    if token:
        body["auth"] = token
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json-rpc"})
    out = json.load(urllib.request.urlopen(req, timeout=30))
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]


def mails():
    with urllib.request.urlopen(MAILHOG + "/api/v2/messages?limit=200", timeout=15) as r:
        data = json.load(r)
    res = []
    for m in data.get("items", []):
        raw = (m["Content"]["Headers"].get("Subject") or [""])[0]
        subj = "".join(t.decode(c or "utf-8") if isinstance(t, bytes) else t
                       for t, c in email.header.decode_header(raw))
        res.append((parse_ts(m["Created"]), subj))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--since", required=True, help="T0 en ISO-8601 UTC")
    ap.add_argument("--wait", type=int, default=240)
    ap.add_argument("--expect", default="", help="texto que debe aparecer en el evento Y en el correo antes de terminar")
    ap.add_argument("--recovery", action="store_true", help="medir la RECUPERACION en lugar del problema")
    a = ap.parse_args()

    t0 = parse_ts(a.since)
    token = rpc("user.login", {"username": USER, "password": PASS})
    hid = rpc("host.get", {"filter": {"host": [a.host]}, "output": ["hostid"]}, token)[0]["hostid"]
    print("Host %s | T0 = %s UTC" % (a.host, datetime.fromtimestamp(t0, timezone.utc).strftime("%H:%M:%S.%f")[:-3]))
    print("Esperando eventos (maximo %d s)..." % a.wait)

    seen = {}
    mailseen = {}
    deadline = time.time() + a.wait
    quiet_since = None
    while time.time() < deadline:
        evs = rpc("event.get", {"hostids": [hid], "time_from": int(t0) - 2, "output": ["eventid", "name", "clock",
                                  "severity", "value", "r_eventid"], "source": 0, "object": 0,
                                  "sortfield": "eventid", "select_acknowledges": "count"}, token)
        for e in evs:
            kind = "RESUELTO" if e["value"] == "0" else "PROBLEMA"
            if (a.recovery and kind == "RESUELTO") or (not a.recovery and kind == "PROBLEMA"):
                seen.setdefault(e["eventid"], (int(e["clock"]), kind, int(e["severity"]), e["name"]))
        for ts, subj in mails():
            if ts >= t0:
                mailseen.setdefault((ts, subj), True)
        ev_ok = any(a.expect in v[3] for v in seen.values()) if a.expect else bool(seen)
        ml_ok = any(a.expect in s for _, s in mailseen) if a.expect else bool(mailseen)
        if ev_ok and ml_ok and quiet_since is None:
            quiet_since = time.time()
        if quiet_since and time.time() - quiet_since > 6:      # margen para eventos hermanos
            break
        time.sleep(2)

    sev = {1: "Info", 2: "Warning", 3: "Average", 4: "High", 5: "Disaster"}
    print("\n%-9s %-9s %8s  %s" % ("Severidad", "Tipo", "Delta(s)", "Evento en Zabbix"))
    first = None
    for clock, kind, sv, name in sorted(seen.values()):
        d = clock - t0
        first = d if first is None else first
        print("%-9s %-9s %8.1f  %s" % (sev.get(sv, sv), kind, d, name))
    print("\n%-8s  %s" % ("Delta(s)", "Correo recibido en Mailhog (asunto)"))
    firstmail = None
    for ts, subj in sorted(mailseen):
        firstmail = (ts - t0) if firstmail is None else firstmail
        print("%8.1f  %s" % (ts - t0, subj))
    print("\n=== RESULTADO ===")
    if first is None:
        print("No se detecto ningun evento en %d s." % a.wait)
    else:
        print("Tiempo hasta el primer evento en Zabbix : %.1f s" % first)
    if firstmail is not None:
        print("Tiempo hasta el primer correo en Mailhog: %.1f s" % firstmail)


if __name__ == "__main__":
    main()
