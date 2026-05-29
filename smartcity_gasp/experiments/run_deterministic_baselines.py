"""Run deterministic smart-city baselines and export traces/tables.

This script is the easiest way to reproduce the paper-style deterministic
results.  It evaluates four execution modes:

B0 direct controller, unguarded;
B1 all agents active, unguarded;
B2 scenario-activated agents, unguarded;
B3 scenario-activated agents, governed.

The exported traces are JSONL files and can be inspected manually.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from smartcity_gasp.core.metrics import EpisodeSummary, aggregate_by_mode, rows_to_latex, rows_to_markdown
from smartcity_gasp.core.traces import TraceLogger, records_to_json
from smartcity_gasp.envs.smartcity_parallel_env import EnvConfig, SmartCityParallelEnv
from smartcity_gasp.policies.rule_based import RuleBasedPolicy


MODES = [
    ("B0_direct_controller", EnvConfig(governed=False, activation_mode="direct", seed=11)),
    ("B1_all_agents_no_guard", EnvConfig(governed=False, activation_mode="all", seed=11)),
    ("B2_activated_no_guard", EnvConfig(governed=False, activation_mode="scenario", seed=11)),
    ("B3_activated_governed", EnvConfig(governed=True, activation_mode="scenario", seed=11)),
]


def run_mode(label: str, config: EnvConfig, episodes: int) -> List[EpisodeSummary]:
    env = SmartCityParallelEnv(config)
    policy = RuleBasedPolicy()
    summaries: List[EpisodeSummary] = []
    for _ in range(episodes):
        env.reset()
        done = False
        while not done:
            actions = policy.act(env)
            _, _, terms, truncs, _ = env.step(actions)
            done = all(terms.values()) or all(truncs.values())
        assert env.last_summary is not None
        env.last_summary.mode = label
        summaries.append(env.last_summary)
    return summaries


def export_outputs(summaries: List[EpisodeSummary], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(exist_ok=True)

    for summary in summaries:
        logger = TraceLogger()
        logger.extend(summary.records)
        logger.to_jsonl(trace_dir / f"{summary.mode}_{summary.scenario_id}.jsonl")

    rows = aggregate_by_mode(summaries)
    with (output_dir / "deterministic_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].to_dict().keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())

    (output_dir / "deterministic_summary.md").write_text(rows_to_markdown(rows) + "\n", encoding="utf-8")
    (output_dir / "deterministic_table.tex").write_text(rows_to_latex(rows) + "\n", encoding="utf-8")

    # Save one short example trace in JSON for the README/paper notes.
    if summaries:
        records_to_json(summaries[-1].records[:12], output_dir / "example_trace.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20, help="episodes per mode")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/results"))
    args = parser.parse_args()

    all_summaries: List[EpisodeSummary] = []
    for label, config in MODES:
        all_summaries.extend(run_mode(label, config, args.episodes))
    export_outputs(all_summaries, args.output_dir)
    print((args.output_dir / "deterministic_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
