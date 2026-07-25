from __future__ import annotations

import re


def find_last_boxed(text: str) -> str:
    marker = r"\boxed"
    idx = text.rfind(marker)
    if idx < 0:
        return ""
    brace_idx = text.find("{", idx)
    if brace_idx < 0:
        return ""
    depth = 0
    chars: list[str] = []
    for ch in text[brace_idx:]:
        if ch == "{":
            depth += 1
            if depth > 1:
                chars.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(chars).strip()
            chars.append(ch)
        else:
            chars.append(ch)
    return ""


def strip_latex_wrappers(text: str) -> str:
    out = text.strip()
    out = re.sub(r"\\boxed\s*{([^{}]*)}", r"\1", out)
    out = re.sub(r"\\textbf\s*{([^{}]*)}", r"\1", out)
    out = re.sub(r"\\mathrm\s*{([^{}]*)}", r"\1", out)
    out = re.sub(r"\\text\s*{([^{}]*)}", r"\1", out)
    return out.strip()


THINK_CLOSE_TAG = "</think>"


def strip_think_block(text: str) -> str:
    """Visible answer text of a thinking-mode response.

    Providers that inline the reasoning trace (e.g. Featherless with Qwen3
    /think) return "<think>...</think>ANSWER" in the completion text. The
    answer must be extracted from the part after the last closing tag, not
    from the trace, where intermediate \\boxed{} candidates would shadow the
    real final answer. Returns text unchanged when no closing tag is present.
    """
    idx = text.rfind(THINK_CLOSE_TAG)
    if idx < 0:
        return text
    return text[idx + len(THINK_CLOSE_TAG):]


def extract_final_answer(text: str) -> str:
    if not text:
        return ""
    visible = strip_think_block(text)
    if visible is not text:
        # Only an explicit marker (boxed / "final answer:") in the visible
        # part may override the trace: a \boxed{} the model committed to while
        # thinking is more reliable than a marker-free closing line.
        marked = _extract_marked_answer(visible)
        if marked:
            return marked
    return _extract_final_answer_impl(text)


def _extract_marked_answer(text: str) -> str:
    boxed = find_last_boxed(text)
    if boxed:
        return boxed

    patterns = [
        r"(?im)^\s*final\s+answer\s*[:：]\s*(.+?)\s*$",
        r"(?im)^\s*answer\s*[:：]\s*(.+?)\s*$",
        r"(?is)\bthe\s+final\s+answer\s+is\s+(.+?)(?:\n|$)",
        r"(?is)\bthe\s+answer\s+is\s+(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, text))
        if matches:
            return matches[-1].group(1).strip()
    return ""


def _extract_final_answer_impl(text: str) -> str:
    marked = _extract_marked_answer(text)
    if marked:
        return marked

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def extract_choice(text: str) -> str:
    text = strip_latex_wrappers(text)
    match = re.search(r"\(([A-E])\)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"\b([A-E])\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""


def normalize_answer(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("∞", r"\infty")
    text = text.replace("π", r"\pi")
    text = text.replace("−", "-")
    text = re.sub(r"\\boxed\s*{([^{}]*)}", r"\1", text)
    text = re.sub(r"\\text\s*{([^{}]*)}", r"\1", text)
    text = text.replace(r"\dfrac", r"\frac")
    text = text.replace(r"\tfrac", r"\frac")
    text = re.sub(r"\\frac\s*{([^{}]+)}\s*{([^{}]+)}", r"\1/\2", text)
    for token in ["$", r"\(", r"\)", r"\[", r"\]", "`", "*"]:
        text = text.replace(token, "")
    for token in [r"\left", r"\right"]:
        text = text.replace(token, "")
    text = text.replace(" ", "")
    text = text.rstrip(".;,")
    if text in {r"\varnothing", "∅", "emptyset", "varnothing"}:
        return r"\emptyset"
    if text.startswith(("nosuch", "novalue", "nosolution", "nonexistent", "non-existent")):
        return r"\emptyset"
    return text


def answers_match(candidate: str, gold: str) -> bool:
    candidate_norm = normalize_answer(candidate)
    gold_norm = normalize_answer(gold)
    if not candidate_norm or not gold_norm:
        return False
    return candidate_norm == gold_norm


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)
