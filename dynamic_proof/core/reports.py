# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Generate durable, human-readable research reports after committed attempts."""
from datetime import datetime, timezone
import json
import re


def _save(base, suffix, text):
    temporary = base.with_suffix(suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(base.with_suffix(suffix))


def _paragraphs(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [key + " · " + (item if isinstance(item, str) else json.dumps(item, ensure_ascii=False))
                for key, item in value.items()]
    if isinstance(value, (tuple, list)) and all(isinstance(part, str) for part in value):
        return list(value)
    if not value:
        return []
    return [json.dumps(value, ensure_ascii=False)]


def _escape_tex(value):
    substitutions = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$",
                     "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "^": r"\textasciicircum{}",
                     "~": r"\textasciitilde{}", "Σ": r"\(\sum\)", "ℤ": r"\(\mathbb Z\)",
                     "ℂ": r"\(\mathbb C\)", "ℕ": r"\(\mathbb N\)", "≠": r"\(\ne\)", "≤": r"\(\le\)",
                     "≥": r"\(\ge\)", "⇒": r"\(\Rightarrow\)", "⇔": r"\(\Leftrightarrow\)",
                     "∀": r"\(\forall\)", "∃": r"\(\exists\)", "∈": r"\(\in\)", "→": r"\(\to\)",
                     "↦": r"\(\mapsto\)", "∣": r"\(\mid\)", "−": r"\(-\)", "×": r"\(\times\)",
                     "ᵢ": r"\({}_i\)", "ⱼ": r"\({}_j\)", "ₙ": r"\({}_n\)", "ⁿ": r"\({}^n\)",
                     "σ": r"\(\sigma\)", "±": r"\(\pm\)"}
    return "".join(substitutions.get(char, char) for char in value)


def _tex_paragraph(value):
    fragments = re.split(r"(https://[A-Za-z0-9./_%+?=&:#~-]+|\b[0-9a-f]{40,64}\b)", value)
    rendered = []
    for index, fragment in enumerate(fragments):
        if index % 2 == 0:
            rendered.append(_escape_tex(fragment))
        elif fragment.startswith("https://"):
            rendered.append(r"\url{" + fragment + "}")
        else:
            groups = (fragment[i:i + 8] for i in range(0, len(fragment), 8))
            rendered.append(r"\texttt{" + r"\allowbreak{}".join(groups) + "}")
    return "".join(rendered)


def _draft(base, title, sections):
    text = [r"\documentclass[11pt]{article}", r"\usepackage{amsmath,amssymb,url}",
            r"\setlength{\emergencystretch}{3em}", r"\begin{document}",
            r"\title{" + _escape_tex(title) + "}", r"\author{Alessio Mattoccia}",
            r"\date{Bozza tecnica per revisione scientifica}", r"\maketitle"]
    for heading, value in sections.items():
        paragraphs = _paragraphs(value)
        if paragraphs:
            text.extend([r"\section*{" + _escape_tex(heading) + "}", "",
                         *(_tex_paragraph(paragraph) + "\n" for paragraph in paragraphs)])
    text.append(r"\end{document}")
    _save(base, ".tex", "\n".join(text) + "\n")


def write_report(directory, job, result, stats, assessment, artifact):
    target = directory / "reports"
    target.mkdir(exist_ok=True, mode=0o700)
    base = target / f"{job['attempt_id']:06d}"
    data = {"attempt": job["attempt_id"], "lab": job["lab"], "strategy": job["strategy"],
            "status": result["status"], "artifact": artifact, "finished": datetime.now(timezone.utc).isoformat(),
            "resources": stats, "result": result, "novelty": assessment}
    _save(base, ".json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")

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
                     "Ipotesi · " + (" · ".join(display["hypotheses"]) or "nessuna aggiuntiva"),
                     "Fonti nel registro · " + (", ".join(claim["sources"]) or "—"), ""])
    if reason := result.get("detail", {}).get("reason"):
        text.extend(["## Esito del tentativo", "", reason, ""])
    if dossier := result.get("detail", {}).get("dossier"):
        sections = dict(dossier)
        if assessment:
            sections["Valutazione della novità"] = assessment["meaning"]
        sections["Materiale supplementare"] = f"Rapporto {base.name}.json e artefatto {artifact} nel registro."
        for heading, value in sections.items():
            if paragraphs := _paragraphs(value):
                text.extend([f"## {heading}", "", "\n\n".join(paragraphs), ""])
        if result.get("substantive") and result.get("proof_complete"):
            _draft(base, result["title"], sections)
    else:
        text.extend(["## Riproducibilità", "", "Il file JSON con lo stesso numero conserva input scientifici, "
                     "verifiche, limiti ed evidenze. L’artefatto con lo stesso hash è nel registro SQLite.", ""])
    _save(base, ".md", "\n".join(text))
