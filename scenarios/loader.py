"""Load log-diagnosis scenario fixtures from YAML files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from config import SCENARIOS_DIR


@dataclass
class LogChunk:
    id: str
    content: str
    is_signal: bool = False
    source: str = "logs"


@dataclass
class ExpectedDiagnosis:
    diagnosis_contains: list[str] = field(default_factory=list)
    required_signal_chunks: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    name: str
    incident: dict[str, Any]
    log_chunks: list[LogChunk]
    metrics_summary: str = ""
    runbook_excerpt: str = ""
    expected: ExpectedDiagnosis = field(default_factory=ExpectedDiagnosis)
    tags: list[str] = field(default_factory=list)


def load_scenario(path: Path) -> Scenario:
    data = yaml.safe_load(path.read_text())
    exp = data.get("expected", {})
    chunks = [
        LogChunk(
            id=c["id"],
            content=c["content"].strip(),
            is_signal=bool(c.get("is_signal", False)),
            source=c.get("source", "logs"),
        )
        for c in data.get("log_chunks", [])
    ]
    return Scenario(
        id=data["id"],
        name=data["name"],
        incident=data["incident"],
        log_chunks=chunks,
        metrics_summary=(data.get("metrics_summary") or "").strip(),
        runbook_excerpt=(data.get("runbook_excerpt") or "").strip(),
        expected=ExpectedDiagnosis(
            diagnosis_contains=exp.get("diagnosis_contains", []),
            required_signal_chunks=exp.get("required_signal_chunks", []),
        ),
        tags=data.get("tags", []),
    )


def load_all_scenarios(directory: Path | None = None) -> list[Scenario]:
    directory = directory or SCENARIOS_DIR
    return [load_scenario(path) for path in sorted(directory.glob("*.yaml"))]
