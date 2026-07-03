from __future__ import annotations

from src.services.tts_benchmark import benchmark_texts, parse_provider_list


def test_parse_provider_list_keeps_order_and_removes_duplicates():
    assert parse_provider_list("xtts, edge, kokoro, edge") == [
        "xtts",
        "edge",
        "kokoro",
    ]


def test_benchmark_texts_cover_neutral_urgent_and_friendly_styles():
    texts = benchmark_texts()
    labels = {item.label for item in texts}

    assert {"neutral", "urgent", "friendly"}.issubset(labels)
    assert all(item.text for item in texts)
