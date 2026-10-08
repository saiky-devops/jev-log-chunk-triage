"""Agent A: dumps all log chunks into the LLM context window."""

from __future__ import annotations

from typing import Any

from agents.common import build_diagnosis_prompt, build_llm, evaluate_diagnosis, invoke_llm_diagnosis
from benchmark.telemetry import TelemetryCollector
from scenarios.loader import Scenario


def run_baseline_agent(scenario: Scenario, telemetry: TelemetryCollector) -> dict[str, Any]:
    all_chunks = [(c.id, c.content) for c in scenario.log_chunks]
    chunk_chars = sum(len(c) for _, c in all_chunks)

    telemetry.set_chunk_stats(
        chunks_total=len(all_chunks),
        chunks_passed=len(all_chunks),
        chunk_chars_total=sum(len(c.content) for c in scenario.log_chunks),
        chunk_chars_passed=chunk_chars,
    )

    llm = build_llm()
    messages = build_diagnosis_prompt(scenario, all_chunks)
    diagnosis = invoke_llm_diagnosis(llm, messages, telemetry, "diagnose_all_chunks")

    passed_ids = [c.id for c in scenario.log_chunks]
    correct, eval_details = evaluate_diagnosis(scenario, diagnosis, passed_ids)
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
