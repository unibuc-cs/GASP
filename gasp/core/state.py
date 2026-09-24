"""Global state of one episode.

The state is symbolic on purpose: every quantity a rule looks at is a field
here, and every field appears in the trace snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .evidence import Evidence, VERIFIED, UNVERIFIED, REFUTED, CONFLICTING


PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"


@dataclass
class Approval:
    key: str                 # action_type@target
    requested_by: str
    requested_at: int
    ready_at: int
    justified: bool          # the request cited verified evidence
    soft: bool = True        # soft approvals can be waived by an adaptive governor; hard ones never
    status: str = PENDING
    delegated: bool = False  # granted by the adaptive governor without a human

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "ready_at": self.ready_at,
            "justified": self.justified,
            "soft": self.soft,
            "status": self.status,
            "delegated": self.delegated,
        }


@dataclass
class State:
    scenario: Any                                  # Scenario
    step: int = 0
    evidence: Dict[str, Evidence] = field(default_factory=dict)
    memory: Dict[str, Evidence] = field(default_factory=dict)
    approvals: Dict[str, Approval] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    emergency_priority_active: bool = False
    active_roles: List[str] = field(default_factory=list)
    last_guard: Dict[str, Dict[str, Any]] = field(default_factory=dict)   # role -> last decision summary
    halted: bool = False
    memory_counter: int = 0
    counters: Dict[str, int] = field(default_factory=dict)
    verification_requests: Dict[str, str] = field(default_factory=dict)   # evidence id -> role that asked
    trust: Dict[str, float] = field(default_factory=dict)                 # per-role trust used by the adaptive governor

    # ---- evidence -------------------------------------------------------
    def all_evidence(self) -> Dict[str, Evidence]:
        merged = dict(self.evidence)
        merged.update(self.memory)
        return merged

    def visible_evidence(self, role: str) -> List[Evidence]:
        out = []
        for ev in self.evidence.values():
            if ev.visible(role):
                out.append(ev)
        for note in self.memory.values():
            if note.expires_at is None or note.expires_at > self.step:
                out.append(note)
        return out

    def lookup(self, ref: str) -> Optional[Evidence]:
        ev = self.evidence.get(ref)
        if ev is None:
            ev = self.memory.get(ref)
        if ev is not None and ev.kind == "memory_note" and ev.expires_at is not None and ev.expires_at <= self.step:
            return None
        return ev

    def verify(self, ref: str) -> Optional[str]:
        """Resolve the status of one piece of evidence. Returns the new status."""

        ev = self.evidence.get(ref)
        if ev is None:
            return None
        self.verification_requests.pop(ref, None)
        if ev.status in (VERIFIED, REFUTED):
            return ev.status
        ev.status = VERIFIED if ev.truthful else REFUTED
        if ev.conflicts_with and ev.conflicts_with in self.evidence:
            other = self.evidence[ev.conflicts_with]
            if other.status in (UNVERIFIED, CONFLICTING):
                other.status = VERIFIED if other.truthful else REFUTED
        return ev.status

    def add_memory_note(self, role: str, claim: str, source_ref: str, topic: str, target: str, expires_in: Optional[int]) -> Evidence:
        self.memory_counter += 1
        source = self.lookup(source_ref)
        status = VERIFIED if (source is not None and source.is_verified()) else UNVERIFIED
        note = Evidence(
            id=f"M{self.memory_counter}",
            topic=topic,
            kind="memory_note",
            claim=claim,
            target=target,
            status=status,
            truthful=bool(source is not None and source.truthful),
            visible_to=frozenset({"*"}),
            source_role=role,
            source_ref=source_ref,
            expires_at=(self.step + expires_in) if expires_in is not None else None,
        )
        self.memory[note.id] = note
        return note

    # ---- approvals ------------------------------------------------------
    def request_approval(self, key: str, role: str, justified: bool, soft: bool = True) -> Approval:
        existing = self.approvals.get(key)
        if existing is not None:
            # A pending request is not duplicated; a denied one stays denied for the episode.
            return existing
        latency = max(1, int(self.scenario.overseer_latency))
        appr = Approval(key=key, requested_by=role, requested_at=self.step, ready_at=self.step + latency, justified=justified, soft=soft)
        self.approvals[key] = appr
        self.counters["approval_requests"] = self.counters.get("approval_requests", 0) + 1
        return appr

    def delegate_approval(self, key: str, role: str) -> Approval:
        """Adaptive governor grants a soft approval to a trusted role; no human is involved."""

        appr = Approval(key=key, requested_by=role, requested_at=self.step, ready_at=self.step, justified=True,
                        soft=True, status=APPROVED, delegated=True)
        self.approvals[key] = appr
        return appr

    def resolve_approvals(self) -> None:
        hidden = bool(self.scenario.params.get("hidden_denial", False))
        for appr in self.approvals.values():
            if appr.status == PENDING and appr.ready_at <= self.step:
                ok = self.scenario.overseer_available and appr.justified and not (hidden and appr.soft)
                appr.status = APPROVED if ok else DENIED

    def is_approved(self, key: str) -> bool:
        appr = self.approvals.get(key)
        return appr is not None and appr.status == APPROVED

    def is_human_approved(self, key: str) -> bool:
        appr = self.approvals.get(key)
        return appr is not None and appr.status == APPROVED and not appr.delegated

    def approval_status(self, key: str) -> Optional[str]:
        appr = self.approvals.get(key)
        return appr.status if appr else None

    # ---- snapshots ------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "flags": dict(self.flags),
            "emergency_priority_active": self.emergency_priority_active,
            "evidence_status": {k: v.status for k, v in self.evidence.items()},
            "memory": [n.public_view() for n in self.memory.values()],
            "approvals": {k: a.status for k, a in self.approvals.items()},
            "active_roles": list(self.active_roles),
        }
