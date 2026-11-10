# SPDX-License-Identifier: Apache-2.0
"""Generate durable, human-readable research reports after committed attempts."""
from datetime import datetime, timezone
import json


def write_report(directory, job, result, stats, assessment, artifact):
    target = directory / "reports"
    target.mkdir(exist_ok=True, mode=0o700)
    base = target / f"{job['attempt_id']:06d}"
    data = {"attempt": job["attempt_id"], "lab": job["lab"], "strategy": job["strategy"],
            "status": result["status"], "artifact": artifact, "finished": datetime.now(timezone.utc).isoformat(),
            "resources": stats, "result": result, "novelty": assessment}
    temporary = base.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(base.with_suffix(".json"))

    text = [f"# {result['title']}", "",
            f"Laboratorio · {job['lab']} | Tentativo · {job['attempt_id']} | Esito · {result['status']}", "",
            f"Artefatto · {artifact}", ""]
    if assessment:
        text.extend([f"Novità · {assessment['meaning']}", ""])
    for claim in result.get("claims", []):
        display = claim["display"]
        text.extend([f"## {claim['title']}", "", f"Classe di evidenza · {claim['kind']}", "",
                     display["conclusion"], "",
                     "Dominio · " + display["domain"],
                     "Ipotesi · " + ("; ".join(display["hypotheses"]) or "nessuna aggiuntiva"),
                     "Fonti nel registro · " + (", ".join(claim["sources"]) or "—"), ""])
    if reason := result.get("detail", {}).get("reason"):
        text.extend(["## Esito del tentativo", "", reason, ""])
    text.extend(["## Riproducibilità", "", "Il file JSON con lo stesso numero conserva input scientifici, "
                 "verifiche, limiti ed evidenze. L’artefatto con lo stesso hash è nel registro SQLite.", ""])
    temporary = base.with_suffix(".md.tmp")
    temporary.write_text("\n".join(text), encoding="utf-8")
    temporary.replace(base.with_suffix(".md"))
