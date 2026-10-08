#!/usr/bin/env python3
"""
Score a raw sample log file with Jev chunk relevance filtering (offline utility).

For full agentic diagnosis use: python scripts/test_agentic.py

Usage:
  python scripts/test_sample_log.py
  python scripts/test_sample_log.py --log samples/report-generator-oom.log
  python scripts/test_sample_log.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
    parser = argparse.ArgumentParser(description="Test Jev chunk scoring on a sample log file")
    parser.add_argument("--log", type=Path, default=None, help="Path to sample .log file")
    parser.add_argument("--incident", type=Path, default=None, help="Incident YAML")
    parser.add_argument("--list", action="store_true", help="List available sample log files")
    args = parser.parse_args()

    if args.list:
        print("Available samples in samples/:\n")
        for log_name, inc_name, desc in SAMPLES:
            print(f"  {log_name:<30} {desc}")
        print("\nExample:")
        print("  python scripts/test_sample_log.py --log samples/crashloop-db-config.log")
        return

    log_path = args.log or DEFAULT_LOG
    incident_path = args.incident or DEFAULT_INCIDENT
    if args.log and not args.incident:
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

    print(f"\nPassed {len(passed)}/{len(chunks)} chunks")
    print(f"Context compression: {pct:.0f}% of characters filtered")


if __name__ == "__main__":
    main()
