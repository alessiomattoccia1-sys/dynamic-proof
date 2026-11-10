# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Provenance records, literature acquisition and conservative novelty assessment."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import ssl
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .model import Kind


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    locator: str
    version: str
    url: str | None = None
    snapshot: str | None = None
    terms: tuple[str, ...] = ()

    def data(self, root: Path) -> dict:
        artifact = root / self.snapshot if self.snapshot else None
        checksum = None
        if artifact is not None and artifact.is_file():
            with artifact.open("rb") as stream:
                checksum = sha256(stream.read()).hexdigest()
        return {"id": self.id, "title": self.title, "locator": self.locator,
                "version": self.version, "url": self.url, "snapshot": self.snapshot,
                "sha256": checksum, "terms": list(self.terms)}


def _fetch(url: str) -> bytes:
    # Only public provider endpoints. Queries come from the reviewed module
    # configuration, never from private source text or discovered hypotheses.
    request = Request(url, headers={"User-Agent": "DynamicProofResearch/0.1 (public literature indexing)"})
    with urlopen(request, timeout=4, context=ssl.create_default_context()) as response:
        payload = response.read(1_000_001)
    if len(payload) > 1_000_000:
        raise ValueError("risposta bibliografica troppo grande")
    return payload


def external_search(query: str) -> list[dict]:
    query = " ".join(query.split())
    if not query or len(query) > 180:
        raise ValueError("query bibliografica non valida")
    phrases = [part.strip().replace('"', "") for part in query.split("|") if part.strip()]
    if not phrases:
        raise ValueError("query bibliografica vuota")
    arxiv_terms = [f'all:"{phrase}"' for phrase in phrases]
    arxiv_query = arxiv_terms[0]
    if len(arxiv_terms) > 1:
        arxiv_query += " AND (" + " OR ".join(arxiv_terms[1:]) + ")"
    adapters = {
        "Crossref": ("https://api.crossref.org/works?" +
                     urlencode({"query.bibliographic": " ".join(phrases), "rows": 5}),
                     _crossref),
        "arXiv": ("https://export.arxiv.org/api/query?" +
                  urlencode({"search_query": arxiv_query, "max_results": 5}), _arxiv),
        "INSPIRE-HEP": ("https://inspirehep.net/api/literature?" +
                        urlencode({"q": " OR ".join(f'"{phrase}"' for phrase in phrases), "size": 5,
                                   "fields": "titles,dois,arxiv_eprints,control_number"}), _inspire),
    }
    records = []
    for name, (url, parser) in adapters.items():
        try:
            hits = parser(_fetch(url))
            records.append({"source": name, "query": query, "url": url, "ok": True, "hits": hits})
        except (OSError, ValueError, ET.ParseError, KeyError) as error:
            records.append({"source": name, "query": query, "url": url, "ok": False,
                            "error": str(error), "hits": []})
    return records


def _crossref(payload: bytes) -> list[dict]:
    items = json.loads(payload)["message"]["items"]
    return [{"title": " ".join(item.get("title", [])).strip(), "doi": item.get("DOI"),
             "url": item.get("URL"), "type": item.get("type"), "abstract": item.get("abstract")}
            for item in items]


def _arxiv(payload: bytes) -> list[dict]:
    feed = ET.fromstring(payload)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    return [{"title": " ".join(entry.findtext("a:title", "", ns).split()),
             "url": entry.findtext("a:id", "", ns), "abstract": entry.findtext("a:summary", "", ns)}
            for entry in feed.findall("a:entry", ns)]


def _inspire(payload: bytes) -> list[dict]:
    result = []
    for hit in json.loads(payload)["hits"]["hits"]:
        record = hit["metadata"]
        identifier = record.get("control_number", hit.get("id"))
        title = next((item["title"] for item in record.get("titles", []) if item.get("title")), "")
        doi = next((item["value"] for item in record.get("dois", []) if item.get("value")), None)
        arxiv = next((item["value"] for item in record.get("arxiv_eprints", []) if item.get("value")), None)
        if str(identifier).isdigit() and title:
            result.append({"title": title, "doi": doi, "arxiv": arxiv,
                           "url": f"https://inspirehep.net/literature/{identifier}"})
    return result


def local_search(query: str, sources: list[dict]) -> list[dict]:
    terms = set(re.findall(r"\w+", query.casefold()))
    ranked = []
    for source in sources:
        text = " ".join((source["title"], source["locator"], *source.get("terms", []))).casefold()
        overlap = terms & set(re.findall(r"\w+", text))
        if overlap:
            ranked.append((len(overlap), source["id"], {"source": source["id"], "title": source["title"],
                          "locator": source["locator"], "overlap": sorted(overlap), "url": source["url"]}))
    return [row[2] for row in sorted(ranked, key=lambda row: (-row[0], row[1]))[:12]]


def assess(*, evidence_kind: Kind, known: tuple[str, ...], similar: bool, substantive: bool,
           proof_complete: bool, independent: bool, replayed: bool, searches: list[dict],
           comparisons: list[dict], first_seen: bool = True) -> dict:
    """Metadata search alone can never satisfy the scientific novelty gate."""
    cited_comparisons = [item for item in comparisons if item.get("work") and item.get("locator")
                         and item.get("direct_prior_art")
                         and item.get("difference") and item.get("reviewed_scope")
                         and item.get("relation") in {"different", "weaker"}]
    unresolved = [item for item in comparisons if item.get("relation") in {"unknown", "equivalent", "stronger"}]
    coverage = {row["source"] for row in searches
                if row.get("ok") and row.get("hits") and row.get("source") != "catalogo locale"}
    gates = {"precise_technical_proof": proof_complete, "independent_verification": independent,
             "reproducible": replayed, "substantive": substantive,
             "two_bibliographic_channels": len(coverage) >= 2,
             "scope_comparison": len({row["work"] for row in cited_comparisons}) >= 2 and not unresolved,
             "adequate_evidence": evidence_kind in {Kind.FORMAL, Kind.EXACT, Kind.COUNTEREXAMPLE},
             "no_known_equivalent": not known and not similar}
    if known or similar:
        level = "known"
    elif all(gates.values()):
        level = "C"
    elif gates["no_known_equivalent"] and gates["two_bibliographic_channels"] and gates["scope_comparison"]:
        level = "B"
    else:
        level = "A" if first_seen else "seen"
    return {"level": level, "gates": gates, "known": list(known), "searches": searches,
            "comparisons": comparisons,
            "meaning": {"known": "risultato noto o riproduzione", "A": "nuovo per la sessione",
                        "seen": "già osservato nella sessione", "B": "potenzialmente nuovo nelle fonti confrontate",
                        "C": "candidato originale verificato, in attesa di revisione scientifica"}[level]}
