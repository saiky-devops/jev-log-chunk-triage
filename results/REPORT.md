# Jev Agentic Diagnostic Agent — Benchmark Results

Generated: 2026-10-08T03:57:36.900115+00:00
JEV_MODE: **live** | LLM: **gpt-4o**

## Summary

Both agents use a **tool-calling loop** (`fetch_logs` → reason → `submit_diagnosis`).
Agentic Jev applies relevance filtering to each `fetch_logs` batch before the LLM sees it.
All log data is **mocked** from recorded fixtures.

| Metric | Agentic | Agentic + Jev | Delta |
| --- | ---: | ---: | ---: |
| LLM calls (avg) | 5.2 | 5.1 | — |
| LLM input tokens (avg) | 4508 | 3983 | 11.7% |
| Est. cost USD (avg) | $0.013514 | $0.012233 | 9.5% |
| Chunks passed to LLM (avg) | 7.7 | 2.6 | 65.9% |
| Context compression (avg) | 0.0% | 53.0% | — |
| Signal recall (avg) | 100% | 100% | — |
| Correct diagnosis rate | 100% | 100% | — |
| Latency p50 (ms) | 4724 | 5275 | -11.7% |

Jev chunk scores (avg, Agentic + Jev only): 7.9

## Per-Scenario Results

| Scenario | Agent | Chunks fetched/passed | LLM calls | Input tokens | Compression | Signal recall | Correct | Latency p50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| crashloop_db_config | agentic | 8/8 | 5.0 | 4357 | 0% | 100% | 100% | 4741 |
| crashloop_db_config | agentic_jev | 7/4 | 5.3 | 4406 | 42% | 100% | 100% | 5210 |
| db_connection_cascade | agentic | 8/8 | 4.7 | 4085 | 0% | 100% | 100% | 3899 |
| db_connection_cascade | agentic_jev | 8/2 | 4.7 | 3756 | 56% | 100% | 100% | 4814 |
| oom_heap_exhaustion | agentic | 8/8 | 5.0 | 4796 | 0% | 100% | 100% | 4705 |
| oom_heap_exhaustion | agentic_jev | 7/3 | 5.0 | 4196 | 54% | 100% | 100% | 4757 |
| prompt_injection_in_logs | agentic | 8/8 | 5.7 | 4750 | 0% | 100% | 100% | 5414 |
| prompt_injection_in_logs | agentic_jev | 8/3 | 5.7 | 4260 | 52% | 100% | 100% | 6236 |
| routine_health_polls | agentic | 6/6 | 5.7 | 4878 | 0% | 100% | 100% | 5422 |
| routine_health_polls | agentic_jev | 6/3 | 5.0 | 3774 | 55% | 100% | 100% | 5113 |
| trace_latency_spike | agentic | 8/8 | 5.3 | 4184 | 0% | 100% | 100% | 5076 |
| trace_latency_spike | agentic_jev | 8/2 | 5.0 | 3507 | 58% | 100% | 100% | 5433 |

## Caveats

- Agentic agents use multiple LLM turns; compare token totals, not per-call size alone.
- Jev adds one API call per chunk scored on each fetch.
- All logs and traces are mocked; results may differ on live observability exports.
- LLM behavior varies run-to-run; report averages over multiple runs.
