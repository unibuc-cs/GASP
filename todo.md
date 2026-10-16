# GASP → SEAMS 2027: plan and status

## Status (16 October 2026, night)

Branch `main`, 48 tests pass, `make` in `paper/` builds the 10 page draft. In the paper: the deterministic results, four
local models in all five modes (Gemma 4 E4B, Glimmer 30B, gpt-oss-120b, Qwen3.5-122B without reasoning), sweeps for
Glimmer and Qwen, a rule-by-rule table of what the prompt leaks. The two API models have empty red rows in Tables V and
VI until they run (they vanish by themselves when results exist). Body ends at the bottom of page 10: every new row or
sentence must be paid for with a cut. 7 days left.

## Plan to the submission

Each run goes into the paper the day it lands. A run not finished by Monday 19 Oct stays out.

| When | Who | What | Why a reviewer cares |
|---|---|---|---|
| 16–17 Oct (a night) | group, cards 0,1 | Glimmer in the second domain: `CONFIG=configs/llm_grid_local_ops.yaml`, pilot, then M2–M4 (`RUNBOOK.md` table) | RQ5 gets LLM evidence; shows whether the leak follows the rule type |
| 17 Oct (hours) | group | Gemma 4 E4B, reasoning off: `configs/llm_grid_local_small_nothink.yaml`, M2–M4 | separates "the model" from "no reasoning" in the Qwen approval leak |
| 17–18 Oct (1–3 h each, optional) | group | reinforced prompt, M2 only: `configs/llm_grid_local_small_reinforced.yaml` (same Gemma server), then `configs/llm_grid_local_qwen_reinforced.yaml` | answers "a better prompt would fix it": emphatic rules, repeated every step; leak still there or not, both are results |
| after each run | group | `python scripts/fetch_outputs.py user@gpu-server`, then tell me | |
| 17 Oct | me | text for each result; one related-work sentence (ToolEmu, AgentDojo) if a line can be found | |
| 18 Oct | me | anonymous artifact zip: `python scripts/make_artifact.py` (checks for names and URLs; `--traces` for the large one) and its README | verifiability criterion; the link in the paper |
| 19–20 Oct | me, then group reads | numbers audit (every number in the text against its file), language pass, RQ answers checked against the abstract | |
| 21 Oct | me | format and anonymity check: 10 + 2 pages, IEEEtran 10pt, PDF metadata, no author strings; red marks all gone or the sentence removed | desk reject risks |
| by 22 Oct | group | repository private or anonymous mirror (the artifact zip on an anonymous host, link in the paper); HotCRP author data; API models if the group still wants them (`RUNBOOK.md` section 5, about 120 USD, a few hours) | |
| 23 Oct AoE | group | submit at https://seams27.hotcrp.com/ | |

Artifact track description (2 pages) by 7 Dec.

## Dates

- Submission Fri 23 Oct 2026 AoE (https://seams27.hotcrp.com/): 10 pages + 2 of references, IEEEtran, double anonymous. Notification 3 Dec, revisions 5 Jan, camera ready 29 Jan. Artifact track: abstract 1 Dec, submission 7 Dec.

## Decisions

- SEAMS 2027 over AAMAS 2027. Models: GPT-6 Sol and Luna (API, run by the group), Glimmer 30B, gpt-oss-120b and Gemma 4 E4B (lab GPU). Glimmer at reasoning level "high" (model card). Second domain with deterministic rows only. RDC dropped. Health checks and target ranges fixed before the runs (`docs/RESULTS_GUIDE.md`); the Glimmer pilot passed and nothing was changed after it.
- Commits carry no assistant attribution lines. Small changes arrive as commits in the folder; the group pushes.

## Log

- 23 Sep: ESEM reviews analyzed; venue chosen.
- 24–25 Sep: code v2, paper prose, runbook, scripts, Glimmer support.
- 6 Oct: work on `main`; documents cut down to README, RUNBOOK, two guides and this file.
- 8 Oct: Glimmer served (the `-assistant` repository is only its drafter); pilot passed, 24 episodes in 56 minutes on three H100s.
- 9 Oct: Glimmer M2–M4 (720 episodes) in the paper: with the rules only in its prompt the model breaks one rule 0.12 times per incident; with the guard added none, at no cost; with the guard alone none, at a cost. Paper 10 pages, red marks only where data is missing.
- 10 Oct: scripts take any local model; configs for gpt-oss-120b and Gemma 4 E4B. The M0/M1 and sweeps command of 9 Oct did not run.
- 11 Oct: only cards 0 and 1 are ours now (the node still shows three): `GPU_IDS=0,1` on every serve command; local models in turns, one at a time (`RUNBOOK.md` section 2). `scripts/fetch_outputs.py` brings all results from the server in one go.
- 12 Oct: Glimmer M0 and M1 (480 episodes) in the paper. Without rules the roles break one in every second incident (114 pollution-zone reroutes, 12 alerts without approval); the prompt removes three quarters, the guard the rest. One agent with every tool keeps the rules about as well as the governed society (4 reroutes) but loses one traffic accident in three: it secures the route again and again and never sends the public notice. Eight red marks left: sweeps, API models, link. Found why the chained sweeps did not start: the run script killed its progress monitor and then waited on it, which under `set -e` ended the script before the statistics and before anything chained after it; fixed.
- 13 Oct: Glimmer sweeps (640 episodes) in the paper. R1 (no pollution rule): no violations in either mode. R3: prompted roles leak 3 reroutes but skip no approval, 86% success; guard alone 76%. Human never available (R2): guarded roles keep their success, prompted roles lose six points to approval lockouts. Seven API marks and the link left.
- 13 Oct (later): gpt-oss-120b M0–M4 (1,200 episodes) in the paper. Same leak as Glimmer (pollution-zone reroutes, 0.19 per incident in M2, zero in M4 at no cost); without rules it skips approvals (0.37 per incident) and hidden context harms 5% of incidents; the guard alone costs it human requests (0.97 against 0.54), not steps. Model names now printed as the paper writes them; paired statistics table compacted to one row per model and pair; the weight grid sentence now reports ties (Glimmer order holds in 216 settings, not 243 as printed before).
- 15 Oct: every file under `outputs` on the PC (and, by the group's report, the Gemma 4 results on the server) became empty during a copy; cause unknown, most likely PyCharm syncing the folder. Restored the PC from my copies: every episode table behind the paper is safe; traces survive only for Glimmer M2–M4 (the others were read for the paper but are gone). Gemma 4 runs again. Guards: `outputs` excluded from PyCharm deployment, a backup in `~/gasp_backups` after each run, the fetch never writes an empty file over one with content.
- 16 Oct: Gemma 4 E4B (1,200 episodes) in the paper. The prompt barely helps it (1.34 to 0.96 violations per incident, mostly pollution-zone reroutes); the guard brings it to zero at no cost over M2; the guard alone doubles the human's requests; as one agent it resolves 45% of the incidents. It fails a quarter of the incidents in M2 and M4, nearly all flooded underpasses: the communication role keeps asking to verify a report another role never checks. Size does not order the leak (0.96, 0.12, 0.19 for 4B, 30B, 120B). The run used three servers (ports 8000-8002), so three cards.
- 16 Oct (later): full review pass. Fixed: abstract said the naive roles broadcast a false alert in a quarter of the episodes with a false report (it is a quarter of all episodes, every one with such a report); the ops domain sentence read as if half of the violations were missed approvals (it is one missed approval every second incident); the formatting-failure range; several Glimmer-only claims (silent violations, hidden harm, false alerts, unnecessary requests) were stated as if for all models; lowercase venue names in four references. Rewritten for flow: results split into shorter paragraphs that give the three-model answer first, then detail; RQ1 reworded so the by-construction zero is not the question; RQ4 now covers incident families and evidence quality with numbers; the deterministic rows mapped to the modes; the single agent got its own discussion paragraph; trust-adaptive paragraph says that GAU would even prefer full delegation; threats note untuned prompts. Second-domain table reduced to the rows the text uses; artifact note folded into the conclusion. 10 pages, references from the bottom of page 10. Eight red marks left: API models and link.
- 16 Oct (evening): the rehearsal results (Qwen3.5-122B-A10B, fp8, thinking off, two identical entries named sol and luna) are in the paper as a fourth model, relabelled `qwen122b` with ten repeats; they are not the GPT-6 models. Found and fixed a metric gap: an action executed while its own approval request was still pending was labelled an approval violation but not counted as a missed approval; `scripts/recount_missed_approvals.py` corrected 391 episodes (mostly Qwen). Qwen leaks approvals through the prompt (0.49 per incident; 217 executed while pending, 130 hard road closures never asked, 106 of them with a rationale saying approval is required), so the guard costs it 14 points of success: the approvals it had skipped. New rule-by-rule table (`paper_rule_table.py`, from traces). LLM figure dropped for space; tables tightened; the "For engineers" paragraph folded into the recommendation. Second-domain config and run-script support, and a reasoning-off control config, ready for the server.
- 16 Oct (night): empty red rows for the two API models in the LLM tables (`--placeholder` in `paper_llm_tables.py`, wired in the Makefile; they disappear when results exist); the text was cut to keep the body on 10 pages. The Qwen passage now says that its prompt names the escalate action and shows the pending answer. Reinforced-prompt control ready (`prompt_variant: reinforced` in a config: emphatic rules paragraph and the rules repeated every step; two configs, M2 only). `scripts/make_artifact.py` packs the anonymous artifact and refuses to write it if a name or URL is left. Plan to the submission as a table above.
