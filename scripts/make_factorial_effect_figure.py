#!/usr/bin/env python3
"""Render a dark 2x2 order x repetition effect table as SVG.

Usage:
    python3 scripts/make_factorial_effect_figure.py OUT.svg RUN_DIR [RUN_DIR...]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape


def load_rows(run_dir: Path) -> list[dict]:
    with (run_dir / "results.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def group_by_item(rows: list[dict]) -> dict[tuple, dict[int, bool]]:
    by_item: dict[tuple, dict[int, bool]] = {}
    for row in rows:
        key = (row.get("run_id"), row["question_id"], row["repeat_idx"])
        by_item.setdefault(key, {})[int(row["k"])] = bool(row["is_correct"])
    return by_item


def acc(by_item: dict[tuple, dict[int, bool]], k: int) -> tuple[float, int]:
    vals = [v[k] for v in by_item.values() if k in v]
    return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)


def mcnemar(by_item: dict[tuple, dict[int, bool]], ka: int, kb: int) -> dict[str, float | int]:
    b = c = 0
    n = 0
    for v in by_item.values():
        if ka in v and kb in v:
            n += 1
            if (not v[ka]) and v[kb]:
                b += 1
            elif v[ka] and (not v[kb]):
                c += 1
    if b + c == 0:
        return {"n": n, "b": b, "c": c, "chi2": 0.0, "p": 1.0}
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(chi2 / 2))
    return {"n": n, "b": b, "c": c, "chi2": chi2, "p": p}


def p_text(p: float) -> str:
    if p < 0.001:
        return "p<0.001"
    if p < 0.05:
        return f"p={p:.3f}"
    return "ns"


def sig_mark(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def effect_text(delta: float, p: float) -> str:
    mark = sig_mark(p)
    suffix = f" {mark}" if mark else ""
    return f"{delta:+.2f} pp ({p_text(p)}){suffix}"


def model_label(run_dir: Path, rows: list[dict]) -> str:
    cfg_path = run_dir / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        label = str(cfg.get("model") or rows[0].get("model") or run_dir.name)
        prompt_suffix = (cfg.get("prompt_config") or {}).get("prompt_suffix")
        if prompt_suffix == "/think":
            return f"{label} - Thinking ON"
        if prompt_suffix == "/no_think":
            return f"{label} - Thinking OFF"
        return label
    return str(rows[0].get("model") or run_dir.name)


def panel_data(run_dir: Path) -> dict:
    rows = load_rows(run_dir)
    by_item = group_by_item(rows)
    accuracy = {k: acc(by_item, k) for k in (1, 2, 3, 4)}
    tests = {
        "rep_insight": mcnemar(by_item, 1, 3),
        "rep_problem": mcnemar(by_item, 2, 4),
        "order_single": mcnemar(by_item, 1, 2),
        "order_repeat": mcnemar(by_item, 3, 4),
    }
    errors = sum(1 for row in rows if row.get("error"))
    expected = len(by_item) * len({int(row["k"]) for row in rows})
    return {
        "run_dir": run_dir,
        "model": model_label(run_dir, rows),
        "rows": rows,
        "by_item": by_item,
        "accuracy": accuracy,
        "tests": tests,
        "errors": errors,
        "expected": expected,
    }


def text_node(
    x: float,
    y: float,
    content: str,
    *,
    fill: str,
    size: int,
    weight: str = "400",
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" dominant-baseline="middle">'
        f"{escape(content)}</text>"
    )


def rect(x: float, y: float, w: float, h: float, *, fill: str, stroke: str = "#2a2e33") -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )


def draw_panel(data: dict, top: float, width: int = 1300, panel_h: int = 430) -> list[str]:
    bg = "#121416"
    header = "#1b1e22"
    cell = "#171a1d"
    grid = "#2a2e33"
    text = "#d6d8dc"
    muted = "#aeb4bd"
    good = "#79d38b"
    bad = "#ff8f7a"
    accent = "#bfc7d5"

    parts: list[str] = []
    parts.append(rect(0, top, width, panel_h, fill=bg, stroke=bg))

    rows = data["rows"]
    n_per_cell = min(data["accuracy"][k][1] for k in (1, 2, 3, 4))
    run_status = "Clean run" if data["errors"] == 0 else "Completed run"
    status = (
        f"{run_status} - {len(rows):,}/{data['expected']:,} rows, "
        f"{data['errors']} errors, n={n_per_cell:,} per cell"
    )
    parts.append(text_node(28, top + 44, data["model"], fill=text, size=24, weight="700"))
    parts.append(text_node(28, top + 82, status, fill=muted, size=16))

    x0 = 28
    y0 = top + 120
    table_w = width - 56
    table_h = 240
    col_w = [0.29, 0.20, 0.20, 0.31]
    row_h = [0.24, 0.25, 0.25, 0.26]

    xs = [x0]
    for cw in col_w:
        xs.append(xs[-1] + table_w * cw)
    ys = [y0]
    for rh in row_h:
        ys.append(ys[-1] + table_h * rh)

    for r in range(4):
        for c in range(4):
            parts.append(
                rect(
                    xs[c],
                    ys[r],
                    xs[c + 1] - xs[c],
                    ys[r + 1] - ys[r],
                    fill=header if r == 0 else cell,
                    stroke=grid,
                )
            )

    headers = ["", "x1 (single)", "x2 (repeated)", "repetition effect"]
    for c, value in enumerate(headers):
        parts.append(
            text_node(
                (xs[c] + xs[c + 1]) / 2,
                (ys[0] + ys[1]) / 2,
                value,
                fill=accent,
                size=18,
                weight="700",
                anchor="middle",
            )
        )

    a = {k: data["accuracy"][k][0] * 100 for k in (1, 2, 3, 4)}
    tests = data["tests"]
    body = [
        [
            "insight-first  {i,q}",
            f"{a[1]:.2f}%",
            f"{a[3]:.2f}%",
            effect_text(a[3] - a[1], float(tests["rep_insight"]["p"])),
        ],
        [
            "problem-first  {q,i}",
            f"{a[2]:.2f}%",
            f"{a[4]:.2f}%",
            effect_text(a[4] - a[2], float(tests["rep_problem"]["p"])),
        ],
        [
            "order effect",
            effect_text(a[2] - a[1], float(tests["order_single"]["p"])),
            effect_text(a[4] - a[3], float(tests["order_repeat"]["p"])),
            "",
        ],
    ]

    for r, row in enumerate(body, start=1):
        for c, value in enumerate(row):
            color = text
            if c == 3 and r in (1, 2):
                color = good if value.startswith("+") else bad
            if r == 3 and c in (1, 2):
                color = good if value.startswith("+") else bad
            if c == 0:
                parts.append(text_node(xs[c] + 16, (ys[r] + ys[r + 1]) / 2, value, fill=color, size=18, weight="700"))
            else:
                parts.append(
                    text_node(
                        (xs[c] + xs[c + 1]) / 2,
                        (ys[r] + ys[r + 1]) / 2,
                        value,
                        fill=color,
                        size=18,
                        anchor="middle",
                    )
                )

    interaction = (a[3] - a[1]) - (a[4] - a[2])
    parts.append(
        text_node(
            28,
            top + panel_h - 34,
            f"Interaction: {interaction:+.2f} pp  (positive means repetition helps insight-first more)",
            fill=muted,
            size=15,
        )
    )
    return parts


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    out = Path(argv[0])
    panels = [panel_data(Path(arg)) for arg in argv[1:]]
    width = 1300
    panel_h = 430
    height = panel_h * len(panels)

    body: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }</style>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#121416"/>',
    ]
    for idx, data in enumerate(panels):
        body.extend(draw_panel(data, idx * panel_h, width=width, panel_h=panel_h))
    body.append("</svg>")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
