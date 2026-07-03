from __future__ import annotations

from src.agent.prompts import build_function_calling_system_prompt


def test_function_prompt_includes_active_mode_and_allowed_tools():
    prompt = build_function_calling_system_prompt(
        "Persona base",
        [],
        "",
        active_mode="news",
        allowed_tool_names=frozenset({"nexus_command", "search_web"}),
    )

    runtime_block = prompt.split("## Modo ativo e ferramentas")[-1]

    assert "Modo ativo: news" in prompt
    assert "nexus_command" in runtime_block
    assert "search_web" in runtime_block
    assert "manage_files" not in runtime_block
