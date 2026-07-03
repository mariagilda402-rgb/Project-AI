from __future__ import annotations

from src.agent.tool_markers import ToolStep, parse_tool_markers


def test_parse_open_app_and_vision_order():
    speak, steps = parse_tool_markers(
        "Vou abrir o app. [tool:open_app:Spotify] Depois olho a tela. [olhartela]"
    )
    assert "Spotify" not in speak  # marcador removido
    assert [s.kind for s in steps] == ["open_app", "vision"]
    assert steps[0].arg == "Spotify"
    assert steps[1].arg is None


def test_parse_desktop_with_arg():
    speak, steps = parse_tool_markers("[tool:desktop:alarme 22h] Pronto.")
    assert steps[0] == ToolStep("desktop", "alarme 22h")
    assert "Pronto" in speak


def test_case_insensitive():
    _, steps = parse_tool_markers("[TOOL:VISION]")
    assert steps[0].kind == "vision"
