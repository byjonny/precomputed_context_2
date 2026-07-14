#!/usr/bin/env python3
"""Create SVG summaries for the seven completed non-reasoning runs."""
from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
RUNS = [
    (
        "Mistral Nemo 12B",
        "results/20260710_005059_think_twice_trs-deepmath_oracle_openai-compatible_"
        "mistralai_Mistral-Nemo-Instruct-2407_k1-2-3-4-5-6",
    ),
    (
        "Mistral Small 24B",
        "results/20260710_221900_think_twice_trs-deepmath_oracle_openai-compatible_"
        "mistralai_Mistral-Small-3.1-24B-Instruct-2503_k1-2-3-4-5-6",
    ),
    (
        "Qwen 2.5 7B",
        "results/20260710_020210_think_twice_trs-deepmath_oracle_openai-compatible_"
        "Qwen_Qwen2.5-7B-Instruct_k1-2-3-4-5-6",
    ),
    (
        "Qwen 2.5 32B",
        "results/20260710_175306_think_twice_trs-deepmath_oracle_openai-compatible_"
        "Qwen_Qwen2.5-32B-Instruct_k1-2-3-4-5-6",
    ),
    (
        "Gemma 3 12B",
        "results/20260712_154858_think_twice_trs-deepmath_oracle_openai-compatible_"
        "google_gemma-3-12b-it_k1-2-3-4-5-6",
    ),
    (
        "Gemma 3 27B",
        "results/20260712_211003_think_twice_trs-deepmath_oracle_openai-compatible_"
        "google_gemma-3-27b-it_k1-2-3-4-5-6",
    ),
    (
        "Qwen 3 8B (thinking off)",
        "results/20260713_002119_think_twice_qwen3_8b_thinking_off_trs-deepmath_oracle_"
        "openai-compatible_Qwen_Qwen3-8B_k1-2-3-4-5-6",
    ),
]

BG = "#111315"
PANEL = "#171a1d"
PANEL_ALT = "#1b1f23"
GRID = "#343a40"
TEXT = "#eef1f4"
MUTED = "#aeb5bd"
GREEN = "#65d58a"
CORAL = "#ff8066"
CYAN = "#58b9e8"
GOLD = "#f2c14e"
WHITE = "#ffffff"


@dataclass
class ModelData:
    label: str
    run_dir: Path
    items: dict[tuple[str, int], dict[int, int]]
    accuracy: dict[int, float]
    errors: int

    def item_effects(self, expression: str) -> list[float]:
        effects: list[float] = []
        for values in self.items.values():
            if expression == "order_overall":
                value = ((values[2] - values[1]) + (values[4] - values[3])) / 2
            elif expression == "order_single":
                value = values[2] - values[1]
            elif expression == "order_repeated":
                value = values[4] - values[3]
            elif expression == "repeat_overall":
                value = ((values[3] - values[1]) + (values[4] - values[2])) / 2
            elif expression == "repeat_insight":
                value = values[3] - values[1]
            elif expression == "repeat_problem":
                value = values[4] - values[2]
            elif expression == "repeat_question":
                value = values[6] - values[5]
            else:
                raise ValueError(f"unknown effect expression: {expression}")
            effects.append(100 * value)
        return effects

    def effect(self, expression: str) -> float:
        return statistics.mean(self.item_effects(expression))

    def ci95(self, expression: str) -> tuple[float, float]:
        values = self.item_effects(expression)
        mean_value = statistics.mean(values)
        se = statistics.stdev(values) / math.sqrt(len(values))
        return mean_value - 1.96 * se, mean_value + 1.96 * se

    @property
    def order_single(self) -> float:
        return 100 * (self.accuracy[2] - self.accuracy[1])

    @property
    def order_repeated(self) -> float:
        return 100 * (self.accuracy[4] - self.accuracy[3])

    @property
    def repeat_insight(self) -> float:
        return 100 * (self.accuracy[3] - self.accuracy[1])

    @property
    def repeat_problem(self) -> float:
        return 100 * (self.accuracy[4] - self.accuracy[2])

    @property
    def question_only(self) -> float:
        return 100 * self.accuracy[5]

    @property
    def repeat_question(self) -> float:
        return 100 * (self.accuracy[6] - self.accuracy[5])


def load_model(label: str, relative_run_dir: str) -> ModelData:
    run_dir = ROOT / relative_run_dir
    rows = []
    with (run_dir / "results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if len(rows) != 6000:
        raise ValueError(f"{label}: expected 6000 rows, found {len(rows)}")

    items: dict[tuple[str, int], dict[int, int]] = {}
    for row in rows:
        key = (str(row["question_id"]), int(row["repeat_idx"]))
        items.setdefault(key, {})[int(row["k"])] = int(bool(row["is_correct"]))
    if len(items) != 1000 or any(set(values) != {1, 2, 3, 4, 5, 6} for values in items.values()):
        raise ValueError(f"{label}: incomplete or duplicate item-condition matrix")

    accuracy = {
        k: statistics.mean(values[k] for values in items.values())
        for k in (1, 2, 3, 4, 5, 6)
    }
    errors = sum(1 for row in rows if row.get("error"))
    return ModelData(label=label, run_dir=run_dir, items=items, accuracy=accuracy, errors=errors)


def text_node(
    x: float,
    y: float,
    content: str,
    *,
    size: int = 18,
    fill: str = TEXT,
    weight: str = "400",
    anchor: str = "start",
    opacity: float = 1.0,
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" dominant-baseline="middle" '
        f'opacity="{opacity:.3f}">{escape(content)}</text>'
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str,
    stroke: str = "none",
    radius: float = 0,
    opacity: float = 1.0,
) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'rx="{radius:.1f}" fill="{fill}" stroke="{stroke}" opacity="{opacity:.3f}"/>'
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str = GRID,
    width: float = 1,
    dash: str | None = None,
    opacity: float = 1.0,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width:.1f}" opacity="{opacity:.3f}"{dash_attr}/>'
    )


def circle(x: float, y: float, radius: float, *, fill: str, stroke: str = "none", width: float = 1) -> str:
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{width:.1f}"/>'
    )


def svg_document(width: int, height: int, title: str, parts: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            f"<title>{escape(title)}</title>",
            '<style>text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }</style>',
            rect(0, 0, width, height, fill=BG),
            *parts,
            "</svg>",
            "",
        ]
    )


def write_svg(path: Path, width: int, height: int, title: str, parts: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg_document(width, height, title, parts), encoding="utf-8")


def mix_color(low: tuple[int, int, int], high: tuple[int, int, int], t: float) -> str:
    bounded = max(0.0, min(1.0, t))
    rgb = tuple(round(a + (b - a) * bounded) for a, b in zip(low, high))
    return "#" + "".join(f"{value:02x}" for value in rgb)


def add_title(parts: list[str], title: str, subtitle: str) -> None:
    parts.append(text_node(40, 48, title, size=28, weight="700"))
    parts.append(text_node(40, 84, subtitle, size=16, fill=MUTED))


def add_model_separators(parts: list[str], y0: float, row_height: float, x1: float, x2: float) -> None:
    for after_index in (1, 3):
        y = y0 + (after_index + 1) * row_height
        parts.append(line(x1, y, x2, y, stroke="#4a5159", width=1.5))


def axis_scale(value: float, minimum: float, maximum: float, x1: float, x2: float) -> float:
    return x1 + ((value - minimum) / (maximum - minimum)) * (x2 - x1)


def add_effect_axis(
    parts: list[str],
    *,
    minimum: float,
    maximum: float,
    ticks: list[float],
    x1: float,
    x2: float,
    y1: float,
    y2: float,
) -> None:
    for tick in ticks:
        x = axis_scale(tick, minimum, maximum, x1, x2)
        color = "#78818a" if tick == 0 else GRID
        parts.append(line(x, y1, x, y2, stroke=color, width=1.5 if tick == 0 else 1))
        parts.append(text_node(x, y2 + 26, f"{tick:+.0f}", size=14, fill=MUTED, anchor="middle"))
    parts.append(text_node((x1 + x2) / 2, y2 + 54, "accuracy difference (percentage points)", size=14, fill=MUTED, anchor="middle"))


def figure_all_conditions(models: list[ModelData], output: Path) -> None:
    width, height = 1540, 820
    parts: list[str] = []
    add_title(
        parts,
        "Seven non-reasoning models across all six prompt conditions",
        "Accuracy; n=1,000 matched questions per cell. Darker green indicates higher accuracy.",
    )
    x0, table_width = 320.0, 1170.0
    column_width = table_width / 6
    y0, row_height = 205.0, 70.0
    headers = [
        ("C1", "insight-first x1", "{i,q}"),
        ("C2", "problem-first x1", "{q,i}"),
        ("C3", "insight-first x2", "{i,q,...,i,q}"),
        ("C4", "problem-first x2", "{q,i,...,q,i}"),
        ("C5", "problem only x1", "{q}"),
        ("C6", "problem only x2", "{q,...,q}"),
    ]
    header_colors = [CYAN, GOLD, GREEN, CORAL, "#9fb3c8", "#d6a96c"]
    for index, (condition, label, recipe) in enumerate(headers):
        center = x0 + (index + 0.5) * column_width
        parts.append(rect(x0 + index * column_width + 4, 126, column_width - 8, 58, fill=PANEL_ALT, radius=4))
        parts.append(rect(x0 + index * column_width + 4, 126, column_width - 8, 4, fill=header_colors[index], radius=2))
        parts.append(text_node(center, 146, f"{condition}  {label}", size=15, weight="700", anchor="middle"))
        parts.append(text_node(center, 169, recipe, size=13, fill=MUTED, anchor="middle"))

    for row_index, model in enumerate(models):
        y = y0 + row_index * row_height
        fill = PANEL if row_index % 2 == 0 else PANEL_ALT
        parts.append(rect(28, y, width - 56, row_height - 4, fill=fill, radius=3))
        parts.append(text_node(46, y + 25, model.label, size=17, weight="700"))
        error_text = "clean" if model.errors == 0 else f"{model.errors} saved errors"
        parts.append(text_node(46, y + 48, error_text, size=12, fill=MUTED))
        for k in range(1, 7):
            value = 100 * model.accuracy[k]
            t = (value - 10) / 65
            cell_fill = mix_color((88, 45, 48), (27, 116, 83), t)
            x = x0 + (k - 1) * column_width
            parts.append(rect(x + 5, y + 7, column_width - 10, row_height - 18, fill=cell_fill, radius=4))
            parts.append(text_node(x + column_width / 2, y + 34, f"{value:.1f}%", size=18, weight="700", anchor="middle"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(
        text_node(
            40,
            height - 42,
            "Rows with provider errors remain in the original n=1,000 denominators for consistency with the saved aggregates.",
            size=13,
            fill=MUTED,
        )
    )
    write_svg(output, width, height, "Accuracy across six prompt conditions", parts)


def figure_order_effect(models: list[ModelData], output: Path) -> None:
    width, height = 1500, 850
    parts: list[str] = []
    add_title(
        parts,
        "Marginal order effect is positive in all 7 non-reasoning models",
        "Problem-first minus insight-first, averaged over single and repeated prompts; bars show paired 95% CIs.",
    )
    parts.append(circle(405, 130, 6, fill=CYAN))
    parts.append(text_node(420, 130, "single", size=14, fill=MUTED))
    parts.append(circle(500, 130, 6, fill=GOLD))
    parts.append(text_node(515, 130, "repeated", size=14, fill=MUTED))
    parts.append(line(620, 130, 672, 130, stroke=GREEN, width=8))
    parts.append(text_node(686, 130, "marginal effect", size=14, fill=MUTED))

    x1, x2 = 355.0, 1325.0
    minimum, maximum = -2.0, 8.0
    y0, row_height = 205.0, 76.0
    y2 = y0 + len(models) * row_height
    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=[-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8],
        x1=x1,
        x2=x2,
        y1=175,
        y2=y2,
    )
    zero_x = axis_scale(0, minimum, maximum, x1, x2)

    for index, model in enumerate(models):
        y = y0 + index * row_height + row_height / 2
        parts.append(text_node(36, y, model.label, size=17, weight="700"))
        overall = model.effect("order_overall")
        ci_low, ci_high = model.ci95("order_overall")
        overall_x = axis_scale(overall, minimum, maximum, x1, x2)
        ci_x1 = axis_scale(ci_low, minimum, maximum, x1, x2)
        ci_x2 = axis_scale(ci_high, minimum, maximum, x1, x2)
        parts.append(line(zero_x, y, overall_x, y, stroke=GREEN, width=8, opacity=0.72))
        parts.append(line(ci_x1, y, ci_x2, y, stroke=WHITE, width=2))
        parts.append(line(ci_x1, y - 7, ci_x1, y + 7, stroke=WHITE, width=2))
        parts.append(line(ci_x2, y - 7, ci_x2, y + 7, stroke=WHITE, width=2))
        parts.append(circle(overall_x, y, 7, fill=GREEN, stroke=BG, width=2))
        parts.append(circle(axis_scale(model.order_single, minimum, maximum, x1, x2), y - 15, 5, fill=CYAN))
        parts.append(circle(axis_scale(model.order_repeated, minimum, maximum, x1, x2), y + 15, 5, fill=GOLD))
        parts.append(text_node(1455, y, f"{overall:+.2f} pp", size=16, fill=GREEN, weight="700", anchor="end"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(text_node(40, height - 28, "Marginal effect = 0.5[(C2-C1) + (C4-C3)].", size=13, fill=MUTED))
    write_svg(output, width, height, "Marginal order effects", parts)


def figure_repetition_by_order(models: list[ModelData], output: Path) -> None:
    width, height = 1500, 850
    positive_interactions = sum(1 for model in models if model.repeat_insight > model.repeat_problem)
    parts: list[str] = []
    add_title(
        parts,
        f"Repetition helps insight-first more in {positive_interactions} of 7 models",
        "Paired accuracy changes from x1 to x2; the two exceptions are visible rather than averaged away.",
    )
    parts.append(circle(430, 130, 7, fill=GREEN))
    parts.append(text_node(446, 130, "insight-first repetition (C3-C1)", size=14, fill=MUTED))
    parts.append(circle(730, 130, 7, fill=CORAL))
    parts.append(text_node(746, 130, "problem-first repetition (C4-C2)", size=14, fill=MUTED))

    x1, x2 = 355.0, 1265.0
    minimum, maximum = -2.0, 5.0
    y0, row_height = 205.0, 76.0
    y2 = y0 + len(models) * row_height
    add_effect_axis(parts, minimum=minimum, maximum=maximum, ticks=[-2, -1, 0, 1, 2, 3, 4, 5], x1=x1, x2=x2, y1=175, y2=y2)
    parts.append(text_node(1455, 169, "interaction", size=13, fill=MUTED, anchor="end"))

    for index, model in enumerate(models):
        y = y0 + index * row_height + row_height / 2
        parts.append(text_node(36, y, model.label, size=17, weight="700"))
        insight = model.repeat_insight
        problem = model.repeat_problem
        insight_x = axis_scale(insight, minimum, maximum, x1, x2)
        problem_x = axis_scale(problem, minimum, maximum, x1, x2)
        parts.append(line(insight_x, y, problem_x, y, stroke="#69727b", width=4))
        parts.append(circle(insight_x, y, 8, fill=GREEN, stroke=BG, width=2))
        parts.append(circle(problem_x, y, 8, fill=CORAL, stroke=BG, width=2))
        parts.append(text_node(insight_x, y - 19, f"{insight:+.1f}", size=13, fill=GREEN, weight="700", anchor="middle"))
        parts.append(text_node(problem_x, y + 21, f"{problem:+.1f}", size=13, fill=CORAL, weight="700", anchor="middle"))
        interaction = insight - problem
        interaction_color = GREEN if interaction > 0 else CORAL if interaction < 0 else MUTED
        parts.append(text_node(1455, y, f"{interaction:+.2f} pp", size=16, fill=interaction_color, weight="700", anchor="end"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(text_node(40, height - 28, "Interaction = (C3-C1) - (C4-C2); positive values favor the insight-first mechanism.", size=13, fill=MUTED))
    write_svg(output, width, height, "Repetition effects by prompt order", parts)


def figure_overall_repetition(models: list[ModelData], output: Path) -> None:
    width, height = 1500, 850
    positive = sum(1 for model in models if model.effect("repeat_overall") > 0)
    parts: list[str] = []
    add_title(
        parts,
        f"Marginal repetition effect is positive in {positive} of 7 models",
        "Repeated minus single prompts, averaged over both orders; bars show paired 95% CIs.",
    )
    x1, x2 = 355.0, 1325.0
    minimum, maximum = -2.5, 6.0
    y0, row_height = 190.0, 78.0
    y2 = y0 + len(models) * row_height
    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=[-2, -1, 0, 1, 2, 3, 4, 5, 6],
        x1=x1,
        x2=x2,
        y1=145,
        y2=y2,
    )
    zero_x = axis_scale(0, minimum, maximum, x1, x2)

    for index, model in enumerate(models):
        y = y0 + index * row_height + row_height / 2
        parts.append(text_node(36, y, model.label, size=17, weight="700"))
        effect = model.effect("repeat_overall")
        ci_low, ci_high = model.ci95("repeat_overall")
        effect_x = axis_scale(effect, minimum, maximum, x1, x2)
        ci_x1 = axis_scale(ci_low, minimum, maximum, x1, x2)
        ci_x2 = axis_scale(ci_high, minimum, maximum, x1, x2)
        color = GREEN if effect > 0 else CORAL
        parts.append(line(zero_x, y, effect_x, y, stroke=color, width=18, opacity=0.78))
        parts.append(line(ci_x1, y, ci_x2, y, stroke=WHITE, width=2))
        parts.append(line(ci_x1, y - 8, ci_x1, y + 8, stroke=WHITE, width=2))
        parts.append(line(ci_x2, y - 8, ci_x2, y + 8, stroke=WHITE, width=2))
        parts.append(circle(effect_x, y, 7, fill=color, stroke=BG, width=2))
        parts.append(text_node(1455, y, f"{effect:+.2f} pp", size=17, fill=color, weight="700", anchor="end"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(text_node(40, height - 28, "Marginal effect = 0.5[(C3-C1) + (C4-C2)]. Mistral Nemo is the near-zero exception.", size=13, fill=MUTED))
    write_svg(output, width, height, "Marginal repetition effects", parts)


def figure_split_repetition(models: list[ModelData], output: Path) -> None:
    width, height = 1800, 880
    parts: list[str] = []
    add_title(
        parts,
        "Repetition effects split by prompt order",
        "Accuracy change from x1 to x2 for the same 1,000 questions; bars show paired 95% CIs.",
    )

    insight_x1, insight_x2 = 360.0, 930.0
    problem_x1, problem_x2 = 1110.0, 1680.0
    minimum, maximum = -5.0, 7.5
    y0, row_height = 205.0, 76.0
    y2 = y0 + len(models) * row_height
    ticks = [-4, -2, 0, 2, 4, 6]

    insight_center = (insight_x1 + insight_x2) / 2
    problem_center = (problem_x1 + problem_x2) / 2
    parts.append(line(insight_x1, 126, insight_x2, 126, stroke=GREEN, width=4))
    parts.append(text_node(insight_center, 146, "Insight-first order", size=20, weight="700", anchor="middle"))
    parts.append(text_node(insight_center, 171, "C3-C1: {i,q} x2 minus {i,q} x1", size=13, fill=MUTED, anchor="middle"))
    parts.append(line(problem_x1, 126, problem_x2, 126, stroke=GOLD, width=4))
    parts.append(text_node(problem_center, 146, "Problem-first order", size=20, weight="700", anchor="middle"))
    parts.append(text_node(problem_center, 171, "C4-C2: {q,i} x2 minus {q,i} x1", size=13, fill=MUTED, anchor="middle"))

    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=ticks,
        x1=insight_x1,
        x2=insight_x2,
        y1=188,
        y2=y2,
    )
    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=ticks,
        x1=problem_x1,
        x2=problem_x2,
        y1=188,
        y2=y2,
    )

    for index, model in enumerate(models):
        y = y0 + index * row_height + row_height / 2
        parts.append(text_node(38, y, model.label, size=17, weight="700"))

        for expression, effect, x1, x2, positive_color, label_x in (
            ("repeat_insight", model.repeat_insight, insight_x1, insight_x2, GREEN, 1030.0),
            ("repeat_problem", model.repeat_problem, problem_x1, problem_x2, GOLD, 1770.0),
        ):
            ci_low, ci_high = model.ci95(expression)
            zero_x = axis_scale(0, minimum, maximum, x1, x2)
            effect_x = axis_scale(effect, minimum, maximum, x1, x2)
            ci_x1 = axis_scale(ci_low, minimum, maximum, x1, x2)
            ci_x2 = axis_scale(ci_high, minimum, maximum, x1, x2)
            color = positive_color if effect >= 0 else CORAL
            parts.append(line(zero_x, y, effect_x, y, stroke=color, width=17, opacity=0.78))
            parts.append(line(ci_x1, y, ci_x2, y, stroke=WHITE, width=2))
            parts.append(line(ci_x1, y - 8, ci_x1, y + 8, stroke=WHITE, width=2))
            parts.append(line(ci_x2, y - 8, ci_x2, y + 8, stroke=WHITE, width=2))
            parts.append(circle(effect_x, y, 7, fill=color, stroke=BG, width=2))
            parts.append(text_node(label_x, y, f"{effect:+.2f} pp", size=16, fill=color, weight="700", anchor="end"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(
        text_node(
            40,
            height - 25,
            "Both panels use the same scale. Positive values mean that repeating the ordered prompt increased accuracy.",
            size=13,
            fill=MUTED,
        )
    )
    write_svg(output, width, height, "Repetition effects split by prompt order", parts)


def figure_repetition_robustness(models: list[ModelData], output: Path) -> None:
    width, height = 2200, 900
    parts: list[str] = []
    mean_question_repeat = statistics.mean(model.repeat_question for model in models)
    mean_insight_repeat = statistics.mean(model.repeat_insight for model in models)
    mean_problem_repeat = statistics.mean(model.repeat_problem for model in models)
    add_title(
        parts,
        "Repetition effects with question-only controls",
        (
            "{q} is below both insight-containing baselines in all 7 models; "
            f"mean pure-question repetition is {mean_question_repeat:+.2f} pp versus "
            f"{mean_insight_repeat:+.2f}/{mean_problem_repeat:+.2f} pp with insights."
        ),
    )

    question_only_center = 392.0
    question_repeat_center = 565.0
    insight_x1, insight_x2 = 700.0, 1240.0
    problem_x1, problem_x2 = 1450.0, 1990.0
    insight_label_x, problem_label_x = 1370.0, 2170.0
    minimum, maximum = -5.0, 7.5
    y0, row_height = 215.0, 76.0
    y2 = y0 + len(models) * row_height
    ticks = [-4, -2, 0, 2, 4, 6]

    parts.append(text_node(38, 151, "Model", size=18, weight="700"))
    parts.append(line(330, 132, 454, 132, stroke=CYAN, width=4))
    parts.append(text_node(question_only_center, 151, "Question only", size=18, weight="700", anchor="middle"))
    parts.append(text_node(question_only_center, 176, "C5: {q} accuracy", size=12, fill=MUTED, anchor="middle"))
    parts.append(line(480, 132, 650, 132, stroke="#9fb3c8", width=4))
    parts.append(text_node(question_repeat_center, 151, "Question repetition", size=18, weight="700", anchor="middle"))
    parts.append(text_node(question_repeat_center, 176, "C6-C5: {q} x2 - {q} x1", size=12, fill=MUTED, anchor="middle"))

    insight_center = (insight_x1 + insight_x2) / 2
    problem_center = (problem_x1 + problem_x2) / 2
    parts.append(line(insight_x1, 132, insight_x2, 132, stroke=GREEN, width=4))
    parts.append(text_node(insight_center, 151, "Insight-first repetition", size=20, weight="700", anchor="middle"))
    parts.append(text_node(insight_center, 176, "C3-C1: {i,q} x2 - {i,q} x1", size=13, fill=MUTED, anchor="middle"))
    parts.append(line(problem_x1, 132, problem_x2, 132, stroke=GOLD, width=4))
    parts.append(text_node(problem_center, 151, "Problem-first repetition", size=20, weight="700", anchor="middle"))
    parts.append(text_node(problem_center, 176, "C4-C2: {q,i} x2 - {q,i} x1", size=13, fill=MUTED, anchor="middle"))

    parts.append(line(310, 126, 310, y2, stroke=GRID))
    parts.append(line(470, 126, 470, y2, stroke=GRID))
    parts.append(line(670, 126, 670, y2, stroke=GRID))
    parts.append(line(1410, 126, 1410, y2, stroke=GRID))

    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=ticks,
        x1=insight_x1,
        x2=insight_x2,
        y1=198,
        y2=y2,
    )
    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=ticks,
        x1=problem_x1,
        x2=problem_x2,
        y1=198,
        y2=y2,
    )

    for index, model in enumerate(models):
        y = y0 + index * row_height + row_height / 2
        parts.append(text_node(38, y, model.label, size=17, weight="700"))
        parts.append(text_node(question_only_center, y, f"{model.question_only:.1f}%", size=17, fill=CYAN, weight="700", anchor="middle"))
        question_repeat_color = CYAN if model.repeat_question > 0 else CORAL if model.repeat_question < 0 else MUTED
        parts.append(
            text_node(
                question_repeat_center,
                y,
                f"{model.repeat_question:+.2f} pp",
                size=16,
                fill=question_repeat_color,
                weight="700",
                anchor="middle",
            )
        )

        for expression, effect, x1, x2, positive_color, label_x in (
            ("repeat_insight", model.repeat_insight, insight_x1, insight_x2, GREEN, insight_label_x),
            ("repeat_problem", model.repeat_problem, problem_x1, problem_x2, GOLD, problem_label_x),
        ):
            ci_low, ci_high = model.ci95(expression)
            zero_x = axis_scale(0, minimum, maximum, x1, x2)
            effect_x = axis_scale(effect, minimum, maximum, x1, x2)
            ci_x1 = axis_scale(ci_low, minimum, maximum, x1, x2)
            ci_x2 = axis_scale(ci_high, minimum, maximum, x1, x2)
            color = positive_color if effect >= 0 else CORAL
            parts.append(line(zero_x, y, effect_x, y, stroke=color, width=17, opacity=0.78))
            parts.append(line(ci_x1, y, ci_x2, y, stroke=WHITE, width=2))
            parts.append(line(ci_x1, y - 8, ci_x1, y + 8, stroke=WHITE, width=2))
            parts.append(line(ci_x2, y - 8, ci_x2, y + 8, stroke=WHITE, width=2))
            parts.append(circle(effect_x, y, 7, fill=color, stroke=BG, width=2))
            parts.append(text_node(label_x, y, f"{effect:+.2f} pp", size=16, fill=color, weight="700", anchor="end"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(
        text_node(
            40,
            height - 25,
            "Effect panels use the same scale and paired 95% CIs. Control values use the same 1,000 matched questions per model.",
            size=13,
            fill=MUTED,
        )
    )
    write_svg(output, width, height, "Repetition effects with question-only controls", parts)


def figure_split_order(models: list[ModelData], output: Path) -> None:
    width, height = 1800, 880
    parts: list[str] = []
    add_title(
        parts,
        "Order effects split by repetition",
        "Problem-first minus insight-first accuracy for the same 1,000 questions; bars show paired 95% CIs.",
    )

    single_x1, single_x2 = 360.0, 930.0
    repeated_x1, repeated_x2 = 1110.0, 1680.0
    minimum, maximum = -4.0, 9.0
    y0, row_height = 205.0, 76.0
    y2 = y0 + len(models) * row_height
    ticks = [-4, -2, 0, 2, 4, 6, 8]

    single_center = (single_x1 + single_x2) / 2
    repeated_center = (repeated_x1 + repeated_x2) / 2
    parts.append(line(single_x1, 126, single_x2, 126, stroke=CYAN, width=4))
    parts.append(text_node(single_center, 146, "Single prompts (x1)", size=20, weight="700", anchor="middle"))
    parts.append(text_node(single_center, 171, "C2-C1: {q,i} minus {i,q}", size=13, fill=MUTED, anchor="middle"))
    parts.append(line(repeated_x1, 126, repeated_x2, 126, stroke=GOLD, width=4))
    parts.append(text_node(repeated_center, 146, "Repeated prompts (x2)", size=20, weight="700", anchor="middle"))
    parts.append(text_node(repeated_center, 171, "C4-C3: {q,i} x2 minus {i,q} x2", size=13, fill=MUTED, anchor="middle"))

    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=ticks,
        x1=single_x1,
        x2=single_x2,
        y1=188,
        y2=y2,
    )
    add_effect_axis(
        parts,
        minimum=minimum,
        maximum=maximum,
        ticks=ticks,
        x1=repeated_x1,
        x2=repeated_x2,
        y1=188,
        y2=y2,
    )

    for index, model in enumerate(models):
        y = y0 + index * row_height + row_height / 2
        parts.append(text_node(38, y, model.label, size=17, weight="700"))

        for expression, effect, x1, x2, positive_color, label_x in (
            ("order_single", model.order_single, single_x1, single_x2, CYAN, 1030.0),
            ("order_repeated", model.order_repeated, repeated_x1, repeated_x2, GOLD, 1770.0),
        ):
            ci_low, ci_high = model.ci95(expression)
            zero_x = axis_scale(0, minimum, maximum, x1, x2)
            effect_x = axis_scale(effect, minimum, maximum, x1, x2)
            ci_x1 = axis_scale(ci_low, minimum, maximum, x1, x2)
            ci_x2 = axis_scale(ci_high, minimum, maximum, x1, x2)
            color = positive_color if effect >= 0 else CORAL
            parts.append(line(zero_x, y, effect_x, y, stroke=color, width=17, opacity=0.78))
            parts.append(line(ci_x1, y, ci_x2, y, stroke=WHITE, width=2))
            parts.append(line(ci_x1, y - 8, ci_x1, y + 8, stroke=WHITE, width=2))
            parts.append(line(ci_x2, y - 8, ci_x2, y + 8, stroke=WHITE, width=2))
            parts.append(circle(effect_x, y, 7, fill=color, stroke=BG, width=2))
            parts.append(text_node(label_x, y, f"{effect:+.2f} pp", size=16, fill=color, weight="700", anchor="end"))

    add_model_separators(parts, y0, row_height, 28, width - 28)
    parts.append(
        text_node(
            40,
            height - 25,
            "Both panels use the same scale. Positive values mean problem-first ordering achieved higher accuracy.",
            size=13,
            fill=MUTED,
        )
    )
    write_svg(output, width, height, "Order effects split by repetition", parts)


def main(argv: list[str]) -> int:
    output_dir = Path(argv[0]) if argv else ROOT / "results"
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    models = [load_model(label, run_dir) for label, run_dir in RUNS]

    outputs = [
        output_dir / "nonreasoning_7_models_01_all_conditions_20260713.svg",
        output_dir / "nonreasoning_7_models_02_order_effect_20260713.svg",
        output_dir / "nonreasoning_7_models_03_repetition_by_order_20260713.svg",
        output_dir / "nonreasoning_7_models_04_overall_repetition_20260713.svg",
        output_dir / "nonreasoning_7_models_05_repetition_split_panels_20260713.svg",
        output_dir / "nonreasoning_7_models_06_order_effect_split_panels_20260713.svg",
        output_dir / "nonreasoning_7_models_07_repetition_robustness_20260713.svg",
    ]
    figure_all_conditions(models, outputs[0])
    figure_order_effect(models, outputs[1])
    figure_repetition_by_order(models, outputs[2])
    figure_overall_repetition(models, outputs[3])
    figure_split_repetition(models, outputs[4])
    figure_split_order(models, outputs[5])
    figure_repetition_robustness(models, outputs[6])

    print("model\torder overall\trep insight\trep problem\trep overall\terrors")
    for model in models:
        print(
            f"{model.label}\t{model.effect('order_overall'):+.2f}\t"
            f"{model.repeat_insight:+.2f}\t{model.repeat_problem:+.2f}\t"
            f"{model.effect('repeat_overall'):+.2f}\t{model.errors}"
        )
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
