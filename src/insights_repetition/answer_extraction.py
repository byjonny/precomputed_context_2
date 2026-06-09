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


def extract_final_answer(text: str) -> str:
    if not text:
        return ""
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
    text = re.sub(r"\\boxed\s*{([^{}]*)}", r"\1", text)
    text = re.sub(r"\\text\s*{([^{}]*)}", r"\1", text)
    for token in ["$", r"\(", r"\)", r"\[", r"\]", "`", "*"]:
        text = text.replace(token, "")
    for token in [r"\left", r"\right"]:
        text = text.replace(token, "")
    text = text.replace(" ", "")
    text = text.rstrip(".;,")
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
