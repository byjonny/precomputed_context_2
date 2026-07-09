from __future__ import annotations

import json
import urllib.error
import urllib.request

from insights_repetition.answer_extraction import estimate_tokens
from insights_repetition.llm.base import LLMBridge
from insights_repetition.types import LLMRequest, LLMResponse, TokenUsage


class OllamaBridge(LLMBridge):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        # Map the config's reasoning flag to Ollama's `think` toggle so reasoning-
        # capable models (qwen3.x, deepseek-r1, gemma) can be forced non-reasoning.
        # {"reasoning": {"enabled": false}} -> think:false (no chain-of-thought).
        reasoning = (request.extra_body or {}).get("reasoning")
        if isinstance(reasoning, dict) and "enabled" in reasoning:
            payload["think"] = bool(reasoning["enabled"])
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=600) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        text = str(raw.get("response") or "")
        prompt_tokens = raw.get("prompt_eval_count")
        completion_tokens = raw.get("eval_count")
        estimated = prompt_tokens is None or completion_tokens is None
        if prompt_tokens is None:
            prompt_tokens = estimate_tokens(request.prompt)
        if completion_tokens is None:
            completion_tokens = estimate_tokens(text)

        usage = TokenUsage(
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            reasoning_tokens=None,
            visible_output_tokens=estimate_tokens(text),
            total_tokens=int(prompt_tokens) + int(completion_tokens),
            estimated=estimated,
            raw_usage={key: raw.get(key) for key in ["prompt_eval_count", "eval_count", "total_duration"]},
        )
        return LLMResponse(text=text, usage=usage, provider=self.name, model=request.model, raw_response=raw)
