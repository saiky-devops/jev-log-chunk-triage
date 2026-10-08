# Jev Agentic Diagnostic Agent — Benchmark Results

Generated: 2026-10-08T04:14:39.214870+00:00
JEV_MODE: **live** | LLM: **gpt-4o**

## Summary

Both agents use a **tool-calling loop** (`fetch_logs` → reason → `submit_diagnosis`).
Agentic Jev applies relevance filtering to each `fetch_logs` batch before the LLM sees it.
All log data is **mocked** from recorded fixtures.

| Metric | Agentic | Agentic + Jev | Delta |
| --- | ---: | ---: | ---: |
| LLM calls (avg) | 5.1 | 5.0 | — |
| LLM input tokens (avg) | 4668 | 3960 | 15.2% |
| Est. cost USD (avg) | $0.014009 | $0.012088 | 13.7% |
| Chunks passed to LLM (avg) | 7.7 | 2.4 | 68.8% |
| Context compression (avg) | 0.0% | 56.6% | — |
| Signal recall (avg) | 100% | 100% | — |
| Correct diagnosis rate | 100% | 100% | — |
| Latency p50 (ms) | 4731 | 5173 | -9.4% |

Jev chunk scores (avg, Agentic + Jev only): 7.7

## Per-Scenario Results

| Scenario | Agent | Chunks fetched/passed | LLM calls | Input tokens | Compression | Signal recall | Correct | Latency p50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| crashloop_db_config | agentic | 8/8 | 5.0 | 4357 | 0% | 100% | 100% | 5386 |
| crashloop_db_config | agentic_jev | 7/4 | 5.3 | 4406 | 42% | 100% | 100% | 5413 |
| db_connection_cascade | agentic | 8/8 | 4.0 | 3635 | 0% | 100% | 100% | 3392 |
| db_connection_cascade | agentic_jev | 8/2 | 4.0 | 3201 | 56% | 100% | 100% | 4378 |
| disk_full_deploy | agentic | 8/8 | 5.7 | 5898 | 0% | 100% | 100% | 4731 |
| disk_full_deploy | agentic_jev | 6/2 | 5.0 | 4214 | 58% | 100% | 100% | 5322 |
| oom_heap_exhaustion | agentic | 7/7 | 5.0 | 4760 | 0% | 100% | 100% | 4189 |
| oom_heap_exhaustion | agentic_jev | 6/2 | 5.0 | 4060 | 61% | 100% | 100% | 4824 |
| prompt_injection_in_logs | agentic | 8/8 | 5.0 | 4001 | 0% | 100% | 100% | 4047 |
| prompt_injection_in_logs | agentic_jev | 8/3 | 5.7 | 4280 | 48% | 100% | 100% | 5620 |
| rate_limit_storm | agentic | 8/8 | 5.3 | 5320 | 0% | 100% | 100% | 4875 |
| rate_limit_storm | agentic_jev | 8/2 | 5.0 | 4189 | 64% | 100% | 100% | 4907 |
| routine_health_polls | agentic | 6/6 | 6.0 | 5057 | 0% | 100% | 100% | 5282 |
| routine_health_polls | agentic_jev | 6/2 | 5.0 | 3571 | 65% | 100% | 100% | 5116 |
| tls_cert_expired | agentic | 8/8 | 5.3 | 5177 | 0% | 100% | 100% | 4318 |
| tls_cert_expired | agentic_jev | 8/3 | 5.0 | 4210 | 58% | 100% | 100% | 5336 |
| trace_latency_spike | agentic | 8/8 | 5.0 | 3808 | 0% | 100% | 100% | 4757 |
| trace_latency_spike | agentic_jev | 8/2 | 5.0 | 3507 | 58% | 100% | 100% | 6268 |

## Caveats

- Agentic agents use multiple LLM turns; compare token totals, not per-call size alone.
- Jev adds one API call per chunk scored on each fetch.
- All logs and traces are mocked; results may differ on live observability exports.
- LLM behavior varies run-to-run; report averages over multiple runs.
