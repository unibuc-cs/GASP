#!/usr/bin/env bash
# Serve meta-models/Muse-Glimmer-30B with vLLM on every GPU of the machine, as OpenAI-compatible servers.
# (Muse-Glimmer-30B-assistant is NOT the model: it is the 5 GB speculative decoding drafter head, without a
# tokenizer, and vLLM cannot serve it on its own.)
#
# Run it over ssh inside tmux so the servers outlive the ssh session:
#   ssh user@gpu-server
#   tmux new -s vllm
#   source ~/muse-glimmer/.venv/bin/activate   # the uv environment on our server; elsewhere: pip install vllm
#   bash scripts/serve_local_model.sh          # then Ctrl-b d to detach
#
# GPUs are detected with nvidia-smi. Default layout: one server per GPU (ports 8000, 8001, ...), each with a full
# copy of the model; scripts/run_local_ablation.sh finds the servers and spreads its processes over them. The
# precision is chosen from the memory of the first GPU: bf16 (about 60 GB) above 70 GB, fp8 (about 30 GB) above
# 38 GB, 4-bit bitsandbytes (about 17 GB, slower) below. Overrides:
#   GPUS=2 bash scripts/serve_local_model.sh        # use only the first two GPUs
#   QUANT=fp8 bash scripts/serve_local_model.sh     # force a precision (fp8 | bitsandbytes | "" for bf16)
#   LAYOUT=tp bash scripts/serve_local_model.sh     # one server over all GPUs (tensor parallel) when the model does
#                                                   # not fit on one GPU; vLLM needs the head count divisible by GPUS
# The first start downloads the weights from Hugging Face (about 60 GB); set HF_HOME to a disk with room.
# Servers listen on 127.0.0.1 only. From another machine reach one through an ssh tunnel:
#   ssh -N -L 8000:localhost:8000 user@gpu-server
set -euo pipefail
MODEL=${MODEL:-meta-models/Muse-Glimmer-30B}
PORT=${PORT:-8000}
LAYOUT=${LAYOUT:-dp}
REASONING_PARSER=${REASONING_PARSER:-muse_glimmer}   # vLLM's parser for this model: keeps the reasoning out of the answer text
NGPU=$(nvidia-smi -L 2>/dev/null | wc -l)
GPUS=${GPUS:-$NGPU}
if (( GPUS < 1 )); then echo "no GPU found by nvidia-smi"; exit 1; fi
MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
if [[ -z "${QUANT+x}" ]]; then        # QUANT not given: choose from GPU memory (MiB)
  if (( MEM >= 70000 )); then QUANT=""; elif (( MEM >= 38000 )); then QUANT=fp8; else QUANT=bitsandbytes; fi
fi
ARGS=(--served-model-name glimmer --host 127.0.0.1 --max-model-len 8192 --max-num-seqs 16 --gpu-memory-utilization 0.92)
if [[ "$REASONING_PARSER" != "none" ]]; then ARGS+=(--reasoning-parser "$REASONING_PARSER"); fi
if [[ -n "$QUANT" ]]; then ARGS+=(--quantization "$QUANT"); fi
echo "GPUs: $NGPU found, using $GPUS; memory per GPU: $MEM MiB; precision: ${QUANT:-bf16}; layout: $LAYOUT"
trap 'kill 0' INT TERM
if [[ "$LAYOUT" == "tp" ]]; then
  echo "vllm serve $MODEL --tensor-parallel-size $GPUS --port $PORT ${ARGS[*]}"
  exec vllm serve "$MODEL" --tensor-parallel-size "$GPUS" --port "$PORT" "${ARGS[@]}"
fi
for ((i = 0; i < GPUS; i++)); do
  echo "GPU $i -> http://127.0.0.1:$((PORT + i))/v1   (log: vllm_gpu$i.log)"
  CUDA_VISIBLE_DEVICES=$i vllm serve "$MODEL" --port $((PORT + i)) "${ARGS[@]}" > "vllm_gpu$i.log" 2>&1 &
done
echo "Servers starting; the first start downloads the weights. Ready when 'curl -s localhost:$PORT/v1/models' answers. Ctrl-c stops all."
wait
