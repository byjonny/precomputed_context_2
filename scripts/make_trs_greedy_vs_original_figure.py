#!/usr/bin/env python3
"""Small-multiple dumbbell figure: original prompt (temp 0.7) vs TRS prompt
(temp 0, greedy), per model, per condition. Each panel's y-axis is zoomed to
that model's own accuracy range so small setup differences are visible.

Regenerate by editing the DATA block (values are exact-match accuracy %, n=1000).
Outputs PNG + PDF next to the other result figures.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# name, bucket, orig+0.7 [q, q|q, q,i, i,q, q,i|q,i, i,q|i,q], TRS+t0 [...]
DATA = [
    ("Mistral Nemo 12B", "5-10B",  [13.8,13.8,18.1,18.6,19.3,17.2], [12.4,11.4,19.7,20.3,18.4,17.0]),
    ("Qwen2.5 7B",       "5-10B",  [42.5,43.0,50.1,44.8,53.3,48.7], [48.2,45.6,52.5,50.9,55.3,49.0]),
    ("Qwen3 8B (off)",   "5-10B",  [49.5,52.9,59.7,58.7,63.4,60.7], [52.0,52.6,60.8,60.5,61.1,60.6]),
    ("Gemma 3 12B",      "10-20B", [53.0,54.8,64.4,61.7,64.3,64.3], [53.4,53.5,60.8,61.4,62.4,63.6]),
    ("Mistral Small 24B","20-50B", [33.2,34.0,44.8,44.2,47.1,46.7], [33.1,33.7,43.8,45.8,46.8,45.5]),
    ("Qwen2.5 32B",      "20-50B", [53.2,52.3,66.0,63.3,65.4,64.3], [55.5,54.5,67.8,64.5,66.1,65.9]),
    ("Gemma 3 27B",      "20-50B", [60.6,62.6,72.3,70.0,73.5,71.9], [61.1,63.4,70.4,69.8,72.4,71.0]),
]
COND = ["q", "q|q", "q,i", "i,q", "q,i|q,i", "i,q|i,q"]
ORIG_C = "#898781"   # gray  = original prompt, temp 0.7
TRS_C  = "#2a78d6"   # blue  = TRS prompt, temp 0 (greedy)

plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans", "axes.edgecolor": "#c3c2b7"})

fig, axes = plt.subplots(2, 4, figsize=(13.5, 6.2))
axes = axes.ravel()

for ax, (name, bucket, orig, trs) in zip(axes, DATA):
    x = range(len(COND))
    for xi, o, t in zip(x, orig, trs):
        ax.plot([xi, xi], [o, t], color="#c3c2b7", lw=1.4, zorder=1)
        ax.scatter(xi, o, s=42, color=ORIG_C, zorder=2)
        ax.scatter(xi, t, s=42, color=TRS_C, zorder=3)
    lo = min(min(orig), min(trs)); hi = max(max(orig), max(trs))
    pad = max(0.8, (hi - lo) * 0.18)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-0.5, len(COND) - 0.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(COND, fontsize=7.5, rotation=0)
    ax.set_title(f"{name}   ({bucket})", fontsize=9.5, loc="left", pad=6)
    ax.grid(axis="y", color="#e1e0d9", lw=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.set_ylabel("accuracy %", fontsize=8)

# 8th cell: legend + note
lg = axes[7]; lg.axis("off")
handles = [
    Line2D([0],[0], marker="o", color="w", markerfacecolor=ORIG_C, markersize=9, label="original prompt · temp 0.7"),
    Line2D([0],[0], marker="o", color="w", markerfacecolor=TRS_C,  markersize=9, label="TRS prompt · temp 0 (greedy)"),
]
lg.legend(handles=handles, loc="upper left", frameon=False, fontsize=10, handletextpad=0.4)
lg.text(0.02, 0.55,
        "Each panel is zoomed to its own\naccuracy range to reveal small\nsetup differences. n = 1,000 paired\nitems per condition per model.\n\nGemma 12B & 27B: original slightly\nhigher. Qwen 7B: TRS clearly higher.\nMost cells nearly identical.",
        fontsize=8.5, va="top", color="#52514e", linespacing=1.5)

fig.suptitle("Original prompt (temp 0.7)  vs  TRS prompt (temp 0, greedy) — seven non-reasoning models",
             fontsize=12, x=0.5, y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.97])

import sys
out = sys.argv[1] if len(sys.argv) > 1 else "results/trs_greedy_vs_original_zoomed"
fig.savefig(out + ".png", dpi=200, bbox_inches="tight")
fig.savefig(out + ".pdf", bbox_inches="tight")
print("wrote", out + ".png", "and", out + ".pdf")
