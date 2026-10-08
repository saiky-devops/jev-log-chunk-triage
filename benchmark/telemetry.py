"""Structured logging for LLM, Jev, and chunk filtering."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CallRecord:
    call_id: str
    call_type: str  # llm | jev
    name: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class RunMetrics:
    scenario_id: str
    agent_type: str
    run_index: int
    llm_calls: int = 0
    jev_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    chunks_total: int = 0
    chunks_passed: int = 0
    chunk_chars_total: int = 0
    chunk_chars_passed: int = 0
    signal_recall: float = 1.0
    latency_ms: float = 0.0
    diagnosis: str = ""
    correct: bool = False
    calls: list[CallRecord] = field(default_factory=list)

    def add_call(self, record: CallRecord) -> None:
        self.calls.append(record)
        if record.call_type == "llm":
            self.llm_calls += 1
            self.input_tokens += record.input_tokens
            self.output_tokens += record.output_tokens
        elif record.call_type == "jev":
            self.jev_calls += 1

    @property
    def context_compression_pct(self) -> float:
        if self.chunk_chars_total == 0:
            return 0.0
        return (1 - self.chunk_chars_passed / self.chunk_chars_total) * 100

    def estimated_cost_usd(self, input_price: float = 2.50, output_price: float = 10.0) -> float:
        """Estimate cost per 1M tokens (gpt-4o list defaults)."""
        return (self.input_tokens * input_price + self.output_tokens * output_price) / 1_000_000


class TelemetryCollector:
    def __init__(self, scenario_id: str, agent_type: str, run_index: int):
        self.metrics = RunMetrics(
            scenario_id=scenario_id, agent_type=agent_type, run_index=run_index
        )
        self._start = time.perf_counter()
        self._signal_recall = 1.0

    def set_chunk_stats(
        self,
        chunks_total: int,
        chunks_passed: int,
        chunk_chars_total: int,
        chunk_chars_passed: int,
    ) -> None:
        self.metrics.chunks_total = chunks_total
        self.metrics.chunks_passed = chunks_passed
        self.metrics.chunk_chars_total = chunk_chars_total
        self.metrics.chunk_chars_passed = chunk_chars_passed

    def log_llm(
        self,
        name: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        **metadata: Any,
    ) -> None:
        self.metrics.add_call(
            CallRecord(
                call_id=str(uuid.uuid4())[:8],
                call_type="llm",
                name=name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                metadata=metadata,
            )
        )

    def log_jev(self, name: str, latency_ms: float, **metadata: Any) -> None:
        self.metrics.add_call(
            CallRecord(
                call_id=str(uuid.uuid4())[:8],
                call_type="jev",
                name=name,
                latency_ms=latency_ms,
                metadata=metadata,
            )
        )

    def finish(
        self,
        diagnosis: str,
        correct: bool,
        signal_recall: float = 1.0,
    ) -> RunMetrics:
        self.metrics.latency_ms = (time.perf_counter() - self._start) * 1000
        self.metrics.diagnosis = diagnosis
        self.metrics.correct = correct
        self.metrics.signal_recall = signal_recall
        return self.metrics

    def save_raw(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{self.metrics.agent_type}_{self.metrics.scenario_id}_run{self.metrics.run_index}.json"
        path.write_text(json.dumps(asdict(self.metrics), indent=2))
        return path
