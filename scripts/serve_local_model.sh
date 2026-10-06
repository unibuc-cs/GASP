#!/usr/bin/env bash
# Serve Muse-Glimmer-30B-assistant with vLLM on the GPU machine, as an OpenAI-compatible server on port 8000.
# Run it over ssh inside tmux (or screen) so the server outlives the ssh session:
#   ssh user@gpu-server
#   tmux new -s vllm
#   pip install vllm                          # once; needs CUDA drivers on the machine
#   bash scripts/serve_local_model.sh          # then detach with Ctrl-b d
# Pick the variant by GPU memory (nvidia-smi):
#   bash scripts/serve_local_model.sh          # bf16: about 60 GB of weights. One 80 GB card, or two cards with TP=2
#   TP=2 bash scripts/serve_local_model.sh     # same, split over two GPUs (2 x 40 GB or 2 x 48 GB)
#   QUANT=fp8 bash scripts/serve_local_model.sh  # about 30 GB: one 40 or 48 GB card (works on Ampere, faster on Ada/Hopper)
#   QUANT=bitsandbytes bash scripts/serve_local_model.sh  # about 17 GB, 4-bit on the fly: a 24 GB card, slower
# The first start downloads the weights from Hugging Face (about 60 GB); set HF_HOME to a disk with room.
# The model listens on 127.0.0.1 only. From another machine reach it through an ssh tunnel:
#   ssh -N -L 8000:localhost:8000 user@gpu-server
set -euo pipefail
MODEL=${MODEL:-meta-models/Muse-Glimmer-30B-assistant}
PORT=${PORT:-8000}
TP=${TP:-1}
ARGS=(--served-model-name glimmer --host 127.0.0.1 --port "$PORT" --max-model-len 8192 --max-num-seqs 16
      --gpu-memory-utilization 0.92 --tensor-parallel-size "$TP")
if [[ -n "${QUANT:-}" ]]; then ARGS+=(--quantization "$QUANT"); fi
echo "vllm serve $MODEL ${ARGS[*]}"
exec vllm serve "$MODEL" "${ARGS[@]}"
