"""Trace records and JSONL export helpers.

The trace is the main measurement object in the demo.  Every proposed action is
stored together with state context, evidence links, guard outcome, violation
labels, support annotations, and reward information.  This is intentionally more
verbose than a typical RL rollout because the paper studies trace-centric
evaluation rather than final reward alone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .actions import GuardDecision, TypedAction


@dataclass
class TraceRecord:
    """One typed trace entry corresponding to one role action."""

    scenario_id: str
    scenario_type: str
    episode_step: int
    role: str
    action: Dict[str, object]
    guard: Dict[str, object]
    state_before: Dict[str, object]
    state_after: Dict[str, object]
    high_impact: bool
    consequential: bool
    supported: bool
    requires_escalation: bool
    escalation_required_label: int
    escalation_probability: float
    violation_type: Optional[str]
    reward: float
    info: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class TraceLogger:
    """Collect and export trace records for one or more episodes."""

    def __init__(self):
        self.records: List[TraceRecord] = []

    def append(self, record: TraceRecord) -> None:
        self.records.append(record)

    def extend(self, records: Iterable[TraceRecord]) -> None:
        self.records.extend(records)

    def clear(self) -> None:
        self.records.clear()

    def to_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec.to_dict(), sort_keys=True) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "TraceLogger":
        logger = cls()
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                payload = json.loads(line)
                logger.records.append(TraceRecord(**payload))
        return logger


def records_to_json(records: List[TraceRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in records], f, indent=2, sort_keys=True)
