# Start here (one page)

Paper for SEAMS 2027, deadline 23 October. Code, tests and draft are done. Only the model runs are missing, and they need your OpenAI key.

## Your part: three commands, one person

```bash
export OPENAI_API_KEY=sk-...          # your key, never committed
bash scripts/run_pilot.sh             # under an hour, a few USD
```

Send back `outputs/llm_pilot/PILOT_REPORT.md` and `outputs/llm_pilot.zip`. When I say go:

```bash
bash scripts/run_main_grid.sh         # a few hours, about 120 USD in total
```

Send back `outputs/llm_results.zip` and `outputs/llm_traces.zip`. Nothing runs locally, no GPU, nothing to install beyond Python.

## What to check in the pilot table

- Guard on (M3, M4): `executed_violations` and `false_alert` are 0.00. Anything else is a bug; tell me.
- `formatting_failures` under 1 per incident; `success` in M2 above 0.3. Otherwise tell me before the main grid.

Everything else in the table is a result, not a problem.

## If you want more

- `todo.md`: the plan and its status.
- `RUNBOOK.md`: the same commands with options and what to do when something breaks.
- `docs/READING_THE_PILOT_REPORT.md`: every number explained.
- `docs/TARGET_RESULTS.md`: what we expect and how the paper reads under each outcome.
