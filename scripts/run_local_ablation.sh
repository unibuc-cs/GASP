#!/usr/bin/env bash
# The open-weight model (Glimmer 30B on a local vLLM server) on the same scenarios: M2, M3, M4, three repeats.
# No API key, no cost; time is set by the GPU. Run on the GPU machine itself (same tmux session as the server,
# second window) or on any machine with an ssh tunnel to it (see scripts/serve_local_model.sh).
#   bash scripts/run_local_ablation.sh pilot   # 8 scenarios, one repeat: 10-30 minutes; check the table first
#   bash scripts/run_local_ablation.sh         # full: 720 episodes, resumable (rerun to continue)
# Results land in outputs/llm/local_M2, local_M3, local_M4 so the paper build picks them up with the API results.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE=${LOCAL_BASE_URL:-http://localhost:8000/v1}
curl -sf "$BASE/models" > /dev/null || { echo "No server answers at $BASE. Start scripts/serve_local_model.sh (or the ssh tunnel) first."; exit 1; }
python -m gasp.experiments.reproduce --out outputs/paper --no-traces --skip-ablation > /dev/null
if [[ "${1:-full}" == "pilot" ]]; then
  python -m gasp.experiments.run_grid --config configs/llm_grid_local.yaml --out outputs/llm_local_pilot \
      --scenarios outputs/paper/scenarios.json --limit 2 --repeats 1
  python -m gasp.experiments.analyze --episodes outputs/llm_local_pilot/episodes.csv --out outputs/llm_local_pilot/stats \
      --pairs M2:M3,M3:M4 --group model > /dev/null
  python -m gasp.experiments.pilot_report --pilot outputs/llm_local_pilot --who "${PILOT_WHO:-<your name>}" \
      --machine "${PILOT_MACHINE:-gpu server, vLLM}" --cost-usd 0
  zip -q -r outputs/llm_local_pilot.zip outputs/llm_local_pilot
  echo "Done. Check outputs/llm_local_pilot/table_llm.md (formatting_failures under 1, success in M2 above 0.3) and send outputs/llm_local_pilot.zip."
else
  # 3 modes x SHARDS processes run at once; vLLM batches their requests, so more processes mean a shorter night.
  # 4 shards (12 processes) suit an 80 GB card; use SHARDS=2 on a 24 GB card.
  SHARDS=${SHARDS:-4}
  for m in M2 M3 M4; do
    for ((k = 0; k < SHARDS; k++)); do
      python -m gasp.experiments.run_grid --config configs/llm_grid_local.yaml --out outputs/llm/local_${m}_s$k \
          --scenarios outputs/paper/scenarios.json --modes $m --repeats 3 --shard $k/$SHARDS > outputs/llm_local_${m}_s$k.log 2>&1 &
    done
  done
  wait
  python -m gasp.experiments.analyze --episodes "outputs/llm/local_*/episodes.csv" --out outputs/llm_local_stats \
      --pairs M2:M3,M3:M4 --group model
  zip -q -r outputs/llm_local.zip outputs/llm/local_* outputs/llm_local_stats --exclude "outputs/llm/local_*/traces/*"
  zip -q -r outputs/llm_local_traces.zip outputs/llm/local_*/traces
  echo "Done. Send outputs/llm_local.zip (small) and outputs/llm_local_traces.zip (large) back."
fi
