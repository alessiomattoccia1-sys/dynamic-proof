// Copyright 2026 Alessio Mattoccia
// SPDX-License-Identifier: Apache-2.0
"use strict";

const labels = {
  formal: ["Proved in Lean", "green"], exact: ["Exact verification", "green"],
  literature: ["Published result", "blue"], conditional: ["Conditional consequence", "amber"],
  certified_numeric: ["Numerical certificate", "green"], exploratory: ["Exploratory", "neutral"],
  conjecture: ["Open problem or hypothesis", "amber"], counterexample: ["Verified counterexample", "red"],
  original_candidate: ["Original candidate · C", "green"]
};
const runLabels = {
  running: ["In progress", "green"], reproduced: ["Reproduced", "green"], partial: ["Partial", "blue"],
  refuted: ["Refuted", "red"], inconclusive: ["Inconclusive", "amber"],
  interrupted: ["Interrupted", "neutral"], failed: ["Error", "red"], verified: ["Verified", "green"]
};
const problemLabels = {
  SAT: "Solutions found", UNSAT: "No solution in the domain", UNKNOWN: "Incomplete search",
  checkpoint: "Checkpoint", budget_exhausted: "Budget exhausted", proved: "Proved in Lean",
  proof_obligation: "Lean verification pending", analytic_derivation: "Analytic derivation",
  counterexample: "Verified counterexample", counterexample_absent: "No counterexample in the domain"
};

// Translate built-in titles at display time. Registry records are immutable.
const englishTitles = new Map([
  [
    "Ostruzione di parità per cariche scalari",
    "Parity obstruction for scalar charges"
  ],
  [
    "Selezione delle entrate di massa U(1)",
    "Selection rule for U(1) mass entries"
  ],
  [
    "Condizioni locali di anomalia U(1)",
    "Local U(1) anomaly conditions"
  ],
  [
    "La connessione commuta con la media metrica",
    "The connection commutes with metric averaging"
  ],
  [
    "Discriminante modulare e proiezione di Fourier",
    "Modular discriminant and Fourier projection"
  ],
  [
    "Rilevazione degli zeri dal tasso di un modello specifico",
    "Detecting zeros from the rate of a specific model"
  ],
  [
    "Densità graduata delle eccitazioni e zeri della zeta",
    "Graded density of excitations and zeta zeros"
  ],
  [
    "Toro compatto · funzione di partizione e media modulare",
    "Compact torus · partition function and modular average"
  ],
  [
    "Rankin–Selberg–Zagier · sottrazione della cuspide",
    "Rankin–Selberg–Zagier · cusp subtraction"
  ],
  [
    "Rankin–Selberg · trasformata di Mellin del termine costante",
    "Rankin–Selberg · Mellin transform of the constant term"
  ],
  [
    "Cacciatori–Cardella · tasso di equidistribuzione",
    "Cacciatori–Cardella · equidistribution rate"
  ],
  [
    "Misura modulare invariante sullo spazio di Siegel",
    "Invariant modular measure on Siegel space"
  ],
  [
    "Hertlein · esponenti di 3, 5, 7 o 11 limitati",
    "Hertlein · bounded exponents of 3, 5, 7, or 11"
  ],
  [
    "Hertlein · esponente di 2 al più 19",
    "Hertlein · exponent of 2 at most 19"
  ],
  [
    "Dispari sopra 5040",
    "Odd integers above 5040"
  ],
  [
    "Verifica finita pubblicata degli zeri",
    "Published finite verification of zeros"
  ],
  [
    "Equivalenze Robin, Lagarias e Riemann",
    "Robin, Lagarias, and Riemann equivalences"
  ],
  [
    "Ipotesi di Riemann",
    "Riemann hypothesis"
  ],
  [
    "Disuguaglianza di Robin su tutti gli interi > 5040",
    "Robin's inequality for all integers > 5040"
  ],
  [
    "Controesempio alla commutazione delle medie",
    "Counterexample to commutation with averaging"
  ],
  [
    "Riduzione monoscala dell’azione metrica",
    "Single-scale reduction of the metric action"
  ],
  [
    "Commutatore esatto per due coefficienti metrici",
    "Exact commutator for two metric coefficients"
  ],
  [
    "L’azione con pesi variabili conserva un termine di derivata della misura",
    "The variable-weight action retains a derivative of the measure"
  ],
  [
    "Volume modulare in genere uno",
    "Genus-one modular volume"
  ],
  [
    "Integrale toroidale riprodotto esattamente",
    "Exact reproduction of the toroidal integral"
  ],
  [
    "Termine costante toroidale certificato",
    "Certified toroidal constant term"
  ],
  [
    "Dualità T del modello toroidale a un cerchio",
    "T-duality of the one-circle toroidal model"
  ],
  [
    "Involucri certificati degli zeri indicizzati",
    "Certified enclosures of indexed zeros"
  ],
  [
    "Riduzione del dominio residuo con Hertlein",
    "Remaining-domain reduction using Hertlein's result"
  ],
  [
    "Limite di Robin per supporto primo finito",
    "Robin bound for finite prime support"
  ],
  [
    "Fattorizzazione e prodotto per σ(5040) in Lean",
    "Factorization and product for σ(5040) in Lean"
  ],
  [
    "Tasso di equidistribuzione sotto RH",
    "Equidistribution rate conditional on RH"
  ],
  [
    "Baseline chirale con cinque fermioni e cariche fino a 9",
    "Five-fermion chiral baseline with charges bounded by 9"
  ],
  [
    "Minimo di scalari per il modello di riferimento",
    "Minimum scalar count for the reference model"
  ],
  [
    "Ostruzione universale per n dispari e cariche scalari di uguale valutazione 2-adica",
    "Universal obstruction for odd n and scalar charges of equal 2-adic valuation"
  ],
  [
    "Classificazione con sei fermioni e cariche fino a 12",
    "Classification for six fermions with charges bounded by 12"
  ],
  [
    "Classificazione chirale con massa piena e scalari di piccola carica",
    "Chiral classification with full mass rank and small scalar charges"
  ],
  [
    "Ricerca di una confutazione del criterio aritmetico di massa",
    "Counterexample search for the arithmetic mass criterion"
  ],
  [
    "Vincolo esatto su due cariche scalari per n dispari",
    "Exact constraint on two scalar charges for odd n"
  ],
  [
    "Verifica finita dell'assenza di modelli strettamente chirali con quattro fermioni",
    "Finite exclusion of strictly chiral models with four fermions"
  ],
  [
    "Classificazione con sette fermioni e cariche fino a 12",
    "Classification for seven fermions with charges bounded by 12"
  ],
  [
    "Masse con uno scalare nel settore pari a sei fermioni",
    "One-scalar masses in the six-fermion sector"
  ],
  [
    "Condizione 4 divisore di n per un solo scalare",
    "Divisibility of n by four for a single scalar"
  ],
  [
    "Costruzione chirale con otto fermioni e uno scalare",
    "Chiral construction with eight fermions and one scalar"
  ]
]);
const displayTitle = (title) => englishTitles.get(title) ?? title;

const byId = (id) => document.getElementById(id);
const text = (id, value) => { byId(id).textContent = value; };
const node = (tag, value, css) => {
  const element = document.createElement(tag);
  if (value !== undefined) element.textContent = value;
  if (css) element.className = css;
  return element;
};
const pill = ([label, color]) => node("span", label, "pill " + color);
const shortStrategy = (name) => name === "@literature" ? "literature" : name.replaceAll("_", " ");
const formatTime = (seconds) => new Date(seconds * 1000).toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"});
let state;
let sourceMap = new Map();
let controlsLocked = false;
let coverageRequest = 0;
let coverageVersion = "";
let renderSignature = "";

async function json(url, options) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Invalid response");
  return result;
}

function notice(message) {
  const box = byId("notice");
  box.hidden = !message;
  box.textContent = message || "";
}

function buttons() {
  const mode = state?.settings.control;
  for (const button of document.querySelectorAll("[data-mode]")) {
    button.disabled = controlsLocked || !state || button.dataset.mode === mode;
  }
}

function renderStats() {
  const {settings, runner_online: online} = state;
  const mode = settings.control;
  byId("runner-dot").className = "indicator " + (online && mode === "running" ? "online" : online ? "" : "offline");
  text("runner-status", online ? {running: "Core online", paused: "Research paused", stopped: "Research stopped"}[mode] : "Orchestrator offline");
  text("runner-note", online ? (mode === "running" ? "Checkpointing enabled" : "Registry available") : "Connecting to the local registry");
  text("count-labs", state.labs.length);
  text("count-runs", state.totals?.attempts ?? state.runs.filter((run) => run.ended).length);
  const evidence = state.totals?.evidence;
  text("count-verified", evidence ?
    ["formal", "exact", "certified_numeric", "counterexample"].reduce((total, key) => total + (evidence[key] || 0), 0) :
    state.claims.filter((claim) => ["formal", "exact", "certified_numeric", "counterexample"].includes(claim.kind)).length);
  text("count-original", evidence?.original_candidate ?? state.claims.filter((claim) => claim.kind === "original_candidate").length);
  const active = state.active[0];
  const labName = state.labs.find((lab) => lab.id === active?.lab)?.title;
  text("active-label", active ? "Active cycle" : "Idle");
  text("active-run", active ? (labName || active.lab) + " · " + (displayTitle(active.problem) || shortStrategy(active.strategy)) :
    "No experiment running");
  text("active-detail", active ? "Stage " + active.stage + " · started at " + formatTime(active.started) : "The registry stores queues and previous attempts.");
  const {wall_seconds: wall, cpu_seconds: cpu, memory_mb: mem, max_jobs_per_day: daily} = state.limits;
  text("limits", "Limits per experiment · " + wall + " s elapsed · " + cpu + " s CPU · " + mem + " MiB RAM");
  const rss = (Number(settings.worker_rss_kib || 0) / 1024).toFixed(1);
  text("consumption", active ? "Observed usage · " + rss + " MiB · CPU " + (settings.worker_cpu_seconds || 0) + " s" :
    "Budget " + daily + " attempts per 24 hours · Lean, SymPy, Arb, and SMT");
  buttons();
}

function initializeFilters() {
  for (const lab of state.labs) {
    const option = node("option", lab.title);
    option.value = lab.id;
    byId("lab-filter").append(option);
  }
  for (const [key, [label]] of Object.entries(labels)) {
    const option = node("option", label);
    option.value = key;
    byId("kind-filter").append(option);
  }
}

function renderLabs() {
  const container = byId("labs");
  container.replaceChildren();
  state.labs.forEach((lab, index) => {
    const counts = Object.fromEntries(state.counts.filter((row) => row.lab === lab.id).map((row) => [row.status, row.count]));
    const card = node("article", undefined, "lab");
    card.append(node("span", "LAB / 0" + (index + 1), "lab-tag"), node("h3", lab.title), node("p", lab.summary));
    const footer = node("footer");
    footer.append(pill([String(counts.queued || 0) + " queued", "neutral"]),
      pill([String(counts.done || 0) + " completed", "blue"]));
    if (counts.running) footer.append(pill(["Active", "green"]));
    if (counts.failed) footer.append(pill([counts.failed + " errors", "red"]));
    const button = node("button", "View registry");
    button.type = "button";
    button.onclick = () => {
      byId("lab-filter").value = lab.id;
      renderClaims();
      byId("registro").scrollIntoView();
    };
    card.append(footer, button);
    container.append(card);
  });
}

async function renderCoverage() {
  const lab = state.labs.find((item) => item.coverage_target);
  if (!lab) return;
  byId("coverage").hidden = false;
  const options = byId("coverage-choices");
  const claims = new Map(state.claims.map((claim) => [claim.id, claim]));
  const renderedOptions = new Set([...options.querySelectorAll("input")].map((input) => input.value));
  for (const id of lab.coverage_options) {
      if (renderedOptions.has(id)) continue;
      const label = node("label");
      const checkbox = node("input");
      checkbox.type = "checkbox";
      checkbox.value = id;
      checkbox.checked = lab.coverage_defaults.includes(id);
      checkbox.onchange = renderCoverage;
      label.append(checkbox, document.createTextNode(displayTitle(claims.get(id)?.title) || id));
      options.append(label);
  }
  const query = new URLSearchParams();
  options.querySelectorAll("input:checked").forEach((input) => query.append("include", input.value));
  if (!query.has("include")) query.append("include", "");
  const signature = query.toString() + JSON.stringify(lab.coverage_options.map((id) => [claims.get(id)?.quarantine, claims.get(id)?.refuted_by]));
  if (coverageVersion === signature) return;
  coverageVersion = signature;
  const request = ++coverageRequest;
  try {
    const result = await json("/api/coverage/" + lab.id + "?" + query);
    if (request !== coverageRequest) return;
    const display = result.display;
    text("coverage-formula", [display.quantifiers, display.domain, ...display.hypotheses].join(" · ") + " ⇒ " + display.conclusion);
    const steps = byId("coverage-steps");
    steps.replaceChildren(...result.steps.map((step) => node("li", step.rule === "lcm_divisibility" ?
      "Composition by least common multiple · " + step.lcm_text :
      (displayTitle(claims.get(step.claim)?.title) || step.claim) + " · remaining condition: " + step.remaining_condition)));
    byId("coverage-trace").hidden = !result.steps.length;
  } catch (error) {
    if (request !== coverageRequest) return;
    coverageVersion = "";
    text("coverage-formula", error.message);
  }
}

function renderClaims() {
  const lab = byId("lab-filter").value;
  const kind = byId("kind-filter").value;
  const query = byId("search-filter").value.toLowerCase();
  const items = state.claims.filter((item) => (!lab || item.lab === lab) && (!kind || item.kind === kind) &&
    (displayTitle(item.title) + " " + item.display.conclusion + " " + item.sources.join(" ")).toLowerCase().includes(query));
  text("result-count", items.length + " entries");
  const container = byId("claim-list");
  container.replaceChildren();
  if (!items.length) container.append(node("p", "No results match these filters.", "panel muted"));
  for (const item of items) {
    const button = node("button", undefined, "claim-row");
    button.type = "button";
    const first = node("span");
    first.append(node("span", displayTitle(item.title), "row-title"),
      node("span", state.labs.find((lab) => lab.id === item.lab)?.title || item.lab, "row-lab"));
    let badge = labels[item.kind] || [item.kind, "neutral"];
    if (item.quarantine) badge = ["Under review", "red"];
    if (item.refuted_by?.length) badge = ["Refuted", "red"];
    button.append(first, pill(badge));
    button.onclick = () => openClaim(item.id);
    container.append(button);
  }
}

function renderRuns() {
  const rows = [];
  for (const run of state.runs) {
    const tr = node("tr");
    const display = runLabels[run.status] || [run.status, "neutral"];
    const status = node("td");
    status.append(pill(display));
    const timing = run.stats ? run.stats.wall_seconds.toFixed(2) + " s" : "—";
    const report = node("td", run.artifact ? undefined : "—");
    if (run.artifact) {
      const number = String(run.id).padStart(6, "0");
      const md = node("a", "MD");
      const data = node("a", "JSON");
      md.href = "/api/report/" + number + ".md";
      data.href = "/api/report/" + number + ".json";
      report.append(md, document.createTextNode(" · "), data);
    }
    tr.append(node("td", "#" + run.id), node("td", run.lab),
      node("td", displayTitle(run.summary?.problem || run.problem) || shortStrategy(run.strategy)),
      status, node("td", timing), report);
    rows.push(tr);
  }
  byId("runs").replaceChildren(...rows);
  byId("events").replaceChildren(...state.events.slice(0, 28).map((event) =>
    node("li", [formatTime(event.at), event.lab, event.action, event.detail.detail || event.detail.strategy]
      .filter(Boolean).join(" · "))));
}

function renderParticle() {
  const section = byId("particle-theory");
  section.hidden = !state.labs.some((lab) => lab.id === "particle_theory");
  if (section.hidden) return;
  const active = state.active.find((run) => run.lab === "particle_theory");
  text("particle-active", active ? (displayTitle(active.problem) || "Active research") + " · " + active.stage : "Registry available");
  const latest = new Map();
  for (const run of state.runs) {
    const problem = run.summary?.problem || run.problem;
    if (run.lab === "particle_theory" && run.artifact && problem && !latest.has(problem)) {
      latest.set(problem, run);
    }
  }
  const rows = [];
  for (const [problem, run] of latest) {
    const data = run.summary || {outcome: run.status};
    const tr = node("tr");
    const view = node("button", "Open " + problem);
    view.type = "button";
    view.onclick = () => openParticleRun(run);
    const control = node("td");
    control.append(view);
    tr.append(node("td", problem), node("td", problemLabels[data.outcome] || runLabels[data.outcome]?.[0] || data.outcome),
      node("td", data.examined === undefined ? "—" : data.examined + " / " + data.total, "progress-count"),
      node("td", data.models ?? "—"), node("td", data.excluded ?? "—"), node("td", data.literature || "—"), control);
    rows.push(tr);
  }
  if (!rows.length) {
    const empty = node("tr");
    const cell = node("td", "Results appear at the first checkpoint.");
    cell.colSpan = 7;
    empty.append(cell);
    rows.push(empty);
  }
  byId("particle-runs").replaceChildren(...rows);
}

function massMatrix(container, mass) {
  if (!mass?.matrix) return;
  container.append(node("h3", "Mass matrix"),
    node("p", "q = (" + mass.fermion_charges.join(", ") + ") · h = (" + mass.scalar_charges.join(", ") + ")", "math"));
  const table = node("table");
  table.setAttribute("aria-label", "Symmetric Yukawa matrix");
  for (const cells of mass.matrix) {
    const row = node("tr");
    row.append(...cells.map((cell) => node("td", cell)));
    table.append(row);
  }
  const frame = node("div", undefined, "table-wrap mass-matrix");
  frame.append(table);
  container.append(frame, node("p", "det M = " + mass.determinant + " · generic rank " + mass.generic_rank +
    " · witness determinant " + mass.witness_determinant, "math"));
}

async function openParticleRun(run) {
  try {
    const artifact = await json("/api/artifact/" + run.artifact);
    const detail = artifact.detail;
    const container = byId("dialog-content");
    container.replaceChildren();
    text("dialog-title", displayTitle(artifact.title));
    container.append(pill(runLabels[run.status] || [run.status, "neutral"]));
    addSection(container, "Outcome", problemLabels[detail.outcome] || detail.outcome || detail.reason || artifact.status, "math");
    if (detail.models?.length) {
      const list = node("ul");
      for (const model of detail.models.slice(0, 20)) {
        list.append(node("li", "(" + model.charges.join(", ") + ") · Σq = " + model.linear_sum +
          " · Σq³ = " + model.cubic_sum));
      }
      container.append(node("h3", "Charge classes"), list);
    }
    if (detail.proof) {
      const list = node("ol");
      list.append(...detail.proof.map((step) => node("li", step)));
      container.append(node("h3", "Proof"), list);
    }
    if (detail.alternative_proof) {
      const second = node("details");
      const steps = node("ol");
      steps.append(...detail.alternative_proof.map((step) => node("li", step)));
      second.append(node("summary", "Second proof"), steps);
      container.append(second);
    }
    if (detail.lean) addSection(container, "Kernel check", detail.lean.status, "math");
    if (detail.formal_obligation) addSection(container, "Proof obligation", detail.formal_obligation);
    if (detail.counterexample?.mass) massMatrix(container, detail.counterexample.mass);
    for (const result of (detail.mass_searches || []).slice(0, 10)) massMatrix(container, result.certificate);
    for (const claim of artifact.claims || []) {
      const button = node("button", displayTitle(claim.title));
      button.type = "button";
      button.onclick = () => openClaim(claim.id);
      container.append(button);
    }
    if (artifact.novelty) addSection(container, "Literature assessment", artifact.novelty.meaning);
    const number = String(run.id).padStart(6, "0");
    const download = node("a", "Full JSON report");
    download.href = "/api/report/" + number + ".json";
    const files = node("p");
    files.append(download);
    if (artifact.substantive && artifact.proof_complete && detail.dossier) {
      const draft = node("a", "LaTeX draft");
      draft.href = "/api/report/" + number + ".tex";
      files.append(document.createTextNode(" · "), draft);
    }
    container.append(files);
    if (!byId("claim-dialog").open) byId("claim-dialog").showModal();
    byId("claim-dialog").scrollTop = 0;
  } catch (error) {
    notice(error.message);
  }
}

function addSection(container, title, value, css) {
  container.append(node("h3", title), node("p", value, css));
}

function graph(container, claim) {
  if (!claim.dependencies.length && !claim.refuted_by?.length) return;
  container.append(node("h3", "Deduction graph"));
  const graph = node("div", undefined, "graph");
  const parents = node("div", undefined, "graph-parents");
  const records = new Map(state.claims.map((item) => [item.id, item]));
  for (const id of claim.dependencies) {
    const label = node("button", displayTitle(records.get(id)?.title) || id);
    label.type = "button";
    label.onclick = () => openClaim(id);
    parents.append(label);
  }
  if (claim.dependencies.length) graph.append(parents, node("p", "↓", "graph-arrow"));
  graph.append(node("strong", displayTitle(claim.title)));
  for (const id of claim.refuted_by || []) {
    const button = node("button", "Counterexample · " + (displayTitle(records.get(id)?.title) || id));
    button.type = "button";
    button.onclick = () => openClaim(id);
    graph.append(node("p", "↓", "graph-arrow"), button);
  }
  container.append(graph);
}

async function openClaim(id) {
  try {
    const item = await json("/api/claim/" + encodeURIComponent(id));
    const container = byId("dialog-content");
    container.replaceChildren();
    text("dialog-title", displayTitle(item.title));
    const badge = item.quarantine ? ["Under review", "red"] : labels[item.kind] || [item.kind, "neutral"];
    container.append(pill(badge));
    addSection(container, "Statement", item.display.conclusion, "math");
    addSection(container, "Domain", [item.display.quantifiers, item.display.domain].filter(Boolean).join(" · "), "math");
    if (item.display.hypotheses.length) addSection(container, "Assumptions", item.display.hypotheses.join(" · "), "muted");
    if (item.sources.length) {
      const list = node("ul");
      for (const id of item.sources) {
        const source = sourceMap.get(id);
        const row = node("li");
        if (source?.url && new URL(source.url).protocol === "https:") {
          const link = node("a", source.title);
          link.href = source.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          row.append(link);
        } else row.textContent = source?.title || id;
        if (source?.locator) row.append(document.createTextNode(" · " + source.locator));
        list.append(row);
      }
      container.append(node("h3", "Sources"), list);
    }
    graph(container, item);
    massMatrix(container, item.evidence?.mass);
    if (item.evidence?.artifact && /^[a-f0-9]{64}$/.test(item.evidence.artifact)) {
      const artifact = node("a", "Open verification and novelty report");
      artifact.href = "/api/artifact/" + item.evidence.artifact;
      artifact.target = "_blank";
      artifact.rel = "noopener";
      container.append(node("h3", "Verified artifact"), artifact);
    }
    container.append(node("h3", "Method, checks, and evidence"));
    if (item.evidence?.witness) {
      container.append(node("p", "Verified witness", "muted"), node("pre", JSON.stringify(item.evidence.witness, null, 2)));
    }
    container.append(node("pre", JSON.stringify(item.evidence, null, 2)));
    if (!byId("claim-dialog").open) byId("claim-dialog").showModal();
    byId("claim-dialog").scrollTop = 0;
  } catch (error) {
    notice(error.message);
  }
}

async function refresh() {
  try {
    state = await json("/api/status");
    if (byId("lab-filter").options.length === 1) initializeFilters();
    renderStats();
    const signature = JSON.stringify([state.counts, state.claims.map((item) => [item.id, item.quarantine, item.refuted_by]),
      state.runs.map((run) => [run.id, run.status, run.artifact]), state.events[0]?.id]);
    if (signature !== renderSignature) {
      renderLabs();
      renderClaims();
      renderRuns();
      renderParticle();
      renderSignature = signature;
    }
    await renderCoverage();
  } catch (error) {
    byId("runner-dot").className = "indicator offline";
    text("runner-status", "Registry unavailable");
    text("runner-note", error.message);
  }
}

for (const button of document.querySelectorAll("[data-mode]")) {
  button.addEventListener("click", async () => {
    controlsLocked = true;
    buttons();
    try {
      const mode = button.dataset.mode;
      await json("/api/control", {method: "POST", headers: {"Content-Type": "application/json", "X-Research-Token": state.csrf},
        body: JSON.stringify({mode})});
      notice({paused: "Pause requested. The active job will return to the queue.",
        stopped: "Stop requested. The registry and dashboard remain available.",
        running: "Research resumed from the persistent registry."}[mode]);
      await refresh();
    } catch (error) {
      notice(error.message);
    } finally {
      controlsLocked = false;
      buttons();
    }
  });
}
for (const id of ["lab-filter", "kind-filter", "search-filter"]) {
  byId(id).addEventListener("input", () => { if (state) renderClaims(); });
}
byId("close-dialog").onclick = () => byId("claim-dialog").close();
json("/api/sources").then((items) => { sourceMap = new Map(items.map((item) => [item.id, item])); }).catch(() => {});
let refreshTimer;
async function poll() {
  clearTimeout(refreshTimer);
  await refresh();
  refreshTimer = setTimeout(poll, 3000);
}
poll();
