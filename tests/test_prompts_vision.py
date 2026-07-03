from __future__ import annotations

from src.agent.prompts import build_vision_instruction, vision_user_wants_detail


def test_vision_instruction_short_by_default():
    text = build_vision_instruction("O que tem na tela?", detail=False)
    assert "5 frases" in text or "curtas" in text.lower()


def test_vision_instruction_allows_detail_when_asked():
    text = build_vision_instruction("Me da um relatório completo do que você vê.", detail=True)
    assert "estruturada" in text.lower() or "marcadores" in text.lower() or "8 frases" in text


def test_vision_user_wants_detail_keyword():
    assert vision_user_wants_detail("Quero um relatório detalhado", vision_detail_default=False) is True
    assert vision_user_wants_detail("O que tem aí?", vision_detail_default=False) is False
