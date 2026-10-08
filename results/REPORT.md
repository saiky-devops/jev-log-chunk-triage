# Jev Agentic Diagnostic Agent — Benchmark Results

Generated: 2026-10-08T03:50:59.551903+00:00
JEV_MODE: **shadow** | LLM: **gpt-4o**

## Summary

Both agents use a **tool-calling loop** (`fetch_logs` → reason → `submit_diagnosis`).
Agentic Jev applies relevance filtering to each `fetch_logs` batch before the LLM sees it.
All log data is **mocked** from recorded fixtures.

> **Note:** Shadow mode scores chunks but still passes all fetched context to the LLM.


| Metric | Agentic | Agentic + Jev | Delta |
| --- | ---: | ---: | ---: |
| LLM calls (avg) | 4.2 | 4.5 | — |
| LLM input tokens (avg) | 2658 | 2867 | -7.9% |
| Est. cost USD (avg) | $0.009064 | $0.009894 | -9.2% |
| Chunks passed to LLM (avg) | 3.5 | 3.3 | 4.8% |
| Context compression (avg) | 0.0% | 0.0% | — |
| Signal recall (avg) | 92% | 89% | — |
| Correct diagnosis rate | 83% | 78% | — |
| Latency p50 (ms) | 4009 | 5030 | -25.5% |

Jev chunk scores (avg, Agentic + Jev only): 3.6

## Per-Scenario Results

| Scenario | Agent | Chunks fetched/passed | LLM calls | Input tokens | Compression | Signal recall | Correct | Latency p50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| crashloop_db_config | agentic | 1/1 | 5.0 | 3196 | 0% | 50% | 0% | 5438 |
| crashloop_db_config | agentic_jev | 1/1 | 6.0 | 3810 | 0% | 50% | 0% | 5135 |
| db_connection_cascade | agentic | 2/2 | 2.0 | 1102 | 0% | 100% | 100% | 2038 |
| db_connection_cascade | agentic_jev | 2/2 | 2.0 | 1102 | 0% | 100% | 100% | 2481 |
| oom_heap_exhaustion | agentic | 2/2 | 3.3 | 1949 | 0% | 100% | 100% | 3785 |
| oom_heap_exhaustion | agentic_jev | 2/2 | 3.3 | 1949 | 0% | 100% | 100% | 4364 |
| prompt_injection_in_logs | agentic | 2/2 | 6.0 | 4033 | 0% | 100% | 100% | 5790 |
| prompt_injection_in_logs | agentic_jev | 2/2 | 6.0 | 4073 | 0% | 100% | 100% | 5748 |
| routine_health_polls | agentic | 6/6 | 4.7 | 3158 | 0% | 100% | 100% | 4735 |
| routine_health_polls | agentic_jev | 6/6 | 4.7 | 3115 | 0% | 100% | 100% | 5480 |
| trace_latency_spike | agentic | 8/8 | 4.0 | 2510 | 0% | 100% | 100% | 3572 |
| trace_latency_spike | agentic_jev | 7/7 | 5.0 | 3152 | 0% | 83% | 67% | 5622 |

## Caveats

- Agentic agents use multiple LLM turns; compare token totals, not per-call size alone.
- Jev adds one API call per chunk scored on each fetch.
- All logs and traces are mocked; results may differ on live observability exports.
- LLM behavior varies run-to-run; report averages over multiple runs.
