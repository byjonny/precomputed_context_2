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


FULL_BLOCK_WITH_HINT_TEMPLATE = """[Repeated Block {index}]
[Solving Hints]
{hints}
[/Solving Hints]

Problem:
{question}
[/Repeated Block {index}]"""


FULL_BLOCK_PROBLEM_ONLY_TEMPLATE = """[Repeated Problem {index}]
Problem:
{question}
[/Repeated Problem {index}]"""


DEFAULT_REPEAT_DELIMITER = "\n\nLet me repeat that:\n\n"
DEFAULT_HINT_DELIMITER = DEFAULT_REPEAT_DELIMITER
DEFAULT_PROBLEM_DELIMITER = DEFAULT_REPEAT_DELIMITER
DEFAULT_BLOCK_DELIMITER = DEFAULT_REPEAT_DELIMITER


def _positive_int(value: Any, default: int) -> int:
    if value is None:
        return default
    parsed = int(value)
    return max(0, parsed)


def _insight_repetitions(k: int, prompt_config: dict[str, Any]) -> int:
    value = prompt_config.get("insight_repetitions", prompt_config.get("hint_repetitions", "k"))
    if value == "k":
        return max(0, k)
    return _positive_int(value, max(0, k))


def _format(template: str, **values: Any) -> str:
    return template.format(**values)


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
    problem_count = _positive_int(prompt_config.get("problem_repetitions"), 1)
    hint_delimiter = str(prompt_config.get("hint_delimiter", DEFAULT_HINT_DELIMITER))
    problem_delimiter = str(prompt_config.get("problem_delimiter", DEFAULT_PROBLEM_DELIMITER))
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
        template = str(prompt_config.get("direct_template", DIRECT_TEMPLATE))
        return _format(template, **values)

    template = str(prompt_config.get("hinted_template", TRS_TEMPLATE))
    return _format(template, **values)


def build_full_block_prompt(question: str, skill_text: str, k: int, prompt_config: dict[str, Any]) -> str:
    insight_count = _insight_repetitions(k, prompt_config)
    problem_count = _positive_int(prompt_config.get("problem_repetitions"), 1)
    block_count = max(insight_count, problem_count, 1)
    block_delimiter = str(prompt_config.get("block_delimiter", DEFAULT_BLOCK_DELIMITER))
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


def build_prompt(question: str, skill_text: str, k: int, prompt_config: dict[str, Any] | None = None) -> str:
    if prompt_config is None:
        if k <= 0:
            return DIRECT_TEMPLATE.format(question=question)
        return TRS_TEMPLATE.format(question=question, hints=repeated_hints(skill_text, k))

    layout = str(prompt_config.get("layout", "separate"))
    if layout == "full_block":
        return build_full_block_prompt(question, skill_text, k, prompt_config)
    if layout != "separate":
        raise ValueError(f"unknown prompt layout: {layout}")
    return build_separate_prompt(question, skill_text, k, prompt_config)
