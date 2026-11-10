// Copyright 2026 Alessio Mattoccia
// SPDX-License-Identifier: Apache-2.0
"use strict";

const labels = {
  formal: ["Dimostrato in Lean", "green"], exact: ["Verifica esatta", "green"],
  literature: ["Risultato in letteratura", "blue"], conditional: ["Conseguenza condizionale", "amber"],
  certified_numeric: ["Certificato numerico", "green"], exploratory: ["Esplorativo", "neutral"],
  conjecture: ["Problema aperto o ipotesi", "amber"], counterexample: ["Controesempio verificato", "red"],
  original_candidate: ["Candidato originale · C", "green"]
};
const runLabels = {
  running: ["In corso", "green"], reproduced: ["Riprodotto", "green"], partial: ["Parziale", "blue"],
  refuted: ["Confutato", "red"], inconclusive: ["Inconcludente", "amber"],
  interrupted: ["Interrotto", "neutral"], failed: ["Errore", "red"], verified: ["Verificato", "green"]
};
const problemLabels = {
  SAT: "Soluzioni trovate", UNSAT: "Nessuna soluzione nel dominio", UNKNOWN: "Ricerca incompleta",
  checkpoint: "Checkpoint", budget_exhausted: "Budget esaurito", proved: "Dimostrato in Lean",
  proof_obligation: "Verifica Lean aperta", analytic_derivation: "Derivazione analitica",
  counterexample: "Controesempio verificato", counterexample_absent: "Nessun controesempio nel dominio"
};

const byId = (id) => document.getElementById(id);
const text = (id, value) => { byId(id).textContent = value; };
const node = (tag, value, css) => {
  const element = document.createElement(tag);
  if (value !== undefined) element.textContent = value;
  if (css) element.className = css;
  return element;
};
const pill = ([label, color]) => node("span", label, "pill " + color);
const shortStrategy = (name) => name === "@literature" ? "letteratura" : name.replaceAll("_", " ");
const formatTime = (seconds) => new Date(seconds * 1000).toLocaleTimeString("it-IT", {hour: "2-digit", minute: "2-digit"});
let state;
let sourceMap = new Map();
let controlsLocked = false;
let coverageRequest = 0;
let coverageVersion = "";
let renderSignature = "";

async function json(url, options) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Risposta non valida");
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
  text("runner-status", online ? {running: "Core operativo", paused: "Ricerca in pausa", stopped: "Ricerca arrestata"}[mode] : "Orchestratore offline");
  text("runner-note", online ? (mode === "running" ? "Checkpoint attivi" : "Registro consultabile") : "Connessione al registro locale");
  text("count-labs", state.labs.length);
  text("count-runs", state.totals?.attempts ?? state.runs.filter((run) => run.ended).length);
  const evidence = state.totals?.evidence;
  text("count-verified", evidence ?
    ["formal", "exact", "certified_numeric", "counterexample"].reduce((total, key) => total + (evidence[key] || 0), 0) :
    state.claims.filter((claim) => ["formal", "exact", "certified_numeric", "counterexample"].includes(claim.kind)).length);
  text("count-original", evidence?.original_candidate ?? state.claims.filter((claim) => claim.kind === "original_candidate").length);
  const active = state.active[0];
  const labName = state.labs.find((lab) => lab.id === active?.lab)?.title;
  text("active-label", active ? "Ciclo attivo" : "In attesa");
  text("active-run", active ? (labName || active.lab) + " · " + (active.problem || shortStrategy(active.strategy)) :
    "Nessun esperimento in esecuzione");
  text("active-detail", active ? "Fase " + active.stage + " · avviato alle " + formatTime(active.started) : "Le code e i tentativi precedenti restano nel registro.");
  const {wall_seconds: wall, cpu_seconds: cpu, memory_mb: mem, max_jobs_per_day: daily} = state.limits;
  text("limits", "Limiti per esperimento · " + wall + " s durata · " + cpu + " s CPU · " + mem + " MiB RAM");
  const rss = (Number(settings.worker_rss_kib || 0) / 1024).toFixed(1);
  text("consumption", active ? "Uso osservato · " + rss + " MiB · CPU " + (settings.worker_cpu_seconds || 0) + " s" :
    "Budget " + daily + " tentativi nelle 24 ore · Lean, SymPy, Arb e SMT");
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
    footer.append(pill([String(counts.queued || 0) + " in coda", "neutral"]),
      pill([String(counts.done || 0) + " completati", "blue"]));
    if (counts.running) footer.append(pill(["Attivo", "green"]));
    if (counts.failed) footer.append(pill([counts.failed + " errori", "red"]));
    const button = node("button", "Vedi il registro");
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
      label.append(checkbox, document.createTextNode(claims.get(id)?.title || id));
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
      "Composizione per minimo comune multiplo · " + step.lcm_text :
      (claims.get(step.claim)?.title || step.claim) + " · resta " + step.remaining_condition)));
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
    (item.title + " " + item.display.conclusion + " " + item.sources.join(" ")).toLowerCase().includes(query));
  text("result-count", items.length + " voci");
  const container = byId("claim-list");
  container.replaceChildren();
  if (!items.length) container.append(node("p", "Nessun risultato per questi filtri.", "panel muted"));
  for (const item of items) {
    const button = node("button", undefined, "claim-row");
    button.type = "button";
    const first = node("span");
    first.append(node("span", item.title, "row-title"),
      node("span", state.labs.find((lab) => lab.id === item.lab)?.title || item.lab, "row-lab"));
    let badge = labels[item.kind] || [item.kind, "neutral"];
    if (item.quarantine) badge = ["In revisione", "red"];
    if (item.refuted_by?.length) badge = ["Confutato", "red"];
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
      node("td", run.summary?.problem || run.problem || shortStrategy(run.strategy)),
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
  text("particle-active", active ? (active.problem || "Ricerca attiva") + " · " + active.stage : "Registro consultabile");
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
    const view = node("button", "Apri " + problem);
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
    const cell = node("td", "Gli esiti compaiono al primo checkpoint.");
    cell.colSpan = 7;
    empty.append(cell);
    rows.push(empty);
  }
  byId("particle-runs").replaceChildren(...rows);
}

function massMatrix(container, mass) {
  if (!mass?.matrix) return;
  container.append(node("h3", "Matrice delle masse"),
    node("p", "q = (" + mass.fermion_charges.join(", ") + ") · h = (" + mass.scalar_charges.join(", ") + ")", "math"));
  const table = node("table");
  table.setAttribute("aria-label", "Matrice simmetrica di Yukawa");
  for (const cells of mass.matrix) {
    const row = node("tr");
    row.append(...cells.map((cell) => node("td", cell)));
    table.append(row);
  }
  const frame = node("div", undefined, "table-wrap mass-matrix");
  frame.append(table);
  container.append(frame, node("p", "det M = " + mass.determinant + " · rango generico " + mass.generic_rank +
    " · determinante del testimone " + mass.witness_determinant, "math"));
}

async function openParticleRun(run) {
  try {
    const artifact = await json("/api/artifact/" + run.artifact);
    const detail = artifact.detail;
    const container = byId("dialog-content");
    container.replaceChildren();
    text("dialog-title", artifact.title);
    container.append(pill(runLabels[run.status] || [run.status, "neutral"]));
    addSection(container, "Esito", problemLabels[detail.outcome] || detail.outcome || detail.reason || artifact.status, "math");
    if (detail.models?.length) {
      const list = node("ul");
      for (const model of detail.models.slice(0, 20)) {
        list.append(node("li", "(" + model.charges.join(", ") + ") · Σq = " + model.linear_sum +
          " · Σq³ = " + model.cubic_sum));
      }
      container.append(node("h3", "Classi di carica"), list);
    }
    if (detail.proof) {
      const list = node("ol");
      list.append(...detail.proof.map((step) => node("li", step)));
      container.append(node("h3", "Dimostrazione"), list);
    }
    if (detail.alternative_proof) {
      const second = node("details");
      const steps = node("ol");
      steps.append(...detail.alternative_proof.map((step) => node("li", step)));
      second.append(node("summary", "Seconda dimostrazione"), steps);
      container.append(second);
    }
    if (detail.lean) addSection(container, "Controllo del kernel", detail.lean.status, "math");
    if (detail.formal_obligation) addSection(container, "Obbligo di prova", detail.formal_obligation);
    if (detail.counterexample?.mass) massMatrix(container, detail.counterexample.mass);
    for (const result of (detail.mass_searches || []).slice(0, 10)) massMatrix(container, result.certificate);
    for (const claim of artifact.claims || []) {
      const button = node("button", claim.title);
      button.type = "button";
      button.onclick = () => openClaim(claim.id);
      container.append(button);
    }
    if (artifact.novelty) addSection(container, "Valutazione bibliografica", artifact.novelty.meaning);
    const number = String(run.id).padStart(6, "0");
    const download = node("a", "Rapporto JSON completo");
    download.href = "/api/report/" + number + ".json";
    const files = node("p");
    files.append(download);
    if (artifact.substantive && artifact.proof_complete && detail.dossier) {
      const draft = node("a", "Bozza LaTeX");
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
  container.append(node("h3", "Grafo delle deduzioni"));
  const graph = node("div", undefined, "graph");
  const parents = node("div", undefined, "graph-parents");
  const records = new Map(state.claims.map((item) => [item.id, item]));
  for (const id of claim.dependencies) {
    const label = node("button", records.get(id)?.title || id);
    label.type = "button";
    label.onclick = () => openClaim(id);
    parents.append(label);
  }
  if (claim.dependencies.length) graph.append(parents, node("p", "↓", "graph-arrow"));
  graph.append(node("strong", claim.title));
  for (const id of claim.refuted_by || []) {
    const button = node("button", "Controesempio · " + (records.get(id)?.title || id));
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
    text("dialog-title", item.title);
    const badge = item.quarantine ? ["In revisione", "red"] : labels[item.kind] || [item.kind, "neutral"];
    container.append(pill(badge));
    addSection(container, "Enunciato", item.display.conclusion, "math");
    addSection(container, "Dominio", [item.display.quantifiers, item.display.domain].filter(Boolean).join(" · "), "math");
    if (item.display.hypotheses.length) addSection(container, "Ipotesi", item.display.hypotheses.join(" · "), "muted");
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
      container.append(node("h3", "Fonti"), list);
    }
    graph(container, item);
    massMatrix(container, item.evidence?.mass);
    if (item.evidence?.artifact && /^[a-f0-9]{64}$/.test(item.evidence.artifact)) {
      const artifact = node("a", "Apri il rapporto di verifica e novità");
      artifact.href = "/api/artifact/" + item.evidence.artifact;
      artifact.target = "_blank";
      artifact.rel = "noopener";
      container.append(node("h3", "Artefatto verificato"), artifact);
    }
    container.append(node("h3", "Procedimento, verifiche ed evidenza"));
    if (item.evidence?.witness) {
      container.append(node("p", "Testimone verificato", "muted"), node("pre", JSON.stringify(item.evidence.witness, null, 2)));
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
    text("runner-status", "Registro non raggiungibile");
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
      notice({paused: "Pausa richiesta. Il lavoro attivo viene interrotto e rimesso in coda.",
        stopped: "Arresto richiesto. Il registro e la dashboard restano consultabili.",
        running: "Ricerca ripresa dal registro persistente."}[mode]);
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
