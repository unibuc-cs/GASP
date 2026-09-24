"""Statistics for paired mode comparisons.

    python -m gasp.experiments.analyze --episodes outputs/llm/episodes.csv --out outputs/llm/stats \
        --pairs M2:M3,M0:M3,M3:M4 --group model

Unit of analysis: the scenario.  Repeats of one scenario are averaged first.
For each pair of modes and each metric: Wilcoxon signed-rank test on the paired
per-scenario values (no normality assumption; many differences are zero),
Cliff's delta as effect size, 95% bootstrap confidence intervals (10k
resamples) for each mean and for the mean difference, Holm correction across
the metrics of one pair.  Output: one markdown table per group and a CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from scipy import stats as sps  # type: ignore
except ImportError:  # pragma: no cover
    sps = None


PRIMARY_METRICS = ["success", "executed_violations", "attempted_violations", "missed_approvals", "false_alert", "hidden_harm",
                   "silent_violation", "tsc", "hallucinated_refs", "overseer_load", "steps", "proposals", "tokens", "gau"]


def read_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row: Dict[str, Any] = {}
            for k, v in r.items():
                if v is None or v == "":
                    row[k] = None
                    continue
                try:
                    row[k] = float(v)
                except ValueError:
                    row[k] = v
            rows.append(row)
    return rows


def per_scenario(rows: List[Dict[str, Any]], group_key: Optional[str]) -> Dict[Tuple, Dict[str, Dict[str, float]]]:
    """(group, mode) -> scenario_id -> metric -> mean over repeats."""

    acc: Dict[Tuple, Dict[str, Dict[str, List[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows:
        g = r.get(group_key) if group_key else "all"
        key = (g, r["mode"])
        for m in PRIMARY_METRICS:
            v = r.get(m)
            if v is not None:
                acc[key][r["scenario_id"]][m].append(float(v))
    out: Dict[Tuple, Dict[str, Dict[str, float]]] = {}
    for key, scen in acc.items():
        out[key] = {sid: {m: float(np.mean(v)) for m, v in ms.items()} for sid, ms in scen.items()}
    return out


def cliffs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    a = np.asarray(a)
    b = np.asarray(b)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return float((gt - lt) / (len(a) * len(b)))


def bootstrap_ci(values: Sequence[float], n_boot: int = 10000, seed: int = 0) -> Tuple[float, float]:
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    means = v[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def wilcoxon_p(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    d = np.asarray(a) - np.asarray(b)
    if len(d) < 5 or np.all(d == 0) or sps is None:
        return None if sps is None else 1.0
    try:
        return float(sps.wilcoxon(a, b, zero_method="zsplit").pvalue)
    except ValueError:
        return None


def holm(pvals: List[Optional[float]]) -> List[Optional[float]]:
    idx = [i for i, p in enumerate(pvals) if p is not None]
    m = len(idx)
    order = sorted(idx, key=lambda i: pvals[i])
    adjusted: List[Optional[float]] = [None] * len(pvals)
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * pvals[i])
        running = max(running, val)
        adjusted[i] = running
    return adjusted


def compare(scen_a: Dict[str, Dict[str, float]], scen_b: Dict[str, Dict[str, float]], label_a: str, label_b: str) -> List[Dict[str, Any]]:
    common = sorted(set(scen_a) & set(scen_b))
    results = []
    pvals = []
    for m in PRIMARY_METRICS:
        a = [scen_a[s][m] for s in common if m in scen_a[s] and m in scen_b[s]]
        b = [scen_b[s][m] for s in common if m in scen_a[s] and m in scen_b[s]]
        if not a:
            continue
        diff = list(np.asarray(b) - np.asarray(a))
        p = wilcoxon_p(a, b)
        pvals.append(p)
        results.append({
            "metric": m, "n": len(a),
            f"mean_{label_a}": float(np.mean(a)), f"ci_{label_a}": bootstrap_ci(a),
            f"mean_{label_b}": float(np.mean(b)), f"ci_{label_b}": bootstrap_ci(b),
            "mean_diff": float(np.mean(diff)), "ci_diff": bootstrap_ci(diff),
            "cliffs_delta": cliffs_delta(b, a), "p_wilcoxon": p,
        })
    for r, padj in zip(results, holm(pvals)):
        r["p_holm"] = padj
    return results


def fmt_ci(ci: Tuple[float, float]) -> str:
    return f"[{ci[0]:.2f}, {ci[1]:.2f}]"


def to_markdown(results: List[Dict[str, Any]], label_a: str, label_b: str) -> str:
    lines = [f"| metric | n | {label_a} mean [95% CI] | {label_b} mean [95% CI] | diff ({label_b} − {label_a}) [95% CI] | Cliff's δ | p (Wilcoxon) | p (Holm) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results:
        p = "–" if r["p_wilcoxon"] is None else f"{r['p_wilcoxon']:.3g}"
        ph = "–" if r.get("p_holm") is None else f"{r['p_holm']:.3g}"
        lines.append(f"| {r['metric']} | {r['n']} | {r[f'mean_{label_a}']:.2f} {fmt_ci(r[f'ci_{label_a}'])} | "
                     f"{r[f'mean_{label_b}']:.2f} {fmt_ci(r[f'ci_{label_b}'])} | {r['mean_diff']:+.2f} {fmt_ci(r['ci_diff'])} | "
                     f"{r['cliffs_delta']:+.2f} | {p} | {ph} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=str, required=True, help="a CSV or a glob such as 'outputs/llm/*/episodes.csv'")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pairs", type=str, default="M2:M3,M0:M3,M3:M4")
    ap.add_argument("--group", type=str, default=None, help="column to split by, e.g. model or rule_set")
    ap.add_argument("--filter", type=str, default=None, help="key=value filters, comma separated, e.g. rule_set=R2,overseer=scenario")
    args = ap.parse_args()

    import glob
    paths = sorted(glob.glob(str(args.episodes))) or [args.episodes]
    rows = []
    for path in paths:
        rows += read_rows(Path(path))
    if args.filter:
        for kv in args.filter.split(","):
            k, v = kv.split("=")
            rows = [r for r in rows if str(r.get(k)) == v or (isinstance(r.get(k), float) and str(r.get(k)) == v)]
    scen = per_scenario(rows, args.group)
    groups = sorted({k[0] for k in scen}, key=str)
    args.out.mkdir(parents=True, exist_ok=True)
    md_parts = []
    all_results = []
    for g in groups:
        for pair in args.pairs.split(","):
            a, b = pair.split(":")
            if (g, a) not in scen or (g, b) not in scen:
                continue
            res = compare(scen[(g, a)], scen[(g, b)], a, b)
            for r in res:
                r["group"] = g
                r["pair"] = pair
            all_results += res
            md_parts.append(f"### {g}: {a} vs {b}\n\n" + to_markdown(res, a, b) + "\n")
    (args.out / "paired_stats.md").write_text("\n".join(md_parts), encoding="utf-8")
    with (args.out / "paired_stats.json").open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=1, default=float)
    print("\n".join(md_parts))


if __name__ == "__main__":
    main()
