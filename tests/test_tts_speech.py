from __future__ import annotations

from src.services.tts import split_text_for_tts, strip_text_for_speech


def test_strip_markdown():
    raw = "**IDE** PyCharm\n\n- item um\n- dois"
    out = strip_text_for_speech(raw)
    assert "**" not in out
    assert "IDE" in out


def test_split_respects_max():
    s = "Um. " * 400
    parts = split_text_for_tts(s, 80)
    assert len(parts) >= 2
    assert all(len(p) <= 85 for p in parts)
