"""Merge several run_grid output directories into one, so one report covers them.

    python -m gasp.experiments.merge_runs --runs "outputs/llm_local_pilot/M*" --out outputs/llm_local_pilot

Used when one run is split over several processes (one per mode or shard, one vLLM server each). Writes
episodes.csv and episodes.jsonl (concatenated), table_llm.md (recomputed over all rows), manifest.json (the first
manifest, with the episode count summed, the merged directories listed and the backend adaptations united) and
copies the trace files into traces/.  Analysis and paper tables read globs and need no merging; the pilot report
reads one directory, which is what this provides.
"""

from __future__ import annotations

import argparse
import glob
import json
import shutil
from pathlib import Path

from gasp.core.metrics import aggregate, markdown_table, write_csv
from gasp.experiments.analyze import read_rows
from gasp.experiments.run_grid import TABLE_COLUMNS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="glob of run directories, each with episodes.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    dirs = sorted(Path(d) for d in glob.glob(args.runs) if (Path(d) / "episodes.csv").exists())
    if not dirs:
        raise SystemExit(f"no run directory with episodes.csv matches {args.runs}")
    args.out.mkdir(parents=True, exist_ok=True)
    rows, jsonl, manifest, adaptations = [], [], None, {}
    for d in dirs:
        rows += read_rows(d / "episodes.csv")
        if (d / "episodes.jsonl").exists():
            jsonl += [ln for ln in (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
        if (d / "manifest.json").exists():
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            manifest = manifest or m
            for name, notes in m.get("backend_adaptations", {}).items():
                adaptations.setdefault(name, [])
                adaptations[name] += [n for n in notes if n not in adaptations[name]]
        traces = args.out / "traces"
        traces.mkdir(exist_ok=True)
        for t in (d / "traces").glob("*.jsonl") if (d / "traces").exists() else []:
            shutil.copy2(t, traces / t.name)
    write_csv(rows, args.out / "episodes.csv")
    (args.out / "episodes.jsonl").write_text("\n".join(jsonl) + "\n", encoding="utf-8")
    (args.out / "table_llm.md").write_text(markdown_table(aggregate(rows, ("model", "mode")), TABLE_COLUMNS, ("model", "mode")) + "\n",
                                           encoding="utf-8")
    if manifest:
        manifest["n_episodes"] = len(rows)
        manifest["modes"] = sorted({r["mode"] for r in rows})
        manifest["merged_from"] = [str(d) for d in dirs]
        manifest["backend_adaptations"] = adaptations
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"merged {len(dirs)} runs, {len(rows)} episodes -> {args.out}")


if __name__ == "__main__":
    main()
