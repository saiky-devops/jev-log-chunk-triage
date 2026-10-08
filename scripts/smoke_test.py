#!/usr/bin/env python3
"""Smoke test: scenarios, Jev chunk scoring, and mock log store — no API keys."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os
os.environ.setdefault("JEV_MODE", "mock")

import importlib
import config
importlib.reload(config)

from jev.chunk_scorer import ChunkRelevanceScorer
from scenarios.loader import load_all_scenarios
from tools.log_store import MockLogStore


def main() -> None:
    scenarios = load_all_scenarios()
    assert len(scenarios) >= 5, f"Expected >=5 scenarios, got {len(scenarios)}"
    print(f"Loaded {len(scenarios)} scenarios")

    scorer = ChunkRelevanceScorer()
    for s in scenarios:
        chunks = [(c.id, c.content, c.is_signal) for c in s.log_chunks]
        passed, scores = scorer.filter_chunks(chunks, s.incident)
        signal_ids = {c.id for c in s.log_chunks if c.is_signal}
        passed_ids = {cid for cid, _ in passed}
        recall = 1.0
        if signal_ids:
            recall = len(signal_ids & passed_ids) / len(signal_ids)
        print(
            f"  {s.id}: {len(passed)}/{len(chunks)} chunks passed, "
            f"signal recall={recall:.0%}, signals={len(signal_ids)}"
        )

    s0 = scenarios[0]
    store = MockLogStore(s0)
    batch = store.fetch_logs(severity="ALL", limit=3)
    assert batch, "MockLogStore should return chunks"
    assert store.remaining_count() == len(s0.log_chunks) - 3
    print(f"\nMockLogStore: fetched {len(batch)} chunk(s), {store.remaining_count()} remaining")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
