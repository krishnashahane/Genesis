"""Pluggable LLM provider.

Genesis never hardcodes a single model vendor. Agents depend only on the
``LLMProvider`` protocol (an async ``complete`` method). Three implementations
ship in-box:

* ``MockProvider``  — deterministic, offline, used in tests & zero-key dev.
* ``AnthropicProvider`` — Claude models (``anthropic`` SDK).
* ``GeminiProvider`` — Google Gemini (``google-generativeai`` SDK).

``build_llm`` selects the provider from Settings. If a real provider is
requested but its SDK/key is missing, it degrades to the mock with a warning so
the runtime always boots.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from genesis.config import Settings
from genesis.observability import METRICS, get_logger

log = get_logger("genesis.llm")


class Message(BaseModel):
    role: str  # system | user | assistant
    content: str


class LLMProvider(Protocol):
    name: str

    async def complete(self, messages: list[Message], **kwargs: object) -> str: ...


class MockProvider:
    """Deterministic provider. Echoes a structured, role-aware response so the
    full agent pipeline is exercisable without any API key or network."""

    name = "mock"

    async def complete(self, messages: list[Message], **kwargs: object) -> str:
        METRICS.incr("llm.calls")
        system = next((m.content for m in messages if m.role == "system"), "")
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        role = system.split(".")[0][:80] if system else "agent"
        return (
            f"[mock:{role}] processed request. "
            f"input_summary={user[:160]!r}"
        )


class AnthropicProvider:  # pragma: no cover - requires network/SDK
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, messages: list[Message], **kwargs: object) -> str:
        METRICS.incr("llm.calls")
        system = "\n".join(m.content for m in messages if m.role == "system")
        convo = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        resp = await self._client.messages.create(
            model=self._model,
            system=system or None,
            messages=convo or [{"role": "user", "content": ""}],
            max_tokens=int(kwargs.get("max_tokens", 1024)),
        )
        return "".join(block.text for block in resp.content if block.type == "text")


class GeminiProvider:  # pragma: no cover - requires network/SDK
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    async def complete(self, messages: list[Message], **kwargs: object) -> str:
        METRICS.incr("llm.calls")
        prompt = "\n\n".join(f"{m.role.upper()}: {m.content}" for m in messages)
        resp = await self._model.generate_content_async(prompt)
        return resp.text or ""


def build_llm(settings: Settings) -> LLMProvider:
    """Construct the configured provider, falling back to mock on any problem."""
    provider = settings.llm_provider
    try:
        if provider == "anthropic" and settings.anthropic_api_key:
            return AnthropicProvider(settings.anthropic_api_key, settings.llm_model)
        if provider == "gemini" and settings.gemini_api_key:
            return GeminiProvider(settings.gemini_api_key, settings.llm_model)
    except Exception as exc:  # pragma: no cover
        log.warning("llm.fallback_to_mock", requested=provider, error=str(exc))
        return MockProvider()
    if provider != "mock":
        log.warning("llm.missing_key", requested=provider)
    return MockProvider()
