# Background: why SEAMS, what the ESEM reviews said, what the old code showed

Written 23 September 2026, when the rework started. The paper "Governed Agent Societies: A Reinforcement Learning View
of Agentic AI" was rejected at the ESEM 2026 Emerging Results and Vision track (reviews 281A, 281B, 281C), after an
earlier rejection at the SIGKDD 2026 Blue Sky track. The plan that followed from this analysis is `../todo.md`; the code
it produced is `../gasp/`.

## 1. Venue: SEAMS 2027, not AAMAS 2027

SEAMS 2027 (Software Engineering for Adaptive and Self-Managing Systems, with ICSE 2027, Dublin, 26–27 April 2027;
CORE A). Research track, full paper: 10 pages plus 2 of references, IEEE template, double anonymous. Dates, all AoE:
submission Friday 23 October 2026, notification 3 December, revised versions 5 January 2027, revision decisions 15
January, camera ready 29 January. Review criteria: novelty, relevance, soundness, presentation, verifiability. The call
names "LLM-based, agentic, and multi-agent self-adaptive systems", "human-in-the-loop, human-on-the-loop", "governance
challenges", "runtime assurance" and MAPE-K; the conference description names smart cities. Artifact track: abstract 1
December, submission 7 December (testbeds, trace datasets and frameworks are listed categories).

The paper fits without changing domain: the guard is a runtime assurance mechanism (Simplex, shields, runtime
enforcement); verifier, governor and overseer are the analyze and plan steps of a MAPE-K loop with a human on the loop;
the typed traces are its knowledge base; evidence quality, overseer availability and LLM nondeterminism are the
uncertainty sources SEAMS papers are built around. This answers reviewers A and C directly.

Why not AAMAS 2027: paper deadline 8 October 2026, too close for the rework; AAMAS reviewers would read the guard as
normative multi-agent systems and electronic institutions and the learning framing as shielded multi-agent RL, none of
which the paper cited; and the old environment could not carry a learning result, which an "RL view" paper would need
there. Fallbacks if SEAMS rejects: ACSOS 2027, ACM TAAS (SEAMS invites extended versions), AAMAS 2028.

## 2. What the reviews said once the venue mismatch is removed

Reviewers A and C rejected on scope: not an empirical software engineering paper, no SE venues in the reference list.
Fixed by the venue, the SE framing and SE citations.

Reviewer B's points hold at any venue and were correct: no statistics, intervals, repeats or sensitivity; scenario
generation undocumented; contribution type unclear (vision, results or framework); GAU weights, escalation probabilities
and RDC unspecified; weak external validity (symbolic scenarios, deterministic policies). The code inspection below
confirmed every one of them and added more.

## 3. What the old code showed

The public repository, run with `run_deterministic_baselines --episodes 80` (seed 11, as in the script), against the
paper's Table 3:

| Mode | Paper: Succ / Cost / Viol / Miss / Blocked / EscCE / TSC / GAU | Code, same order |
|---|---|---|
| B0 direct | 0.86 / 5.4 / 2.31 / 1.18 / 0.00 / 0.34 / 0.58 / 0.41 | 0.00 / 8.00 / 2.27 / 1.49 / 0.00 / 0.25 / 0.96 / 0.00 |
| B1 all, no guard | 0.88 / 7.2 / 1.76 / 0.94 / 0.00 / 0.29 / 0.64 / 0.48 | 1.00 / 2.00 / 1.59 / 1.04 / 0.00 / 0.22 / 0.93 / 0.61 |
| B2 activated, no guard | 0.90 / 5.9 / 1.29 / 0.71 / 0.00 / 0.23 / 0.69 / 0.56 | 1.00 / 2.00 / 1.59 / 1.04 / 0.00 / 0.22 / 0.93 / 0.61 |
| B3 activated, guarded | 0.87 / 6.4 / 0.18 / 0.11 / 1.36 / 0.09 / 0.91 / 0.78 | 0.91 / 2.70 / 0.75 / 0.00 / 2.24 / 0.23 / 0.92 / 0.80 |

Findings, in order of importance. The code behind Table 3 is not available (confirmed by the group), so the new paper
cites none of the old numbers; one script regenerates every number from scratch.

1. Table 3 does not come from this code.
2. The environment was solved in two steps: rule policies query evidence at step 0 and finish at step 1 in every
   unguarded mode, with a horizon of 8. Nothing long-horizon was exercised and "cost" carried no information.
3. B0 never succeeded: its action map lacked the power, water and pollution actions. B1 and B2 were identical on every
   metric, because inactive roles simply did nothing.
4. TSC and EscCE did not move between B2 and B3 (0.93 to 0.92; 0.22 to 0.23), yet the paper's claim rested on them
   moving. "Supported" was a state flag copied into every action, and the escalation probability was a constant per
   risk level, so EscCE measured the rule set, not the policy.
5. Activation precision and recall compared the activation policy with the lookup table that defined it: 1.0 by
   construction, against 0.84 and 0.91 in the paper.
6. GAU weights were hard coded and unstated; missed escalations were counted twice.
7. RDC was the share of positive-reward records of the busiest role, not a Shapley or counterfactual quantity.
8. Scenario families were sampled uniformly at random (18/21/21/20), not 20 per family as stated.
9. Guard-caught proposals were still counted as violations, mixing attempted with executed violations. Under a guard,
   executed violations must be zero by construction; the informative numbers are attempts and overseer load.
10. Two numbers already in the traces carried the thesis better than Table 3: the silent violation rate (successful
    episodes with at least one violation) was 1.00 in B2 and 0.52 in B3; overseer load was 1.81 escalations per
    episode in B3.

What changed in response is the current design: attempted and executed violations split; evidence as objects with ids,
visibility and status; a 16-step horizon with verification, approvals with latency and refusal, planted false reports
and hidden context; LLM-driven roles compared across five modes; paired statistics; the trust-adaptive governor; a
second domain on the same guard, traces and metrics. The old prototype is kept in `../legacy/`.

## 4. Anonymity

Double anonymous review: the GitHub repository name and the old "SmartCity-GASP-MARL" strings identify the group, so
the repository goes private before submission or the artifact goes through an anonymous mirror; any arXiv version
needs a different title; PDF metadata, acknowledgements and figshare or GitHub strings are checked before upload.
