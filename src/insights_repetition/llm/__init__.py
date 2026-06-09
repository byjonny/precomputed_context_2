from __future__ import annotations

from insights_repetition.llm.base import LLMBridge
from insights_repetition.llm.mock import MockBridge
from insights_repetition.llm.ollama import OllamaBridge
from insights_repetition.llm.openai_compat import OpenAICompatibleBridge
from insights_repetition.llm.openrouter import OpenRouterBridge

OPENAI_DEFAULT_URL = "https://api.openai.com/v1/chat/completions"
OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_llm_bridge(
    provider: str,
    *,
    ollama_url: str = "http://localhost:11434",
    api_base_url: str = "https://api.openai.com/v1/chat/completions",
    api_key_env: str = "INSIGHTS_API_KEY",
) -> LLMBridge:
    if provider == MockBridge.name:
        return MockBridge()
    if provider == OllamaBridge.name:
        return OllamaBridge(ollama_url)
    if provider == OpenRouterBridge.name:
        if api_base_url == OPENAI_DEFAULT_URL:
            api_base_url = OPENROUTER_DEFAULT_URL
        if api_key_env in {"INSIGHTS_API_KEY", "TRS_API_KEY"}:
            api_key_env = "OPENROUTER_API_KEY"
        return OpenRouterBridge(api_base_url=api_base_url, api_key_env=api_key_env)
    if provider == OpenAICompatibleBridge.name:
        return OpenAICompatibleBridge(api_base_url=api_base_url, api_key_env=api_key_env)
    raise ValueError("unknown provider {!r}; choose mock, ollama, openrouter, or openai-compatible".format(provider))
