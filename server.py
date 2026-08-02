"""Tiny local web server for the lead launcher. Stdlib only.

GET  /            -> the button page (index.html)
GET  /config      -> button metadata + recipient (for the page)
POST /run/<1..5>  -> start that button's pipeline on a background thread -> {job_id}
GET  /status/<id> -> {running, log, result} for live polling

One job at a time: the pipelines share the master workbook and the same API keys,
so a second click while one runs is refused (409).
"""

import json
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import orchestrator

JOBS = {}
LOCK = threading.Lock()
CURRENT = {"id": None}          # id of the running job, or None


def _start_job(button_id: str, params: dict):
    jobid = uuid.uuid4().hex[:12]
    job = {"running": True, "button": button_id, "log": [], "result": None}
    JOBS[jobid] = job

    def log(line: str):
        job["log"].append(str(line))

    def worker():
        try:
            job["result"] = orchestrator.run(button_id, jobid, log, params)
        except Exception as exc:  # last-resort guard; orchestrator handles its own
            job["result"] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}",
                             "rate_limits": [], "count": 0, "drafted": 0,
                             "mailed": False, "label": button_id}
        finally:
            job["running"] = False
            with LOCK:
                CURRENT["id"] = None

    threading.Thread(target=worker, daemon=True).start()
    return jobid


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass   # keep the console clean; the page shows progress

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(f"{config.LAUNCHER_DIR}\\index.html", "rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, "index.html missing", "text/plain")
            return

        if self.path == "/config":
            buttons = []
            for k, v in sorted(config.BUTTONS.items()):
                options = v.get("options")
                if options is not None and not options:
                    continue   # the tool repo is missing/broken — hide the card
                b = {"id": k, "label": v["label"], "subtitle": v["subtitle"]}
                if options:
                    b["options"] = options
                buttons.append(b)
            self._json(200, {"buttons": buttons, "recipient": config.RECIPIENT})
            return

        if self.path.startswith("/status/"):
            jobid = self.path.rsplit("/", 1)[-1]
            job = JOBS.get(jobid)
            if not job:
                self._json(404, {"error": "unknown job"})
                return
            self._json(200, {"running": job["running"], "log": job["log"],
                             "result": job["result"]})
            return

        self._json(404, {"error": "not found"})

    def _body_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length))
            return data if isinstance(data, dict) else {}
        except (ValueError, OSError):
            return {}

    def do_POST(self):
        if self.path.startswith("/run/"):
            button_id = self.path.rsplit("/", 1)[-1]
            if button_id not in config.BUTTONS:
                self._json(400, {"error": f"unknown button {button_id}"})
                return
            params = self._body_json()
            options = config.BUTTONS[button_id].get("options")
            if options is not None:
                choice = str(params.get("choice") or "").strip()
                if not choice:
                    self._json(400, {"error": "pick an option from the dropdown first"})
                    return
                if choice not in options:
                    self._json(400, {"error": f"unknown option '{choice}'"})
                    return
            with LOCK:
                if CURRENT["id"] is not None:
                    self._json(409, {"error": "a run is already in progress"})
                    return
                jobid = _start_job(button_id, params)
                CURRENT["id"] = jobid
            self._json(200, {"job_id": jobid})
            return
        self._json(404, {"error": "not found"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", config.PORT), Handler)
    url = f"http://127.0.0.1:{config.PORT}/"
    print(f"Chillispark lead launcher running at {url}")
    print(f"Leads will be emailed to: {config.RECIPIENT}")
    print("Close this window to stop. Opening your browser...")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
