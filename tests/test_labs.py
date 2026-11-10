# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
from math import prod
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dynamic_proof.core.experiment import audit_statement
from dynamic_proof.core.model import Kind
from dynamic_proof.core.plugin import Context
from dynamic_proof.labs import riemann, strings, tmf
from dynamic_proof.core.verification import verify_lean


ROOT = Path(__file__).resolve().parent.parent
CONTEXT = Context(ROOT, False, lambda *_: None)


class ScientificRegression(unittest.TestCase):
    def test_robin_reference_and_partial_scope(self):
        result = riemann.robin_range(CONTEXT, {"start": 5040, "end": 5042})
        self.assertEqual(result.status, "refuted")
        self.assertEqual(result.claims[0].statement, riemann.INCLUSIVE)
        self.assertEqual(result.detail["negative"][0]["sigma"], 19344)
        self.assertEqual(result.detail["checked"], 3)
        good = riemann.robin_range(CONTEXT, {"start": 5041, "end": 5044})
        self.assertEqual(good.claims[0].kind, Kind.CERTIFIED)
        self.assertEqual(good.claims[0].evidence["interval"], [5041, 5044])
        self.assertIn("lower_dyadic", good.detail["positives"][0]["threshold_minus_sigma"])

    def test_residual_and_zeta(self):
        result = riemann.robin_reduce(CONTEXT, {})
        self.assertEqual(result.detail["modulus"], prod(riemann.HERTLEIN_DIVISORS))
        self.assertEqual(len(result.claims[0].dependencies), 3)
        zero = riemann.zeta_zeros(CONTEXT, {"first": 1, "count": 1})
        self.assertEqual(zero.claims[0].kind, Kind.CERTIFIED)
        self.assertTrue(zero.detail["zeros"][0]["mpmath_height"].startswith("14.134725"))

    def test_two_string_references(self):
        self.assertEqual(strings.modular_volume(CONTEXT, {}).detail["exact"], "pi/3")
        config = {"radius": "3/2", "height": "1/10"}
        first = strings.theta_reference(CONTEXT, config)
        second = strings.theta_reference(CONTEXT, config)
        self.assertEqual(first.data(), second.data())
        self.assertEqual(first.claims[0].kind, Kind.CERTIFIED)
        self.assertTrue(strings.theta_dual(CONTEXT, {}).detail["certificate"]["valid"])
        delta = strings.ramanujan_projection(CONTEXT, {"count": 8})
        self.assertEqual(delta.detail["tau_1_to_N"][:4], [1, -24, 252, -1472])
        unfolding = strings.theta_unfolding(CONTEXT, {})
        self.assertEqual(unfolding.status, "reproduced")
        self.assertIn("R**2 + 1", unfolding.detail["mean"])

    def test_tmf_public_geometry(self):
        self.assertEqual(tmf.mono_scale(CONTEXT, {}).status, "reproduced")
        result = tmf.mean_connection(CONTEXT, {})
        self.assertEqual(result.status, "refuted")
        self.assertEqual(result.claims[0].kind, Kind.COUNTEREXAMPLE)
        self.assertEqual(result.claims[0].statement, tmf.MEAN_CONNECTION)
        witness = result.detail["witness"]
        self.assertEqual(witness["connection_of_mean"], "1/6")
        self.assertEqual(witness["mean_of_connections"], "1/8")
        self.assertEqual(witness["difference"], "1/24")
        self.assertEqual(tmf.variable_action(CONTEXT, {}).detail["acceleration_hessian"], "Matrix([[2*x + 2, 0], [0, 2]])")
        self.assertTrue(tmf.weighted_identity(CONTEXT, {}).detail["certificate"]["valid"])

    @unittest.skipUnless((ROOT / ".tools/lean/bin/lean").is_file(), "toolchain Lean opzionale assente")
    def test_independent_lean_check_and_rejection(self):
        good = riemann.robin_arithmetic_proof(CONTEXT, {})
        self.assertEqual(good.claims[0].kind, Kind.FORMAL)
        self.assertTrue(good.detail["lean"]["valid"])
        with TemporaryDirectory() as temp:
            file = Path(temp) / "Bad.lean"
            file.write_text("theorem bad : False := by sorry\n")
            with self.assertRaisesRegex(ValueError, "vietati"):
                verify_lean(ROOT / ".tools/lean/bin/lean", file, {"bad": "False"}, cwd=ROOT)
            file.write_text("theorem one : 1 = 1 := rfl\n")
            wrong = verify_lean(ROOT / ".tools/lean/bin/lean", file, {"one": "1 = 2"}, cwd=ROOT)
            self.assertFalse(wrong["valid"])

    @unittest.skipUnless((ROOT / ".tools/lean/bin/lean").is_file(), "toolchain Lean opzionale assente")
    def test_generic_hypothesis_generation(self):
        import json
        raw = json.loads((ROOT / "sources/example-statement.json").read_text())
        result = audit_statement(CONTEXT, "riemann", raw)
        self.assertEqual(result.claims[0].kind, Kind.FORMAL)
        self.assertEqual(len(result.followups), 1)
        relaxed = audit_statement(CONTEXT, "riemann", result.followups[0].payload)
        self.assertEqual(relaxed.claims[0].kind, Kind.COUNTEREXAMPLE)

    @unittest.skipUnless((ROOT / ".tools/lean/bin/lean").is_file(), "toolchain Lean opzionale assente")
    def test_tmf_reference_lean(self):
        result = tmf.mean_connection(CONTEXT, {})
        self.assertTrue(result.detail["lean"]["valid"])
        self.assertIn("dp_tmf_mean_gap", result.detail["lean"]["axioms"])
