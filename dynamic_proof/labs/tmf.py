# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Public examples of averaged metrics and variational dynamics at finite scale."""
from __future__ import annotations

from fractions import Fraction

import sympy as sp

from ..core.literature import Source
from ..core.model import Claim, Kind, cited, e, num, var
from ..core.plugin import Context, Lab, Result, Work
from ..core.verification import rational_identity, verify_lean


JOYCE = "geometry.joyce"
DPR003 = "dp.geometry.dpr003"
SOURCES = (
    Source(JOYCE, "Dominic Joyce, Riemannian holonomy groups and calibrated geometry",
           "§1.4, formula di Koszul e connessione di Levi-Civita", "2006",
           "https://people.maths.ox.ac.uk/joyce/RHCGnotes.pdf",
           terms=("Levi-Civita connection", "Riemannian metric", "Koszul")),
    Source(DPR003, "Dynamic Proof · DPR-003",
           "Controesempio per due metriche e pesi costanti", "2026-11-10",
           "https://mattoccia.com/dynamics-lab/dynamic-proof/dpr-003/",
           terms=("averaged connections", "metric average", "counterexample")),
)
MEAN_CONNECTION = cited("∇^G = Σ_i w_i ∇^{g_i}",
                        "G=Σ_i w_i g_i, pesi positivi costanti con somma uno",
                        domain="famiglia finita di metriche riemanniane lisce sullo stesso dominio")
CLAIMS = (
    Claim("tmf.mean_connection.identity", "tmf", "La connessione commuta con la media metrica",
          MEAN_CONNECTION, Kind.CONJECTURE, (JOYCE,), evidence={"origin": "ipotesi di controllo"}),
)


def _lean(context: Context, expected: dict[str, str]) -> dict:
    directory = context.root / "proofs"
    tools = context.root / ".tools" / "lean" / "bin"
    return verify_lean(tools / "lean", directory / "Reference.lean", expected, cwd=directory,
                       lake=tools / "lake", timeout=12)


def _euler(metric: sp.Matrix, coordinates, velocity, acceleration) -> sp.Matrix:
    lagrangian = (sp.Matrix(velocity).T * metric * sp.Matrix(velocity))[0]
    rows = []
    for coordinate, speed in zip(coordinates, velocity):
        momentum = sp.diff(lagrangian, speed)
        derivative = sum(sp.diff(momentum, x)*v for x, v in zip(coordinates, velocity))
        derivative += sum(sp.diff(momentum, v)*a for v, a in zip(velocity, acceleration))
        rows.append(sp.simplify(derivative - sp.diff(lagrangian, coordinate)))
    return sp.Matrix(rows)


def _connection(metric: sp.Matrix, coordinates) -> list[sp.Matrix]:
    inverse = metric.inv()
    dimension = len(coordinates)
    return [
        sp.Matrix(dimension, dimension, lambda i, j: sp.simplify(sum(
            inverse[k, l] * (sp.diff(metric[l, j], coordinates[i]) + sp.diff(metric[l, i], coordinates[j])
                             - sp.diff(metric[i, j], coordinates[l])) / 2 for l in range(dimension))))
        for k in range(dimension)
    ]


def _metric_acceleration(metric, coordinates, velocity, acceleration):
    v = sp.Matrix(velocity)
    return sp.Matrix(acceleration) + sp.Matrix([(v.T * term * v)[0] for term in _connection(metric, coordinates)])


def mean_connection(context: Context, _payload: dict) -> Result:
    context.stage("calcolo", "Confronto delle connessioni di due metriche nel caso DPR-003")
    x, y = sp.symbols("x y", real=True)
    coordinates = (x, y)
    first, second = sp.eye(2), sp.diag(1+x, 1)
    metric = (first + second) / 2
    connection_of_mean = _connection(metric, coordinates)[0][0, 0]
    mean_of_connections = sum(_connection(g, coordinates)[0][0, 0] for g in (first, second)) / 2
    difference = sp.cancel(connection_of_mean - mean_of_connections)
    exact_gap = Fraction(1, 6) - (Fraction(0) + Fraction(1, 4))/2
    if (sp.cancel(difference - x/(4*(x+1)*(x+2))) != 0
            or difference.subs(x, 1) != sp.Rational(1, 24) or exact_gap != Fraction(1, 24)):
        raise ArithmeticError("testimone geometrico non verificato")
    context.stage("verifica", "Christoffel simbolico e confronto con aritmetica razionale")
    lean = _lean(context, {"dp_tmf_mean_gap": "(1 / 6 : ℚ) - (0 + 1 / 4) / 2 = 1 / 24"})
    witness = {
        "domain": "x > -1", "metrics": ["diag(1,1)", "diag(1+x,1)"], "weights": ["1/2", "1/2"],
        "point_x": 1, "connection_of_mean": str(connection_of_mean.subs(x, 1)),
        "mean_of_connections": str(mean_of_connections.subs(x, 1)), "difference": str(exact_gap),
        "difference_formula": str(difference),
    }
    claim = Claim("tmf.mean_connection.counterexample", "tmf", "Controesempio alla commutazione delle medie",
                  MEAN_CONNECTION, Kind.COUNTEREXAMPLE, (JOYCE, DPR003), ("tmf.mean_connection.identity",),
                  {"verified": True, "witness": witness, "lean": lean,
                   "independent": "formula di Christoffel e aritmetica razionale"})
    return Result("refuted", claim.title, {"witness": witness, "lean": lean}, (claim,),
                  (Work("weighted_identity", {}, 75, 5), Work("variable_action", {}, 72, 5)),
                  known=(DPR003,), proof_complete=True, independent=True)


def mono_scale(context: Context, _payload: dict) -> Result:
    context.stage("deduzione", "Riduzione monoscala con misura di Dirac")
    x, y, vx, vy, ax, ay = sp.symbols("x y vx vy ax ay", real=True)
    args = (x, y), (vx, vy), (ax, ay)
    metric = sp.diag(sp.exp(x), 1+x*x)
    lhs = _euler(metric, *args)
    rhs = 2 * metric * _metric_acceleration(metric, *args)
    if sp.simplify(lhs - rhs) != sp.zeros(2, 1):
        raise ArithmeticError("riduzione monoscala non riprodotta")
    claim = Claim("tmf.mono", "tmf", "Riduzione monoscala dell’azione metrica",
                  cited("μ=δ_{s₀} ⇒ G=g_{s₀} e δS=0 ⇔ ∇^{g_{s₀}}_{γ̇}γ̇=0",
                        "g_{s₀} riemanniana liscia e variazioni a estremi fissati"),
                  Kind.EXACT, (JOYCE,), evidence={"verified": True,
                      "independent": "valutazione della misura di Dirac e confronto EL–Christoffel",
                      "proof": "l’integrale di Dirac seleziona g_{s₀}; EL=2g_{s₀}(∇γ̇γ̇,·); "
                               "g_{s₀} non degenere", "example": str(lhs)})
    return Result("reproduced", claim.title, claim.evidence, (claim,), known=(JOYCE,),
                  proof_complete=True, independent=True)


def weighted_identity(context: Context, _payload: dict) -> Result:
    context.stage("generazione", "Identità del commutatore tra media metrica e media affine")
    w, a, b, da, db, dw = map(var, ("w", "a", "b", "da", "db", "dw"))
    add = lambda u, v: e("add", u, v)
    sub = lambda u, v: e("sub", u, v)
    mul = lambda u, v: e("mul", u, v)
    div = lambda u, v: e("div", u, v)
    wb = sub(num(1), w)
    G = add(mul(w, a), mul(wb, b))
    Gp = add(add(mul(w, da), mul(wb, db)), mul(dw, sub(a, b)))
    lhs = sub(div(Gp, mul(num(2), G)),
              add(mul(w, div(da, mul(num(2), a))), mul(wb, div(db, mul(num(2), b)))))
    rhs = div(mul(sub(a, b), add(mul(mul(w, wb), sub(div(da, a), div(db, b))), dw)), mul(num(2), G))
    checked = rational_identity(lhs, rhs, ("w", "a", "b", "da", "db", "dw"))
    lean = _lean(context, {"dp_tmf_cleared":
        "∀ w a b da db dw : ℚ, a*b*(w*da+(1-w)*db+dw*(a-b)) "
        "- (w*a+(1-w)*b)*(w*b*da+(1-w)*a*db) "
        "= w*(1-w)*(a-b)*(b*da-a*db)+a*b*dw*(a-b)"})
    if not checked["valid"]:
        raise ArithmeticError("l’identità razionale non passa la verifica indipendente")
    claim = Claim("tmf.weighted.commutator", "tmf", "Commutatore esatto per due coefficienti metrici",
                  cited("Γ_G−[wΓ_a+(1−w)Γ_b]=(a−b)[w(1−w)(a′/a−b′/b)+w′]/(2G)",
                        "G=wa+(1−w)b, a,b>0, 0<w<1, a,b,w lisce",
                        domain="un coefficiente metrico lungo una coordinata separata"),
                  Kind.EXACT, (JOYCE,), evidence={"verified": True,
                    "independent": checked["independent"], "certificate": checked, "lean_polynomial": lean})
    return Result("partial", claim.title, {"certificate": checked, "lean": lean,
                  "consequence": "con w costante e a/b costante, le due connessioni coincidono"},
                  (claim,),
                  substantive=False, proof_complete=True, independent=True)


def variable_action(context: Context, _payload: dict) -> Result:
    context.stage("ricerca", "Termini di derivazione della misura e ordine delle equazioni")
    x, y, vx, vy, ax, ay = sp.symbols("x y vx vy ax ay", real=True)
    args = (x, y), (vx, vy), (ax, ay)
    G = (1-x)*sp.eye(2) + x*sp.diag(2, 1)
    euler = _euler(G, *args)
    expected = sp.Matrix([2*(1+x)*ax + vx**2, 2*ay])
    hessian = euler.jacobian([ax, ay])
    if sp.simplify(euler - expected) != sp.zeros(2, 1) or hessian != 2 * G:
        raise ArithmeticError("ordine e derivata dei pesi non riprodotti")
    independent = 2 * (1 + Fraction(1, 2)) * (-Fraction(1, 3)) + 1
    if independent != 0:
        raise ArithmeticError("testimone per i pesi variabili non verificato")
    claim = Claim("tmf.variable.el", "tmf", "L’azione con pesi variabili conserva un termine di derivata della misura",
                  cited("EL_x=2(1+x)ẍ+ẋ², EL_y=2ÿ; Hessiana nelle accelerazioni=2G",
                        "0<x<1; g₁=I, g₂=diag(2,1); w₁=1−x, w₂=x"),
                  Kind.EXACT, (JOYCE,), evidence=
                  {"verified": True, "independent": "Euler–Lagrange e Christoffel espliciti, controllo razionale",
                   "equation": str(euler), "acceleration_hessian": str(hessian),
                   "order": "secondo ordine per la curva; primo ordine sullo spazio delle fasi (x,v). "
                            "Un flusso gradiente su x richiede una legge distinta.",
                   "weight_term": "∂_k G_ij = ∑_s (w_s ∂_k g_{s,ij} + (∂_k w_s)g_{s,ij})"})
    return Result("partial", claim.title, claim.evidence, (claim,),
                  proof_complete=True, independent=True)


LAB = Lab("tmf", "TMF · Multiscale geometry",
          "Mathematical checks of averaged metrics, connections, and finite-scale actions.",
          SOURCES, CLAIMS, {"mono_scale": mono_scale, "mean_connection": mean_connection,
                           "weighted_identity": weighted_identity, "variable_action": variable_action},
          (Work("mono_scale", {}, 100), Work("mean_connection", {}, 98)))
