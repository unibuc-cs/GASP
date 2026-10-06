# Legacy prototype (ESEM 2026 version)

The code behind the ESEM 2026 submission, kept for reference. Nothing in the SEAMS 2027 paper uses it; the current
code is `gasp/` in the repository root. Known differences from the ESEM paper's Table 3 are listed in
`../docs/BACKGROUND.md`.

Contents: `smartcity_gasp/` (symbolic smart-city environment, typed traces, rule-based guard, deterministic baselines
B0–B3, small IPPO/MAPPO trainers), `configs/` (its experiment configs), `docs/` (the mapping between this code and
the ESEM paper), `outputs/results/` (sample outputs), `tests/` (two smoke tests).

Run from this folder:

```bash
cd legacy
python -m pytest tests -q
python -m smartcity_gasp.experiments.run_deterministic_baselines --episodes 80   # B0–B3 table into outputs/results
python -m smartcity_gasp.experiments.train_marl --algorithm mappo --governed --episodes 20 --eval-episodes 10   # needs torch
```
