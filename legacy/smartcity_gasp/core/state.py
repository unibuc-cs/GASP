"""Symbolic smart-city state for the GASP/MARL prototype.

The environment is intentionally small.  A realistic city simulator would make
it harder to inspect why an action was allowed, denied, or escalated.  This
state model instead exposes the governance-relevant variables needed by the
paper: scenario type, affected services, evidence quality, congestion, critical
infrastructure risk, and whether approvals or verified reports are available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Sequence


class ScenarioType(str, Enum):
    TRAFFIC_ACCIDENT = "traffic_accident"
    POWER_OUTAGE = "power_outage"
    FLOODED_UNDERPASS = "flooded_underpass"
    POLLUTION_SPIKE = "pollution_spike"


class EvidenceQuality(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    COMPLETE = "complete"
    CONFLICTING = "conflicting"


SERVICE_AGENTS: List[str] = [
    "TrafficAgent",
    "EmergencyAgent",
    "EnergyAgent",
    "WaterAgent",
    "PollutionAgent",
    "PublicTransportAgent",
    "PublicWorksAgent",
    "CitizenCommsAgent",
]

GOVERNANCE_ROLES: List[str] = ["VerifierAgent", "GovernorAgent", "HumanOverseer"]

ALL_ROLES: List[str] = SERVICE_AGENTS + GOVERNANCE_ROLES

ROLE_TO_INDEX: Dict[str, int] = {role: idx for idx, role in enumerate(SERVICE_AGENTS)}


SCENARIO_TO_REQUIRED_SERVICES: Dict[ScenarioType, List[str]] = {
    ScenarioType.TRAFFIC_ACCIDENT: [
        "TrafficAgent",
        "EmergencyAgent",
        "CitizenCommsAgent",
    ],
    ScenarioType.POWER_OUTAGE: [
        "EnergyAgent",
        "EmergencyAgent",
        "TrafficAgent",
        "CitizenCommsAgent",
    ],
    ScenarioType.FLOODED_UNDERPASS: [
        "WaterAgent",
        "TrafficAgent",
        "PublicWorksAgent",
        "CitizenCommsAgent",
    ],
    ScenarioType.POLLUTION_SPIKE: [
        "PollutionAgent",
        "TrafficAgent",
        "PublicTransportAgent",
        "CitizenCommsAgent",
    ],
}


@dataclass
class Scenario:
    """Immutable incident description sampled at episode reset."""

    scenario_id: str
    scenario_type: ScenarioType
    severity: int
    evidence_quality: EvidenceQuality
    congestion: int
    hospital_access_risk: bool
    pollution_zone_active: bool
    power_status_bad: bool
    water_status_bad: bool
    overseer_available: bool
    affected_services: List[str]

    @property
    def required_services(self) -> List[str]:
        return list(SCENARIO_TO_REQUIRED_SERVICES[self.scenario_type])


@dataclass
class CityState:
    """Mutable state updated during one episode."""

    scenario: Scenario
    step: int = 0
    max_steps: int = 8
    evidence_verified: bool = False
    public_report_verified: bool = False
    human_approval: bool = False
    emergency_priority_active: bool = False
    route_secured: bool = False
    ambulance_dispatched: bool = False
    power_restored: bool = False
    water_hazard_closed: bool = False
    repair_crew_dispatched: bool = False
    pollution_mitigated: bool = False
    transport_capacity_added: bool = False
    public_alert_sent: bool = False
    memory_supported: bool = False
    halted: bool = False
    objective_progress: float = 0.0
    last_guard_blocks: int = 0
    active_agents: List[str] = field(default_factory=list)

    def clone_summary(self) -> Dict[str, object]:
        """Small JSON-serializable state snapshot for traces."""

        return {
            "scenario_id": self.scenario.scenario_id,
            "scenario_type": self.scenario.scenario_type.value,
            "step": self.step,
            "evidence_verified": self.evidence_verified,
            "public_report_verified": self.public_report_verified,
            "human_approval": self.human_approval,
            "emergency_priority_active": self.emergency_priority_active,
            "route_secured": self.route_secured,
            "ambulance_dispatched": self.ambulance_dispatched,
            "power_restored": self.power_restored,
            "water_hazard_closed": self.water_hazard_closed,
            "repair_crew_dispatched": self.repair_crew_dispatched,
            "pollution_mitigated": self.pollution_mitigated,
            "transport_capacity_added": self.transport_capacity_added,
            "public_alert_sent": self.public_alert_sent,
            "memory_supported": self.memory_supported,
            "objective_progress": round(self.objective_progress, 3),
            "active_agents": list(self.active_agents),
        }

    def is_success(self) -> bool:
        """Scenario-specific success condition."""

        stype = self.scenario.scenario_type
        if stype == ScenarioType.TRAFFIC_ACCIDENT:
            return self.ambulance_dispatched and self.route_secured
        if stype == ScenarioType.POWER_OUTAGE:
            return self.power_restored and (self.ambulance_dispatched or self.route_secured)
        if stype == ScenarioType.FLOODED_UNDERPASS:
            return self.water_hazard_closed and self.repair_crew_dispatched
        if stype == ScenarioType.POLLUTION_SPIKE:
            return self.pollution_mitigated and self.transport_capacity_added
        return False

    def local_observation(self, agent: str) -> List[float]:
        """Return a fixed-size local observation for one service agent.

        The vector includes role identity, scenario indicators, and the state
        features that are plausibly observable by the role.  This is not meant
        to model real information access.  It simply gives MARL policies partial
        but sufficient information to learn scenario-specific behavior.
        """

        scenario = self.scenario
        role_one_hot = [0.0] * len(SERVICE_AGENTS)
        if agent in ROLE_TO_INDEX:
            role_one_hot[ROLE_TO_INDEX[agent]] = 1.0

        scenario_one_hot = [
            1.0 if scenario.scenario_type == ScenarioType.TRAFFIC_ACCIDENT else 0.0,
            1.0 if scenario.scenario_type == ScenarioType.POWER_OUTAGE else 0.0,
            1.0 if scenario.scenario_type == ScenarioType.FLOODED_UNDERPASS else 0.0,
            1.0 if scenario.scenario_type == ScenarioType.POLLUTION_SPIKE else 0.0,
        ]

        evidence_value = {
            EvidenceQuality.MISSING: 0.0,
            EvidenceQuality.PARTIAL: 0.35,
            EvidenceQuality.CONFLICTING: 0.5,
            EvidenceQuality.COMPLETE: 1.0,
        }[scenario.evidence_quality]

        shared_features = [
            scenario.severity / 3.0,
            scenario.congestion / 3.0,
            evidence_value,
            1.0 if scenario.hospital_access_risk else 0.0,
            1.0 if scenario.pollution_zone_active else 0.0,
            1.0 if scenario.power_status_bad else 0.0,
            1.0 if scenario.water_status_bad else 0.0,
            1.0 if scenario.overseer_available else 0.0,
            1.0 if self.evidence_verified else 0.0,
            1.0 if self.public_report_verified else 0.0,
            1.0 if self.human_approval else 0.0,
            1.0 if self.emergency_priority_active else 0.0,
            1.0 if self.route_secured else 0.0,
            1.0 if self.ambulance_dispatched else 0.0,
            1.0 if self.power_restored else 0.0,
            1.0 if self.water_hazard_closed else 0.0,
            1.0 if self.pollution_mitigated else 0.0,
            self.step / max(1, self.max_steps),
        ]

        return role_one_hot + scenario_one_hot + shared_features

    def global_observation(self) -> List[float]:
        """Global state vector used by the centralized critic."""

        # We concatenate local observations for all service roles and a small
        # summary of the active role mask.  This keeps the centralized critic
        # simple while exposing more information than any single role sees.
        global_vec: List[float] = []
        for role in SERVICE_AGENTS:
            global_vec.extend(self.local_observation(role))
        active_mask = [1.0 if role in self.active_agents else 0.0 for role in SERVICE_AGENTS]
        return global_vec + active_mask


def obs_dim() -> int:
    """Dimension of a local observation vector."""

    dummy_scenario = Scenario(
        scenario_id="dummy",
        scenario_type=ScenarioType.TRAFFIC_ACCIDENT,
        severity=1,
        evidence_quality=EvidenceQuality.PARTIAL,
        congestion=1,
        hospital_access_risk=True,
        pollution_zone_active=False,
        power_status_bad=False,
        water_status_bad=False,
        overseer_available=True,
        affected_services=SCENARIO_TO_REQUIRED_SERVICES[ScenarioType.TRAFFIC_ACCIDENT],
    )
    return len(CityState(dummy_scenario).local_observation("TrafficAgent"))


def global_obs_dim() -> int:
    dummy_scenario = Scenario(
        scenario_id="dummy",
        scenario_type=ScenarioType.TRAFFIC_ACCIDENT,
        severity=1,
        evidence_quality=EvidenceQuality.PARTIAL,
        congestion=1,
        hospital_access_risk=True,
        pollution_zone_active=False,
        power_status_bad=False,
        water_status_bad=False,
        overseer_available=True,
        affected_services=SCENARIO_TO_REQUIRED_SERVICES[ScenarioType.TRAFFIC_ACCIDENT],
    )
    return len(CityState(dummy_scenario).global_observation())
