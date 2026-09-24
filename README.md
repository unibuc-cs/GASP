# GASP: governed agent societies

Two code bases live here.

- `gasp/` (v2, current): evidence objects with ids and visibility, three rule sets, a runtime guard that
  separates attempted from executed violations, deterministic and LLM role policies, typed JSONL traces,
  trace metrics, paired statistics, role ablation. This is what the SEAMS 2027 submission uses.
- `smartcity_gasp/` (v1, legacy): the prototype behind the ESEM 2026 submission. Kept for reference only.

## v2 quick start

```bash
pip install -r requirements.txt
python -m pytest tests -q                                   # guard rules, invariants, LLM parsing
python -m gasp.experiments.reproduce --out outputs/paper    # every deterministic table, traces, manifest
python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm \
       --scenarios outputs/paper/scenarios.json --limit 2   # LLM pilot (needs API keys; resumable)
python -m gasp.experiments.analyze --episodes outputs/llm/episodes.csv --out outputs/llm/stats \
       --pairs M2:M3,M0:M3,M3:M4 --group model               # paired Wilcoxon, Cliff's delta, bootstrap CIs
```

Modes: M0 one agent with all tools and the rules in its prompt; M1 roles, no rules anywhere; M2 roles, rules
in prompts only; M3 roles, runtime guard, rules not in prompts; M4 rules in prompts and guard. The deterministic
reference rows (D0 to D6 in `reproduce.py`) mirror these with a naive brain (does not know the rules) and a
procedural brain (follows them).

Rule sets are data: `configs/rules/R1.yaml` (lenient), `R2.yaml` (default), `R3.yaml` (strict).

Two domains implement the same interface (`gasp/domains/base.py`): `smartcity` (city operations centre) and `ops`
(software incident response). `--domain ops` on `reproduce.py` runs everything for the second domain; the guard,
traces, metrics, statistics and both deterministic brains are shared. See `RUNBOOK.md` for the LLM experiments
and `paper/` for the SEAMS draft (`make` builds it).

---

# v1 (legacy): SmartCity-GASP-MARL

This repository is a compact research demo for **Governed Agent Societies** in a
smart-city setting.  It implements a symbolic multi-agent environment, typed
action traces, runtime governance guards, deterministic baselines, and small
IPPO/MAPPO-style MARL trainers.

The demo is intentionally toy-sized.  It is not a realistic city simulator.  It
is designed to make the following paper concepts executable and inspectable:

- multi-role execution under partial observations;
- scenario-based role activation;
- typed action records instead of free-form control only;
- governance-aware transition dynamics;
- JSONL execution traces;
- trace-centric metrics such as TSC, EscCE, GAU, activation precision/recall,
  and a simple RDC proxy;
- deterministic and learned multi-agent policy modes.

## Project structure

```text
smartcity_gasp_marl/
  smartcity_gasp/
    core/          # state, scenarios, typed actions, governance, metrics, traces
    envs/          # PettingZoo-like parallel MARL environment
    policies/      # deterministic and random policies
    marl/          # compact PPO, IPPO, and MAPPO-style training utilities
    experiments/   # runnable scripts
  configs/         # example experiment configuration files
  docs/            # algorithm alignment and paper integration notes
  outputs/         # generated sample outputs
  tests/           # lightweight smoke tests
```

## Installation

The deterministic environment requires only Python and NumPy.

```bash
python -m pip install -r requirements.txt
```

For MARL training, install PyTorch as appropriate for your machine.  The code
will still run deterministic baselines if PyTorch is not available.

## Quick start

Run the deterministic baselines:

```bash
python -m smartcity_gasp.experiments.run_deterministic_baselines --episodes 20
```

Run a short MAPPO smoke training session:

```bash
python -m smartcity_gasp.experiments.train_marl --algorithm mappo --episodes 20 --eval-episodes 10
```

Run the governed MAPPO variant:

```bash
python -m smartcity_gasp.experiments.train_marl --algorithm mappo --governed --episodes 20 --eval-episodes 10
```

Run the compact end-to-end smoke suite:

```bash
python -m smartcity_gasp.experiments.evaluate_all --quick
```

## Execution modes

The deterministic experiment compares four modes:

| Mode | Meaning |
|---|---|
| B0 direct controller | A single direct controller acts without role activation or guard. |
| B1 all agents, no guard | All service agents act in every scenario; no governance guard. |
| B2 activated, no guard | Only scenario-relevant agents act; no governance guard. |
| B3 activated, governed | Scenario-relevant agents act; high-impact actions pass through the guard. |

The MARL experiment supports:

| Mode | Meaning |
|---|---|
| IPPO unguarded | Independent PPO-style actor/critic over local observations. |
| MAPPO unguarded | Local actor with centralized critic over global state. |
| MAPPO governed | Same centralized-critic setup, but actions pass through the guard. |

## Smart-city scenarios

Episodes sample one of four symbolic incident families:

1. traffic accident near a hospital;
2. power outage in a critical district;
3. flooded underpass;
4. pollution spike near a school.

Each scenario has severity, evidence quality, congestion, hospital-access risk,
pollution-zone status, power/water status, overseer availability, and a required
role set.

## Typed actions

RL policies output integer actions.  The environment converts each integer into
a typed action record before guard evaluation.  A trace entry therefore contains
fields such as:

```json
{
  "role": "TrafficAgent",
  "action_type": "open_bus_lane",
  "target": "hospital_route",
  "evidence_refs": ["verified_incident_report"],
  "risk_level": "high",
  "escalation_requested": false,
  "p_escalation": 0.65
}
```

## Governance rules

The current guard implements simple, inspectable rules:

- public alerts require verified evidence;
- bus-lane opening for longer than five minutes requires approval;
- road closure affecting hospital access requires escalation;
- memory writes require a source and an expiration condition;
- pollution-zone rerouting is sanitized unless emergency priority is active;
- inactive service roles are denied in governed execution.

## Outputs

Generated outputs are written under `outputs/results/`:

```text
deterministic_results.csv
deterministic_summary.md
deterministic_table.tex
example_trace.json
traces/*.jsonl
*_learning_curve.csv
*_results.csv
*_summary.md
*_table.tex
```

The JSONL traces are the most useful artifact for the paper: they show proposed
actions, evidence links, guard outcomes, violations, support annotations, and
reward signals.

## Notes for paper use

The code implements the governed simulation and trace-evaluation parts of the
paper algorithm directly.  The learning layer provides IPPO and MAPPO-style
policy training.  The centralized critic uses global state, while actors act
from local observations.  The verifier/governor are rule-based runtime guards in
this version, which keeps governance inspectable and avoids learning a black-box
safety policy before the trace metrics are validated.

See `docs/algorithm_alignment.md` and `docs/paper_integration_notes.md` for the
precise mapping between the code and the paper sections.
