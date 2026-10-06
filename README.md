# GASP: governed agent societies

Code, experiments and paper draft for the SEAMS 2027 submission (deadline Friday 23 October 2026, AoE). A society of
LLM-driven roles handles city incidents under rules; a runtime guard enforces the rules, a human answers approval
requests, and every proposal leaves a trace. The paper compares rules in prompts with rules enforced by the guard.

Status: code, tests and the draft (`paper/main.pdf`, 8 pages) are done. Only the model runs are missing, and they need
an OpenAI key. The red marks in the draft are the places that wait for them.

## Your part: three commands, one person

```bash
pip install -r requirements.txt && python -m pytest tests -q     # expect: 45 passed
export OPENAI_API_KEY=sk-...                                      # your key, never committed
bash scripts/run_pilot.sh                                         # under an hour, a few USD
```

Send back `outputs/llm_pilot/PILOT_REPORT.md` and `outputs/llm_pilot.zip`. When the pilot is cleared:

```bash
bash scripts/run_main_grid.sh                                     # a few hours, about 120 USD in total
```

Send back `outputs/llm_results.zip` and `outputs/llm_traces.zip`. Nothing runs on your machine but a Python script
that calls the API; no GPU.

Optional, if the lab GPU is free: `bash scripts/serve_local_model.sh` on the GPU server (vLLM), then
`bash scripts/run_local_ablation.sh`. Adds an open-weight 30B model as a third model; no key, no cost, a few hours.

## What to check in the pilot table

- Guard on (M3, M4): `executed_violations` and `false_alert` are 0.00. Anything else is a bug; tell me.
- `formatting_failures` under 1 per incident and `success` in M2 above 0.3. Otherwise tell me before the main grid.

Everything else in the table is a result, not a problem. `docs/RESULTS_GUIDE.md` explains every column and what we expect.

## Where things are

| | |
|---|---|
| `RUNBOOK.md` | every command with its options, the GPU variant, what to do when something breaks |
| `docs/RESULTS_GUIDE.md` | what each number means, the health checks, the expected ranges, what each outcome means for the paper |
| `todo.md` | plan, status, open items, running log |
| `docs/BACKGROUND.md` | why SEAMS, what the ESEM reviews said, what the old code showed |
| `gasp/` | the code: `core/` (evidence, actions, guard, state, traces, metrics), `domains/` (smartcity, ops), `policies/` (procedural, naive, LLM, backends), `experiments/` (reproduce, run_grid, analyze, paper tables and figures, pilot report) |
| `configs/` | rule sets `rules/R1–R3.yaml`; LLM grids `llm_grid.yaml` (API models), `llm_grid_local.yaml` (vLLM), `llm_grid_dryrun.yaml` (no model) |
| `scripts/`, `notebooks/` | the run scripts above and a Colab notebook for the pilot |
| `paper/` | the IEEE draft; `make` rebuilds tables and figures from `outputs/` and the PDF |
| `outputs/paper*/`, `outputs/llm_pilot_example/` | generated deterministic tables (`python -m gasp.experiments.reproduce --out outputs/paper`, 8 seconds) and an example pilot report from a run without a model |
| `legacy/` | the ESEM 2026 prototype, reference only |

Modes, in every table: M0 one agent with all tools and the rules in its prompt; M1 roles, no rules anywhere; M2 roles,
rules in prompts; M3 roles, guard, no rules in prompts; M4 rules in prompts and guard. D0–D6 are the deterministic
mirrors with a naive brain (ignores the rules) and a procedural brain (follows them).
