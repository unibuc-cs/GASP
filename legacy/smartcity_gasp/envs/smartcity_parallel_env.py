"""PettingZoo-like parallel multi-agent environment for SmartCity-GASP.

The class intentionally mirrors the small subset of the PettingZoo ParallelEnv
API that is useful for the paper artifact: ``reset`` returns a dictionary of
agent observations, and ``step`` consumes a dictionary of agent actions.  This
keeps the demo dependency-light while still making the MARL structure clear.

A full PettingZoo wrapper can be added later without changing the core domain
logic.  The important research interface is already here: service agents act
from local observations, the centralized critic can inspect a global state
vector, typed actions are checked by the guard, and every transition produces a
trace entry.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from smartcity_gasp.core.actions import (
    ACTION_DIM,
    ActionType,
    GuardOutcome,
    RiskLevel,
    TypedAction,
)
from smartcity_gasp.core.activation import activate_agents
from smartcity_gasp.core.governance import GovernanceGuard, is_high_impact
from smartcity_gasp.core.metrics import EpisodeSummary
from smartcity_gasp.core.scenarios import ScenarioGenerator
from smartcity_gasp.core.state import (
    CityState,
    EvidenceQuality,
    SERVICE_AGENTS,
    Scenario,
    ScenarioType,
    global_obs_dim,
    obs_dim,
)
from smartcity_gasp.core.traces import TraceRecord


@dataclass
class EnvConfig:
    """Configuration for a smart-city MARL episode."""

    governed: bool = True
    activation_mode: str = "scenario"  # scenario, all, direct
    max_steps: int = 8
    seed: int = 7
    include_direct_controller: bool = False
    trace_mode: str = "full"


class SmartCityParallelEnv:
    """A small parallel multi-agent environment with typed action traces."""

    metadata = {"name": "smartcity_gasp_parallel_v0"}

    def __init__(self, config: Optional[EnvConfig] = None):
        self.config = config or EnvConfig()
        self.rng = random.Random(self.config.seed)
        self.scenario_gen = ScenarioGenerator(seed=self.config.seed)
        self.guard = GovernanceGuard(enabled=self.config.governed)
        self.possible_agents = ["DirectController"] if self.config.activation_mode == "direct" else list(SERVICE_AGENTS)
        self.agents: List[str] = []
        self.state: Optional[CityState] = None
        self.episode_records: List[TraceRecord] = []
        self.total_reward: float = 0.0
        self.last_summary: Optional[EpisodeSummary] = None

    @property
    def observation_dim(self) -> int:
        return obs_dim()

    @property
    def global_observation_dim(self) -> int:
        return global_obs_dim()

    @property
    def action_dim(self) -> int:
        return ACTION_DIM

    def reset(self, seed: Optional[int] = None, scenario: Optional[Scenario] = None):
        """Start a new scenario and return local observations."""

        if seed is not None:
            self.rng.seed(seed)
            self.scenario_gen = ScenarioGenerator(seed=seed)

        scenario = scenario or self.scenario_gen.sample()
        self.state = CityState(scenario=scenario, max_steps=self.config.max_steps)
        self.agents = activate_agents(scenario, mode=self.config.activation_mode)
        self.state.active_agents = list(self.agents)

        # Complete evidence is available immediately; weaker evidence requires
        # agents to query or verify it during the episode.
        self.state.evidence_verified = scenario.evidence_quality == EvidenceQuality.COMPLETE
        self.state.public_report_verified = scenario.evidence_quality == EvidenceQuality.COMPLETE
        self.state.human_approval = False
        self.episode_records = []
        self.total_reward = 0.0
        self.last_summary = None
        return self._observations(), self._infos()

    def step(self, actions: Dict[str, int]):
        """Apply one parallel step of proposed integer actions."""

        if self.state is None:
            raise RuntimeError("reset must be called before step")

        state = self.state
        rewards = {agent: -0.02 for agent in self.agents}
        infos = self._infos()
        terminations = {agent: False for agent in self.agents}
        truncations = {agent: False for agent in self.agents}

        state.last_guard_blocks = 0
        step_records: List[TraceRecord] = []

        for agent in list(self.agents):
            action_index = int(actions.get(agent, 0))
            state_before = state.clone_summary()
            typed_action = self._action_from_index(agent, action_index)
            decision = self.guard.check(state, typed_action)

            # In governed mode, escalation can become an explicit approval event.
            if decision.outcome == GuardOutcome.ESCALATE:
                if state.scenario.overseer_available:
                    state.human_approval = True
                    # The action is not executed in this step.  A later proposal
                    # can execute with approval, making escalation visible in the trace.
                    rewards[agent] += 0.15
                else:
                    rewards[agent] -= 0.30

            executed_action = decision.transformed_action or typed_action
            if decision.executed:
                rewards[agent] += self._apply_action(executed_action)
            else:
                state.last_guard_blocks += 1
                rewards[agent] -= 0.15

            # Unguarded execution can still be labelled as a violation.  Governed
            # execution records denied or escalated proposals separately.
            if decision.violation_type:
                rewards[agent] -= 0.35
            if decision.supported and is_high_impact(typed_action):
                rewards[agent] += 0.10
            if agent not in state.scenario.required_services and agent != "DirectController":
                rewards[agent] -= 0.08

            high_impact = is_high_impact(typed_action)
            state_after = state.clone_summary()
            rec = TraceRecord(
                scenario_id=state.scenario.scenario_id,
                scenario_type=state.scenario.scenario_type.value,
                episode_step=state.step,
                role=agent,
                action=typed_action.to_dict(),
                guard=decision.to_dict(),
                state_before=state_before,
                state_after=state_after,
                high_impact=high_impact,
                consequential=high_impact or typed_action.action_type != ActionType.NOOP,
                supported=decision.supported,
                requires_escalation=decision.requires_escalation,
                escalation_required_label=1 if decision.requires_escalation else 0,
                escalation_probability=float(typed_action.p_escalation),
                violation_type=decision.violation_type,
                reward=float(rewards[agent]),
                info={"action_index": action_index},
            )
            step_records.append(rec)

        self.episode_records.extend(step_records)
        state.step += 1

        done = state.is_success() or state.halted
        truncated = state.step >= state.max_steps and not done
        if done:
            for agent in self.agents:
                rewards[agent] += 1.0
        if truncated:
            for agent in self.agents:
                rewards[agent] -= 0.30

        self.total_reward += sum(rewards.values()) / max(1, len(rewards))
        for agent in self.agents:
            terminations[agent] = done
            truncations[agent] = truncated

        if done or truncated:
            self.last_summary = EpisodeSummary(
                scenario_id=state.scenario.scenario_id,
                scenario_type=state.scenario.scenario_type.value,
                mode=self.mode_name,
                success=state.is_success(),
                steps=state.step,
                active_agents=list(self.agents),
                required_agents=list(state.scenario.required_services),
                total_reward=self.total_reward,
                records=list(self.episode_records),
            )

        return self._observations(), rewards, terminations, truncations, infos

    @property
    def mode_name(self) -> str:
        guard = "governed" if self.config.governed else "unguarded"
        return f"{self.config.activation_mode}_{guard}"

    def global_state_vector(self) -> np.ndarray:
        if self.state is None:
            raise RuntimeError("environment is not initialized")
        return np.asarray(self.state.global_observation(), dtype=np.float32)

    def _observations(self) -> Dict[str, np.ndarray]:
        if self.state is None:
            return {}
        return {
            agent: np.asarray(self.state.local_observation(agent if agent != "DirectController" else "TrafficAgent"), dtype=np.float32)
            for agent in self.agents
        }

    def _infos(self) -> Dict[str, Dict[str, object]]:
        if self.state is None:
            return {}
        return {
            agent: {
                "scenario_id": self.state.scenario.scenario_id,
                "scenario_type": self.state.scenario.scenario_type.value,
                "active_agents": list(self.agents),
                "required_agents": list(self.state.scenario.required_services),
            }
            for agent in self.agents
        }

    def _action_from_index(self, agent: str, action_index: int) -> TypedAction:
        """Convert a discrete RL action into a typed action."""

        assert self.state is not None
        state = self.state
        common_target = self._default_target_for_scenario()
        refs: List[str] = []
        if state.evidence_verified:
            refs.append("verified_incident_report")
        if state.public_report_verified:
            refs.append("verified_public_report")

        if action_index == 0:
            action_type = ActionType.NOOP
            risk = RiskLevel.LOW
        elif action_index == 1:
            action_type = ActionType.QUERY_EVIDENCE
            risk = RiskLevel.LOW
        elif action_index == 2:
            action_type = ActionType.REQUEST_VERIFICATION
            risk = RiskLevel.LOW
        elif action_index == 3:
            action_type = ActionType.ESCALATE
            risk = RiskLevel.MEDIUM
        elif action_index == 4:
            action_type = ActionType.WRITE_MEMORY
            risk = RiskLevel.HIGH
        else:
            action_type, risk = self._role_specific_action(agent, action_index)

        payload = self._default_payload(action_type)
        escalation_requested = action_type == ActionType.ESCALATE
        p_esc = self._estimate_escalation_probability(action_type, risk)
        return TypedAction(
            role=agent,
            action_type=action_type,
            target=common_target,
            payload=payload,
            evidence_refs=refs,
            risk_level=risk,
            escalation_requested=escalation_requested,
            p_escalation=p_esc,
        )

    def _role_specific_action(self, agent: str, action_index: int) -> Tuple[ActionType, RiskLevel]:
        """Map role action slots to service-specific typed actions."""

        if agent == "DirectController":
            # The direct controller uses broad high-impact actions and therefore
            # tends to succeed quickly while producing poorer governance traces.
            mapping = {
                5: (ActionType.REROUTE_TRAFFIC, RiskLevel.MEDIUM),
                6: (ActionType.DISPATCH_AMBULANCE, RiskLevel.MEDIUM),
                7: (ActionType.BROADCAST_ALERT, RiskLevel.HIGH),
            }
            return mapping.get(action_index, (ActionType.NOOP, RiskLevel.LOW))

        role_actions = {
            "TrafficAgent": {
                5: (ActionType.REROUTE_TRAFFIC, RiskLevel.MEDIUM),
                6: (ActionType.OPEN_BUS_LANE, RiskLevel.HIGH),
                7: (ActionType.CHANGE_SIGNAL_PRIORITY, RiskLevel.MEDIUM),
            },
            "EmergencyAgent": {
                5: (ActionType.DISPATCH_AMBULANCE, RiskLevel.MEDIUM),
                6: (ActionType.CHANGE_SIGNAL_PRIORITY, RiskLevel.MEDIUM),
                7: (ActionType.ESCALATE, RiskLevel.HIGH),
            },
            "EnergyAgent": {
                5: (ActionType.RESTORE_POWER, RiskLevel.HIGH),
                6: (ActionType.ISOLATE_GRID_SEGMENT, RiskLevel.HIGH),
                7: (ActionType.DISPATCH_REPAIR_CREW, RiskLevel.MEDIUM),
            },
            "WaterAgent": {
                5: (ActionType.CLOSE_FLOODED_UNDERPASS, RiskLevel.HIGH),
                6: (ActionType.DISPATCH_REPAIR_CREW, RiskLevel.MEDIUM),
                7: (ActionType.QUERY_EVIDENCE, RiskLevel.LOW),
            },
            "PollutionAgent": {
                5: (ActionType.REDUCE_TRAFFIC_ZONE, RiskLevel.HIGH),
                6: (ActionType.QUERY_EVIDENCE, RiskLevel.LOW),
                7: (ActionType.SEND_TARGETED_NOTICE, RiskLevel.MEDIUM),
            },
            "PublicTransportAgent": {
                5: (ActionType.ADD_PUBLIC_TRANSPORT_CAPACITY, RiskLevel.MEDIUM),
                6: (ActionType.REROUTE_TRAFFIC, RiskLevel.MEDIUM),
                7: (ActionType.SEND_TARGETED_NOTICE, RiskLevel.MEDIUM),
            },
            "PublicWorksAgent": {
                5: (ActionType.DISPATCH_REPAIR_CREW, RiskLevel.MEDIUM),
                6: (ActionType.CLOSE_ROAD, RiskLevel.HIGH),
                7: (ActionType.WRITE_MEMORY, RiskLevel.HIGH),
            },
            "CitizenCommsAgent": {
                5: (ActionType.BROADCAST_ALERT, RiskLevel.HIGH),
                6: (ActionType.SEND_TARGETED_NOTICE, RiskLevel.MEDIUM),
                7: (ActionType.REQUEST_VERIFICATION, RiskLevel.LOW),
            },
        }
        return role_actions.get(agent, {}).get(action_index, (ActionType.NOOP, RiskLevel.LOW))

    def _default_payload(self, action_type: ActionType) -> Dict[str, object]:
        payload: Dict[str, object] = {}
        if action_type == ActionType.OPEN_BUS_LANE:
            payload["duration"] = 8
        if action_type == ActionType.WRITE_MEMORY:
            payload["claim"] = "incident state updated"
            # The expiration is omitted when evidence is weak to create an
            # observable unsupported-memory failure in unguarded traces.
            if self.state and self.state.evidence_verified:
                payload["expires_in_steps"] = 3
        return payload

    def _estimate_escalation_probability(self, action_type: ActionType, risk: RiskLevel) -> float:
        if action_type == ActionType.ESCALATE:
            return 0.95
        if risk == RiskLevel.HIGH:
            return 0.65
        if risk == RiskLevel.MEDIUM:
            return 0.25
        return 0.05

    def _default_target_for_scenario(self) -> str:
        assert self.state is not None
        stype = self.state.scenario.scenario_type
        if stype == ScenarioType.TRAFFIC_ACCIDENT:
            return "hospital_route"
        if stype == ScenarioType.POWER_OUTAGE:
            return "critical_district"
        if stype == ScenarioType.FLOODED_UNDERPASS:
            return "underpass_4"
        if stype == ScenarioType.POLLUTION_SPIKE:
            return "school_zone"
        return "city"

    def _apply_action(self, action: TypedAction) -> float:
        """Apply an allowed action and return shaping reward."""

        assert self.state is not None
        state = self.state
        reward = 0.0

        if action.action_type == ActionType.NOOP:
            return -0.01

        if action.action_type == ActionType.QUERY_EVIDENCE:
            # Querying improves evidence unless the scenario has conflicting
            # reports.  Conflicting evidence still helps less, which encourages
            # explicit verification and escalation.
            if state.scenario.evidence_quality != EvidenceQuality.CONFLICTING:
                state.evidence_verified = True
                reward += 0.10
            else:
                reward += 0.02
            return reward

        if action.action_type == ActionType.REQUEST_VERIFICATION:
            if state.scenario.evidence_quality in {EvidenceQuality.PARTIAL, EvidenceQuality.COMPLETE}:
                state.evidence_verified = True
                state.public_report_verified = True
                reward += 0.12
            return reward

        if action.action_type == ActionType.ESCALATE:
            if state.scenario.overseer_available:
                state.human_approval = True
                reward += 0.12
            else:
                reward -= 0.15
            return reward

        if action.action_type == ActionType.WRITE_MEMORY:
            state.memory_supported = bool(action.evidence_refs) and action.payload.get("expires_in_steps") is not None
            reward += 0.05 if state.memory_supported else -0.10
            return reward

        if action.action_type == ActionType.DISPATCH_AMBULANCE:
            state.ambulance_dispatched = True
            state.emergency_priority_active = True
            reward += 0.22

        elif action.action_type in {ActionType.REROUTE_TRAFFIC, ActionType.CHANGE_SIGNAL_PRIORITY}:
            state.route_secured = True
            reward += 0.18

        elif action.action_type == ActionType.OPEN_BUS_LANE:
            state.route_secured = True
            state.emergency_priority_active = True
            reward += 0.25

        elif action.action_type == ActionType.CLOSE_ROAD:
            state.route_secured = not state.scenario.hospital_access_risk or state.human_approval
            reward += 0.12 if state.route_secured else -0.18

        elif action.action_type == ActionType.RESTORE_POWER:
            state.power_restored = True
            reward += 0.28

        elif action.action_type == ActionType.ISOLATE_GRID_SEGMENT:
            state.power_restored = state.human_approval or state.evidence_verified
            reward += 0.16 if state.power_restored else -0.15

        elif action.action_type == ActionType.CLOSE_FLOODED_UNDERPASS:
            state.water_hazard_closed = True
            reward += 0.25

        elif action.action_type == ActionType.DISPATCH_REPAIR_CREW:
            state.repair_crew_dispatched = True
            if state.scenario.scenario_type == ScenarioType.POWER_OUTAGE:
                state.power_restored = True
            reward += 0.18

        elif action.action_type == ActionType.REDUCE_TRAFFIC_ZONE:
            state.pollution_mitigated = True
            reward += 0.25

        elif action.action_type == ActionType.ADD_PUBLIC_TRANSPORT_CAPACITY:
            state.transport_capacity_added = True
            reward += 0.20

        elif action.action_type in {ActionType.BROADCAST_ALERT, ActionType.SEND_TARGETED_NOTICE}:
            state.public_alert_sent = True
            reward += 0.10

        state.objective_progress = min(1.0, state.objective_progress + max(0.0, reward))
        return reward
