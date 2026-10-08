#!/usr/bin/env python3
"""
Run the agentic diagnostic loop on one scenario (tool calls + optional Jev per fetch).

Usage:
  python scripts/test_agentic.py
  python scripts/test_agentic.py --scenario oom_heap_exhaustion --jev
  JEV_MODE=live python scripts/test_agentic.py --scenario crashloop_db_config --jev
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.agentic import run_agentic_agent
from benchmark.telemetry import TelemetryCollector
from config import SCENARIOS_DIR
from scenarios.loader import load_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Test agentic loop on one scenario")
    parser.add_argument(
        "--scenario",
        default="oom_heap_exhaustion",
        help="Scenario ID (yaml filename without extension)",
    )
    parser.add_argument(
        "--jev",
        action="store_true",
        help="Apply Jev filter on each fetch_logs result",
    )
    args = parser.parse_args()

    import config as cfg

    if not cfg.settings.openai_api_key:
        print("Set OPENAI_API_KEY in .env")
        sys.exit(1)

    path = SCENARIOS_DIR / f"{args.scenario}.yaml"
    if not path.exists():
        print(f"Scenario not found: {path}")
        sys.exit(1)

    scenario = load_scenario(path)
    agent_type = "agentic_jev" if args.jev else "agentic"
    telemetry = TelemetryCollector(scenario.id, agent_type, 0)

    print(f"Scenario: {scenario.id}")
    print(f"Agent: {agent_type} | JEV_MODE={cfg.settings.jev_mode}")
    print(f"Max turns: {cfg.settings.agent_max_turns}\n")

    result = run_agentic_agent(scenario, telemetry, use_jev=args.jev)
    details = result["eval_details"]

    print(f"LLM calls: {result['metrics'].llm_calls}")
    print(f"Jev calls: {result['metrics'].jev_calls}")
    print(f"Chunks fetched/passed to agent: {result['metrics'].chunks_total}/{result['metrics'].chunks_passed}")
    print(f"Signal recall: {details.get('signal_recall', 0):.0%}")
    print(f"Correct: {result['metrics'].correct}")
    print(f"Turns used: {details.get('agentic_turns', '?')}")
    print("\n--- DIAGNOSIS ---")
    print(result["diagnosis"])


if __name__ == "__main__":
    main()
