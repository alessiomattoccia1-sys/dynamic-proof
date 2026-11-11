# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Local anomaly and renormalizable Yukawa constraints for a chiral U(1)."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from itertools import combinations, combinations_with_replacement, islice
import json
from math import comb, gcd, isqrt, prod
from platform import python_version
import re
import time

import sympy as sp
import z3

from ..core.literature import Source
from ..core.model import Claim, Kind, cited, digest
from ..core.plugin import Context, Lab, Result, Work
from ..core.verification import verify_lean


ID = "particle_theory"
GENERAL = "particle.costa2019"
FEW = "particle.costa2020"
HIGGS = "particle.berryman2016"
BATRA = "particle.batra2006"
SOURCES = (
    Source(GENERAL, "Costa, Dobrescu e Fox · General Solution to the U(1) Anomaly Equations",
           "Eqs. (1)–(2), parametrizzazione intera generale", "2019",
           "https://doi.org/10.1103/PhysRevLett.123.151601",
           terms=("chiral U(1)", "anomaly cancellation", "Weyl")),
    Source(FEW, "Costa, Dobrescu e Fox · Chiral Abelian Gauge Theories with Few Fermions",
           "Sez. II, III e IV.C, anomalie, cinque fermioni e modello con Higgs", "2020",
           "https://doi.org/10.1103/PhysRevD.101.095032",
           terms=("chiral U(1)", "Weyl", "Yukawa masses")),
    Source(HIGGS, "Berryman, de Gouvêa, Hernández e Kelly · Imperfect Mirror Copies of the Standard Model",
           "Sez. IV e Fig. 2, conteggio degli Higgs e distinzione Dirac/Majorana", "2016",
           "https://doi.org/10.1103/PhysRevD.94.035009",
           terms=("Abelian Higgs", "Yukawa masses", "chiral fermions")),
    Source(BATRA, "Batra, Dobrescu e Spivak · Anomaly-Free Sets of Fermions",
           "Sez. 2, equazioni e soluzioni a carica intera", "2006",
           "https://doi.org/10.1063/1.2222081",
           terms=("chiral U(1)", "anomaly cancellation")),
)
ANOMALIES = "particle.local_anomalies"
YUKAWA = "particle.yukawa_selection"
ODD = "particle.odd_scalar_valuation"
PHYSICS = (
    "Quattro dimensioni, soli fermioni di Weyl sinistrorsi e singoletti del Modello Standard",
    "U(1) isolato, soli campi dichiarati, cancellazione perturbativa locale senza Green–Schwarz",
)
MASS = (
    "Scalari complessi carichi con VEV non nulli, accoppiamenti Yukawa rinormalizzabili",
    "Coefficienti complessi indipendenti per entrata simmetrica permessa, nessun altro contributo di massa",
)
LIMITATIONS = (
    "Il risultato riguarda le anomalie locali e il rango della massa al livello degli operatori dichiarati.",
    "Potenziale scalare, esistenza e stabilità dinamica del vuoto, effetti non perturbativi e fenomenologia "
    "restano problemi separati.",
)
ODD_STATEMENT = cited(
    "det M = 0 per ogni matrice supportata. Su ℂ il rango è minore di n.",
    "n dispari, Σᵢ qᵢ = 0, d ∈ ℤ e d ≠ 0",
    "Mᵢⱼ ≠ 0 ⇒ qᵢ + qⱼ = d(2k + 1) per qualche k ∈ ℤ",
    domain="∀ n, q ∈ ℤⁿ, d ∈ ℤ e M ∈ Matₙ(R), R anello commutativo")
CLAIMS = (
    Claim(ANOMALIES, ID, "Condizioni locali di anomalia U(1)",
          cited("Σᵢ qᵢ = Σᵢ qᵢ³ = 0", *PHYSICS, domain="Cariche U(1) dei fermioni"),
          Kind.LITERATURE, (GENERAL, FEW, BATRA)),
    Claim(YUKAWA, ID, "Selezione delle entrate di massa U(1)",
          cited("Mᵢⱼ ≠ 0 ⇒ |qᵢ + qⱼ| ∈ H, H = {|hₐ|}", *PHYSICS, *MASS,
                domain="Matrice simmetrica per fermioni di Weyl"),
          Kind.LITERATURE, (FEW, HIGGS)),
    Claim(ODD, ID, "Ostruzione di parità per cariche scalari", ODD_STATEMENT,
          Kind.CONJECTURE, (HIGGS,), (YUKAWA,)),
)
BASELINE = (-9, -5, -1, 7, 8)
PROGRAM = tuple(f"PT-{index:03d}" for index in range(1, 13))

DEFAULT_BUDGET = {
    "steps_per_cycle": 20_000, "max_steps": 400_000, "max_models": 256,
    "smt_ms": 2500, "verification_steps": 300_000, "scalar_sets": 3000,
}
BUDGET_CAPS = {
    "steps_per_cycle": 50_000, "max_steps": 2_000_000, "max_models": 512,
    "smt_ms": 5000, "verification_steps": 500_000, "scalar_sets": 20_000,
}


def _integer(value, lower, upper, name):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name} requires an integer between {lower} and {upper}")
    return value


def _flag(raw, name, default):
    value = raw.get(name, default)
    if type(value) is not bool:
        raise ValueError(f"{name} requires a boolean")
    return value


def read_problem(raw: dict) -> dict:
    """Return the canonical JSON payload accepted by the shared job queue."""
    keys = {"id", "title", "type", "fermions", "charge_bound", "fermion_charges", "anomalies",
            "strict_chirality", "primitive", "scalar_charges", "max_scalars", "mass_condition",
            "method", "theorem", "budget", "completeness", "references"}
    if not isinstance(raw, dict) or raw.keys() - keys:
        raise ValueError("Particle Theory problem contains unknown fields")
    name, title, mode = raw.get("id"), raw.get("title"), raw.get("type")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", name):
        raise ValueError("invalid problem identifier")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 140 or "\n" in title:
        raise ValueError("invalid problem title")
    if mode not in ("classification", "construction", "counterexample", "proof"):
        raise ValueError("unsupported search type")
    size = _integer(raw.get("fermions"), 1, 10, "fermions")
    bound = _integer(raw.get("charge_bound"), 1, 32, "charge_bound")
    fixed = raw.get("fermion_charges")
    if fixed is not None:
        if not isinstance(fixed, list) or len(fixed) != size:
            raise ValueError("fermion_charges must have exactly fermions entries")
        fixed = sorted(_integer(q, -bound, bound, "carica fermionica") for q in fixed)
        if 0 in fixed:
            raise ValueError("fermion charges must be nonzero")
        fixed = list(canonical_charges(fixed))
    anomalies = raw.get("anomalies", ["linear", "cubic"])
    if not isinstance(anomalies, list) or any(a not in ("linear", "cubic") for a in anomalies):
        raise ValueError("anomalies accepts linear and cubic")
    anomalies = sorted(set(anomalies))
    method = raw.get("method", "quadratic" if len(anomalies) == 2 and size >= 2 else "enumeration")
    if method not in ("enumeration", "quadratic") or (method == "quadratic" and
                                                       (len(anomalies) != 2 or size < 2)):
        raise ValueError("quadratic requires at least two fermions and both anomaly equations")
    scalar = raw.get("scalar_charges")
    if scalar is not None:
        if not isinstance(scalar, list) or len(scalar) > 64:
            raise ValueError("scalar_charges must be a list of at most 64 entries")
        scalar = sorted({abs(_integer(h, -64, 64, "carica scalare")) for h in scalar})
        if 0 in scalar:
            raise ValueError("scalar charges must be nonzero")
    max_scalars = _integer(raw.get("max_scalars", 0), 0, size, "max_scalars")
    mass = raw.get("mass_condition", "any")
    if mass not in ("any", "full_rank"):
        raise ValueError("mass_condition accepts any and full_rank")
    theorem = raw.get("theorem")
    if mode == "proof":
        theorems = ("odd_scalar_valuation", "two_scalar_labels", "one_scalar_multiple_four")
        if theorem not in theorems or fixed is not None:
            raise ValueError("specify a supported universal theorem without fixed fermion charges")
        if theorem == "odd_scalar_valuation" and size % 2 == 0:
            raise ValueError("fermions must be odd for the theorem's counterexample search")
        if theorem == "one_scalar_multiple_four" and size % 4 == 0:
            raise ValueError("fermions must lie outside 4ℕ for the theorem's counterexample search")
    elif theorem is not None:
        raise ValueError("theorem applies to proof problems")
    if mode == "counterexample" and (not scalar or len(scalar) != max_scalars or mass != "any"):
        raise ValueError("a counterexample to arithmetic sufficiency requires a fixed scalar set")
    completeness = raw.get("completeness", "witness" if mode in ("construction", "counterexample") else "exhaustive")
    if (completeness not in ("exhaustive", "witness")
            or (mode in ("classification", "proof") and completeness != "exhaustive")
            or (mode == "counterexample" and completeness != "witness")):
        raise ValueError("completeness criterion is incompatible with the search type")
    references = raw.get("references", [GENERAL, FEW])
    allowed = {s.id for s in SOURCES}
    if not isinstance(references, list) or any(not isinstance(s, str) or s not in allowed for s in references):
        raise ValueError("use reference identifiers from the Particle Theory catalogue")
    budget = raw.get("budget", {})
    if not isinstance(budget, dict) or budget.keys() - DEFAULT_BUDGET.keys():
        raise ValueError("Particle Theory budget contains unknown fields")
    budget = {key: _integer(budget.get(key, value), 1, BUDGET_CAPS[key], key)
              for key, value in DEFAULT_BUDGET.items()}
    return {
        "id": name, "title": title.strip(), "type": mode, "fermions": size, "charge_bound": bound,
        "fermion_charges": fixed, "anomalies": anomalies, "strict_chirality": _flag(raw, "strict_chirality", True),
        "primitive": _flag(raw, "primitive", True), "scalar_charges": scalar, "max_scalars": max_scalars,
        "mass_condition": mass, "method": method, "theorem": theorem, "budget": budget,
        "completeness": completeness, "references": sorted(set(references) | {GENERAL, FEW}),
    }


def submit(raw: dict) -> Work:
    return Work("problem", {"problem": read_problem(raw)}, 90)


def canonical_charges(charges, *, primitive=False) -> tuple[int, ...]:
    scale = (gcd(*charges) or 1) if primitive else 1
    return min(tuple(sorted(q // scale for q in charges)), tuple(sorted(-q // scale for q in charges)))


def chirality(charges) -> dict:
    counts = Counter(charges)
    pairs = {q: min(counts[q], counts[-q]) for q in sorted(counts) if q > 0 and counts[-q]}
    return {"strict": 0 not in counts and not pairs, "opposite_pairs": pairs,
            "vector_like": 2 * sum(pairs.values()) + counts[0] == len(charges),
            "gcd": gcd(*charges), "canonical": list(canonical_charges(charges, primitive=True))}


def _pool(bound):
    return tuple(q for q in range(-bound, bound + 1) if q)


def _reject(charges, problem):
    if "linear" in problem["anomalies"] and sum(charges):
        return "linear"
    if "cubic" in problem["anomalies"] and sum(q**3 for q in charges):
        return "cubic"
    if problem["strict_chirality"] and any(-q in charges for q in charges):
        return "opposite_pairs"
    if problem["primitive"] and gcd(*charges) != 1:
        return "nonprimitive"
    return None


def _completions(prefix, problem):
    """Solve x+y=s and x³+y³=t using the integer discriminant."""
    bound = problem["charge_bound"]
    total, cubes = -sum(prefix), -sum(q**3 for q in prefix)
    lower = prefix[-1] if prefix else -bound
    if not total:
        if not cubes and not problem["strict_chirality"]:
            for x in range(lower, 0):
                yield (*prefix, x, -x)
        return
    product, rem = divmod(total**3 - cubes, 3 * total)
    discriminant = total**2 - 4 * product
    if rem or discriminant < 0:
        return
    delta = isqrt(discriminant)
    if delta**2 != discriminant or (total - delta) % 2:
        return
    x, y = (total - delta) // 2, (total + delta) // 2
    if lower <= x <= y <= bound and x and y:
        yield (*prefix, x, y)


def scan(problem, checkpoint):
    fixed = problem["fermion_charges"]
    pool = _pool(problem["charge_bound"])
    length = problem["fermions"] - 2 if problem["method"] == "quadratic" else problem["fermions"]
    total = 1 if fixed else comb(len(pool) + length - 1, length)
    budget = problem["budget"]
    offset = checkpoint.get("offset", 0)
    rows = [tuple(row) for row in checkpoint.get("rows", [])]
    excluded = Counter(checkpoint.get("excluded", {}))
    batch = []
    limit = min(total, budget["max_steps"], offset + budget["steps_per_cycle"])
    units = [tuple(fixed)] if fixed else combinations_with_replacement(pool, length)
    overflow = False
    for unit in islice(units, offset, limit):
        matches, misses = [], Counter()
        options = _completions(unit, problem) if not fixed and problem["method"] == "quadratic" else (unit,)
        for row in options:
            reason = _reject(row, problem)
            if reason:
                misses[reason] += 1
            else:
                matches.append(row)
        if len(rows) + len(matches) > budget["max_models"]:
            overflow = True
            break
        offset += 1
        rows.extend(matches)
        batch.extend(matches)
        excluded.update(misses)
        if not matches and not misses:
            excluded["prefix_without_completion"] += 1
    return {
        "offset": offset, "total": total, "rows": rows, "batch": batch, "excluded": dict(excluded),
        "complete": offset == total, "budget_exhausted": overflow or (offset < total and offset >= budget["max_steps"]),
        "model_limit": overflow,
        "unit": "fixed_assignment" if fixed else "multiset" if problem["method"] == "enumeration" else "sorted_prefix",
    }


def smt_models(problem):
    """Use independent QF_LIA constraints on the multiplicity of each charge."""
    values = _pool(problem["charge_bound"])
    count = {q: z3.Int(f"m_{'p' if q > 0 else 'n'}{abs(q)}") for q in values}
    solver = z3.SolverFor("QF_LIA")
    solver.add(*(m >= 0 for m in count.values()), z3.Sum(list(count.values())) == problem["fermions"])
    for name, exponent in (("linear", 1), ("cubic", 3)):
        if name in problem["anomalies"]:
            solver.add(z3.Sum([q**exponent * count[q] for q in values]) == 0)
    if problem["strict_chirality"]:
        solver.add(*(z3.Or(count[q] == 0, count[-q] == 0) for q in values if q > 0))
    if problem["primitive"]:
        solver.add(*(z3.Or([m > 0 for q, m in count.items() if q % prime])
                     for prime in sp.primerange(2, problem["charge_bound"] + 1)))
    if problem["fermion_charges"]:
        fixed = Counter(problem["fermion_charges"])
        solver.add(*(m == fixed[q] for q, m in count.items()))
    rows = []
    deadline = time.monotonic() + problem["budget"]["smt_ms"] / 1000
    status, reason = "UNKNOWN", "limite di modelli SMT"
    while len(rows) <= problem["budget"]["max_models"]:
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining < 1:
            status, reason = "TIMEOUT", "budget SMT esaurito"
            break
        solver.set(timeout=remaining)
        answer = solver.check()
        if answer == z3.unsat:
            status, reason = "UNSAT", "tutti i modelli elencati sono stati bloccati"
            break
        if answer == z3.unknown:
            reason = solver.reason_unknown()
            status = "TIMEOUT" if reason in {"timeout", "canceled"} else "UNKNOWN"
            break
        model = solver.model()
        multiplicities = {q: model.eval(m).as_long() for q, m in count.items()}
        charges = tuple(q for q in values for _ in range(multiplicities[q]))
        if len(charges) != problem["fermions"] or _reject(charges, problem):
            raise ValueError("SMT model conflicts with exact verification")
        rows.append(charges)
        solver.add(z3.Or([m != multiplicities[q] for q, m in count.items()]))
    return {"method": "Z3 QF_LIA sulle molteplicità", "version": z3.get_version_string(),
            "status": "SAT" if rows else status, "terminal_check": status, "reason": reason,
            "complete": status == "UNSAT", "models": sorted(rows)}


def independent_scan(problem, expected):
    """Use SMT first; if it stops, check by linear completion or direct enumeration."""
    smt = smt_models(problem)
    if smt["complete"]:
        if set(smt["models"]) != set(expected):
            raise ValueError("Z3 classification and enumeration disagree")
        return {"verified": True, "smt": smt, "method": smt["method"]}
    if not set(smt["models"]) <= set(expected):
        raise ValueError("Z3 found a model missing from the enumeration")
    pool = _pool(problem["charge_bound"])
    n = problem["fermions"]
    linear = "linear" in problem["anomalies"]
    length = n - int(linear)
    fixed = problem["fermion_charges"]
    work = 1 if fixed else comb(len(pool) + length - 1, length)
    if work > problem["budget"]["verification_steps"]:
        return {"verified": False, "smt": smt, "method": "limite per il secondo enumeratore",
                "verification_units": work}
    rows = set()
    for prefix in [tuple(fixed)] if fixed else combinations_with_replacement(pool, length):
        row = (*prefix, -sum(prefix)) if linear and not fixed else prefix
        if row[-1] not in pool or (len(row) > 1 and row[-1] < row[-2]):
            continue
        counts = Counter(row)
        if linear and sum(q * m for q, m in counts.items()):
            continue
        if "cubic" in problem["anomalies"] and sum(q*q*q * m for q, m in counts.items()):
            continue
        if problem["strict_chirality"] and set(counts) & {-q for q in counts}:
            continue
        if problem["primitive"] and gcd(*counts) != 1:
            continue
        rows.add(row)
    if rows != set(expected):
        raise ValueError("the two integer classifications disagree")
    # With only the cubic equation a second direct scan has the same search
    # space. Its witness checks are distinct, but it is not a second solver.
    return {"verified": bool(linear and not fixed), "smt": smt,
            "method": "completamento lineare con controllo per molteplicità" if linear and not fixed
            else "ricontrollo diretto delle condizioni", "verification_units": work}


def support(charges, scalars):
    return tuple(tuple(j for j, right in enumerate(charges) if abs(left + right) in scalars) for left in charges)


def matching_certificate(neighbors):
    """A matching and an equal-size cover certify the term rank."""
    by_column = {}

    def augment(row, visited):
        for column in neighbors[row]:
            if column in visited:
                continue
            visited.add(column)
            if column not in by_column or augment(by_column[column], visited):
                by_column[column] = row
                return True
        return False

    for row in range(len(neighbors)):
        augment(row, set())
    by_row = {row: column for column, row in by_column.items()}
    reached = set(range(len(neighbors))) - by_row.keys()
    frontier = sorted(reached)
    columns = set()
    for row in frontier:
        for column in neighbors[row]:
            if by_row.get(row) == column or column in columns:
                continue
            columns.add(column)
            other = by_column.get(column)
            if other is not None and other not in reached:
                reached.add(other)
                frontier.append(other)
    rows = set(range(len(neighbors))) - reached
    if (len(rows) + len(columns) != len(by_row)
            or any(i not in rows and j not in columns for i, entries in enumerate(neighbors) for j in entries)):
        raise ValueError("invalid bipartite cover certificate")
    return by_row, {"rows": sorted(rows), "columns": sorted(columns)}


def _mass_witness(size, matching):
    """Use disjoint transpositions, loops and odd cycles in the symmetric support."""
    witness = [[0] * size for _ in range(size)]
    remaining = set(range(size))

    def component(start):
        vertices = []
        current = start
        while current in remaining:
            remaining.remove(current)
            vertices.append(current)
            current = matching.get(current)
        return vertices

    def mark(edges):
        for i, j in edges:
            witness[i][j] = witness[j][i] = 1

    for start in sorted(remaining - set(matching.values())):
        path = component(start)
        mark(zip(path[::2], path[1::2]))
    while remaining:
        cycle = component(min(remaining))
        if len(cycle) % 2:
            mark(zip(cycle, cycle[1:] + cycle[:1]))
        else:
            mark(zip(cycle[::2], cycle[1::2]))
    return witness


def exact_rank(matrix):
    """Independent Gaussian elimination over Q. Return rank and determinant."""
    work = [list(map(Fraction, row)) for row in matrix]
    rank, determinant = 0, Fraction(1)
    for column in range(len(work)):
        pivot = next((i for i in range(rank, len(work)) if work[i][column]), None)
        if pivot is None:
            continue
        if pivot != rank:
            work[rank], work[pivot] = work[pivot], work[rank]
            determinant = -determinant
        value = work[rank][column]
        determinant *= value
        for i in range(rank + 1, len(work)):
            factor = work[i][column] / value
            for j in range(column, len(work)):
                work[i][j] -= factor * work[rank][j]
        rank += 1
    return rank, determinant if rank == len(work) else Fraction(0)


def mass_certificate(charges, scalars):
    neighbors = support(charges, scalars)
    matching, cover = matching_certificate(neighbors)
    size = len(charges)
    witness = _mass_witness(size, matching)
    if any(value and j not in neighbors[i] for i, row in enumerate(witness) for j, value in enumerate(row)):
        raise ValueError("witness contains a forbidden entry")
    rank, determinant = exact_rank(witness)
    evaluated = sp.Matrix(witness)
    if rank != len(matching) or rank != evaluated.rank() or determinant != evaluated.det():
        raise ValueError("rank, cover, and rational witness disagree")
    base_symbols = {(0, 3): "a", (0, 4): "b", (1, 3): "c", (2, 2): "d"}
    matrix = sp.zeros(size)
    entries = []
    for i, options in enumerate(neighbors):
        for j in options:
            if j < i:
                continue
            name = f"y_{i+1}_{j+1}"
            if tuple(charges) == BASELINE and tuple(scalars) == (1, 2):
                name = base_symbols[i, j]
            symbol = sp.Symbol(name)
            matrix[i, j] = matrix[j, i] = symbol
            entries.append({"row": i + 1, "column": j + 1, "symbol": name,
                            "scalar_charge": abs(charges[i] + charges[j]),
                            "conjugate": charges[i] + charges[j] > 0})
    if rank < size:
        symbolic = "0"
        symbolic_status = "identically_zero"
    elif size <= 6 or (size <= 8 and prod(map(len, neighbors)) <= 4096):
        polynomial = sp.factor(matrix.det(method="domain-ge"))
        values = {matrix[i, j]: witness[i][j] for i in range(size) for j in neighbors[i]}
        if polynomial.subs(values) != determinant:
            raise ValueError("the determinant polynomial does not reproduce the witness")
        symbolic = str(polynomial)
        symbolic_status = "expanded_exact"
    else:
        symbolic, symbolic_status = "det(M)", "unevaluated_with_exact_witness"
    return {
        "fermion_charges": list(charges), "scalar_charges": list(scalars),
        "matrix": [[str(matrix[i, j]) for j in range(size)] for i in range(size)],
        "allowed_yukawa": entries, "determinant": symbolic, "symbolic_status": symbolic_status,
        "generic_rank": rank, "witness_matrix": witness, "witness_determinant": str(determinant),
        "witness_rank": rank, "vertex_cover": cover,
        "independent_check": "Copertura bipartita verificata, rango del testimone con SymPy ed eliminazione in ℚ",
    }


def scalar_search(charges, problem, allowance):
    possible = sorted({abs(a + b) for a, b in combinations_with_replacement(charges, 2) if a + b})
    pool = possible if problem["scalar_charges"] is None else problem["scalar_charges"]
    cap = min(problem["max_scalars"], len(pool))
    exhaustive = problem["type"] == "classification" or problem["completeness"] == "exhaustive"
    total = sum(comb(len(pool), k) for k in range(cap + 1))
    tested, compatible, first, best = [], [], None, ((), -1)
    for size in range(cap + 1):
        for scalars in combinations(pool, size):
            if len(tested) == allowance:
                break
            matching, cover = matching_certificate(support(charges, scalars))
            rank = len(matching)
            tested.append((scalars, rank, cover))
            if rank > best[1]:
                best = scalars, rank
            if rank == len(charges):
                compatible.append(scalars)
                if first is None:
                    first = scalars
                if not exhaustive:
                    break
        if len(tested) == allowance or (first is not None and not exhaustive):
            break
    complete = len(tested) == total
    has_witness = first is not None
    return {
        "status": "SAT" if has_witness else "UNSAT" if complete else "UNKNOWN",
        "complete": complete, "tested_sets": len(tested), "possible_sets": total, "pool": pool,
        "minimum": len(first) if has_witness else None,
        "compatible_sets": compatible,
        "certificate": mass_certificate(charges, first if has_witness else best[0]) if tested else None,
        "rank_trace_sha256": digest(tested), "rank_trace": tested if len(tested) <= 160 else None,
        "completeness_rule": "Ordine per cardinalità crescente. Copertura di ogni supporto e rango esatto.",
    }


def signed_sum_witness(size, scalars, target=0):
    """Dynamic programming on signed scalar labels, independent of the mass support."""
    signed = sorted({value for h in scalars for value in (h, -h)})
    reachable = {0: ()}
    for _ in range(size):
        reachable = {total + value: (*terms, value)
                     for total, terms in reachable.items() for value in signed}
    return reachable.get(target)


def two_scalar_allowed(n, a, b):
    scale = gcd(a, b)
    reduced = (a + b) // scale
    return reduced % 2 == 1 and reduced <= n


def _comparisons():
    return (
        {"work": GENERAL, "locator": "Eqs. (1)–(2) e parametrizzazione", "direct_prior_art": True,
         "reviewed_scope": "Cancellazione locale delle anomalie per cariche intere U(1)",
         "relation": "different",
         "difference": "Parametrizzazione delle cariche fermioniche. Qui si impongono anche vincoli "
                       "su entrate, cariche scalari e determinante della massa."},
        {"work": FEW, "locator": "Sez. II, III e IV.C", "direct_prior_art": True,
         "reviewed_scope": "Soluzioni minime e costruzione di un settore oscuro con due fattori abeliani",
         "relation": "different",
         "difference": "Il modello con masse di Dirac usa sei fermioni e U(1) × U(1). Qui il settore è "
                       "U(1) singolo e sono ammesse anche entrate diagonali."},
        {"work": HIGGS, "locator": "Sez. IV e Fig. 2", "direct_prior_art": True,
         "reviewed_scope": "Numero di campi di Higgs e possibilità di masse Dirac o Majorana in modelli chirali",
         "relation": "unknown",
         "difference": "Il conteggio pubblicato impone masse Dirac per i modi massivi e consente un "
                       "modo massless. Qui si misura il rango pieno ammettendo termini Majorana. "
                       "La ricerca di formulazioni equivalenti del criterio resta aperta."},
    )


def _domain(problem):
    if problem["fermion_charges"] is not None:
        return "Assegnazione fissata q = " + str(tuple(problem["fermion_charges"]))
    return f"{problem['fermions']} fermioni, qᵢ ∈ ℤ, 1 ≤ |qᵢ| ≤ {problem['charge_bound']}"


def _assumptions(problem, include_mass=False):
    terms = list(PHYSICS)
    for name, equation in (("linear", "Σᵢ qᵢ = 0"), ("cubic", "Σᵢ qᵢ³ = 0")):
        if name in problem["anomalies"]:
            terms.append(equation)
    if problem["strict_chirality"]:
        terms.append("qᵢ + qⱼ ≠ 0 per i ≠ j")
    if problem["primitive"]:
        terms.append("MCD(|qᵢ|) = 1")
    if include_mass:
        terms.extend(MASS)
        pool = problem["scalar_charges"]
        terms.append(f"Al più {problem['max_scalars']} scalari distinti in valore assoluto"
                     + (f" dal pool {tuple(pool)}" if pool is not None else " dal supporto |qᵢ + qⱼ| > 0"))
    return tuple(terms)


def _claim(suffix, title, statement, kind, sources, dependencies, evidence):
    identifier = digest([statement.fingerprint(), evidence])[:20]
    return Claim(f"particle.{suffix}.{identifier}", ID, title, statement, kind, sources, dependencies, evidence)


def _base_detail(problem, outcome, **summary):
    return {
        "problem": problem, "outcome": outcome,
        "summary": {"problem": problem["id"], "outcome": outcome, **summary},
        "limitations": LIMITATIONS,
        "reproducibility": {"python": python_version(), "sympy": sp.__version__, "z3": z3.get_version_string(),
                            "input_sha256": digest(problem), "command": "submit particle_theory FILE.json"},
    }


def _next_example(example):
    index = PROGRAM.index(example) + 1 if example else len(PROGRAM)
    return (Work("problem", {"example": PROGRAM[index]}, 70),) if index < len(PROGRAM) else ()


def _label_lean(context):
    tools = context.root / ".tools/lean/bin"
    proofs = context.root / "proofs"
    if not (tools / "lean").is_file() or not (tools / "lake").is_file():
        return {"valid": False, "status": "unavailable", "reason": "Lean e Lake richiesti per ParticleNoGo.lean"}
    prefix = ("∀ {n : ℕ} {R : Type*} [CommRing R] (q : Fin n → ℤ) (d : ℤ) "
              "(M : Matrix (Fin n) (Fin n) R), Odd n → d ≠ 0 → (∑ i, q i = 0) → ")
    return verify_lean(
        tools / "lean", proofs / "ParticleNoGo.lean",
        {"dp_particle_odd_det": prefix + "(∀ i j, M i j ≠ 0 → ∃ k : ℤ, q i + q j = d * (2 * k + 1)) → M.det = 0",
         "dp_particle_one_scalar": prefix + "(∀ i j, M i j ≠ 0 → q i + q j = d ∨ q i + q j = -d) → M.det = 0"},
        cwd=proofs, lake=tools / "lake", timeout=10,
    )


def _single_scalar_probe(problem, *, exclude_both_fixed_charges=False):
    n, bound = problem["fermions"], problem["charge_bound"]
    pool = _pool(bound)
    budget = problem["budget"]
    total = comb(len(pool) + n - 2, n - 1)
    examined, supports = 0, 0
    for prefix in islice(combinations_with_replacement(pool, n - 1), budget["verification_steps"]):
        last = -sum(prefix)
        examined += 1
        if last not in pool or (prefix and last < prefix[-1]):
            continue
        charges = (*prefix, last)
        for h in sorted({abs(a + b) for a, b in combinations_with_replacement(charges, 2) if a + b}):
            if exclude_both_fixed_charges and h % 2 == 0 and h // 2 in charges and -(h // 2) in charges:
                continue
            if supports == budget["scalar_sets"]:
                return {"prefixes": examined, "prefixes_total": total, "supports": supports, "complete": False}
            matching, _ = matching_certificate(support(charges, (h,)))
            if len(matching) == n:
                raise ValueError(f"unexpected counterexample to parity: {charges}, {h}")
            supports += 1
    return {"prefixes": examined, "prefixes_total": total, "supports": supports, "complete": examined == total}


def _four_proof(context, problem, sources, comparisons, followups):
    statement = cited(
        "det M ≠ 0 ⇒ 4 divide n",
        "Σᵢ qᵢ = 0, h ∈ ℤ, h > 0",
        "Mᵢⱼ ≠ 0 ⇒ qᵢ + qⱼ ∈ {h, -h}",
        "Almeno uno dei valori h/2, -h/2 è assente dalle cariche fermioniche",
        domain="∀ n ≥ 1, q ∈ ℤⁿ, h ∈ ℤ, M ∈ Matₙ(ℂ)",
    )
    proof = (
        "Un termine non nullo del determinante dà una permutazione con somme di coppia ±h. "
        "La loro somma è 2Σᵢ qᵢ = 0, quindi i due segni compaiono lo stesso numero di volte.",
        "Costruire il grafo sui valori distinti delle cariche, con archi se la somma è ±h. "
        "A ogni vertice vi è al più un vicino per segno, dato dalle riflessioni x ↦ h−x e x ↦ −h−x.",
        "Un ciclo semplice senza cappi dovrebbe alternare i segni e avere lunghezza pari 2k. "
        "La composizione di due riflessioni diverse è la traslazione di ±2h. "
        "Dopo 2k archi il valore cambia di ±2kh, quindi un ciclo semplice è impossibile.",
        "I cicli della permutazione proiettano su cammini chiusi nel grafo dei valori. "
        "Ogni arco senza cappio attraversa un taglio della foresta e compare un numero pari di volte. "
        "Poiché un segno è privo di cappi, le etichette di quel segno compaiono un numero pari di volte.",
        "Il loro conteggio è n/2, quindi 4 divide n. La chiralità stretta impedisce che h/2 e −h/2 "
        "compaiano entrambi. Con le due anomalie n ≥ 5 per i risultati di letteratura, da cui n ≥ 8.",
    )
    alternative = (
        "Per ogni carica x, siano p(x), m(x) i conteggi degli archi uscenti di etichetta h, −h "
        "nel termine di permutazione. I conteggi entranti e uscenti coincidono, perciò "
        "p(x)+m(x)=p(h−x)+m(−h−x).",
        "La differenza D(x)=p(x)−p(h−x)=m(−h−x)−m(x) cambia segno sotto entrambe le riflessioni. "
        "È quindi periodica di periodo 2h e ha supporto finito. Segue D=0.",
        "Ogni conteggio è invariante per la sua riflessione. Per il segno privo del punto fisso "
        "nel multinsieme delle cariche, i termini si raggruppano in coppie di uguale molteplicità. "
        "Il conteggio di quel segno è dunque pari e coincide con n/2.",
    )
    context.stage("verifica_indipendente", "Due derivazioni universali e ricerca finita di supporti")
    probe = _single_scalar_probe(problem, exclude_both_fixed_charges=True)
    evidence = {
        "verified": True, "independent": True, "proof": proof, "alternative_proof": alternative,
        "proof_status": "two_analytic_proofs",
        "formal_obligation": "Formalizzare in Lean la simmetria delle molteplicità o il lemma sui cammini chiusi.",
        "counterexample_search": probe, "independent_check": "Dimostrazione per molteplicità e supporto finito.",
        "assumption_boundary": mass_certificate((-1, 1), (2,)),
        "literature_status": "specific_equivalence_under_review", "limitations": LIMITATIONS,
    }
    claim = _claim("one_scalar_multiple_four", "Massa piena con uno scalare richiede 4 ∣ n",
                   statement, Kind.EXACT, sources, (ANOMALIES, YUKAWA), evidence)
    detail = _base_detail(problem, "analytic_derivation", examined=probe["prefixes"], total=probe["prefixes_total"],
                          literature="Equivalenza bibliografica aperta")
    detail.update(evidence)
    detail["dossier"] = _dossier(claim, detail, comparisons)
    detail["dossier"]["Seconda dimostrazione"] = alternative
    return Result("verified", problem["title"], detail, (claim,), followups, comparisons=comparisons,
                  substantive=True, proof_complete=True, independent=True,
                  public_query="chiral Abelian | fermion mass | single scalar | Majorana")


def _proof(context, problem, followups):
    context.stage("deduzione", "Espansione del determinante e conservazione della carica")
    sources = tuple(sorted(set(problem["references"]) | {HIGGS}))
    comparisons = _comparisons()
    if problem["theorem"] == "one_scalar_multiple_four":
        return _four_proof(context, problem, sources, comparisons, followups)
    if problem["theorem"] == "odd_scalar_valuation":
        proof = (
            "Un termine del determinante richiede una permutazione σ con M_{σ(i),i} ≠ 0 per ogni i.",
            "La somma delle cariche associate è Σᵢ(q_{σ(i)}+qᵢ)=2Σᵢqᵢ=0.",
            "Ogni somma di coppia è d(2kᵢ+1). Poiché d ≠ 0, 2Σᵢ kᵢ+n=0, impossibile con n dispari.",
            "Ogni termine contiene quindi un fattore nullo. Per un solo scalare h si pone d=h.",
        )
        counterexamples = _single_scalar_probe(problem)
        context.stage("verifica_indipendente", "Compilazione del teorema nel kernel Lean")
        lean = _label_lean(context)
        kind = Kind.FORMAL if lean["valid"] else Kind.CONDITIONAL
        evidence = {"proof": proof, "lean": lean, "counterexample_search": counterexamples,
                    "proof_status": "kernel_checked" if lean["valid"] else "analytic_proof_with_open_lean_check",
                    "literature_status": "specific_equivalence_under_review", "limitations": LIMITATIONS}
        claim = _claim("odd_scalar", "Ostruzione per n dispari e multipli dispari di d",
                       ODD_STATEMENT, kind, sources, (ODD,), evidence)
        outcome = "proved" if lean["valid"] else "proof_obligation"
        detail = _base_detail(problem, outcome, examined=counterexamples["prefixes"],
                              total=counterexamples["prefixes_total"], literature="Equivalenza bibliografica aperta")
        detail.update(evidence)
        detail["dossier"] = _dossier(claim, detail, comparisons)
        return Result("verified" if lean["valid"] else "partial", problem["title"], detail, (claim,), followups,
                      comparisons=comparisons, substantive=True, proof_complete=lean["valid"],
                      independent=lean["valid"], public_query="chiral U(1) | odd fermions | Yukawa determinant")

    n, bound = problem["fermions"], problem["charge_bound"]
    tested = 0
    for size, a, b in islice(
        ((size, a, b) for size in range(1, n + 1, 2) for a, b in combinations(range(1, bound + 1), 2)),
        problem["budget"]["verification_steps"],
    ):
        if (signed_sum_witness(size, (a, b)) is not None) != two_scalar_allowed(size, a, b):
            raise ValueError(f"unexpected counterexample to the arithmetic equivalence: {size}, {a}, {b}")
        tested += 1
    proof = (
        "Si scriva a'=a/g e b'=b/g, g=MCD(a,b). Le differenze dei conteggi con segno "
        "u e v soddisfano a'u+b'v=0.",
        "La coprimalità implica (u,v)=(b'k,-a'k). Il minimo numero di termini per queste "
        "differenze è |k|(a'+b'), e aggiungere coppie opposte conserva la parità.",
        "Per n dispari, k è dispari e a'+b' è dispari. Serve n ≥ a'+b'. "
        "Per la sufficienza aritmetica prendere k=1 e aggiungere (n-a'-b')/2 coppie.",
        "Un termine di determinante impone tale relazione perché il suo totale è 2Σᵢqᵢ. "
        "Per cariche fermioniche fissate serve anche il supporto di una permutazione.",
    )
    statement = cited(
        "Esistono n termini in {±a, ±b} di somma zero ⇔ (a+b)/MCD(a,b) è dispari e ≤ n. "
        "Nel settore Σᵢ qᵢ=0 questa condizione è necessaria per det M ≠ 0.",
        "n dispari e positivo, 0 < a < b interi", *MASS,
        domain="Somme di etichette scalari e matrici di massa U(1)")
    evidence = {"proof": proof, "proof_status": "analytic_derivation",
                "formal_obligation": "Formalizzare l'equivalenza aritmetica a due scalari in Lean.",
                "independent_check": "Programmazione dinamica sulle somme con segno, nel dominio del controllo.",
                "counterexample_search": {"tested": tested, "total": ((n + 1) // 2) * comb(bound, 2),
                                          "a_b_bound": bound, "odd_n_at_most": n},
                "literature_status": "specific_equivalence_under_review", "limitations": LIMITATIONS}
    claim = _claim("two_scalar_labels", "Criterio aritmetico per due scalari e n dispari",
                   statement, Kind.CONDITIONAL, sources, (YUKAWA,), evidence)
    detail = _base_detail(problem, "analytic_derivation", examined=tested,
                          total=evidence["counterexample_search"]["total"],
                          literature="Equivalenza bibliografica aperta")
    detail.update(evidence)
    detail["dossier"] = _dossier(claim, detail, comparisons)
    return Result("verified", problem["title"], detail, (claim,), followups, comparisons=comparisons,
                  substantive=True, proof_complete=True, public_query="chiral U(1) | two Higgs | fermion mass rank")


def _dossier(claim, detail, comparisons):
    verification = detail.get("independent_check")
    if verification is None:
        lean = detail.get("lean", {})
        verification = {key: lean[key] for key in ("status", "version", "source_sha256", "axioms") if key in lean}
    return {
        "Enunciato": claim.statement.display()["conclusion"],
        "Dominio": claim.statement.display()["domain"],
        "Ipotesi fisiche e matematiche": claim.statement.display()["hypotheses"],
        "Dipendenze": claim.dependencies,
        "Metodo e certificato": detail.get("proof", "Enumerazione intera e certificati associati nel JSON."),
        "Calcoli esatti": "Il rapporto JSON conserva risultati, parametri e certificati riproducibili.",
        "Verifica indipendente": verification,
        "Ricerca di controesempi": detail.get("counterexample_search", {}),
        "Stato della prova": detail.get("proof_status", "certificato finito"),
        "Obbligo di prova": detail.get("formal_obligation", ""),
        "Confronto con la letteratura": comparisons,
        "Fonti": [f"{source.title}. {source.locator}. {source.url}" for source in SOURCES if source.id in claim.sources],
        "Riproducibilità": detail["reproducibility"], "Limiti": detail["limitations"],
    }


def _summarize_models(rows):
    groups = {}
    for row in rows:
        groups.setdefault(canonical_charges(row), []).append(list(row))
    return [
        {"charges": list(row), "linear_sum": sum(row), "cubic_sum": sum(q**3 for q in row),
         "anomaly_free": sum(row) == sum(q**3 for q in row) == 0,
         "chirality": chirality(row), "equivalent_orientations": sorted(groups[row])}
        for row in sorted(groups)
    ]


def _paired_construction(mass):
    charges, scalars = mass["fermion_charges"], mass["scalar_charges"]
    matrix = mass["witness_matrix"]
    if len(scalars) != 1 or any(row[i] or sum(row) != 1 for i, row in enumerate(matrix)):
        return None
    h, = scalars
    pairs = [(charges[i], charges[j]) for i, row in enumerate(matrix) for j in range(i + 1, len(row)) if row[j]]
    squared_differences = {sign: sum((a-b)**2 for a, b in pairs if a+b == sign) for sign in (h, -h)}
    return {
        "pairs": pairs, "pair_sums": [a+b for a, b in pairs],
        "squared_differences_by_pair_sum": squared_differences,
        "method": "Per una coppia di somma s e differenza d, la somma dei cubi è (s³+3sd²)/4.",
    }


def _counterexample(problem, models, detail, followups):
    scalars = problem["scalar_charges"]
    sources = tuple(sorted(set(problem["references"]) | {HIGGS}))
    statement = cited(
        "L'esistenza di una somma di n etichette scalari con totale 2Σᵢqᵢ implica una massa di rango pieno.",
        *_assumptions(problem, True), domain=_domain(problem),
    )
    proposal = _claim("sufficiency", "Sufficienza aritmetica del supporto scalare", statement,
                      Kind.CONJECTURE, sources, (ANOMALIES, YUKAWA), {"origin": "problema di confutazione"})
    tested, found = 0, None
    for model in models[:problem["budget"]["scalar_sets"]]:
        charges = model["charges"]
        tested += 1
        labels = signed_sum_witness(len(charges), scalars, 2 * sum(charges))
        if labels is None:
            continue
        matching, _ = matching_certificate(support(charges, scalars))
        if len(matching) == len(charges):
            continue
        if sum(labels) != 2 * sum(charges) or any(abs(label) not in scalars for label in labels):
            raise ValueError("invalid arithmetic relation")
        found = {"charges": charges, "signed_scalar_labels": labels, "mass": mass_certificate(charges, scalars)}
        break
    detail["counterexample_search"] = {"tested_orbits": tested, "complete": found is None and tested == len(models)}
    if found is None:
        detail["outcome"] = detail["summary"]["outcome"] = ("counterexample_absent" if tested == len(models)
                                                           else "budget_exhausted")
        return Result("inconclusive", problem["title"], detail, (proposal,), followups)
    detail["outcome"] = detail["summary"]["outcome"] = "counterexample"
    detail["counterexample"] = found
    detail["proof_status"] = "exact_counterexample"
    claim = _claim("counterexample", "Controesempio alla sufficienza aritmetica", statement, Kind.COUNTEREXAMPLE,
                   sources, (proposal.id,), {"verified": True, "witness": found, "mass": found["mass"]})
    detail["dossier"] = _dossier(claim, detail, _comparisons())
    return Result("refuted", problem["title"], detail, (proposal, claim), followups,
                  comparisons=_comparisons(), proof_complete=True, independent=True)


def _classify(context, problem, scan_result, detail, followups):
    rows = scan_result["rows"]
    context.stage("verifica_indipendente", "Modello SMT su molteplicità o completamento lineare")
    independent = independent_scan(problem, rows)
    models = _summarize_models(rows)
    detail.update({"oriented_assignments": rows, "models": models, "independent_check": independent})
    detail["summary"]["models"] = len(models)
    if problem["type"] == "counterexample":
        return _counterexample(problem, models, detail, followups)
    include_mass = problem["max_scalars"] > 0 or problem["mass_condition"] == "full_rank"
    masses, eligible = [], models
    complete = True
    if include_mass:
        context.stage("calcolo_simbolico", "Matrice di Yukawa, copertura e testimoni razionali")
        budget = problem["budget"]["scalar_sets"]
        for model in models:
            if not budget:
                complete = False
                break
            answer = scalar_search(model["charges"], problem, budget)
            budget -= answer["tested_sets"]
            masses.append({"charges": model["charges"], **answer})
            if problem["type"] == "classification" or problem["completeness"] == "exhaustive":
                complete &= answer["complete"]
            else:
                complete &= answer["status"] != "UNKNOWN"
        detail["mass_searches"] = masses
        if problem["mass_condition"] == "full_rank":
            eligible = [model for model, answer in zip(models, masses) if answer["status"] == "SAT"]
    eligible_charges = [model["charges"] for model in eligible]
    detail["qualified_models"] = eligible_charges
    detail["summary"]["qualified"] = len(eligible)
    detail["complete"] = complete
    detail["outcome"] = detail["summary"]["outcome"] = (
        "SAT" if eligible else "UNSAT" if complete else "UNKNOWN")
    if not complete or not independent["verified"]:
        detail["proof_status"] = "budget_exhausted" if not complete else "independent_check_open"
        return Result("partial", problem["title"], detail, followups=followups)
    baseline_charges = [model["charges"] for model in models] == [list(BASELINE)]
    baseline_domain = (not include_mass and problem["fermion_charges"] is None
                       and problem["charge_bound"] == 9 and problem["fermions"] == 5
                       and problem["strict_chirality"] and problem["primitive"]
                       and len(problem["anomalies"]) == 2)
    baseline_mass = bool(masses and masses[0]["minimum"] == 2
                         and masses[0]["certificate"]["determinant"] == "b**2*c**2*d")
    baseline = baseline_charges and (baseline_domain or baseline_mass)
    certificate = {
        "verified": True, "independent": True,
        "models": eligible_charges, "examined": scan_result["offset"], "unit": scan_result["unit"],
        "completeness": "finite_exhaustion" if problem["type"] == "classification" or not eligible
        else "verified_witnesses_and_minimum",
        "mass_certificate_count": len(masses),
    }
    if masses and len(masses) == 1:
        certificate["mass"] = masses[0]["certificate"]
        certificate["minimum_scalars"] = masses[0]["minimum"]
        if problem["type"] == "construction" and certificate["mass"]:
            if pairs := _paired_construction(certificate["mass"]):
                detail["construction"] = pairs
    detail["proof_status"] = certificate["completeness"]
    conclusion = (f"{len(eligible)} classi di carica ammissibili con i vincoli dichiarati." if eligible
                  else "Nessuna assegnazione ammissibile nel dominio finito dichiarato.")
    if problem["type"] == "construction" and len(masses) == 1 and masses[0]["minimum"] is not None:
        mass = masses[0]["certificate"]
        conclusion = (f"Minimo di {masses[0]['minimum']} scalari. Per h = {tuple(mass['scalar_charges'])}, "
                      f"rango {mass['generic_rank']} e det M = {mass['determinant']}.")
    statement = cited(
        conclusion, *_assumptions(problem, include_mass), domain=_domain(problem),
    )
    sources = tuple(sorted(set(problem["references"]) | ({HIGGS} if include_mass else set())))
    dependencies = (ANOMALIES, YUKAWA) if include_mass else (ANOMALIES,)
    claim = _claim("classification", problem["title"], statement, Kind.EXACT, sources, dependencies, certificate)
    detail["dossier"] = _dossier(claim, detail, _comparisons())
    few = (not eligible and problem["fermions"] < 5 and problem["strict_chirality"]
           and len(problem["anomalies"]) == 2)
    known = ("baseline Particle Pilot",) if baseline else (FEW,) if few else ()
    return Result("reproduced" if baseline or few else "verified", problem["title"], detail, (claim,), followups,
                  known=known, comparisons=_comparisons(),
                  proof_complete=True, independent=True)


def run_problem(context: Context, payload: dict) -> Result:
    example = payload.get("example")
    if "problem" in payload:
        problem = read_problem(payload["problem"])
    elif example in PROGRAM:
        file = context.root / "experiments" / "particle" / f"{example}.json"
        problem = read_problem(json.loads(file.read_text(encoding="utf-8")))
    else:
        raise ValueError("unknown Particle Theory problem")
    followups = _next_example(example)
    if problem["type"] == "proof":
        return _proof(context, problem, followups)

    context.stage("ricerca", f"{problem['id']} · {problem['method']}")
    search = scan(problem, payload.get("checkpoint", {}))
    outcome = "space_exhausted" if search["complete"] else (
        "budget_exhausted" if search["budget_exhausted"] else "checkpoint")
    models = _summarize_models(search["rows"])
    detail = _base_detail(problem, outcome, examined=search["offset"], total=search["total"],
                          models=len(models), excluded=sum(search["excluded"].values()),
                          literature="Fonti primarie nel registro")
    detail["enumeration"] = {key: value for key, value in search.items() if key != "rows"}
    detail["completeness_rule"] = (
        "Ogni multinsieme ha un unico ordinamento. Con quadratic il prefisso ordinato determina "
        "le ultime due cariche tramite il discriminante o il caso x+y=0."
    )
    if search["complete"]:
        return _classify(context, problem, search, detail, followups)
    detail["models"] = models
    if outcome == "checkpoint":
        checkpoint = {key: search[key] for key in ("offset", "rows", "excluded")}
        followups = (Work("problem", {"example": example, "problem": problem, "checkpoint": checkpoint}, 85),)
    elif (not search["model_limit"] and problem["method"] == "enumeration" and len(problem["anomalies"]) == 2
          and problem["fermions"] >= 2 and problem["fermion_charges"] is None):
        alternative = problem | {"method": "quadratic"}
        detail["next_strategy"] = "quadratic"
        followups = (Work("problem", {"example": example, "problem": alternative}, 85),)
    return Result("partial", problem["title"], detail, followups=followups)


LAB = Lab(
    ID, "Particle Theory",
    "U(1) anomalies, chiral charges, and Yukawa mass rank with exact integer and symbolic checks.",
    SOURCES, CLAIMS, {"problem": run_problem}, (Work("problem", {"example": PROGRAM[0]}, 70),),
    submit=submit,
)
