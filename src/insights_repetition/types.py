from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProblemRecord:
    question_id: str
    question: str
    answer: str
    skill_text: str
    dataset_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    visible_output_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    cost_currency: str | None = None
    cost_details: dict[str, Any] = field(default_factory=dict)
    estimated: bool = False
    raw_usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMRequest:
    prompt: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 2048
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    usage: TokenUsage
    provider: str
    model: str
    reasoning_text: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    is_correct: bool
    predicted_answer: str
    gold_answer: str
    predicted_normalized: str
    gold_normalized: str
    method: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
