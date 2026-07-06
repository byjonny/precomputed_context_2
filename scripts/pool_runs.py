#!/usr/bin/env python3
"""Pool two or more experiment runs (disjoint items, same k design) into one
combined summary: accuracy by k, the 1->2 repetition delta, and a McNemar test
on the k=1 vs k=2 discordant pairs.

Usage:
    PYTHONPATH=src python3 scripts/pool_runs.py results/RUN_A results/RUN_B [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv: list[str]) -> int:
    if len(argv) < 1:
        print(__doc__)
        return 1

    run_dirs = [Path(a) for a in argv]
    rows: list[dict] = []
    seen_ids: set[str] = set()
    overlaps = 0
    for d in run_dirs:
        run_rows = load_rows(d)
        ids = {r["question_id"] for r in run_rows}
        overlaps += len(ids & seen_ids)
        seen_ids |= ids
        rows.extend(run_rows)
        print(f"loaded {len(run_rows):>6} rows / {len(ids):>5} items  <- {d.name}")
    if overlaps:
        print(f"\nNote: {overlaps} item-ids appear in more than one run. That is EXPECTED "
              f"for round-robin passes over the same items (each pass = one replicate); "
              f"accuracy-by-k pools all samples and the paired test keys on run_id. "
              f"Only a concern if you meant these runs to cover DISJOINT item sets.")

    # accuracy by k
    by_k: dict[int, list[dict]] = {}
    for r in rows:
        by_k.setdefault(int(r["k"]), []).append(r)

    print("\n=== accuracy by k (pooled) ===")
    for k in sorted(by_k):
        rs = by_k[k]
        acc = sum(1 for r in rs if r["is_correct"]) / len(rs)
        mean_in = sum(r["usage"].get("prompt_tokens") or 0 for r in rs) / len(rs)
        mean_out = sum(r["usage"].get("completion_tokens") or 0 for r in rs) / len(rs)
        print(f"k={k}: n={len(rs):>6}  acc={acc:.4f} ({acc*100:.2f}%)  "
              f"mean_in={mean_in:.1f}  mean_out={mean_out:.1f}")

    # paired k=1 vs k=2 per replicate (run_id, question_id, repeat_idx).
    # Including run_id keeps round-robin passes over the same items (each a
    # separate run dir at repeat_idx=0) as distinct pairs instead of colliding.
    pair: dict[tuple, dict[int, bool]] = {}
    for r in rows:
        key = (r.get("run_id"), r["question_id"], r["repeat_idx"])
        pair.setdefault(key, {})[int(r["k"])] = bool(r["is_correct"])

    both = [(v[1], v[2]) for v in pair.values() if 1 in v and 2 in v]
    improved = sum(1 for a, b in both if (not a) and b)   # wrong->right
    hurt = sum(1 for a, b in both if a and (not b))        # right->wrong
    stable_c = sum(1 for a, b in both if a and b)
    stable_w = sum(1 for a, b in both if (not a) and (not b))
    n = len(both)

    print("\n=== k=1 -> k=2 transitions (paired, pooled) ===")
    print(f"items with both k:    {n}")
    print(f"improved (W->R):      {improved}")
    print(f"hurt     (R->W):      {hurt}")
    print(f"stable correct:       {stable_c}")
    print(f"stable wrong:         {stable_w}")
    if n:
        acc1 = (improved + 0 + stable_c) / n  # = (R at k1)/n
        acc1 = sum(1 for a, _ in both if a) / n
        acc2 = sum(1 for _, b in both if b) / n
        print(f"\nacc k=1: {acc1*100:.2f}%   acc k=2: {acc2*100:.2f}%   "
              f"delta: {(acc2-acc1)*100:+.2f} pp")

    # McNemar with continuity correction
    b, c = improved, hurt
    if b + c > 0:
        chi2 = (abs(b - c) - 1) ** 2 / (b + c)
        # two-sided p from chi-square df=1 via survival function
        import math
        p = math.erfc(math.sqrt(chi2 / 2.0))
        print(f"\nMcNemar (cont. corrected): chi2={chi2:.2f}, p={p:.4g}  "
              f"({'significant' if p < 0.05 else 'not significant'} at 0.05)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
