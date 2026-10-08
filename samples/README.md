# Sample log files

Standalone mock log and trace exports for manual testing outside the YAML scenario benchmark.

## Samples

| Log file | Incident file | What to look for |
| --- | --- | --- |
| `report-generator-oom.log` | `incident-report-generator-oom.yaml` | OOM / heap exhaustion in batch job |
| `crashloop-db-config.log` | `incident-crashloop-db-config.yaml` | Invalid DATABASE_URL, CrashLoopBackOff |
| `db-connection-cascade.log` | `incident-db-connection-cascade.yaml` | Postgres connection refused, 503 cascade |
| `prompt-injection.log` | `incident-prompt-injection.yaml` | NPE + adversarial text in logs |
| `trace-latency-spike.log` | `incident-trace-latency-spike.yaml` | Slow `postgres.query` span in APM traces |
| `routine-health-polls.log` | `incident-routine-health-polls.yaml` | All noise — benign probe traffic |

Lines starting with `#` are stripped before chunking. `[SIGNAL]` comments are for humans only.

## Quick test

```bash
source .venv/bin/activate

# Default: OOM sample
python scripts/test_sample_log.py

# Other samples
python scripts/test_sample_log.py --log samples/crashloop-db-config.log --incident samples/incident-crashloop-db-config.yaml
python scripts/test_sample_log.py --log samples/db-connection-cascade.log --incident samples/incident-db-connection-cascade.yaml
python scripts/test_sample_log.py --log samples/prompt-injection.log --incident samples/incident-prompt-injection.yaml
python scripts/test_sample_log.py --log samples/trace-latency-spike.log --incident samples/incident-trace-latency-spike.yaml
python scripts/test_sample_log.py --log samples/routine-health-polls.log --incident samples/incident-routine-health-polls.yaml

# Live Jev + LLM diagnosis
JEV_MODE=live python scripts/test_sample_log.py --log samples/db-connection-cascade.log --incident samples/incident-db-connection-cascade.yaml --diagnose
```

## List all samples

```bash
python scripts/test_sample_log.py --list
```

Chunks are split on blank lines. For fixed-size chunks used in the benchmark harness, see `scenarios/`.
