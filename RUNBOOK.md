# Runbook

Every operation, in the order you need them. `user@gpu-server` is the lab GPU node; the repository is `~/GASP` there
and `C:\Work\GASP` on the PC.

## 1. Sync code

The server has no git: PyCharm copies the code. Right-click the project > Deployment > Upload to the server
(or turn on Tools > Deployment > Automatic Upload once). `git push` on the PC only updates GitHub.

Keep PyCharm away from the results: Settings > Build, Execution, Deployment > Deployment > Excluded Paths, add `outputs`
both locally and on the server. Results travel only with `fetch_outputs.py` (section 3). On 15 Oct a sync left every
file under `outputs` empty.

## 2. Local models on the GPU server

Only cards 0 and 1 are ours: always `GPU_IDS=0,1`. One model at a time. Two tmux windows: serve in one, run in the other.

```bash
ssh user@gpu-server
tmux new -s vllm                               # later: tmux attach -t vllm
source ~/muse-glimmer/.venv/bin/activate
cd ~/GASP
```
   
tmux: `Ctrl-b c` new window, `Ctrl-b n` next window, `Ctrl-b d` leave (everything keeps running).

| Step | Window 0 (serve) | Window 1 (run) |
|---|---|---|
| Glimmer sweeps (done) | `GPU_IDS=0,1 bash scripts/serve_local_model.sh` | `bash scripts/run_local_ablation.sh sens` |
| gpt-oss-120b (done) | `MODEL=openai/gpt-oss-120b NAME=gptoss120b GPU_IDS=0,1 bash scripts/serve_local_model.sh` | `CONFIG=configs/llm_grid_local_large.yaml bash scripts/run_local_ablation.sh pilot`, then the same without `pilot` |
| Gemma 4 E4B (done) | `MODEL=google/gemma-4-E4B-it NAME=gemma4 GPU_IDS=0,1 bash scripts/serve_local_model.sh` | `CONFIG=configs/llm_grid_local_small.yaml bash scripts/run_local_ablation.sh pilot`, then the same without `pilot` |
| Qwen3.5-122B, no reasoning (done as the rehearsal; relabelled) | `MODEL=Qwen/Qwen3.5-122B-A10B NAME=qwen122b QUANT=fp8 LAYOUT=tp GPU_IDS=0,1 bash scripts/serve_local_model.sh` | `CONFIG=configs/mimic/llm_grid_mimic.yaml bash scripts/run_main_grid.sh`, then `... sens` |
| Glimmer, second domain (next) | `GPU_IDS=0,1 bash scripts/serve_local_model.sh` | `CONFIG=configs/llm_grid_local_ops.yaml bash scripts/run_local_ablation.sh pilot`, then the same without `pilot` (about a night) |
| Gemma 4 E4B, reasoning off (control, after that) | `MODEL=google/gemma-4-E4B-it NAME=gemma4 GPU_IDS=0,1 bash scripts/serve_local_model.sh` | `CONFIG=configs/llm_grid_local_small_nothink.yaml bash scripts/run_local_ablation.sh pilot`, then the same without `pilot` (fast) |

Between models:
  
```bash
pkill -f "vllm serve"; sleep 10; nvidia-smi    # stop the old servers; memory comes back
curl -s localhost:8000/v1/models               # new servers ready when this prints the model name; only then run
```

Good to know:

- A run prints one progress line every 20 s with the time left. Ctrl-c stops it; the same command continues where it stopped.
- Pilot is fine when: format failures under 1 per episode, success in M2 above 0.3, executed violations 0 in M3 and M4.
  Otherwise stop and tell me.
- Each finished run also leaves a copy in `~/gasp_backups/` on the server, outside the project, so a sync cannot reach it.
- The rehearsal of the API path (`configs/mimic`) ran Qwen3.5-122B under the names `sol` and `luna`. Those results are now
  one model, `qwen122b`, in `outputs/llm/qwen122b_M*` and `outputs/llm_sens/qwen122b_*`; the originals sit in `outputs/mimic`.
  If the real API run happens, its results land in `outputs/llm/M0` to `M4` as before and nothing collides. On the server,
  do the same before the API run: `python scripts/relabel_runs.py outputs/llm/M2 outputs/llm/qwen122b_M2 --model qwen122b --offset luna=5`
  for each mode, then move `outputs/llm/M?` away.
- Times on two cards: sweeps about half a day; the full run of a new model about a day.

## 3. Bring the results to the PC

After each step, in a terminal on the PC (not PyCharm's Run button):

```bash
python scripts/fetch_outputs.py user@gpu-server          # --no-traces skips the large trace files
```

It copies everything into `outputs\` and prints the episode counts. Then tell me; I write the paper part.

## 4. Build the paper

```bash
cd paper && make              # tables, figure, statistics from outputs/, then main.pdf
```

`make sync` needs only Python (no TeX); compile in Overleaf if there is no TeX. Red marks in the PDF say what is missing
and which file the numbers come from; none may remain at submission.

## 5. API models (GPT-6 Sol and Luna)

On any machine with internet; about 120 USD in total.

```bash
export OPENAI_API_KEY=sk-...                     # never commit it
pip install -r requirements.txt
bash scripts/run_pilot.sh                        # under an hour; check outputs/llm_pilot/PILOT_REPORT.md (same checks as above)
bash scripts/run_main_grid.sh                    # a few hours; rerun the same command if it stops
bash scripts/run_main_grid.sh sens               # sweeps on Luna
```

Then `fetch` is not needed: the results are already in `outputs/llm/` on that machine; copy that folder to the PC
(or run `make` there) and fill the red marks that start with "API:", or send the folder to me.

## 6. If something goes wrong

- "No server serving ...": the servers are not ready yet; wait for the `curl` line above to answer.
- The run uses the third card: `GPU_IDS=0,1` was missing on the serve command; stop and serve again.
- API errors 429 or 5xx: rerun the same command; finished episodes are kept.
- Every episode takes 16 steps: a result, not a bug; tell me.

Details on every number: `docs/RESULTS_GUIDE.md`.
