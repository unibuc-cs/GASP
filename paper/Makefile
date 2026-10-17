# Build the paper. `make` syncs tables and figures from the experiment outputs (OUT, relative to the repo root)
# and builds main.pdf. Run from paper/.
OUT ?= outputs/paper

all: sync pdf

sync:
	cd .. && python -m gasp.experiments.paper_tables --paper-out $(OUT) --dest paper/tables
	# the city domain: the rows the text discusses (single agent, naive society with and without the guard, compliant society)
	grep -v '^D0g \|^D1 \|^D1g \|^D6g ' ../$(OUT)/table_main.tex > tables/table_main.tex
	cp ../$(OUT)/worked_example/worked_example.tex tables/worked_example.tex
	cd .. && python -m gasp.experiments.paper_adaptive_figure --out paper/figures/tradeoff_R3_15.png > /dev/null   # LLM line added when the adaptive sweep exists
	# the second domain: only the rows the text discusses (single agent, naive society with and without the guard, compliant society)
	grep -v '^D0g \|^D1 \|^D1g \|^D6g ' ../outputs/paper_ops/table_main.tex > tables/table_main_ops.tex
	# LLM results, when they exist (outputs/llm/*/episodes.csv from the grid runs); the API models sol and luna get empty red rows until they run
	@if ls ../outputs/llm/*/episodes.csv > /dev/null 2>&1; then \
	  cd .. && python -m gasp.experiments.analyze --episodes "outputs/llm/*/episodes.csv" --out outputs/llm/stats --pairs M2:M3,M2:M4,M3:M4,M0:M3,M1:M2,M1:M3 --group model > /dev/null && \
	  python -m gasp.experiments.paper_llm_tables --episodes "outputs/llm/*/episodes.csv" --stats outputs/llm/stats/paired_stats.json --sens "outputs/llm_sens/*/episodes.csv" --skip-tag ov-always --skip-tag R1 --placeholder sol --placeholder luna --control gemma4nt=gemma4 --control gemma4rp=gemma4 --control qwen122brp=qwen122b --dest paper/tables && \
	  python -m gasp.experiments.paper_figures --episodes "outputs/llm/*/episodes.csv" --out paper/figures/llm_modes.png && \
	  python -m gasp.experiments.paper_rule_table --runs "outputs/llm/*" --dest paper/tables && \
	  python -m gasp.experiments.paper_strata_table --episodes "outputs/llm/*/episodes.csv" --scenarios outputs/paper/scenarios.json --skip gemma4nt --skip gemma4rp --skip qwen122brp --dest paper/tables && \
	  python -m gasp.experiments.failure_catalogue --traces "outputs/llm/*/traces" --out outputs/llm/failure_catalogue.md > /dev/null; \
	else echo "no LLM results yet (outputs/llm/*/episodes.csv); skipping LLM tables"; fi
	# LLM roles in the second domain (outputs/llm_ops), when they exist: tables/ops/table_llm_main.tex and table_llm_stats.tex
	@if ls ../outputs/llm_ops/*/episodes.csv > /dev/null 2>&1; then \
	  cd .. && python -m gasp.experiments.analyze --episodes "outputs/llm_ops/*/episodes.csv" --out outputs/llm_ops/stats --pairs M2:M3,M2:M4,M3:M4 --group model > /dev/null && \
	  python -m gasp.experiments.paper_llm_tables --episodes "outputs/llm_ops/*/episodes.csv" --stats outputs/llm_ops/stats/paired_stats.json --dest paper/tables/ops; \
	else echo "no LLM results in the second domain yet (outputs/llm_ops/*/episodes.csv)"; fi

pdf:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /dev/null
	@pdfinfo main.pdf 2>/dev/null | grep Pages || true

clean:
	latexmk -C main.tex
