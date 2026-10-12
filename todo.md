# GASP → SEAMS 2027: plan and status

## Status (12 October 2026)

Branch `main`, 45 tests pass, `make` in `paper/` builds the 10 page draft. Everything that does not depend on model runs
is written. In the paper: the deterministic results and Glimmer M0–M4. Missing: the Glimmer sweeps; gpt-oss-120b and
Gemma 4 (lab GPU, cards 0 and 1 only); the two API models. 11 days left.

## What is left

Group:

- [ ] Glimmer sweeps (`bash scripts/run_local_ablation.sh sens`, 640 episodes), then `python scripts/fetch_outputs.py user@gpu-server`. M0 and M1 are in the paper.
- [ ] gpt-oss-120b, then Gemma 4 E4B (turns 2 and 3), pilot first. After each turn: `python scripts/fetch_outputs.py user@gpu-server` on the PC.
- [ ] The two API models: pilot, then main grid (`scripts/run_pilot.sh`, `scripts/run_main_grid.sh`, about 120 USD), then the "API:" red marks in the paper, or hand the results back.
- [ ] Repository private or anonymous mirror before 23 Oct. HotCRP author data (names, affiliations, ORCIDs) by 16 Oct.

Me, as results arrive:

- [ ] Fill the red marks (sweeps, API models, anonymous link); one sentence per new model in the Models paragraph; the size comparison in RQ4.
- [ ] Keep 10 pages; anonymity check (names, repository strings, PDF metadata); last language pass.
- [ ] Artifact track description (2 pages) by 7 Dec.

## Dates

- Submission Fri 23 Oct 2026 AoE (https://seams27.hotcrp.com/): 10 pages + 2 of references, IEEEtran, double anonymous. Notification 3 Dec, revisions 5 Jan, camera ready 29 Jan. Artifact track: abstract 1 Dec, submission 7 Dec.
- 11–15 Oct: the three local turns, one model at a time. Proposal: a model not done by Sun 18 Oct stays out of this submission.
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
- 11 Oct: only cards 0 and 1 are ours now (the node still shows three): `GPU_IDS=0,1` on every serve command; local models in turns, one at a time (`RUNBOOK.md` section 7). `scripts/fetch_outputs.py` brings all results from the server in one go.
- 12 Oct: Glimmer M0 and M1 (480 episodes) in the paper. Without rules the roles break one in every second incident (114 pollution-zone reroutes, 12 alerts without approval); the prompt removes three quarters, the guard the rest. One agent with every tool keeps the rules about as well as the governed society (4 reroutes) but loses one traffic accident in three: it secures the route again and again and never sends the public notice. Eight red marks left: sweeps, API models, link.
