# Paper integration notes

## Suggested Methods wording

The prototype supports two policy classes.  The first uses deterministic role
policies to obtain reproducible baseline traces.  The second implements
trainable multi-agent policies with independent actors and either local or
centralized critics.  In the MAPPO-style condition, actors receive local
observations while the critic receives a global state vector.  Both policy
classes emit the same typed action records and are evaluated through the same
runtime guard and trace metrics.

## Suggested Evaluation wording

The evaluation should separate deterministic baselines from learned MARL modes.
The deterministic baselines isolate the effect of scenario-based role activation
and explicit governance.  The learned modes test whether the same environment
can support policy optimization under governance-aware transition dynamics.

Recommended table columns:

```text
Mode | Learned | Guard | Success | Cost | Viol. | Miss. esc. | Blocked | EscCE | TSC | GAU
```

Recommended learned modes:

```text
M0 Random policy
M1 IPPO unguarded
M2 MAPPO unguarded
M3 MAPPO governed
```

## Suggested limitation paragraph

The smart-city environment is symbolic and controlled.  It does not model real
traffic, legal procedure, infrastructure physics, or sensor uncertainty.  The
purpose is to evaluate whether typed traces and runtime governance expose
execution properties that are invisible in final-state success metrics.  The
learned policies should therefore be interpreted as preliminary evidence about
the framework, not as optimized smart-city controllers.

## Safe claim

The artifact instantiates governed simulation and trace-centric evaluation under
both deterministic and trainable multi-agent policies.  It does not yet implement
a full offline trace-optimization pipeline or a learned governance policy.
