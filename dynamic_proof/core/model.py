# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Immutable statements and a typed, serializable fragment for executable mathematics."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from hashlib import sha256
import json
import re
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return sha256(canonical(value).encode()).hexdigest()


class Kind(StrEnum):
    FORMAL = "formal"
    EXACT = "exact"
    LITERATURE = "literature"
    CONDITIONAL = "conditional"
    CERTIFIED = "certified_numeric"
    EXPLORATORY = "exploratory"
    CONJECTURE = "conjecture"
    COUNTEREXAMPLE = "counterexample"
    ORIGINAL = "original_candidate"


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple[Expr | str, ...]

    def data(self) -> list:
        return [self.op, *(arg.data() if isinstance(arg, Expr) else arg for arg in self.args)]

    @classmethod
    def read(cls, value: list) -> Expr:
        if not isinstance(value, list) or not value or not isinstance(value[0], str):
            raise ValueError("espressione non valida")
        return cls(value[0], tuple(cls.read(x) if isinstance(x, list) else x for x in value[1:]))

    def __str__(self) -> str:
        op, args = self.op, self.args
        if op in ("var", "num", "opaque"):
            return str(args[0])
        if op in ("true", "false"):
            return "vero" if op == "true" else "falso"
        if op == "not":
            return f"¬({args[0]})"
        if op == "divides":
            return f"{args[0]} ∣ {args[1]}"
        infix = {"and": "∧", "or": "∨", "eq": "=", "lt": "<", "le": "≤",
                 "gt": ">", "ge": "≥", "add": "+", "sub": "−", "mul": "·", "div": "/", "pow": "^"}
        return "(" + f" {infix[op]} ".join(map(str, args)) + ")"


def e(op: str, *args: Expr | str) -> Expr:
    return Expr(op, args)


TRUE = e("true")
FALSE = e("false")


def var(name: str) -> Expr:
    return e("var", name)


def num(value: int | str | Fraction) -> Expr:
    return e("num", str(Fraction(value)))


def opaque(formula: str) -> Expr:
    return e("opaque", formula)


def logic(op: str, *values: Expr) -> Expr:
    """Flatten, deduplicate and order Boolean operands without assuming facts."""
    identity, zero = (TRUE, FALSE) if op == "and" else (FALSE, TRUE)
    parts: set[Expr] = set()
    for value in values:
        if value == zero:
            return zero
        if value == identity:
            continue
        parts.update(value.args if value.op == op else (value,))
    if not parts:
        return identity
    ordered = sorted(parts, key=lambda part: canonical(part.data()))
    return ordered[0] if len(ordered) == 1 else e(op, *ordered)


def conjunction(*values: Expr) -> Expr:
    return logic("and", *values)


def disjunction(*values: Expr) -> Expr:
    return logic("or", *values)


def negate(value: Expr) -> Expr:
    if value == TRUE:
        return FALSE
    if value == FALSE:
        return TRUE
    if value.op == "not":
        return value.args[0]
    if value.op == "and":
        return disjunction(*(negate(arg) for arg in value.args))
    if value.op == "or":
        return conjunction(*(negate(arg) for arg in value.args))
    return e("not", value)


def _type_of(value: Expr, names: dict[str, str]) -> str:
    op, args = value.op, value.args
    if op in ("true", "false") and not args:
        return "bool"
    if op == "opaque" and len(args) == 1 and isinstance(args[0], str) and args[0].strip():
        return "bool"
    if op == "num" and len(args) == 1 and isinstance(args[0], str):
        return "int" if Fraction(args[0]).denominator == 1 else "real"
    if op == "var" and len(args) == 1 and isinstance(args[0], str) and args[0] in names:
        return names[args[0]]
    if any(not isinstance(arg, Expr) for arg in args):
        raise ValueError(f"argomenti non validi per {op}")
    types = [_type_of(arg, names) for arg in args]
    if op in ("and", "or", "not") and types and set(types) == {"bool"}:
        if op != "not" or len(types) == 1:
            return "bool"
    numeric = set(types) <= {"int", "real"}
    if op in ("eq", "lt", "le", "gt", "ge") and len(types) == 2 and numeric:
        return "bool"
    if op == "divides" and types == ["int", "int"]:
        return "bool"
    if op in ("add", "sub", "mul", "div", "pow") and len(types) == 2 and numeric:
        if op == "pow" and (args[1].op != "num" or types[1] != "int" or int(args[1].args[0]) not in range(65)):
            raise ValueError("sono supportate potenze intere da 0 a 64")
        return "real" if "real" in types or op == "div" else "int"
    raise ValueError(f"operatore o tipi incompatibili: {op} {types}")


@dataclass(frozen=True)
class Binder:
    name: str
    sort: str
    quantifier: str = "forall"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.name):
            raise ValueError("nome di variabile non valido")
        if self.sort not in {"int", "real", "symbolic"} or self.quantifier not in {"forall", "exists"}:
            raise ValueError("tipo o quantificatore non supportato")


@dataclass(frozen=True)
class Statement:
    binders: tuple[Binder, ...]
    domain: Expr
    hypotheses: tuple[Expr, ...]
    conclusion: Expr

    def __post_init__(self) -> None:
        names = {b.name: b.sort for b in self.binders}
        if len(names) != len(self.binders):
            raise ValueError("variabili duplicate")
        if any(_type_of(part, names) != "bool" for part in (self.domain, *self.hypotheses, self.conclusion)):
            raise ValueError("dominio, ipotesi e conclusione devono essere proposizioni")

    @property
    def scope(self) -> Expr:
        return conjunction(self.domain, *self.hypotheses)

    @property
    def universal(self) -> bool:
        return all(b.quantifier == "forall" for b in self.binders)

    def data(self) -> dict:
        return {
            "binders": [[b.name, b.sort, b.quantifier] for b in self.binders],
            "domain": self.domain.data(),
            "hypotheses": [h.data() for h in sorted(set(self.hypotheses), key=lambda h: canonical(h.data()))],
            "conclusion": self.conclusion.data(),
        }

    @classmethod
    def read(cls, data: dict) -> Statement:
        return cls(tuple(Binder(*b) for b in data["binders"]), Expr.read(data["domain"]),
                   tuple(Expr.read(h) for h in data["hypotheses"]), Expr.read(data["conclusion"]))

    def fingerprint(self) -> str:
        """Normalize the names of executable bound variables for deduplication."""
        names = {binder.name: f"x{index}" for index, binder in enumerate(self.binders)}
        data = self.data()

        def alpha(part: list) -> list:
            if part[0] == "var":
                return ["var", names[part[1]]]
            children = [alpha(child) if isinstance(child, list) else child for child in part[1:]]
            if part[0] in {"and", "or", "eq", "mul", "add"}:
                children.sort(key=canonical)
            return [part[0], *children]

        # Opaque mathematical text keeps its spelling. Alpha-equivalence is not
        # asserted for formulas whose binding has not been machine interpreted.
        data["binders"] = [[names[name], sort, quantifier] for name, sort, quantifier in data["binders"]]
        for key in ("domain", "conclusion"):
            data[key] = alpha(data[key])
        data["hypotheses"] = sorted([alpha(h) for h in data["hypotheses"]], key=canonical)
        return digest(data)

    def display(self) -> dict:
        return {
            "quantifiers": ", ".join(
                f"{'∀' if b.quantifier == 'forall' else '∃'} {b.name} ∈ "
                f"{ {'int': 'ℤ', 'real': 'ℝ', 'symbolic': 'dominio dichiarato'}[b.sort]}"
                for b in self.binders
            ),
            "domain": str(self.domain),
            "hypotheses": [str(h) for h in self.hypotheses],
            "conclusion": str(self.conclusion),
        }


def cited(formula: str, *hypotheses: str, domain: str | None = None) -> Statement:
    """Store an exact external formula. Its text is inert to all solvers."""
    return Statement((), opaque(domain) if domain else TRUE, tuple(map(opaque, hypotheses)), opaque(formula))


@dataclass(frozen=True)
class Claim:
    id: str
    lab: str
    title: str
    statement: Statement
    kind: Kind
    sources: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    evidence: dict | None = None

    def data(self) -> dict:
        return {"id": self.id, "lab": self.lab, "title": self.title, "statement": self.statement.data(),
                "display": self.statement.display(), "fingerprint": self.statement.fingerprint(),
                "kind": self.kind.value, "sources": list(self.sources), "dependencies": list(self.dependencies),
                "evidence": self.evidence or {}}

    @classmethod
    def read(cls, data: dict) -> Claim:
        return cls(data["id"], data["lab"], data["title"], Statement.read(data["statement"]),
                   Kind(data["kind"]), tuple(data["sources"]), tuple(data["dependencies"]), data["evidence"])
