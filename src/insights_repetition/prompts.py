from __future__ import annotations

from typing import Any


DIRECT_TEMPLATE = """You are a helpful and harmless assistant.
Let's think step by step.
End your response with exactly one line in this format:
Final answer: <answer>

Problem:
{question}
"""


TRS_TEMPLATE = """You are a helpful and harmless assistant.
You may be given a Solving Hints section. Use it only if relevant; otherwise ignore it completely.
If you find these solving hints useful, please try to reduce the number of tokens used while staying correct.
End your response with exactly one line in this format:
Final answer: <answer>

[Solving Hints]
{hints}
[/Solving Hints]

Problem:
{question}
"""


FULL_BLOCK_TEMPLATE = """You are a helpful and harmless assistant.
You may be given repeated problem-solving blocks. Use them only if relevant; otherwise ignore them completely.
If you find these blocks useful, please try to reduce the number of tokens used while staying correct.
End your response with exactly one line in this format:
Final answer: <answer>

{blocks}
"""


FULL_BLOCK_WITH_HINT_TEMPLATE = """[Solving Hints]
{hints}
[/Solving Hints]

Problem:
{question}"""


FULL_BLOCK_PROBLEM_ONLY_TEMPLATE = """Problem:
{question}"""


SEQUENCE_TEMPLATE = """You are a helpful and harmless assistant.
You may be given a Solving Hints section. Use it only if relevant; otherwise ignore it completely.
If you find these solving hints useful, please try to reduce the number of tokens used while staying correct.
End your response with exactly one line in this format:
Final answer: <answer>

{parts}
"""


INSIGHT_PART_TEMPLATE = """[Solving Hints]
{hints}
[/Solving Hints]"""


QUESTION_PART_TEMPLATE = """Problem:
{question}"""


DEFAULT_REPEAT_DELIMITER = "\n\nLet me repeat it:\n\n"
DEFAULT_HINT_DELIMITER = DEFAULT_REPEAT_DELIMITER
DEFAULT_PROBLEM_DELIMITER = DEFAULT_REPEAT_DELIMITER
DEFAULT_BLOCK_DELIMITER = DEFAULT_REPEAT_DELIMITER


# Single-source preamble: set prompt_config["preamble"] to replace the
# instruction header of every built-in template at once (the {q} direct
# template, the [Solving Hints] template, and the sequence template share
# their body structure below). An explicit per-template override in the
# config still wins; configs without "preamble" behave exactly as before.
_PREAMBLE_BODIES = {
    "direct_template": "\n\nProblem:\n{question}\n",
    "hinted_template": "\n\n[Solving Hints]\n{hints}\n[/Solving Hints]\n\nProblem:\n{question}\n",
    "sequence_template": "\n\n{parts}\n",
}


def _template(prompt_config: dict[str, Any], key: str, default: str) -> str:
    explicit = prompt_config.get(key)
    if explicit is not None:
        return str(explicit)
    preamble = prompt_config.get("preamble")
    if preamble is not None and key in _PREAMBLE_BODIES:
        return str(preamble).rstrip("\n") + _PREAMBLE_BODIES[key]
    return default


def _positive_int(value: Any, default: int) -> int:
    if value is None:
        return default
    parsed = int(value)
    return max(0, parsed)


def _config_value(prompt_config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in prompt_config:
            return prompt_config[key]
    return default


def _value_for_k(value: Any, k: int) -> Any:
    if isinstance(value, dict):
        return value.get(str(k), value.get(k))
    if isinstance(value, (list, tuple)):
        if k >= len(value):
            raise ValueError(f"prompt repetition array has no entry for k={k}")
        return value[k]
    return value


def _condition_for_k(prompt_config: dict[str, Any], k: int) -> dict[str, Any] | None:
    conditions = prompt_config.get("conditions")
    if isinstance(conditions, dict):
        condition = conditions.get(str(k), conditions.get(k))
        return condition if isinstance(condition, dict) else None
    if isinstance(conditions, list):
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            condition_id = condition.get("k", condition.get("id"))
            if condition_id == k or str(condition_id) == str(k):
                return condition
    return None


def _insight_repetitions(k: int, prompt_config: dict[str, Any]) -> int:
    condition = _condition_for_k(prompt_config, k)
    condition_value = (
        _config_value(
            condition,
            "repeat_insight",
            "insight_repetitions",
            "hint_repetitions",
            "skill_repetitions",
            "insight_copies",
            "skill_copies",
            "i",
            default=None,
        )
        if condition
        else None
    )
    if condition_value is not None:
        return _positive_int(_value_for_k(condition_value, k), max(0, k))

    value = _config_value(
        prompt_config,
        "repeat_insight",
        "insight_repetitions",
        "hint_repetitions",
        "skill_repetitions",
        "insight_copies",
        "skill_copies",
        default="k",
    )
    value = _value_for_k(value, k)
    if value == "k":
        return max(0, k)
    return _positive_int(value, max(0, k))


def _problem_repetitions(k: int, prompt_config: dict[str, Any]) -> int:
    condition = _condition_for_k(prompt_config, k)
    condition_value = (
        _config_value(
            condition,
            "repeat_question",
            "repeat_problem",
            "question_repetitions",
            "problem_repetitions",
            "question_copies",
            "problem_copies",
            "q",
            default=None,
        )
        if condition
        else None
    )
    if condition_value is not None:
        return _positive_int(_value_for_k(condition_value, k), 1)

    value = _config_value(
        prompt_config,
        "repeat_question",
        "repeat_problem",
        "question_repetitions",
        "problem_repetitions",
        "question_copies",
        "problem_copies",
        default=1,
    )
    value = _value_for_k(value, k)
    return _positive_int(
        value,
        1,
    )


def _repeat_delimiter(prompt_config: dict[str, Any], specific_key: str, default: str) -> str:
    return str(_config_value(prompt_config, specific_key, "separator", "repeat_delimiter", default=default))


def _layout(prompt_config: dict[str, Any]) -> str:
    value = str(_config_value(prompt_config, "mode", "layout", "style", default="separate"))
    aliases = {
        "block": "full_block",
        "full-block": "full_block",
        "fullblock": "full_block",
        "explicit": "sequence",
        "custom": "sequence",
    }
    return aliases.get(value, value)


def _format(template: str, **values: Any) -> str:
    return template.format(**values)


def _as_sequence(value: Any) -> list[Any]:
    if isinstance(value, str):
        text = value.strip()
        if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
            text = text[1:-1]
        return [part.strip() for part in text.replace(",", " ").split() if part.strip()]
    if isinstance(value, (list, tuple)):
        return list(value)
    raise ValueError("prompt sequence must be a list or a whitespace/comma-separated string")


def _sequence_from_condition(condition: Any) -> list[Any] | None:
    if isinstance(condition, dict):
        if "sequence" in condition:
            return _as_sequence(condition["sequence"])
        if "parts" in condition:
            return _as_sequence(condition["parts"])
        return None
    return _as_sequence(condition)


def _sequence_for_k(prompt_config: dict[str, Any], k: int) -> list[Any] | None:
    sequence_by_k = prompt_config.get("sequence_by_k")
    if isinstance(sequence_by_k, dict):
        condition = sequence_by_k.get(str(k), sequence_by_k.get(k))
        if condition is not None:
            return _sequence_from_condition(condition)

    conditions = prompt_config.get("conditions")
    if isinstance(conditions, dict):
        condition = conditions.get(str(k), conditions.get(k))
        if condition is not None:
            return _sequence_from_condition(condition)
    elif isinstance(conditions, list):
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            condition_id = condition.get("k", condition.get("id"))
            if condition_id == k or str(condition_id) == str(k):
                return _sequence_from_condition(condition)

    if "sequence" in prompt_config:
        return _as_sequence(prompt_config["sequence"])
    if "parts" in prompt_config:
        return _as_sequence(prompt_config["parts"])
    return None


def _sequence_token(part: Any) -> str:
    token = part.get("type") if isinstance(part, dict) else part
    return str(token).strip().lower()


def _canonical_sequence_counts(sequence: list[Any]) -> tuple[int, int] | None:
    tokens = [_sequence_token(part) for part in sequence]
    insight_tokens = {"i", "insight", "s", "skill", "hint", "h"}
    question_tokens = {"q", "question", "problem"}
    if any(token not in insight_tokens | question_tokens for token in tokens):
        return None

    seen_question = False
    insight_count = 0
    question_count = 0
    for token in tokens:
        if token in insight_tokens:
            if seen_question:
                return None
            insight_count += 1
        elif token in question_tokens:
            seen_question = True
            question_count += 1

    if question_count <= 0:
        return None
    if insight_count == 0:
        return (0, 1) if question_count == 1 else None
    if question_count != 1:
        return None
    return insight_count, question_count


def _render_sequence_part(part: Any, question: str, skill_text: str, separator: str) -> str:
    token = _sequence_token(part)
    if token in {"q", "question", "problem"}:
        return QUESTION_PART_TEMPLATE.format(question=question)
    if token in {"i", "insight", "s", "skill", "hint", "h"}:
        return INSIGHT_PART_TEMPLATE.format(hints=skill_text.strip())
    if token in {"sep", "separator", "repeat"}:
        return separator.strip()
    raise ValueError(f"unknown prompt sequence part: {part!r}")


def repeated_hints(skill_text: str, k: int, delimiter: str = DEFAULT_HINT_DELIMITER) -> str:
    if k <= 0:
        return ""
    return delimiter.join(skill_text.strip() for _ in range(k))


def repeated_problem(question: str, repetitions: int, delimiter: str = DEFAULT_PROBLEM_DELIMITER) -> str:
    if repetitions <= 0:
        return ""
    return delimiter.join(question.strip() for _ in range(repetitions))


def build_separate_prompt(question: str, skill_text: str, k: int, prompt_config: dict[str, Any]) -> str:
    insight_count = _insight_repetitions(k, prompt_config)
    problem_count = _problem_repetitions(k, prompt_config)
    hint_delimiter = _repeat_delimiter(prompt_config, "hint_delimiter", DEFAULT_HINT_DELIMITER)
    problem_delimiter = _repeat_delimiter(prompt_config, "problem_delimiter", DEFAULT_PROBLEM_DELIMITER)
    problem_text = repeated_problem(question, problem_count, problem_delimiter)
    hints = repeated_hints(skill_text, insight_count, hint_delimiter)

    values = {
        "question": problem_text,
        "problem": problem_text,
        "hints": hints,
        "skill_text": skill_text,
        "k": k,
        "insight_repetitions": insight_count,
        "problem_repetitions": problem_count,
    }
    if not hints.strip():
        template = _template(prompt_config, "direct_template", DIRECT_TEMPLATE)
        return _format(template, **values)

    template = _template(prompt_config, "hinted_template", TRS_TEMPLATE)
    return _format(template, **values)


def build_full_block_prompt(question: str, skill_text: str, k: int, prompt_config: dict[str, Any]) -> str:
    insight_count = _insight_repetitions(k, prompt_config)
    problem_count = _problem_repetitions(k, prompt_config)
    block_count = max(insight_count, problem_count, 1)
    block_delimiter = _repeat_delimiter(prompt_config, "block_delimiter", DEFAULT_BLOCK_DELIMITER)
    block_template = str(prompt_config.get("block_template", FULL_BLOCK_WITH_HINT_TEMPLATE))
    problem_only_template = str(prompt_config.get("problem_only_block_template", FULL_BLOCK_PROBLEM_ONLY_TEMPLATE))

    blocks: list[str] = []
    for index in range(1, block_count + 1):
        has_hint = index <= insight_count and bool(skill_text.strip())
        has_problem = index <= problem_count
        if has_hint and has_problem:
            blocks.append(
                _format(
                    block_template,
                    index=index,
                    question=question,
                    problem=question,
                    hints=skill_text.strip(),
                    skill_text=skill_text,
                    k=k,
                    insight_repetitions=insight_count,
                    problem_repetitions=problem_count,
                )
            )
        elif has_problem:
            blocks.append(
                _format(
                    problem_only_template,
                    index=index,
                    question=question,
                    problem=question,
                    hints="",
                    skill_text=skill_text,
                    k=k,
                    insight_repetitions=insight_count,
                    problem_repetitions=problem_count,
                )
            )

    template = str(prompt_config.get("full_block_template", FULL_BLOCK_TEMPLATE))
    return _format(
        template,
        blocks=block_delimiter.join(blocks),
        question=question,
        problem=question,
        hints=repeated_hints(skill_text, insight_count),
        skill_text=skill_text,
        k=k,
        insight_repetitions=insight_count,
        problem_repetitions=problem_count,
    )


def build_sequence_prompt(question: str, skill_text: str, k: int, prompt_config: dict[str, Any]) -> str:
    sequence = _sequence_for_k(prompt_config, k)
    if sequence is None:
        raise ValueError("sequence prompt mode requires sequence, parts, sequence_by_k, or conditions")
    canonical_counts = _canonical_sequence_counts(sequence)
    if canonical_counts is not None:
        insight_count, question_count = canonical_counts
        separate_config = dict(prompt_config)
        separate_config["repeat_insight"] = insight_count
        separate_config["repeat_question"] = question_count
        return build_separate_prompt(question, skill_text, k, separate_config)

    separator = _repeat_delimiter(prompt_config, "separator", DEFAULT_REPEAT_DELIMITER)
    parts = [_render_sequence_part(part, question, skill_text, separator) for part in sequence]
    template = _template(prompt_config, "sequence_template", SEQUENCE_TEMPLATE)
    return _format(
        template,
        parts="\n\n".join(part for part in parts if part.strip()),
        question=question,
        problem=question,
        hints=skill_text,
        skill_text=skill_text,
        k=k,
    )


def build_prompt(question: str, skill_text: str, k: int, prompt_config: dict[str, Any] | None = None) -> str:
    if prompt_config is None:
        if k <= 0:
            return DIRECT_TEMPLATE.format(question=question)
        return TRS_TEMPLATE.format(question=question, hints=repeated_hints(skill_text, k))

    layout = _layout(prompt_config)
    if layout == "sequence" or _sequence_for_k(prompt_config, k) is not None:
        prompt = build_sequence_prompt(question, skill_text, k, prompt_config)
    elif layout == "full_block":
        prompt = build_full_block_prompt(question, skill_text, k, prompt_config)
    else:
        if layout != "separate":
            raise ValueError(f"unknown prompt layout: {layout}")
        prompt = build_separate_prompt(question, skill_text, k, prompt_config)

    suffix = str(prompt_config.get("prompt_suffix") or "")
    if suffix.strip():
        return f"{prompt.rstrip()}\n\n{suffix.strip()}\n"
    return prompt
