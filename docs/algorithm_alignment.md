# Alignment with the GASP algorithm

This note maps the implementation to the updated paper algorithm.

## Implemented directly

| Paper concept | Code location | Notes |
|---|---|---|
| Global state `s_t` | `smartcity_gasp/core/state.py` | `CityState` stores scenario state, memory-like flags, active roles, progress, and governance context. |
| Local observations `o_t^(i)` | `CityState.local_observation()` | Each service agent receives a fixed local vector with role identity and partial scenario/state features. |
| Global critic observation | `CityState.global_observation()` | Used by MAPPO-style centralized critic. |
| Active role subset `I_t` | `smartcity_gasp/core/activation.py` | Scenario-based role activation implements role selection. |
| Typed actions `A_i` | `smartcity_gasp/core/actions.py` | Integer actions are converted into explicit `TypedAction` records. |
| Runtime guard `G(s_t,a_t,c_t)` | `smartcity_gasp/core/governance.py` | Rule-based guard returns allow, deny, request evidence, sanitize, or escalate. |
| Transition `T` | `SmartCityParallelEnv._apply_action()` | Applies allowed/transformed actions and updates symbolic city state. |
| Trace tuple `(s_t,a_t,e_t,chi_t)` | `smartcity_gasp/core/traces.py` | `TraceRecord` stores state snapshots, action, guard outcome, support, escalation, and violation labels. |
| Trace evaluator `Q_phi` | `smartcity_gasp/core/metrics.py` | Implemented first as deterministic trace metrics. |
| Governed simulation loop | `smartcity_gasp/envs/smartcity_parallel_env.py` | Parallel MARL environment executes agent actions and records traces. |
| IPPO/MAPPO training | `smartcity_gasp/marl/ppo.py` | Compact PPO implementation for local critics and centralized critics. |

## Implemented as a simplified prototype

The paper's trace-driven improvement stages include warm start, offline
optimization, and governed simulation.  This artifact implements governed
simulation and online PPO-style policy learning.  The warm-start and offline
optimization stages are represented by the interface and data artifacts rather
than a full imitation-learning pipeline.

The current `Q_phi` is a deterministic metric evaluator.  MAPPO uses a neural
centralized critic over the global state, but this critic is not yet trained to
predict the full trace metric vector.  This is a reasonable first implementation
for an Emerging Results paper because it keeps the governance measurements
interpretable.

## What is MARL in this artifact?

The MARL setting is concrete:

- each service role is an agent;
- agents act simultaneously through a parallel environment;
- actors observe local state;
- MAPPO's critic observes global state;
- rewards combine task progress, cost, violations, support, and escalation;
- governed runs alter transitions through the guard;
- all runs produce the same typed trace format.

## What remains future work?

- learned verifier/governor policies;
- imitation learning from curated traces;
- offline RL over stored compliant/non-compliant traces;
- counterfactual role removal by replaying episodes with one role disabled;
- LLM-driven policies that emit the same typed action interface.
