#!/usr/bin/env bash
# Serve an open-weight model with vLLM as OpenAI-compatible servers, one per GPU by default.
# Default model: meta-models/Muse-Glimmer-30B. (Muse-Glimmer-30B-assistant is NOT the model: it is the 5 GB
# speculative decoding drafter head, without a tokenizer, and vLLM cannot serve it on its own.)
#
# Run it over ssh inside tmux so the servers outlive the ssh session:
#   ssh user@gpu-server
#   tmux new -s vllm
#   source ~/muse-glimmer/.venv/bin/activate   # the uv environment on our server; elsewhere: pip install vllm
#   bash scripts/serve_local_model.sh          # then Ctrl-b d to detach
#
# Any model, any subset of GPUs, several models at once (one script per model, different GPU_IDS and PORT):
#   MODEL=Qwen/Qwen3.5-4B NAME=qwen4b GPU_IDS=2 PORT=8010 bash scripts/serve_local_model.sh
#   MODEL=Qwen/Qwen3.5-122B-A10B-FP8 NAME=qwen122b GPU_IDS=0,1 LAYOUT=tp PORT=8000 bash scripts/serve_local_model.sh
# Variables (all optional):
#   MODEL     Hugging Face id of the model                 NAME      served model name; the config's `model` field
#   GPU_IDS   comma list of GPU indices (default: all)     PORT      first port; dp layout uses PORT, PORT+1, ...
#   LAYOUT    dp: one server per GPU, full copy each (default); tp: one server, tensor parallel over GPU_IDS (head
#             count must be divisible by the GPU count); pp: one server, pipeline parallel over GPU_IDS (any model)
#   QUANT     fp8 | bitsandbytes | "" (bf16); default chosen from the first GPU's memory for a 30B model, so set it
#             for other sizes; a checkpoint that is already quantized (FP8, AWQ) needs nothing
#   REASONING_PARSER  vLLM parser that separates the model's reasoning from its answer; default by model family
#             (Glimmer: muse_glimmer, Qwen: qwen3, gpt-oss: openai_gptoss, otherwise none); "none" disables
#   MAX_LEN   context length (default 8192)                EXTRA_ARGS  anything else for vllm serve
# The first start downloads the weights from Hugging Face; set HF_HOME to a disk with room.
# Servers listen on 127.0.0.1 only. From another machine reach one through an ssh tunnel:
#   ssh -N -L 8000:localhost:8000 user@gpu-server
set -euo pipefail
MODEL=${MODEL:-meta-models/Muse-Glimmer-30B}
NAME=${NAME:-$(basename "$MODEL" | tr '[:upper:]' '[:lower:]' | sed 's/muse-glimmer-30b/glimmer/')}
PORT=${PORT:-8000}
LAYOUT=${LAYOUT:-dp}
MAX_LEN=${MAX_LEN:-8192}
NGPU=$(nvidia-smi -L 2>/dev/null | wc -l)
if [[ -z "${GPU_IDS:-}" ]]; then GPU_IDS=$(seq -s, 0 $((NGPU - 1))); fi
IFS=',' read -r -a GPU_LIST <<< "$GPU_IDS"
GPUS=${#GPU_LIST[@]}
if (( NGPU < 1 || GPUS < 1 )); then echo "no GPU found by nvidia-smi"; exit 1; fi
MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i "${GPU_LIST[0]}" | head -1 | tr -d ' ')
if [[ -z "${QUANT+x}" ]]; then        # QUANT not given: choose from GPU memory (MiB) for a 30B dense model
  if (( MEM >= 70000 )); then QUANT=""; elif (( MEM >= 38000 )); then QUANT=fp8; else QUANT=bitsandbytes; fi
fi
if [[ -z "${REASONING_PARSER:-}" ]]; then
  case "${MODEL,,}" in
    *glimmer*) REASONING_PARSER=muse_glimmer ;;
    *qwen*)    REASONING_PARSER=qwen3 ;;
    *gpt-oss*) REASONING_PARSER=openai_gptoss ;;
    *)         REASONING_PARSER=none ;;
  esac
fi
ARGS=(--served-model-name "$NAME" --host 127.0.0.1 --max-model-len "$MAX_LEN" --max-num-seqs 16 --gpu-memory-utilization 0.92)
if [[ "$REASONING_PARSER" != "none" ]]; then ARGS+=(--reasoning-parser "$REASONING_PARSER"); fi
if [[ -n "$QUANT" ]]; then ARGS+=(--quantization "$QUANT"); fi
if [[ -n "${EXTRA_ARGS:-}" ]]; then read -r -a EXTRA <<< "$EXTRA_ARGS"; ARGS+=("${EXTRA[@]}"); fi
echo "model $MODEL served as '$NAME'; GPUs $GPU_IDS ($GPUS of $NGPU); memory per GPU $MEM MiB; precision ${QUANT:-bf16}; layout $LAYOUT; reasoning parser $REASONING_PARSER"
trap 'kill 0' INT TERM
if [[ "$LAYOUT" == "tp" || "$LAYOUT" == "pp" ]]; then
  PAR=--tensor-parallel-size; [[ "$LAYOUT" == "pp" ]] && PAR=--pipeline-parallel-size
  echo "CUDA_VISIBLE_DEVICES=$GPU_IDS vllm serve $MODEL $PAR $GPUS --port $PORT ${ARGS[*]}   (log: vllm_$NAME.log)"
  CUDA_VISIBLE_DEVICES=$GPU_IDS vllm serve "$MODEL" "$PAR" "$GPUS" --port "$PORT" "${ARGS[@]}" 2>&1 | tee "vllm_$NAME.log"
  exit
fi
i=0
for gpu in "${GPU_LIST[@]}"; do
  echo "GPU $gpu -> http://127.0.0.1:$((PORT + i))/v1   (log: vllm_${NAME}_gpu$gpu.log)"
  CUDA_VISIBLE_DEVICES=$gpu vllm serve "$MODEL" --port $((PORT + i)) "${ARGS[@]}" > "vllm_${NAME}_gpu$gpu.log" 2>&1 &
  i=$((i + 1))
done
echo "Servers starting; the first start downloads the weights. Ready when 'curl -s localhost:$PORT/v1/models' answers. Ctrl-c stops all."
wait
