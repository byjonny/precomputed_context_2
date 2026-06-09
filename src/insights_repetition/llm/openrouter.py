from __future__ import annotations

import os

from insights_repetition.llm.openai_compat import OpenAICompatibleBridge


class OpenRouterBridge(OpenAICompatibleBridge):
    name = "openrouter"

    def __init__(
        self,
        api_base_url: str = "https://openrouter.ai/api/v1/chat/completions",
        api_key_env: str = "OPENROUTER_API_KEY",
    ) -> None:
        super().__init__(
            api_base_url=api_base_url,
            api_key_env=api_key_env,
            extra_headers={
                "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", ""),
                "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "insights-repetition"),
            },
        )
