# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Research on new structured statements, reusable by every lab."""
from pathlib import Path
import tempfile

from .logic import solve, witness_valid
from .model import Claim, Expr, Kind, Statement, digest
from .plugin import Context, Result, Work
from .verification import verify_lean


def lean_int_type(statement: Statement) -> str:
    if not statement.universal or any(item.sort != "int" for item in statement.binders):
        raise ValueError("Lean automatico supporta quantificatori universali interi")
    names = {item.name: f"v{index}" for index, item in enumerate(statement.binders)}
    infix = {"and": " ∧ ", "or": " ∨ ", "eq": " = ", "lt": " < ", "le": " ≤ ",
             "gt": " > ", "ge": " ≥ ", "add": " + ", "sub": " - ", "mul": " * "}

    def emit(expr: Expr) -> str:
        op, args = expr.op, expr.args
        if op == "num":
            value = int(args[0])
            return f"({value} : Int)"
        if op == "var":
            return names[args[0]]
        if op in ("true", "false"):
            return "True" if op == "true" else "False"
        if op == "not":
            return f"(¬ {emit(args[0])})"
        if op in infix:
            if op == "mul" and all(arg.op != "num" for arg in args):
                raise ValueError("moltiplicazione non lineare fuori dal frammento")
            return "(" + infix[op].join(emit(arg) for arg in args) + ")"
        raise ValueError(f"operatore Lean non supportato: {op}")

    quantifiers = "∀ " + " ".join(f"({name} : Int)" for name in names.values()) + ", " if names else ""
    return quantifiers + f"{emit(statement.scope)} → {emit(statement.conclusion)}"


def audit_statement(context: Context, lab: str, payload: dict) -> Result:
    statement = Statement.read(payload["statement"])
    title = payload["title"]
    key = digest([lab, statement.fingerprint()])[:20]
    dependencies = (payload["parent"],) if payload.get("parent") else ()
    context.stage("ricerca", "Ricerca SMT e controllo razionale di un eventuale testimone")
    smt = solve(statement)
    if smt["status"] == "counterexample" and witness_valid(statement, smt["witness"]):
        claim = Claim(f"generic.refutation.{key}", lab, title, statement, Kind.COUNTEREXAMPLE,
                      dependencies=dependencies,
                      evidence={"verified": True, "witness": smt["witness"],
                                "independent": "SMT e valutazione in ℚ", "solver": smt})
        return Result("refuted", title, {"smt": smt}, (claim,), proof_complete=True, independent=True)
    lean = None
    if smt["status"] == "unsat":
        try:
            expected = lean_int_type(statement)
        except ValueError as error:
            lean = {"valid": False, "reason": str(error)}
        else:
            context.stage("verifica", "Controllo indipendente con il kernel Lean")
            tools = context.root / ".tools" / "lean" / "bin"
            with tempfile.TemporaryDirectory(prefix="dp-generated-") as directory:
                file = Path(directory) / "Generated.lean"
                source = "import Lean\n\ntheorem dp_goal : " + expected + " := by omega\n"
                file.write_text(source, encoding="utf-8")
                lean = verify_lean(tools / "lean", file, {"dp_goal": expected}, cwd=context.root)
                lean["generated_source"] = source
        if lean["valid"]:
            claim = Claim(f"generic.proof.{key}", lab, title, statement, Kind.FORMAL,
                          dependencies=dependencies,
                          evidence={"lean": lean, "smt": smt, "usable_for_coverage": True})
            followups = []
            if payload.get("relax"):
                for index in range(len(statement.hypotheses)):
                    variant = Statement(statement.binders, statement.domain,
                                        statement.hypotheses[:index] + statement.hypotheses[index+1:],
                                        statement.conclusion)
                    followups.append(Work("@statement", {"title": title + f" · ipotesi {index + 1} rimossa",
                                          "statement": variant.data(), "parent": claim.id}, 45, 12))
            return Result("reproduced", title, {"smt": smt, "lean": lean}, (claim,), tuple(followups),
                          proof_complete=True, independent=True)
    return Result("inconclusive", title, {"smt": smt, "lean": lean,
                  "reason": "risultato senza testimone verificato o prova indipendente"})
