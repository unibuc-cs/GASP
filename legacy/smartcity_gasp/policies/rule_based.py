"""Readable deterministic policies for baseline experiments.

These policies are not meant to be optimal.  They are hand-written to produce
interpretable traces for the paper and to provide sanity checks for the MARL
environment.  Learned IPPO/MAPPO policies use the same action indices, so the
resulting traces remain comparable.
"""

from __future__ import annotations

from typing import Dict

from smartcity_gasp.core.state import ScenarioType
from smartcity_gasp.envs.smartcity_parallel_env import SmartCityParallelEnv


class RuleBasedPolicy:
    """Simple scenario-aware role policy."""

    def act(self, env: SmartCityParallelEnv) -> Dict[str, int]:
        if env.state is None:
            raise RuntimeError("environment must be reset before acting")
        state = env.state
        stype = state.scenario.scenario_type
        actions: Dict[str, int] = {}

        for agent in env.agents:
            if agent == "DirectController":
                actions[agent] = self._direct_action(state.step, stype)
            elif agent == "TrafficAgent":
                actions[agent] = self._traffic_action(state.step, stype)
            elif agent == "EmergencyAgent":
                actions[agent] = self._emergency_action(state.step, stype)
            elif agent == "EnergyAgent":
                actions[agent] = self._energy_action(state.step, stype)
            elif agent == "WaterAgent":
                actions[agent] = self._water_action(state.step, stype)
            elif agent == "PollutionAgent":
                actions[agent] = self._pollution_action(state.step, stype)
            elif agent == "PublicTransportAgent":
                actions[agent] = self._transport_action(state.step, stype)
            elif agent == "PublicWorksAgent":
                actions[agent] = self._works_action(state.step, stype)
            elif agent == "CitizenCommsAgent":
                actions[agent] = self._comms_action(state.step, stype)
            else:
                actions[agent] = 0
        return actions

    def _direct_action(self, step: int, stype: ScenarioType) -> int:
        if step == 0:
            return 1  # query evidence
        if stype in {ScenarioType.TRAFFIC_ACCIDENT, ScenarioType.POWER_OUTAGE}:
            return 6  # dispatch ambulance
        if stype == ScenarioType.FLOODED_UNDERPASS:
            return 5  # route intervention, imperfect for flooding
        return 7  # broadcast alert

    def _traffic_action(self, step: int, stype: ScenarioType) -> int:
        if step == 0:
            return 1
        if stype == ScenarioType.TRAFFIC_ACCIDENT:
            return 6  # open bus lane
        if stype == ScenarioType.POWER_OUTAGE:
            return 7  # signal priority
        if stype == ScenarioType.FLOODED_UNDERPASS:
            return 5  # reroute traffic
        if stype == ScenarioType.POLLUTION_SPIKE:
            return 5  # reroute traffic, possibly sanitized
        return 0

    def _emergency_action(self, step: int, stype: ScenarioType) -> int:
        if stype in {ScenarioType.TRAFFIC_ACCIDENT, ScenarioType.POWER_OUTAGE}:
            return 5 if step > 0 else 1
        return 0

    def _energy_action(self, step: int, stype: ScenarioType) -> int:
        if stype == ScenarioType.POWER_OUTAGE:
            return 5 if step > 0 else 1
        return 0

    def _water_action(self, step: int, stype: ScenarioType) -> int:
        if stype == ScenarioType.FLOODED_UNDERPASS:
            return 5 if step > 0 else 1
        return 0

    def _pollution_action(self, step: int, stype: ScenarioType) -> int:
        if stype == ScenarioType.POLLUTION_SPIKE:
            return 5 if step > 0 else 1
        return 0

    def _transport_action(self, step: int, stype: ScenarioType) -> int:
        if stype == ScenarioType.POLLUTION_SPIKE:
            return 5 if step > 0 else 0
        return 0

    def _works_action(self, step: int, stype: ScenarioType) -> int:
        if stype == ScenarioType.FLOODED_UNDERPASS:
            return 5 if step > 0 else 0
        return 0

    def _comms_action(self, step: int, stype: ScenarioType) -> int:
        if step == 0:
            return 2  # request verification before communication
        return 5  # broadcast alert
