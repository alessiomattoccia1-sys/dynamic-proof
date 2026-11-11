# Scientific method

The sector contains left-handed Weyl fermions that are singlets under the other gauge groups. In four dimensions, the local perturbative anomaly conditions are \(\sum_i q_i=0\) and \(\sum_i q_i^3=0\). Opposite charges allow an invariant bilinear. Strict chirality excludes both opposite charge pairs and zero charges. Primitive normalization takes the greatest common divisor of the absolute charges. [Costa, Dobrescu, and Fox (2019)](https://doi.org/10.1103/PhysRevLett.123.151601)

## Integer classification

Each multiset has a unique nondecreasing vector. For \(n\) fermions and charge bound \(B\), direct enumeration has \(\binom{2B+n-1}{n}\) elements. The reduced strategy obtains \(s=x+y\) and \(t=x^3+y^3\) from each ordered prefix of length \(n-2\). For \(s\ne0\), the product must be \(xy=(s^3-t)/(3s)\). Divisibility, a square discriminant, parity, order, and bounds give exact tests on the roots. For \(s=0\), one needs \(t=0\) and \(y=-x\), which strict chirality excludes. Completeness refers to the search units of the chosen strategy.

The SMT model uses integer multiplicities \(m_q\ge0\) with linear sums whose coefficients are \(1,q,q^3\). Opposite charges cannot both have positive multiplicity. For each prime \(p\le B\), primitivity requires a present charge that is indivisible by \(p\). Blocking each model and obtaining UNSAT for the remainder completes the comparison with enumeration. If SMT hits a limit, an independent linear completion uses a prefix of length \(n-1\) when its cost fits the budget. The report also records the final Z3 status.

## Mass matrix

The allowed terms are \(y_{ij,a}\phi_a\psi_i\psi_j\) and terms with \(\phi_a^\dagger\), with \(|q_i+q_j|=|h_a|\). With nonzero vacuum expectation values and an independent coefficient per allowed symmetric entry, generic rank is the maximum rank achievable on the support.

A maximum matching between rows and columns of the support has the same cardinality as a minimum vertex cover. The cover, checked directly against every allowed entry, bounds the rank from above. Identifying row and column indices, the matching edges form paths, loops, and cycles. Adjacent pairs along a path or even cycle give invertible order-two blocks. Loops give order-one blocks. A simple odd cycle with its allowed entries set to one has determinant two. These blocks give a rational witness attaining the upper bound. The code checks equality using elimination over \(\mathbb Q\) and SymPy. It expands symbolic determinants up to order six, and up to order eight for sufficiently sparse supports. The cover certifies identically zero determinants.

The search tests scalar sets in increasing order of cardinality. A scalar charge absent from all absolute pair sums contributes empty support. The first invertible matrix certifies the minimum. A negative conclusion within the requested domain requires exhausting every specified set.

## Parity obstruction

A nonzero determinant term would require \(n\) sums \(q_{\sigma(i)}+q_i\) with total \(2\sum_i q_i=0\). If every allowed sum is an odd multiple of a nonzero integer \(d\), division by \(d\) would give an odd total for odd \(n\). Thus every determinant term has a zero factor. For one scalar take \(d=h\). For several scalar charges with the same 2-adic valuation, take \(d\) to be their common power of two. Lean verifies the determinant result for matrices over a commutative ring. The checked declarations are `dp_particle_one_scalar` and `dp_particle_odd_det`.

## Two scalar charges

For integers \(0<a<b\), let \(g=\gcd(a,b)\), \(a'=a/g\), and \(b'=b/g\). A sum of \(n\) labels from \(\{\pm a,\pm b\}\) is zero if the signed count differences \(u,v\) satisfy \(a'u+b'v=0\). Coprimality gives \((u,v)=(b'k,-a'k)\). The smallest number of terms for a given \(k\) is \(|k|(a'+b')\), and additional terms come in opposite pairs. For odd \(n\), the arithmetic condition is that \(a'+b'\) be odd and at most \(n\). Conversely, taking \(k=1\) and adding opposite pairs constructs a sum of length \(n\).

For five fermions, the arithmetically possible primitive ratios are \(1:2\), \(1:4\), and \(2:3\). Whether individual entries can be realized depends on the fixed fermion charges. PT-006 searches for singular support even when a compatible scalar sum exists. PT-007 cross-checks the criterion using dynamic programming on finite sums and records formalizing the arithmetic equivalence in Lean as an open obligation.

## One scalar and divisibility by four

Let \(h>0\) be an integer and let \(M\) be supported on pairs with \(q_i+q_j=\pm h\). If \(\sum_i q_i=0\) and at least one of \(h/2,-h/2\) is absent from the charge multiset, then \(\det M\ne0\) implies \(4\mid n\).

A nonzero determinant term gives a permutation in which labels \(+h,-h\) each appear \(n/2\) times, since their sum is \(2\sum_i q_i=0\). On the graph of distinct charges, each vertex has at most one neighbour of each label. A simple loop-free cycle would have to alternate labels. The composition of the two reflections \(x\mapsto h-x\) and \(x\mapsto -h-x\) is a nonzero translation, so an even number of alternating steps cannot close a cycle. The loop-free graph is therefore a forest. In the permutation cycles each non-loop edge is crossed an even number of times because it separates a cut of the forest. The label with no fixed point has no loops. Its count \(n/2\) is even.

A second proof uses multiplicities. Let \(p(x),m(x)\) count positive and negative labels leaving charge \(x\) in the permutation. Conservation of counts gives

\[
p(x)+m(x)=p(h-x)+m(-h-x).
\]

The difference \(D(x)=p(x)-p(h-x)=m(-h-x)-m(x)\) is antisymmetric under both reflections and therefore has period \(2h\). Its support is finite, so it vanishes identically. Each count is invariant under its own reflection. The label with no fixed point has an even count, giving \(4\mid n\).

Strict chirality ensures that at least one fixed point is absent. The known bound \(n\ge5\) with both anomalies cancelled therefore implies \(n\ge8\) for a single scalar. PT-012 attains this bound with \(q=(-7,-6,-3,1,1,2,4,8)\) and \(h=5\). The four pairs have sums \(+5,+5,-5,-5\) and absolute differences \(3,11,7,9\). A pair with sum \(s\) and difference \(d\) has cube sum \((s^3+3sd^2)/4\). The identity \(3^2+11^2=7^2+9^2=130\) gives cubic cancellation. Four symmetric off-diagonal blocks with coefficient one give determinant one. When both fixed points are present, \(q=(-1,1)\) and \(h=2\) permit an invertible diagonal matrix at \(n=2\).
