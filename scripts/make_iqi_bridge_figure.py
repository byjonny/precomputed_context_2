#!/usr/bin/env python3
"""Visualize full-pair versus insight-only repetition effects."""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
RUNS = [
    (
        "Qwen 2.5 7B",
        "results/20260710_020210_think_twice_trs-deepmath_oracle_openai-compatible_"
        "Qwen_Qwen2.5-7B-Instruct_k1-2-3-4-5-6",
        "results/20260714_231502_ordering_iqi_anchor_trs-deepmath_oracle_"
        "openai-compatible_Qwen_Qwen2.5-7B-Instruct_k1-2-3",
    ),
    (
        "Mistral Small 24B",
        "results/20260710_221900_think_twice_trs-deepmath_oracle_openai-compatible_"
        "mistralai_Mistral-Small-3.1-24B-Instruct-2503_k1-2-3-4-5-6",
        "results/20260715_023539_ordering_iqi_anchor_trs-deepmath_oracle_"
        "openai-compatible_mistralai_Mistral-Small-3.1-24B-Instruct-2503_k1-2-3",
    ),
]

BG = "#111315"
TEXT = "#eef1f4"
MUTED = "#aeb5bd"
GRID = "#343a40"
WHITE = "#ffffff"
CYAN = "#58b9e8"
GREEN = "#65d58a"
GOLD = "#f2c14e"
CORAL = "#ff8066"


def text_node(
    x: float,
    y: float,
    content: str,
    *,
    size: int = 18,
    fill: str = TEXT,
    weight: str = "400",
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" dominant-baseline="middle">'
        f"{escape(content)}</text>"
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str = GRID,
    width: float = 1,
    opacity: float = 1.0,
) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width:.1f}" opacity="{opacity:.3f}"/>'
    )


def circle(x: float, y: float, radius: float, *, fill: str) -> str:
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" '
        f'stroke="{BG}" stroke-width="2"/>'
    )


def load_rows(relative_dir: str) -> dict[tuple[str, int], dict[int, dict]]:
    rows: dict[tuple[str, int], dict[int, dict]] = {}
    path = ROOT / relative_dir / "results.jsonl"
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            row = json.loads(raw_line)
            key = (str(row["question_id"]), int(row["repeat_idx"]))
            rows.setdefault(key, {})[int(row["k"])] = row
    return rows


def paired_effect(rows: dict, baseline_k: int, treatment_k: int) -> dict[str, float]:
    values = [
        int(by_k[treatment_k]["is_correct"]) - int(by_k[baseline_k]["is_correct"])
        for by_k in rows.values()
    ]
    n = len(values)
    effect = statistics.mean(values)
    se = statistics.stdev(values) / math.sqrt(n)
    improved = sum(value == 1 for value in values)
    hurt = sum(value == -1 for value in values)
    discordant = improved + hurt
    chi_square = ((abs(improved - hurt) - 1) ** 2 / discordant) if discordant else 0.0
    baseline = statistics.mean(int(by_k[baseline_k]["is_correct"]) for by_k in rows.values())
    treatment = statistics.mean(int(by_k[treatment_k]["is_correct"]) for by_k in rows.values())
    return {
        "effect": 100 * effect,
        "low": 100 * (effect - 1.96 * se),
        "high": 100 * (effect + 1.96 * se),
        "p": math.erfc(math.sqrt(chi_square / 2)),
        "baseline": 100 * baseline,
        "treatment": 100 * treatment,
    }


def scale(value: float, x1: float, x2: float) -> float:
    minimum, maximum = -4.0, 7.0
    return x1 + (value - minimum) / (maximum - minimum) * (x2 - x1)


def p_label(value: float) -> str:
    if value < 0.001:
        return "p<.001"
    return f"p={value:.3f}".replace("0.", ".")


def render_panel(parts: list[str], x0: float, model: str, effects: list[dict]) -> None:
    panel_width = 830.0
    label_x = x0 + 10
    plot_x1, plot_x2 = x0 + 270, x0 + 700
    value_x = x0 + panel_width - 5
    row_ys = [285.0, 440.0, 595.0]
    axis_y = 705.0

    parts.append(text_node(x0 + panel_width / 2, 145, model, size=24, weight="700", anchor="middle"))
    parts.append(line(x0, 178, x0 + panel_width, 178, stroke="#4a5159", width=1.5))

    for tick in (-4, -2, 0, 2, 4, 6):
        x = scale(tick, plot_x1, plot_x2)
        parts.append(
            line(
                x,
                205,
                x,
                axis_y,
                stroke="#78818a" if tick == 0 else GRID,
                width=1.5 if tick == 0 else 1,
            )
        )
        parts.append(text_node(x, axis_y + 25, f"{tick:+d}", size=14, fill=MUTED, anchor="middle"))

    labels = [
        ("Second insight after question", "{i,q | i}", CYAN),
        ("Full pair repeated", "{i,q | i,q}", GREEN),
        ("Second insight before question", "{i | i,q}", GOLD),
    ]
    for y, effect, (title, recipe, positive_color) in zip(row_ys, effects, labels):
        color = positive_color if effect["effect"] >= 0 else CORAL
        parts.append(text_node(label_x, y - 22, title, size=17, weight="700"))
        parts.append(text_node(label_x, y + 4, recipe, size=14, fill=MUTED))
        parts.append(
            text_node(
                label_x,
                y + 30,
                f'{{i,q}} baseline: {effect["baseline"]:.1f}%',
                size=13,
                fill=MUTED,
            )
        )
        parts.append(
            text_node(
                label_x,
                y + 52,
                f'Treatment accuracy: {effect["treatment"]:.1f}%',
                size=13,
                fill=MUTED,
            )
        )
        zero_x = scale(0, plot_x1, plot_x2)
        effect_x = scale(effect["effect"], plot_x1, plot_x2)
        low_x = scale(effect["low"], plot_x1, plot_x2)
        high_x = scale(effect["high"], plot_x1, plot_x2)
        parts.append(line(zero_x, y, effect_x, y, stroke=color, width=17, opacity=0.78))
        parts.append(line(low_x, y, high_x, y, stroke=WHITE, width=2))
        parts.append(line(low_x, y - 8, low_x, y + 8, stroke=WHITE, width=2))
        parts.append(line(high_x, y - 8, high_x, y + 8, stroke=WHITE, width=2))
        parts.append(circle(effect_x, y, 7, fill=color))
        parts.append(
            text_node(
                value_x,
                y - 11,
                f'{effect["effect"]:+.2f} pp',
                size=17,
                fill=color,
                weight="700",
                anchor="end",
            )
        )
        parts.append(text_node(value_x, y + 16, p_label(effect["p"]), size=13, fill=MUTED, anchor="end"))

    one_insight_mean = statistics.mean((effects[0]["effect"], effects[2]["effect"]))
    gap = effects[1]["effect"] - one_insight_mean
    parts.append(
        text_node(
            x0 + panel_width / 2,
            790,
            f"Full-pair gain minus mean one-extra-insight gain: {gap:+.1f} pp",
            size=17,
            fill=GREEN,
            weight="700",
            anchor="middle",
        )
    )


def main(argv: list[str]) -> int:
    output = Path(argv[0]) if argv else ROOT / "results/iqi_bridge_effects_20260715.svg"
    if not output.is_absolute():
        output = ROOT / output

    model_effects = []
    for model, old_dir, bridge_dir in RUNS:
        old_rows = load_rows(old_dir)
        bridge_rows = load_rows(bridge_dir)
        if set(old_rows) != set(bridge_rows) or len(bridge_rows) != 1000:
            raise ValueError(f"{model}: old and bridge item sets do not match")
        model_effects.append(
            (
                model,
                [
                    paired_effect(bridge_rows, 1, 2),
                    paired_effect(old_rows, 1, 3),
                    paired_effect(bridge_rows, 1, 3),
                ],
            )
        )

    width, height = 1800, 900
    parts = [
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>',
        text_node(40, 48, "Full-pair repetition versus insight-only repetition", size=29, weight="700"),
        text_node(
            40,
            84,
            "Paired accuracy change relative to the same-run {i,q} control; n=1,000 per condition, bars show 95% CIs.",
            size=16,
            fill=MUTED,
        ),
        line(900, 126, 900, 825, stroke="#4a5159", width=1.5),
    ]
    render_panel(parts, 35, *model_effects[0])
    render_panel(parts, 935, *model_effects[1])
    parts.append(
        text_node(
            40,
            850,
            "Baseline in every row is {i,q}. Full-pair uses the original-run control; one-extra-insight rows use the IQI bridge-run control.",
            size=13,
            fill=MUTED,
        )
    )
    parts.append(
        text_node(
            40,
            874,
            "Evaluator errors count as incorrect (Qwen bridge: 66 balanced DNS failures across k=1/2/3; Mistral bridge: 0).",
            size=13,
            fill=MUTED,
        )
    )
    document = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<title>Full-pair versus insight-only repetition effects</title>",
            '<style>text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }</style>',
            *parts,
            "</svg>",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
