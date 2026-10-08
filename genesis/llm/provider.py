"""Pluggable LLM providers with an offline-safe mock default."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from genesis.config import Settings
from genesis.observability import METRICS


class Message(BaseModel):
    role: str
    content: str


class LLMProvider(Protocol):
    name: str

    async def complete(self, messages: list[Message], **kwargs: object) -> str: ...


class MockProvider:
    name = "mock"

    async def complete(self, messages: list[Message], **kwargs: object) -> str:
        METRICS.incr("llm.calls")
        system = next((message.content for message in messages if message.role == "system"), "")
        user = next((message.content for message in reversed(messages) if message.role == "user"), "")
        role = system.split(".", 1)[0][:80] if system else "agent"
        return f"[mock:{role}] processed request. input_summary={user[:160]!r}"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, messages: list[Message], **kwargs: object) -> str:
        METRICS.incr("llm.calls")
        system = "\n".join(message.content for message in messages if message.role == "system")
        conversation = [
            {"role": message.role, "content": message.content}
            for message in messages
            if message.role in {"user", "assistant"}
        ]
        response = await self._client.messages.create(
            model=self._model,
            system=system or None,
            messages=conversation or [{"role": "user", "content": ""}],
            max_tokens=int(kwargs.get("max_tokens", 1024)),
        )
        return "".join(block.text for block in response.content if block.type == "text")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def complete(self, messages: list[Message], **kwargs: object) -> str:
        from google.genai import types

        METRICS.incr("llm.calls")
        prompt = "\n\n".join(
            f"{message.role.upper()}: {message.content}" for message in messages
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=int(kwargs.get("max_tokens", 1024)),
            ),
        )
        return response.text or ""


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockProvider()

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError(
                "GENESIS_ANTHROPIC_API_KEY is required for the anthropic provider."
            )
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "GENESIS_GEMINI_API_KEY is required for the gemini provider."
            )
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
