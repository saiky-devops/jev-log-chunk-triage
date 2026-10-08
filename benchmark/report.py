"""Generate benchmark report and charts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from config import RESULTS_DIR


def write_markdown_report(summary: dict[str, Any], output_path: Path) -> None:
    by_agent = summary["by_agent"]
    plain = by_agent.get("agentic", {})
    jev = by_agent.get("agentic_jev", {})

    def pct_reduction(base_val: float, jev_val: float) -> str:
        if base_val == 0:
            return "N/A"
        return f"{((base_val - jev_val) / base_val) * 100:.1f}%"

    cfg = summary.get("config", {})
    jev_mode = cfg.get("jev_mode", "unknown")
    llm_model = cfg.get("llm_model", "unknown")

    lines = [
        "# Jev Agentic Diagnostic Agent — Benchmark Results",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"JEV_MODE: **{jev_mode}** | LLM: **{llm_model}**",
        "",
        "## Summary",
        "",
        "Both agents use a **tool-calling loop** (`fetch_logs` → reason → `submit_diagnosis`).",
        "Agentic Jev applies relevance filtering to each `fetch_logs` batch before the LLM sees it.",
        "All log data is **mocked** from recorded fixtures.",
        *(["", "> **Note:** Shadow mode scores chunks but still passes all fetched context to the LLM.", ""]
          if jev_mode == "shadow" else []),
        "",
        "| Metric | Agentic | Agentic + Jev | Delta |",
        "| --- | ---: | ---: | ---: |",
        f"| LLM calls (avg) | {plain.get('llm_calls_avg', 0):.1f} | {jev.get('llm_calls_avg', 0):.1f} | — |",
        f"| LLM input tokens (avg) | {plain.get('input_tokens_avg', 0):.0f} | {jev.get('input_tokens_avg', 0):.0f} | {pct_reduction(plain.get('input_tokens_avg', 0), jev.get('input_tokens_avg', 0))} |",
        f"| Est. cost USD (avg) | ${plain.get('cost_usd_avg', 0):.6f} | ${jev.get('cost_usd_avg', 0):.6f} | {pct_reduction(plain.get('cost_usd_avg', 0), jev.get('cost_usd_avg', 0))} |",
        f"| Chunks passed to LLM (avg) | {plain.get('chunks_passed_avg', 0):.1f} | {jev.get('chunks_passed_avg', 0):.1f} | {pct_reduction(plain.get('chunks_passed_avg', 0), jev.get('chunks_passed_avg', 0))} |",
        f"| Context compression (avg) | {plain.get('context_compression_pct_avg', 0):.1f}% | {jev.get('context_compression_pct_avg', 0):.1f}% | — |",
        f"| Signal recall (avg) | {plain.get('signal_recall_avg', 1)*100:.0f}% | {jev.get('signal_recall_avg', 0)*100:.0f}% | — |",
        f"| Correct diagnosis rate | {plain.get('correct_rate', 0)*100:.0f}% | {jev.get('correct_rate', 0)*100:.0f}% | — |",
        f"| Latency p50 (ms) | {plain.get('latency_ms_p50', 0):.0f} | {jev.get('latency_ms_p50', 0):.0f} | {pct_reduction(plain.get('latency_ms_p50', 0), jev.get('latency_ms_p50', 0))} |",
        "",
        f"Jev chunk scores (avg, Agentic + Jev only): {jev.get('jev_calls_avg', 0):.1f}",
        "",
        "## Per-Scenario Results",
        "",
        "| Scenario | Agent | Chunks fetched/passed | LLM calls | Input tokens | Compression | Signal recall | Correct | Latency p50 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in summary["by_scenario"]:
        chunks = f"{row['chunks_total_avg']:.0f}/{row['chunks_passed_avg']:.0f}"
        lines.append(
            f"| {row['scenario_id']} | {row['agent_type']} | {chunks} | "
            f"{row['llm_calls_avg']:.1f} | {row['input_tokens_avg']:.0f} | "
            f"{row['context_compression_pct_avg']:.0f}% | "
            f"{row['signal_recall_avg']*100:.0f}% | {row['correct_rate']*100:.0f}% | "
            f"{row['latency_ms_p50']:.0f} |"
        )

    lines.extend([
        "",
        "## Caveats",
        "",
        "- Agentic agents use multiple LLM turns; compare token totals, not per-call size alone.",
        "- Jev adds one API call per chunk scored on each fetch.",
        "- All logs and traces are mocked; results may differ on live observability exports.",
        "- LLM behavior varies run-to-run; report averages over multiple runs.",
        "",
    ])

    output_path.write_text("\n".join(lines))


def generate_charts(summary: dict[str, Any], charts_dir: Path) -> list[Path]:
    charts_dir.mkdir(parents=True, exist_ok=True)
    if not summary.get("by_scenario"):
        return []
    df = pd.DataFrame(summary["by_scenario"])
    paths: list[Path] = []
    agent_types = sorted(df["agent_type"].unique())
    colors = ["#4C72B0", "#55A868", "#DD8452", "#C44E52"]

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot = df.pivot(index="scenario_id", columns="agent_type", values="input_tokens_avg")
    pivot.plot(kind="bar", ax=ax, color=colors[: len(pivot.columns)])
    ax.set_title("LLM Input Tokens per Scenario")
    ax.set_ylabel("Input tokens")
    ax.legend(title="Agent")
    fig.tight_layout()
    p1 = charts_dir / "input_tokens_by_scenario.png"
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    paths.append(p1)

    if "agentic_jev" in agent_types:
        fig, ax = plt.subplots(figsize=(10, 5))
        jev_df = df[df["agent_type"] == "agentic_jev"]
        ax.bar(jev_df["scenario_id"], jev_df["context_compression_pct_avg"], color="#55A868")
        ax.set_title("Context Compression (Agentic + Jev)")
        ax.set_ylabel("% chars filtered")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        p2 = charts_dir / "context_compression.png"
        fig.savefig(p2, dpi=150)
        plt.close(fig)
        paths.append(p2)

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot_lat = df.pivot(index="scenario_id", columns="agent_type", values="latency_ms_p50")
    pivot_lat.plot(kind="bar", ax=ax, color=colors[: len(pivot_lat.columns)])
    ax.set_title("Latency p50 (ms) per Scenario")
    ax.set_ylabel("ms")
    ax.legend(title="Agent")
    fig.tight_layout()
    p3 = charts_dir / "latency_by_scenario.png"
    fig.savefig(p3, dpi=150)
    plt.close(fig)
    paths.append(p3)

    return paths


def save_results(summary: dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "raw").mkdir(exist_ok=True)
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    report_path = RESULTS_DIR / "REPORT.md"
    write_markdown_report(summary, report_path)
    generate_charts(summary, RESULTS_DIR / "charts")
    return report_path
