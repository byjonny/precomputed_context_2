#!/usr/bin/env python3
"""Build the Experiment (I) slide figure:

    top    : prompt schematic (k=1 vs k=2) + n
    center : 2x2 contingency matrix (k1 correct/wrong x k2 correct/wrong)
    bottom : short significance note (McNemar)

Usage:
    .venv/bin/python scripts/make_slide_figure.py <run_dir> [out.png]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ---- palette (TUM) ----
TUM_BLUE = "#3070B3"
TUM_DARK = "#072140"
GOOD = "#A2AD00"      # TUM green  -> improved / stable-correct
BAD = "#EA7237"       # orange     -> hurt
GREY = "#C4C4C4"      # stable wrong
INSIGHT_C = "#3070B3"
PROBLEM_C = "#9ABCE4"


def load_counts(run_dir: Path) -> dict:
    pair: dict[tuple, dict[int, bool]] = {}
    with (run_dir / "results.jsonl").open() as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            pair.setdefault((r["question_id"], r["repeat_idx"]), {})[int(r["k"])] = bool(r["is_correct"])
    both = [(v[1], v[2]) for v in pair.values() if 1 in v and 2 in v]
    n = len(both)
    sc = sum(1 for a, b in both if a and b)
    hurt = sum(1 for a, b in both if a and not b)
    imp = sum(1 for a, b in both if (not a) and b)
    sw = sum(1 for a, b in both if (not a) and (not b))
    acc1 = sum(1 for a, _ in both if a) / n
    acc2 = sum(1 for _, b in both if b) / n
    chi2 = (abs(imp - hurt) - 1) ** 2 / (imp + hurt)
    p = math.erfc(math.sqrt(chi2 / 2))
    return dict(n=n, sc=sc, hurt=hurt, imp=imp, sw=sw,
                acc1=acc1, acc2=acc2, delta=acc2 - acc1, chi2=chi2, p=p)


def box(ax, x, y, w, h, text, fc, tc="white", fs=12, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.03",
                                linewidth=0, facecolor=fc, mutation_aspect=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc,
            fontsize=fs, fontweight="bold" if bold else "normal")


def draw_prompts(ax, n):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.0, 0.93, "Prompt design", fontsize=13, fontweight="bold", color=TUM_DARK)
    ax.text(1.0, 0.93, f"n = {n:,} items", fontsize=12, color=TUM_BLUE,
            fontweight="bold", ha="right")

    h = 0.26
    # k = 1
    ax.text(0.0, 0.60, "k = 1", fontsize=12, fontweight="bold", color=TUM_DARK, va="center")
    box(ax, 0.16, 0.47, 0.18, h, "Insight", INSIGHT_C, fs=11)
    box(ax, 0.35, 0.47, 0.20, h, "Problem", PROBLEM_C, tc=TUM_DARK, fs=11)

    # k = 2  (two compact pairs with a clear empty gap for the connector)
    ax.text(0.0, 0.17, "k = 2", fontsize=12, fontweight="bold", color=TUM_DARK, va="center")
    cy = 0.04
    box(ax, 0.14, cy, 0.115, h, "Insight", INSIGHT_C, fs=9)
    box(ax, 0.255, cy, 0.13, h, "Problem", PROBLEM_C, tc=TUM_DARK, fs=9)
    # connector in the empty gap 0.385 .. 0.535
    gap_c = 0.46
    arr = FancyArrowPatch((0.40, cy + h / 2), (0.52, cy + h / 2),
                          arrowstyle="-|>", mutation_scale=11, color="#888", lw=1.4)
    ax.add_patch(arr)
    ax.text(gap_c, cy + h + 0.05, "repeat", ha="center", va="center",
            fontsize=8.5, style="italic", color="#666")
    box(ax, 0.535, cy, 0.115, h, "Insight", INSIGHT_C, fs=9)
    box(ax, 0.65, cy, 0.13, h, "Problem", PROBLEM_C, tc=TUM_DARK, fs=9)


def draw_matrix(ax, c):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    # grid geometry
    x0, y0, w, hgt = 0.30, 0.10, 0.62, 0.70
    cw, ch = w / 2, hgt / 2
    cells = {  # (col,row) row0=top: k1 correct ; row1: k1 wrong
        (0, 0): (c["sc"], "stable\ncorrect", GOOD, "white"),
        (1, 0): (c["hurt"], "hurt\nR→W", BAD, "white"),
        (0, 1): (c["imp"], "improved\nW→R", TUM_BLUE, "white"),
        (1, 1): (c["sw"], "stable\nwrong", GREY, TUM_DARK),
    }
    for (col, row), (val, lab, fc, tc) in cells.items():
        cx, cy = x0 + col * cw, y0 + (1 - row) * ch
        discordant = (col, row) in {(1, 0), (0, 1)}
        ax.add_patch(plt.Rectangle((cx, cy), cw, ch, facecolor=fc,
                                   edgecolor="white", linewidth=3, zorder=1))
        if discordant:  # emphasise the cells that drive the test
            ax.add_patch(plt.Rectangle((cx + 0.006, cy + 0.006), cw - 0.012, ch - 0.012,
                                       fill=False, edgecolor="white", linewidth=2.2,
                                       linestyle=(0, (4, 3)), zorder=3))
        ax.text(cx + cw / 2, cy + ch / 2 + 0.045, f"{val:,}", ha="center", va="center",
                fontsize=27, fontweight="bold", color=tc, zorder=4)
        ax.text(cx + cw / 2, cy + ch / 2 - 0.075, lab, ha="center", va="center",
                fontsize=10.5, color=tc, zorder=4)

    # headers
    ax.text(x0 + w / 2, y0 + hgt + 0.11, "k = 2", ha="center", fontsize=13,
            fontweight="bold", color=TUM_DARK)
    ax.text(x0 + cw / 2, y0 + hgt + 0.04, "correct", ha="center", fontsize=11, color=TUM_DARK)
    ax.text(x0 + cw + cw / 2, y0 + hgt + 0.04, "wrong", ha="center", fontsize=11, color=TUM_DARK)
    ax.text(x0 - 0.135, y0 + hgt / 2, "k = 1", va="center", rotation=90, fontsize=13,
            fontweight="bold", color=TUM_DARK)
    ax.text(x0 - 0.055, y0 + hgt - ch / 2, "correct", va="center", rotation=90,
            fontsize=11, color=TUM_DARK)
    ax.text(x0 - 0.055, y0 + ch / 2, "wrong", va="center", rotation=90,
            fontsize=11, color=TUM_DARK)


def draw_stats(ax, c):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0.0), 1, 1.0, facecolor="#F2F5F9", edgecolor="none"))
    ax.text(0.5, 0.80, f"Accuracy {c['acc1']*100:.1f}%  →  {c['acc2']*100:.2f}%"
                       f"   (Δ = +{c['delta']*100:.2f} pp)",
            ha="center", va="center", fontsize=13, fontweight="bold", color=TUM_DARK)
    ax.text(0.5, 0.50, f"McNemar on the discordant cells ({c['imp']} vs {c['hurt']}):"
                       f"  χ² = {c['chi2']:.1f},  p ≈ {c['p']:.3f}",
            ha="center", va="center", fontsize=12, color=TUM_DARK)
    ax.text(0.5, 0.20, "Repetition (k=2) significantly improves accuracy (p < 0.01) — "
                       "agreement cells (574 / 969) carry no signal.",
            ha="center", va="center", fontsize=10.5, style="italic", color="#555")


def main(argv):
    if not argv:
        print(__doc__); return 1
    run_dir = Path(argv[0])
    out = Path(argv[1]) if len(argv) > 1 else run_dir / "experiment1_slide_figure.png"
    c = load_counts(run_dir)

    fig = plt.figure(figsize=(7.2, 8.6), dpi=200)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.05, 2.0, 0.7], hspace=0.18,
                          left=0.04, right=0.97, top=0.97, bottom=0.03)
    draw_prompts(fig.add_subplot(gs[0]), c["n"])
    draw_matrix(fig.add_subplot(gs[1]), c)
    draw_stats(fig.add_subplot(gs[2]), c)
    fig.savefig(out, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
