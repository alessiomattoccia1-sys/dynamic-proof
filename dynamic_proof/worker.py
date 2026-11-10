# SPDX-License-Identifier: Apache-2.0
"""One isolated experiment. Only registered strategies can run."""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import signal
import sys
import threading
import time


def _send(data):
    print(json.dumps(data, ensure_ascii=False, allow_nan=False), flush=True)


def _result(data):
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    divisor = 1024 if sys.platform == "darwin" else 1
    usage = {"max_rss_kib": max(own.ru_maxrss, children.ru_maxrss) // divisor,
             "cpu_seconds": own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime}
    _send({"result": data, "usage": usage})


def _parent_watch(parent):
    while os.getppid() == parent:
        time.sleep(0.3)
    os.killpg(os.getpgrp(), signal.SIGKILL)


def main():
    specification = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    parent = specification["parent"]
    if os.getppid() != parent:
        return 2
    threading.Thread(target=_parent_watch, args=(parent,), daemon=True).start()
    limits = specification["limits"]
    resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"] + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if sys.platform.startswith("linux"):
        memory = limits["memory_mb"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    try:
        if specification["strategy"] == "@literature":
            from .core.literature import external_search
            query = specification["payload"]["query"]
            _send({"stage": "letteratura", "detail": query})
            hits = external_search(query) if specification["online"] else []
            _result({"status": "reproduced" if any(row["ok"] for row in hits) else "inconclusive",
                              "title": "Confronto bibliografico",
                              "detail": {"query": query, "searches": hits},
                              "claims": [], "followups": []})
            return 0
        from .core.plugin import Context
        if specification["strategy"] == "@statement":
            from .core.experiment import audit_statement
            emit = lambda name, detail: _send({"stage": name, "detail": detail})
            context = Context(Path(specification["root"]), False, emit)
            _result(audit_statement(context, specification["lab"], specification["payload"]).data())
            return 0
        from .labs.catalog import BY_ID
        lab = BY_ID[specification["lab"]]
        strategy = lab.strategies[specification["strategy"]]
        emit = lambda name, detail: _send({"stage": name, "detail": detail})
        ctx = Context(Path(specification["root"]), specification["online"], emit)
        ctx.stage("formalizzazione", f"{lab.title} · {specification['strategy']}")
        result = strategy(ctx, specification["payload"])
        _result(result.data())
        return 0
    except Exception as error:
        import traceback
        traceback.print_exc()
        _send({"error": f"{type(error).__name__}: {error}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
