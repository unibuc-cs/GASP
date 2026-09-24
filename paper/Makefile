# Build the paper. `make` syncs tables and figures from the experiment outputs (OUT, relative to the repo root)
# and builds main.pdf. Run from paper/.
OUT ?= outputs/paper

all: sync pdf

sync:
	cd .. && python -m gasp.experiments.paper_tables --paper-out $(OUT) --dest paper/tables
	cp ../$(OUT)/table_main.tex tables/table_main.tex
	cp ../$(OUT)/worked_example/worked_example.tex tables/worked_example.tex
	cp ../$(OUT)/adaptive/tradeoff_R3_15.png figures/tradeoff_R3_15.png

pdf:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /dev/null
	@pdfinfo main.pdf 2>/dev/null | grep Pages || true

clean:
	latexmk -C main.tex
