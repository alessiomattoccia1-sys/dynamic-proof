# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dynamic_proof.core.literature import assess
from dynamic_proof.core.logic import deduce, evaluate, residual, solve, witness_valid
from dynamic_proof.core.model import Binder, Claim, Kind, Statement, TRUE, e, num, var
from dynamic_proof.core.plugin import Work
from dynamic_proof.core.store import Store
from dynamic_proof.core.verification import rational_identity


X = var("x")
B = (Binder("x", "int"),)
GOAL = e("ge", X, num(0))


class LogicTests(unittest.TestCase):
    def test_typechecking_and_alpha_equivalence(self):
        original = Statement(B, TRUE, (), e("eq", e("add", X, num(2)), num(3)))
        alternate = Statement((Binder("q", "int"),), TRUE, (),
                              e("eq", num(3), e("add", num(2), var("q"))))
        self.assertEqual(Statement.read(original.data()), original)
        self.assertEqual(original.fingerprint(), alternate.fingerprint())
        with self.assertRaises(ValueError):
            Statement(B, TRUE, (), e("eq", var("unknown"), num(1)))
        with self.assertRaises(ValueError):
            Statement(B, TRUE, (), e("divides", num("1/2"), X))

    def test_counterexample_checked_exactly(self):
        target = Statement(B, GOAL, (), e("gt", X, num(0)))
        result = solve(target)
        self.assertEqual(result["status"], "counterexample")
        self.assertEqual(result["witness"], {"x": "0"})
        self.assertTrue(witness_valid(target, result["witness"]))
        self.assertFalse(witness_valid(target, {"x": "1/2"}))
        self.assertFalse(witness_valid(target, {"x": "-1"}))

    def test_coverage_preserves_narrow_premises(self):
        target = Statement(B, TRUE, (GOAL,), e("gt", X, num(0)))
        premise = Claim("p", "a", "narrow",
                        Statement(B, e("gt", X, num(1)), (e("lt", X, num(5)),), target.conclusion),
                        Kind.EXACT, evidence={"usable_for_coverage": True})
        reduced = residual(target, [premise])
        for value in range(-2, 8):
            expected = value >= 0 and not 1 < value < 5
            self.assertEqual(evaluate(reduced.residual.scope, {"x": Fraction(value)}), expected)
        self.assertEqual(reduced.dependencies, ("p",))
        wrong = Claim("p2", "a", "wrong", Statement(B, TRUE, (), e("lt", X, num(0))),
                      Kind.EXACT, evidence={"usable_for_coverage": True})
        with self.assertRaisesRegex(ValueError, "incompatible"):
            residual(target, [wrong])

    def test_exhaustive_certificate_only_covers_declared_interval(self):
        target = Statement(B, GOAL, (), GOAL)
        finite = Statement(B, e("and", e("ge", X, num(2)), e("le", X, num(4))), (), GOAL)
        claim = Claim("f", "a", "f", finite, Kind.CERTIFIED,
                      evidence={"verified": True, "precision_bits": 100, "exhaustive": True,
                                "count": 3, "interval": [2, 4]})
        result = residual(target, [claim]).residual
        self.assertTrue(evaluate(result.scope, {"x": Fraction(5)}))
        self.assertFalse(evaluate(result.scope, {"x": Fraction(3)}))
        malformed = Claim("m", "a", "m", finite, Kind.CERTIFIED,
                          evidence=claim.evidence | {"count": 2})
        with self.assertRaises(ValueError):
            residual(target, [malformed])

    def test_guarded_deduction_and_incompatibility(self):
        positive = e("gt", X, num(0))
        target = Statement(B, positive, (), e("ge", X, num(1)))
        premise = Claim("p", "a", "p", Statement(B, positive, (), target.conclusion), Kind.EXACT,
                        evidence={"usable_for_coverage": True})
        self.assertEqual(deduce(target, [premise])["status"], "conditional")
        broader = Statement(B, TRUE, (), target.conclusion)
        self.assertEqual(deduce(broader, [premise])["status"], "sat")
        vacuous = Statement(B, e("and", positive, e("lt", X, num(0))), (), target.conclusion)
        self.assertEqual(deduce(vacuous, [premise])["status"], "incompatible_scope")

    def test_symbolic_independence_and_denominators(self):
        identity = rational_identity(e("div", e("mul", X, X), X), X, ("x",))
        self.assertTrue(identity["valid"])
        self.assertEqual(identity["denominators_nonzero"], ["x"])
        wrong = rational_identity(e("add", X, num(1)), X, ("x",))
        self.assertFalse(wrong["valid"])
        with self.assertRaises(ValueError):
            rational_identity(e("div", X, e("sub", X, X)), X, ("x",))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name) / "research.db")

    def test_checkpoint_recovery_and_dedup(self):
        job = Work("test", {"n": 1}).data()
        self.assertTrue(self.store.enqueue("a", job))
        self.assertFalse(self.store.enqueue("a", job))
        active = self.store.next_job(50)
        self.store.stage(active, "verifica", "simulazione interruzione")
        self.store.recover()
        again = self.store.next_job(50)
        self.assertEqual(active["id"], again["id"])
        self.assertNotEqual(active["attempt_id"], again["attempt_id"])
        result = {"status": "failed", "title": "tentativo negativo", "detail": {"why": "regression"}}
        key = self.store.finish(again, result, {"wall_seconds": 0}, None)
        self.assertEqual(self.store.artifact(key)["detail"]["why"], "regression")
        self.assertEqual(self.store.snapshot()["totals"]["attempts"], 2)

    def test_dynamic_fairness_and_control(self):
        self.store.enqueue("a", Work("x", {"n": 1}, 99).data())
        self.store.enqueue("a", Work("x", {"n": 2}, 98).data())
        self.store.enqueue("b", Work("x", {"n": 1}, 5).data())
        self.store.control("paused")
        self.assertIsNone(self.store.next_job(10))
        self.store.control("running")
        first = self.store.next_job(10)
        self.assertEqual(first["lab"], "a")
        self.store.finish(first, {"status": "reproduced"}, {}, None)
        self.assertEqual(self.store.next_job(10)["lab"], "b")

    def test_registry_enforces_proof_and_trace(self):
        target = Statement(B, TRUE, (), GOAL)
        proposal = Claim("p", "a", "open", target, Kind.CONJECTURE)
        self.store.add_claim(proposal)
        with self.assertRaises(ValueError):
            self.store.add_claim(Claim("bad", "a", "bad", target, Kind.FORMAL))
        with self.assertRaises(ValueError):
            self.store.add_claim(Claim("c", "a", "cycle", target, Kind.CONJECTURE, dependencies=("c",)))
        self.store.add_claim(Claim("r", "a", "witness", target, Kind.COUNTEREXAMPLE,
                                   dependencies=("p",), evidence={"verified": True, "witness": {"x": "-1"}}))
        self.assertEqual(self.store.claim("p")["refuted_by"], ["r"])

    def test_metadata_never_promotes_novelty(self):
        sources = [{"source": "arXiv", "ok": True, "hits": [{}]},
                   {"source": "Crossref", "ok": True, "hits": [{}]}]
        comparison = {"work": "w1", "locator": "theorem 2", "difference": "scope",
                      "reviewed_scope": "primary formula", "relation": "different"}
        options = dict(known=(), similar=False, substantive=True, proof_complete=True,
                       independent=True, replayed=True, searches=sources)
        self.assertEqual(assess(evidence_kind=Kind.EXACT, comparisons=[comparison], **options)["level"], "A")
        related = [comparison | {"direct_prior_art": True}, comparison | {"direct_prior_art": True, "work": "w2"}]
        self.assertEqual(assess(evidence_kind=Kind.CERTIFIED, comparisons=related, **options)["level"], "B")
        self.assertEqual(assess(evidence_kind=Kind.EXACT, comparisons=related, **options)["level"], "C")
