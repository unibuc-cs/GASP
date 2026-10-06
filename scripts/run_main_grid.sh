#!/usr/bin/env bash
# Main grid: 80 scenarios, five modes, both models, five repeats; modes run in parallel; resumable (rerun to continue).
# About 30k calls and 40M tokens per model: roughly 110 USD for GPT-6 Sol and 6 USD for GPT-6 Luna at list prices.
#   export OPENAI_API_KEY=sk-...
#   bash scripts/run_main_grid.sh            # main grid, both models
#   bash scripts/run_main_grid.sh sens       # sensitivity sweeps on Luna (R1, R3, overseer always/never), one repeat
set -euo pipefail
cd "$(dirname "$0")/.."
python -m gasp.experiments.reproduce --out outputs/paper --no-traces --skip-ablation > /dev/null
if [[ "${1:-main}" == "main" ]]; then
  for m in M0 M1 M2 M3 M4; do
    python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm/$m \
        --scenarios outputs/paper/scenarios.json --modes $m --repeats 5 > outputs/llm_$m.log 2>&1 &
  done
  wait
  python -m gasp.experiments.analyze --episodes "outputs/llm/*/episodes.csv" --out outputs/llm/stats \
      --pairs M2:M3,M0:M3,M3:M4,M1:M2 --group model
  zip -q -r outputs/llm_results.zip outputs/llm --exclude "outputs/llm/*/traces/*"
  zip -q -r outputs/llm_traces.zip outputs/llm/*/traces
  echo "Done. Send outputs/llm_results.zip (small) and outputs/llm_traces.zip (large) back."
else
  for rs in R1 R3; do
    python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_sens/$rs \
        --scenarios outputs/paper/scenarios.json --modes M2,M3 --models luna --repeats 1 --rule-set $rs --tag $rs &
  done
  for ov in always never; do
    python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm_sens/ov_$ov \
        --scenarios outputs/paper/scenarios.json --modes M2,M3 --models luna --repeats 1 --overseer $ov --tag ov-$ov &
  done
  wait
  python -m gasp.experiments.analyze --episodes "outputs/llm_sens/*/episodes.csv" --out outputs/llm_sens/stats \
      --pairs M2:M3 --group tag
  zip -q -r outputs/llm_sens.zip outputs/llm_sens --exclude "outputs/llm_sens/*/traces/*"
  echo "Done. Send outputs/llm_sens.zip back."
fi
