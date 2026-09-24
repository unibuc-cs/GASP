# GASP → SEAMS 2027: plan and todo

Status 2026-09-24 (evening). Target: SEAMS 2027 research track, full paper. Deadline Friday 23 October 2026 (AoE). 29 days.

## 0. Where things stand

Status 2026-09-24, late. Branch `seams2027`, 44 tests pass, `make` in `paper/` builds an 8 page draft.

Done since the last update:

- Second domain implemented: software incident response (`gasp/domains/ops.py`, 7 roles, 4 incident families) on a shared base class (`gasp/domains/base.py`); guard, traces, metrics, statistics and both deterministic brains unchanged. Same pattern as the city: naive roles unguarded execute 1.9 violations per incident, 23% false status page notices, 5% hidden harm; guarded: zero, 1.06 approval requests per incident. Tests run over both domains. RQ5 is back in the paper with its own table.
- Paper prose: abstract, introduction, related work, model, testbed (both domains), evaluation design, deterministic results, strict rules and absent human, adaptive governance, discussion, threats, conclusion. Red TODO markers remain only where LLM numbers go. Draft PDF: `gasp-seams2027-draft.pdf`.
- Rules table and scenario feature table generated from the YAML and the scenario set (`gasp/experiments/paper_tables.py`, part of `make sync`).
- LLM run preparation for the group: `RUNBOOK.md` (setup, estimate, pilot, main grid in parallel, sensitivity, statistics, what to hand back, what to do when it breaks). `--estimate` mode runs the whole grid with a compliant JSON-speaking policy and no API calls: 4,100 calls and 5.5M tokens per repeat for the five modes. Idle roles are no longer asked for actions, which cut calls by about a third with no change to any metric.
- Prompt: observation guide (how evidence, verification, notes, approvals and last_guard work), society and role descriptions supplied by the domain, prompt hashes in the manifest.
- Grid runner: `--rule-set`, `--overseer always|never`, `--tag`; analyzer accepts globs so parallel runs merge.
- Bibliography: author lists filled for every verified entry; only page numbers of the classic entries left to check.
- Trade-off figure labels fixed.

Waiting on the group (see section 17 for the exact list): model identifiers and who runs the grid, repository privacy, HotCRP author data, four design confirmations.

Next on my side without input: MAPE-K relabelling of the architecture figure; failure catalogue and worked example from LLM traces once they exist; numbers refresh if the scenario count changes; language pass.

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
- [ ] Models for the LLM roles: one frontier model through an API, one small open model on the local GPUs. Put the exact identifiers and the endpoint in `configs/llm_grid.yaml` (section 17 says what I need).
- [x] Second domain: implemented on 24 Sep with deterministic rows (section 10). Open: LLM roles in it too, if budget allows (about the same cost as the city grid).
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
- [x] Prompt hashes in the LLM manifest (per role and prompt variant).
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
- [ ] Pilot: 8 scenarios (`--limit 2`), all modes, one model. Runs on the group's machine; RUNBOOK.md section 3.
- [x] `--estimate` mode: the grid with a compliant JSON-speaking policy and no API calls, to size the budget.
- [x] Idle roles skipped (no call when a role has nothing left to do); metrics unchanged, calls down by about a third.
- [x] Observation guide in the system prompt; society and role texts come from the domain.
- [ ] Coordinator as an LLM that picks the active roles (only then measure activation precision and recall). Optional.
- [ ] Budget check after the pilot. Measured with the compliant policy: 4,100 calls and 5.5M tokens per repeat for 400 episodes (M0–M4); plan 1.5x for a real model, times 5 repeats: roughly 30k calls and 40M tokens per model, in the order of 150–200 USD for a frontier model.

## 6. Experiment matrix

Modes (in `run_grid.py`): M0 one agent, all tools, rules in prompt · M1 roles, no rules anywhere · M2 roles, rules in prompts only · M3 roles, guard, rules not in prompts · M4 rules in prompts and guard · M0g one agent with guard. Deterministic mirrors D0–D6 in `reproduce.py`.

- [x] Deterministic grid at R2 (10 modes), rule-set table (R1–R3), overseer sweep (R2 and R3, forced on and off), GAU weight grid.
- [ ] LLM pilot (group's machine, RUNBOOK.md).
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
- [x] Figure relabelled: only the two ends are annotated; the caption lists the thresholds.
- [ ] Paper text: present it as a measured trade-off, not a recommendation.

## 10. Second domain: software incident response (done)

- `gasp/domains/ops.py`: roles Monitor, Diagnoser, Deploy, Capacity, Dependency, Storage, Comms; families bad deploy, traffic spike, dependency outage, disk full; evidence health alerts, metrics, logs, deploy records, dependency status, disk usage, customer reports, a planted "data breach" post, a distractor warning.
- Correspondence with the city domain, written into the module docstring and the paper: rollback needs a verified failing health check; status page update declaring a major incident needs approval; scaling beyond 4 replicas is the bus lane; isolating a critical dependency the grid segment; a config change on a critical service the hospital road closure (hard approval); a full restart during a traffic spike is sanitized to a rolling restart.
- `gasp/domains/base.py` holds the shared actions, discovery, verification permission and idle logic; the city domain was moved onto it with identical results.
- [x] `python -m gasp.experiments.reproduce --domain ops --out outputs/paper_ops` produces the full table set; tests cover both domains.
- [ ] LLM roles in this domain (optional, same cost as the city grid): decide with the budget.
- [ ] Paper: one paragraph in the testbed section and one in the results are written; add the ops feature table to the appendix or artifact if space is short.

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
- [x] Author lists filled (Brorholt, Larsen, Schilling for compositional shielding; Li, Zhang, Li, Weyns, Jin, Tei for the SEAMS 2024 paper; Maia et al. for MAPER; Li, Adepu, Kang, Garlan for SEAMS 2020).
- [ ] Check page numbers of the classic entries (Kephart and Chess, Salehie and Tahvildari, Calinescu et al., Sha, Falcone et al., Esteva et al., Hübner et al.).
- [ ] Keep the agentic AI and MARL citations that still carry weight; drop padding surveys.

## 13. Artifact track (by 7 Dec)

- Two page description accompanying the research paper. Categories: testbed/exemplar, dataset (JSONL traces), framework.
- Contents already in place: environment, rule sets, prompts, scenario sets, traces, regeneration and analysis scripts, README with one-command reproduction, license, manifests.
- [ ] Abstract 1 Dec, submission 7 Dec 2026. DOI at camera ready.

## 14. Timeline

- Week 1, Thu 24 – Sun 27 Sep: decisions (section 2); ~~schema freeze; reproduction script; environment redesign; LLM wrapper~~ done 24 Sep; pilot as soon as keys exist.
- Week 2, Mon 28 Sep – Sun 4 Oct: group runs the pilot (by Tue 30 Sep) and the main grid (by Sun 5 Oct); ~~adaptive governor; observation trimming; IEEE skeleton; worked example; Sections 1–5 and the deterministic results~~ done 24 Sep; architecture figure relabelled.
- Week 3, Mon 5 – Sun 11 Oct: LLM results text and figures; sensitivity runs; failure catalogue; optional LLM roles in the ops domain.
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
- 2026-09-24 (late): second domain (software incident response) on a shared base class, same pattern as the city; paper prose for every section except the LLM results; rules and feature tables generated; runbook and estimate mode for the group's runs (about 4,100 calls and 5.5M tokens per repeat); idle roles skipped; bib authors filled. Draft PDF at 8 pages with placeholders.
- 2026-09-24 (later): hidden context and soft/hard approvals; trust-adaptive governor with delegated approvals and the sweep (R2/R3 × 5/15/30%); worked example script; prompt compaction (about 950 tokens per call); hidden context leak fixed; pending re-proposals no longer count as attempts; IEEE skeleton compiles. Finding: under strict rules, delegating soft approvals to roles that earned trust by compliance removes the human load and the success loss but exposes every hidden context case; the trade-off is close to linear in the delegated share.

## 17. Exactly what I need from the group

Each item: what, in which form, by when, and why.

1. **Model identifiers** (by Fri 27 Sep). For each of the two models: the exact API model string (for example the dated version string the API expects), the provider kind (`anthropic` or `openai`-compatible), and for the local model the served name and endpoint URL. Where: `configs/llm_grid.yaml`, or just send me the strings and I fill them in. Why: the paper names the models; the config drives every run.
2. **Who runs the LLM grid, and when** (by Fri 27 Sep). One person with the API key and access to the GPU box follows `RUNBOOK.md`: estimate (no cost), pilot (Tue 30 Sep), main grid (Sun 5 Oct), sensitivity (Wed 8 Oct). I do not need the key. What comes back to me: `episodes.csv`, `manifest.json`, `table_llm.md` per run directory, `stats/paired_stats.md`, and the traces as a zip. Everything else in the paper is written; the results paragraphs wait for these files.
3. **Repository** (by Fri 27 Sep). One of: (a) make `github.com/unibuc-cs/GASP` private until notification, or (b) keep it public and create an anonymous mirror for the submission (I prepare the export, someone with an account uploads to anonymous.4open.science). Also: merge branch `seams2027` from the zip (`git fetch <unzipped-path> seams2027`), or add the repository folder in the desktop app so I commit directly and stop sending zips.
4. **HotCRP data** (by Fri 10 Oct). Author names, affiliations, ORCIDs, one corresponding e-mail. The PDF stays anonymous; the form is not.
5. **Four design confirmations** (read the Testbed section of the draft, 10 minutes, by Fri 27 Sep). Say yes or what to change:
   - Verification is by topic; a role that cannot check an item forwards the request to one that can (this is how the communication role gets its evidence).
   - A public message must have every cited item verified, not just one.
   - Hidden context: in 15% of scenarios the human refuses soft approval requests for reasons the rules do not encode; acting without asking then counts as hidden harm. Soft approvals can be delegated by the adaptive governor; hard ones (hospital road closure, config change on a critical service) never.
   - The guard reads risk levels from the action catalogue, not from the proposal.
6. **Two small decisions** (whenever, before 12 Oct): drop RDC (my recommendation; the ablation only mirrors the success conditions) or keep it as a testbed description; LLM roles in the second domain too (same cost again) or deterministic rows only.
7. **The ESEM Table 3** (no deadline). Was it produced by a version of the code other than the public one? I need nothing else; the new paper cites none of the old numbers either way. If the figshare artifact differs from GitHub, keep it private.
