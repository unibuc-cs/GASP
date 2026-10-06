#!/usr/bin/env bash
# Pilot of the LLM experiments: eight scenarios, five modes, both models, one repeat. A few USD, under an hour.
# Needs: Python 3.10+, internet, and OPENAI_API_KEY set in the environment. Run from the repository root:
#   export OPENAI_API_KEY=sk-...        (never commit it)
#   bash scripts/run_pilot.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -q -r requirements.txt
python -m pytest tests -q
python -m gasp.experiments.reproduce --out outputs/paper --no-traces --skip-ablation > /dev/null
echo "== estimate (no API calls) =="
python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_estimate \
    --scenarios outputs/paper/scenarios.json --estimate --repeats 1 | tail -2
echo "== pilot =="
python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_pilot \
    --scenarios outputs/paper/scenarios.json --limit 2 --repeats 1
python -m gasp.experiments.analyze --episodes outputs/llm_pilot/episodes.csv --out outputs/llm_pilot/stats \
    --pairs M2:M3,M0:M3,M3:M4 --group model > /dev/null
python -m gasp.experiments.pilot_report --pilot outputs/llm_pilot --who "${PILOT_WHO:-<your name>}" --machine "${PILOT_MACHINE:-laptop}"
zip -q -r outputs/llm_pilot.zip outputs/llm_pilot
echo "Done. Fill the remaining fields in outputs/llm_pilot/PILOT_REPORT.md (wall time, cost, impressions) and send it with outputs/llm_pilot.zip."
