from __future__ import annotations

from src.agent.orchestrator import _is_short_greeting


def test_greetings_detected():
    assert _is_short_greeting("olá")
    assert _is_short_greeting("Olá!")
    assert _is_short_greeting("  oi  ")
    assert _is_short_greeting("bom dia")


def test_normal_message_not_greeting():
    assert not _is_short_greeting("O que aparece na minha tela?")
    assert not _is_short_greeting("abre o spotify")
