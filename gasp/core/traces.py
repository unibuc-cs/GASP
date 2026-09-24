"""Trace records and JSONL export."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class TraceRecord:
    scenario_id: str
    family: str
    mode: str
    step: int
    role: str
    action: Dict[str, Any]
    guard: Dict[str, Any]
    executed: bool
    high_impact: bool
    attempted_violation: bool
    executed_violation: bool
    violation_type: Optional[str]
    rule_id: Optional[str]
    supported: bool
    refs_total: int
    refs_invalid: int
    cited_false: bool
    cited_unverified: bool
    requires_approval: bool
    approval_granted: bool
    escalation: bool               # the guard escalated or the role asked for approval itself
    needs_approval_prob: Optional[float]
    off_target: bool
    formatting_failure: bool       # the policy produced an invalid action and it was replaced by noop
    tokens_in: int
    tokens_out: int
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def write_jsonl(records: Iterable[TraceRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict(), sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> List[TraceRecord]:
    out: List[TraceRecord] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(TraceRecord(**json.loads(line)))
    return out
