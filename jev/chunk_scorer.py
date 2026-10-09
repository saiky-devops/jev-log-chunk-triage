"""Jev log-chunk relevance scorer — filter context before LLM diagnosis."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import config

try:
    from langchain_typesafe import Noul, TypeSafeClassifier
except ImportError:  # pragma: no cover
    TypeSafeClassifier = None  # type: ignore
    Noul = None  # type: ignore


@dataclass
class ChunkScore:
    chunk_id: str
    relevance: float
    passed: bool
    source: str  # jev | mock | shadow


LogFn = Callable[[str, float, dict[str, Any]], None]


class ChunkRelevanceScorer:
    """Score log/trace chunks for anomaly relevance to the active incident."""

    def __init__(self, log_fn: LogFn | None = None):
        self.log_fn = log_fn
        settings = config.settings
        self.mode = settings.jev_mode
        self.threshold = settings.relevance_threshold
        self._classifier = None
        if self.mode != "mock" and TypeSafeClassifier and settings.typesafe_api_key:
            self._classifier = TypeSafeClassifier()

    def _log(self, name: str, latency_ms: float, **metadata: Any) -> None:
        if self.log_fn:
            self.log_fn(name, latency_ms, metadata)

    def _format_incident(self, incident: dict[str, Any]) -> str:
        parts = [
            f"Title: {incident.get('title', 'unknown')}",
            f"Service: {incident.get('service', 'unknown')}",
            f"Description: {incident.get('description', '')}",
        ]
        if incident.get("symptoms"):
            parts.append(f"Symptoms: {incident['symptoms']}")
        return "\n".join(parts)

    def _mock_score(self, chunk_content: str, *, signal_hint: bool = False) -> float:
        """Keyword heuristics. signal_hint only in mock mode (never live/shadow fallback)."""
        if signal_hint:
            return 0.92
        text = chunk_content.lower()
        signal_markers = (
            "out of memory",
            "oomkilled",
            "exit code 137",
            "heap usage",
            "connection refused",
            "database unreachable",
            "crashloop",
            "invalid database_url",
            "ignore previous instructions",
            "nullpointerexception",
            "postgres.query",
            "dominant",
            "no space left on device",
            "diskpressure",
            "certificate has expired",
            "x509:",
            "429 too many requests",
            "deadline exceeded",
            "upstream timeout",
        )
        if any(m in text for m in signal_markers):
            return 0.90
        noise_markers = (
            "health check ok",
            "get /health 200",
            "get /ready 200",
            "heartbeat completed",
            "profiling sample",
            "gc pause",
            "cache hit ratio",
            "no config changes",
            "downstream_rq_200",
        )
        if any(m in text for m in noise_markers):
            return 0.08
        return 0.25

    def score_chunk(
        self,
        chunk_id: str,
        chunk_content: str,
        incident: dict[str, Any],
        is_signal: bool = False,
    ) -> ChunkScore:
        start = time.perf_counter()
        incident_ctx = self._format_incident(incident)
        state = (
            f"INCIDENT CONTEXT\n{incident_ctx}\n\n"
            f"LOG CHUNK ({chunk_id})\n{chunk_content[:4000]}"
        )

        allow_signal_hint = self.mode == "mock"

        if self._classifier and Noul:
            try:
                response = self._classifier.invoke(
                    {
                        "state": state,
                        "questions": {
                            "relevant": Noul(
                                instructions=(
                                    "This log or trace chunk contains anomaly signal "
                                    "that helps diagnose the incident described above"
                                )
                            )
                        },
                    }
                )
                if response and hasattr(response, "nouls"):
                    relevance = response.nouls["relevant"].noul
                    source = "jev"
                else:
                    relevance = self._mock_score(chunk_content, signal_hint=False)
                    source = "jev_error"
            except Exception as exc:
                self._log("jev_error", (time.perf_counter() - start) * 1000, error=str(exc))
                relevance = self._mock_score(chunk_content, signal_hint=False)
                source = "jev_error"
        else:
            relevance = self._mock_score(
                chunk_content,
                signal_hint=allow_signal_hint and is_signal,
            )
            source = "mock"

        passed = relevance >= self.threshold
        if self.mode == "shadow":
            passed = True
            source = "shadow" if source == "jev" else source

        latency = (time.perf_counter() - start) * 1000
        self._log(
            "chunk_score",
            latency,
            chunk_id=chunk_id,
            relevance=round(relevance, 3),
            passed=passed,
            source=source,
        )
        return ChunkScore(chunk_id, relevance, passed, source)

    def filter_chunks(
        self,
        chunks: list[tuple[str, str, bool]],
        incident: dict[str, Any],
    ) -> tuple[list[tuple[str, str]], list[ChunkScore]]:
        """Return (passed_chunks, all_scores). Each chunk is (id, content, is_signal)."""
        passed: list[tuple[str, str]] = []
        scores: list[ChunkScore] = []
        for chunk_id, content, is_signal in chunks:
            score = self.score_chunk(chunk_id, content, incident, is_signal)
            scores.append(score)
            if score.passed:
                passed.append((chunk_id, content))
        return passed, scores
