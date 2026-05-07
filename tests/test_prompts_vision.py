from __future__ import annotations

from src.agent.prompts import build_vision_instruction


def test_vision_instruction_short_by_default():
    text = build_vision_instruction("O que tem na tela?")
    assert "5 frases" in text or "curtas" in text


def test_vision_instruction_allows_detail_when_asked():
    text = build_vision_instruction("Me da um relatório completo do que você vê.")
    assert "detalhe" in text.lower() or "mais" in text.lower()
