# Jev Log Relevance Filter — Benchmark Results

Generated: 2026-10-08T02:47:26.001829+00:00
JEV_MODE: **live** | LLM: **gpt-4o**

## Summary

Agent A dumps **all** log/trace chunks into the LLM. Agent B uses Jev to score
chunk relevance and passes only high-signal excerpts to the diagnostic LLM.
All log data is **mocked** from recorded fixtures.

| Metric | Baseline | With Jev | Reduction |
| --- | ---: | ---: | ---: |
| LLM input tokens (avg) | 611 | 324 | 47.1% |
| Est. cost USD (avg) | $0.002928 | $0.002148 | 26.6% |
| Chunks passed to LLM (avg) | 7.7 | 2.0 | 73.9% |
| Context compression (avg) | 0% | 63.9% | — |
| Signal recall (avg) | 100% | 100% | — |
| Correct diagnosis rate | 100% | 100% | — |
| Latency p50 (ms) | 1433 | 2414 | -68.5% |

Jev chunk scores (avg, Agent B only): 7.9

## Per-Scenario Results

| Scenario | Agent | Chunks in/out | Input tokens | Compression | Signal recall | Correct | Latency p50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| crashloop_db_config | baseline | 8/8 | 634 | 0% | 100% | 100% | 1390 |
| crashloop_db_config | with_jev | 8/4 | 440 | 42% | 100% | 100% | 2792 |
| db_connection_cascade | baseline | 8/8 | 593 | 0% | 100% | 100% | 1683 |
| db_connection_cascade | with_jev | 8/2 | 334 | 56% | 100% | 100% | 2364 |
| oom_heap_exhaustion | baseline | 8/8 | 835 | 0% | 100% | 100% | 1349 |
| oom_heap_exhaustion | with_jev | 8/2 | 385 | 68% | 100% | 100% | 2291 |
| prompt_injection_in_logs | baseline | 8/8 | 526 | 0% | 100% | 100% | 1427 |
| prompt_injection_in_logs | with_jev | 8/2 | 271 | 60% | 100% | 100% | 2533 |
| routine_health_polls | baseline | 6/6 | 568 | 0% | 100% | 100% | 1413 |
| routine_health_polls | with_jev | 6/0 | 197 | 100% | 100% | 100% | 1902 |
| trace_latency_spike | baseline | 8/8 | 512 | 0% | 100% | 100% | 1504 |
| trace_latency_spike | with_jev | 8/2 | 314 | 58% | 100% | 100% | 2450 |

## Caveats

- Savings depend on log volume and signal-to-noise ratio in your observability stream.
- Jev adds one API call per chunk; trade LLM tokens for Jev calls.
- All logs and traces are mocked; results may differ on live Datadog/Splunk exports.
- LLM behavior varies run-to-run; report averages over multiple runs.
