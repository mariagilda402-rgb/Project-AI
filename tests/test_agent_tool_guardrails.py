from __future__ import annotations

from src.agent.tool_guardrails import ToolCallGuardrailController


def test_guardrail_blocks_exact_repeated_call_after_threshold():
    guard = ToolCallGuardrailController(exact_repeat_limit=2)

    assert guard.before_call("search_web", {"query": "x"}).allow is True
    guard.after_call("search_web", {"query": "x"}, "same result")
    assert guard.before_call("search_web", {"query": "x"}).allow is True
    guard.after_call("search_web", {"query": "x"}, "same result")

    decision = guard.before_call("search_web", {"query": "x"})

    assert decision.allow is False
    assert "repetida" in decision.message.lower()


def test_guardrail_resets_per_turn():
    guard = ToolCallGuardrailController(exact_repeat_limit=1)

    assert guard.before_call("search_web", {"query": "x"}).allow is True
    guard.after_call("search_web", {"query": "x"}, "same")
    assert guard.before_call("search_web", {"query": "x"}).allow is False

    guard.reset_turn()

    assert guard.before_call("search_web", {"query": "x"}).allow is True


def test_guardrail_flags_repeated_no_progress_result():
    guard = ToolCallGuardrailController(no_progress_limit=2)

    guard.after_call("analyze_screen", {"instruction": "olhe"}, "Sem mudanca.")
    decision = guard.after_call(
        "analyze_screen", {"instruction": "olhe"}, "Sem mudanca."
    )

    assert decision.allow is False
    assert "sem progresso" in decision.message.lower()
