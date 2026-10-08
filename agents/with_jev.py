"""Agent B: Jev scores log chunks; only high-signal excerpts reach the LLM."""

from __future__ import annotations

from typing import Any

from agents.common import build_diagnosis_prompt, build_llm, evaluate_diagnosis, invoke_llm_diagnosis
from benchmark.telemetry import TelemetryCollector
from jev.chunk_scorer import ChunkRelevanceScorer
from scenarios.loader import Scenario


def run_jev_agent(scenario: Scenario, telemetry: TelemetryCollector) -> dict[str, Any]:
    scorer = ChunkRelevanceScorer(
        log_fn=lambda name, latency, meta: telemetry.log_jev(name, latency, **meta)
    )

    chunk_tuples = [(c.id, c.content, c.is_signal) for c in scenario.log_chunks]
    passed, scores = scorer.filter_chunks(chunk_tuples, scenario.incident)

    total_chars = sum(len(c.content) for c in scenario.log_chunks)
    passed_chars = sum(len(content) for _, content in passed)

    telemetry.set_chunk_stats(
        chunks_total=len(scenario.log_chunks),
        chunks_passed=len(passed),
        chunk_chars_total=total_chars,
        chunk_chars_passed=passed_chars,
    )

    llm = build_llm()
    messages = build_diagnosis_prompt(scenario, passed)
    diagnosis = invoke_llm_diagnosis(llm, messages, telemetry, "diagnose_filtered_chunks")

    passed_ids = [cid for cid, _ in passed]
    correct, eval_details = evaluate_diagnosis(scenario, diagnosis, passed_ids)
    eval_details["score_details"] = [
        {"chunk_id": s.chunk_id, "relevance": s.relevance, "passed": s.passed} for s in scores
    ]
    metrics = telemetry.finish(
        diagnosis=diagnosis,
        correct=correct,
        signal_recall=eval_details.get("signal_recall", 1.0),
    )

    return {
        "metrics": metrics,
        "diagnosis": diagnosis,
        "passed_chunks": passed_ids,
        "eval_details": eval_details,
    }
