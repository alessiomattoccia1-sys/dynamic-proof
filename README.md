# Dynamic Proof Research Engine

Created by **Alessio Mattoccia**.

**Dynamics Lab · Engine 03 · v0.2.0**

Dynamic Proof runs local deductive research with a persistent scheduler, a SQLite registry, and a dashboard. It records domains, assumptions, provenance, and dependencies. It combines symbolic computation, certified interval arithmetic, counterexample searches, and optional formal verification.

| Laboratory | Included experiments |
| --- | --- |
| Riemann and number theory | Robin's criterion, divisibility reductions, finite Arb checks, and indexed zeta zeros. |
| String Theory | Genus-one toroidal integral, T-duality, constant terms, and modular projections. |
| TMF · Multiscale geometry | Levi-Civita connections, the DPR-003 counterexample, single-scale reduction, and variable-weight actions. |
| Particle Theory | Local U(1) anomalies, chiral equivalence, Yukawa mass rank, and a Lean-verified parity theorem. [Particle Theory manual](docs/particle_theory/README.md) |

TMF is a candidate theory. Each Robin report specifies its verification domain. The Riemann hypothesis remains open. [Engine page and reports](https://mattoccia.com/dynamics-lab/dynamic-proof/) · [Clay Mathematics Institute](https://www.claymath.org/millennium/riemann-hypothesis/)

## Getting started

The qualified environment is macOS on Apple Silicon with Python 3.12. Run the commands from the extracted archive or checkout.

~~~sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m dynamic_proof serve
~~~

Open the [local dashboard](http://127.0.0.1:8791/). On first start, the engine creates `state/`, registers the four labs, and begins running jobs. Press `Ctrl+C` to exit. Subsequent runs resume from the same registry.

~~~sh
.venv/bin/python -m dynamic_proof status
.venv/bin/python -m dynamic_proof control paused
.venv/bin/python -m dynamic_proof control running
.venv/bin/python -m dynamic_proof control stopped
~~~

`config.toml` controls per-experiment budgets, scheduling, the dashboard port, and literature search. The distributed configuration uses the local catalogue. Set `online_literature = true` to query arXiv, Crossref, and INSPIRE-HEP with the lab's search terms. Pass `--state` before the subcommand to use a separate registry.

~~~sh
.venv/bin/python -m dynamic_proof --state .work/demo run --cycles 8
.venv/bin/python -m dynamic_proof queue riemann sources/example-statement.json
.venv/bin/python -m dynamic_proof --state .local/particle-research init --lab particle_theory
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 30
~~~

The `queue` command accepts structured statements. In the linear integer fragment, the engine searches for counterexamples with SMT and attempts formal verification when Lean is configured. The optional `relax` field requests variants that remove one assumption at a time. On macOS, install the optional login service with `.venv/bin/python scripts/macos_service.py install`. The service writes logs to the state directory of the copy that installed it.

Use `--lab` with `init`, `run`, or `serve` to select a queue. Use `submit particle_theory FILE.json` to submit a specialist problem to the same runner. [Particle Theory schema and commands](docs/particle_theory/README.md)

## Reproduction and tests

The archive includes the public DPR-001, DPR-002, and DPR-003 data, SHA-256 manifests, and the replay script. [Public experiment index](https://mattoccia.com/dynamics-lab/dynamic-proof/PUBLIC_EXPORT.json)

~~~sh
.venv/bin/python experiments/verify-dynamic-proof.py.txt
.venv/bin/python -m unittest discover -s tests -v
~~~

The first command recomputes the three results. The test suite covers the core, scientific verifiers, dashboard endpoints, and recovery after interruption. Lean tests run when the toolchain is available.

### Optional formal verification

Place Lean **4.33.1**, with `bin/lean` and `bin/lake`, in `.tools/lean` or link the official distribution there. From `proofs/`, load the pinned dependencies.

~~~sh
cd proofs
PATH="$PWD/../.tools/lean/bin:$PATH" lake exe cache get Mathlib.Tactic.Ring Mathlib.Tactic.NormNum Mathlib.Data.Rat.Defs Mathlib.LinearAlgebra.Matrix.Determinant.Basic
cd ..
.venv/bin/python -m unittest discover -s tests -v
~~~

The kernel checks the expected types and axioms of the declarations. The reports identify the evidence for each claim, including formal identities, analytic arguments, published results, and numerical checks. [Official Lean 4.33.1 distribution](https://github.com/leanprover/lean4/releases/tag/v4.33.1)

## License

The original source code and included reproduction materials are distributed under the **Apache License 2.0**. Dependencies are installed separately and retain their own licenses. The experiment reports cite the scientific sources. [LICENSE](LICENSE) · [NOTICE](NOTICE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
