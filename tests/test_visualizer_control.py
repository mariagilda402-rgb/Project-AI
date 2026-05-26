from __future__ import annotations

import json

from src.tools.base import ToolResult
from src.tools.registry import ToolRegistry
from src.tools.visualizer_control import VisualizerControlTool


def test_visualizer_control_can_set_particle_core_state(tmp_path):
    state_file = tmp_path / "visualizer_state.json"
    tool = VisualizerControlTool(str(state_file))

    result = tool.run("estado executando sincronizando comandos")
    state = json.loads(state_file.read_text(encoding="utf-8"))

    assert result.ok is True
    assert state["status"] == "executing"
    assert state["subtitle"] == "sincronizando comandos"
    assert "executando" in result.message.lower()


def test_visualizer_control_can_set_transient_emotion(tmp_path):
    state_file = tmp_path / "visualizer_state.json"
    tool = VisualizerControlTool(str(state_file))

    result = tool.run("emocao feliz")
    state = json.loads(state_file.read_text(encoding="utf-8"))

    assert result.ok is True
    assert state["emotion"] == "happy"
    assert "feliz" in result.message.lower()


def test_tool_registry_drives_visualizer_state_around_marker_tools(monkeypatch):
    events = []

    monkeypatch.setattr(
        "src.services.visualizer.set_executing",
        lambda detail="": events.append(("executing", detail)),
    )
    monkeypatch.setattr(
        "src.services.visualizer.set_success",
        lambda detail="": events.append(("success", detail)),
    )
    monkeypatch.setattr(
        "src.services.visualizer.set_alert",
        lambda detail="": events.append(("alert", detail)),
    )

    class DummyNexusTool:
        name = "nexus"
        description = "Nexus"
        critical = False

        def run(self, command: str) -> ToolResult:
            return ToolResult(True, "ok")

    registry = ToolRegistry([DummyNexusTool()], require_critical_confirmation=False)

    result = registry.run_by_marker("nexus", "abrir painel de estudos", "abrir painel de estudos")

    assert result.ok is True
    assert events[0][0] == "executing"
    assert "nexus" in events[0][1].lower()
    assert events[-1][0] == "success"


def test_tool_registry_uses_alert_state_for_failed_marker_tool(monkeypatch):
    events = []

    monkeypatch.setattr(
        "src.services.visualizer.set_executing",
        lambda detail="": events.append(("executing", detail)),
    )
    monkeypatch.setattr(
        "src.services.visualizer.set_success",
        lambda detail="": events.append(("success", detail)),
    )
    monkeypatch.setattr(
        "src.services.visualizer.set_alert",
        lambda detail="": events.append(("alert", detail)),
    )

    class FailingNexusTool:
        name = "nexus"
        description = "Nexus"
        critical = False

        def run(self, command: str) -> ToolResult:
            return ToolResult(False, "falhou")

    registry = ToolRegistry([FailingNexusTool()], require_critical_confirmation=False)

    result = registry.run_by_marker("nexus", "comando ruim", "comando ruim")

    assert result.ok is False
    assert events[0][0] == "executing"
    assert events[-1][0] == "alert"


def test_tool_registry_does_not_override_direct_visualizer_control(monkeypatch):
    events = []

    monkeypatch.setattr(
        "src.services.visualizer.set_executing",
        lambda detail="": events.append(("executing", detail)),
    )
    monkeypatch.setattr(
        "src.services.visualizer.set_success",
        lambda detail="": events.append(("success", detail)),
    )
    monkeypatch.setattr(
        "src.services.visualizer.set_alert",
        lambda detail="": events.append(("alert", detail)),
    )

    class DummyVisualizerTool:
        name = "visualizer_control"
        description = "Visualizer"
        critical = False

        def run(self, command: str) -> ToolResult:
            return ToolResult(True, "estado alterado")

    registry = ToolRegistry([DummyVisualizerTool()], require_critical_confirmation=False)

    result = registry.run_by_marker("visualizer_control", "estado alerta", "estado alerta")

    assert result.ok is True
    assert events == []


def test_desktop_app_applies_visualizer_position_and_display_mode(tmp_path, monkeypatch):
    import src.services.visualizer as visualizer
    from src.ui.desktop_app import DesktopApp

    class FakeWindow:
        def __init__(self):
            self.moves = []
            self.shown = 0
            self.hidden = 0

        def move(self, x: int, y: int) -> None:
            self.moves.append((x, y))

        def show(self) -> None:
            self.shown += 1

        def hide(self) -> None:
            self.hidden += 1

    state_file = tmp_path / "visualizer_state.json"
    state_file.write_text(
        json.dumps({"position": "bottom_right", "display_mode": "hidden", "status": "idle"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(visualizer, "STATE_FILE", state_file)
    monkeypatch.setattr(
        "src.ui.desktop_app.webview.screens",
        [type("Screen", (), {"width": 1000, "height": 800})()],
    )

    app = DesktopApp.__new__(DesktopApp)
    app.ghost_window = FakeWindow()
    app._panel_visible = False
    app._visualizer_last_state = ""
    app._visualizer_last_position = ""
    app._visualizer_last_display_mode = ""

    app._apply_visualizer_window_state()

    assert app.ghost_window.moves[-1] == (700, 450)
    assert app.ghost_window.hidden == 1

    state_file.write_text(
        json.dumps({"position": "top_right", "display_mode": "always", "status": "executing"}),
        encoding="utf-8",
    )

    app._apply_visualizer_window_state()

    assert app.ghost_window.moves[-1] == (700, 50)
    assert app.ghost_window.shown == 1
