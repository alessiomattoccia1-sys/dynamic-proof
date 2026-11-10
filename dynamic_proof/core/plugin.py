# SPDX-License-Identifier: Apache-2.0
"""The application registers independent laboratories using this interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .literature import Source
from .model import Claim


@dataclass(frozen=True)
class Work:
    strategy: str
    payload: dict
    priority: int = 40
    delay: float = 0.0
    # Strategy depth bounds retries and alternative investigations independently.
    generation: int = 0

    def data(self) -> dict:
        return {"strategy": self.strategy, "payload": self.payload, "priority": self.priority,
                "delay": self.delay, "generation": self.generation}


@dataclass(frozen=True)
class Result:
    status: str
    title: str
    detail: dict
    claims: tuple[Claim, ...] = ()
    followups: tuple[Work, ...] = ()
    known: tuple[str, ...] = ()
    comparisons: tuple[dict, ...] = ()
    substantive: bool = False
    proof_complete: bool = False
    independent: bool = False
    public_query: str | None = None

    def data(self) -> dict:
        return {"status": self.status, "title": self.title, "detail": self.detail,
                "claims": [claim.data() for claim in self.claims], "followups": [job.data() for job in self.followups],
                "known": list(self.known), "comparisons": list(self.comparisons),
                "substantive": self.substantive, "proof_complete": self.proof_complete,
                "independent": self.independent, "public_query": self.public_query}


@dataclass(frozen=True)
class Context:
    root: Path
    online_literature: bool
    emit: Callable[[str, str], None]

    def stage(self, name: str, detail: str) -> None:
        self.emit(name, detail)


@dataclass(frozen=True)
class Lab:
    id: str
    title: str
    summary: str
    sources: tuple[Source, ...]
    claims: tuple[Claim, ...]
    strategies: dict[str, Callable[[Context, dict], Result]]
    seeds: tuple[Work, ...]
    coverage_target: str | None = None
    coverage_options: tuple[str, ...] = field(default_factory=tuple)
