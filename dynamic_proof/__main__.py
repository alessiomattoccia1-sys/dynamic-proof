# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Run the Dynamic Proof service or inspect its local research state."""
from argparse import ArgumentParser
from dataclasses import asdict
import json
from pathlib import Path
import signal
import threading

from .config import read_config
from .core.logic import deduce
from .core.model import Claim, Kind, Statement, digest
from .core.plugin import Work
from .core.runner import Runner
from .core.store import Store
from .dashboard import make_server
from .labs.catalog import BY_ID, LABS


ROOT = Path(__file__).resolve().parent.parent
QUERIES = {
    "riemann": "Robin inequality | Riemann hypothesis | divisor sums",
    "strings": "Rankin Selberg | string theory | horocycle",
    "tmf": "Levi-Civita connections | conformal metrics | averaging",
    "particle_theory": "chiral U(1) anomaly | Yukawa masses | Abelian Higgs fermions",
}


def main():
    parser = ArgumentParser(prog="dynamic-proof")
    parser.add_argument("--state", type=Path, default=ROOT / "state")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="register sources, statements, and initial jobs")
    run = commands.add_parser("run", help="run persistent research from the command line")
    run.add_argument("--cycles", type=int, help="maximum attempts in this run")
    serve = commands.add_parser("serve", help="serve the dashboard and run persistent research")
    serve.add_argument("--port", type=int)
    for command in (initialize, run, serve):
        command.add_argument("--lab", choices=tuple(BY_ID), help="limit the command to one laboratory")
    commands.add_parser("status", help="show registry status as JSON")
    queue = commands.add_parser("queue", help="queue a new structured statement")
    queue.add_argument("lab", choices=tuple(lab.id for lab in LABS))
    queue.add_argument("file", type=Path)
    submit = commands.add_parser("submit", help="queue a lab-specific JSON problem")
    submit.add_argument("lab", choices=tuple(lab.id for lab in LABS if lab.submit))
    submit.add_argument("file", type=Path)
    transfer = commands.add_parser("transfer", help="transfer a result with the same domain and assumptions")
    transfer.add_argument("claim")
    transfer.add_argument("lab", choices=tuple(lab.id for lab in LABS))
    entail = commands.add_parser("deduce", help="check whether registered premises entail a statement in the SMT fragment")
    entail.add_argument("target")
    entail.add_argument("premises", nargs="+")
    control = commands.add_parser("control")
    control.add_argument("mode", choices=("running", "paused", "stopped"))
    args = parser.parse_args()
    config, port = read_config(args.config)
    store = Store(args.state.resolve() / "research.sqlite3")
    if args.command == "status":
        print(json.dumps(store.snapshot() | {"limits": asdict(config)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "control":
        store.control(args.mode)
        print(args.mode)
        return 0
    selected = getattr(args, "lab", None) if args.command in {"init", "run", "serve", "submit"} else None
    selected_labs = (BY_ID[selected],) if selected else LABS
    store.register(ROOT, selected_labs)
    if args.command == "init":
        print(f"Registry initialized · {store.path}")
        return 0
    if args.command == "submit":
        try:
            if args.file.stat().st_size > 64 * 1024:
                raise ValueError("file is too large")
            problem = json.loads(args.file.read_text(encoding="utf-8"))
            added = store.enqueue(args.lab, BY_ID[args.lab].submit(problem).data())
        except (ValueError, KeyError, TypeError, RecursionError, OSError) as error:
            parser.error(str(error))
        print(f"{problem['id']} · {'queued' if added else 'already registered'}")
        return 0
    if args.command == "queue":
        try:
            if args.file.stat().st_size > 64 * 1024:
                raise ValueError("file is too large")
            raw = json.loads(args.file.read_text(encoding="utf-8"))
            statement = Statement.read(raw["statement"])
            title = raw["title"]
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 140:
                raise ValueError("invalid title")
            if len(statement.binders) > 12 or len(statement.hypotheses) > 16:
                raise ValueError("statement is too large for a single search")
            if type(raw.get("relax", False)) is not bool:
                raise ValueError("relax must be a boolean")
            proposal = Claim("input." + digest([args.lab, statement.fingerprint()])[:20], args.lab, title,
                             statement, Kind.CONJECTURE, evidence={"origin": "structured input"})
            added = store.queue_claim(proposal, Work("@statement", {"statement": statement.data(), "title": title,
                                         "parent": proposal.id, "relax": raw.get("relax", False)}, 92).data())
        except (ValueError, KeyError, TypeError, RecursionError, OSError) as error:
            parser.error(str(error))
        print(f"{proposal.id} · {'queued' if added else 'already registered'}")
        return 0
    if args.command == "transfer":
        source = store.claim(args.claim)
        if (not source or source["quarantine"] or source["refuted_by"]
                or Kind(source["kind"]) not in {Kind.FORMAL, Kind.EXACT, Kind.LITERATURE, Kind.CONDITIONAL}):
            parser.error("result is missing or ineligible for reuse")
        original = Claim.read(source)
        if original.lab == args.lab:
            parser.error("select a different laboratory")
        imported = Claim(f"transfer.{args.lab}.{original.id}", args.lab, original.title, original.statement,
                         Kind.CONDITIONAL, original.sources, (original.id,),
                         {"rule": "transfer with identical domain, quantifiers, and assumptions",
                          "usable_for_coverage": bool(original.evidence.get("usable_for_coverage"))})
        store.add_claim(imported)
        print(imported.id)
        return 0
    if args.command == "deduce":
        rows = [store.claim(identifier) for identifier in [args.target, *args.premises]]
        if any(not row or row["quarantine"] or row["refuted_by"] for row in rows):
            parser.error("statement is missing or under review")
        target, *premises = map(Claim.read, rows)
        try:
            trace = deduce(target.statement, premises)
        except ValueError as error:
            parser.error(str(error))
        if trace["status"] == "conditional":
            identifier = "deduction." + digest([target.id, sorted(trace["dependencies"])])[:20]
            store.add_claim(Claim(identifier, target.lab, target.title, target.statement, Kind.CONDITIONAL,
                                  dependencies=tuple(trace["dependencies"]), evidence=trace))
            trace["id"] = identifier
        print(json.dumps(trace, ensure_ascii=False, indent=2))
        return 0 if trace["status"] == "conditional" else 1
    runner = Runner(ROOT, store, config, QUERIES)
    if args.command == "run":
        if args.cycles is not None and args.cycles < 1:
            parser.error("--cycles must be positive")
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: runner.stop.set())
        completed = runner.run(args.cycles, lab=selected)
        print(f"Attempts completed · {completed}")
        return 0

    if args.port is not None and not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    http = make_server(store, selected_labs, config, args.port or port)
    failed = []

    def research_loop():
        try:
            runner.run(lab=selected)
        except Exception as error:
            failed.append(error)
            print(f"Orchestrator stopped · {error}", flush=True)
            http.shutdown()

    def shutdown(*_args):
        runner.stop.set()
        threading.Thread(target=http.shutdown, daemon=True).start()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown)
    background = threading.Thread(target=research_loop, name="dp-research", daemon=True)
    background.start()
    print(f"Dynamic Proof · http://127.0.0.1:{http.server_port}", flush=True)
    try:
        http.serve_forever(poll_interval=0.25)
    finally:
        runner.stop.set()
        background.join(timeout=8)
        http.server_close()
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
