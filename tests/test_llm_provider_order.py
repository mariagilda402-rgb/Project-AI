from __future__ import annotations

from src.services.llm import LLMService


def test_merge_openai_messages_fuses_extra_system():
    msgs = LLMService._merge_messages_for_openai_chat(
        "Prompt principal.",
        [
            {"role": "user", "content": "Oi"},
            {"role": "system", "content": "Preferencias: x"},
        ],
    )
    assert msgs[0]["role"] == "system"
    assert "Prompt principal" in msgs[0]["content"]
    assert "Preferencias" in msgs[0]["content"]
    assert len([m for m in msgs if m["role"] == "system"]) == 1
    assert msgs[-1] == {"role": "user", "content": "Oi"}


def test_order_primary_gemini_skip_gemini():
    llm = LLMService(
        gemini_api_key="x",
        gemini_model="m",
        primary_llm_provider="gemini",
    )
    assert llm._chat_provider_order(skip_gemini=True) == ["openrouter", "nvidia", "groq"]


def test_order_primary_nvidia():
    llm = LLMService(
        gemini_api_key="x",
        gemini_model="m",
        nvidia_api_key="k",
        nvidia_model="meta/llama",
        primary_llm_provider="nvidia",
    )
    assert llm._chat_provider_order(skip_gemini=False)[0] == "nvidia"


def test_order_primary_groq():
    llm = LLMService(
        gemini_api_key="x",
        gemini_model="m",
        groq_api_key="g",
        groq_model="llama-3.1-8b-instant",
        primary_llm_provider="groq",
        fallback_gemini=False,
    )
    order = llm._chat_provider_order(skip_gemini=False)
    assert order[0] == "groq"
    assert "gemini" not in order
    assert llm.wants_groq_native_tools() is True


def test_order_groq_can_include_gemini_fallback_when_enabled():
    llm = LLMService(
        gemini_api_key="x",
        gemini_model="m",
        groq_api_key="g",
        groq_model="llama-3.1-8b-instant",
        primary_llm_provider="groq",
        fallback_gemini=True,
    )
    order = llm._chat_provider_order(skip_gemini=False)
    assert order[0] == "groq"
    assert "gemini" in order


def test_wants_groq_tools_false_without_key():
    llm = LLMService(
        gemini_api_key="x",
        gemini_model="m",
        primary_llm_provider="groq",
    )
    assert llm.wants_groq_native_tools() is False
