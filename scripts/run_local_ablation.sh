#!/usr/bin/env bash
# The open-weight model (Glimmer 30B on local vLLM servers) on the same scenarios: M2, M3, M4, three repeats.
# No API key, no cost; time is set by the GPUs. Run on the GPU machine (second tmux window, next to the servers)
# or on any machine with an ssh tunnel to one server (LOCAL_BASE_URL=http://localhost:8000/v1).
#   bash scripts/run_local_ablation.sh pilot   # 8 scenarios, one repeat: 10-30 minutes; check the table first
#   bash scripts/run_local_ablation.sh         # full: 720 episodes, resumable (rerun to continue)
# Servers are found on ports 8000, 8001, ... (one per GPU, started by scripts/serve_local_model.sh); the work is
# split into shards and the shards spread over the servers, so every GPU is busy. Results land in
# outputs/llm/local_* so the paper build picks them up with the API results.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT=${PORT:-8000}
SERVERS=()
if [[ -n "${LOCAL_BASE_URL:-}" ]]; then
  SERVERS=("$LOCAL_BASE_URL")
else
  for ((i = 0; i < 16; i++)); do
    curl -sf "http://localhost:$((PORT + i))/v1/models" > /dev/null 2>&1 && SERVERS+=("http://localhost:$((PORT + i))/v1")
  done
fi
N=${#SERVERS[@]}
if (( N == 0 )); then echo "No server answers on ports $PORT... Start scripts/serve_local_model.sh (or set LOCAL_BASE_URL) first."; exit 1; fi
echo "Using $N server(s): ${SERVERS[*]}"
python -m gasp.experiments.reproduce --out outputs/paper --no-traces --skip-ablation > /dev/null
wait_with_progress() {   # $1 = total episodes, $2... = globs of run directories; redraws every 20 s while jobs run
  local total=$1; shift
  python -m gasp.experiments.progress --runs "$@" --total "$total" --watch 20 &
  local mon=$!
  while [[ -n "$(jobs -rp | grep -v "^$mon$")" ]]; do sleep 5; done
  kill "$mon" 2>/dev/null; wait "$mon" 2>/dev/null; echo
  python -m gasp.experiments.progress --runs "$@" --total "$total"
}
if [[ "${1:-full}" == "pilot" ]]; then
  # one process per mode, each on its own server when there are several; merged into one directory for the report
  j=0
  for m in M2 M3 M4; do
    python -m gasp.experiments.run_grid --config configs/llm_grid_local.yaml --out outputs/llm_local_pilot/$m \
        --scenarios outputs/paper/scenarios.json --limit 2 --repeats 1 --modes $m --base-url "${SERVERS[$((j % N))]}" \
        > outputs/llm_local_pilot_$m.log 2>&1 &
    j=$((j + 1))
  done
  echo "3 pilot processes started (logs: outputs/llm_local_pilot_M*.log); 30-60 minutes at reasoning level high."
  wait_with_progress 24 "outputs/llm_local_pilot/M*"
  python -m gasp.experiments.merge_runs --runs "outputs/llm_local_pilot/M*" --out outputs/llm_local_pilot
  python -m gasp.experiments.analyze --episodes outputs/llm_local_pilot/episodes.csv --out outputs/llm_local_pilot/stats \
      --pairs M2:M3,M3:M4 --group model > /dev/null
  python -m gasp.experiments.pilot_report --pilot outputs/llm_local_pilot --who "${PILOT_WHO:-<your name>}" \
      --machine "${PILOT_MACHINE:-gpu server, vLLM, $N GPU(s)}" --cost-usd 0
  zip -q -r outputs/llm_local_pilot.zip outputs/llm_local_pilot
  echo "Done. Check outputs/llm_local_pilot/table_llm.md (formatting_failures under 1, success in M2 above 0.3) and send outputs/llm_local_pilot.zip."
elif [[ "${1:-full}" == "sens" ]]; then
  # Sensitivity on the same model, one repeat: rule sets R1 and R3, and the human always or never available; M2 and M3.
  # 4 sweeps x 2 modes x 80 scenarios = 640 episodes. Results in outputs/llm_sens/local_<tag>_<mode>_s<k>.
  SHARDS=${SHARDS:-$((2 * N))}
  j=0
  for sweep in "R1:--rule-set R1" "R3:--rule-set R3" "ov-always:--overseer always" "ov-never:--overseer never"; do
    tag=${sweep%%:*}; opt=${sweep#*:}
    for m in M2 M3; do
      for ((k = 0; k < SHARDS; k++)); do
        python -m gasp.experiments.run_grid --config configs/llm_grid_local.yaml --out outputs/llm_sens/local_${tag}_${m}_s$k \
            --scenarios outputs/paper/scenarios.json --modes $m --repeats 1 --shard $k/$SHARDS $opt --tag $tag \
            --base-url "${SERVERS[$((j % N))]}" > outputs/llm_sens_local_${tag}_${m}_s$k.log 2>&1 &
        j=$((j + 1))
      done
    done
  done
  echo "$j processes started over $N server(s); logs in outputs/llm_sens_local_*.log."
  wait_with_progress 640 "outputs/llm_sens/local_*"
  python -m gasp.experiments.analyze --episodes "outputs/llm_sens/local_*/episodes.csv" --out outputs/llm_sens/stats \
      --pairs M2:M3 --group tag
  echo "Done. Results in outputs/llm_sens/ (the folder sync brings them over)."
else
  # MODES x SHARDS processes at once, dealt round-robin over the servers; each vLLM server batches the requests
  # it receives. Default: 4 shards per server, so about 12 concurrent requests per GPU.
  #   bash scripts/run_local_ablation.sh                      # M2 M3 M4 (the primary comparison), 3 repeats, 720 episodes
  #   MODES="M0 M1" bash scripts/run_local_ablation.sh        # the two remaining modes afterwards, 480 episodes
  MODES=${MODES:-"M2 M3 M4"}
  REPEATS=${REPEATS:-3}
  SHARDS=${SHARDS:-$((4 * N))}
  nmodes=$(echo $MODES | wc -w); total=$((80 * REPEATS * nmodes))
  j=0
  for m in $MODES; do
    for ((k = 0; k < SHARDS; k++)); do
      python -m gasp.experiments.run_grid --config configs/llm_grid_local.yaml --out outputs/llm/local_${m}_s$k \
          --scenarios outputs/paper/scenarios.json --modes $m --repeats $REPEATS --shard $k/$SHARDS \
          --base-url "${SERVERS[$((j % N))]}" > outputs/llm_local_${m}_s$k.log 2>&1 &
      j=$((j + 1))
    done
  done
  echo "$j processes started over $N server(s) for modes $MODES; logs in outputs/llm_local_*.log."
  globs=(); for m in $MODES; do globs+=("outputs/llm/local_${m}_*"); done
  wait_with_progress "$total" "${globs[@]}"
  python -m gasp.experiments.analyze --episodes "outputs/llm/local_*/episodes.csv" --out outputs/llm_local_stats \
      --pairs M2:M3,M3:M4,M2:M4,M0:M3,M1:M2 --group model
  echo "Done. Results in outputs/llm/local_* and outputs/llm_local_stats (the folder sync brings them over)."
fi
