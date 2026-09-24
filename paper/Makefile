# Build the paper. `make` syncs tables and figures from the experiment outputs (OUT, relative to the repo root)
# and builds main.pdf. Run from paper/.
OUT ?= outputs/paper

all: sync pdf

sync:
	cd .. && python -m gasp.experiments.paper_tables --paper-out $(OUT) --dest paper/tables
	cp ../$(OUT)/table_main.tex tables/table_main.tex
	cp ../$(OUT)/worked_example/worked_example.tex tables/worked_example.tex
	cp ../$(OUT)/adaptive/tradeoff_R3_15.png figures/tradeoff_R3_15.png
	cp ../outputs/paper_ops/table_main.tex tables/table_main_ops.tex
	# LLM results, when they exist (outputs/llm/*/episodes.csv from the grid runs)
	@if ls ../outputs/llm/*/episodes.csv > /dev/null 2>&1; then \
	  cd .. && python -m gasp.experiments.analyze --episodes "outputs/llm/*/episodes.csv" --out outputs/llm/stats --pairs M2:M3,M0:M3,M3:M4,M1:M2 --group model > /dev/null && \
	  python -m gasp.experiments.paper_llm_tables --episodes "outputs/llm/*/episodes.csv" --stats outputs/llm/stats/paired_stats.json --dest paper/tables && \
	  python -m gasp.experiments.paper_figures --episodes "outputs/llm/*/episodes.csv" --out paper/figures/llm_modes.png && \
	  python -m gasp.experiments.failure_catalogue --traces "outputs/llm/*/traces" --out outputs/llm/failure_catalogue.md > /dev/null; \
	else echo "no LLM results yet (outputs/llm/*/episodes.csv); skipping LLM tables"; fi

pdf:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /dev/null
	@pdfinfo main.pdf 2>/dev/null | grep Pages || true

clean:
	latexmk -C main.tex
