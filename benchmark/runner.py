"""Benchmark harness: run agentic agents across scenarios, collect metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.agentic import run_agentic_agent
from benchmark.metrics import aggregate_all
from benchmark.report import save_results
from benchmark.telemetry import RunMetrics, TelemetryCollector
from config import RESULTS_DIR
import config
from scenarios.loader import load_all_scenarios, load_scenario


def run_single(
    scenario_id: str,
    agent_type: str,
    run_index: int,
    raw_dir: Path,
) -> RunMetrics:
    scenario = load_scenario(ROOT / "scenarios" / f"{scenario_id}.yaml")
    telemetry = TelemetryCollector(scenario_id, agent_type, run_index)

    if agent_type == "agentic":
        run_agentic_agent(scenario, telemetry, use_jev=False)
    elif agent_type == "agentic_jev":
        run_agentic_agent(scenario, telemetry, use_jev=True)
    else:
        raise ValueError(f"Unknown agent_type: {agent_type} (use agentic or agentic_jev)")

    metrics = telemetry.metrics
    telemetry.save_raw(raw_dir)
    return metrics


def run_benchmark(
    scenario_filter: list[str] | None = None,
    runs: int | None = None,
    agents: list[str] | None = None,
) -> Path:
    settings = config.settings
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY is required. Copy .env.example to .env and set your key.")
        sys.exit(1)

    runs = runs or settings.benchmark_runs
    agents = agents or ["agentic", "agentic_jev"]
    scenarios = load_all_scenarios()
    if scenario_filter:
        scenarios = [s for s in scenarios if s.id in scenario_filter]

    print(f"Running benchmark: {len(scenarios)} scenarios × {runs} runs × {len(agents)} agents")
    print(f"JEV_MODE={settings.jev_mode}, LLM_MODEL={settings.llm_model}")
    if settings.jev_mode == "shadow":
        print(
            "WARNING: JEV_MODE=shadow scores chunks but does NOT filter — "
            "context compression will be 0% and agentic_jev adds overhead only. "
            "Use JEV_MODE=live for meaningful comparison."
        )
    if "agentic_jev" in agents and settings.jev_mode == "mock":
        print("WARNING: agentic_jev with JEV_MODE=mock uses keyword heuristics only.")

    raw_dir = RESULTS_DIR / "raw"
    all_metrics: list[RunMetrics] = []

    for scenario in scenarios:
        for agent in agents:
            for i in range(runs):
                print(f"  [{agent}] {scenario.id} run {i + 1}/{runs}...", end=" ", flush=True)
                try:
                    metrics = run_single(scenario.id, agent, i, raw_dir)
                    status = "OK" if metrics.correct else "FAIL"
                    print(
                        f"{status} (llm={metrics.llm_calls}, jev={metrics.jev_calls}, "
                        f"chunks={metrics.chunks_passed}/{metrics.chunks_total}, "
                        f"tokens_in={metrics.input_tokens}, {metrics.latency_ms:.0f}ms)"
                    )
                    all_metrics.append(metrics)
                except Exception as exc:
                    print(f"ERROR: {exc}")

    if not all_metrics:
        print("\nNo successful runs. Check API keys, billing, and error messages above.")
        sys.exit(1)

    summary = aggregate_all(all_metrics)
    summary["config"] = {
        "jev_mode": settings.jev_mode,
        "llm_model": settings.llm_model,
        "benchmark_runs": runs,
        "scenarios": [s.id for s in scenarios],
    }
    report_path = save_results(summary)
    print(f"\nReport written to {report_path}")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Jev agentic diagnostic benchmark")
    parser.add_argument(
        "--scenarios",
        default="all",
        help="Comma-separated scenario IDs or 'all'",
    )
    parser.add_argument("--runs", type=int, default=None, help="Runs per scenario per agent")
    parser.add_argument(
        "--agents",
        default="agentic,agentic_jev",
        help="Comma-separated: agentic, agentic_jev",
    )
    parser.add_argument(
        "--jev-mode",
        choices=["shadow", "live", "mock"],
        default=None,
        help="Override JEV_MODE env var",
    )
    args = parser.parse_args()

    if args.jev_mode:
        import importlib
        import os

        os.environ["JEV_MODE"] = args.jev_mode
        importlib.reload(config)

    scenario_filter = None if args.scenarios == "all" else args.scenarios.split(",")
    agents = args.agents.split(",")
    run_benchmark(scenario_filter=scenario_filter, runs=args.runs, agents=agents)


if __name__ == "__main__":
    main()
