# Jev as a Log Relevance Filter for Diagnostic Agents

When TypeSafe released Jev, I started wondering: where does a fast decision model fit if we're **not** trying to replace LLM reasoning entirely?

One answer stood out immediately — **context bloat**.

If you build a diagnostic agent over Kubernetes logs or Datadog traces, the naive pattern is: fetch everything, dump it into the LLM, ask for a root cause. That works in a demo. In production it burns tokens, adds latency, and buries the five lines that actually matter inside ten thousand lines of health-check noise.

That's a bounded decision:

> *Does this log chunk contain anomaly signal relevant to the incident I'm investigating?*

Jev is built for exactly that kind of question.

## The hypothesis

Instead of putting massive raw log or trace exports into the LLM context window, **Jev scores each chunk for relevance** and passes only high-signal excerpts to the diagnostic agent.

Deterministic code handles chunking and fetching. Jev handles relevance. The frontier LLM handles actual diagnosis — on a fraction of the context.

## The experiment

I built a reproducible benchmark with **mocked log and trace chunks** (no live Datadog or cluster required).

Both agents use **LangChain**, **`gpt-4o`**, and the same diagnosis prompt. The only difference:

| Agent A (baseline) | Agent B (with Jev) |
| --- | --- |
| Concatenate **all** chunks → LLM | Jev `Noul` score per chunk → filter → LLM |

**6 scenarios** — OOM heap exhaustion, CrashLoop config error, DB connection cascade, prompt injection in logs, routine health-check noise, trace latency spike.

Each scenario marks ground-truth **signal chunks** so we can measure **signal recall** (did the filter keep the lines that matter?).

## What we measure

- LLM **input tokens** — the primary savings lever
- **Context compression** — % of log chars filtered out
- **Signal recall** — filter quality
- **Correct diagnosis rate** — did the compact context still produce the right answer?
- Jev calls (one per chunk) vs LLM calls (one diagnosis)

Run shadow mode first (`JEV_MODE=shadow`) to validate scores without changing behavior, then live mode to enforce filtering.

## Expected results pattern

On signal-heavy scenarios (OOM, CrashLoop, DB outage), Agent B should show:

- **Large input token reduction** — often 60–80% depending on noise ratio
- **Full signal recall** when Jev threshold is tuned correctly
- Similar or slightly better diagnosis quality — the LLM sees *more signal per token*

On all-noise scenarios (`routine_health_polls`), Jev should filter nearly everything; the LLM gets minimal context and should still conclude "benign / no anomaly."

Tradeoff to disclose: **Jev adds one API call per chunk.** You trade LLM tokens for Jev calls. On high-volume streams, batching and cheap code filters (ERROR-level only) before Jev keep this economical.

## What I'm not claiming

- Jev replaces the diagnostic LLM — it **feeds** it better context
- Universal latency wins — scoring N chunks adds overhead; savings show up most on token cost and downstream LLM latency
- Production-ready log pipeline — this uses mocked fixtures; real pipelines need chunk sizing, retention, and calibration on your log formats

## Architectural takeaway

```
[ chunk logs ] → [ code: split/window ] → [ Jev: relevance score ] → [ LLM: diagnose ] → action
```

This is complementary to agent-loop optimizations (triage, tool gates). Those decide **what the agent does**. Jev context filtering decides **what the agent sees**.

Both matter. This benchmark focuses on the second — because that's where observability-heavy agents hurt most.

## Reproduce

```bash
git clone https://github.com/saiky-devops/jev-k8s-agent-benchmark
cd jev-k8s-agent-benchmark
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python scripts/smoke_test.py
python scripts/test_sample_log.py --list
JEV_MODE=live python run_benchmark.py --runs 3
```

See [results/REPORT.md](../results/REPORT.md) for measured numbers.

## References

- [Building a Harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev)
- [langchain-typesafe](https://pypi.org/project/langchain-typesafe/)
