#!/usr/bin/env python3
"""Insight-echo plausibility study for the {q,i} -> {q,i|q,i} repetition gain.

Hypothesis under test (delivery/uptake account): the second insight copy raises
the probability that the model actually uses the card. If so, items that flip
wrong->right under repetition should show increased lexical uptake of the card
in their completions.

Echo metric: for each item, V = content words (>=4 chars, non-stopword) that
appear in the skill card but NOT in the question. echo(response) = |tokens(response)
 intersect V| / |V|. Excluding question vocabulary ensures question restatement
scores zero; the {q} condition (card never shown) provides the coincidental-
overlap baseline for the correctness confound.

Pre-specified comparisons:
  P1 sanity      echo({q,i}) >> echo({q})
  P2 confound    echo by correctness within {q} (no card shown)
  P3 key test    paired delta echo ({q,i|q,i} - {q,i}) by transition group
  P4 asymmetry   improved vs hurt deltas
  P5 prospective among items wrong at x1: does low echo at x1 predict the flip?

Default run: Qwen 2.5 7B main factorial (k2={q,i}, k4={q,i|q,i}, k5={q}).
"""

from __future__ import annotations

import json
import math
import random
import re
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = "20260710_020210_think_twice_trs-deepmath_oracle_openai-compatible_Qwen_Qwen2.5-7B-Instruct_k1-2-3-4-5-6"
K_SINGLE, K_REPEATED, K_BARE = 2, 4, 5
MIN_VOCAB = 10
BOOTSTRAP = 10_000

STOPWORDS = set(
    """
    this that with from have will which their there would could should about
    when where what then than them they were been being also each such only
    into over under between because while after before during these those
    them being does doing done other another same more most some many much
    very just like both without within upon must may might shall
    problem problems question answer answers final solution solutions solve
    solving given find determine calculate compute value values number numbers
    step steps first second using use used following result results
    """.split()
)

WORD = re.compile(r"[a-z]{4,}")


def tokens(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOPWORDS}


def bootstrap_ci(values: list[float], seed: int = 42) -> tuple[float, float, float]:
    rng = random.Random(seed)
    n = len(values)
    mean = statistics.fmean(values)
    means = []
    for _ in range(BOOTSTRAP):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))
    means.sort()
    return mean, means[int(0.025 * BOOTSTRAP)], means[int(0.975 * BOOTSTRAP)]


def sign_test_p(diffs: list[float]) -> float:
    """Exact two-sided sign test on nonzero paired differences."""
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def main() -> None:
    rows: dict[tuple[int, int], dict] = {}
    for line in (ROOT / "results" / RUN / "results.jsonl").open():
        r = json.loads(line)
        if r["k"] in (K_SINGLE, K_REPEATED, K_BARE):
            rows[(r["item_index"], r["k"])] = r

    items = sorted({i for i, _ in rows})
    skipped = 0
    data = []
    for i in items:
        single, repeated, bare = rows[(i, K_SINGLE)], rows[(i, K_REPEATED)], rows[(i, K_BARE)]
        vocab = tokens(single["skill_text"]) - tokens(single["question"])
        if len(vocab) < MIN_VOCAB:
            skipped += 1
            continue
        echo = lambda r: len(tokens(r["response_text"]) & vocab) / len(vocab)
        data.append(
            {
                "item": i,
                "vocab": len(vocab),
                "e_single": echo(single),
                "e_repeated": echo(repeated),
                "e_bare": echo(bare),
                "c_single": bool(single["is_correct"]),
                "c_repeated": bool(repeated["is_correct"]),
                "c_bare": bool(bare["is_correct"]),
                "len_single": len(single["response_text"].split()),
                "len_repeated": len(repeated["response_text"].split()),
            }
        )

    out = [
        "# Insight-echo plausibility study: Qwen 2.5 7B, {q,i} -> {q,i|q,i}",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')}. n={len(data)} items analyzed "
        f"({skipped} skipped for distinctive card vocabulary < {MIN_VOCAB} words).",
        "Echo = share of the card's distinctive vocabulary (card words absent from the question,",
        "stopwords removed) that appears in the completion. Bootstrap CIs, 10k resamples.",
        "",
    ]

    def fmt(x):
        return f"{x*100:.1f}%"

    # P1 sanity + P2 confound
    m_qi, lo, hi = bootstrap_ci([d["e_single"] for d in data])
    m_q, lo2, hi2 = bootstrap_ci([d["e_bare"] for d in data])
    out += [
        "## P1 sanity: does the metric detect card usage at all?",
        "",
        f"- mean echo with card in prompt ({{q,i}}): **{fmt(m_qi)}** [{fmt(lo)}, {fmt(hi)}]",
        f"- mean echo without card ({{q}}):        **{fmt(m_q)}** [{fmt(lo2)}, {fmt(hi2)}]",
        "",
    ]

    bare_correct = [d["e_bare"] for d in data if d["c_bare"]]
    bare_wrong = [d["e_bare"] for d in data if not d["c_bare"]]
    mc, lc, hc = bootstrap_ci(bare_correct)
    mw, lw, hw = bootstrap_ci(bare_wrong)
    out += [
        "## P2 correctness confound, measured where the card was never shown ({q}):",
        "",
        f"- echo of correct {{q}} responses: {fmt(mc)} [{fmt(lc)}, {fmt(hc)}]  (n={len(bare_correct)})",
        f"- echo of wrong {{q}} responses:   {fmt(mw)} [{fmt(lw)}, {fmt(hw)}]  (n={len(bare_wrong)})",
        f"- confound size (correct - wrong, no card): **{fmt(mc-mw)}**",
        "",
    ]

    # P3/P4: paired deltas by transition group
    groups = {
        "improved (wrong->right)": [d for d in data if not d["c_single"] and d["c_repeated"]],
        "hurt (right->wrong)": [d for d in data if d["c_single"] and not d["c_repeated"]],
        "stable correct": [d for d in data if d["c_single"] and d["c_repeated"]],
        "stable wrong": [d for d in data if not d["c_single"] and not d["c_repeated"]],
    }
    out += [
        "## P3/P4 paired echo change under repetition, by transition group",
        "",
        "| Group | n | echo at x1 | echo at x2 | paired delta | 95% CI | sign-test p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, g in groups.items():
        diffs = [d["e_repeated"] - d["e_single"] for d in g]
        m1 = statistics.fmean(d["e_single"] for d in g)
        m2 = statistics.fmean(d["e_repeated"] for d in g)
        md, lo, hi = bootstrap_ci(diffs)
        out.append(
            f"| {name} | {len(g)} | {fmt(m1)} | {fmt(m2)} | {fmt(md)} | [{fmt(lo)}, {fmt(hi)}] | {sign_test_p(diffs):.4f} |"
        )
    out.append("")

    # response length check (echo could rise with longer outputs)
    for name in ("improved (wrong->right)", "hurt (right->wrong)"):
        g = groups[name]
        l1 = statistics.fmean(d["len_single"] for d in g)
        l2 = statistics.fmean(d["len_repeated"] for d in g)
        out.append(f"- length check, {name}: mean words {l1:.0f} (x1) vs {l2:.0f} (x2)")
    out.append("")

    # P5 prospective: among items wrong at x1, does low echo at x1 predict the flip?
    wrong_x1 = [d for d in data if not d["c_single"]]
    flipped = [d["e_single"] for d in wrong_x1 if d["c_repeated"]]
    stayed = [d["e_single"] for d in wrong_x1 if not d["c_repeated"]]
    mf, lf, hf = bootstrap_ci(flipped)
    ms, ls, hs = bootstrap_ci(stayed)
    # bootstrap CI of the difference in means (unpaired)
    rng = random.Random(7)
    diffs = []
    for _ in range(BOOTSTRAP):
        a = [flipped[rng.randrange(len(flipped))] for _ in range(len(flipped))]
        b = [stayed[rng.randrange(len(stayed))] for _ in range(len(stayed))]
        diffs.append(statistics.fmean(a) - statistics.fmean(b))
    diffs.sort()
    out += [
        "## P5 prospective: echo at x1 among items that were WRONG at x1",
        "",
        f"- future improved (flip to correct at x2): {fmt(mf)} [{fmt(lf)}, {fmt(hf)}]  (n={len(flipped)})",
        f"- stable wrong:                            {fmt(ms)} [{fmt(ls)}, {fmt(hs)}]  (n={len(stayed)})",
        f"- difference (improved - stable wrong): **{fmt(mf-ms)}** "
        f"[{fmt(diffs[int(0.025*BOOTSTRAP)])}, {fmt(diffs[int(0.975*BOOTSTRAP)])}]",
        "",
        "Uptake account predicts a NEGATIVE difference: flips should come from items where",
        "the first copy was under-used.",
        "",
    ]

    # bonus: uptake rate at x2 on improved items vs their own x1
    imp = groups["improved (wrong->right)"]
    gain_share = sum(1 for d in imp if d["e_repeated"] > d["e_single"]) / len(imp)
    out.append(f"- share of improved items whose echo rose under repetition: {gain_share:.0%}")

    text = "\n".join(out)
    output = ROOT / "results" / f"insight_echo_qwen7b_{time.strftime('%Y%m%d')}.md"
    output.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nwritten to {output}")


if __name__ == "__main__":
    main()
