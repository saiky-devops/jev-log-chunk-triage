# Jev as a Log Relevance Filter for Agentic Diagnostic Agents

When TypeSafe released Jev, I started wondering: where does a fast decision model fit if we're **not** trying to replace LLM reasoning entirely?

One answer stood out — **context bloat** in agentic observability workflows.

If you build a diagnostic agent over Kubernetes logs or Datadog traces, the naive pattern is: fetch everything, dump it into the LLM, ask for a root cause. A better pattern is an **agent loop** — start with the alert, fetch logs on demand, re-fetch if context is thin. But each fetch can still be huge.

That's two bounded decisions:

> *Should the agent fetch more logs?* (tool loop)  
> *Does this fetched chunk contain anomaly signal relevant to this incident?* (Jev)

Jev handles the second.

## The hypothesis

An agentic diagnostic agent calls `fetch_logs` as a tool. **Jev scores each returned batch** for relevance before the LLM reads it — keeping multi-turn investigations compact without losing the ability to re-fetch.

Deterministic code handles chunking and fetching. Jev handles relevance per batch. The frontier LLM handles reasoning and diagnosis.

## The experiment

Reproducible benchmark with **mocked log chunks** (no live Datadog or cluster required).

Both agents use **LangChain tool calling**, **`gpt-4o`**, and the same scenarios. The only difference:

| Agentic | Agentic + Jev |
| --- | --- |
| Tool loop, all fetched chunks shown | Tool loop, Jev `Noul` filter per fetch |

**6 scenarios** — OOM, CrashLoop config, DB cascade, prompt injection, routine noise, trace latency spike.

Each scenario marks ground-truth **signal chunks** for **signal recall** measurement.

## What we measure

- LLM **calls per run** and **input tokens** (multi-turn totals)
- **Context compression** on each fetch
- **Signal recall** and **correct diagnosis rate**
- Jev calls per chunk scored

Run shadow mode first (`JEV_MODE=shadow`) to validate scores, then live mode to enforce filtering.

## Architectural takeaway

```
Alert → [ agent: fetch_logs → Jev filter batch → reason ]* → submit_diagnosis
```

Jev decides **what the agent sees** on each fetch. The tool loop decides **when to fetch more**.

## Reproduce

```bash
git clone https://github.com/saiky-devops/jev-log-relevance-filter
cd jev-log-relevance-filter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python scripts/smoke_test.py
python scripts/test_agentic.py --scenario oom_heap_exhaustion --jev
JEV_MODE=live python run_benchmark.py --runs 3
```

See [results/REPORT.md](../results/REPORT.md) for measured numbers.

## References

- [Building a Harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev)
- [langchain-typesafe](https://pypi.org/project/langchain-typesafe/)
