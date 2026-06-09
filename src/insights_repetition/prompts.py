from __future__ import annotations


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


def repeated_hints(skill_text: str, k: int, delimiter: str = "\n\n--- same hint repeated ---\n\n") -> str:
    if k <= 0:
        return ""
    return delimiter.join(skill_text.strip() for _ in range(k))


def build_prompt(question: str, skill_text: str, k: int) -> str:
    if k <= 0:
        return DIRECT_TEMPLATE.format(question=question)
    return TRS_TEMPLATE.format(question=question, hints=repeated_hints(skill_text, k))
