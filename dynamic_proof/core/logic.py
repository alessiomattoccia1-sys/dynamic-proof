# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Constraint solving, independently validated witnesses, and coverage deductions."""
from dataclasses import dataclass
from fractions import Fraction
from math import lcm
import operator

import z3

from .model import Claim, Expr, FALSE, Kind, Statement, TRUE, conjunction, e, negate, num, var


ARITHMETIC = {"eq": operator.eq, "lt": operator.lt, "le": operator.le, "gt": operator.gt,
              "ge": operator.ge, "add": operator.add, "sub": operator.sub,
              "mul": operator.mul, "div": operator.truediv, "pow": operator.pow}


def evaluate(expr: Expr, values: dict[str, Fraction]) -> bool | Fraction:
    op, args = expr.op, expr.args
    if op == "num":
        return Fraction(args[0])
    if op == "var":
        return values[args[0]]
    if op == "true":
        return True
    if op == "false":
        return False
    if op == "opaque":
        raise ValueError("external formula has no executable evaluator")
    if op == "and":
        return all(evaluate(arg, values) for arg in args)
    if op == "or":
        return any(evaluate(arg, values) for arg in args)
    if op == "not":
        return not evaluate(args[0], values)
    left, right = (evaluate(arg, values) for arg in args)
    if op == "divides":
        return right == 0 if left == 0 else right % left == 0
    return ARITHMETIC[op](left, int(right) if op == "pow" else right)


def witness_valid(statement: Statement, witness: dict[str, str | int]) -> bool:
    if not statement.universal or set(witness) != {binder.name for binder in statement.binders}:
        return False
    try:
        values = {name: Fraction(value) for name, value in witness.items()}
        if any(b.sort == "symbolic" or (b.sort == "int" and values[b.name].denominator != 1)
               for b in statement.binders):
            return False
        return evaluate(statement.scope, values) is True and evaluate(statement.conclusion, values) is False
    except (ValueError, KeyError, ZeroDivisionError, TypeError):
        return False


def z3_expression(expr: Expr, symbols: dict):
    op, args = expr.op, expr.args
    if op == "var":
        return symbols[args[0]]
    if op == "num":
        value = Fraction(args[0])
        return z3.IntVal(value.numerator) if value.denominator == 1 else z3.RealVal(str(value))
    if op in ("true", "false"):
        return z3.BoolVal(op == "true")
    if op == "opaque":
        raise ValueError("external formula has no SMT translation")
    terms = [z3_expression(arg, symbols) for arg in args]
    if op in {"and", "or", "not"}:
        return {"and": z3.And, "or": z3.Or, "not": z3.Not}[op](*terms)
    left, right = terms
    if op == "divides":
        return z3.If(left == 0, right == 0, right % left == 0)
    if op == "div":
        # SMT gives division by zero a total interpretation. Accept only known
        # nonzero literal divisors so an undefined term cannot prove a claim.
        if args[1].op != "num" or Fraction(args[1].args[0]) == 0:
            raise ValueError("SMT division requires a nonzero constant denominator")
        if z3.is_int(left):
            left = z3.ToReal(left)
    if op == "pow":
        exponent = int(args[1].args[0])
        term = z3.IntVal(1)
        for _ in range(exponent):
            term = term * left
        return term
    return ARITHMETIC[op](left, right)


def solve(statement: Statement, timeout_ms: int = 1200) -> dict:
    """Check for a countermodel. SAT is replayed with exact arithmetic."""
    if not statement.universal or any(b.sort == "symbolic" for b in statement.binders):
        return {"status": "unsupported", "method": "z3"}
    symbols = {b.name: (z3.Int if b.sort == "int" else z3.Real)(b.name) for b in statement.binders}
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    try:
        solver.add(z3_expression(statement.scope, symbols), z3.Not(z3_expression(statement.conclusion, symbols)))
    except ValueError as error:
        return {"status": "unsupported", "method": "z3", "reason": str(error)}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        witness = {key: str(model.eval(symbol, model_completion=True)) for key, symbol in symbols.items()}
        if not witness_valid(statement, witness):
            return {"status": "unknown", "method": "z3", "reason": "testimone non riproducibile in ℚ"}
        return {"status": "counterexample", "method": "z3 + aritmetica razionale indipendente",
                "witness": witness}
    if result == z3.unsat:
        return {"status": "unsat", "method": "z3", "smt2": solver.to_smt2()}
    return {"status": "unknown", "method": "z3", "reason": solver.reason_unknown()}


@dataclass(frozen=True)
class Coverage:
    residual: Statement
    dependencies: tuple[str, ...]
    steps: tuple[dict, ...]

    def data(self) -> dict:
        return {"residual": self.residual.data(), "display": self.residual.display(),
                "dependencies": list(self.dependencies), "steps": list(self.steps)}


def _conjuncts(expr: Expr) -> tuple[Expr, ...]:
    return expr.args if expr.op == "and" else (expr,)


def _merge_divisors(parts: list[Expr]) -> tuple[list[Expr], list[dict]]:
    groups: dict[Expr, list[int]] = {}
    remaining = []
    for part in parts:
        if part.op == "divides" and part.args[0].op == "num":
            divisor = Fraction(part.args[0].args[0])
            if divisor.denominator == 1 and divisor > 0:
                groups.setdefault(part.args[1], []).append(int(divisor))
                continue
        remaining.append(part)
    steps = []
    for term, divisors in groups.items():
        merged = lcm(*divisors)
        remaining.append(e("divides", num(merged), term))
        if len(divisors) > 1:
            steps.append({"rule": "lcm_divisibility", "divisors": sorted(divisors), "lcm": merged,
                          "lcm_text": str(merged),
                          "term": str(term)})
    return remaining, steps


def usable_for_coverage(claim: Claim) -> bool:
    evidence = claim.evidence or {}
    if claim.kind in {Kind.FORMAL, Kind.EXACT, Kind.LITERATURE, Kind.CONDITIONAL}:
        return evidence.get("usable_for_coverage") is True
    if claim.kind != Kind.CERTIFIED or not (evidence.get("verified") and evidence.get("exhaustive")):
        return False
    statement = claim.statement
    interval = evidence.get("interval")
    if not (isinstance(interval, list) and len(interval) == 2 and all(type(n) is int for n in interval)
            and interval[0] <= interval[1] and evidence.get("count") == interval[1] - interval[0] + 1
            and evidence.get("precision_bits") and statement.universal and len(statement.binders) == 1
            and statement.binders[0].sort == "int" and not statement.hypotheses):
        return False
    variable = var(statement.binders[0].name)
    expected = {e("ge", variable, num(interval[0])), e("le", variable, num(interval[1]))}
    return set(_conjuncts(statement.domain)) == expected


def residual(target: Statement, proven: list[Claim]) -> Coverage:
    """Restrict a universal claim by the actual guarded domains of admissible results."""
    if not target.universal:
        raise ValueError("coverage requires a universal target")
    target_parts = set(_conjuncts(target.scope))
    parts = []
    steps = []
    dependencies = []
    for claim in proven:
        statement = claim.statement
        if not usable_for_coverage(claim):
            raise ValueError(f"{claim.id}: evidence is incompatible with reduction")
        if statement.binders != target.binders or statement.conclusion != target.conclusion:
            raise ValueError(f"{claim.id}: incompatible conclusion or quantifier domain")
        relative_scope = conjunction(*(item for item in _conjuncts(statement.scope) if item not in target_parts))
        excluded = negate(relative_scope)
        parts.extend(_conjuncts(excluded))
        dependencies.append(claim.id)
        steps.append({"rule": "subtract_proven_scope", "claim": claim.id, "scope": str(statement.scope),
                      "remaining_condition": str(excluded)})
    parts, arithmetic_steps = _merge_divisors(parts)
    simplified = conjunction(*parts)
    new_hypotheses = target.hypotheses if simplified == TRUE else (*target.hypotheses, simplified)
    return Coverage(Statement(target.binders, target.domain, new_hypotheses, target.conclusion),
                    tuple(dependencies), tuple(steps + arithmetic_steps))


def deduce(target: Statement, premises: list[Claim], timeout_ms: int = 1200) -> dict:
    """Prove a universal consequence relative to the supplied guarded premises."""
    eligible = {Kind.FORMAL, Kind.EXACT, Kind.LITERATURE, Kind.CONDITIONAL}
    if not premises or any(claim.kind not in eligible or not (claim.evidence or {}).get("usable_for_coverage")
                           or claim.statement.binders != target.binders for claim in premises):
        raise ValueError("premise lacks sufficient evidence or has incompatible quantifiers")
    if not target.universal or any(b.sort == "symbolic" for b in target.binders):
        raise ValueError("deduction is outside the universal SMT fragment")
    symbols = {b.name: (z3.Int if b.sort == "int" else z3.Real)(b.name) for b in target.binders}
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    for premise in premises:
        statement = premise.statement
        solver.add(z3.Implies(z3_expression(statement.scope, symbols),
                              z3_expression(statement.conclusion, symbols)))
    # Detect inconsistent premise sets rather than certify an arbitrary result.
    if solver.check() != z3.sat:
        return {"status": "inconsistent_or_unknown", "dependencies": [claim.id for claim in premises]}
    solver.push()
    solver.add(z3_expression(target.scope, symbols))
    if solver.check() != z3.sat:
        return {"status": "incompatible_scope", "dependencies": [claim.id for claim in premises]}
    solver.add(z3.Not(z3_expression(target.conclusion, symbols)))
    result = solver.check()
    return {"status": "conditional" if result == z3.unsat else str(result),
            "dependencies": [claim.id for claim in premises], "smt2": solver.to_smt2(),
            "rule": "conseguenza logica di premesse con guardie"}
