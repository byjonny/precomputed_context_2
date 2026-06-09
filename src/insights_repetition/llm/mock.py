from __future__ import annotations

from insights_repetition.answer_extraction import estimate_tokens
from insights_repetition.llm.base import LLMBridge
from insights_repetition.types import LLMRequest, LLMResponse, TokenUsage


class MockBridge(LLMBridge):
    name = "mock"

    def generate(self, request: LLMRequest) -> LLMResponse:
        gold = str(request.metadata.get("gold_answer") or "MOCK")
        text = f"Final answer: {gold}"
        usage = TokenUsage(
            prompt_tokens=estimate_tokens(request.prompt),
            completion_tokens=estimate_tokens(text),
            reasoning_tokens=0,
            visible_output_tokens=estimate_tokens(text),
            total_tokens=estimate_tokens(request.prompt) + estimate_tokens(text),
            estimated=True,
            raw_usage={"source": "mock_estimate"},
        )
        return LLMResponse(text=text, usage=usage, provider=self.name, model=request.model)
