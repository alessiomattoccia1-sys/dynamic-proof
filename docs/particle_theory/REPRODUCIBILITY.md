# Reproducibility

Particle Theory development started from commit `fd2512333d903467a34dd4eae048ea3429faaf8c`. The preceding release, `v0.1.0`, was at commit `42d04e95c5cd7c44befda4aacb976fe0a0064167`. [Repository](https://github.com/alessiomattoccia1-sys/dynamic-proof)

The pilot ZIP was unavailable during qualification. The tests reconstruct the baseline from the specified inputs and an independent enumeration. For \((-9,-5,-1,7,8)\), both the linear and cubic sums vanish. The two sign orientations form one class among 26,334 multisets. The matrix for \(h=(1,2)\) has determinant \(b^2c^2d\). Setting \(a=b=c=d=1\) gives determinant one.

~~~sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python experiments/verify-dynamic-proof.py.txt
.venv/bin/python -m dynamic_proof --state .local/particle-research init --lab particle_theory
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 30
~~~

For formal verification, use Lean 4.33.1 and the mathlib commit pinned in `proofs/lake-manifest.json`. With Lean in `.tools/lean/bin` and the Lake dependencies installed, `test_no_go_full_lean_statement` checks types, the source hash, and the axioms of both declarations. Reports identify which results have formal proofs, analytic arguments, or finite checks.

~~~sh
cd proofs
PATH="$PWD/../.tools/lean/bin:$PATH" lake env lean --trust=0 ParticleNoGo.lean
~~~

The `research.sqlite3` registry stores attempts, checkpoint transactions, artifacts, dependencies, and literature assessments. The state directory's `reports/` holds JSON and Markdown for completed attempts and LaTeX drafts for derivations with a dossier. Compile the drafts with XeLaTeX. Reports include the normalized input digest and library versions.

~~~sh
.venv/bin/python -m dynamic_proof --state .local/particle-research status
.venv/bin/python -m dynamic_proof --state .local/particle-research serve --lab particle_theory --port 8791
~~~

To enable the three literature channels, copy `config.toml`, set `online_literature = true`, and pass `--config PATH` before the subcommand.

~~~sh
.venv/bin/python -m dynamic_proof --state .local/particle-research control paused
.venv/bin/python -m dynamic_proof --state .local/particle-research control running
.venv/bin/python -m dynamic_proof --state .local/particle-research run --lab particle_theory --cycles 30
~~~

`control stopped` stops active work. After restarting, `control running` makes the queue runnable again. To explore a new domain or raise the budget of a problem that hit a computational limit, update the JSON and use `submit`. The registry retains the previous attempt.
