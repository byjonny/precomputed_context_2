# Paper build. Run from paper/.
#   make            -> regenerate figures (if data present) + build PDF
#   make pdf        -> compile main.pdf with latexmk
#   make figures    -> regenerate figures/*.pdf from results/ via analysis scripts
#   make watch      -> rebuild on save (latexmk -pvc)
#   make clean      -> remove LaTeX aux files (keeps figures + PDF)
#   make distclean  -> also remove main.pdf

PYTHON ?= ../.venv/bin/python
RESULTS ?= ../results
LATEXMK ?= latexmk

# Pick the newest matching run dir unless caller overrides EXP1_RUN=...
# Experiment 1 = k=1 vs k=2 block repetition; those run dirs end in _k1-2.
EXP1_RUN ?= $(shell ls -d $(RESULTS)/*_k1-2 2>/dev/null | sort | tail -1)

.PHONY: all pdf figures watch clean distclean
all: figures pdf

pdf:
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error main.tex

figures:
	@if [ -z "$(EXP1_RUN)" ]; then \
	  echo ">> no results dir found (results/ is git-ignored); skipping figure regen."; \
	  echo ">> committed figures/*.pdf will be used as-is."; \
	else \
	  echo ">> regenerating figures from $(EXP1_RUN)"; \
	  $(PYTHON) ../scripts/make_slide_figure.py "$(EXP1_RUN)" figures/experiment1.pdf; \
	fi

watch:
	$(LATEXMK) -pdf -pvc -interaction=nonstopmode main.tex

clean:
	$(LATEXMK) -c
	rm -f main.bbl

distclean: clean
	$(LATEXMK) -C
