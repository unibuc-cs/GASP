"""Train IPPO or MAPPO-style policies in the SmartCity-GASP environment.

The script is intentionally small and CPU-friendly.  It is suitable for smoke
runs and preliminary experiments, not for benchmark-scale MARL optimization.
For paper tables, train several seeds and export evaluation summaries with the
same typed trace metrics used by the deterministic baselines.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

from smartcity_gasp.core.metrics import EpisodeSummary, aggregate_by_mode, rows_to_latex, rows_to_markdown
from smartcity_gasp.core.traces import TraceLogger
from smartcity_gasp.envs.smartcity_parallel_env import EnvConfig, SmartCityParallelEnv
from smartcity_gasp.marl.ppo import PPOConfig, PPOTrainer, save_training_curve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", choices=["ippo", "mappo"], default="mappo")
    parser.add_argument("--episodes", type=int, default=120)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--governed", action="store_true")
    parser.add_argument("--activation-mode", choices=["scenario", "all", "direct"], default="scenario")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/results"))
    args = parser.parse_args()

    env = SmartCityParallelEnv(
        EnvConfig(
            governed=args.governed,
            activation_mode=args.activation_mode,
            seed=args.seed,
        )
    )
    trainer = PPOTrainer(
        env,
        PPOConfig(
            algorithm=args.algorithm,
            episodes=args.episodes,
            seed=args.seed,
        ),
    )
    train_summaries = trainer.train()
    eval_summaries = trainer.evaluate(args.eval_episodes, deterministic=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    mode_tag = f"{args.algorithm}_{'governed' if args.governed else 'unguarded'}"
    trainer.save(args.output_dir / f"{mode_tag}.pt")
    save_training_curve(train_summaries, args.output_dir / f"{mode_tag}_learning_curve.csv")

    rows = aggregate_by_mode(eval_summaries)
    (args.output_dir / f"{mode_tag}_summary.md").write_text(rows_to_markdown(rows) + "\n", encoding="utf-8")
    (args.output_dir / f"{mode_tag}_table.tex").write_text(rows_to_latex(rows) + "\n", encoding="utf-8")

    with (args.output_dir / f"{mode_tag}_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].to_dict().keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())

    trace_dir = args.output_dir / "traces"
    trace_dir.mkdir(exist_ok=True)
    for summary in eval_summaries[:5]:
        logger = TraceLogger()
        logger.extend(summary.records)
        logger.to_jsonl(trace_dir / f"{summary.mode}_{summary.scenario_id}.jsonl")

    print((args.output_dir / f"{mode_tag}_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
