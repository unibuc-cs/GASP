"""Shared helpers for experiment scripts: scenario sets, manifests, running a mode."""

from __future__ import annotations

import json
import platform
import random
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from gasp import __version__
from gasp.core.domain import Scenario
from gasp.core.env import EnvConfig, EpisodeResult, run_episode
from gasp.core.metrics import episode_metrics
from gasp.core.rules import RuleSet
from gasp.core.traces import write_jsonl


def make_scenarios(domain, per_family: int, seed: int, options: Optional[Dict[str, Any]] = None) -> List[Scenario]:
    """Stratified scenario set: exactly ``per_family`` scenarios per family, reproducible from the seed."""

    rng = random.Random(seed)
    out: List[Scenario] = []
    for fam in domain.families():
        for i in range(per_family):
            out.append(domain.sample_scenario(rng, fam, i + 1, options or {}))
    return out


def save_scenarios(scenarios: List[Scenario], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([s.to_dict() for s in scenarios], indent=1), encoding="utf-8")


def load_scenarios(path: str | Path) -> List[Scenario]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Scenario(**d) for d in data]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"


def manifest(extra: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "gasp_version": __version__,
        "git_commit": git_commit(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        **extra,
    }


def run_mode(domain, scenarios: Iterable[Scenario], policy, config: EnvConfig, rule_set: RuleSet,
             trace_dir: Optional[Path] = None, repeats: int = 1) -> List[EpisodeResult]:
    results: List[EpisodeResult] = []
    for sc in scenarios:
        for rep in range(repeats):
            res = run_episode(domain, sc, policy, config, rule_set)
            res.mode = config.mode_name
            if repeats > 1:
                res.scenario_id = f"{sc.scenario_id}"
                for rec in res.records:
                    rec.mode = config.mode_name
            results.append(res)
            if trace_dir is not None:
                suffix = f"_r{rep}" if repeats > 1 else ""
                write_jsonl(res.records, trace_dir / f"{config.mode_name}__{sc.scenario_id}{suffix}.jsonl")
    return results


def metrics_rows(results: List[EpisodeResult], max_steps: int, extra: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    rows = []
    for i, res in enumerate(results):
        row = episode_metrics(res, max_steps)
        row.update(extra or {})
        rows.append(row)
    return rows
