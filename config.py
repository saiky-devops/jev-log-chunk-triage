"""Central configuration via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
SCENARIOS_DIR = ROOT / "scenarios"
RESULTS_DIR = ROOT / "results"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    llm_model: str
    typesafe_api_key: str | None
    jev_mode: str  # shadow | live | mock
    benchmark_runs: int
    relevance_threshold: float

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            typesafe_api_key=os.getenv("TYPESAFE_API_KEY"),
            jev_mode=os.getenv("JEV_MODE", "mock").lower(),
            benchmark_runs=int(os.getenv("BENCHMARK_RUNS", "3")),
            relevance_threshold=float(os.getenv("RELEVANCE_THRESHOLD", "0.65")),
        )


settings = Settings.from_env()
