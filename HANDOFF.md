# Handoff: GASP for SEAMS 2027 (state on 18 Oct 2026)

For the next assistant or person who continues this work. The paper is submission-ready except for the items under "Open".

## What this is

A SEAMS 2027 research-track submission (deadline Fri 23 Oct 2026 AoE, https://seams27.hotcrp.com/; 10 pages body + 2 of
references, IEEEtran 10pt, double anonymous). Paper: `paper/main.tex`, built with `make` in `paper/` (regenerates every table
and figure from `outputs/`, then the PDF). Current build: body ends at the bottom of page 10, references on page 11.
Every added sentence must be paid for with a cut.

## Where things are

- `todo.md`: status, plan table, dates, decisions, day-by-day log (the authoritative history). `RUNBOOK.md`: every
  operation on the GPU server and the PC. `docs/RESULTS_GUIDE.md`: what every number means.
- Code: `gasp/` (testbed, guard, metrics, policies, experiments); `scripts/` (serving, runs, fetch, relabel, recount, artifact).
- Results on the PC (`C:\Work\GASP\outputs`, git-ignored): `llm/` (city, all models and controls), `llm_sens/` (sweeps,
  adaptive governor), `llm_ops/` (second domain, Glimmer and gpt-oss-120b), `llm_ops_v1/` (first second-domain run,
  before the visibility fix), `paper/`, `paper_ops/` (deterministic). This repository copy has the episode tables but few
  trace files; traces are on the PC and in `~/gasp_backups` on the server.
- Paper tables are generated: `paper/Makefile` calls `paper_llm_tables.py` (main, stats, controls, placeholders),
  `paper_rule_table.py` (from traces; refuses to overwrite without traces), `paper_strata_table.py`, `paper_adaptive_figure.py`.
  `% NUM` comments in `main.tex` name the file each paragraph's numbers come from.

## Constraints that held for the whole project (keep them)

- The user pushes to GitHub (`unibuc-cs/GASP`, branch `main`) from `C:\Work\GASP`; the assistant cannot. Commits carry no
  assistant attribution lines. Code reaches the PC as a git bundle merged with `--ff-only`; the user's uncommitted edits
  (`scripts/run_main_grid.sh`, `run_pilot.sh`, `serve_local_model.sh`, `configs/mimic/`) must survive.
- GPU server: only cards 0 and 1 (`GPU_IDS=0,1`), one model at a time; no git there (PyCharm uploads code; `outputs`
  excluded from sync); results come to the PC with `python scripts/fetch_outputs.py user@gpu-server`.
- Writing rules from the user: concise, plain, human; no "we"; no meta-closing sentences; no promotional or vague wording;
  few hyphenated compounds; short section titles; hypotheses as "tested whether"; no "regime", "cell", "holds/carries".

## Open (in order)

1. Red marks in the PDF: seven `\todo{API: ...}` (two API models, GPT-6 Sol and Luna, never run; the group's call) and
   `\todo{anonymous link}`. If the API models are not run, delete the seven marks and the two placeholder rows
   (`--placeholder sol --placeholder luna` in `paper/Makefile`); the text already stands on four open-weight models.
   If they are run (`RUNBOOK.md` section 5), the rows fill themselves and each mark says which sentence to write.
2. Anonymous artifact: `python scripts/make_artifact.py --traces` on the PC writes `dist/gasp-artifact.zip` (refuses if a
   name or URL remains); upload it to an anonymous host and put the link where `\todo{anonymous link}` is. A version
   without traces (3.6 MB) was built on 18 Oct.
3. Repository private, or an anonymous mirror, before submission. HotCRP author data (names, affiliations, ORCIDs).
4. Final read by a human; `make` and check `pdfinfo` (Author/Title empty), 10 + 2 pages, no `??`.
5. After notification: artifact track description (2 pages) by 7 Dec 2026.

## Known weak points a reviewer may raise (stated in Threats, not changed)

Absence of the human counts as refusal and a refusal binds even for requests no rule required (the approval lockouts
follow from this). Sweeps and the adaptive run have one repeat; the adaptive governor ran with one LLM. The second domain
was corrected once (diagnosis role's visibility) and rerun; the first run is disclosed and kept.

## Numbers audit (18 Oct)

Every number in the text was checked against its source: episode tables, `outputs/llm/stats/paired_stats.json`,
`outputs/llm_ops/stats/`, `outputs/paper/*.md`, `outputs/paper/adaptive/table_adaptive.md`, and trace counts (Glimmer from
the traces here; the other models' trace counts from analyses run on the PC, `C:\Work\GASP\.sync\analyze_new.py`).
