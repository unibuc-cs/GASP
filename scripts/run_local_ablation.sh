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
# Which model: a config file with one local model entry. The servers are found by the served model name, so several
# models can be served at once on different ports and each config picks its own.
#   CONFIG=configs/llm_grid_local_qwen4b.yaml bash scripts/run_local_ablation.sh pilot
CONFIG=${CONFIG:-configs/llm_grid_local.yaml}
read -r NAME MODEL_ID CONFIG_MODES < <(python - "$CONFIG" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])); m = c["models"][0]
print(m["name"], m["model"], ",".join(c.get("modes", ["M2", "M3", "M4"])))
PY
)
PREFIX=${PREFIX:-$([[ "$NAME" == "glimmer" ]] && echo local || echo "$NAME")}   # output directories: outputs/llm/<PREFIX>_<mode>_s<k>
SERVERS=()
if [[ -n "${LOCAL_BASE_URL:-}" ]]; then
  SERVERS=("$LOCAL_BASE_URL")
else
  for ((port = 8000; port < 8032; port++)); do
    ids=$(curl -sf "http://localhost:$port/v1/models" 2>/dev/null | python -c "import sys,json; print(' '.join(m['id'] for m in json.load(sys.stdin).get('data', [])))" 2>/dev/null || true)
    for id in $ids; do [[ "$id" == "$MODEL_ID" ]] && SERVERS+=("http://localhost:$port/v1"); done
  done
fi
N=${#SERVERS[@]}
if (( N == 0 )); then echo "No server serving '$MODEL_ID' answers on ports 8000-8031. Start scripts/serve_local_model.sh with NAME=$MODEL_ID (or set LOCAL_BASE_URL) first."; exit 1; fi
echo "Model $NAME ($MODEL_ID): using $N server(s): ${SERVERS[*]}"
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
    python -m gasp.experiments.run_grid --config "$CONFIG" --out outputs/llm_local_pilot_$NAME/$m \
        --scenarios outputs/paper/scenarios.json --limit 2 --repeats 1 --modes $m --base-url "${SERVERS[$((j % N))]}" \
        > outputs/llm_local_pilot_${NAME}_$m.log 2>&1 &
    j=$((j + 1))
  done
  echo "3 pilot processes started (logs: outputs/llm_local_pilot_${NAME}_M*.log); 30-60 minutes at reasoning level high."
  wait_with_progress 24 "outputs/llm_local_pilot_$NAME/M*"
  python -m gasp.experiments.merge_runs --runs "outputs/llm_local_pilot_$NAME/M*" --out outputs/llm_local_pilot_$NAME
  python -m gasp.experiments.analyze --episodes outputs/llm_local_pilot_$NAME/episodes.csv --out outputs/llm_local_pilot_$NAME/stats \
      --pairs M2:M3,M3:M4 --group model > /dev/null
  python -m gasp.experiments.pilot_report --pilot outputs/llm_local_pilot_$NAME --who "${PILOT_WHO:-<your name>}" \
      --machine "${PILOT_MACHINE:-gpu server, vLLM, $N GPU(s)}" --cost-usd 0
  zip -q -r outputs/llm_local_pilot_$NAME.zip outputs/llm_local_pilot_$NAME
  echo "Done. Check outputs/llm_local_pilot_$NAME/table_llm.md (formatting_failures under 1, success in M2 above 0.3) and send outputs/llm_local_pilot_$NAME.zip."
elif [[ "${1:-full}" == "sens" ]]; then
  # Sensitivity on the same model, one repeat: rule sets R1 and R3, and the human always or never available; M2 and M3.
  # 4 sweeps x 2 modes x 80 scenarios = 640 episodes. Results in outputs/llm_sens/local_<tag>_<mode>_s<k>.
  SHARDS=${SHARDS:-$((2 * N))}
  j=0
  for sweep in "R1:--rule-set R1" "R3:--rule-set R3" "ov-always:--overseer always" "ov-never:--overseer never"; do
    tag=${sweep%%:*}; opt=${sweep#*:}
    for m in M2 M3; do
      for ((k = 0; k < SHARDS; k++)); do
        python -m gasp.experiments.run_grid --config "$CONFIG" --out outputs/llm_sens/${PREFIX}_${tag}_${m}_s$k \
            --scenarios outputs/paper/scenarios.json --modes $m --repeats 1 --shard $k/$SHARDS $opt --tag $tag \
            --base-url "${SERVERS[$((j % N))]}" > outputs/llm_sens_${PREFIX}_${tag}_${m}_s$k.log 2>&1 &
        j=$((j + 1))
      done
    done
  done
  echo "$j processes started over $N server(s); logs in outputs/llm_sens_local_*.log."
  wait_with_progress 640 "outputs/llm_sens/${PREFIX}_*"
  python -m gasp.experiments.analyze --episodes "outputs/llm_sens/local_*/episodes.csv" --out outputs/llm_sens/stats \
      --pairs M2:M3 --group tag
  echo "Done. Results in outputs/llm_sens/ (the folder sync brings them over)."
else
  # MODES x SHARDS processes at once, dealt round-robin over the servers; each vLLM server batches the requests
  # it receives. Default: 4 shards per server, so about 12 concurrent requests per GPU.
  #   bash scripts/run_local_ablation.sh                      # the config's modes (Glimmer: M2 M3 M4), 3 repeats
  #   MODES="M0 M1" bash scripts/run_local_ablation.sh        # a chosen subset, for instance the two remaining modes
  MODES=${MODES:-${CONFIG_MODES//,/ }}     # default: the config's mode list
  REPEATS=${REPEATS:-3}
  SHARDS=${SHARDS:-$((4 * N))}
  nmodes=$(echo $MODES | wc -w); total=$((80 * REPEATS * nmodes))
  j=0
  for m in $MODES; do
    for ((k = 0; k < SHARDS; k++)); do
      python -m gasp.experiments.run_grid --config "$CONFIG" --out outputs/llm/${PREFIX}_${m}_s$k \
          --scenarios outputs/paper/scenarios.json --modes $m --repeats $REPEATS --shard $k/$SHARDS \
          --base-url "${SERVERS[$((j % N))]}" > outputs/llm_${PREFIX}_${m}_s$k.log 2>&1 &
      j=$((j + 1))
    done
  done
  echo "$j processes started over $N server(s) for modes $MODES; logs in outputs/llm_local_*.log."
  globs=(); for m in $MODES; do globs+=("outputs/llm/${PREFIX}_${m}_*"); done
  wait_with_progress "$total" "${globs[@]}"
  python -m gasp.experiments.analyze --episodes "outputs/llm/${PREFIX}_*/episodes.csv" --out outputs/llm_${PREFIX}_stats \
      --pairs M2:M3,M3:M4,M2:M4,M0:M3,M1:M2 --group model
  echo "Done. Results in outputs/llm/${PREFIX}_* and outputs/llm_${PREFIX}_stats (the folder sync brings them over)."
fi
