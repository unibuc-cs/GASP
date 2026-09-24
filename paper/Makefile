# Build the paper; sync tables and figures from the experiment outputs first.
OUT ?= ../outputs/paper

all: sync pdf

sync:
	cp $(OUT)/table_main.tex tables/table_main.tex
	cp $(OUT)/worked_example/worked_example.tex tables/worked_example.tex
	cp $(OUT)/adaptive/tradeoff_R3_15.png figures/tradeoff_R3_15.png

pdf:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /dev/null
	@pdfinfo main.pdf 2>/dev/null | grep Pages || true

clean:
	latexmk -C main.tex
