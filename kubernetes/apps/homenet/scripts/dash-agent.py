#!/usr/bin/env python3
"""Run a collector when the dashboard asks for it, and at no other time.

Homepage's customapi widget does a plain HTTP GET, so the only way to tie a
collection to someone opening the page is to put something behind the URL
that runs it. Nothing in front of it does CGI, so this is that something.

Was switch-agent.py, which did this for the switch alone while WAN health
came from a once-a-minute cron that ran whether or not anyone was looking.
Both endpoints belong on the same footing, so the agent now takes a table.

MIN_AGE is the safety floor, per endpoint, because the two devices tolerate
very different treatment:

  switch  60s  An Easy Smart switch permits one web session and every scrape
               logs the operator out of the UI. Restraint here is not just
               politeness to a small CPU.
  wan     30s  RouterOS REST has no session limit and the call is cheap, so
               this only needs to be under the widget's refresh interval for
               an open tab to see current data.

Locks are per endpoint and non-blocking: a slow switch scrape must not hold
up WAN health, and a second request arriving mid-collection should be served
the cached copy rather than queueing another login against the switch.

/power.json is the odd one out: the Proxmox host measures it (battery, fan,
CPU temperature are only visible there) and PUTs it here every minute. It has
no collector; GET just serves the last copy.

Paths default to a conventional /var layout and are overridden by the
environment in the cluster (kubernetes/apps/homenet).
"""
import http.server, os, subprocess, threading, time

WWW = os.environ.get("WWW_DIR", "/var/www/wan")
BIN = os.environ.get("SCRIPT_DIR", "/usr/local/bin")
PAUSE = os.environ.get("SWITCH_PAUSE_FILE", "/etc/switch-scrape.pause")

# url path -> cache file, collector, min seconds between runs, pause file
ENDPOINTS = {
    "/switch.json": (f"{WWW}/switch.json", f"{BIN}/switch-json.sh", 60, PAUSE),
    "/wan.json":    (f"{WWW}/wan.json",    f"{BIN}/wan-json.sh",    30, None),
    "/power.json":  (f"{WWW}/power.json",  None,                     0, None),
}
ADDR = (os.environ.get("DASH_ADDR", "127.0.0.1"), int(os.environ.get("DASH_PORT", "8099")))

# PUT bodies larger than this are refused. power.json is ~100 bytes.
MAX_PUT = 4096

_locks = {p: threading.Lock() for p in ENDPOINTS}


def age(path):
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return 1e9


def refresh(path):
    cache, script, min_age, pause = ENDPOINTS[path]
    if script is None:
        return
    if age(cache) < min_age:
        return
    if pause and os.path.exists(pause):
        return
    if not _locks[path].acquire(blocking=False):
        return
    try:
        subprocess.run([script], timeout=45, capture_output=True)
    except subprocess.TimeoutExpired:
        pass
    finally:
        _locks[path].release()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path not in ENDPOINTS:
            self.send_error(404)
            return
        refresh(path)
        try:
            body = open(ENDPOINTS[path][0], "rb").read()
        except OSError:
            body = b'{"error":"no data"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        path = self.path.split("?", 1)[0]
        if path != "/power.json":
            self.send_error(405)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_PUT:
            self.send_error(400)
            return
        body = self.rfile.read(length)
        # Same sanity check the host applied before pushing: a reading
        # without a state field is a failed one, and must not replace a
        # good copy.
        if b'"state"' not in body:
            self.send_error(400)
            return
        cache = ENDPOINTS[path][0]
        with open(cache + ".tmp", "wb") as f:
            f.write(body)
        os.replace(cache + ".tmp", cache)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(ADDR, Handler).serve_forever()
