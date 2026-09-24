# GASP → SEAMS 2027: plan and todo

Status 2026-09-24 (evening). Target: SEAMS 2027 research track, full paper. Deadline Friday 23 October 2026 (AoE). 29 days.

## 0. Where things stand

Status 2026-09-24, end of day. Branch `seams2027`, package `gasp/`, 36 tests pass, `make` in `paper/` builds the IEEE skeleton.

Done today, first half: new environment, guard with attempted vs executed violations, deterministic policies, LLM role policy with backends, metrics, statistics, reproduction script (see sections 3–8).

Done today, second half:

- Hidden context: in 15% of scenarios the overseer knows something the rules do not encode and refuses soft approval requests; acting without asking then causes "hidden harm". New metric, new flag, new tests. Unguarded naive roles: hidden harm in 7% of episodes; guarded: 0.
- Soft vs hard approvals (road closures near a hospital are hard and never delegated).
- Trust-adaptive governor: per role trust carried across incidents, soft approvals delegated to trusted roles. Sweep over thresholds, rule sets and hidden context rates (5/15/30%), tables and figures in `outputs/paper/adaptive`. Result under R3: static guard costs 14% success when the human is unavailable and puts two requests per incident on the human; delegation removes both and exposes the system to every hidden context case (16% of episodes). Trust earned by compliance says nothing about what the rules do not encode.
- Worked example script: one trace to every metric, markdown and LaTeX (`gasp/experiments/worked_example.py`).
- Re-proposing while an approval is pending no longer counts as a violation attempt.
- Hidden context removed from observations (it had leaked); LLM prompt compacted: about 750 system + 200 observation tokens per call, so the main grid is about 25M tokens per model.
- GAU includes hidden harm; weight grid has 243 points.
- Paper skeleton: `paper/main.tex` (IEEEtran, all sections, RQs, contribution list, red TODO notes saying what goes where), `paper/references.bib` with the verified references, `paper/Makefile` that syncs tables and figures from the outputs and builds the PDF.

Needs the group (blocking):

- API keys and model names for the pilot (`configs/llm_grid.yaml`); the pilot is one command once keys exist.
- Owners for the writing and for the LLM runs.
- Repository privacy decision.

Next in line (no one blocked): prompt hashes in the manifest; redraw the trade-off figure for print; fill the three bib entries marked TODO; start writing Sections 3–5 from the skeleton notes; decide RDC.

## 1. Target and hard dates

- Venue: 22nd International Symposium on Software Engineering for Adaptive and Self-Managing Systems, Dublin, 26–27 April 2027, co-located with ICSE 2027. CORE A.
- Format: 10 pages of content + 2 pages of references, IEEE conference template (`\documentclass[10pt,conference]{IEEEtran}`). Strict, desk reject on format violations.
- Double anonymous: no author names, prior work in third person, anonymized supplementary material, different title for any arXiv preprint.
- Dates (all AoE): submission Fri 23 Oct 2026 (no abstract deadline) · notification Thu 3 Dec 2026 · revised versions Tue 5 Jan 2027 · revision decisions Fri 15 Jan · camera ready Fri 29 Jan.
- Review criteria to write against: novelty, relevance, soundness, presentation, verifiability ("does the paper support independent verification or replication").
- Submission site: https://seams27.hotcrp.com/. ORCID required for all authors.
- Artifact track: abstract 1 Dec, submission 7 Dec 2026. A 2 page description can accompany the research paper (categories: testbed/exemplar, dataset such as traces, framework).
- [ ] Create the HotCRP submission early; collect ORCIDs.
- [ ] Decide on arXiv: either no preprint before notification, or a preprint with a different title.

## 2. Decisions to lock by Fri 27 Sep

- [ ] Owners: (a) environment and role policies, (b) metrics and statistics, (c) writing, (d) artifact and reproduction script.
- [ ] Models for the LLM roles: one frontier model through the API, one small open model on the local GPUs. Put the names and the endpoint in `configs/llm_grid.yaml`.
- [ ] Second domain (incident response, section 10): decide on 10 Oct based on whether the smart-city grid is done. Not before.
- [x] Freeze the typed action schema and the trace record fields. Fields added: `evidence_refs` chosen by the policy, `needs_approval_prob`, `attempted_violation`, `executed_violation`, `refs_invalid`, `cited_false`, `off_target`, `formatting_failure`, token counts.
- [ ] Repository anonymity: make `github.com/unibuc-cs/GASP` private until notification, or submit through an anonymous mirror. The v1 name "SmartCity-GASP-MARL" is gone from the README header but still in the legacy code.
- [ ] Old numbers: find which code produced the ESEM Table 3 (figshare version?). The new paper uses only regenerated numbers whatever the answer.

## 3. Reproducibility and code hygiene

- [x] `python -m gasp.experiments.reproduce --out outputs/paper` regenerates scenarios, traces, per-episode CSV, main table (markdown and LaTeX), per-family table, rule-set table, overseer table, GAU weight grid, role ablation, manifest. Runs in 8 seconds.
- [x] Stratified scenario generation, exactly N per family, seed in the manifest, saved as `scenarios.json` and reused by the LLM grid.
- [x] Feature distribution table (`feature_table.json`), for the paper's scenario table.
- [x] Attempted vs executed violations split; tests assert executed = 0 under every rule set and both policy brains.
- [x] Guard unit tests: one per rule and outcome, plus unguarded labelling, reproducibility, solvability.
- [x] Manifest with git commit, Python version, seed, mode list, episode count; LLM manifest with config, temperature, repeats.
- [ ] Add prompt hashes to the LLM manifest.
- [x] Fix the legacy `.gitignore` (was UTF-16, so bytecode had been committed). Done on the branch.
- [ ] Check the main repository's `.gitignore` too when merging.

## 4. Environment redesign

- [x] Horizon 16 steps by default, configurable.
- [x] Evidence objects with id, topic, kind, status (unverified, verified, conflicting, refuted), hidden truth flag, visibility per role. E1 primary report, E3 congestion sensor, E4 public report (visible to communication only), E5 family-specific second item, F1 planted false report, D1 distractor.
- [x] Evidence quality: complete (E1 verified), partial (E1 unverified), missing (only the public report and the sensor exist; `query_evidence` on a topic finds the rest), conflicting (E1 plus a contradicting E2; verifying one resolves both).
- [x] Verification permission by topic: a role can only have facts checked on topics it works on. The communication role cannot verify field facts; `request_verification` on something it cannot check forwards the request to the roles that can, and they serve it when idle. Memory notes with a verified source are the other path.
- [x] False report in about 25% of scenarios; naive policies cite it, the guard blocks it (false alerts: 21–31% without guard, 0 with).
- [x] Partial observability through visibility lists; flags visible per role.
- [x] Overseer: availability (80%), latency 1–3 steps, denial of requests without verified evidence, denied stays denied for the episode. Approval keyed by action and target.
- [x] Distractor evidence and `off_target` labelling.
- [x] Rule sets as YAML (`configs/rules/R1.yaml`, `R2.yaml`, `R3.yaml`) with a plain-language rendering used in prompts.
- [x] Guard reads the action catalogue's risk level, never the level the policy claims (an LLM could under-declare).
- [x] Public communication rule: every cited item must be verified; a refuted citation makes any action unsupported.
- [x] Solvability: the procedural policy reaches 100% success with zero attempted violations on every scenario under R2 (existence proof; also a test).
- [ ] Sanity target changed: the deterministic policies reach 100% success in every R2 mode, so the governance cost in success shows only under R3 with the overseer unavailable (85%). Decide whether to make some approval-required actions fallback-free under R2 so the cost is visible there too, or leave it to the LLM runs. Suggestion: leave it; report R3 as the strict setting.
- [x] Trim the observation JSON: `allowed_actions` dropped from the user message (it is in the system prompt), compact JSON. About 200 tokens per observation now.
- [x] Hidden context: `params.hidden_denial` (15% by default, `hidden_denial_rate` option); the overseer refuses soft requests in those scenarios; never shown to policies.
- [x] Approval kinds: hard (road closure with hospital access at risk) and soft (everything else that needs approval).

## 5. Role policies

- [x] `LLMRolePolicy`: system prompt with job, allowed actions and their evidence topics, output schema; user message = observation JSON; one retry on invalid output; second failure = noop marked as formatting failure.
- [x] Two prompt variants (rules absent, rules included) driven by `include_rules`.
- [x] Backends: Anthropic SDK, OpenAI-compatible HTTP (works for vLLM, Ollama, OpenRouter), mock for tests. Exponential backoff on 429/5xx. Prompt cache for temperature 0 runs.
- [x] Token counts per call recorded in traces and per-episode rows.
- [x] Deterministic reference policies: naive and procedural brains; monolithic controller with either brain.
- [ ] Pilot: 8 scenarios (`--limit 2`), all modes, one model. Blocked on keys.
- [ ] Coordinator as an LLM that picks the active roles (only then measure activation precision and recall). Optional.
- [ ] Budget check after the pilot: about 24k calls per model for the main grid at 1.5k tokens each; confirm and scale.

## 6. Experiment matrix

Modes (in `run_grid.py`): M0 one agent, all tools, rules in prompt · M1 roles, no rules anywhere · M2 roles, rules in prompts only · M3 roles, guard, rules not in prompts · M4 rules in prompts and guard · M0g one agent with guard. Deterministic mirrors D0–D6 in `reproduce.py`.

- [x] Deterministic grid at R2 (10 modes), rule-set table (R1–R3), overseer sweep (R2 and R3, forced on and off), GAU weight grid.
- [ ] LLM pilot (blocked on keys).
- [ ] LLM main grid: models × M0–M4, 80 scenarios × 5 repeats.
- [ ] LLM sensitivity: M2 vs M3 under R1/R3 and overseer availability, small model only.
- [ ] Adaptive governor run (section 9).
- [ ] Second domain (section 10) if go on 10 Oct.

## 7. Metrics

- [x] Implemented in `gasp/core/metrics.py`: success, steps, proposals, attempted and executed violations (by type), missed approvals, unsupported memory writes, escalations, overseer load, approvals granted and denied, unnecessary share, escalation precision and recall, Brier score of `needs_approval_prob`, TSC on executed high-impact actions, hallucinated references, cited false evidence, false alert, unsupported alert, silent violation, off-target actions, formatting failures, tokens, GAU with stated weights (0.30 executed violation, 0.20 missed approval, 0.10 unsupported memory write, 0.10 step cost) and a 81-point weight grid.
- [x] RDC by role ablation (`gasp/experiments/ablation.py`).
- [ ] RDC finding: with the current success conditions the drop is 1.0 for every sole provider of an outcome flag, so RDC describes the task structure rather than the policy. Decide: drop it, or keep it as a testbed description. Suggestion: drop from the metrics table, mention once.
- [x] Worked example: `gasp/experiments/worked_example.py` picks the trace with the most distinct guard outcomes (or `--scenario`), writes the step table and the metric derivation as markdown and LaTeX. The LaTeX lands in the paper through `make sync`.
- [x] New metrics: hidden_harm, hidden_exposure, approvals_waived, approvals_delegated; GAU includes hidden harm (weight 0.30).
- [x] Pending re-proposals are waiting, not violation attempts; escalations count new requests only.
- [ ] Remove the old EscCE and activation precision/recall from the paper text.

## 8. Statistics

- [x] `gasp/experiments/analyze.py`: per-scenario aggregation over repeats, paired Wilcoxon (zsplit for zero differences), Cliff's delta, 10k-resample bootstrap CIs, Holm correction per pair, markdown and JSON output, `--group model`, `--filter rule_set=R2`.
- [x] Checked on the deterministic rows: naive roles guard vs no guard, executed violations −2.12 [−2.23, −2.02], δ = −1.00; steps +3.20 [2.94, 3.48]; overseer load +0.64 [0.50, 0.78].
- [ ] Decide the sample size after the pilot (80 scenarios unless CIs for success or overseer load are wider than about ±0.1; then 160).
- [ ] Figures: strip or box plots per mode and family (dataviz pass when the LLM data exists).

## 9. Self-adaptation element: trust-adaptive governor

- The governor keeps a per role trust score from recent supported actions and violations. Medium-risk actions require approval only while trust is below a threshold. Hard rules never relax.
- Output: executed violations against overseer load, static R1/R2/R3 vs adaptive, one Pareto plot.
- Threshold by sweep on a separate 20-scenario tuning set (seed different from the evaluation set).
- [x] Implemented inside guard and environment (`EnvConfig.adaptive_threshold`, trust carried across incidents, delegated approvals that never reach the human); sweep in `gasp/experiments/adaptive.py`; tests for hard vs soft, waiver only above threshold, harm only without human approval.
- [x] Sweep run for R2 and R3 at hidden context rates 5/15/30%. Tables in `outputs/paper/adaptive/table_adaptive.md`, figures `tradeoff_*.png`.
- [ ] Redraw the figure for print: one label per distinct point (thresholds 0.5–0.9 coincide for the naive brain).
- [ ] Paper text: present it as a measured trade-off, not a recommendation.

## 10. Optional second domain: incident response for a web service

- Roles: monitor, diagnoser, remediator, communicator, plus verifier, governor, overseer. Actions: query logs and metrics, restart service, roll back deployment, scale out, change config, update status page, write runbook memory, request verification, escalate. Rules: rollback needs a verified failing health check; status page update needs a verified incident; production config change needs approval; runbook writes need source and expiry; actions outside the affected service are denied. Families: bad deploy, traffic spike, dependency outage, disk full.
- The v2 layout makes this a new file in `gasp/domains/` implementing the same interface as `smartcity.py`; guard, traces, metrics and statistics are shared.
- [ ] Go or no-go on 10 Oct.

## 11. Paper (IEEE, 10 + 2 pages)

Working title (must differ from any arXiv title): "Governed Agent Societies: Runtime Governance and Trace-Based Assurance for LLM-Driven Multi-Agent Self-Adaptive Systems".

Research questions: RQ1 enforcement vs prompting (executed violations, missed approvals); RQ2 cost (success, steps, tokens, overseer load); RQ3 what final success hides (silent violation rate, unsupported actions, hallucinated evidence, false alerts); RQ4 robustness across models, evidence quality, overseer availability, rule strictness; RQ5 (if section 10) transfer to a software operations domain unchanged.

Section plan with page budget: 1 Introduction (1) · 2 Background and related work (1.25) · 3 Governed agent societies: model, MAPE-K mapping, guard semantics and rule language, the executed-violation property, trace schema (1.5) · 4 Testbed: society, scenario generator with distribution table, rule sets, LLM role policies (1.25) · 5 Evaluation design: modes, metrics with formulas, worked example, statistics (1) · 6 Results by RQ with intervals and per-family plots, sensitivity, adaptive governor, failure catalogue (2.5) · 7 Discussion: engineer's recipe, overseer load trade-off, threats to validity (0.75) · 8 Conclusion and artifact (0.25).

Things the testbed section must now explain (new since the ESEM version): evidence objects and statuses; verification permission by topic and forwarded requests; memory notes as evidence with inherited status; approval lifecycle (pending, approved, denied, latency); attempted vs executed violations; the guard using catalogue risk levels; public communication requiring every citation verified.

- [x] IEEE skeleton with section stubs, RQs, contribution list and red TODO notes (`paper/main.tex`; `make` builds it, `make sync` refreshes tables and figures from `outputs/paper`).
- [ ] Contribution statement: framework and evaluation paper; learning layer is future work; remove Listing 1's warm start and offline optimization.
- [ ] Related work with SE venue citations (section 12).
- [ ] Worked example table (section 7).
- [ ] Threats to validity.
- [ ] Check every point of ESEM reviewer B is answered: scenario generation (feature table), statistics (section 8), contribution type, metric definitions (section 7), external validity (LLM roles, second domain).
- [ ] Language pass with the project checklist (`claude/human-language-checklist.md`).
- [ ] Anonymity check: names, repo names, figshare and GitHub strings, acknowledgements, PDF metadata.
- [ ] IEEE template conversion; 10 pages; figures legible at print size.

## 12. Related work to add

Verified: AgentSpec (ICSE 2026, closest work: single agent, no roles, no human escalation as an outcome, no trace metrics) · Progent (2025) · GuardAgent (ICML 2025) · τ-bench (ICLR 2025) · Why Do Multi-Agent LLM Systems Fail? (NeurIPS 2025) · Safe Multi-Agent RL via Shielding (AAMAS 2021) · Compositional Shielding and RL for Multi-Agent Systems (AAMAS 2025) · Exploring the Potential of LLMs in Self-adaptive Systems (SEAMS 2024) · MAPER (SEAMS 2026) · Explanations for Human-on-the-loop (SEAMS 2020).

- [x] Entries drafted in `paper/references.bib` for all of the above.
- [ ] Fill the author lists marked TODO (compositional shielding AAMAS 2025; SEAMS 2024 LLM paper; MAPER) and check pages/DOIs of the classic entries.
- [ ] Keep the agentic AI and MARL citations that still carry weight; drop padding surveys.

## 13. Artifact track (by 7 Dec)

- Two page description accompanying the research paper. Categories: testbed/exemplar, dataset (JSONL traces), framework.
- Contents already in place: environment, rule sets, prompts, scenario sets, traces, regeneration and analysis scripts, README with one-command reproduction, license, manifests.
- [ ] Abstract 1 Dec, submission 7 Dec 2026. DOI at camera ready.

## 14. Timeline

- Week 1, Thu 24 – Sun 27 Sep: decisions (section 2); ~~schema freeze; reproduction script; environment redesign; LLM wrapper~~ done 24 Sep; pilot as soon as keys exist.
- Week 2, Mon 28 Sep – Sun 4 Oct: pilot and budget check; ~~adaptive governor; observation trimming; IEEE skeleton; worked example~~ done 24 Sep; write Sections 3–5 from the skeleton notes; redraw figures.
- Week 3, Mon 5 – Sun 11 Oct: main grid; statistics and figures; sensitivity; go or no-go on the second domain Fri 10 Oct.
- Week 4, Mon 12 – Sun 18 Oct: results text; full draft; related work; threats.
- Week 5, Mon 19 – Fri 23 Oct: internal review 19–20; anonymity and format check 21; buffer 22; submit Fri 23 Oct AoE.
- After: artifact description by 7 Dec; response letter and revision 3 Dec – 5 Jan if the decision is "revision".

## 15. Risks and fallbacks

- LLM roles too weak (success collapses everywhere): shorten the horizon or add one worked example per role to the prompt; the mode comparison stays valid as long as all modes share the policy.
- Cost or time: frontier model for the main grid only; small model for every sweep; `--limit` for pilots; runs are resumable.
- Success drops a lot under the guard: report it as cost; first check for rule bugs against the procedural policy, which reaches 100% with zero violations.
- The old table stays unexplained: the paper mentions no old numbers.
- Second domain not ready: revision round or future work.
- A reviewer finds the GitHub repository: make it private or use an anonymous mirror before submission.

## 16. Running log

- 2026-09-23: three ESEM reviews analyzed. Public repository run at 80 episodes does not reproduce the paper's Table 3. Venue decision: SEAMS 2027 (deadline 23 Oct) over AAMAS 2027 (deadline 8 Oct).
- 2026-09-24: plan created. Built `gasp/` v2 on branch `seams2027`: environment, rule sets, guard, deterministic policies, LLM policy and backends, metrics, statistics, ablation, reproduction script, 33 tests. First deterministic table produced. Findings while building: (1) with parallel roles, "steps" is a poor cost measure; report proposals too; (2) the communication role needs a verified path to public facts, so verification requests are forwarded to roles that can check them; (3) a public message must have every citation verified, otherwise a true and an untrue claim can go out together; (4) the guard must use catalogue risk levels; (5) under lenient rules a naive society can get stuck waiting for verification it never asks for, which the forwarding mechanism fixed; (6) RDC by ablation mostly reflects task structure.
- 2026-09-24 (later): hidden context and soft/hard approvals; trust-adaptive governor with delegated approvals and the sweep (R2/R3 × 5/15/30%); worked example script; prompt compaction (about 950 tokens per call); hidden context leak fixed; pending re-proposals no longer count as attempts; IEEE skeleton compiles. Finding: under strict rules, delegating soft approvals to roles that earned trust by compliance removes the human load and the success loss but exposes every hidden context case; the trade-off is close to linear in the delegated share.
