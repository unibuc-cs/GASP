"""Give a finished run directory a new model name, merging the entries it contains into one model.

Used for the rehearsal of the API path (configs/mimic): its two entries `sol` and `luna` were the same local model with
the same settings, so their episodes are ten repeats of one model and must appear in the paper under that model's name.

    python scripts/relabel_runs.py outputs/llm/M2 outputs/llm/qwen122b_M2 --model qwen122b --offset luna=5
    python scripts/relabel_runs.py outputs/llm_sens/R1 outputs/llm_sens/qwen122b_R1 --model qwen122b

Writes DEST with episodes.csv, episodes.jsonl, manifest.json and the traces renamed (`<model>__<mode>__<scenario>__r<k>.jsonl`);
--offset NAME=K adds K to the repeat numbers of entry NAME so repeats stay distinct. SRC is left as it is.
"""
import argparse
import csv
import json
import os
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dest")
    ap.add_argument("--model", required=True, help="the new model name")
    ap.add_argument("--offset", action="append", default=[], help="NAME=K: add K to the repeats of entry NAME")
    a = ap.parse_args()
    offsets = {kv.split("=")[0]: int(kv.split("=")[1]) for kv in a.offset}
    if os.path.exists(a.dest):
        raise SystemExit(f"{a.dest} exists; remove it first")
    os.makedirs(os.path.join(a.dest, "traces"))

    rows = list(csv.DictReader(open(os.path.join(a.src, "episodes.csv"), newline="", encoding="utf-8")))
    seen = set()
    for r in rows:
        old_model, old_rep = r["model"], int(r["repeat"])
        new_rep = old_rep + offsets.get(old_model, 0)
        key = (r["mode"], r["scenario_id"], new_rep)
        if key in seen:
            raise SystemExit(f"repeat collision for {key}: give the entries different --offset values")
        seen.add(key)
        src_trace = os.path.join(a.src, "traces", f"{old_model}__{r['mode']}__{r['scenario_id']}__r{old_rep}.jsonl")
        dst_trace = os.path.join(a.dest, "traces", f"{a.model}__{r['mode']}__{r['scenario_id']}__r{new_rep}.jsonl")
        if os.path.exists(src_trace):
            with open(src_trace, encoding="utf-8") as f, open(dst_trace, "w", encoding="utf-8") as g:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        d["model"] = a.model
                        d["repeat"] = new_rep
                        g.write(json.dumps(d) + "\n")
        r["model"], r["repeat"] = a.model, str(new_rep)
    with open(os.path.join(a.dest, "episodes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    jl = os.path.join(a.src, "episodes.jsonl")
    if os.path.exists(jl):
        with open(jl, encoding="utf-8") as f, open(os.path.join(a.dest, "episodes.jsonl"), "w", encoding="utf-8") as g:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    d["repeat"] = int(d["repeat"]) + offsets.get(d["model"], 0)
                    d["model"] = a.model
                    g.write(json.dumps(d) + "\n")
    mp = os.path.join(a.src, "manifest.json")
    if os.path.exists(mp):
        man = json.load(open(mp, encoding="utf-8"))
        entries = man.get("config", {}).get("models", [])
        man["relabelled"] = {"from": [e.get("name") for e in entries], "to": a.model, "repeat_offsets": offsets,
                             "note": "entries with identical settings merged into one model"}
        for e in entries:
            e["name"] = a.model
        json.dump(man, open(os.path.join(a.dest, "manifest.json"), "w", encoding="utf-8"), indent=1)
    for extra in ("table_llm.md",):
        if os.path.exists(os.path.join(a.src, extra)):
            shutil.copy2(os.path.join(a.src, extra), os.path.join(a.dest, extra))
    print(f"{a.dest}: {len(rows)} episodes as model {a.model}, repeats {min(int(r['repeat']) for r in rows)}-{max(int(r['repeat']) for r in rows)}")


if __name__ == "__main__":
    main()
