# GASP → SEAMS 2027: plan and status

## 0. Status (6 October 2026)

Branch `main`, 45 tests pass, `make` in `paper/` builds the 8 page draft. Code, tests, scripts, documents and
every part of the paper that does not depend on model runs are done. Nothing from the model runs has arrived yet: not
the pilot, not the main grid. Seventeen days to the deadline; the model runs are the critical path.

What is needed from the group, in order: (1) someone runs the pilot with an OpenAI key and sends the report and zip,
(2) the same person runs the main grid, (3) optionally the Glimmer run on the lab GPU, (4) the repository goes private
or an anonymous mirror is made before 23 October, (5) author data for HotCRP. The commands are in `README.md`; the
details in `RUNBOOK.md`.

## 1. Dates and format

- SEAMS 2027, with ICSE 2027, Dublin, 26–27 April 2027. CORE A. Submission site https://seams27.hotcrp.com/, ORCID for every author.
- Submission Fri 23 Oct 2026 AoE (no abstract deadline) · notification 3 Dec · revised versions 5 Jan 2027 · revision decisions 15 Jan · camera ready 29 Jan.
- 10 pages plus 2 of references, IEEEtran 10pt conference; desk reject on format violations. Double anonymous: no names, prior work in third person, anonymized supplementary material, different title for any arXiv version.
- Review criteria: novelty, relevance, soundness, presentation, verifiability.
- Artifact track: abstract 1 Dec, submission 7 Dec 2026; a 2 page description can accompany the paper.

## 2. What is built

- Environment (`gasp/core`, `gasp/domains`): evidence objects with id, topic, status and visibility per role; verification by topic with forwarded requests; memory notes that inherit their source's status; approvals with latency, refusal, hard and soft kinds, hidden context the human alone knows (15 % of scenarios); horizon 16; planted false reports (24 % of scenarios), distractors, four evidence qualities. Rule sets R1–R3 as YAML with a plain-language rendering for prompts. Two domains on one base class: smart city (8 roles, 4 incident families) and software incident response (7 roles, 4 families).
- Guard (`gasp/core/guard.py`): scope → memory provenance → public communication → evidence → approval → sanitize; outcomes allow, deny, sanitize, request evidence, escalate. Attempted and executed violations split; executed = 0 under the guard by construction and by test. Trust-adaptive governor (per role trust, delegated soft approvals) with its sweep.
- Policies (`gasp/policies`): procedural (follows the rules; reaches every goal with zero attempts), naive (ignores them, reacts to the guard), one-agent variants, LLM roles with two prompt variants, retry on invalid JSON. Backends: OpenAI-compatible (API or local vLLM; adapts to rejected parameters; extra request fields), Anthropic, mock, procedural JSON for dry runs.
- Metrics and statistics (`gasp/core/metrics.py`, `gasp/experiments/analyze.py`): success, steps, proposals, attempted and executed violations, missed approvals, overseer load, escalation precision and recall, Brier of the self-reported approval probability, TSC, hallucinated references, false alert, hidden harm, silent violation rate, formatting failures, tokens, GAU with stated weights and a weight grid. Paired Wilcoxon, Cliff's delta, 10k bootstrap intervals, Holm. RDC dropped from the paper (circular with our own success conditions); the ablation script stays in the artifact.
- Experiments (`gasp/experiments`): `reproduce.py` regenerates every deterministic table, trace and manifest in 8 seconds, both domains; `run_grid.py` runs models × modes × scenarios × repeats, resumable, with estimate, shard and sensitivity options; generators for the paper tables, the figure, the worked example, the failure catalogue and the pilot report. `make` in `paper/` pulls all of it into the PDF; the LLM parts switch on when `outputs/llm/*/episodes.csv` exists.
- Runs for the group: `scripts/run_pilot.sh`, `scripts/run_main_grid.sh` (modes in parallel; `sens` for the Luna sweeps), `scripts/serve_local_model.sh` and `scripts/run_local_ablation.sh` (Glimmer 30B on vLLM), a Colab notebook. Configs: `configs/llm_grid.yaml` (GPT-6 Sol, GPT-6 Luna; 5 repeats; R2; temperature 0.7), `llm_grid_local.yaml` (Glimmer; M2–M4; 3 repeats), `llm_grid_dryrun.yaml`.
- Paper (`paper/main.tex`): every section written except the LLM results; red marks only where numbers are missing (10 of them). Related work with SE venues, MAPE-K mapping, the executed-violation property, worked example from a real trace, feature and rules tables, architecture figure, adaptive governor trade-off, second domain results, threats. Bibliography checked; DOIs at camera ready.
- Documents: `README.md` (entry), `RUNBOOK.md`, `docs/RESULTS_GUIDE.md`, `docs/BACKGROUND.md`, this file. Legacy prototype moved to `legacy/`.

Deterministic reference results (R2, 80 scenarios): roles that ignore the rules resolve every incident in 1.25 steps with 2.1 executed violations, a false alert in 24 % of incidents and a silent violation rate of 1.00; under the guard the same roles still resolve every incident, in 4.5 steps, with 0 executed violations, 0 false alerts, 0.64 approval requests per incident and 3.9 blocked proposals. Under R3 with the human absent, success falls to 50 %. Delegating soft approvals to roles that earned trust removes the human load and the success loss but exposes every hidden context case.

## 3. Open items

Group:

- [ ] Pilot: `bash scripts/run_pilot.sh` (or the Colab notebook) with the key; send `PILOT_REPORT.md` and `llm_pilot.zip`. Overdue since 30 Sep; new target Thu 8 Oct.
- [ ] Main grid: `bash scripts/run_main_grid.sh`, then `bash scripts/run_main_grid.sh sens`; send `llm_results.zip`, `llm_sens.zip`, `llm_traces.zip`. Target Mon 12 Oct. About 120 USD.
- [ ] Optional: Glimmer on the lab GPU (`RUNBOOK.md` section 7); send `llm_local.zip` and `llm_local_traces.zip`. Target Wed 14 Oct.
- [ ] Repository private, or anonymous mirror, before 23 Oct.
- [ ] HotCRP: names, affiliations, ORCIDs, corresponding e-mail, by 16 Oct. Create the submission early.
- [ ] Decide on arXiv: nothing before notification, or a preprint with a different title.

Mine, once data arrives:

- [ ] Read the pilot report and traces; change the prompt or temperature once if a health check fails; record it in the paper.
- [ ] Results text for RQ1–RQ4 from `outputs/llm/stats`, the figure, the failure catalogue excerpts, the headline numbers in abstract, introduction and conclusion; the discussion paragraph on prompted against enforced rules; the Models paragraph and the threats sentence trimmed to the runs that were done.
- [ ] Page budget: 10 pages with the results in; cut the deterministic detail or move the ops feature table to the artifact if over.
- [ ] Anonymity check (names, repository strings, PDF metadata) and a last language pass.
- [ ] Artifact track description (2 pages) by 7 Dec.

Optional, if time and budget allow: LLM roles in the ops domain (about 6 USD on Luna); an LLM coordinator that chooses the active roles.

## 4. Timeline

- By Thu 8 Oct: pilot received and read.
- Fri 9 – Mon 12 Oct: main grid runs; sensitivity sweeps; Glimmer if the GPU is free.
- Tue 13 – Sun 18 Oct: results text, figures, failure catalogue, discussion; full draft at 10 pages.
- Mon 19 – Tue 20 Oct: internal review. Wed 21: anonymity and format check. Thu 22: buffer. Fri 23 Oct: submit.
- If the pilot slips past 12 Oct: run the main grid with 3 repeats instead of 5 (about 70 USD, two thirds of the time) and skip Glimmer.

## 5. Risks and fallbacks

- No model runs in time: the paper cannot be submitted as a results paper; the deterministic rows alone do not carry the thesis. This is the one risk that matters.
- LLM roles too weak (success collapses everywhere): one worked example per role in the prompt, or a shorter horizon; the mode comparison stays valid as long as every mode shares the policy.
- M2 already at zero executed violations: lean on robustness (Luna, Glimmer, R3, absent human) and on the cost side.
- Success drops a lot under the guard: report it as cost after checking against the procedural policy, which reaches 100 % with zero violations.
- Glimmer cannot follow the schema or run the testbed: a capability finding, kept out of the paired tests; drop its sentence from the paper.
- A reviewer finds the GitHub repository: private or mirror before submission.

## 6. Decisions taken

- Venue: SEAMS 2027 over AAMAS 2027 (23 Sep). Models: GPT-6 Sol and GPT-6 Luna through the OpenAI API, Glimmer 30B locally as the provider check (24 Sep, 25 Sep). Second domain in this submission with deterministic rows; LLM roles there only if budget allows. RDC removed. The ESEM code behind Table 3 is not available; the paper cites no old numbers. The pilot's thresholds and the target ranges are fixed before the runs (`docs/RESULTS_GUIDE.md`); prompts and temperature may change once after the pilot, recorded.

## 7. Running log

- 23 Sep: ESEM reviews analyzed; the public repository does not reproduce Table 3; venue decision.
- 24 Sep: `gasp/` v2 built on branch `seams2027` (environment, rules, guard, policies, LLM backends, metrics, statistics, reproduction script); second domain on a shared base; paper prose for every section except the LLM results; runbook and estimate mode (about 4,100 calls and 5.5M tokens per repeat); hidden context, soft and hard approvals, trust-adaptive governor and its sweep; worked example; prompt compaction (about 950 tokens per call). Findings while building: parallel roles make "steps" a poor cost measure, so proposals are reported too; the communication role needs a verified path to public facts (forwarded verification requests); a public message needs every citation verified; the guard must use catalogue risk levels, not the level a policy claims.
- 25 Sep: models fixed; pilot and grid scripts, Colab notebook, backend adaptation to rejected parameters; architecture figure; pilot report generator and example; LLM tables, figure and failure catalogue wired into the paper build; language pass; target results; one-page entry document; Glimmer 30B on vLLM over ssh (config, scripts, parser and backend changes, shard option).
- 6 Oct: work moves to `main` (the group pushed the branch; its one extra commit, the tracked PDF, is kept). Documents restructured: one entry point (`README.md`), one results guide, one background note; legacy prototype moved to `legacy/`; hidden harm added to the LLM table and the pilot checks; plan rewritten to the current state. No pilot received yet.
