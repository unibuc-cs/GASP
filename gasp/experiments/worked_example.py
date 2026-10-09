"""Turn one trace into every metric value, step by step (for the paper's worked example).

    python -m gasp.experiments.worked_example --traces outputs/paper/traces --mode D3-roles-naive-guard \
        [--scenario TRAF-004] --out outputs/paper/worked_example

Without --scenario the script picks the trace of that mode with the most
distinct guard outcomes.  Output: a step table and the metric derivation, as
markdown and LaTeX.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

from gasp.core.env import EpisodeResult
from gasp.core.metrics import GAU_WEIGHTS, episode_metrics
from gasp.core.traces import TraceRecord, read_jsonl
from gasp.domains import get_domain


def pick_trace(trace_dir: Path, mode: str) -> Path:
    best, best_score = None, -1
    for p in sorted(trace_dir.glob(f"{mode}__*.jsonl")):
        recs = read_jsonl(p)
        outcomes = {r.guard["outcome"] for r in recs if r.action["action_type"] != "noop"}
        score = len(outcomes) * 10 + sum(1 for r in recs if r.escalation) - len(recs) / 50
        if score > best_score:
            best, best_score = p, score
    if best is None:
        raise SystemExit(f"no traces for mode {mode} in {trace_dir}")
    return best


def result_from_trace(domain, recs: List[TraceRecord], max_steps: int) -> EpisodeResult:
    flags = recs[-1].state_after["flags"]
    fake_state = SimpleNamespace(flags=flags, scenario=SimpleNamespace(family=recs[0].family))
    approvals = recs[-1].state_after.get("approvals", {})
    return EpisodeResult(
        scenario_id=recs[0].scenario_id, family=recs[0].family, mode=recs[0].mode,
        success=domain.is_success(fake_state), steps=recs[-1].step + 1,
        active_roles=recs[-1].state_after.get("active_roles", []),
        required_roles=domain.required_roles_by_family[recs[0].family],
        records=recs, final_flags=flags, approvals=approvals,
        hidden_exposure=False,
    )


def step_table(recs: List[TraceRecord]) -> List[Dict[str, str]]:
    rows = []
    for r in recs:
        a = r.action
        if a["action_type"] == "noop":
            continue
        refs = ", ".join(a["evidence_refs"]) or "–"
        status = {k: v for k, v in r.state_before.get("evidence_status", {}).items() if k in a["evidence_refs"]}
        ref_txt = ", ".join(f"{k} ({v})" for k, v in status.items()) if status else refs
        payload = a.get("payload", {})
        extra = payload.get("ref") or payload.get("topic") or payload.get("for_action") or ""
        outcome = r.guard["outcome"]
        note = r.violation_type or ("waived" if r.approval_waived else "")
        rows.append({"step": str(r.step), "role": r.role.replace("Agent", ""), "action": a["action_type"] + (f" ({extra})" if extra else ""),
                     "evidence": ref_txt, "guard": outcome, "rule": r.rule_id or "–", "note": note})
    return rows


def derivation(m: Dict[str, Any], recs: List[TraceRecord], max_steps: int) -> List[str]:
    proposals = [r for r in recs if r.action["action_type"] != "noop"]
    executed = [r for r in recs if r.executed and r.action["action_type"] != "noop"]
    executed_hi = [r for r in executed if r.high_impact]
    lines = [
        f"proposals (non-noop role actions): {len(proposals)}; environment steps: {int(m['steps'])}",
        f"attempted violations: {int(m['attempted_violations'])} = " + ", ".join(f"{k} × {v}" for k, v in m['violation_types'].items()),
        f"executed violations: {int(m['executed_violations'])} (executed proposals that broke a rule)",
        f"missed approvals: {int(m['missed_approvals'])} (executed actions that required approval and had none)",
        f"escalations: {int(m['escalations'])}; overseer load (distinct approval requests reaching the human): {int(m['overseer_load'])}; "
        f"granted {int(m['approvals_granted'])}, denied {int(m['approvals_denied'])}",
        f"escalation precision {fmt(m['escalation_precision'])}, recall {fmt(m['escalation_recall'])}",
        f"TSC: executed high-impact actions {len(executed_hi)}, supported {sum(1 for r in executed_hi if r.supported)} → {m['tsc']:.2f}",
        f"hallucinated references: {sum(r.refs_invalid for r in proposals)} of {sum(r.refs_total for r in proposals)} cited ids → {m['hallucinated_refs']:.2f}",
        f"false alert sent: {int(m['false_alert'])}; hidden harm: {int(m['hidden_harm'])}",
        f"success: {int(m['success'])}; silent violation (success with an executed violation): {int(m['silent_violation'])}",
        f"GAU = success − {GAU_WEIGHTS['executed_violation']}·executed violations − {GAU_WEIGHTS['missed_approval']}·missed approvals − "
        f"{GAU_WEIGHTS['unsupported_memory']}·unsupported memory writes − {GAU_WEIGHTS['step_cost']}·steps/{max_steps} − "
        f"{GAU_WEIGHTS['hidden_harm']}·hidden harm = {m['gau']:.2f}",
    ]
    if m.get("brier") is not None:
        lines.insert(6, f"Brier score of the reported approval probability: {m['brier']:.2f}")
    return lines


def fmt(v) -> str:
    return "–" if v is None else f"{v:.2f}"


def to_markdown(rows: List[Dict[str, str]], lines: List[str], title: str) -> str:
    out = [f"### {title}", "", "| step | role | action | cited evidence (status when cited) | guard | rule | note |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['step']} | {r['role']} | {r['action']} | {r['evidence']} | {r['guard']} | {r['rule']} | {r['note']} |")
    out += ["", "Metric derivation:", ""] + [f"- {l}" for l in lines]
    return "\n".join(out) + "\n"


def to_latex(rows: List[Dict[str, str]], lines: List[str], title: str) -> str:
    esc = lambda s: s.replace("_", r"\_").replace("→", r"$\rightarrow$").replace("−", "-").replace("×", r"$\times$").replace("·", r"$\cdot$")
    out = [r"\begin{table*}[t]", r"\centering", r"\caption{" + esc(title) + r"}", r"\label{tab:worked}", r"\footnotesize",
           r"\resizebox{\textwidth}{!}{\begin{tabular}{@{}llp{0.22\linewidth}p{0.26\linewidth}lll@{}}", r"\toprule",
           r"\textbf{Step} & \textbf{Role} & \textbf{Action} & \textbf{Evidence} & \textbf{Guard} & \textbf{Rule} & \textbf{Note} \\", r"\midrule"]
    for r in rows:
        out.append(" & ".join(esc(r[k]) for k in ("step", "role", "action", "evidence", "guard", "rule", "note")) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}}", "", r"\smallskip", r"\begin{minipage}{0.96\linewidth}\footnotesize\raggedright"]
    out += [r"\textbf{Derivation.} " + " ".join(esc(l) + "." for l in lines)]
    out += [r"\end{minipage}", r"\end{table*}"]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path, default=Path("outputs/paper/traces"))
    ap.add_argument("--mode", default="D3-roles-naive-guard")
    ap.add_argument("--scenario", default=None)
    ap.add_argument("--max-steps", type=int, default=16)
    ap.add_argument("--out", type=Path, default=Path("outputs/paper/worked_example"))
    args = ap.parse_args()
    domain = get_domain("smartcity")
    path = args.traces / f"{args.mode}__{args.scenario}.jsonl" if args.scenario else pick_trace(args.traces, args.mode)
    recs = read_jsonl(path)
    res = result_from_trace(domain, recs, args.max_steps)
    m = episode_metrics(res, args.max_steps)
    rows = step_table(recs)
    lines = derivation(m, recs, args.max_steps)
    title = f"Worked example: {recs[0].scenario_id} ({recs[0].family.replace('_', ' ')}), mode {args.mode}"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "worked_example.md").write_text(to_markdown(rows, lines, title), encoding="utf-8")
    (args.out / "worked_example.tex").write_text(to_latex(rows, lines, title), encoding="utf-8")
    (args.out / "metrics.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(to_markdown(rows, lines, title))


if __name__ == "__main__":
    main()
