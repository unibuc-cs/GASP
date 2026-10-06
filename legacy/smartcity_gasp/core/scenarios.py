"""Scenario generation for the smart-city governed-agent benchmark.

The generator is deterministic under a seed.  Each episode samples one incident
family and a small set of governance-relevant variables.  This gives the MARL
trainer enough variation to learn role-specific behavior while keeping every
scenario easy to inspect in a JSON trace.
"""

from __future__ import annotations

import random
from dataclasses import asdict
from typing import Dict, Iterable, List, Optional

from .state import (
    EvidenceQuality,
    SCENARIO_TO_REQUIRED_SERVICES,
    Scenario,
    ScenarioType,
)


class ScenarioGenerator:
    """Reproducible scenario sampler used by baselines and MARL training."""

    def __init__(self, seed: int = 7):
        self.seed = seed
        self.rng = random.Random(seed)
        self.counter = 0

    def sample(self, scenario_type: Optional[ScenarioType] = None) -> Scenario:
        self.counter += 1
        stype = scenario_type or self.rng.choice(list(ScenarioType))
        severity = self.rng.randint(1, 3)
        congestion = self.rng.randint(1, 3)
        evidence_quality = self.rng.choice(list(EvidenceQuality))

        hospital_access_risk = stype in {ScenarioType.TRAFFIC_ACCIDENT, ScenarioType.POWER_OUTAGE}
        if stype == ScenarioType.TRAFFIC_ACCIDENT:
            hospital_access_risk = True
        elif self.rng.random() < 0.2:
            hospital_access_risk = True

        pollution_zone_active = stype == ScenarioType.POLLUTION_SPIKE or self.rng.random() < 0.35
        power_status_bad = stype == ScenarioType.POWER_OUTAGE
        water_status_bad = stype == ScenarioType.FLOODED_UNDERPASS
        overseer_available = self.rng.random() > 0.20

        return Scenario(
            scenario_id=f"S{self.counter:04d}",
            scenario_type=stype,
            severity=severity,
            evidence_quality=evidence_quality,
            congestion=congestion,
            hospital_access_risk=hospital_access_risk,
            pollution_zone_active=pollution_zone_active,
            power_status_bad=power_status_bad,
            water_status_bad=water_status_bad,
            overseer_available=overseer_available,
            affected_services=list(SCENARIO_TO_REQUIRED_SERVICES[stype]),
        )

    def batch(self, n: int) -> List[Scenario]:
        return [self.sample() for _ in range(n)]


def scenario_to_dict(scenario: Scenario) -> Dict[str, object]:
    """JSON-friendly scenario serialization."""

    data = asdict(scenario)
    data["scenario_type"] = scenario.scenario_type.value
    data["evidence_quality"] = scenario.evidence_quality.value
    return data
