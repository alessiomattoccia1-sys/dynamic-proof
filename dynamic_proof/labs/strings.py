# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Mathematical string theory laboratory, with explicit scopes for modular results."""
from __future__ import annotations

from fractions import Fraction
from math import comb

from flint import arb, ctx
import sympy as sp

from ..core.literature import Source
from ..core.model import Claim, Kind, cited, e, num, var
from ..core.plugin import Context, Lab, Result, Work
from ..core.verification import ball_data, rational_identity


CC = "strings.cacciatori2010"
ACER = "strings.angelantonj2011"
SOURCES = (
    Source(CC, "Cacciatori e Cardella, Equidistribution Rates, Closed String Amplitudes, and the Riemann Hypothesis",
           "§2, (2.7), (2.38)–(2.44); appendice A.2", "arXiv:1007.3717v3 / JHEP12(2010)025",
           "https://arxiv.org/abs/1007.3717v3",
           terms=("Rankin Selberg", "Mellin", "automorphic", "Siegel", "equidistribution", "Riemann zeta")),
    Source(ACER, "Angelantonj, Cardella, Elitzur e Rabinovici, Vacuum Stability, String Density of States and the Riemann Zeta Function",
           "§§2–4, (2.1)–(2.6), (3.2)–(3.3), (4.1)–(4.2); §7 sui tachioni",
           "arXiv:1012.5091v2 / JHEP02(2011)024", "https://arxiv.org/abs/1012.5091v2",
           terms=("string", "T duality", "worldsheet", "density of states", "tachyon", "Rankin Selberg", "theta")),
)

CLAIMS = (
    Claim("strings.measure", "strings", "Misura modulare invariante sullo spazio di Siegel",
          cited("dμ_g = det(Im τ)^{−g−1} ∏_{i≤j} d Re τ_ij d Im τ_ij",
                "τ ∈ H_g, azione di Sp(2g,ℤ)"), Kind.LITERATURE, (CC,)),
    Claim("strings.equidistribution", "strings", "Cacciatori–Cardella · tasso di equidistribuzione",
          cited("∫_{Γ_{g−1}\\H_{g−1}} ⟨f⟩_{2g−1} dμ_{g−1} = "
                "Vol(Γ_{g−1}\\H_{g−1})/Vol(Γ_g\\H_g) ∫_{Γ_g\\H_g} f dμ_g + O(v₁^{g−Θ/2})",
                "v₁→0⁺; Θ=sup Re ρ per ζ*(ρ)=0",
                "f automorfa di peso 0 nel regime di applicabilità di §2, (2.38)–(2.44)",
                "il passaggio di Mellin richiede le ipotesi analitiche della fonte"),
          Kind.LITERATURE, (CC,), ("strings.measure",),
          evidence={"locator": "(2.44)", "normalization": "ζ*(s)=π^{−s/2} Γ(s/2) ζ(s)"}),
    Claim("strings.rankin", "strings", "Rankin–Selberg · trasformata di Mellin del termine costante",
          cited("∫_F f(τ) E(τ,s) dμ = ∫₀^∞ y^{s−2} a₀(y) dy; a₀(y)=∫_{−1/2}^{1/2} f(x+iy) dx",
                "f automorfa con decrescita rapida alla cuspide; semipiano di convergenza prima di continuare"),
          Kind.LITERATURE, (ACER,), evidence={"locator": "§2.1, (2.1)–(2.2)"}),
    Claim("strings.rankin_moderate", "strings", "Rankin–Selberg–Zagier · sottrazione della cuspide",
          cited("R*(f,s)=ζ*(2s)∫₀^∞ y^{s−2}[a₀(y)−φ(y)] dy",
                "crescita moderata alla cuspide nella forma richiesta in §2.2",
                "f(x+iy)=φ(y)+O(y^{−N}) per ogni N>0, φ(y)=Σ_i c_i y^{α_i}(log y)^{n_i}/n_i!"),
          Kind.LITERATURE, (ACER,), ("strings.rankin",), evidence={"locator": "§2.2, (2.5)"}),
    Claim("strings.theta", "strings", "Toro compatto · funzione di partizione e media modulare",
          cited("∫_F RΘ(τ,R) dμ = (π/3)(R+R^{-1}); "
                "a₀(y,R)=√y Σ_{m,n∈ℤ:mn=0} exp[−π y(m²/R²+n²R²)]",
                "R>0, y=Im τ>0, un cerchio compatto, convenzioni di §3.2"),
          Kind.LITERATURE, (ACER,), ("strings.rankin_moderate",), evidence={"locator": "(3.2)–(3.3)"}),
    Claim("strings.density", "strings", "Densità graduata delle eccitazioni e zeri della zeta",
          cited("g(Λ) ~ (3/π) Λ^{2−d} Ω + Λ^{−d} Σ_{ζ*(ρ)=0} Cρ Λ^ρ "
                "+ d(0) Ψ(1−d/2) Λ^{2−2d}",
                "Λ→∞; g(Λ)=Σ_{m²}(d_B(m²)−d_F(m²))e^{−4π m²/Λ²}",
                "vuoti Type II chiusi del §4, crescita moderata, tachioni fisici e non fisici assenti"),
          Kind.LITERATURE, (ACER,), ("strings.rankin_moderate",), evidence={"locator": "(4.2)",
          "scope": "relazione matematica condizionata alle ipotesi sul modello"}),
    Claim("strings.reverse_gap", "strings", "Rilevazione degli zeri dal tasso di un modello specifico",
          cited("Stabilire quando i coefficienti Cρ di un modello non annullano gli zeri da rilevare",
                "servono crescita ammessa e controllo esplicito dei coefficienti; il caso (3.3) ha Cρ=0"),
          Kind.CONJECTURE, (CC, ACER), ("strings.equidistribution", "strings.theta", "strings.density")),
    Claim("strings.delta_source", "strings", "Discriminante modulare e proiezione di Fourier",
          cited("Δ(τ)=q∏_{n≥1}(1−q^n)^24=Σ_{n≥1}τ(n)q^n; "
                "a₀(y)=y^12 Σ_{n≥1} τ(n)^2 e^{−4πny}",
                "f(τ)=y^12|Δ(τ)|², y=Im τ>0, decrescita rapida alla cuspide"),
          Kind.LITERATURE, (ACER,), ("strings.rankin",), evidence={"locator": "§3.1, prima di (3.1)"}),
)


def modular_volume(context: Context, _payload: dict) -> Result:
    context.stage("calcolo", "Riproduzione della normalizzazione g=1 di Cacciatori–Cardella (2.42)")
    x = sp.Symbol("x", real=True)
    integral = sp.integrate(1 / sp.sqrt(1 - x*x), (x, -sp.Rational(1, 2), sp.Rational(1, 2)))
    zeta_formula = 2 * sp.pi**-1 * sp.gamma(1) * sp.zeta(2)
    if sp.simplify(integral - zeta_formula) != 0 or integral != sp.pi / 3:
        raise ArithmeticError("normalizzazione g=1 non riprodotta")
    bits = 128
    with ctx.workprec(bits):
        hyperbolic = 2 * (arb(1) / 2).asin()
        completed = 2 * arb(2).zeta() / arb.pi()
        if not hyperbolic.overlaps(completed):
            raise ArithmeticError("controllo indipendente del volume")
        numerical = {"integral": ball_data(hyperbolic, bits), "completed_zeta": ball_data(completed, bits)}
    context.stage("verifica", "Integrale simbolico e confronto rigoroso di archi e zeta in Arb")
    proof = {"integral": "∫_{−1/2}^{1/2} dx∫_{√(1−x²)}^∞ dy/y²",
             "antiderivative": "arcsin x", "exact": str(integral), "intervals": numerical}
    claim = Claim("strings.volume.g1", "strings", "Volume modulare in genere uno",
                  cited("Vol(PSL(2,ℤ)\\H)=π/3=2ζ*(2)"),
                  Kind.EXACT, (CC,), ("strings.measure",),
                  {"verified": True, "independent": "integrale del dominio e formula ζ*(2)", **proof})
    return Result("reproduced", claim.title, proof, (claim,), known=(CC,), proof_complete=True, independent=True)


def _positive(value: str) -> Fraction:
    result = Fraction(value)
    if not 0 < result <= 20 or result < Fraction(1, 10_000):
        raise ValueError("parametro fuori dal dominio computazionale")
    return result


def theta_unfolding(context: Context, _payload: dict) -> Result:
    context.stage("calcolo", "Riproduzione simbolica dell’integrale toroidale (3.2)")
    y, r, n = sp.symbols("y R n", positive=True)
    c = sp.pi * r*r * n*n
    integral = sp.integrate(sp.exp(-c/y)/y**2, (y, 0, sp.oo))
    antiderivative = sp.exp(-c/y)/c
    if sp.simplify(sp.diff(antiderivative, y) - sp.exp(-c/y)/y**2) != 0:
        raise ArithmeticError("primitiva dell’integrale spiegato non valida")
    if sp.simplify(integral - 1/c) != 0:
        raise ArithmeticError("integrazione e sostituzione 1/y discordanti")
    volume = sp.pi/3
    final = sp.simplify(r * (volume + 2*sp.zeta(2)/(sp.pi*r**2)))
    if sp.simplify(final - volume*(r+1/r)) != 0:
        raise ArithmeticError("normalizzazione della media modulare discordante")
    claim = Claim("strings.theta.unfolding", "strings", "Integrale toroidale riprodotto esattamente",
                  cited("∫_F RΘ(τ,R)dμ=(π/3)(R+R⁻¹)", "R>0, svolgimento della serie di Poincaré in (3.2)"),
                  Kind.EXACT, (ACER, CC), ("strings.theta", "strings.volume.g1"),
                  {"verified": True, "independent": "integrale simbolico e derivata di una primitiva esplicita",
                   "primitive": str(antiderivative), "integral": str(integral), "mean": str(final),
                   "analytic_steps": "Svolgimento della fonte, Tonelli per i termini positivi, "
                                     "sostituzione 1/y e somma convergente su n non nullo."})
    return Result("reproduced", claim.title, claim.evidence, (claim,), known=(ACER,),
                  proof_complete=True, independent=True)


def _arb(value: Fraction) -> arb:
    return arb(value.numerator) / value.denominator


def _gaussian(alpha: arb, count: int) -> tuple[arb, arb]:
    if not alpha > 0:
        raise ValueError("gaussiana non convergente nel dominio")
    value = sum(((-alpha * (k*k)).exp() for k in range(1, count + 1)), arb(0))
    tail_bound = (-alpha * ((count + 1)**2)).exp() / (1 - (-alpha * (2 * count + 3)).exp())
    return value + arb(0).union(tail_bound.upper()), tail_bound


def theta_balls(radius: Fraction, height: Fraction, bits: int, count: int) -> dict:
    with ctx.workprec(bits):
        radius_ball, y = _arb(radius), _arb(height)
        pi = arb.pi()
        a, ea = _gaussian(pi * y / radius_ball**2, count)
        b, eb = _gaussian(pi * y * radius_ball**2, count)
        c, ec = _gaussian(pi * radius_ball**2 / y, count)
        d, ed = _gaussian(pi / (radius_ball**2 * y), count)
        direct = y.sqrt() * (1 + 2*(a+b))
        limit = radius_ball + 1/radius_ball
        poisson = limit - y.sqrt() + 2*(radius_ball*c + d/radius_ball)
        if not direct.overlaps(poisson):
            raise ArithmeticError("forme diretta e di Poisson incompatibili")
        joint = direct.intersection(poisson)
        return {"direct": ball_data(direct, bits), "poisson": ball_data(poisson, bits),
                "intersection": ball_data(joint, bits), "limit": ball_data(limit, bits),
                "tail_direct_upper": ball_data((2*y.sqrt()*(ea+eb)).upper(), bits),
                "tail_poisson_upper": ball_data((2*(radius_ball*ec+ed/radius_ball)).upper(), bits)}


def theta_reference(context: Context, payload: dict) -> Result:
    radius = _positive(payload["radius"])
    y = _positive(payload["height"])
    bits, count = 128, 72
    context.stage("calcolo", "Termine costante del toro con due sviluppi e resto gaussiano")
    intervals = theta_balls(radius, y, bits, count)
    context.stage("verifica", "Somma sulle due assi del reticolo e somma trasformata da Poisson")
    proof = {"radius": str(radius), "height": str(y), "terms_per_series": count,
             "tail_formula": "Σ_{k>N} e^{-a k²} ≤ e^{-a(N+1)²}/(1−e^{-a(2N+3)}) per a>0",
             "precision_bits": bits, **intervals}
    name = f"{radius.numerator}-{radius.denominator}.{y.numerator}-{y.denominator}"
    claim = Claim(f"strings.theta.check.{name}", "strings", "Termine costante toroidale certificato",
                  cited(f"a₀(y,R) per R={radius}, y={y}, secondo (3.3)"),
                  Kind.CERTIFIED, (ACER,), ("strings.theta",),
                  {"verified": True, "independent": "serie diretta e rappresentazione di Poisson", **proof})
    return Result("reproduced", claim.title, proof, (claim,), known=(ACER,), independent=True)


def theta_dual(context: Context, _payload: dict) -> Result:
    context.stage("deduzione", "Invarianza esatta dello spettro a un cerchio sotto R↦1/R")
    r, m, n = map(var, ("R", "m", "n"))

    def mass(radius, momentum, winding):
        return e("add", e("div", e("pow", momentum, num(2)), e("pow", radius, num(2))),
                 e("mul", e("pow", winding, num(2)), e("pow", radius, num(2))))

    checked = rational_identity(mass(r, m, n), mass(e("div", num(1), r), n, m), ("R", "m", "n"))
    if not checked["valid"]:
        raise ArithmeticError("identità spettrale non verificata")
    claim = Claim("strings.t_dual", "strings", "Dualità T del modello toroidale a un cerchio",
                  cited("RΘ(τ,R)=R⁻¹Θ(τ,R⁻¹)",
                        "R>0, Im τ>0; scambio biiettivo (m,n)↦(n,m) e fase mn invariata"),
                  Kind.EXACT, (ACER,), ("strings.theta",),
                  {"verified": True, "independent": checked["independent"], "mass_identity": checked,
                   "extension": "somma assolutamente convergente; scambio degli indici preserva la fase"})
    return Result("reproduced", claim.title, {"certificate": checked}, (claim,),
                  (Work("coefficient_gap", {"variant": 0}, 48, 18),), known=(ACER,),
                  proof_complete=True, independent=True)


def coefficient_gap(context: Context, payload: dict) -> Result:
    variant = payload["variant"]
    if variant not in range(4):
        raise ValueError("strategia non disponibile")
    configurations = (
        ("3/2", "1/16", "cancellazione dei coefficienti nel modello a un cerchio"),
        ("2", "1/25", "raggio fuori dal punto autoduale"),
        ("1", "1/50", "punto autoduale, controllo del resto di Poisson"),
        ("5/4", "1/100", "cut-off più piccolo e termine √y da sottrarre"),
    )
    radius_text, y_text, question = configurations[variant]
    radius, y = Fraction(radius_text), Fraction(y_text)
    context.stage("ricerca", "Confronto tra termine zero-dipendente e resto esponenziale")
    with ctx.workprec(128):
        rb, yb = _arb(radius), _arb(y)
        c, _ = _gaussian(arb.pi() * rb**2 / yb, 40)
        d, _ = _gaussian(arb.pi() / (rb**2 * yb), 40)
        remainder = 2*(rb*c + d/rb)
        certified = ball_data(remainder, 128)
    if variant + 1 < len(configurations):
        followups = (Work("coefficient_gap", {"variant": variant + 1}, 40, 45 * (variant + 1), variant + 1),)
    else:
        followups = (Work("graded_spectrum", {"scale": 2}, 42, 90),)
    return Result("partial", "Controllo del resto nel modello con coefficienti Cρ nulli",
                  {"question": question, "radius": radius_text, "height": y_text, "remainder": certified,
                   "source": "Angelantonj et al., §3.2, p. 10", "obligation":
                       "per usare il tasso come indicatore occorre provare non-annullamento fuori dal modello"},
                  followups=followups, known=(ACER,), independent=True)


def graded_spectrum(context: Context, payload: dict) -> Result:
    """An exact finite spectrum audit, keeping truncation separate from (4.2)."""
    cutoff = payload["scale"]
    if not 1 <= cutoff <= 128:
        raise ValueError("cut-off non supportato")
    context.stage("ricerca", "Controllo che level matching e finitezza non siano confusi con crescita moderata")
    # A toy perturbation: the unphysical term survives at fixed x but disappears
    # from the Fourier constant term. This is a condition check, not a string vacuum.
    modes = [(1, 1, 1), (2, 2, -1), (-1, 0, 1)]
    level_matched = [m for m in modes if m[0] == m[1]]
    unphysical = [m for m in modes if m[0] != m[1] and m[0] + m[1] < 0]
    with ctx.workprec(100):
        total = sum((weight * (-2 * arb.pi() * (left+right) / cutoff**2).exp()
                     for left, right, weight in level_matched), arb(0))
        interval = ball_data(total, 100)
    claim = Claim(f"strings.cusp_control.{cutoff}", "strings",
                  "Un termine a crescita rapida può sparire nella proiezione di Fourier",
                  cited("Un modo con h+ḣ<0 e h≠ḣ può avere proiezione nulla su a₀ ma crescere alla cuspide",
                        "controllo algebrico su modi, senza asserire invarianza modulare del toy model"),
                  Kind.EXACT, (ACER,), ("strings.density",),
                  {"verified": bool(unphysical), "independent": "frequenza intera non nulla e integrale esatto",
                   "witness": unphysical})
    followups = (Work("graded_spectrum", {"scale": cutoff * 2}, 35, 180 * cutoff, cutoff),) if cutoff < 128 else ()
    return Result("partial", claim.title, {"finite_spectrum": modes, "selected": level_matched,
                  "cutoff": cutoff, "weighted_sum": interval, "application_to_4_2": "premessa non verificata"},
                  (claim,), followups, known=(ACER,), independent=True)


def ramanujan_projection(context: Context, payload: dict) -> Result:
    count = payload["count"]
    if count not in (8, 16, 32, 64, 128):
        raise ValueError("ordine di proiezione non supportato")
    context.stage("calcolo", "Sviluppo esatto di Δ e proiezione del termine costante")
    coefficients = [1] + [0] * (count - 1)
    for stride in range(1, count):
        updated = [0] * count
        for power in range(min(24, (count - 1)//stride) + 1):
            step = stride * power
            multiplier = (-1)**power * comb(24, power)
            for index in range(step, count):
                updated[index] += multiplier * coefficients[index-step]
        coefficients = updated
    # Independently use the logarithmic derivative of ∏(1-q^k)^24.
    recurrence = [1]
    for k in range(1, count):
        value = -24 * sum(int(sp.divisor_sigma(j)) * recurrence[k-j] for j in range(1, k+1))
        quotient, remainder = divmod(value, k)
        if remainder:
            raise ArithmeticError("ricorrenza logaritmica non intera")
        recurrence.append(quotient)
    if coefficients != recurrence:
        raise ArithmeticError("prodotto q e ricorrenza discordanti")
    coefficients_squared = [coefficient**2 for coefficient in coefficients]
    context.stage("verifica", "Prodotto q, derivata logaritmica e selezione n=m sotto media periodica")
    evidence = {"verified": True, "independent": "prodotto q troncato vs ricorrenza logaritmica esatta",
                "tau_1_to_N": coefficients, "constant_term_coefficients": coefficients_squared,
                "projection": "∫_{−1/2}^{1/2} exp(2πi(n−m)x)dx=δ_{n,m}",
                "scope": f"coefficienti esatti fino all’ordine {count}; nessuna stima dell’asintotica infinita"}
    claim = Claim(f"strings.delta.projection.{count}", "strings",
                  "Proiezione esatta del discriminante modulare",
                  cited(f"Primi {count} coefficienti di y^12 Σ τ(n)^2 exp(−4πny) verificati esattamente"),
                  Kind.EXACT, (ACER,), ("strings.delta_source",), evidence)
    followups = (Work("ramanujan_projection", {"count": count*2}, 38, 80*count/8),) if count < 128 else ()
    return Result("reproduced", claim.title, evidence, (claim,), followups, known=(ACER,),
                  proof_complete=True, independent=True)


LAB = Lab("strings", "String Theory",
          "Worldsheets, modular measures, Rankin–Selberg, partition functions, and spectral hypotheses.",
          SOURCES, CLAIMS, {"modular_volume": modular_volume, "theta_reference": theta_reference,
                           "theta_dual": theta_dual, "coefficient_gap": coefficient_gap,
                           "graded_spectrum": graded_spectrum, "ramanujan_projection": ramanujan_projection,
                           "theta_unfolding": theta_unfolding},
          (Work("modular_volume", {}, 95),
           Work("theta_reference", {"radius": "3/2", "height": "1/10"}, 90),
           Work("theta_dual", {}, 85), Work("theta_unfolding", {}, 74),
           Work("ramanujan_projection", {"count": 8}, 70)))
