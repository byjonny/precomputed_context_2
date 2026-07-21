#!/usr/bin/env python3
"""Per-item transition analysis for the x1 -> x2 repetition contrasts.

For every main factorial run, pair each item's outcome under the single
condition with its outcome under the repeated condition and count:
wrong->right (improved), right->wrong (hurt), stable correct, stable wrong.

Contrasts (main-run condition mapping k1..k6 = iq, qi, iqiq, qiqi, q, qq):
  problem-first  {q,i}  -> {q,i|q,i}   (k2 -> k4)
  insight-first  {i,q}  -> {i,q|i,q}   (k1 -> k3)
  question-only  {q}    -> {q|q}       (k5 -> k6, control)

McNemar is continuity-corrected, matching the analyses in results/*.md.
Writes results/repetition_transitions_<date>.md and prints the same tables.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAIN_RUNS = [
    ("Mistral Nemo 12B", "20260710_005059_think_twice_trs-deepmath_oracle_openai-compatible_mistralai_Mistral-Nemo-Instruct-2407_k1-2-3-4-5-6"),
    ("Mistral Small 24B", "20260710_221900_think_twice_trs-deepmath_oracle_openai-compatible_mistralai_Mistral-Small-3.1-24B-Instruct-2503_k1-2-3-4-5-6"),
    ("Qwen 2.5 7B", "20260710_020210_think_twice_trs-deepmath_oracle_openai-compatible_Qwen_Qwen2.5-7B-Instruct_k1-2-3-4-5-6"),
    ("Qwen 2.5 32B", "20260710_175306_think_twice_trs-deepmath_oracle_openai-compatible_Qwen_Qwen2.5-32B-Instruct_k1-2-3-4-5-6"),
    ("Gemma 3 12B", "20260712_154858_think_twice_trs-deepmath_oracle_openai-compatible_google_gemma-3-12b-it_k1-2-3-4-5-6"),
    ("Gemma 3 27B", "20260712_211003_think_twice_trs-deepmath_oracle_openai-compatible_google_gemma-3-27b-it_k1-2-3-4-5-6"),
    ("Qwen 3 8B (think off)", "20260713_002119_think_twice_qwen3_8b_thinking_off_trs-deepmath_oracle_openai-compatible_Qwen_Qwen3-8B_k1-2-3-4-5-6"),
    ("Qwen 3 8B (think on)", "20260712_160527_think_twice_qwen3_8b_thinking_on_trs-deepmath_oracle_openai-compatible_Qwen_Qwen3-8B_k1-2-3-4-5-6"),
]

CONTRASTS = [
    ("problem-first", "{q,i} -> {q,i|q,i}", 2, 4),
    ("insight-first", "{i,q} -> {i,q|i,q}", 1, 3),
    ("question-only", "{q} -> {q|q}", 5, 6),
]


def mcnemar_p(b: int, c: int) -> float:
    """Continuity-corrected McNemar test; b = wrong->right, c = right->wrong."""
    if b + c == 0:
        return 1.0
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    return math.erfc(math.sqrt(chi2 / 2))


def load_outcomes(run_dir: Path) -> dict[tuple[int, int], bool]:
    outcomes: dict[tuple[int, int], bool] = {}
    for line in (run_dir / "results.jsonl").open():
        row = json.loads(line)
        outcomes[(int(row["item_index"]), int(row["k"]))] = bool(row["is_correct"])
    return outcomes


def main() -> None:
    lines: list[str] = [
        "# Per-item repetition transitions (x1 -> x2)",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} from post-retry results.jsonl (error records count as wrong).",
        "Each cell pairs the same item under the single and the repeated condition; n=1,000 per contrast.",
        "`improved` = wrong->right, `hurt` = right->wrong, net = improved - hurt (= accuracy delta in tenths of pp).",
        "McNemar is continuity-corrected on the discordant pairs.",
        "",
    ]
    for label, description, k_single, k_repeated in CONTRASTS:
        lines.append(f"## {label}: `{description}`")
        lines.append("")
        lines.append("| Model | improved | hurt | stable correct | stable wrong | net (pp) | discordant | McNemar p |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for model, run_name in MAIN_RUNS:
            outcomes = load_outcomes(ROOT / "results" / run_name)
            items = sorted({item for item, _ in outcomes})
            improved = hurt = stable_correct = stable_wrong = 0
            for item in items:
                single = outcomes[(item, k_single)]
                repeated = outcomes[(item, k_repeated)]
                if not single and repeated:
                    improved += 1
                elif single and not repeated:
                    hurt += 1
                elif single and repeated:
                    stable_correct += 1
                else:
                    stable_wrong += 1
            n = improved + hurt + stable_correct + stable_wrong
            net = improved - hurt
            p = mcnemar_p(improved, hurt)
            lines.append(
                f"| {model} | {improved} | {hurt} | {stable_correct} | {stable_wrong} "
                f"| {net / (n / 100):+.1f} | {improved + hurt} ({(improved + hurt) / n:.0%}) | {p:.3f} |"
            )
        lines.append("")

    output = ROOT / "results" / f"repetition_transitions_{time.strftime('%Y%m%d')}.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten to {output}")


if __name__ == "__main__":
    main()
