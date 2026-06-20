"""LLM provider abstraction with offline-safe mock default."""

from genesis.llm.provider import LLMProvider, Message, build_llm

__all__ = ["LLMProvider", "Message", "build_llm"]
