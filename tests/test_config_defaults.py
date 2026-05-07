from __future__ import annotations

from src.config import _default_vision_provider


def test_vision_follows_groq_when_llm_is_groq():
    assert (
        _default_vision_provider("", "groq", "gemini-key", "nv-key", "groq-key")
        == "groq"
    )


def test_vision_explicit_overrides():
    assert (
        _default_vision_provider("gemini", "groq", "gk", "nk", "gq") == "gemini"
    )
