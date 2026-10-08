"""Agentic diagnostic loop: tool calls to fetch logs, optional Jev filter per fetch."""

from __future__ import annotations

import json
import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from agents.common import build_llm, count_tokens_approx, evaluate_diagnosis, format_incident_block
from benchmark.telemetry import TelemetryCollector
from config import settings
from jev.chunk_scorer import ChunkRelevanceScorer, ChunkScore
from scenarios.loader import Scenario
from tools.log_store import MockLogStore

AGENTIC_SYSTEM_PROMPT = """You are an observability diagnostic agent investigating an active incident.

You do NOT have log excerpts yet — only the incident summary below. Use tools to gather evidence:
- fetch_logs: pull log chunks (try severity=ERROR or narrow time windows if initial fetches are noise)
- fetch_metrics: pull metrics summary
- submit_diagnosis: call when ready with your final answer

Your diagnosis must start with "DIAGNOSIS:" and include:
- likely root cause
- supporting evidence from fetched logs
- recommended next action

If fetched logs are insufficient, call fetch_logs again with different filters before submitting."""


def _log_llm_turn(
    telemetry: TelemetryCollector,
    messages: list,
    response: AIMessage,
    call_name: str,
) -> None:
    input_text = " ".join(
        m.content if isinstance(getattr(m, "content", None), str) else str(getattr(m, "content", ""))
        for m in messages
    )
    output_text = response.content if isinstance(response.content, str) else str(response.content or "")
    if response.tool_calls:
        output_text += " " + json.dumps(response.tool_calls)
    usage = getattr(response, "usage_metadata", None)
    if usage:
        in_tok = usage.get("input_tokens", count_tokens_approx(input_text))
        out_tok = usage.get("output_tokens", count_tokens_approx(output_text))
    else:
        in_tok = count_tokens_approx(input_text)
        out_tok = count_tokens_approx(output_text)
    telemetry.log_llm(call_name, in_tok, out_tok, 0, turn_tool_calls=len(response.tool_calls))


def _apply_jev_filter(
    scorer: ChunkRelevanceScorer,
    chunks: list[tuple[str, str, bool]],
    incident: dict[str, Any],
    use_jev: bool,
) -> tuple[list[tuple[str, str]], list[ChunkScore]]:
    """Return (passed_for_llm, scores). Fallback top-2 if live filter drops all."""
    if not use_jev:
        return [(cid, content) for cid, content, _ in chunks], []

    passed, scores = scorer.filter_chunks(chunks, incident)

    if not passed and scores and settings.jev_mode == "live":
        top = sorted(scores, key=lambda s: s.relevance, reverse=True)[:2]
        if top and top[0].relevance >= 0.25:
            id_to_content = {cid: content for cid, content, _ in chunks}
            passed = [(s.chunk_id, id_to_content[s.chunk_id]) for s in top if s.chunk_id in id_to_content]

    return passed, scores


def _format_fetch_result(
    passed: list[tuple[str, str]],
    raw_count: int,
    remaining: int,
    use_jev: bool,
) -> str:
    if not passed:
        return (
            f"No relevant log excerpts returned ({raw_count} raw chunk(s) fetched, "
            f"{remaining} chunk(s) remain in store). "
            "Try fetch_logs with severity=ERROR or a different time window."
        )
    sections = [f"--- {cid} ---\n{content}" for cid, content in passed]
    filter_note = " (Jev relevance filter applied)" if use_jev and settings.jev_mode == "live" else ""
    return (
        f"Returned {len(passed)}/{raw_count} excerpt(s){filter_note}. "
        f"{remaining} chunk(s) remain.\n\n" + "\n\n".join(sections)
    )


def _build_tools(
    scenario: Scenario,
    store: MockLogStore,
    scorer: ChunkRelevanceScorer,
    use_jev: bool,
    telemetry: TelemetryCollector,
    state: dict[str, Any],
) -> list[StructuredTool]:
    incident = scenario.incident

    def fetch_logs(
        severity: str = "ALL",
        time_start: str = "",
        time_end: str = "",
        limit: int = 4,
    ) -> str:
        raw = store.fetch_logs(
            severity=severity,
            time_start=time_start,
            time_end=time_end,
            limit=limit,
        )
        state["chunks_total"] += len(raw)
        state["chunks_fetched_raw"] += len(raw)
        for cid, _, _ in raw:
            state["all_fetched_ids"].add(cid)

        passed, _scores = _apply_jev_filter(scorer, raw, incident, use_jev)
        state["chunks_passed"] += len(passed)
        for cid, content, _ in raw:
            state["chunk_chars_total"] += len(content)
        for cid, content in passed:
            state["passed_chunk_ids"].add(cid)
            state["chunk_chars_passed"] += len(content)

        return _format_fetch_result(passed, len(raw), store.remaining_count(), use_jev)

    def fetch_metrics() -> str:
        if scenario.metrics_summary:
            return f"METRICS SUMMARY\n{scenario.metrics_summary}"
        return "No metrics available for this incident."

    def submit_diagnosis(diagnosis: str) -> str:
        state["diagnosis"] = diagnosis.strip()
        return "Diagnosis recorded. Investigation complete."

    return [
        StructuredTool.from_function(
            fetch_logs,
            name="fetch_logs",
            description=(
                "Fetch log excerpts from the observability store. "
                "severity: ALL, ERROR, WARN, or INFO. "
                "Optional ISO time_start/time_end (e.g. 2026-10-06T02:01:00Z). "
                "limit: max chunks (default 4)."
            ),
        ),
        StructuredTool.from_function(
            fetch_metrics,
            name="fetch_metrics",
            description="Fetch metrics summary for the active incident.",
        ),
        StructuredTool.from_function(
            submit_diagnosis,
            name="submit_diagnosis",
            description="Submit final root-cause diagnosis when you have enough evidence.",
        ),
    ]


def run_agentic_agent(
    scenario: Scenario,
    telemetry: TelemetryCollector,
    use_jev: bool = False,
) -> dict[str, Any]:
    """
    Run tool-calling agent loop.
    use_jev=False: return all fetched chunks to the LLM.
    use_jev=True: Jev filters each fetch_logs result before the LLM sees it.
    """
    store = MockLogStore(scenario)
    scorer = ChunkRelevanceScorer(
        log_fn=lambda name, latency, meta: telemetry.log_jev(name, latency, **meta)
    )
    state: dict[str, Any] = {
        "diagnosis": "",
        "passed_chunk_ids": set(),
        "all_fetched_ids": set(),
        "chunks_total": 0,
        "chunks_fetched_raw": 0,
        "chunks_passed": 0,
        "chunk_chars_total": 0,
        "chunk_chars_passed": 0,
    }

    tools = _build_tools(scenario, store, scorer, use_jev, telemetry, state)
    tools_by_name = {t.name: t for t in tools}

    llm = build_llm().bind_tools(tools)
    messages: list = [
        SystemMessage(content=AGENTIC_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"{format_incident_block(scenario)}\n\n"
                "LOG EXCERPTS: (none yet — use fetch_logs to retrieve)\n\n"
                f"Log store contains {store.total_chunks} chunk(s) for this service."
            )
        ),
    ]

    max_turns = settings.agent_max_turns
    start = time.perf_counter()

    for turn in range(1, max_turns + 1):
        turn_start = time.perf_counter()
        response = llm.invoke(messages)
        latency = (time.perf_counter() - turn_start) * 1000
        _log_llm_turn(telemetry, messages, response, f"agentic_turn_{turn}")
        telemetry.metrics.calls[-1].latency_ms = latency
        messages.append(response)

        if not response.tool_calls:
            if response.content and not state["diagnosis"]:
                state["diagnosis"] = str(response.content)
            break

        done = False
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call.get("args") or {}
            tool = tools_by_name.get(name)
            if not tool:
                result = f"Unknown tool: {name}"
            else:
                result = tool.invoke(args)

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

            if name == "submit_diagnosis" and state["diagnosis"]:
                done = True
                break

        if done:
            break

    diagnosis = state["diagnosis"]
    if not diagnosis and messages:
        last = messages[-1]
        if isinstance(last, AIMessage) and last.content:
            diagnosis = str(last.content)

    passed_ids = sorted(state["passed_chunk_ids"])
    telemetry.set_chunk_stats(
        chunks_total=state["chunks_fetched_raw"],
        chunks_passed=len(passed_ids),
        chunk_chars_total=state["chunk_chars_total"],
        chunk_chars_passed=state["chunk_chars_passed"],
    )

    correct, eval_details = evaluate_diagnosis(scenario, diagnosis, passed_ids)
    eval_details["agentic_turns"] = min(turn, max_turns)
    eval_details["tools_used"] = state["chunks_fetched_raw"] > 0

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
