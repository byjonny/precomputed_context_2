#!/usr/bin/env python3
"""Analyze the 2x2 order x repetition factorial.

Condition labels (k in results.jsonl):
    1 = {i,q}            insight-first,  single
    2 = {q,i}            problem-first,  single
    3 = {i,q,sep,i,q}    insight-first,  repeated
    4 = {q,i,sep,q,i}    problem-first,  repeated

Reports per-condition accuracy, the 2x2 accuracy table, paired McNemar tests
for each contrast, and the interaction term.

Usage:
    .venv/bin/python scripts/analyze_factorial.py <run_dir> [more_run_dirs...]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

LABELS = {1: "insight-first x1  {i,q}",
          2: "problem-first x1  {q,i}",
          3: "insight-first x2  {i,q,sep,i,q}",
          4: "problem-first x2  {q,i,sep,q,i}"}


def load(run_dirs):
    # by_item[(qid,repeat)][k] = bool correct
    by_item: dict[tuple, dict[int, bool]] = {}
    for d in run_dirs:
        for line in (Path(d) / "results.jsonl").open():
            if not line.strip():
                continue
            r = json.loads(line)
            by_item.setdefault((r["question_id"], r["repeat_idx"]), {})[int(r["k"])] = bool(r["is_correct"])
    return by_item


def acc(by_item, k):
    vals = [v[k] for v in by_item.values() if k in v]
    return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)


def mcnemar(by_item, ka, kb):
    """Paired test: does kb differ from ka on items where both were run."""
    b = c = 0  # b: ka wrong, kb right ; c: ka right, kb wrong
    n = 0
    for v in by_item.values():
        if ka in v and kb in v:
            n += 1
            if (not v[ka]) and v[kb]:
                b += 1
            elif v[ka] and (not v[kb]):
                c += 1
    if b + c == 0:
        return dict(n=n, b=b, c=c, chi2=0.0, p=1.0)
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(chi2 / 2))
    return dict(n=n, b=b, c=c, chi2=chi2, p=p)


def main(argv):
    if not argv:
        print(__doc__); return 1
    by_item = load(argv)
    a = {k: acc(by_item, k)[0] for k in (1, 2, 3, 4)}
    nn = {k: acc(by_item, k)[1] for k in (1, 2, 3, 4)}

    print("=== per-condition accuracy ===")
    for k in (1, 2, 3, 4):
        print(f"  C{k}  {LABELS[k]:<32}  acc={a[k]*100:6.2f}%   n={nn[k]}")

    print("\n=== 2x2 accuracy table (%) ===")
    print(f"               single(x1)   repeated(x2)   rep-effect")
    print(f"  insight-first  {a[1]*100:7.2f}      {a[3]*100:7.2f}      {(a[3]-a[1])*100:+6.2f} pp")
    print(f"  problem-first  {a[2]*100:7.2f}      {a[4]*100:7.2f}      {(a[4]-a[2])*100:+6.2f} pp")
    print(f"  order-effect   {(a[2]-a[1])*100:+6.2f}      {(a[4]-a[3])*100:+6.2f}")

    inter = (a[3] - a[1]) - (a[4] - a[2])
    print(f"\n  interaction (rep|insight - rep|problem) = {inter*100:+.2f} pp")
    print("  (mechanism predicts > 0: repetition helps insight-first more)")

    contrasts = [
        ("Repetition effect, insight-first", 1, 3),
        ("Repetition effect, problem-first", 2, 4),
        ("Order effect, single",            1, 2),
        ("Order effect, repeated",          3, 4),
        ("Repeat-insight vs reorder (C3 vs C2)", 2, 3),
    ]
    print("\n=== paired McNemar contrasts (continuity corrected) ===")
    for name, ka, kb in contrasts:
        m = mcnemar(by_item, ka, kb)
        sig = "***" if m["p"] < 0.001 else "**" if m["p"] < 0.01 else "*" if m["p"] < 0.05 else "ns"
        print(f"  {name:<38} C{ka}->C{kb}: "
              f"d={a[kb]*100-a[ka]*100:+5.2f}pp  "
              f"discordant {m['b']}/{m['c']}  chi2={m['chi2']:5.2f}  p={m['p']:.4f} {sig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
