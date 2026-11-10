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
from .labs.catalog import LABS


ROOT = Path(__file__).resolve().parent.parent
QUERIES = {
    "riemann": "Robin inequality | Riemann hypothesis | divisor sums",
    "strings": "Rankin Selberg | string theory | horocycle",
    "tmf": "Levi-Civita connections | conformal metrics | averaging",
}


def main():
    parser = ArgumentParser(prog="dynamic-proof")
    parser.add_argument("--state", type=Path, default=ROOT / "state")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="registra fonti, enunciati e attività iniziali")
    run = commands.add_parser("run", help="ricerca persistente senza interfaccia")
    run.add_argument("--cycles", type=int, help="limite di tentativi in questa esecuzione")
    serve = commands.add_parser("serve", help="dashboard e ricerca persistente")
    serve.add_argument("--port", type=int)
    commands.add_parser("status", help="stato JSON del registro")
    queue = commands.add_parser("queue", help="accoda un nuovo enunciato strutturato")
    queue.add_argument("lab", choices=tuple(lab.id for lab in LABS))
    queue.add_argument("file", type=Path)
    transfer = commands.add_parser("transfer", help="trasferisce un risultato con lo stesso dominio e le stesse ipotesi")
    transfer.add_argument("claim")
    transfer.add_argument("lab", choices=tuple(lab.id for lab in LABS))
    entail = commands.add_parser("deduce", help="verifica una conseguenza di premesse registrate nel frammento SMT")
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
    store.register(ROOT, LABS)
    if args.command == "init":
        print(f"Registro inizializzato · {store.path}")
        return 0
    if args.command == "queue":
        try:
            if args.file.stat().st_size > 64 * 1024:
                raise ValueError("file troppo grande")
            raw = json.loads(args.file.read_text(encoding="utf-8"))
            statement = Statement.read(raw["statement"])
            title = raw["title"]
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 140:
                raise ValueError("titolo non valido")
            if len(statement.binders) > 12 or len(statement.hypotheses) > 16:
                raise ValueError("enunciato troppo ampio per una singola ricerca")
            if type(raw.get("relax", False)) is not bool:
                raise ValueError("relax deve essere booleano")
            proposal = Claim("input." + digest([args.lab, statement.fingerprint()])[:20], args.lab, title,
                             statement, Kind.CONJECTURE, evidence={"origin": "input strutturato"})
            added = store.queue_claim(proposal, Work("@statement", {"statement": statement.data(), "title": title,
                                         "parent": proposal.id, "relax": raw.get("relax", False)}, 92).data())
        except (ValueError, KeyError, TypeError, RecursionError, OSError) as error:
            parser.error(str(error))
        print(f"{proposal.id} · {'in coda' if added else 'già registrato'}")
        return 0
    if args.command == "transfer":
        source = store.claim(args.claim)
        if (not source or source["quarantine"] or source["refuted_by"]
                or Kind(source["kind"]) not in {Kind.FORMAL, Kind.EXACT, Kind.LITERATURE, Kind.CONDITIONAL}):
            parser.error("risultato assente o inadatto al riuso")
        original = Claim.read(source)
        if original.lab == args.lab:
            parser.error("selezionare un laboratorio diverso")
        imported = Claim(f"transfer.{args.lab}.{original.id}", args.lab, original.title, original.statement,
                         Kind.CONDITIONAL, original.sources, (original.id,),
                         {"rule": "trasferimento con identici dominio, quantificatori e ipotesi",
                          "usable_for_coverage": bool(original.evidence.get("usable_for_coverage"))})
        store.add_claim(imported)
        print(imported.id)
        return 0
    if args.command == "deduce":
        rows = [store.claim(identifier) for identifier in [args.target, *args.premises]]
        if any(not row or row["quarantine"] or row["refuted_by"] for row in rows):
            parser.error("enunciato assente o in revisione")
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
            parser.error("--cycles deve essere positivo")
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: runner.stop.set())
        completed = runner.run(args.cycles)
        print(f"Tentativi terminati · {completed}")
        return 0

    if args.port is not None and not 1024 <= args.port <= 65535:
        parser.error("--port deve essere compresa tra 1024 e 65535")
    http = make_server(store, LABS, config, args.port or port)
    failed = []

    def research_loop():
        try:
            runner.run()
        except Exception as error:
            failed.append(error)
            print(f"Orchestratore interrotto · {error}", flush=True)
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
