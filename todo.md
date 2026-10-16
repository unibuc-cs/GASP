# GASP → SEAMS 2027: plan and status

## Status (16 October 2026, evening)

Branch `main`, 45 tests pass, `make` in `paper/` builds the 10 page draft. In the paper: the deterministic results and four
local models in all five modes (Gemma 4 E4B, Glimmer 30B, gpt-oss-120b, and Qwen3.5-122B without reasoning, which came
from the rehearsal of the API path), sweeps for Glimmer and Qwen, and a rule-by-rule table of what the prompt leaks.
Missing: the two API models (optional now), the second domain with LLM roles, a reasoning-off control. 7 days left.

## What is left

Plan, in order; each step is a day or less on the two cards and goes into the paper the same day:

1. **Second domain with Glimmer** (next, about a night): `CONFIG=configs/llm_grid_local_ops.yaml`, pilot then M2–M4. Answers
   whether the leak follows the rule type (its counterpart rule is the full restart during a traffic spike) and turns the
   paper's future work into a result.
2. **Reasoning-off control** (a few hours): Gemma 4 E4B with thinking off, `CONFIG=configs/llm_grid_local_small_nothink.yaml`,
   M2–M4. Separates "the model" from "answering without reasoning" for the approval leak Qwen showed.
3. **API models** (group's call, about 120 USD, a few hours): `bash scripts/run_main_grid.sh` with the key; results land in
   `outputs/llm/M0`–`M4` and the "API:" red marks get filled. Without them the paper stands on four open-weight models.
4. **Fetch after each step**: `python scripts/fetch_outputs.py user@gpu-server`; tell me, I write it in.
5. **Final pass** (19–21 Oct): page budget (the body now ends exactly at the bottom of page 10), anonymity check, language.

Group also:

- [ ] Repository private or anonymous mirror before 23 Oct. HotCRP author data (names, affiliations, ORCIDs).

Me, as results arrive:

- [ ] Each run: tables, text, page budget. Red marks left: API models (seven) and the anonymous link.
- [ ] Artifact track description (2 pages) by 7 Dec.

## Dates

- Submission Fri 23 Oct 2026 AoE (https://seams27.hotcrp.com/): 10 pages + 2 of references, IEEEtran, double anonymous. Notification 3 Dec, revisions 5 Jan, camera ready 29 Jan. Artifact track: abstract 1 Dec, submission 7 Dec.
- 17–18 Oct: second domain and reasoning-off control on the two cards; a run not done by Mon 19 Oct stays out of this submission.
- 13–18 Oct: results text, full draft. 19–20 Oct: internal review. 21 Oct: anonymity and format check. 23 Oct: submit.

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
