# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Exact and certified verification adapters, with reproducible artifacts."""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from pathlib import Path
import re
import subprocess

from flint import arb, ctx
import sympy as sp

from .model import Expr


def ball_data(value: arb, precision: int) -> dict:
    if not value.is_finite():
        raise ValueError("non-finite Arb interval")
    with ctx.workprec(precision):
        lower, upper = value.lower().man_exp(), value.upper().man_exp()
        return {"engine": "FLINT/Arb", "precision_bits": precision, "ball": str(value),
                "absolute_radius": str(value.rad()),
                "lower_dyadic": [str(lower[0]), int(lower[1])],
                "upper_dyadic": [str(upper[0]), int(upper[1])]}


Polynomial = dict[tuple[int, ...], Fraction]


def _sum(left: Polynomial, right: Polynomial, sign: int = 1) -> Polynomial:
    total = left.copy()
    for powers, coefficient in right.items():
        total[powers] = total.get(powers, Fraction()) + sign * coefficient
    return {powers: coefficient for powers, coefficient in total.items() if coefficient}


def _mul(left: Polynomial, right: Polynomial) -> Polynomial:
    total: Polynomial = {}
    for (left_powers, a), (right_powers, b) in product(left.items(), right.items()):
        powers = tuple(x + y for x, y in zip(left_powers, right_powers))
        total[powers] = total.get(powers, Fraction()) + a * b
    return {powers: coefficient for powers, coefficient in total.items() if coefficient}


def rational_identity(left: Expr, right: Expr, variables: tuple[str, ...]) -> dict:
    """Check an identity in Q(variables) using SymPy and an independent sparse polynomial normalizer.

    This certifies equality where all input denominators are nonzero. It does
    not assert that the hypotheses of a geometric or physical model imply that.
    """
    if len(set(variables)) != len(variables):
        raise ValueError("duplicate variables")
    zero = (0,) * len(variables)
    one = {zero: Fraction(1)}
    symbolic = {name: sp.Symbol(name) for name in variables}
    denominators: set[Expr] = set()

    def convert(term: Expr) -> tuple[sp.Expr, Polynomial, Polynomial]:
        op, args = term.op, term.args
        if op == "num":
            value = Fraction(args[0])
            return sp.Rational(value.numerator, value.denominator), ({zero: value} if value else {}), one
        if op == "var":
            index = variables.index(args[0])
            return symbolic[args[0]], {tuple(int(i == index) for i in range(len(variables))): Fraction(1)}, one
        if op not in ("add", "sub", "mul", "div", "pow") or len(args) != 2:
            raise ValueError("non-rational term")
        sa, an, ad = convert(args[0])
        if op == "pow":
            if args[1].op != "num":
                raise ValueError("nonconstant exponent")
            exponent = Fraction(args[1].args[0])
            if exponent.denominator != 1 or not 0 <= exponent <= 64:
                raise ValueError("unsupported exponent")
            numerator, denominator = one, one
            for _ in range(int(exponent)):
                numerator, denominator = _mul(numerator, an), _mul(denominator, ad)
            return sa ** int(exponent), numerator, denominator
        sb, bn, bd = convert(args[1])
        if op == "div":
            if not bn:
                raise ValueError("identically zero denominator")
            if args[1].op != "num":
                denominators.add(args[1])
            return sa / sb, _mul(an, bd), _mul(ad, bn)
        if op == "mul":
            return sa * sb, _mul(an, bn), _mul(ad, bd)
        sign = 1 if op == "add" else -1
        return sa + sign * sb, _sum(_mul(an, bd), _mul(ad, bn), sign), _mul(ad, bd)

    sa, an, ad = convert(left)
    sb, bn, bd = convert(right)
    remainder = _sum(_mul(an, bd), _mul(bn, ad), -1)
    sympy_zero = sp.cancel(sa - sb) == 0
    return {"valid": sympy_zero and not remainder, "primary": "SymPy cancel",
            "independent": "normalizzazione polinomiale sparsa su ℚ",
            "variables": list(variables), "left": left.data(), "right": right.data(),
            "denominators_nonzero": sorted(map(str, denominators)),
            "remainder": [[list(powers), str(value)] for powers, value in sorted(remainder.items())],
            "sympy_zero": sympy_zero, "independent_zero": not remainder}


def verify_lean(lean: Path, proof: Path, expectations: dict[str, str],
                *, cwd: Path, timeout: float = 15.0, lake: Path | None = None) -> dict:
    """Check project-trusted Lean source against a separately specified declaration type."""
    import os
    import tempfile
    from hashlib import sha256

    if not lean.is_file():
        return {"valid": False, "status": "unavailable", "reason": "toolchain Lean assente"}
    if not expectations or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name) for name in expectations):
        raise ValueError("invalid Lean declarations")
    source = proof.read_text(encoding="utf-8")
    if re.search(r"\b(sorry|admit|axiom|unsafe|native_decide|implemented_by|run_cmd|elab|macro)\b|set_option|#eval",
                 source):
        raise ValueError("the Lean source contains forbidden constructs")
    checkers = []
    for index, (name, expected_type) in enumerate(expectations.items()):
        checkers.extend([f"theorem dp_check_{index} : {expected_type} := {name}",
                         f"#print axioms dp_check_{index}"])
    with tempfile.TemporaryDirectory(prefix="dp-lean-") as temp:
        check = Path(temp) / "Verified.lean"
        check.write_text(source + "\n\n" + "\n".join(checkers) + "\n", encoding="utf-8")
        command = [str(lean)] if lake is None else [str(lake), "env", str(lean)]
        env = dict(os.environ)
        env["PATH"] = str(lean.parent) + os.pathsep + env.get("PATH", "")
        try:
            result = subprocess.run([*command, "--trust=0", str(check)], cwd=cwd, env=env,
                                    capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"valid": False, "status": "timeout", "reason": "limite di verifica Lean"}
    output = result.stdout + result.stderr
    allowed = {"propext", "Classical.choice", "Quot.sound"}
    audited = {}
    for index, name in enumerate(expectations):
        target = f"'dp_check_{index}'"
        line = next((line for line in output.splitlines() if line.startswith(target)), "")
        match = re.search(r"depends on axioms: \[([^\]]*)\]", line)
        if match:
            audited[name] = {item.strip() for item in match.group(1).split(",") if item.strip()}
        elif "does not depend on any axioms" in line:
            audited[name] = set()
    valid = (result.returncode == 0 and set(audited) == set(expectations)
             and all(values <= allowed for values in audited.values()))
    version = subprocess.run([str(lean), "--version"], capture_output=True, text=True, timeout=3, check=False)
    return {"valid": valid, "status": "checked" if valid else "rejected", "method": "Lean kernel",
            "version": version.stdout.strip(), "source_sha256": sha256(source.encode()).hexdigest(),
            "source": proof.name, "expected_types": expectations,
            "axioms": {key: sorted(values) for key, values in audited.items()}, "output": output[-5000:]}
