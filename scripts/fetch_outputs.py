"""Bring every result from the GPU server into this repository's outputs/ folder, in one go. Run it on the PC after each turn:

    python scripts/fetch_outputs.py user@gpu-server            # the repository is ~/GASP on the server
    python scripts/fetch_outputs.py user@gpu-server work/GASP  # elsewhere: its path on the server (no spaces)
    python scripts/fetch_outputs.py user@gpu-server --no-traces   # skip the traces (large; needed once, at the end)

It packs outputs/llm, outputs/llm_sens, the statistics, pilot and log files on the server, copies the pack with scp,
unpacks it here at the right place (outputs/llm/..., never outputs/outputs/...) and prints what is there now.
Needs ssh and scp on the PC (Windows 10 and later have them); it asks for the password like ssh does.
"""
import csv
import glob
import os
import subprocess
import sys
import tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACK = "outputs/gasp_outputs.tgz"      # on the server, inside the repository (git ignores it)
WANTED = "outputs/llm outputs/llm_sens outputs/llm_*_stats outputs/llm_local_pilot* outputs/*.log"


def run(args):
    r = subprocess.run(args)
    if r.returncode != 0:
        sys.exit(f"{args[0]} failed (exit code {r.returncode}); nothing to pack, wrong path on the server, or no connection")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    server, remote = args[0], (args[1] if len(args) > 1 else "GASP")
    exclude = "--exclude=traces " if "--no-traces" in sys.argv else ""
    pack_cmd = f"cd {remote} && ls -d {WANTED} 2>/dev/null | tee /dev/stderr | tar czf {PACK} {exclude}-T - && du -h {PACK}"
    print(f"packing on {server} (in {remote}):", flush=True)
    run(["ssh", server, pack_cmd])
    local_pack = os.path.join(ROOT, "outputs", "gasp_outputs.tgz")
    os.makedirs(os.path.dirname(local_pack), exist_ok=True)
    print("copying ...", flush=True)
    run(["scp", "-q", f"{server}:{remote}/{PACK}", local_pack])
    print("unpacking ...", flush=True)
    with tarfile.open(local_pack) as tar:
        try:
            tar.extractall(ROOT, filter="data")
        except TypeError:          # Python before the filter argument
            tar.extractall(ROOT)
    os.remove(local_pack)
    report()


def report():
    """One line per run group: episodes finished, over how many shard directories."""
    groups = {}
    for d in sorted(glob.glob(os.path.join(ROOT, "outputs", "llm", "*")) + glob.glob(os.path.join(ROOT, "outputs", "llm_sens", "*"))):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        key = name.rsplit("_s", 1)[0] if "_s" in name and name.rsplit("_s", 1)[1].isdigit() else name
        key = os.path.basename(os.path.dirname(d)) + "/" + key
        n = 0
        path = os.path.join(d, "episodes.csv")
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                n = sum(1 for _ in csv.DictReader(f))
        elif os.path.exists(os.path.join(d, "episodes.jsonl")):
            with open(os.path.join(d, "episodes.jsonl"), encoding="utf-8") as f:
                n = sum(1 for line in f if line.strip())
        dirs, eps = groups.get(key, (0, 0))
        groups[key] = (dirs + 1, eps + n)
    print("now in outputs/ (episodes finished / shard directories):")
    for key, (dirs, eps) in groups.items():
        print(f"  {key:28s} {eps:5d} episodes in {dirs} directories")
    if not groups:
        print("  nothing yet")


if __name__ == "__main__":
    main()
