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
trap 'kill 0' INT TERM      # Ctrl-c stops the run and its processes; started again, it continues where it was
# Which model: a config file with one local model entry. The servers are found by the served model name, so several
# models can be served at once on different ports and each config picks its own.
#   CONFIG=configs/llm_grid_local_qwen4b.yaml bash scripts/run_local_ablation.sh pilot
CONFIG=${CONFIG:-configs/llm_grid_local.yaml}
read -r NAME MODEL_ID CONFIG_MODES DOMAIN < <(python - "$CONFIG" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])); m = c["models"][0]
print(m["name"], m["model"], ",".join(c.get("modes", ["M2", "M3", "M4"])), c.get("domain", "smartcity"))
PY
)
PREFIX=${PREFIX:-$([[ "$NAME" == "glimmer" ]] && echo local || echo "$NAME")}   # output directories: outputs/llm/<PREFIX>_<mode>_s<k>
# The second domain (domain: ops in the config) keeps its own scenario set and output root, so its rows never mix with the city's.
if [[ "$DOMAIN" == "ops" ]]; then OUT=outputs/llm_ops; SENS_OUT=outputs/llm_ops_sens; PAPER=outputs/paper_ops; else OUT=outputs/llm; SENS_OUT=outputs/llm_sens; PAPER=outputs/paper; fi
SCEN=$PAPER/scenarios.json
DOMAIN_SUFFIX=$([[ "$DOMAIN" == "ops" ]] && echo _ops || echo "")
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
python -m gasp.experiments.reproduce --domain "$DOMAIN" --out "$PAPER" --no-traces --skip-ablation > /dev/null
backup() {   # $1 = name, $2... = paths; a copy outside the project folder, which no PyCharm sync can touch
  mkdir -p ~/gasp_backups
  local f=~/gasp_backups/$1_$(date +%Y%m%d_%H%M).tgz
  tar czf "$f" "${@:2}" && echo "Backup: $f ($(du -h "$f" | cut -f1))"
}
wait_with_progress() {   # $1 = total episodes, $2... = globs of run directories; redraws every 20 s while jobs run
  local total=$1; shift
  python -m gasp.experiments.progress --runs "$@" --total "$total" --watch 20 &
  local mon=$!
  while [[ -n "$(jobs -rp | grep -v "^$mon$")" ]]; do sleep 5; done
  kill "$mon" 2>/dev/null || true; wait "$mon" 2>/dev/null || true; echo   # (a killed monitor must not stop the script)
  python -m gasp.experiments.progress --runs "$@" --total "$total"
}
if [[ "${1:-full}" == "pilot" ]]; then
  # one process per mode, each on its own server when there are several; merged into one directory for the report
  j=0
  for m in ${MODES:-${CONFIG_MODES//,/ }}; do       # the config's modes (a control config may have only M2)
    python -m gasp.experiments.run_grid --config "$CONFIG" --out outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}/$m \
        --scenarios "$SCEN" --limit 2 --repeats 1 --modes $m --base-url "${SERVERS[$((j % N))]}" \
        > outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}_$m.log 2>&1 &
    j=$((j + 1))
  done
  echo "$j pilot processes started (logs: outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}_M*.log); 30-60 minutes at reasoning level high."
  wait_with_progress $((8 * j)) "outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}/M*"
  python -m gasp.experiments.merge_runs --runs "outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}/M*" --out outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}
  python -m gasp.experiments.analyze --episodes outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}/episodes.csv --out outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}/stats \
      --pairs M2:M3,M3:M4 --group model > /dev/null
  python -m gasp.experiments.pilot_report --pilot outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX} --who "${PILOT_WHO:-<your name>}" \
      --machine "${PILOT_MACHINE:-gpu server, vLLM, $N GPU(s)}" --cost-usd 0
  zip -q -r outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}.zip outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}
  echo "Done. Check outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}/table_llm.md (formatting_failures under 1, success in M2 above 0.3) and send outputs/llm_local_pilot_${NAME}${DOMAIN_SUFFIX}.zip."
elif [[ "${1:-full}" == "sens" ]]; then
  # Sensitivity on the same model, one repeat: rule sets R1 and R3, and the human always or never available; M2 and M3.
  # 4 sweeps x 2 modes x 80 scenarios = 640 episodes. Results in outputs/llm_sens/local_<tag>_<mode>_s<k>.
  SHARDS=${SHARDS:-$((2 * N))}
  j=0
  for sweep in "R1:--rule-set R1" "R3:--rule-set R3" "ov-always:--overseer always" "ov-never:--overseer never"; do
    tag=${sweep%%:*}; opt=${sweep#*:}
    for m in M2 M3; do
      for ((k = 0; k < SHARDS; k++)); do
        python -m gasp.experiments.run_grid --config "$CONFIG" --out ${SENS_OUT}/${PREFIX}_${tag}_${m}_s$k \
            --scenarios "$SCEN" --modes $m --repeats 1 --shard $k/$SHARDS $opt --tag $tag \
            --base-url "${SERVERS[$((j % N))]}" > ${SENS_OUT}_${PREFIX}_${tag}_${m}_s$k.log 2>&1 &
        j=$((j + 1))
      done
    done
  done
  echo "$j processes started over $N server(s); logs in ${SENS_OUT}_${PREFIX}_*.log."
  wait_with_progress 640 "${SENS_OUT}/${PREFIX}_*"
  python -m gasp.experiments.analyze --episodes "${SENS_OUT}/${PREFIX}_*/episodes.csv" --out ${SENS_OUT}/${PREFIX}_stats \
      --pairs M2:M3 --group tag
  backup "${PREFIX}_sens" ${SENS_OUT}/${PREFIX}_*
  echo "Done. Results in ${SENS_OUT}/; on the PC: python scripts/fetch_outputs.py user@gpu-server"
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
      python -m gasp.experiments.run_grid --config "$CONFIG" --out ${OUT}/${PREFIX}_${m}_s$k \
          --scenarios "$SCEN" --modes $m --repeats $REPEATS --shard $k/$SHARDS \
          --base-url "${SERVERS[$((j % N))]}" > ${OUT}_${PREFIX}_${m}_s$k.log 2>&1 &
      j=$((j + 1))
    done
  done
  echo "$j processes started over $N server(s) for modes $MODES; logs in ${OUT}_${PREFIX}_*.log."
  globs=(); for m in $MODES; do globs+=("${OUT}/${PREFIX}_${m}_*"); done
  wait_with_progress "$total" "${globs[@]}"
  python -m gasp.experiments.analyze --episodes "${OUT}/${PREFIX}_*/episodes.csv" --out ${OUT}_${PREFIX}_stats \
      --pairs M2:M3,M3:M4,M2:M4,M0:M3,M1:M2 --group model
  backup "${PREFIX}_$(echo $MODES | tr -d ' ')" ${OUT}/${PREFIX}_* ${OUT}_${PREFIX}_stats
  echo "Done. Results in ${OUT}/${PREFIX}_*; on the PC: python scripts/fetch_outputs.py user@gpu-server"
fi
