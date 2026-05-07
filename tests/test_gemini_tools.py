from __future__ import annotations

from src.agent.gemini_tools import build_agent_tool, build_openai_agent_tools


def test_build_agent_tool_has_declarations():
    tool = build_agent_tool()
    fds = tool.function_declarations or []
    names = {fd.name for fd in fds}
    assert "analyze_screen" in names
    assert "open_windows_application" in names


def test_openai_tools_count():
    tools = build_openai_agent_tools()
    assert len(tools) == 7
    assert tools[0]["function"]["name"]
