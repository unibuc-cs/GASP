"""Evidence objects.

Every piece of evidence has an id that policies must cite when they propose a
high-impact action.  The guard checks the cited ids, not a state flag, so
support is something a policy does or fails to do.  Memory notes are evidence
too: a note written with a verified source inherits ``verified`` status and
becomes visible to every active role, which is how roles coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, FrozenSet, Optional


UNVERIFIED = "unverified"
VERIFIED = "verified"
CONFLICTING = "conflicting"
REFUTED = "refuted"


@dataclass
class Evidence:
    id: str
    topic: str                 # incident, congestion, hazard, pollution, power, water, public, distractor
    kind: str                  # sensor_reading, incident_report, field_report, camera_confirmation, public_report, memory_note
    claim: str
    target: str                # district or route the claim is about
    status: str = UNVERIFIED
    truthful: bool = True      # hidden ground truth; verification reveals it
    visible_to: FrozenSet[str] = frozenset()
    source_role: Optional[str] = None        # memory notes only
    source_ref: Optional[str] = None         # memory notes only: the evidence id they cite
    expires_at: Optional[int] = None         # memory notes only
    conflicts_with: Optional[str] = None     # id of a contradicting piece of evidence

    def visible(self, role: str) -> bool:
        return role in self.visible_to or "*" in self.visible_to

    def is_verified(self) -> bool:
        return self.status == VERIFIED

    def public_view(self) -> Dict[str, object]:
        """What a role is allowed to see. The truth flag stays hidden."""

        return {
            "id": self.id,
            "topic": self.topic,
            "kind": self.kind,
            "claim": self.claim,
            "target": self.target,
            "status": self.status,
            "source_role": self.source_role,
            "source_ref": self.source_ref,
            "expires_at": self.expires_at,
        }

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["visible_to"] = sorted(self.visible_to)
        return data
