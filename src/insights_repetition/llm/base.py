from __future__ import annotations

from abc import ABC, abstractmethod

from insights_repetition.types import LLMRequest, LLMResponse


class LLMBridge(ABC):
    name = "base"

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
