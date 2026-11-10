# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Number theory laboratory. Domain knowledge stays out of the core."""
from __future__ import annotations

from math import isqrt, prod

from flint import acb, arb, ctx
import mpmath as mp
from sympy import divisor_sigma, factorint

from ..core.logic import residual
from ..core.literature import Source
from ..core.model import Binder, Claim, Kind, Statement, TRUE, cited, disjunction, e, negate, num, opaque, var
from ..core.plugin import Context, Lab, Result, Work
from ..core.verification import ball_data, rational_identity, verify_lean


SOURCES = (
    Source("rh.clay", "Riemann Hypothesis", "Enunciato ufficiale e stato del problema", "consultato 2026-11-09",
           "https://www.claymath.org/millennium/Riemann-Hypothesis/"),
    Source("rh.hertlein", "Alexander Hertlein, Robin’s inequality for new families of integers",
           "INTEGERS 18 A71, teoremi 1–3", "2018", "https://math.colgate.edu/~integers/s71/s71.pdf",
           terms=("Robin", "prime valuations", "divisor sums", "upper bounds")),
    Source("rh.choie", "Choie, Lichiardopol, Moree e Solé, On Robin’s criterion for the Riemann hypothesis",
           "Theorem 1.2 e insieme delle eccezioni fino a 5040", "2007",
           "https://www.numdam.org/article/JTNB_2007__19_2_357_0.pdf", terms=("Robin", "odd integers", "divisor sums")),
    Source("rh.robin1984", "Robin1984 — formalizzazione Lean del criterio di Robin e Lagarias",
           "Solution.lean, dichiarazioni robin_inequality_iff_riemannHypothesis e riemann_hypothesis_iff_lagarias_elementary_criterion",
           "acab1a31f31e0499518a4416b63281e0b4838f9c",
           "https://github.com/kimihiro64/Robin1984/tree/acab1a31f31e0499518a4416b63281e0b4838f9c",
           terms=("Robin", "Lagarias", "colossally abundant", "Lean")),
    Source("rh.flint", "FLINT — zeri di Hardy e della zeta", "acb_dirichlet_zeta_zero",
           "python-flint 0.8.0", "https://flintlib.org/doc/acb_dirichlet.html",
           terms=("zeta zeros", "rigorous balls")),
    Source("rh.platt", "Platt e Trudgian, The Riemann hypothesis is true up to 3·10^12",
           "Verifica finita degli zeri per 0 < Im ρ ≤ 3·10^12", "2020 arXiv",
           "https://arxiv.org/abs/2004.09765", terms=("certified zeta zeros", "Riemann")),

)

n = var("n")
BINDERS = (Binder("n", "int"),)
ROBIN = opaque("σ(n) < e^γ n log(log n)")
STANDARD = e("gt", n, num(5040))
TARGET = Statement(BINDERS, STANDARD, (), ROBIN)
INCLUSIVE = Statement(BINDERS, e("ge", n, num(5040)), (), ROBIN)
HERTLEIN_DIVISORS = (2**20, 3**13, 5**8, 7**7, 11**6)


def scope_claim(identifier, title, condition, source):
    return Claim(identifier, "riemann", title, Statement(BINDERS, STANDARD, (condition,), ROBIN),
                 Kind.LITERATURE, (source,), evidence={"usable_for_coverage": True, "scope_reviewed": True})


ODD = scope_claim("riemann.odd", "Dispari sopra 5040", negate(e("divides", num(2), n)), "rh.choie")
H1 = scope_claim("riemann.hertlein1", "Hertlein · esponente di 2 al più 19",
                 negate(e("divides", num(HERTLEIN_DIVISORS[0]), n)), "rh.hertlein")
H2 = scope_claim("riemann.hertlein2", "Hertlein · esponenti di 3, 5, 7 o 11 limitati",
                 disjunction(*(negate(e("divides", num(d), n)) for d in HERTLEIN_DIVISORS[1:])), "rh.hertlein")
CLAIMS = (
    Claim("riemann.target", "riemann", "Disuguaglianza di Robin su tutti gli interi > 5040",
          TARGET, Kind.CONJECTURE, ("rh.robin1984",)),
    Claim("riemann.rh", "riemann", "Ipotesi di Riemann",
          cited("∀ ρ, ζ(ρ)=0 ∧ ρ non banale ⇒ Re(ρ)=1/2"), Kind.CONJECTURE, ("rh.clay",)),
    Claim("riemann.equivalence", "riemann", "Equivalenze Robin, Lagarias e Riemann",
          cited("RH ⇔ (∀ n>5040, σ(n)<e^γ n log(log n)) ⇔ (∀ n≥1, σ(n)≤H_n+exp(H_n) log(H_n))",
                "H_n = Σ_{j=1}^n 1/j"), Kind.LITERATURE, ("rh.robin1984",),
          evidence={"upstream_formalization": True, "local_kernel_check": False}),
    Claim("riemann.historical_zeros", "riemann", "Verifica finita pubblicata degli zeri",
          cited("∀ ρ=β+iγ, ζ(ρ)=0 ∧ 0<γ≤3·10^12 ⇒ β=1/2"),
          Kind.LITERATURE, ("rh.platt",), evidence={"scope": "finito, verifica esterna"}),
    ODD, H1, H2,
)


def sigma_by_pairs(value: int) -> int:
    return sum(d + (value // d if d * d != value else 0)
               for d in range(1, isqrt(value) + 1) if value % d == 0)


def robin_gap(value: int, sigma: int, bits: int) -> arb:
    with ctx.workprec(bits):
        return arb.const_euler().exp() * value * arb(value).log().log() - sigma


def robin_range(context: Context, payload: dict) -> Result:
    start, end = payload["start"], payload["end"]
    if not 2 <= start <= end <= 1_000_000 or end - start > 250:
        raise ValueError("intervallo Robin non supportato")
    bits = payload.get("bits", 100)
    if not 64 <= bits <= 384:
        raise ValueError("precisione non supportata")
    context.stage("calcolo", f"Somma dei divisori ed errore certificato per {start} ≤ n ≤ {end}")
    positive = []
    negative = []
    uncertain = []
    for value in range(start, end + 1):
        sigma = sigma_by_pairs(value)
        if sigma != int(divisor_sigma(value)):
            raise ArithmeticError(f"divergenze nella somma dei divisori di {value}")
        gap = robin_gap(value, sigma, bits)
        replay = robin_gap(value, sigma, bits + 24)
        if not gap.overlaps(replay):
            raise ArithmeticError(f"intervalli indipendenti dalla precisione disgiunti per {value}")
        row = {"n": value, "sigma": sigma, "threshold_minus_sigma": ball_data(gap, bits)}
        if gap > 0 and replay > 0:
            positive.append(row)
        elif gap < 0 and replay < 0:
            negative.append(row)
        else:
            uncertain.append(row)
    context.stage("verifica", "Controllo per coppie di divisori e SymPy, confronto Arb a due precisioni")
    claims = []
    if positive and not negative and not uncertain:
        finite = Statement(BINDERS, e("and", e("ge", n, num(start)), e("le", n, num(end))), (), ROBIN)
        claims.append(Claim(f"riemann.range.{start}.{end}.{bits}", "riemann",
                            f"Robin verificato per {start} ≤ n ≤ {end}", finite, Kind.CERTIFIED,
                            ("rh.robin1984",), evidence={"verified": True, "precision_bits": bits,
                             "independent": "due somme esatte; Arb a due precisioni",
                             "error_bounds": "estremi diadici per ogni n nel rapporto",
                             "count": len(positive), "interval": [start, end], "exhaustive": True}))
    for row in negative:
        value = row["n"]
        if value == 5040:
            statement, refs = INCLUSIVE, ("rh.choie",)
        else:
            statement, refs = (TARGET, ("rh.robin1984",)) if value > 5040 else (
                Statement(BINDERS, e("ge", n, num(2)), (), ROBIN), ("rh.choie",))
        claims.append(Claim(f"riemann.robin.refutation.{value}.{bits}", "riemann",
                            f"Robin · testimone n={value}", statement, Kind.COUNTEREXAMPLE, refs,
                            evidence={"verified": True, "witness": row, "precision_bits": bits,
                                      "independent": "sigma per coppie e SymPy; segno ricontrollato con Arb"}))
    next_work = ()
    if uncertain and bits < 300:
        next_work = (Work("robin_interval", {"start": start, "end": end, "bits": bits + 64}, 60, 30),)
    known = ("rh.choie",) if negative and all(row["n"] <= 5040 for row in negative) else ()
    return Result("inconclusive" if uncertain else ("refuted" if negative else "reproduced"),
                  f"Verifica di Robin nell’intervallo [{start}, {end}]",
                  {"checked": len(positive) + len(negative), "positives": positive, "negative": negative,
                   "inconclusive": uncertain, "precision_bits": bits, "input": payload,
                   "scope": "intervallo esaustivo; ciascun segno ha un limite d’errore"},
                  tuple(claims), next_work, known=known,
                  substantive=any(row["n"] > 5040 for row in negative),
                  independent=not uncertain)


def zeta_zeros(context: Context, payload: dict) -> Result:
    first, count = payload["first"], payload["count"]
    if not 1 <= first <= 600 or not 1 <= count <= 8:
        raise ValueError("intervallo di indici non supportato")
    bits = 112
    zeros = []
    context.stage("calcolo", f"Isolamento degli zeri indicizzati da {first} a {first + count - 1}")
    with ctx.workprec(bits), mp.workdps(42):
        for index in range(first, first + count):
            zero = acb.zeta_zero(index)
            if not zero.is_finite() or zero.real != arb("0.5") or not zero.zeta().contains(0):
                raise ArithmeticError(f"certificato Arb non utilizzabile per indice {index}")
            independent = mp.im(mp.zetazero(index))
            # mpmath is a numerical consistency check, not a second zero-count proof.
            if not zero.imag.overlaps(arb(mp.nstr(independent, 39))):
                raise ArithmeticError(f"valore indipendente incompatibile per indice {index}")
            zeros.append({"index": index, "real": ball_data(zero.real, bits), "imag": ball_data(zero.imag, bits),
                          "mpmath_height": mp.nstr(independent, 37)})
    context.stage("verifica", "Involucri Arb e confronto numerico mpmath")
    claim = Claim(f"riemann.zeros.{first}.{count}", "riemann", "Involucri certificati degli zeri indicizzati",
                  cited(f"Re ρ_k = 1/2 per gli indici {first}…{first+count-1} restituiti da FLINT"),
                  Kind.CERTIFIED, ("rh.flint", "rh.platt"),
                  evidence={"verified": True, "precision_bits": bits, "zeros": zeros,
                            "scope": "soltanto gli indici riportati", "comparison": "mpmath"})
    return Result("reproduced", claim.title, {"zeros": zeros, "scope": "insieme finito di indici"}, (claim,),
                  known=("rh.platt",), independent=True)


def robin_reduce(context: Context, _payload: dict) -> Result:
    context.stage("deduzione", "Sottrazione dei domini coperti e composizione delle divisibilità")
    reduction = residual(TARGET, [ODD, H1, H2])
    modulus = prod(HERTLEIN_DIVISORS)
    actual = [step["lcm"] for step in reduction.steps if step["rule"] == "lcm_divisibility"]
    if actual != [modulus]:
        raise ArithmeticError("la deduzione e il prodotto di potenze prime divergono")
    claim = Claim("riemann.residual", "riemann", "Riduzione del dominio residuo con Hertlein",
                  cited(f"Robin ∀ n>5040 ⇔ Robin ∀ n>5040 con {modulus}∣n",
                        "risultati di Choie e Hertlein validi nelle famiglie indicate"),
                  Kind.CONDITIONAL, ("rh.choie", "rh.hertlein"), reduction.dependencies,
                  evidence={"trace": reduction.data(), "independent": "mcm e prodotto di potenze coprime"})
    return Result("reproduced", claim.title, {"coverage": reduction.data(), "modulus": modulus}, (claim,),
                  (Work("factor_support", {"index": 0}, 53, 10),), known=("rh.hertlein",), independent=True)


SUPPORTS = ((2, 3, 5, 7, 11), (2, 3, 5, 7, 11, 13), (2, 3, 5, 7, 11, 13, 17),
            (2, 3, 5, 7, 11, 13, 17, 19, 23, 29))


def factor_support(context: Context, payload: dict) -> Result:
    index = payload["index"]
    support = SUPPORTS[index]
    bound = prod(HERTLEIN_DIVISORS)
    bits = 128
    context.stage("ricerca", "Costruzione di un limite uniforme per un supporto primo finito")
    numerator = prod(support)
    denominator = prod(p - 1 for p in support)
    with ctx.workprec(bits):
        lhs = arb(numerator) / denominator
        rhs = arb.const_euler().exp() * arb(bound).log().log()
        separation = rhs - lhs
        verified = separation > 0
        certificate = ball_data(separation, bits)
    expected_factors = dict(zip((2, 3, 5, 7, 11), (20, 13, 8, 7, 6)))
    if factorint(bound) != expected_factors:
        raise ArithmeticError("fattorizzazione del limite incongruente")
    claims = ()
    if verified:
        claim = Claim(f"riemann.support.{index}", "riemann", "Limite di Robin per supporto primo finito",
                      cited(f"σ(n) < e^γ n log(log n) per n≥{bound} con tutti i fattori primi in {support}",
                            "formula moltiplicativa di σ; log(log n) crescente per n>1"),
                      Kind.CONDITIONAL, ("rh.hertlein",), ("riemann.residual",),
                      evidence={"verification": certificate, "proof":
                                "σ(n)/n è un prodotto di somme geometriche troncate, ciascuna ≤ p/(p−1). "
                                "Il prodotto è minore di e^γ log(log bound), certificato con Arb."})
        claims = (claim,)
    next_work = (Work("factor_support", {"index": index + 1}, 45, 45 * (index + 1), index + 1),) \
        if index + 1 < len(SUPPORTS) else (Work("large_robin_search", {"start": 1, "count": 48}, 43, 60),)
    return Result("partial" if verified else "inconclusive", "Limite uniforme su una famiglia residua",
                  {"prime_support": list(support), "n_min": str(bound), "separation": certificate,
                   "verified": verified, "strategy": "prodotto di Eulero finito, tecnica standard"},
                  claims, next_work, known=("rh.hertlein",), independent=True)


def large_robin_search(context: Context, payload: dict) -> Result:
    start, count = payload["start"], payload["count"]
    if not 1 <= start <= 100_000 or not 1 <= count <= 80:
        raise ValueError("finestra dei cofattori non valida")
    context.stage("ricerca", f"Controllo dei cofattori {start}…{start+count-1} nel dominio residuo")
    base_factors = dict(zip((2, 3, 5, 7, 11), (20, 13, 8, 7, 6)))
    modulus = prod(HERTLEIN_DIVISORS)
    bits = 100
    rows = []
    claims = []
    ambiguous = 0
    for cofactor in range(start, start + count):
        factors = base_factors.copy()
        for prime, exponent in factorint(cofactor).items():
            factors[int(prime)] = factors.get(int(prime), 0) + int(exponent)
        value = modulus * cofactor
        if prod(p**a for p, a in factors.items()) != value:
            raise ArithmeticError("fattori non verificati")
        sigma = prod((p**(a + 1) - 1) // (p - 1) for p, a in factors.items())
        if sigma != prod(sum(p**k for k in range(a + 1)) for p, a in factors.items()):
            raise ArithmeticError("controllo indipendente del prodotto σ")
        gap = robin_gap(value, sigma, bits)
        if gap < 0:
            replay = robin_gap(value, sigma, bits + 32)
            if not replay < 0:
                ambiguous += 1
                continue
            witness = {"n": str(value), "sigma": str(sigma), "factors": factors, "gap": ball_data(gap, bits)}
            claims.append(Claim(f"riemann.large.refutation.{cofactor}", "riemann",
                                "Controesempio a Robin nel dominio residuo", TARGET, Kind.COUNTEREXAMPLE,
                                ("rh.hertlein", "rh.robin1984"), ("riemann.residual",),
                                {"verified": True, "witness": witness, "precision_bits": bits}))
        elif gap > 0:
            rows.append({"cofactor": cofactor, "gap": ball_data(gap, bits)})
        else:
            ambiguous += 1
    next_start = start + count
    delay = min(86400, 120 * (1 + next_start // 96)**2)
    followups = (Work("large_robin_search", {"start": next_start, "count": count}, 35, delay,
                      next_start // count),) if next_start <= 100_000 and not claims else ()
    return Result("refuted" if claims else "inconclusive", "Ricerca limitata di controesempi nel residuo",
                  {"modulus": str(modulus), "range_cofactors": [start, start + count - 1], "checked": rows,
                   "uncertain": ambiguous, "scope": "solo multipli esplicitamente esaminati"},
                  tuple(claims), followups, substantive=bool(claims), proof_complete=bool(claims),
                  independent=True)


def robin_arithmetic_proof(context: Context, _payload: dict) -> Result:
    context.stage("verifica", "Verifica Lean della fattorizzazione e della somma dei divisori di 5040")
    tools = context.root / ".tools" / "lean" / "bin"
    proofs = context.root / "proofs"
    expected = ("(2 : ℕ)^4 * 3^2 * 5 * 7 = 5040 ∧ "
                "(1 + 2 + 2^2 + 2^3 + 2^4 : ℕ) * (1 + 3 + 3^2) * (1 + 5) * (1 + 7) = 19344")
    check = verify_lean(tools / "lean", proofs / "Reference.lean", {"dp_divisors_5040": expected},
                        cwd=proofs, lake=tools / "lake", timeout=14)
    if not check["valid"]:
        return Result("inconclusive", "Verifica Lean di 5040", {"lean": check})
    if sigma_by_pairs(5040) != 19344:
        raise ArithmeticError("verifica aritmetica indipendente fallita")
    claim = Claim("riemann.lean.5040", "riemann", "Fattorizzazione e prodotto per σ(5040) in Lean",
                  cited(expected), Kind.FORMAL, ("rh.choie",),
                  evidence={"lean": check, "scope": "identità aritmetiche; la soglia trascendente è certificata separatamente"})
    return Result("reproduced", claim.title, {"lean": check}, (claim,),
                  known=("rh.choie",), proof_complete=True, independent=True)


def rankin_bridge(context: Context, _payload: dict) -> Result:
    context.stage("deduzione", "Trasferimento del tasso di equidistribuzione dal laboratorio stringhe")
    genus = var("g")
    exponent = e("sub", genus, e("div", num("1/2"), num(2)))
    expected = e("sub", genus, num("1/4"))
    proof = rational_identity(exponent, expected, ("g",))
    if not proof["valid"]:
        raise ArithmeticError("esponente di equidistribuzione non verificato")
    claim = Claim("riemann.rankin.transfer", "riemann", "Tasso di equidistribuzione sotto RH",
                  cited("RH ⇒ O(v₁^{g−1/4}) in (2.44)",
                        "ipotesi di Cacciatori–Cardella sulle funzioni automorfe; v₁→0⁺",
                        "Θ=1/2 sotto RH"),
                  Kind.CONDITIONAL, ("strings.cacciatori2010", "strings.angelantonj2011"),
                  ("strings.equidistribution", "strings.theta", "riemann.rh"),
                  evidence={"derivation": proof, "transfer": "strings → riemann",
                            "open": "una classe di test che rilevi i coefficienti non nulli degli zeri; "
                                    "il toro a un cerchio mostra un caso di annullamento"})
    return Result("partial", claim.title, claim.evidence, (claim,), known=("strings.cacciatori2010",),
                  proof_complete=True, independent=True)


LAB = Lab("riemann", "Riemann e teoria dei numeri",
          "Criterio di Robin, zeri della zeta, riduzioni su famiglie di interi e priorità analitiche.",
          SOURCES, CLAIMS, {"robin_interval": robin_range, "zeta_zeros": zeta_zeros,
                           "robin_reduce": robin_reduce, "factor_support": factor_support,
                           "large_robin_search": large_robin_search, "robin_arithmetic_proof": robin_arithmetic_proof,
                           "rankin_bridge": rankin_bridge},
          (Work("robin_interval", {"start": 5040, "end": 5040}, 95),
           Work("robin_interval", {"start": 5041, "end": 5100}, 85),
           Work("robin_reduce", {}, 80), Work("zeta_zeros", {"first": 1, "count": 3}, 75),
           Work("robin_arithmetic_proof", {}, 73), Work("rankin_bridge", {}, 65)),
          "riemann.target", (ODD.id, H1.id, H2.id))
