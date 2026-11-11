# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
import itertools
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from dynamic_proof.core.plugin import Context
from dynamic_proof.core.store import Store
from dynamic_proof.labs import particle_theory as pt
from dynamic_proof.labs.catalog import BY_ID


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = Context(ROOT, False, lambda *_: None)


def example(number):
    return json.loads((ROOT / f"experiments/particle/PT-{number:03d}.json").read_text(encoding="utf-8"))


def evaluate(raw):
    result = pt.run_problem(CONTEXT, pt.submit(raw).payload)
    while result.followups:
        result = pt.run_problem(CONTEXT, result.followups[0].payload)
    return result


class ParticleTheoryTests(unittest.TestCase):
    def test_pilot_exact_enumeration_and_smt(self):
        result = evaluate(example(1))
        self.assertEqual(result.status, "reproduced")
        self.assertEqual(result.known, ("baseline Particle Pilot",))
        self.assertEqual(result.detail["enumeration"]["offset"], 26_334)
        self.assertEqual(result.detail["oriented_assignments"], [pt.BASELINE, (-8, -7, 1, 5, 9)])
        check = result.detail["independent_check"]
        self.assertTrue(check["verified"])
        self.assertEqual(check["smt"]["status"], "SAT")
        self.assertEqual(check["smt"]["terminal_check"], "UNSAT")
        self.assertEqual(check["smt"]["models"], result.detail["oriented_assignments"])
        self.assertEqual(len(result.detail["models"]), 1)

    def test_reduction_matches_direct_scan_and_handles_opposite_pairs(self):
        base = pt.read_problem(example(1)) | {"budget": pt.DEFAULT_BUDGET | {"steps_per_cycle": 30_000}}
        direct = pt.scan(base, {})
        reduced = pt.scan(base | {"method": "quadratic"}, {})
        self.assertEqual(direct["rows"], reduced["rows"])
        self.assertTrue(reduced["complete"])
        self.assertLess(reduced["offset"], direct["offset"])
        pair = pt.read_problem({"id": "PAIR", "title": "Coppie", "type": "classification",
                                "fermions": 2, "charge_bound": 4, "strict_chirality": False,
                                "primitive": False})
        self.assertEqual(pt.scan(pair, {})["rows"], [(-4, 4), (-3, 3), (-2, 2), (-1, 1)])
        self.assertTrue(pt.chirality((-4, 4))["vector_like"])
        self.assertFalse(pt.chirality((-4, 4))["strict"])
        self.assertEqual(pt.chirality(tuple(-2*q for q in pt.BASELINE))["canonical"], list(pt.BASELINE))

    def test_exact_mass_and_minimum(self):
        result = evaluate(example(2))
        self.assertEqual(result.status, "reproduced")
        search, = result.detail["mass_searches"]
        self.assertEqual(search["minimum"], 2)
        one_scalar = [(scalars, rank) for scalars, rank, _ in search["rank_trace"] if len(scalars) == 1]
        self.assertEqual(len(one_scalar), 10)
        self.assertTrue(all(rank < 5 for _, rank in one_scalar))
        certificate = search["certificate"]
        self.assertEqual(certificate["scalar_charges"], [1, 2])
        self.assertEqual(certificate["determinant"], "b**2*c**2*d")
        self.assertEqual(certificate["generic_rank"], 5)
        self.assertEqual(certificate["witness_determinant"], "1")
        self.assertEqual(certificate["matrix"][2][2], "d")

    def test_rank_certificates_include_symmetric_odd_cycles(self):
        upper = list(itertools.combinations_with_replacement(range(3), 2))
        for bits in itertools.product((0, 1), repeat=len(upper)):
            support = [{j if i == row else i for (i, j), bit in zip(upper, bits)
                        if bit and row in (i, j)} for row in range(3)]
            support = tuple(tuple(sorted(row)) for row in support)
            matching, cover = pt.matching_certificate(support)
            witness = pt._mass_witness(3, matching)
            self.assertEqual(pt.exact_rank(witness)[0], len(matching))
            self.assertEqual(len(cover["rows"]) + len(cover["columns"]), len(matching))

    def test_finite_unsat_and_budget_exhaustion(self):
        result = evaluate(example(8))
        self.assertEqual(result.detail["outcome"], "UNSAT")
        self.assertTrue(result.detail["complete"])
        self.assertEqual(result.detail["qualified_models"], [])
        self.assertEqual(result.detail["enumeration"]["offset"], 5985)
        self.assertTrue(result.detail["independent_check"]["verified"])
        limited = example(1) | {"budget": {"max_steps": 12, "steps_per_cycle": 12}}
        result = pt.run_problem(CONTEXT, pt.submit(limited).payload)
        self.assertEqual(result.detail["outcome"], "budget_exhausted")
        self.assertEqual(result.followups[0].payload["problem"]["method"], "quadratic")
        self.assertEqual(result.claims, ())
        result = pt.run_problem(CONTEXT, result.followups[0].payload)
        self.assertEqual(result.detail["outcome"], "budget_exhausted")
        self.assertEqual(result.followups, ())

    def test_counterexample_to_arithmetic_sufficiency(self):
        result = evaluate(example(6))
        self.assertEqual(result.status, "refuted")
        conjecture, refutation = result.claims
        self.assertEqual(conjecture.statement.fingerprint(), refutation.statement.fingerprint())
        witness = refutation.evidence["witness"]
        self.assertEqual(witness["charges"], list(pt.BASELINE))
        self.assertEqual(sum(witness["signed_scalar_labels"]), 0)
        self.assertLess(witness["mass"]["generic_rank"], 5)
        self.assertEqual(witness["mass"]["determinant"], "0")

    def test_two_scalar_bound_and_independent_probe(self):
        result = evaluate(example(7))
        self.assertEqual(result.detail["counterexample_search"]["tested"], 330)
        self.assertTrue(pt.two_scalar_allowed(5, 3, 6))
        self.assertFalse(pt.two_scalar_allowed(5, 1, 6))
        self.assertFalse(pt.two_scalar_allowed(9, 3, 5))
        self.assertFalse(result.independent)
        self.assertEqual(result.claims[0].kind, "conditional")

    def test_mod_four_obstruction_and_eight_fermion_construction(self):
        proof = evaluate(example(11))
        self.assertTrue(proof.proof_complete and proof.independent)
        self.assertEqual(proof.claims[0].kind, "exact")
        self.assertTrue(proof.detail["counterexample_search"]["complete"])
        self.assertEqual(proof.detail["assumption_boundary"]["generic_rank"], 2)
        example_at_eight = evaluate(example(12)).detail
        self.assertTrue(example_at_eight["models"][0]["anomaly_free"])
        self.assertTrue(example_at_eight["models"][0]["chirality"]["strict"])
        self.assertEqual(example_at_eight["mass_searches"][0]["minimum"], 1)
        self.assertEqual(example_at_eight["mass_searches"][0]["certificate"]["generic_rank"], 8)
        self.assertEqual(example_at_eight["construction"]["squared_differences_by_pair_sum"], {5: 130, -5: 130})

    @unittest.skipUnless((ROOT / ".tools/lean/bin/lake").is_file(), "Lean non configurato")
    def test_no_go_full_lean_statement(self):
        result = evaluate(example(3))
        self.assertEqual(result.claims[0].kind, "formal", result.detail["lean"].get("output"))
        self.assertTrue(result.detail["counterexample_search"]["complete"])
        self.assertEqual(set(result.detail["lean"]["expected_types"]),
                         {"dp_particle_one_scalar", "dp_particle_odd_det"})

    def test_json_validation_and_equivalence(self):
        raw = example(2)
        signed = raw | {"fermion_charges": [-q for q in raw["fermion_charges"]]}
        self.assertEqual(pt.submit(raw).payload, pt.submit(signed).payload)
        for invalid in ({"fermions": True}, {"scalar_charges": [0]}, {"unknown": 5},
                        {"fermion_charges": [-9, -5, 0, 7, 8]}):
            with self.assertRaises(ValueError):
                pt.read_problem(raw | invalid)


class ParticleQueueTests(unittest.TestCase):
    def test_selective_run_submit_and_checkpoint_recovery(self):
        with TemporaryDirectory() as directory:
            state = Path(directory)
            store = Store(state / "research.sqlite3")
            store.register(ROOT, (BY_ID["riemann"],))
            cli = [sys.executable, "-B", "-m", "dynamic_proof", "--state", str(state)]

            def invoke(*args):
                result = subprocess.run([*cli, *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            invoke("init", "--lab", pt.ID)
            invoke("run", "--lab", pt.ID, "--cycles", "1")
            first, = store.snapshot()["runs"]
            self.assertEqual(first["lab"], pt.ID)
            self.assertEqual(first["summary"]["examined"], 10_000)
            interrupted = store.next_job(100, pt.ID)
            self.assertEqual(interrupted["payload"]["checkpoint"]["offset"], 10_000)
            invoke("run", "--lab", pt.ID, "--cycles", "2")
            runs = store.snapshot()["runs"]
            self.assertEqual({r["lab"] for r in runs}, {pt.ID})
            self.assertTrue(any(r["status"] == "interrupted" for r in runs))
            self.assertEqual(runs[0]["summary"]["examined"], 26_334)
            self.assertTrue(any(c["lab"] == "riemann" and c["status"] == "queued"
                                for c in store.snapshot()["counts"]))
            file = str(ROOT / "experiments/particle/PT-006.json")
            self.assertIn("queued", invoke("submit", pt.ID, file))
            self.assertIn("already registered", invoke("submit", pt.ID, file))
            invoke("run", "--lab", pt.ID, "--cycles", "1")
            refuted = [claim for claim in store.snapshot()["claims"] if claim["refuted_by"]]
            self.assertTrue(any(claim["lab"] == pt.ID for claim in refuted))
