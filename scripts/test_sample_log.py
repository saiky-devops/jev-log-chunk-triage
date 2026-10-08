#!/usr/bin/env python3
"""
Score a raw sample log file with Jev chunk relevance filtering.

Usage:
  python scripts/test_sample_log.py
  python scripts/test_sample_log.py --log samples/report-generator-oom.log
  JEV_MODE=live python scripts/test_sample_log.py --diagnose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.common import build_diagnosis_prompt, build_llm, invoke_llm_diagnosis
from jev.chunk_scorer import ChunkRelevanceScorer
from scripts.log_utils import chunk_by_blank_lines, load_incident, load_log_lines

SAMPLES = [
    ("report-generator-oom.log", "incident-report-generator-oom.yaml", "OOM heap exhaustion"),
    ("crashloop-db-config.log", "incident-crashloop-db-config.yaml", "CrashLoop bad DATABASE_URL"),
    ("db-connection-cascade.log", "incident-db-connection-cascade.yaml", "DB connection refused"),
    ("prompt-injection.log", "incident-prompt-injection.yaml", "NPE + log injection"),
    ("trace-latency-spike.log", "incident-trace-latency-spike.yaml", "Slow postgres.query span"),
    ("routine-health-polls.log", "incident-routine-health-polls.yaml", "All noise (benign)"),
]

DEFAULT_LOG = ROOT / "samples" / "report-generator-oom.log"
DEFAULT_INCIDENT = ROOT / "samples" / "incident-report-generator-oom.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Jev filtering on a sample log file")
    parser.add_argument("--log", type=Path, default=None, help="Path to sample .log file")
    parser.add_argument("--incident", type=Path, default=None, help="Incident YAML")
    parser.add_argument("--list", action="store_true", help="List available sample log files")
    parser.add_argument("--diagnose", action="store_true", help="Run LLM diagnosis on filtered chunks")
    args = parser.parse_args()

    if args.list:
        print("Available samples in samples/:\n")
        for log_name, inc_name, desc in SAMPLES:
            print(f"  {log_name:<30} {desc}")
        print("\nExample:")
        print("  python scripts/test_sample_log.py --log samples/crashloop-db-config.log \\")
        print("    --incident samples/incident-crashloop-db-config.yaml")
        return

    log_path = args.log or DEFAULT_LOG
    incident_path = args.incident or DEFAULT_INCIDENT
    if args.log and not args.incident:
        # Auto-pair incident file when log name is known
        for log_name, inc_name, _ in SAMPLES:
            if log_path.name == log_name:
                incident_path = ROOT / "samples" / inc_name
                break

    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        sys.exit(1)

    incident = load_incident(incident_path)
    lines = load_log_lines(log_path)
    chunks = chunk_by_blank_lines(lines)

    print(f"Log: {log_path.name}")
    print(f"Lines: {len(lines)}  Chunks: {len(chunks)}")
    print(f"JEV_MODE={__import__('config').settings.jev_mode}\n")

    scorer = ChunkRelevanceScorer()
    chunk_tuples = [(cid, content, False) for cid, content in chunks]
    passed, scores = scorer.filter_chunks(chunk_tuples, incident)

    print(f"{'CHUNK':<12} {'RELEVANCE':>10}  {'PASS':>5}  PREVIEW")
    print("-" * 70)
    for score in scores:
        preview = next(c for cid, c in chunks if cid == score.chunk_id).split("\n")[0][:45]
        print(
            f"{score.chunk_id:<12} {score.relevance:>10.3f}  "
            f"{'yes' if score.passed else 'no':>5}  {preview}..."
        )

    total_chars = sum(len(c) for _, c in chunks)
    passed_chars = sum(len(c) for _, c in passed)
    pct = (1 - passed_chars / total_chars) * 100 if total_chars else 0

    print(f"\nPassed {len(passed)}/{len(chunks)} chunks to LLM")
    print(f"Context compression: {pct:.0f}% of characters filtered")

    if args.diagnose:
        import config as cfg
        if not cfg.settings.openai_api_key:
            print("\nSet OPENAI_API_KEY in .env to run --diagnose")
            sys.exit(1)
        from benchmark.telemetry import TelemetryCollector

        class ScenarioShim:
            def __init__(self, inc: dict, metrics: str = ""):
                self.incident = inc
                self.metrics_summary = inc.get("metrics_summary", metrics)
                self.runbook_excerpt = ""

        scenario = ScenarioShim(incident, incident.get("metrics_summary", ""))
        telemetry = TelemetryCollector("sample_log", "with_jev", 0)
        llm = build_llm()
        messages = build_diagnosis_prompt(scenario, passed)  # type: ignore[arg-type]
        diagnosis = invoke_llm_diagnosis(llm, messages, telemetry, "sample_diagnose")
        print("\n--- DIAGNOSIS ---")
        print(diagnosis)


if __name__ == "__main__":
    main()
