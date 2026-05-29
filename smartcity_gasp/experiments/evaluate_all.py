"""Run a compact end-to-end experiment suite.

By default this runs deterministic baselines and, if PyTorch is available, short
IPPO/MAPPO smoke-training runs.  The output is intended as a working example for
users; serious paper numbers should be regenerated with more episodes and seeds.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/results"))
    parser.add_argument("--quick", action="store_true", help="very small run for CI/smoke tests")
    args = parser.parse_args()

    det_episodes = "6" if args.quick else "20"
    train_episodes = "2" if args.quick else "120"
    eval_episodes = "2" if args.quick else "40"

    run([sys.executable, "-m", "smartcity_gasp.experiments.run_deterministic_baselines", "--episodes", det_episodes, "--output-dir", str(args.output_dir)])

    try:
        import torch  # noqa: F401
    except Exception:
        print("PyTorch is not installed; skipping MARL training.")
        return

    run([sys.executable, "-m", "smartcity_gasp.experiments.train_marl", "--algorithm", "ippo", "--episodes", train_episodes, "--eval-episodes", eval_episodes, "--output-dir", str(args.output_dir)])
    run([sys.executable, "-m", "smartcity_gasp.experiments.train_marl", "--algorithm", "mappo", "--episodes", train_episodes, "--eval-episodes", eval_episodes, "--output-dir", str(args.output_dir)])
    run([sys.executable, "-m", "smartcity_gasp.experiments.train_marl", "--algorithm", "mappo", "--governed", "--episodes", train_episodes, "--eval-episodes", eval_episodes, "--output-dir", str(args.output_dir)])


if __name__ == "__main__":
    main()
