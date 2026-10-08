"""Shared diagnostic agent utilities."""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from config import settings
from scenarios.loader import Scenario


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key or "not-set",
        temperature=0,
    )


def count_tokens_approx(text: str) -> int:
    return max(1, len(text) // 4)


def format_incident_block(scenario: Scenario) -> str:
    inc = scenario.incident
    parts = [
        f"INCIDENT: {inc.get('title', 'Unknown')}",
        f"Service: {inc.get('service', 'unknown')}",
        f"Description: {inc.get('description', '')}",
    ]
    if inc.get("symptoms"):
        parts.append(f"Symptoms: {inc['symptoms']}")
    if scenario.metrics_summary:
        parts.append(f"\nMETRICS SUMMARY\n{scenario.metrics_summary}")
    if scenario.runbook_excerpt:
        parts.append(f"\nRUNBOOK EXCERPT\n{scenario.runbook_excerpt}")
    return "\n".join(parts)


def evaluate_diagnosis(
    scenario: Scenario,
    diagnosis: str,
    passed_chunk_ids: list[str],
) -> tuple[bool, dict[str, Any]]:
    text = diagnosis.lower()
    details: dict[str, Any] = {}

    contains_ok = True
    if scenario.expected.diagnosis_contains:
        contains_ok = any(str(k).lower() in text for k in scenario.expected.diagnosis_contains)
    details["contains_ok"] = contains_ok

    signal_recall = 1.0
    required = scenario.expected.required_signal_chunks
    if required:
        passed_set = set(passed_chunk_ids)
        hit = sum(1 for cid in required if cid in passed_set)
        signal_recall = hit / len(required)
    details["signal_recall"] = signal_recall

    signal_ok = signal_recall >= 1.0
    details["signal_ok"] = signal_ok

    correct = contains_ok and signal_ok
    return correct, details
