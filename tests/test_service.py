# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dynamic_proof.core.store import Store


ROOT = Path(__file__).resolve().parent.parent
CONFIG = """[research]
online_literature = false
memory_mb = 3072
wall_seconds = 45
cpu_seconds = 25
min_job_interval = 0
max_jobs_per_day = 80
"""


class LiveService(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = self.root / "state"
        config = self.root / "config.toml"
        config.write_text(CONFIG)
        self.cmd = [sys.executable, "-m", "dynamic_proof", "--state", str(self.state), "--config", str(config)]

    def test_end_to_end_references_and_browser_api(self):
        completed = subprocess.run([*self.cmd, "run", "--cycles", "14"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=95)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        store = Store(self.state / "research.sqlite3")
        snapshot = store.snapshot()
        reproduced = {attempt["lab"] for attempt in snapshot["runs"] if attempt["status"] == "reproduced"}
        self.assertEqual(reproduced, {"riemann", "strings", "tmf"})
        failures = [store.artifact(row["artifact"]) for row in snapshot["runs"] if row["status"] == "failed"]
        self.assertEqual(failures, [])
        self.assertTrue(store.claim("tmf.mean_connection.identity")["refuted_by"])
        self.assertTrue(any(row["stats"]["peak_rss_kib"] > 5000 for row in snapshot["runs"]))
        self.assertEqual(snapshot["totals"]["evidence"].get("original_candidate", 0), 0)
        store.control("paused")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        process = subprocess.Popen([*self.cmd, "serve", "--port", str(port)], cwd=ROOT,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    status = self.read_json(base + "/api/status")
                    break
                except (URLError, ConnectionResetError):
                    time.sleep(0.1)
            else:
                self.fail("dashboard non raggiungibile")
            self.assertEqual(status["settings"]["control"], "paused")
            self.assertEqual(len(status["labs"]), 3)
            coverage = self.read_json(base + "/api/coverage/riemann?include=riemann.hertlein1")
            self.assertIn(str(2**20), " ".join(coverage["display"]["hypotheses"]))
            with self.assertRaises(HTTPError) as invalid:
                self.read_json(base + "/api/coverage/riemann?include=strings.theta")
            self.assertEqual(invalid.exception.code, 422)
            with self.assertRaises(HTTPError) as cross_origin:
                self.read_json(Request(base + "/api/control", b'{"mode":"stopped"}',
                                       headers={"Origin": "https://example.com", "X-Research-Token": status["csrf"]}))
            self.assertEqual(cross_origin.exception.code, 403)
            self.read_json(Request(base + "/api/control", b'{"mode":"stopped"}',
                                   headers={"Origin": base, "X-Research-Token": status["csrf"]}))
            self.assertEqual(self.read_json(base + "/api/status")["settings"]["control"], "stopped")
            with urlopen(base + "/api/report/000001.md", timeout=4) as response:
                self.assertIn("attachment", response.headers["Content-Disposition"])
                self.assertIn(b"Riproducibilit", response.read())
        finally:
            process.terminate()
            process.wait(timeout=10)

    @staticmethod
    def read_json(request):
        with urlopen(request, timeout=4) as response:
            return json.load(response)

    def test_real_process_crash_and_recovery(self):
        store = Store(self.state / "research.sqlite3")
        from dynamic_proof.core.plugin import Work
        from dynamic_proof.labs.catalog import LABS

        store.enqueue("tmf", Work("mean_connection", {}, 200).data())
        store.register(ROOT, LABS)
        process = subprocess.Popen([*self.cmd, "run", "--cycles", "1"], cwd=ROOT,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 8
            while not store.setting("worker_pid") and time.monotonic() < deadline and process.poll() is None:
                time.sleep(0.015)
            self.assertTrue(store.setting("worker_pid"), "nessun worker attivo da interrompere")
            process.kill()
            process.wait(timeout=4)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=4)
        self.assertEqual(len(store.snapshot()["active"]), 1)
        result = subprocess.run([*self.cmd, "run", "--cycles", "3"], cwd=ROOT, capture_output=True,
                                text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempts = store.snapshot()["runs"]
        self.assertTrue(any(row["status"] == "interrupted" for row in attempts))
        self.assertTrue(any(row["strategy"] == "mean_connection" and row["status"] == "refuted" for row in attempts))
        self.assertIsNotNone(store.claim("tmf.mean_connection.counterexample"))
