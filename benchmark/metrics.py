"""Aggregate benchmark metrics across runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median
from typing import Any

from benchmark.telemetry import RunMetrics


@dataclass
class AggregatedMetrics:
    agent_type: str
    scenario_id: str
    runs: int
    llm_calls_avg: float
    jev_calls_avg: float
    input_tokens_avg: float
    output_tokens_avg: float
    cost_usd_avg: float
    chunks_total_avg: float
    chunks_passed_avg: float
    context_compression_pct_avg: float
    signal_recall_avg: float
    latency_ms_p50: float
    latency_ms_p95: float
    correct_rate: float


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def aggregate_runs(runs: list[RunMetrics]) -> AggregatedMetrics:
    if not runs:
        raise ValueError("No runs to aggregate")
    latencies = [r.latency_ms for r in runs]
    return AggregatedMetrics(
        agent_type=runs[0].agent_type,
        scenario_id=runs[0].scenario_id,
        runs=len(runs),
        llm_calls_avg=mean(r.llm_calls for r in runs),
        jev_calls_avg=mean(r.jev_calls for r in runs),
        input_tokens_avg=mean(r.input_tokens for r in runs),
        output_tokens_avg=mean(r.output_tokens for r in runs),
        cost_usd_avg=mean(r.estimated_cost_usd() for r in runs),
        chunks_total_avg=mean(r.chunks_total for r in runs),
        chunks_passed_avg=mean(r.chunks_passed for r in runs),
        context_compression_pct_avg=mean(r.context_compression_pct for r in runs),
        signal_recall_avg=mean(r.signal_recall for r in runs),
        latency_ms_p50=median(latencies),
        latency_ms_p95=percentile(latencies, 0.95),
        correct_rate=mean(1.0 if r.correct else 0.0 for r in runs),
    )


def aggregate_all(all_runs: list[RunMetrics]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[RunMetrics]] = {}
    for run in all_runs:
        groups.setdefault((run.agent_type, run.scenario_id), []).append(run)

    by_scenario = [asdict(aggregate_runs(runs)) for runs in groups.values()]

    by_agent: dict[str, list[RunMetrics]] = {}
    for run in all_runs:
        by_agent.setdefault(run.agent_type, []).append(run)

    agent_totals = {}
    for agent, runs in by_agent.items():
        agent_totals[agent] = {
            "runs": len(runs),
            "llm_calls_avg": mean(r.llm_calls for r in runs),
            "jev_calls_avg": mean(r.jev_calls for r in runs),
            "input_tokens_avg": mean(r.input_tokens for r in runs),
            "output_tokens_avg": mean(r.output_tokens for r in runs),
            "cost_usd_avg": mean(r.estimated_cost_usd() for r in runs),
            "chunks_passed_avg": mean(r.chunks_passed for r in runs),
            "context_compression_pct_avg": mean(r.context_compression_pct for r in runs),
            "signal_recall_avg": mean(r.signal_recall for r in runs),
            "latency_ms_p50": median(r.latency_ms for r in runs),
            "latency_ms_p95": percentile([r.latency_ms for r in runs], 0.95),
            "correct_rate": mean(1.0 if r.correct else 0.0 for r in runs),
        }

    return {"by_scenario": by_scenario, "by_agent": agent_totals}
