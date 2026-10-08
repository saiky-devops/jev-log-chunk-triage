"""Shared diagnostic agent utilities."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings
from scenarios.loader import LogChunk, Scenario

SYSTEM_PROMPT = """You are an observability diagnostic agent. Given an incident summary and
log/trace excerpts, produce a concise root-cause diagnosis.

Respond with a paragraph starting with "DIAGNOSIS:" that states:
- likely root cause
- supporting evidence from the logs
- recommended next action (rollback, escalate, adjust limits, or no action)

Use only evidence present in the provided context."""


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


def format_chunks_block(chunks: list[tuple[str, str]]) -> str:
    if not chunks:
        return "LOG EXCERPTS\n(none passed relevance filter)"
    sections = []
    for chunk_id, content in chunks:
        sections.append(f"--- {chunk_id} ---\n{content}")
    return "LOG EXCERPTS\n" + "\n\n".join(sections)


def build_diagnosis_prompt(scenario: Scenario, chunks: list[tuple[str, str]]) -> list:
    body = f"{format_incident_block(scenario)}\n\n{format_chunks_block(chunks)}"
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=body),
    ]


def invoke_llm_diagnosis(
    llm: ChatOpenAI,
    messages: list,
    telemetry: Any,
    call_name: str = "diagnose",
) -> str:
    start = time.perf_counter()
    input_text = " ".join(
        m.content if isinstance(getattr(m, "content", None), str) else str(getattr(m, "content", ""))
        for m in messages
    )
    response = llm.invoke(messages)
    latency = (time.perf_counter() - start) * 1000
    output_text = response.content if isinstance(response.content, str) else str(response.content or "")
    usage = getattr(response, "usage_metadata", None)
    if usage:
        in_tok = usage.get("input_tokens", count_tokens_approx(input_text))
        out_tok = usage.get("output_tokens", count_tokens_approx(output_text))
    else:
        in_tok = count_tokens_approx(input_text)
        out_tok = count_tokens_approx(output_text)
    telemetry.log_llm(call_name, in_tok, out_tok, latency, context_chars=len(input_text))
    return output_text


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
