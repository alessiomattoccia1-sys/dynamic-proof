# Results of the first Particle Theory programme

Mac mini, 10–11 November 2026. The runner completed 20 attempts, including checkpoints, out of a budget of 30. PT-001–PT-010 came from the initial queue. PT-010 prompted PT-011 and PT-012, submitted to the same registry. The subsequent run found the queue exhausted.

| Problem | Verified outcome |
| --- | --- |
| PT-001 | 26,334 multisets. Two oriented assignments, one primitive class modulo global sign. Enumeration and Z3 agree. |
| PT-002 | All ten one-scalar supports are singular for the reference model. The minimum is two. For \(h=(1,2)\), the generic rank is 5, the determinant is \(b^2c^2d\), and an explicit witness has determinant 1. |
| PT-003 | Lean verifies the odd one-scalar case and the version for odd multiples of a common integer. The finite search examined 1,365 prefixes and 1,174 one-scalar supports. |
| PT-004 | Six primitive chiral classes for \(n=6\), \(\lvert q_i\rvert\le12\), across 17,550 ordered prefixes. |
| PT-005 | Two locally anomaly-free classes for \(n=5\), \(\lvert q_i\rvert\le14\). One admits rank 5 with at most two scalars from the pool 1–6. It is the pilot class, with pairs \((1,2)\) and \((2,3)\). |
| PT-006 | For the pilot model with \(h=(3,6)\), the label sum \(6+3+3-6-6\) is zero, yet the generic rank is 4. This refutes sufficiency of the arithmetic condition. |
| PT-007 | For odd \(n\), the two-scalar arithmetic criterion is that \((a+b)/\gcd(a,b)\) be odd and at most \(n\). Analytic derivation and 330 exact dynamic-programming comparisons. |
| PT-008 | UNSAT for four fermions with \(\lvert q_i\rvert\le9\), after 5,985 multisets and a Z3 cross-check. |
| PT-009 | 22 primitive chiral classes for \(n=7\), \(\lvert q_i\rvert\le12\), across 98,280 ordered prefixes. |
| PT-010 | None of the six PT-004 classes reaches rank 6 with one scalar. Each has maximum rank 4 within the search domain. |
| PT-011 | Two analytic proofs of \(4\mid n\) when one scalar gives full mass rank, \(\sum q_i=0\), and at least one of the fixed points \(h/2,-h/2\) is absent. The finite check examined 2,002 prefixes and 1,056 six-fermion supports. |
| PT-012 | \(q=(-7,-6,-3,1,1,2,4,8)\), \(h=5\). Both anomaly sums vanish. The support admits rank 8 and an integer witness of determinant 1. |

## Eight-fermion threshold

PT-011 gives a lower bound of eight in the chiral sector with both anomalies cancelled, using the published general minimum of five fermions. PT-012 attains the bound with a single scalar. The dossier records the charge-graph proof, the multiplicity proof, and the \(n=2\) example that shows why the fixed-point assumption matters. Lean formalization of PT-011 and the priority check remain open. [Method and proofs](SCIENTIFIC_METHOD.md) · [Costa, Dobrescu, and Fox (2020)](https://doi.org/10.1103/PhysRevD.101.095032)

The registry classified PT-011 and PT-012 as new to the session. For PT-011, it records Crossref, arXiv, and INSPIRE-HEP responses and comparison with primary sources. The targeted search for the threshold allowing Majorana masses remains open. [Prior-art comparison](PRIOR_ART.md)

The reproducibility commands write dossiers under the selected state directory's `reports/`. In the first run, attempts 5, 11, and 19 contained LaTeX drafts. Attempt 20 recorded the eight-fermion matrix, symbolic polynomial, and witness. [Reproduction and resumption](REPRODUCIBILITY.md)
