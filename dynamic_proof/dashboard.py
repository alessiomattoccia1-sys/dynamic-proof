# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Loopback-only control and read access to the live research registry."""
from __future__ import annotations

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import time
from urllib.parse import parse_qs, unquote, urlsplit

from .core.logic import residual, usable_for_coverage
from .core.model import Claim


STATIC = Path(__file__).with_name("web")
MIMES = {"index.html": "text/html; charset=utf-8", "style.css": "text/css; charset=utf-8",
         "app.js": "text/javascript; charset=utf-8"}


def make_server(store, labs, config, port):
    token = secrets.token_urlsafe(24)
    modules = {lab.id: lab for lab in labs}

    class Handler(BaseHTTPRequestHandler):
        server_version = "DynamicProof"

        def log_message(self, *_args):
            return

        def _allowed_host(self):
            port = self.server.server_port
            return self.headers.get("Host", "") in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def _reply(self, status, data, mime, disposition=None):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _json(self, status, data):
            self._reply(status, json.dumps(data, ensure_ascii=False, allow_nan=False).encode(),
                        "application/json; charset=utf-8")

        def do_GET(self):
            if not self._allowed_host():
                self._json(403, {"error": "accesso consentito solo in loopback"})
                return
            request = urlsplit(self.path)
            path = request.path
            static = "index.html" if path == "/" else path.removeprefix("/")
            if static in MIMES:
                self._reply(200, (STATIC / static).read_bytes(), MIMES[static])
            elif path == "/api/status":
                data = store.snapshot()
                heartbeat = float(data["settings"].get("heartbeat") or 0)
                data["runner_online"] = bool(data["settings"].get("runner_pid")) and time.time() - heartbeat < 10
                data["limits"] = asdict(config)
                data["csrf"] = token
                data["labs"] = []
                for lab in labs:
                    options = self._options(lab, data["claims"])
                    data["labs"].append({"id": lab.id, "title": lab.title, "summary": lab.summary,
                                         "coverage_target": lab.coverage_target, "coverage_options": options,
                                         "coverage_defaults": list(lab.coverage_options)})
                self._json(200, data)
            elif path == "/api/sources":
                self._json(200, store.sources())
            elif path.startswith("/api/claim/"):
                found = store.claim(unquote(path.removeprefix("/api/claim/")))
                self._json(200, found) if found else self._json(404, {"error": "enunciato assente"})
            elif path.startswith("/api/artifact/"):
                key = path.removeprefix("/api/artifact/")
                found = store.artifact(key) if re.fullmatch(r"[a-f0-9]{64}", key) else None
                self._json(200, found) if found else self._json(404, {"error": "artefatto assente"})
            elif path.startswith("/api/report/"):
                self._report(path.removeprefix("/api/report/"))
            elif path.startswith("/api/coverage/"):
                self._coverage(path.removeprefix("/api/coverage/"), parse_qs(request.query, keep_blank_values=True))
            else:
                self._json(404, {"error": "risorsa non trovata"})

        def _report(self, filename):
            if re.fullmatch(r"[0-9]{6,}\.(md|json)", filename):
                file = store.path.parent / "reports" / filename
                if file.is_file():
                    mime = "text/markdown; charset=utf-8" if file.suffix == ".md" else "application/json; charset=utf-8"
                    self._reply(200, file.read_bytes(), mime, f'attachment; filename="dynamic-proof-{filename}"')
                    return
            self._json(404, {"error": "rapporto assente"})

        def _coverage(self, lab_id, query):
            lab = modules.get(lab_id)
            if not lab or not lab.coverage_target:
                self._json(404, {"error": "riduzione non configurata"})
                return
            identifiers = query.get("include", list(lab.coverage_options))
            identifiers = list(dict.fromkeys(item for item in identifiers if item))
            options = self._options(lab, store.snapshot()["claims"])
            if any(item not in options for item in identifiers):
                self._json(422, {"error": "risultato incompatibile con il dominio di copertura"})
                return
            try:
                target = Claim.read(store.claim(lab.coverage_target))
                premises = []
                for identifier in identifiers:
                    data = store.claim(identifier)
                    if not data or data.get("quarantine") or data.get("refuted_by"):
                        raise ValueError(f"premessa in revisione: {identifier}")
                    premises.append(Claim.read(data))
                self._json(200, residual(target.statement, premises).data())
            except (TypeError, ValueError, KeyError) as error:
                self._json(422, {"error": str(error)})

        def _options(self, lab, rows):
            options = list(lab.coverage_options)
            if not lab.coverage_target:
                return options
            raw_target = store.claim(lab.coverage_target)
            if not raw_target:
                return options
            target = Claim.read(raw_target).statement
            for row in rows:
                if row["lab"] != lab.id or row["id"] in options or row.get("quarantine"):
                    continue
                if row.get("refuted_by"):
                    continue
                claim = Claim.read(row)
                if (usable_for_coverage(claim) and claim.statement.binders == target.binders
                        and claim.statement.conclusion == target.conclusion):
                    options.append(claim.id)
            return options

        def do_POST(self):
            port = self.server.server_port
            if (not self._allowed_host()
                    or self.headers.get("Origin", "") not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
                    or not secrets.compare_digest(self.headers.get("X-Research-Token", ""), token)):
                self._json(403, {"error": "controllo locale non autorizzato"})
                return
            if self.path != "/api/control":
                self._json(404, {"error": "risorsa non trovata"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 1024:
                    raise ValueError("richiesta non valida")
                data = json.loads(self.rfile.read(size))
                store.control(data["mode"])
            except (ValueError, KeyError, TypeError):
                self._json(422, {"error": "comando di controllo non valido"})
                return
            self._json(200, {"mode": data["mode"]})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
