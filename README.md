# Jev Agentic Log Diagnostic Agent

Benchmark and demo for an **agentic diagnostic agent** that investigates incidents via tool calls — fetching logs on demand — with optional **Jev** (TypeSafe's System One model) relevance filtering on each fetch.

> **Scope:** All logs are mocked fixtures (`scenarios/`, `samples/`). This validates the agentic + Jev pattern reproducibly; it is not a production log pipeline.

## The problem

Diagnostic agents often receive massive log exports or Datadog trace dumps. Stuffing everything into the LLM context window explodes **tokens, cost, and latency**. Most lines are noise — and a single dump may not contain enough signal to diagnose.

## The approach

An **agentic loop**: the LLM starts with incident context only, calls tools to fetch evidence, and submits a diagnosis when ready. Jev optionally filters each fetch batch before the LLM sees it.

```
Alert → incident context (no logs yet)
  → LLM: fetch_logs(severity=ERROR)
  → [Jev filter batch] → tool result
  → LLM: fetch_metrics()
  → LLM: submit_diagnosis(...)
```

| | Agentic | Agentic + Jev |
| --- | --- | --- |
| CLI name | `agentic` | `agentic_jev` |
| Log access | `fetch_logs` tool (mock store) | Same |
| Per-fetch filtering | None — all fetched chunks shown | Jev scores each batch |
| LLM calls | Multiple (reason → act → observe) | Multiple |
| Recovery | Re-fetch with different filters if context is thin | Same + compact excerpts |

## End-to-end flow (alert → LLM response)

```mermaid
flowchart TD
    A[Alert fires] --> B[Build incident context]
    B --> M[LLM starts with incident only — no logs]
    M --> N[LLM calls fetch_logs tool]
    N --> O[MockLogStore returns chunk batch]
    O --> Q{Agentic + Jev?}
    Q -->|yes| R[Jev filter this batch]
    Q -->|no| S[Return all fetched chunks]
    R --> T[Tool result back to LLM]
    S --> T
    T --> U{Enough evidence?}
    U -->|no| N
    U -->|yes| V[submit_diagnosis → DIAGNOSIS]
```

| Step | What happens | In this repo |
| --- | --- | --- |
| 1. **Alert** | Pager/monitor fires | `scenario.incident` or `samples/incident-*.yaml` |
| 2. **Incident context** | LLM sees incident — **no logs yet** | `agents/agentic.py` initial prompt |
| 3. **fetch_logs** | LLM requests logs (severity, time window) | `tools/log_store.py` |
| 4. **Filter batch** | Jev filters fetch (Agentic + Jev only) | `jev/chunk_scorer.py` in tool handler |
| 5. **Reason & repeat** | Re-fetch or call `submit_diagnosis` | Loop up to `AGENT_MAX_TURNS` |

### Example (Agentic + Jev)

```
Turn 1:  fetch_logs(severity=ERROR)  → Jev keeps 2 signal chunks
Turn 2:  fetch_metrics()             → memory 250-255Mi / 256Mi limit
Turn 3:  submit_diagnosis(...)       → DIAGNOSIS: heap OOM; recommend 512Mi limit
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY, TYPESAFE_API_KEY

python scripts/smoke_test.py                                    # offline, no keys
python scripts/test_agentic.py --scenario oom_heap_exhaustion     # one scenario
JEV_MODE=live python scripts/test_agentic.py --scenario oom_heap_exhaustion --jev
JEV_MODE=live python run_benchmark.py --runs 3                    # full benchmark
```

Results: `results/REPORT.md`, `results/summary.json`, `results/charts/`

## Configuration

Copy `.env.example` to `.env`. Do **not** commit `.env`.

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | Required for LLM + tool calling |
| `LLM_MODEL` | `gpt-4o-mini` | Diagnostic LLM (`gpt-4o` recommended for benchmark) |
| `TYPESAFE_API_KEY` | — | Required for live Jev scoring (not needed in `mock` mode) |
| `JEV_MODE` | `mock` | `mock` = heuristics, `shadow` = score but pass all, `live` = filter |
| `RELEVANCE_THRESHOLD` | `0.65` | Chunks below this score are dropped in `live` mode |
| `AGENT_MAX_TURNS` | `8` | Max ReAct loop iterations |
| `BENCHMARK_RUNS` | `3` | Runs per scenario per agent |

## Scenarios (mocked logs & traces)

| Scenario | Signal buried in |
| --- | --- |
| `oom_heap_exhaustion` | OOM / heap errors among health checks |
| `crashloop_db_config` | Invalid DATABASE_URL among probe logs |
| `db_connection_cascade` | Connection refused among access logs |
| `prompt_injection_in_logs` | Injection line + NPE among routine logs |
| `routine_health_polls` | All noise — benign health-check traffic |
| `trace_latency_spike` | Slow DB span among normal traces |

Matching sample files in `samples/`. Score chunks offline: `python scripts/test_sample_log.py --list`.

## Metrics

- **LLM calls per run** — multi-turn agentic cost
- **LLM input tokens** — total across all turns
- **Chunks fetched / passed** — after optional Jev filter
- **Context compression %** — chars filtered by Jev per fetch
- **Signal recall** — ground-truth signal chunks reached the LLM
- **Correct diagnosis rate**
- **Jev calls** — one per chunk scored
- **Latency** p50 / p95

## Project layout

```
agents/           agentic.py (tool loop), common.py (shared utilities)
tools/            log_store.py — mock fetch_logs backend
jev/              chunk_scorer.py — Jev relevance scoring
scenarios/        YAML fixtures (benchmark)
samples/          standalone .log + incident YAML
scripts/          smoke_test.py, test_agentic.py, test_sample_log.py, log_utils.py
benchmark/        runner, telemetry, metrics, report
results/          REPORT.md, summary.json, charts (results/raw/ is gitignored)
article/          write-up draft
```

## References

- [article/ARTICLE.md](article/ARTICLE.md) — experiment write-up
- [Building a Harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev)
- [langchain-typesafe](https://pypi.org/project/langchain-typesafe/)
