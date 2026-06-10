from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request

from insights_repetition.answer_extraction import estimate_tokens
from insights_repetition.llm.base import LLMBridge
from insights_repetition.types import LLMRequest, LLMResponse, TokenUsage


def build_ssl_context() -> ssl.SSLContext | None:
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if cafile:
        return ssl.create_default_context(cafile=cafile)

    try:
        import certifi  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def ssl_error_hint(exc: urllib.error.URLError) -> str:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc):
        return (
            " SSL certificate verification failed. On macOS with python.org Python, run the "
            "'Install Certificates.command' shipped with Python, use the project script with a Python "
            "runtime that has certificates, or set SSL_CERT_FILE/REQUESTS_CA_BUNDLE to a valid CA bundle."
        )
    return ""


def extract_reasoning_text(message: dict) -> str:
    direct = str(
        message.get("reasoning_content")
        or message.get("reasoning")
        or message.get("thinking")
        or ""
    )
    if direct:
        return direct

    details = message.get("reasoning_details") or []
    if not isinstance(details, list):
        return ""

    parts: list[str] = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        text = detail.get("text") or detail.get("summary") or detail.get("content")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


class OpenAICompatibleBridge(LLMBridge):
    name = "openai-compatible"

    def __init__(
        self,
        api_base_url: str,
        api_key_env: str = "INSIGHTS_API_KEY",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.api_base_url = api_base_url
        self.api_key_env = api_key_env
        self.extra_headers = extra_headers or {}

    def generate(self, request: LLMRequest) -> LLMResponse:
        api_key = os.environ.get(self.api_key_env, "").strip()
        if not api_key:
            raise RuntimeError(f"missing API key env var: {self.api_key_env}")

        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        payload.update(request.extra_body)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        headers.update({key: value for key, value in self.extra_headers.items() if value})

        http_request = urllib.request.Request(
            self.api_base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        urlopen_kwargs = {"timeout": request.timeout_s or 600}
        ssl_context = build_ssl_context()
        if ssl_context is not None:
            urlopen_kwargs["context"] = ssl_context
        try:
            with urllib.request.urlopen(http_request, **urlopen_kwargs) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible request failed: {exc}.{ssl_error_hint(exc)}") from exc

        choices = raw.get("choices") or []
        message = (choices[0].get("message") if choices else {}) or {}
        text = str(message.get("content") or "")
        reasoning_text = extract_reasoning_text(message)
        usage_raw = raw.get("usage") or {}
        completion_details = usage_raw.get("completion_tokens_details") or {}
        cost = usage_raw.get("cost")
        cost_details = usage_raw.get("cost_details") or {}
        prompt_tokens = usage_raw.get("prompt_tokens")
        completion_tokens = usage_raw.get("completion_tokens")
        reasoning_tokens = completion_details.get("reasoning_tokens")
        if reasoning_tokens is None:
            reasoning_tokens = usage_raw.get("reasoning_tokens")
        estimated = prompt_tokens is None or completion_tokens is None
        if prompt_tokens is None:
            prompt_tokens = estimate_tokens(request.prompt)
        if completion_tokens is None:
            completion_tokens = estimate_tokens(text + "\n" + reasoning_text)

        usage = TokenUsage(
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            reasoning_tokens=int(reasoning_tokens) if reasoning_tokens is not None else None,
            visible_output_tokens=estimate_tokens(text),
            total_tokens=int(usage_raw.get("total_tokens") or (int(prompt_tokens) + int(completion_tokens))),
            cost=float(cost) if cost is not None else None,
            cost_currency="USD" if cost is not None else None,
            cost_details=cost_details,
            estimated=estimated,
            raw_usage=usage_raw,
        )
        return LLMResponse(
            text=text,
            reasoning_text=reasoning_text,
            usage=usage,
            provider=self.name,
            model=request.model,
            raw_response=raw,
        )
