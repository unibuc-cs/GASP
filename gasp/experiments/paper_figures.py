"""Figure for the LLM results: four small panels, one dot per mode and model with a 95% bootstrap interval.

    python -m gasp.experiments.paper_figures --episodes "outputs/llm/*/episodes.csv" --out paper/figures/llm_modes.png
"""

from __future__ import annotations

import argparse
import glob
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from gasp.experiments.analyze import bootstrap_ci, read_rows


PANELS = [("success", "task success"), ("executed_violations", "executed violations per incident"),
          ("overseer_load", "approval requests per incident"), ("steps", "steps per incident")]
MODES = ["M0", "M1", "M2", "M3", "M4"]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # fixed categorical order


def per_scenario_means(rows: List[Dict[str, Any]], metric: str) -> Dict[tuple, List[float]]:
    acc: Dict[tuple, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get(metric) is not None:
            acc[(r["model"], r["mode"])][r["scenario_id"]].append(float(r[metric]))
    return {k: [float(np.mean(v)) for v in scen.values()] for k, scen in acc.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=str, required=True)
    ap.add_argument("--out", type=Path, default=Path("paper/figures/llm_modes.png"))
    args = ap.parse_args()
    rows: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(args.episodes)) or [args.episodes]:
        rows += read_rows(Path(path))
    models = sorted({r["model"] for r in rows})
    modes = [m for m in MODES if any(r["mode"] == m for r in rows)]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(PANELS), figsize=(2.2 * len(PANELS), 2.4), dpi=200)
    for ax, (metric, title) in zip(axes, PANELS):
        data = per_scenario_means(rows, metric)
        for i, model in enumerate(models):
            xs, ys, lo, hi = [], [], [], []
            for j, mode in enumerate(modes):
                vals = data.get((model, mode))
                if not vals:
                    continue
                m = float(np.mean(vals))
                a, b = bootstrap_ci(vals, n_boot=2000)
                xs.append(j + (i - (len(models) - 1) / 2) * 0.18)
                ys.append(m)
                lo.append(m - a)
                hi.append(b - m)
            ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", color=COLORS[i % len(COLORS)], markersize=4, capsize=2, linewidth=1, label=model)
        ax.set_xticks(range(len(modes)))
        ax.set_xticklabels(modes, fontsize=7)
        ax.set_title(title, fontsize=8)
        ax.tick_params(axis="y", labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(True, axis="y", color="#eeeeee", linewidth=0.6)
    axes[0].legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, bbox_inches="tight")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
