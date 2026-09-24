# Runbook: the LLM experiments

Everything below runs without changing code. Budget, commands, what to check, and what to hand back.

## 1. Setup (10 minutes)

```bash
git checkout seams2027
python -m pip install -r requirements.txt
python -m pip install anthropic            # only for the Anthropic backend
python -m pytest tests -q                  # expect: 36 passed
python -m gasp.experiments.reproduce --out outputs/paper   # 8 s; writes outputs/paper/scenarios.json (the shared scenario set)
```

Edit `configs/llm_grid.yaml`:

- `models[].name`: a short label that will appear in tables (e.g. `sonnet`, `qwen7b`).
- `models[].kind`: `anthropic` (needs `ANTHROPIC_API_KEY`) or `openai` (any OpenAI-compatible endpoint: OpenAI, OpenRouter, vLLM, Ollama with `/v1`).
- `models[].model`: the exact model identifier the API expects.
- `models[].base_url` and `api_key_env` for `openai` kinds. For a local vLLM server: `http://<host>:8000/v1`, any key.
- Leave `temperature: 0.7`, `repeats: 5`, `max_steps: 16`, `rule_set: R2`.

## 2. Estimate before spending (no API calls)

```bash
python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_estimate \
    --scenarios outputs/paper/scenarios.json --estimate --repeats 1
```

Prints calls and tokens for one repeat of the five modes with a perfectly compliant policy (measured: about 4,100 calls and 5.5M tokens for 400 episodes). Plan for 1.5x with a real model, times 5 repeats: roughly 30k calls and 40M tokens per model for the main grid. At typical frontier prices that is in the order of 150–200 USD per frontier model; a local model costs GPU time only.

## 3. Pilot (30–60 minutes, a few USD)

```bash
python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_pilot \
    --scenarios outputs/paper/scenarios.json --limit 2 --repeats 1
```

Eight scenarios (two per family), five modes, one repeat, every model in the config. Look at `outputs/llm_pilot/table_llm.md`:

- `formatting_failures` should be well below 1 per episode. Higher means the model does not follow the JSON schema; tell us which model.
- `success` in M2 (rules in prompt, no guard) should be above 0.3. Near zero means the model cannot operate the testbed at all and we need to look at traces before spending more.
- `executed_violations` must be 0.00 in M3 and M4 (guard on). Anything else is a bug: send the traces.
- `hallucinated_refs` above 0.2 is worth a look but not a blocker; it is one of our findings.

Also check `outputs/llm_pilot/traces/*.jsonl` for two or three episodes: does the rationale field make sense?

## 4. Main grid (hours; resumable)

Run modes in parallel processes, one output directory per mode, so nothing is written to the same file twice:

```bash
for m in M0 M1 M2 M3 M4; do
  nohup python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm/$m \
      --scenarios outputs/paper/scenarios.json --modes $m --repeats 5 > outputs/llm_$m.log 2>&1 &
done
```

Each process appends one line per finished episode to `episodes.jsonl` and can be stopped and restarted at any time; finished episodes are skipped. Sequential speed is about 3 s per call, so one mode for one model takes 4–5 hours; five processes bring the whole grid to about that.

Sensitivity (small model only, M2 and M3, one repeat is enough):

```bash
for rs in R1 R3; do
  python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_sens/$rs \
      --scenarios outputs/paper/scenarios.json --modes M2,M3 --models <small-model-name> --repeats 1 --rule-set $rs --tag $rs
done
for ov in always never; do
  python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_sens/ov_$ov \
      --scenarios outputs/paper/scenarios.json --modes M2,M3 --models <small-model-name> --repeats 1 --overseer $ov --tag ov-$ov
done
```

## 5. Statistics

```bash
python -m gasp.experiments.analyze --episodes "outputs/llm/*/episodes.csv" --out outputs/llm/stats \
    --pairs M2:M3,M0:M3,M3:M4,M1:M2 --group model
python -m gasp.experiments.analyze --episodes "outputs/llm_sens/*/episodes.csv" --out outputs/llm_sens/stats \
    --pairs M2:M3 --group tag
```

## 6. What to hand back

Small files (a few MB), by mail or in the repo:

- `outputs/llm/*/episodes.csv`, `outputs/llm/*/manifest.json`, `outputs/llm/*/table_llm.md`
- `outputs/llm/stats/paired_stats.md` and `.json`
- `outputs/llm_sens/**` (same files)
- the pilot directory as a whole

Large: `outputs/llm/*/traces/` (zip it; a few hundred MB). Needed for the worked example, the failure catalogue and the hallucinated-reference examples.

## 7. If something goes wrong

- 429 or 5xx from the API: the backend retries five times with backoff; if a run dies, restart the same command.
- A model never returns valid JSON: lower `temperature` to 0.3 in the config for that model and rerun the pilot; if it still fails, replace the model.
- Very long episodes (always 16 steps): look at `last_guard` in the traces; if the model keeps repeating a blocked action, that is a result (report it), not a bug.
