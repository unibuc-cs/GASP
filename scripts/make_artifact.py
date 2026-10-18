"""Pack the anonymous artifact for the submission: code, configs, scenario sets, every episode table and manifest, the
statistics and the generated paper tables, in one zip without author names, affiliations or repository URLs.

    python scripts/make_artifact.py                      # dist/gasp-artifact.zip, without the trace files (small)
    python scripts/make_artifact.py --traces             # with the JSONL traces (large)
    python scripts/make_artifact.py --forbid "Some Name" # one more string that must not appear anywhere

Takes the tracked files (git ls-files) minus the internal ones (todo.md, notebooks/, legacy/), replaces the repository
URL and the copyright holder, adds outputs/paper*, outputs/llm*/ (episodes, manifests, stats, catalogue; traces on
request), writes ARTIFACT.md at the root and then scans every text file for the forbidden strings. Stops with exit code 1
and the list of files if one is found, so that nothing identifying can leave by accident.
"""
import argparse
import glob
import io
import os
import subprocess
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCLUDE_PREFIXES = ("todo.md", "notebooks/", "legacy/", ".sync/", ".github/", "scripts/make_artifact.py", "runs-", "HANDOFF.md")
REPLACE = {"unibuc-cs/GASP": "ANONYMIZED/GASP", "github.com/unibuc-cs": "github.com/ANONYMIZED",
           "Computer Science Department - University of Bucharest": "the authors"}
FORBID = ["unibuc", "bucharest", "stefanescu", "ilds.ro", "@gmail"]
RESULT_GLOBS = ["outputs/paper*/**/*", "outputs/llm*/**/episodes.csv", "outputs/llm*/**/episodes.jsonl", "outputs/llm*/**/manifest.json",
                "outputs/llm*/**/table_llm.md", "outputs/llm*/stats/*", "outputs/llm*/**/PILOT_REPORT.md", "outputs/llm/failure_catalogue.md"]
TEXT_EXT = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".tex", ".bib", ".sh", ".cmd", ".toml", ".cfg", ".ini", ".jsonl", ""}

ARTIFACT_MD = """# Artifact: Governed Agent Societies (anonymous)

Code, configurations, scenario sets, per-episode results, manifests and statistics behind every table of the paper.

- `gasp/` the testbed: core (evidence, actions, guard, traces, metrics), domains (smart city, software incident response),
  policies (procedural, naive, LLM), experiments (reproduction, grid runs, statistics, paper tables).
- `configs/` the rule sets and the LLM grid configurations that produced the runs.
- `outputs/paper/`, `outputs/paper_ops/` deterministic tables and the scenario sets (`scenarios.json`).
- `outputs/llm/<model>_<mode>_s<k>/` one directory per model, mode and shard: `episodes.csv` (one row per episode, every
  metric of the paper), `manifest.json` (code version, seed, configuration, served model) and, when included, `traces/`
  (one JSONL file per episode, one record per proposal). `outputs/llm_sens/` the sweeps over rule sets and human
  availability. `outputs/llm/stats/` the paired statistics.
- `paper/tables/` the generated LaTeX tables.

Reproduce: `pip install -r requirements.txt`, then `python -m gasp.experiments.reproduce --out outputs/paper` (deterministic
rows, seconds) and `cd paper && make sync` (every table and the statistics from `outputs/`). `RUNBOOK.md` and
`docs/` describe the LLM runs; `scripts/serve_local_model.sh` serves an open-weight model with vLLM and
`scripts/run_local_ablation.sh` runs the grid against it.

Run directory names: `local_*` is Glimmer (city); `gemma4_*`, `gptoss120b_*`, `qwen122b_*` the other models; `gemma4nt_*`
Gemma with reasoning off; `gemma4rp_*` and `qwen122brp_*` the reinforced prompt; `outputs/llm_sens/*_R1|R3|ov-always|ov-never_*`
the sweeps and `*_adaptive-t<th>_*` the trust-adaptive governor; `outputs/llm_ops/` the second domain and
`outputs/llm_ops_v1/` its first run, before the diagnosis role's visibility was corrected (see the paper, RQ5).

Notes. The Qwen3.5-122B runs were made under two entry names with identical settings and merged into one model of ten
repeats (`scripts/relabel_runs.py`; the manifests record it). Trace files are missing for the Glimmer M0, M1 and sweep
runs, which were lost in a copy error after their episode tables had been written; every episode table is complete.
"""


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f and not f.startswith(EXCLUDE_PREFIXES)]


def result_files(with_traces):
    files = set()
    for g in RESULT_GLOBS:
        for p in glob.glob(os.path.join(ROOT, g), recursive=True):
            if os.path.isfile(p):
                files.add(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    if with_traces:
        for p in glob.glob(os.path.join(ROOT, "outputs", "llm*", "*", "traces", "*.jsonl")):
            files.add(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    return sorted(f for f in files if "/mimic/" not in f and "/cache/" not in f)


def scrub(data: bytes) -> bytes:
    text = data.decode("utf-8")
    for a, b in REPLACE.items():
        text = text.replace(a, b)
    return text.encode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/gasp-artifact.zip")
    ap.add_argument("--traces", action="store_true", help="include the JSONL trace files (large)")
    ap.add_argument("--forbid", action="append", default=[], help="another string that must not appear (case-insensitive)")
    args = ap.parse_args()
    forbid = [f.lower() for f in FORBID + args.forbid]
    files = sorted(set(tracked_files()) | set(result_files(args.traces)))
    out = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    offending, n_text = [], 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ARTIFACT.md", ARTIFACT_MD)
        for f in files:
            path = os.path.join(ROOT, f)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                data = fh.read()
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                try:
                    data = scrub(data)
                    n_text += 1
                    low = data.decode("utf-8").lower()
                    hits = [s for s in forbid if s in low]
                    if hits:
                        offending.append((f, hits))
                except UnicodeDecodeError:
                    pass
            z.writestr(f, data)
    size = os.path.getsize(out) / 1e6
    print(f"{out}: {len(files)} files ({n_text} text files scanned), {size:.1f} MB" + (" with traces" if args.traces else ", no traces"))
    if offending:
        for f, hits in offending:
            print(f"  identifying text in {f}: {', '.join(hits)}")
        os.remove(out)
        sys.exit("the artifact was not written: remove the strings above (or add them to REPLACE) and run again")


if __name__ == "__main__":
    main()
