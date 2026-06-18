"""The single provider-specific module: OpenAI Chat Completions.

Swapping providers (Claude, Azure, a local model, …) means rewriting only this
file — the rest of the app calls `is_enabled()` / `chat()` / `chat_stream()`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

_DEFAULT_MODEL = "gpt-4o-mini"


def model_name() -> str:
    return os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL)


def is_enabled() -> bool:
    """True when an API key is configured (otherwise callers use the fallback path)."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def _client():
    from openai import OpenAI  # imported lazily so the package isn't required at import time

    return OpenAI()  # reads OPENAI_API_KEY from the environment


def chat(messages: list[dict]) -> str:
    """Non-streaming completion → the assistant's text."""
    resp = _client().chat.completions.create(
        model=model_name(),
        messages=messages,
        temperature=0.2,  # low variance — we want grounded, repeatable analysis
    )
    return resp.choices[0].message.content or ""


def chat_stream(messages: list[dict]) -> Iterator[str]:
    """Streaming completion → text deltas as they arrive."""
    stream = _client().chat.completions.create(
        model=model_name(),
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
