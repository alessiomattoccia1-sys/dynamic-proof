# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Validated service configuration."""
from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class ResearchConfig:
    wall_seconds: int = 30
    cpu_seconds: int = 18
    memory_mb: int = 3072
    min_job_interval: int = 15
    max_jobs_per_day: int = 96
    continue_after_candidate: bool = True
    online_literature: bool = True
    max_retries: int = 2

    def __post_init__(self):
        bounds = {"wall_seconds": (2, 3600), "cpu_seconds": (1, 3600), "memory_mb": (64, 32_768),
                  "min_job_interval": (0, 3600), "max_jobs_per_day": (1, 10_000), "max_retries": (0, 10)}
        for field, (lower, upper) in bounds.items():
            value = getattr(self, field)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(f"{field} fuori dall’intervallo {lower}–{upper}")
        if type(self.online_literature) is not bool or type(self.continue_after_candidate) is not bool:
            raise ValueError("i controlli della ricerca richiedono valori booleani")


def read_config(path: Path) -> tuple[ResearchConfig, int]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    research = ResearchConfig(**data.get("research", {}))
    port = data.get("dashboard", {}).get("port", 8789)
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("porta non valida")
    return research, port
