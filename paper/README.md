# Seminar paper

Modular LaTeX source. `main.tex` holds the preamble + skeleton and `\input`s
one file per section from `sections/`. Figures are build products generated
from experiment data — never copy-pasted.

## Layout
```
paper/
  main.tex            # preamble + \input skeleton (edit rarely)
  refs.bib            # references
  sections/*.tex      # one file per section — edit these
  figures/            # generated PDFs, committed (results/ is git-ignored)
  Makefile
```

## Build
One-time TeX install (Debian/Ubuntu):
```
sudo apt install texlive-latex-recommended texlive-latex-extra latexmk
```
Then, from `paper/`:
```
make            # regenerate figures (if data present) + compile main.pdf
make pdf        # just compile
make figures    # just regenerate figures from ../results
make watch      # auto-rebuild on save
```

## Collaboration (minimize merge conflicts)
- `main.tex` changes rarely. Each author works in **one** `sections/*.tex`.
- Branch per section: `feature/sec-results`, `feature/sec-methods`, ...
- Because branches touch disjoint files, merges into `main` are trivial.

## Figures
`results/` is git-ignored, so raw run data does not travel with the repo.
Whoever has the data runs `make figures` and **commits** the resulting
`figures/*.pdf`, so every co-author can compile without the data.
Override the run dir: `make figures EXP1_RUN=../results/<run_dir>`.
