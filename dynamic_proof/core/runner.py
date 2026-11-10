# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Persistent bounded research cycles with process-group cancellation."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

from .literature import assess, local_search
from .model import Kind, canonical, digest
from .plugin import Work
from .reports import write_report


_MAX_OUTPUT_BYTES = 16 * 1024 * 1024


class Interrupted(Exception):
    pass


class BudgetExceeded(Exception):
    pass


def _group_stats(group: int) -> tuple[int, float]:
    try:
        report = subprocess.run(["ps", "-axo", "pgid=,rss=,time="],
                                capture_output=True, text=True, timeout=1, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 0, 0.0
    rss_kib = 0
    cpu = 0.0
    for line in report.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3 or parts[0] != str(group):
            continue
        try:
            rss_kib += int(parts[1])
            fields = parts[2].replace("-", ":").split(":")
            seconds = 0.0
            for index, item in enumerate(reversed(fields)):
                seconds += float(item) * (60 ** index if index < 3 else 86400)
            cpu += seconds
        except ValueError:
            continue
    return rss_kib, cpu


class Runner:
    def __init__(self, root, store, config, queries=None):
        self.root = root
        self.store = store
        self.config = config
        self.queries = queries or {}
        self.stop = threading.Event()

    def run(self, limit=None):
        lock_path = self.store.path.parent / "runner.lock"
        with lock_path.open("a+", encoding="utf-8") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("orchestratore già in esecuzione per questo registro") from error
            self.store.recover()
            self.store.set_setting("runner_pid", os.getpid())
            self.store.event("runner_start", {"pid": os.getpid(), "limits": asdict(self.config)})
            completed = 0
            last_run = 0.0
            last_review = 0.0
            try:
                while not self.stop.is_set() and (limit is None or completed < limit):
                    self.store.set_setting("heartbeat", time.time())
                    if self.store.setting("control") == "running" and time.monotonic() - last_review > 60:
                        if limit is None:
                            self._schedule_review()
                        last_review = time.monotonic()
                    if limit is None and time.monotonic() - last_run < self.config.min_job_interval:
                        self.stop.wait(1)
                        continue
                    job = self.store.next_job(self.config.max_jobs_per_day)
                    if job is None:
                        if limit is not None:
                            break
                        self.stop.wait(1)
                        continue
                    self._cycle(job)
                    completed += 1
                    last_run = time.monotonic()
            finally:
                self.store.set_setting("runner_pid", "")
                self.store.event("runner_exit", {"cycles": completed})
        return completed

    def _schedule_review(self):
        now = datetime.now(timezone.utc)
        # Persistent research includes a low-frequency refresh for each source
        # queue once a week. The dedup key survives crashes and restarts.
        if not self.config.online_literature:
            return
        week = now.strftime("%G-W%V")
        for lab, query in self.queries.items():
            self.store.enqueue(lab, Work("@literature", {"query": query, "week": week}, 8).data())

    def _cycle(self, job):
        started = time.monotonic()
        metrics = {"peak_rss_kib": 0, "cpu_seconds_observed": 0.0}
        assessment = None
        retry = None
        try:
            result = self._experiment(job, metrics)
            self.store.stage(job, "classificazione", "Separazione tra prova, certificato numerico e novità")
            if result.get("claims"):
                assessment = self._assess(job, result, metrics, started)
                result["pause_after_candidate"] = not self.config.continue_after_candidate
        except Interrupted as error:
            result = self._failure("interrupted", str(error))
            retry = 0
        except (BudgetExceeded, RuntimeError, OSError, ValueError) as error:
            result = self._failure("failed", str(error))
            if job["attempts"] <= self.config.max_retries:
                retry = min(900, 15 * (2**job["attempts"]))
        metrics["wall_seconds"] = round(time.monotonic() - started, 4)
        metrics["limits"] = asdict(self.config)
        try:
            artifact = self.store.finish(job, result, metrics, assessment, retry)
        except (ValueError, KeyError, TypeError) as error:
            result = self._failure("failed", f"registro ha rifiutato il risultato: {error}")
            assessment = None
            artifact = self.store.finish(job, result, metrics, None)
        try:
            write_report(self.store.path.parent, job, result, metrics, assessment, artifact)
        except OSError as error:
            self.store.event("report_error", {"error": str(error), "artifact": artifact},
                             job["lab"], job["attempt_id"])

    def _assess(self, job, result, metrics, started):
        target = result["claims"][-1]
        first_seen, literature_matches = self.store.prior(target["fingerprint"])
        known = tuple(dict.fromkeys((*result.get("known", ()), *literature_matches)))
        evidence_kind = Kind(target["kind"])
        substantive = result.get("substantive", False)
        proof = result.get("proof_complete", False)
        independent = result.get("independent", False)
        comparisons = result.get("comparisons", [])
        query = result.get("public_query") or self.queries.get(job["lab"], "")
        searches = [{"source": "catalogo locale", "query": query, "ok": True,
                     "hits": local_search(query, self.store.sources())}]
        replayed = False
        if not known and substantive and proof and independent:
            time_left = self.config.wall_seconds - (time.monotonic() - started)
            if time_left > 2:
                self.store.stage(job, "verifica_indipendente", "Ripetizione in un nuovo processo")
                try:
                    replay = self._experiment(job, metrics, time_limit=time_left)
                    replayed = _replay_signature(result) == _replay_signature(replay)
                except (BudgetExceeded, RuntimeError, OSError, ValueError) as error:
                    self.store.event("replay_unavailable", {"reason": str(error)}, job["lab"], job["attempt_id"])
            time_left = self.config.wall_seconds - (time.monotonic() - started)
            if self.config.online_literature and query and time_left > 3:
                self.store.stage(job, "letteratura", "Ricerca pubblica con termini generali del laboratorio")
                try:
                    study = self._experiment(job | {"strategy": "@literature", "payload": {"query": query}},
                                             metrics, time_limit=time_left)
                    searches.extend(study["detail"]["searches"])
                except (BudgetExceeded, RuntimeError, OSError, ValueError) as error:
                    searches.append({"source": "ricerca esterna", "query": query, "ok": False,
                                     "error": str(error), "hits": []})
        outcome = assess(evidence_kind=evidence_kind, known=known, similar=False,
                         substantive=substantive, proof_complete=proof, independent=independent,
                         replayed=replayed, searches=searches, comparisons=comparisons, first_seen=not first_seen)
        return outcome | {"fingerprint": target["fingerprint"], "claim": target["id"]}

    @staticmethod
    def _failure(status, reason):
        return {"status": status, "title": "Esperimento interrotto" if status == "interrupted" else "Tentativo negativo",
                "detail": {"reason": reason}, "claims": [], "followups": []}

    def _experiment(self, job, stats, time_limit=None):
        start = time.monotonic()
        wall = self.config.wall_seconds if time_limit is None else min(time_limit, self.config.wall_seconds)
        specification = {"lab": job["lab"], "strategy": job["strategy"], "payload": job["payload"],
                         "root": str(self.root), "parent": os.getpid(), "online": self.config.online_literature,
                         "limits": asdict(self.config)}
        with tempfile.TemporaryDirectory(prefix="dp-job-", dir=self.store.path.parent) as temporary:
            folder = Path(temporary)
            jobfile = folder / "job.json"
            jobfile.write_text(canonical(specification), encoding="utf-8")
            with (folder / "stdout").open("wb") as stdout, (folder / "stderr").open("wb") as stderr:
                process = subprocess.Popen([sys.executable, "-m", "dynamic_proof.worker", str(jobfile)],
                                           cwd=self.root, stdout=stdout, stderr=stderr, start_new_session=True,
                                           stdin=subprocess.DEVNULL)
                self.store.set_setting("worker_pid", process.pid)
                try:
                    with (folder / "stdout").open("rb") as output:
                        return self._monitor(process, output, folder, start, wall, job, stats)
                finally:
                    if process.poll() is None:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait(timeout=3)
                    self.store.set_setting("worker_pid", "")

    def _monitor(self, process, output, folder, start, wall, job, stats):
        result = None
        last_sample = 0.0
        while True:
            if self.stop.is_set() or self.store.setting("control") != "running":
                raise Interrupted("pausa o arresto; il checkpoint del lavoro verrà ripreso")
            if time.monotonic() - start > wall:
                raise BudgetExceeded(f"superato limite di durata ({wall:.1f} s)")
            if (folder / "stdout").stat().st_size > _MAX_OUTPUT_BYTES:
                raise BudgetExceeded("dimensione massima del registro di un esperimento")
            while True:
                mark = output.tell()
                line = output.readline()
                if not line.endswith(b"\n"):
                    output.seek(mark)
                    break
                data = json.loads(line)
                if "stage" in data:
                    self.store.stage(job, data["stage"], data["detail"])
                elif "error" in data:
                    log = (folder / "stderr").read_bytes()[-1800:].decode(errors="replace")
                    raise RuntimeError(data["error"] + ("\n" + log if log else ""))
                elif "result" in data:
                    usage = data.get("usage", {})
                    rss = usage.get("max_rss_kib", 0)
                    cpu = usage.get("cpu_seconds", 0.0)
                    stats["peak_rss_kib"] = max(stats["peak_rss_kib"], rss)
                    stats["cpu_seconds_observed"] = max(stats["cpu_seconds_observed"], round(cpu, 4))
                    if rss > self.config.memory_mb * 1024 or cpu > self.config.cpu_seconds:
                        raise BudgetExceeded("risorse finali del worker oltre i limiti")
                    result = data["result"]
            if process.poll() is not None:
                if output.tell() < (folder / "stdout").stat().st_size:
                    pending = output.readline()
                    if pending.endswith(b"\n"):
                        output.seek(-len(pending), os.SEEK_CUR)
                        continue
                if process.returncode != 0 or result is None:
                    log = (folder / "stderr").read_bytes()[-1800:].decode(errors="replace")
                    raise RuntimeError(f"worker terminato con codice {process.returncode}: {log}")
                return result
            now = time.monotonic()
            if now - last_sample >= 0.35:
                rss, cpu = _group_stats(process.pid)
                stats["peak_rss_kib"] = max(stats["peak_rss_kib"], rss)
                stats["cpu_seconds_observed"] = max(stats["cpu_seconds_observed"], round(cpu, 4))
                if rss > self.config.memory_mb * 1024:
                    raise BudgetExceeded(f"superato limite RSS ({self.config.memory_mb} MiB)")
                if cpu > self.config.cpu_seconds:
                    raise BudgetExceeded(f"superato limite CPU del gruppo ({self.config.cpu_seconds} s)")
                self.store.set_setting("worker_rss_kib", rss)
                self.store.set_setting("worker_cpu_seconds", round(cpu, 3))
                self.store.set_setting("heartbeat", time.time())
                last_sample = now
            self.stop.wait(0.15)


def _replay_signature(result):
    # Compare the scientific data. Scheduling and acquisition metadata are
    # deliberately excluded. Disagreement blocks originality promotion.
    return digest({"status": result["status"], "claims": result.get("claims", []),
                   "detail": result["detail"]})
