# GASP → SEAMS 2027: plan and status

## 0. Status (6 October 2026)

Branch `main`, 45 tests pass, `make` in `paper/` builds the 8 page draft. Code, tests, scripts, documents and
every part of the paper that does not depend on model runs are done. The Glimmer run (M2–M4, 720 episodes) is in the paper; M0, M1 and the sweeps run next on the lab GPUs. The API models
have not been run; 14 days to the deadline.

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
- Paper (`paper/main.tex`): every section written except the LLM results; red marks only where numbers are missing (4 of them). Related work with SE venues, MAPE-K mapping, the executed-violation property, worked example from a real trace, feature and rules tables, architecture figure, adaptive governor trade-off, second domain results, threats. Bibliography checked; DOIs at camera ready.
- Documents: `README.md` (entry), `RUNBOOK.md`, `docs/RESULTS_GUIDE.md`, `docs/BACKGROUND.md`, this file. Legacy prototype moved to `legacy/`.

Deterministic reference results (R2, 80 scenarios): roles that ignore the rules resolve every incident in 1.25 steps with 2.1 executed violations, a false alert in 24 % of incidents and a silent violation rate of 1.00; under the guard the same roles still resolve every incident, in 4.5 steps, with 0 executed violations, 0 false alerts, 0.64 approval requests per incident and 3.9 blocked proposals. Under R3 with the human absent, success falls to 50 %. Delegating soft approvals to roles that earned trust removes the human load and the success loss but exposes every hidden context case.

## 3. Open items

Group:

- [ ] Pilot: `bash scripts/run_pilot.sh` (or the Colab notebook) with the key; send `PILOT_REPORT.md` and `llm_pilot.zip`. Overdue since 30 Sep; new target Thu 8 Oct.
- [ ] Main grid: `bash scripts/run_main_grid.sh`, then `bash scripts/run_main_grid.sh sens`; send `llm_results.zip`, `llm_sens.zip`, `llm_traces.zip`. Target Mon 12 Oct. About 120 USD.
- [x] Glimmer pilot (8 Oct) and full run M2–M4, 720 episodes (9 Oct): in the paper (Tables tab:llm, tab:llmstats, Figure fig:llm; RQ1–RQ4 text).
- [ ] Glimmer M0 and M1 (`MODES="M0 M1" bash scripts/run_local_ablation.sh`, 480 episodes), then the sweeps (`bash scripts/run_local_ablation.sh sens`, 640 episodes). Results come back through the folder.
- [ ] Repository private, or anonymous mirror, before 23 Oct.
- [ ] HotCRP: names, affiliations, ORCIDs, corresponding e-mail, by 16 Oct. Create the submission early.
- [ ] Decide on arXiv: nothing before notification, or a preprint with a different title.

Mine, once data arrives:

- [ ] Read the pilot report and traces; change the prompt or temperature once if a health check fails; record it in the paper.
- [x] Results text for RQ1–RQ3 and the family part of RQ4 from the Glimmer run; headline sentences in abstract and conclusion; failure catalogue extended with the mechanisms the traces show (executed violations by rule, unnecessary requests, approval lock-out, evidence loop, timeout).
- [ ] Add M0 and M1 to the LLM paragraphs; RQ4 from the sweeps; the discussion paragraph on prompted against enforced rules; the Models paragraph and the threats sentence trimmed to the runs that were done (API models: decide by 13 Oct whether anyone runs them; otherwise the paper is one open-weight model plus the deterministic reference and the second domain).
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
- 8 Oct: first attempt to serve Glimmer failed: the serve script named `Muse-Glimmer-30B-assistant`, which is the speculative decoding drafter head (5 GB, no tokenizer), not a chat model. Fixed: the script serves `meta-models/Muse-Glimmer-30B`; the reasoning level is set through the system prompt line from the model card (`Reasoning strength: low`) instead of a request field; the backend got a per-model system prompt prefix for that.
- 8 Oct (later): Glimmer runs at the model card's recommended reasoning level ("high"; decision by the group) with 4096 tokens per answer; the serve script detects the GPUs and starts one server per GPU, the ablation script spreads its processes over them (`--base-url` in `run_grid.py`). Commits carry no assistant attribution lines from here on, at the group's request.
- 8 Oct (later): the GPU node is three H100 80 GB: bf16, one server per card. Pilot runs one process per mode over the servers and `merge_runs.py` joins them for the report.
- 8 Oct (evening): Glimmer pilot done on three H100s, 24 episodes in 56 minutes. All health checks pass: formatting failures 0, hallucinated references 0, executed violations, false alerts and hidden harm 0 under the guard, success 0.88 in M2 and 1.00 in M3. Two observations. (1) M2 and M4 rows are identical to the token: each vLLM server samples from a fixed default seed and the two processes sent identical request sequences, and the guard never fired in M4 because the model attempted no violation when told the rules; in the full run the interleaved processes break this. (2) FLOO-001 (hospital access at risk, human unavailable): with the rules in its prompt the model asked for an approval the rules do not require for an underpass closure, the absent human counted as a refusal, and the model then refused to close for the rest of the episode, so the incident stayed open; without the rules (M3) it closed after one blocked attempt. Over-escalation as a cost of prompted rules; worth a paragraph if it recurs. Decision: full run as configured, no changes after the pilot.
- 9 Oct: full Glimmer run received through the folder (720 episodes, 10.9k calls, 24M tokens, one night on three H100s). Results: M2 executes 0.12 violations per incident, all pollution-zone reroutes (29 of 240 episodes), silent violation rate 0.11; M4 zero at no cost (success 0.96 both, same steps, requests, tokens); M3 zero at +4 steps, +50 % tokens, +0.22 requests, −0.07 success (Holm p 0.08). 64–71 % of the human's requests were not required by the rules (the model asks whenever hospital access is at risk). All 43 failures are timeouts: approval lock-outs (18 in M2/M4, same three scenarios every repeat; 8 in M3) and evidence loops of the communication role (17 in M3). No false alert, hidden harm, hallucinated reference or blocked loop anywhere. Paper: RQ1–RQ3 written, RQ4 partly, abstract and conclusion headline, tables and figure generated, all tables fitted to the page; 9 pages, 4 red marks left (M0/M1, sweeps, API models, anonymous link). Scripts: mode selection and sensitivity sweeps for the local runs.
