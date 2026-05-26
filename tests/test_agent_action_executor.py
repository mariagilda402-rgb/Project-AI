from __future__ import annotations

from src.agent.action_executor import ActionExecutor
from src.agent.tool_guardrails import ToolCallGuardrailController


def test_action_executor_blocks_tool_outside_selected_toolset():
    executor = ActionExecutor(
        allowed_tool_names=frozenset({"search_web"}),
        guardrails=ToolCallGuardrailController(),
        legacy_execute=lambda name, args, user_text: "should not run",
    )

    result = executor.execute("manage_files", {"action": "delete_file"}, "apague")

    assert "bloqueada" in result.lower()


def test_action_executor_delegates_allowed_tool():
    calls = []

    executor = ActionExecutor(
        allowed_tool_names=frozenset({"search_web"}),
        guardrails=ToolCallGuardrailController(),
        legacy_execute=lambda name, args, user_text: calls.append((name, args, user_text))
        or "ok",
    )

    result = executor.execute("search_web", {"query": "tempo"}, "pesquise tempo")

    assert result == "ok"
    assert calls == [("search_web", {"query": "tempo"}, "pesquise tempo")]


def test_action_executor_returns_guardrail_message_for_repeated_call():
    guardrails = ToolCallGuardrailController(exact_repeat_limit=1)
    executor = ActionExecutor(
        allowed_tool_names=frozenset({"search_web"}),
        guardrails=guardrails,
        legacy_execute=lambda name, args, user_text: "ok",
    )

    assert executor.execute("search_web", {"query": "x"}, "x") == "ok"
    result = executor.execute("search_web", {"query": "x"}, "x")

    assert "repetida" in result.lower()
