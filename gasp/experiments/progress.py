"""One line of progress for a grid run split over several processes.

    python -m gasp.experiments.progress --runs "outputs/llm/local_M2_*" "outputs/llm/local_M3_*" --total 480   # print once
    python -m gasp.experiments.progress --runs "outputs/llm_local_pilot/M*" --total 24 --watch 20   # redraw every 20 s

Counts the finished episodes (lines of episodes.jsonl in every matching run directory), shows a bar, the model
calls and tokens so far, the time since the monitor started and an estimate of the time left, plus the counts
per mode.  With --watch it redraws in place until the total is reached or Ctrl-c; the run scripts stop it when
their processes end.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from collections import Counter
from pathlib import Path


def snapshot(runs_globs):
    done, calls, tokens, per_mode, last = 0, 0, 0, Counter(), ""
    for d in sorted({d for g in runs_globs for d in glob.glob(g)}):
        p = Path(d) / "episodes.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            done += 1
            calls += int(r.get("calls", 0) or 0)
            tokens += int(r.get("tokens", 0) or 0)
            per_mode[r.get("mode", "?")] += 1
            last = f"{r.get('mode', '?')} {r.get('scenario_id', '?')} success={r.get('success', 0):.0f} steps={r.get('steps', 0):.0f}"
    return done, calls, tokens, per_mode, last


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, nargs="+", help="one or more globs of run directories")
    ap.add_argument("--total", type=int, required=True, help="episodes expected over all matching runs")
    ap.add_argument("--watch", type=float, default=0, help="seconds between redraws; 0 prints once")
    args = ap.parse_args()
    t0 = time.time()
    done0 = snapshot(args.runs)[0]
    tty = sys.stdout.isatty()
    while True:
        done, calls, tokens, per_mode, last = snapshot(args.runs)
        elapsed = time.time() - t0
        rate = (done - done0) / elapsed if elapsed > 0 and done > done0 else 0.0
        eta = fmt_time((args.total - done) / rate) if rate > 0 else "--:--:--"
        width = 30
        filled = min(width, int(width * done / args.total)) if args.total else 0
        bar = "#" * filled + "-" * (width - filled)
        modes = " ".join(f"{m}:{n}" for m, n in sorted(per_mode.items()))
        line = (f"[{bar}] {done}/{args.total} episodes  {calls} calls  {tokens / 1e6:.1f}M tokens  "
                f"elapsed {fmt_time(elapsed)}  left {eta}  ({modes})  last: {last}")
        if tty and args.watch:
            sys.stdout.write("\r" + line[:200].ljust(200))
        else:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()
        if not args.watch or done >= args.total:
            if tty and args.watch:
                sys.stdout.write("\n")
            break
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
