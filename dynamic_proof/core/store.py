# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Transactional theorem, evidence and research-memory registries."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time

from .model import Claim, Kind, Statement, canonical, digest


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS claims(
    id TEXT PRIMARY KEY, lab TEXT NOT NULL, kind TEXT NOT NULL, fingerprint TEXT NOT NULL,
    data TEXT NOT NULL, created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS claims_fingerprint ON claims(fingerprint);
CREATE TABLE IF NOT EXISTS edges(
    child TEXT NOT NULL REFERENCES claims(id), parent TEXT NOT NULL REFERENCES claims(id),
    PRIMARY KEY(child, parent)
);
CREATE TABLE IF NOT EXISTS quarantined(id TEXT PRIMARY KEY REFERENCES claims(id), reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS refutations(
    target TEXT NOT NULL REFERENCES claims(id), witness TEXT NOT NULL REFERENCES claims(id),
    PRIMARY KEY(target, witness)
);
CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(
    id TEXT PRIMARY KEY, lab TEXT NOT NULL, strategy TEXT NOT NULL, payload TEXT NOT NULL,
    priority INTEGER NOT NULL, generation INTEGER NOT NULL, available REAL NOT NULL, created REAL NOT NULL,
    status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, parent TEXT REFERENCES jobs(id)
);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status, available, lab);
CREATE TABLE IF NOT EXISTS attempts(
    id INTEGER PRIMARY KEY, job TEXT NOT NULL REFERENCES jobs(id), started REAL NOT NULL, ended REAL,
    status TEXT NOT NULL, stage TEXT NOT NULL, artifact TEXT REFERENCES artifacts(id), stats TEXT
);
CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY, at REAL NOT NULL, action TEXT NOT NULL, lab TEXT, attempt INTEGER, detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS novelty(
    fingerprint TEXT PRIMARY KEY, level TEXT NOT NULL, artifact TEXT NOT NULL REFERENCES artifacts(id), updated REAL NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            conn.execute("INSERT OR IGNORE INTO settings VALUES ('control','running')")

    @contextmanager
    def connection(self, *, write: bool = False):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                if write:
                    conn.execute("BEGIN IMMEDIATE")
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _event(conn, action, detail, lab=None, attempt=None):
        conn.execute("INSERT INTO events(at,action,lab,attempt,detail) VALUES(?,?,?,?,?)",
                     (time.time(), action, lab, attempt, canonical(detail)))

    def event(self, action, detail, lab=None, attempt=None):
        with self.connection(write=True) as conn:
            self._event(conn, action, detail, lab, attempt)

    def setting(self, key, default=None):
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self.connection(write=True) as conn:
            conn.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (key, str(value)))

    def control(self, value: str):
        if value not in {"running", "paused", "stopped"}:
            raise ValueError("comando di controllo non valido")
        with self.connection(write=True) as conn:
            conn.execute("UPDATE settings SET value=? WHERE key='control'", (value,))
            self._event(conn, "control", {"mode": value})

    def register(self, root, labs):
        with self.connection(write=True) as conn:
            for lab in labs:
                for source in lab.sources:
                    data = source.data(root)
                    old = conn.execute("SELECT data FROM sources WHERE id=?", (source.id,)).fetchone()
                    if old and old["data"] != canonical(data):
                        raise ValueError(f"fonte modificata con lo stesso identificativo: {source.id}")
                    conn.execute("INSERT OR IGNORE INTO sources VALUES(?,?)", (source.id, canonical(data)))
            for lab in labs:
                for claim in lab.claims:
                    self._claim(conn, claim)
                for job in lab.seeds:
                    self._enqueue(conn, lab.id, job.data())

    def _claim(self, conn, claim: Claim):
        data = claim.data()
        payload = canonical(data)
        old = conn.execute("SELECT data FROM claims WHERE id=?", (claim.id,)).fetchone()
        if old:
            if old["data"] != payload:
                raise ValueError(f"registro immutabile: {claim.id}")
            return
        for source in claim.sources:
            if not conn.execute("SELECT 1 FROM sources WHERE id=?", (source,)).fetchone():
                raise ValueError(f"fonte inesistente: {source}")
        for parent in claim.dependencies:
            if not conn.execute("SELECT 1 FROM claims WHERE id=?", (parent,)).fetchone():
                raise ValueError(f"dipendenza assente o ciclica: {parent}")
        evidence = claim.evidence or {}
        if claim.kind == Kind.FORMAL and not evidence.get("lean", {}).get("valid"):
            raise ValueError("prova formale senza controllo del kernel")
        if claim.kind == Kind.EXACT and not (evidence.get("verified") and evidence.get("independent")):
            raise ValueError("verifica esatta incompleta")
        if claim.kind == Kind.CERTIFIED and not (evidence.get("verified") and evidence.get("precision_bits")):
            raise ValueError("certificazione numerica senza verifica o precisione")
        if claim.kind == Kind.COUNTEREXAMPLE and not (evidence.get("verified") and evidence.get("witness")):
            raise ValueError("controesempio privo di testimone verificato")
        if claim.kind == Kind.LITERATURE and not claim.sources:
            raise ValueError("risultato riportato senza una fonte")
        if claim.kind == Kind.ORIGINAL and evidence.get("novelty_level") != "C":
            raise ValueError("classificazione C obbligatoria")
        conn.execute("INSERT INTO claims VALUES(?,?,?,?,?,?)",
                     (claim.id, claim.lab, claim.kind, data["fingerprint"], payload, time.time()))
        conn.executemany("INSERT INTO edges VALUES(?,?)", [(claim.id, parent) for parent in claim.dependencies])
        # A matching verified refutation and assertion need independent review.
        same = conn.execute("SELECT id,kind FROM claims WHERE fingerprint=? AND id<>?",
                            (data["fingerprint"], claim.id)).fetchall()
        if claim.kind == Kind.COUNTEREXAMPLE:
            for row in same:
                if row["kind"] == Kind.CONJECTURE:
                    conn.execute("INSERT OR IGNORE INTO refutations VALUES(?,?)", (row["id"], claim.id))
            for item in evidence.get("impacts", []):
                if conn.execute("SELECT 1 FROM claims WHERE id=?", (item,)).fetchone():
                    conn.execute("INSERT OR IGNORE INTO quarantined VALUES(?,?)",
                                 (item, f"dipendenza scientifica da riesaminare dopo {claim.id}"))
            self._event(conn, "refutation_registered", {"witness": claim.id,
                        "impact": evidence.get("impacts", [])}, claim.lab)
        asserted = {Kind.FORMAL, Kind.EXACT, Kind.LITERATURE}
        conflict = [row["id"] for row in same if
                    (claim.kind == Kind.COUNTEREXAMPLE and row["kind"] in asserted)
                    or (claim.kind in asserted and row["kind"] == Kind.COUNTEREXAMPLE)]
        if conflict:
            reason = "asserzione e controesempio verificato con lo stesso enunciato"
            affected = set(conflict + [claim.id])
            # Withdraw dependent results from reusable coverage until reviewed.
            for parent in tuple(affected):
                children = conn.execute("""
                    WITH RECURSIVE descendants(id) AS (
                        SELECT child FROM edges WHERE parent=?
                        UNION SELECT edges.child FROM edges JOIN descendants ON edges.parent=descendants.id
                    ) SELECT id FROM descendants
                """, (parent,))
                affected.update(row["id"] for row in children)
            conn.executemany("INSERT OR IGNORE INTO quarantined VALUES(?,?)",
                             [(identifier, reason) for identifier in sorted(affected)])
            self._event(conn, "evidence_conflict", {"ids": sorted(affected), "reason": reason}, claim.lab)
        blocked_parents = conn.execute(
            "SELECT 1 FROM edges JOIN quarantined ON parent=quarantined.id WHERE child=?", (claim.id,)).fetchone()
        if blocked_parents:
            conn.execute("INSERT OR IGNORE INTO quarantined VALUES(?,?)", (claim.id, "dipendenza in revisione"))

    def add_claim(self, claim: Claim):
        with self.connection(write=True) as conn:
            self._claim(conn, claim)

    def claim(self, identifier: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute("""
                SELECT data, reason FROM claims LEFT JOIN quarantined USING(id) WHERE id=?
            """, (identifier,)).fetchone()
            refutations = [item[0] for item in conn.execute(
                "SELECT witness FROM refutations WHERE target=? ORDER BY witness", (identifier,))]
        if row is None:
            return None
        return json.loads(row["data"]) | {"quarantine": row["reason"], "refuted_by": refutations}

    def _enqueue(self, conn, lab, job, parent=None):
        identity = job["payload"]
        if job["strategy"] == "@statement":
            identity = Statement.read(identity["statement"]).fingerprint()
        job_id = digest([lab, job["strategy"], identity])
        now = time.time()
        changed = conn.execute("""
            INSERT OR IGNORE INTO jobs VALUES(?,?,?,?,?,?,?,?,'queued',0,?)
        """, (job_id, lab, job["strategy"], canonical(job["payload"]), int(job["priority"]),
              int(job["generation"]), now + max(0, job["delay"]), now, parent)).rowcount
        if changed:
            self._event(conn, "enqueued", {"strategy": job["strategy"], "job": job_id}, lab)
        return changed == 1

    def enqueue(self, lab, job):
        with self.connection(write=True) as conn:
            return self._enqueue(conn, lab, job)

    def queue_claim(self, proposal, job):
        with self.connection(write=True) as conn:
            if not conn.execute("SELECT 1 FROM claims WHERE id=?", (proposal.id,)).fetchone():
                self._claim(conn, proposal)
            return self._enqueue(conn, proposal.lab, job)

    def recover(self):
        with self.connection(write=True) as conn:
            now = time.time()
            rows = conn.execute("SELECT id,job FROM attempts WHERE ended IS NULL").fetchall()
            for row in rows:
                conn.execute("UPDATE attempts SET ended=?, status='interrupted' WHERE id=?", (now, row["id"]))
                conn.execute("UPDATE jobs SET status='queued',available=? WHERE id=?", (now, row["job"]))
                self._event(conn, "checkpoint_recovered", {"job": row["job"]}, attempt=row["id"])

    def next_job(self, daily_limit: int) -> dict | None:
        now = time.time()
        with self.connection(write=True) as conn:
            if conn.execute("SELECT value FROM settings WHERE key='control'").fetchone()[0] != "running":
                return None
            count = conn.execute("SELECT count(*) FROM attempts WHERE started>=?", (now - 86400,)).fetchone()[0]
            if count >= daily_limit:
                return None
            row = conn.execute("""
                SELECT jobs.* FROM jobs
                WHERE status='queued' AND available<=?
                ORDER BY COALESCE((
                    SELECT MAX(attempts.started) FROM attempts JOIN jobs AS prior ON prior.id=attempts.job
                    WHERE prior.lab=jobs.lab
                ),0), (priority + MIN((?-created)/120,20) - 3*attempts) DESC, created, id
                LIMIT 1
            """, (now, now)).fetchone()
            if not row:
                return None
            conn.execute("UPDATE jobs SET status='running',attempts=attempts+1 WHERE id=?", (row["id"],))
            attempt = conn.execute("""
                INSERT INTO attempts(job,started,status,stage) VALUES(?,?,'running','acquisizione')
            """, (row["id"], now)).lastrowid
            self._event(conn, "started", {"job": row["id"], "strategy": row["strategy"]}, row["lab"], attempt)
            return dict(row) | {"payload": json.loads(row["payload"]), "attempt_id": attempt,
                                "attempts": row["attempts"] + 1}

    def stage(self, job, name, detail):
        with self.connection(write=True) as conn:
            conn.execute("UPDATE attempts SET stage=? WHERE id=? AND ended IS NULL", (name, job["attempt_id"]))
            self._event(conn, "stage", {"name": name, "detail": detail}, job["lab"], job["attempt_id"])

    @staticmethod
    def _artifact(conn, data):
        key = digest(data)
        conn.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?)", (key, canonical(data)))
        return key

    def finish(self, job, result, stats, novelty, retry_delay=None):
        with self.connection(write=True) as conn:
            now = time.time()
            key = self._artifact(conn, result | {"novelty": novelty})
            for raw in result.get("claims", []):
                self._claim(conn, Claim.read(raw))
            for item in result.get("followups", []):
                if not self._enqueue(conn, job["lab"], item, job["id"]):
                    self._event(conn, "duplicate_hypothesis", {"strategy": item["strategy"],
                                "payload": item["payload"]}, job["lab"], job["attempt_id"])
            status = result["status"]
            level = novelty["level"] if novelty else None
            if novelty and novelty.get("fingerprint"):
                fingerprint = novelty["fingerprint"]
                previous = conn.execute("SELECT level FROM novelty WHERE fingerprint=?", (fingerprint,)).fetchone()
                rank = {"seen": 0, "A": 1, "B": 2, "C": 3, "known": 4}
                if not previous or rank[level] >= rank[previous["level"]]:
                    conn.execute("INSERT OR REPLACE INTO novelty VALUES(?,?,?,?)", (fingerprint, level, key, now))
            if level == "C":
                target = Claim.read(result["claims"][-1])
                quarantined = conn.execute("SELECT 1 FROM quarantined WHERE id=?", (target.id,)).fetchone()
                if quarantined:
                    raise ValueError("risultato in revisione, promozione vietata")
                claim = Claim(f"original.{target.id}", target.lab, target.title, target.statement,
                              Kind.ORIGINAL, target.sources, (target.id,),
                              {"novelty_level": "C", "proof_kind": target.kind, "artifact": key})
                self._claim(conn, claim)
                self._event(conn, "original_candidate", {"claim": claim.id, "artifact": key}, job["lab"],
                            job["attempt_id"])
            conn.execute("UPDATE attempts SET status=?,stage='salvataggio',ended=?,artifact=?,stats=? WHERE id=?",
                         (status, now, key, canonical(stats), job["attempt_id"]))
            control = conn.execute("SELECT value FROM settings WHERE key='control'").fetchone()[0]
            if retry_delay is not None:
                job_status = "queued"
                available = now + retry_delay
            else:
                job_status = "failed" if status == "failed" else "done"
                available = now
            conn.execute("UPDATE jobs SET status=?,available=? WHERE id=?", (job_status, available, job["id"]))
            if level == "C" and result.get("pause_after_candidate") and control == "running":
                conn.execute("UPDATE settings SET value='paused' WHERE key='control'")
            self._event(conn, "checkpoint", {"status": status, "artifact": key, "next": len(result.get("followups", [])),
                                            "retry": retry_delay is not None}, job["lab"], job["attempt_id"])
            return key

    def prior(self, fingerprint):
        with self.connection() as conn:
            novelty = conn.execute("SELECT level FROM novelty WHERE fingerprint=?", (fingerprint,)).fetchone()
            rows = conn.execute("SELECT id,kind FROM claims WHERE fingerprint=?", (fingerprint,)).fetchall()
        return bool(novelty or rows), tuple(row["id"] for row in rows if row["kind"] == Kind.LITERATURE)

    def sources(self):
        with self.connection() as conn:
            return [json.loads(row[0]) for row in conn.execute("SELECT data FROM sources ORDER BY id")]

    def artifact(self, key):
        with self.connection() as conn:
            row = conn.execute("SELECT data FROM artifacts WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def snapshot(self):
        with self.connection() as conn:
            conn.execute("BEGIN")
            counts = [dict(row) for row in conn.execute(
                "SELECT lab,status,count(*) AS count FROM jobs GROUP BY lab,status")]
            active = [dict(row) for row in conn.execute("""
                SELECT attempts.id,started,stage,lab,strategy FROM attempts JOIN jobs ON job=jobs.id
                WHERE ended IS NULL
            """)]
            runs = [dict(row) for row in conn.execute("""
                SELECT attempts.*,lab,strategy FROM attempts JOIN jobs ON job=jobs.id
                ORDER BY attempts.id DESC LIMIT 50
            """)]
            claims = [json.loads(row["data"]) | {"quarantine": row["reason"]} for row in conn.execute("""
                SELECT data, reason FROM claims LEFT JOIN quarantined USING(id)
                ORDER BY claims.created DESC LIMIT 250
            """)]
            events = [dict(row) | {"detail": json.loads(row["detail"])} for row in conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT 65")]
            settings = dict(conn.execute("SELECT key,value FROM settings"))
            refutations = {}
            for row in conn.execute("SELECT target,witness FROM refutations ORDER BY witness"):
                refutations.setdefault(row["target"], []).append(row["witness"])
            totals = {"attempts": conn.execute("SELECT count(*) FROM attempts WHERE ended IS NOT NULL").fetchone()[0],
                      "evidence": dict(conn.execute("SELECT kind,count(*) FROM claims GROUP BY kind"))}
        for row in runs:
            row["stats"] = json.loads(row["stats"]) if row["stats"] else None
        for claim in claims:
            claim["refuted_by"] = refutations.get(claim["id"], [])
        return {"generated": datetime.now(timezone.utc).isoformat(), "settings": settings,
                "counts": counts, "active": active, "runs": runs, "claims": claims, "events": events,
                "totals": totals}
