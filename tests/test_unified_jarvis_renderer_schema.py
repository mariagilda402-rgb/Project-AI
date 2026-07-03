from src.jarvis_unified.renderer_schema import (
    make_dashboard,
    make_render_update,
    validate_block,
)


def test_validate_supported_blocks():
    assert validate_block({"type": "text", "text": "Oi"})["ok"] is True
    assert validate_block({"type": "chart_pie"})["ok"] is False


def test_make_dashboard_and_update():
    doc = make_dashboard("market", "Mercado", [{"type": "text", "text": "Resumo"}])
    update = make_render_update(
        "market",
        "append",
        {"type": "assistant_transcript", "text": "Falando..."},
    )

    assert doc["surface_id"] == "market"
    assert update["type"] == "render_update"
    assert update["payload"]["op"] == "append"
